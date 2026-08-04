"""Safely repair historical SynthTrade exits from the exact OKX OCO fill.

The default command is read-only: it creates a reviewable JSON report.  Writing
is deliberately a second, explicit step and only applies rows marked verified
by the report.  It never matches an exit by symbol, side, or chronology.

Examples (run from the repository root):

    .venv\\Scripts\\python scripts/repair_okx_trade_history.py \
        --session-id <uuid> --report C:\\tmp\\okx-repair.json

    .venv\\Scripts\\python scripts/repair_okx_trade_history.py \
        --apply --report C:\\tmp\\okx-repair.json --confirm APPLY_OKX_REPAIR
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "synthtrade" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db.supabase_client import get_supabase  # noqa: E402
from app.execution.okx_exchange import OkxExchangeAdapter  # noqa: E402
from app.scalping.reconciliation import (  # noqa: E402
    _get_verified_bracket_fills,
    _matched_bracket_fill,
)


CONFIRM_TOKEN = "APPLY_OKX_REPAIR"
DEFAULT_FEE_RATE = 0.001


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _repair_values(row: dict[str, Any], match: dict[str, Any], fee_rate: float) -> dict[str, Any]:
    """Build an auditable DB update from an exact OCO match only."""
    entry = float(row["entry_price"])
    quantity = float(row["quantity"])
    exit_price = float(match["fill_price"])
    side = row.get("side", "BUY")
    gross = (exit_price - entry) * quantity if side == "BUY" else (entry - exit_price) * quantity

    stored_entry_fee = _number(row.get("entry_commission"))
    stored_exit_fee = _number(row.get("exit_commission"))
    entry_fee = stored_entry_fee if stored_entry_fee is not None else entry * quantity * fee_rate
    exit_fee = stored_exit_fee if stored_exit_fee is not None else exit_price * quantity * fee_rate
    pnl = gross - entry_fee - exit_fee

    return {
        "status": "closed",
        "exit_price": exit_price,
        "exit_time": match["fill_time"],
        "pnl": round(pnl, 2),
        "pnl_pct": round((pnl / (entry * quantity)) * 100, 2),
        "signal_reason": match["reason"],
        "entry_commission": entry_fee,
        "exit_commission": exit_fee,
        "repair_source": match["source"],
        "exit_order_id": match.get("exit_order_id"),
        "fee_source": "stored" if stored_entry_fee is not None and stored_exit_fee is not None else "estimated",
    }


def _validate_row(row: dict[str, Any]) -> str | None:
    if row.get("exchange_provider") not in (None, "okx"):
        return "skip_non_okx_provider"
    if not (row.get("exchange_bracket_id") or row.get("oco_order_list_id")):
        return "skip_missing_oco_id"
    if _number(row.get("entry_price")) in (None, 0) or _number(row.get("quantity")) in (None, 0):
        return "skip_invalid_entry_or_quantity"
    if not row.get("symbol"):
        return "skip_missing_symbol"
    return None


def _load_candidates(args: argparse.Namespace) -> list[dict[str, Any]]:
    db = get_supabase()
    if args.trade_id:
        rows: list[dict[str, Any]] = []
        for trade_id in args.trade_id:
            response = db.table("scalping_trades").select("*").eq("id", trade_id).limit(1).execute()
            rows.extend(response.data or [])
        return rows

    query = db.table("scalping_trades").select("*").eq("session_id", args.session_id)
    if args.from_time:
        query = query.gte("entry_time", args.from_time)
    if args.to_time:
        query = query.lte("entry_time", args.to_time)
    return (query.order("entry_time", desc=False).limit(args.limit).execute().data or [])


async def _make_report(args: argparse.Namespace) -> dict[str, Any]:
    adapter = OkxExchangeAdapter.from_settings()
    rows = _load_candidates(args)
    findings: list[dict[str, Any]] = []
    for row in rows:
        action = _validate_row(row)
        before = {
            key: row.get(key)
            for key in ("status", "exit_price", "exit_time", "pnl", "pnl_pct", "signal_reason", "exchange_bracket_id", "oco_order_list_id")
        }
        finding: dict[str, Any] = {"trade_id": row.get("id"), "symbol": row.get("symbol"), "before": before}
        if action:
            finding["action"] = action
            findings.append(finding)
            continue

        bracket_id = str(row.get("exchange_bracket_id") or row.get("oco_order_list_id"))
        fills = await _get_verified_bracket_fills(adapter, row["symbol"], bracket_id)
        match = _matched_bracket_fill(fills, bracket_id)
        if not match or not match.get("fill_time"):
            finding["action"] = "skip_unverified_oco_fill"
            finding["bracket_id"] = bracket_id
            findings.append(finding)
            continue

        after = _repair_values(row, match, args.fee_rate)
        finding.update({
            "action": "update_verified",
            "bracket_id": bracket_id,
            "after": after,
            "evidence": {
                "source": match["source"], "exit_order_id": match.get("exit_order_id"),
                "fill_time": match["fill_time"], "reason": match["reason"],
            },
        })
        findings.append(finding)

    return {
        "format": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run",
        "scope": {"session_id": args.session_id, "trade_ids": args.trade_id, "from": args.from_time, "to": args.to_time},
        "fee_rate_when_missing": args.fee_rate,
        "findings": findings,
    }


def _apply_report(report_path: Path, confirm: str) -> int:
    if confirm != CONFIRM_TOKEN:
        raise SystemExit(f"Refusing write: pass --confirm {CONFIRM_TOKEN}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("format") != 1 or report.get("mode") != "dry_run":
        raise SystemExit("Refusing write: report is not a valid dry-run report")

    db = get_supabase()
    updated = 0
    skipped = 0
    for finding in report.get("findings", []):
        if finding.get("action") != "update_verified":
            skipped += 1
            continue
        trade_id = finding.get("trade_id")
        after = finding.get("after") or {}
        # ``repair_source`` and evidence are report-only fields, not schema columns.
        update = {key: value for key, value in after.items() if key not in {"repair_source", "exit_order_id", "fee_source"}}
        current = db.table("scalping_trades").select("exchange_bracket_id,oco_order_list_id").eq("id", trade_id).limit(1).execute()
        if not current.data:
            skipped += 1
            continue
        current_bracket = current.data[0].get("exchange_bracket_id") or current.data[0].get("oco_order_list_id")
        if str(current_bracket) != str(finding.get("bracket_id")):
            skipped += 1
            continue
        db.table("scalping_trades").update(update).eq("id", trade_id).execute()
        updated += 1
    print(json.dumps({"updated": updated, "skipped": skipped, "report": str(report_path)}, indent=2))
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=False)
    scope.add_argument("--session-id", help="Repair only a single scalping session UUID")
    scope.add_argument("--trade-id", action="append", help="Repair one trade UUID; repeat for several rows")
    parser.add_argument("--from", dest="from_time", help="Optional ISO UTC lower bound for entry_time")
    parser.add_argument("--to", dest="to_time", help="Optional ISO UTC upper bound for entry_time")
    parser.add_argument("--limit", type=int, default=200, help="Maximum rows in a session dry-run (default: 200)")
    parser.add_argument("--fee-rate", type=float, default=DEFAULT_FEE_RATE, help="Fallback historical fee rate when DB fees are missing")
    parser.add_argument("--report", required=True, type=Path, help="JSON report path; must not overwrite an existing file in dry-run")
    parser.add_argument("--apply", action="store_true", help="Apply a previously reviewed dry-run report")
    parser.add_argument("--confirm", default="", help=f"Required with --apply: {CONFIRM_TOKEN}")
    args = parser.parse_args()
    if not args.apply and not (args.session_id or args.trade_id):
        parser.error("dry-run requires --session-id or at least one --trade-id")
    if args.fee_rate < 0 or args.fee_rate > 0.02:
        parser.error("--fee-rate must be between 0 and 0.02")
    return args


async def _main() -> int:
    args = _parse_args()
    if args.apply:
        return _apply_report(args.report, args.confirm)
    if args.report.exists():
        raise SystemExit(f"Refusing to overwrite existing report: {args.report}")
    report = await _make_report(args)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    verified = sum(item.get("action") == "update_verified" for item in report["findings"])
    print(json.dumps({"dry_run": True, "candidates": len(report["findings"]), "verified": verified, "report": str(args.report)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
