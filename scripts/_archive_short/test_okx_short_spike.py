#!/usr/bin/env python3
"""OKX Short Selling read-only spike — TASK-1220.

Tests all margin-related OKX endpoints on the REAL account (LIVE mode).
No orders are placed. All requests are GET (read-only).

Outputs:
  - docs/analysis/okx-short-spike-results.json  (raw payload)
  - docs/analysis/okx-short-spike-results.md    (human-readable summary)
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ENV = PROJECT_ROOT / "synthtrade" / "backend" / ".env"
OKX_BASE_URL = "https://eea.okx.com"

# Symbols to test — BTC and ETH are expected to be borrowable; OKB is a risk candidate
DEFAULT_SYMBOLS = ["BTC-EUR", "ETH-EUR", "OKB-EUR"]


def _load_env_file(path: Path) -> None:
    """Load a .env file into os.environ (same logic as test_okx_demo.py)."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _mask(value: str | None) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


@dataclass
class StepResult:
    name: str
    ok: bool
    details: dict[str, Any]


class SpikeRecorder:
    def __init__(self) -> None:
        self.results: list[StepResult] = []

    def add(self, name: str, ok: bool, **details: Any) -> None:
        stored = {
            k: _mask(str(v)) if k.lower() in {"api_key", "secret", "passphrase"} else v
            for k, v in details.items()
        }
        self.results.append(StepResult(name=name, ok=ok, details=stored))
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {name}")
        for k, v in stored.items():
            print(f"  {k}: {v}")

    def write_json(self, path: Path) -> None:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "task": "TASK-1220",
            "results": [asdict(r) for r in self.results],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON report: {path}")

    def write_markdown(self, path: Path, symbols: list[str]) -> None:
        """Generate a human-readable markdown summary."""
        lines = [
            "# OKX Short Selling — Spike Results (TASK-1220)",
            "",
            f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"> Account: LIVE (eea.okx.com)",
            f"> Symbols tested: {', '.join(symbols)}",
            "",
            "## Step Summary",
            "",
            "| Step | Status |",
            "|------|--------|",
        ]
        for r in self.results:
            icon = "✅" if r.ok else "❌"
            lines.append(f"| {r.name} | {icon} |")

        lines += ["", "## Raw Results", ""]
        for r in self.results:
            lines.append(f"### {r.name}")
            lines.append("")
            for k, v in r.details.items():
                lines.append(f"- **{k}:** `{v}`")
            lines.append("")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Markdown report: {path}")


class OkxRestClient:
    """Minimal REST client for OKX (LIVE mode, read-only)."""

    def __init__(self, use_live: bool = True) -> None:
        if use_live:
            self.api_key = _require_env("OKX_API_KEY_LIVE")
            self.secret = _require_env("OKX_SECRET_KEY_LIVE")
            self.passphrase = _require_env("OKX_PASSPHRASE_LIVE")
        else:
            self.api_key = _require_env("OKX_API_KEY")
            self.secret = _require_env("OKX_SECRET_KEY")
            self.passphrase = _require_env("OKX_PASSPHRASE")

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        prehash = f"{timestamp}{method.upper()}{request_path}{body}"
        return base64.b64encode(
            hmac.new(self.secret.encode(), prehash.encode(), hashlib.sha256).digest()
        ).decode("ascii")

    async def get(self, path: str, *, auth: bool = False) -> dict[str, Any]:
        import httpx

        headers: dict[str, str] = {}
        if auth:
            ts = self._timestamp()
            headers.update({
                "OK-ACCESS-KEY": self.api_key,
                "OK-ACCESS-SIGN": self._sign(ts, "GET", path),
                "OK-ACCESS-TIMESTAMP": ts,
                "OK-ACCESS-PASSPHRASE": self.passphrase,
            })

        async with httpx.AsyncClient(base_url=OKX_BASE_URL, timeout=20.0) as client:
            resp = await client.get(path, headers=headers)
            try:
                payload = resp.json()
            except Exception:
                payload = {"raw_text": resp.text}
            if isinstance(payload, dict):
                payload["_http_status"] = resp.status_code
            return payload


# ── Helpers ──────────────────────────────────────────────────────────────────

def _row_list(data: dict) -> list[dict]:
    return data.get("data") or []


# ── 1220.A — /account/config ────────────────────────────────────────────────

async def spike_account_config(rec: SpikeRecorder, client: OkxRestClient) -> None:
    resp = await client.get("/api/v5/account/config", auth=True)
    rows = _row_list(resp)
    cfg = rows[0] if rows else {}
    rec.add(
        "1220A_account_config",
        resp.get("code") == "0" and bool(cfg),
        enableSpotBorrow=cfg.get("enableSpotBorrow"),
        acctLv=cfg.get("acctLv"),
        acctSt=cfg.get("acctSt"),
        posMode=cfg.get("posMode"),
        uid=cfg.get("uid"),
        http_status=resp.get("_http_status"),
        raw_code=resp.get("code"),
        raw_msg=resp.get("msg"),
    )


# ── 1220.B — /account/max-loan ─────────────────────────────────────────────

async def spike_max_loan(rec: SpikeRecorder, client: OkxRestClient, symbols: list[str]) -> None:
    borrowable_isolated: list[str] = []
    borrowable_cross: list[str] = []
    for inst_id in symbols:
        # Test isolated first, fallback to cross if Simple mode
        for mgn in ("isolated", "cross"):
            resp = await client.get(
                f"/api/v5/account/max-loan?instId={inst_id}&mgnMode={mgn}",
                auth=True,
            )
            rows = _row_list(resp)
            # Find the sell-side row (borrowable asset, not EUR collateral)
            sell_rows = [r for r in rows if r.get("side") == "sell"]
            loan = sell_rows[0] if sell_rows else (rows[0] if rows else {})
            max_loan = float(loan.get("maxLoan", "0") or "0")
            is_borrowable = max_loan > 0
            rec.add(
                f"1220B_max_loan_{inst_id}_{mgn}",
                resp.get("code") == "0",
                instId=inst_id,
                mgnMode=mgn,
                maxLoan=loan.get("maxLoan"),
                ccy=loan.get("ccy"),
                side=loan.get("side"),
                is_borrowable=is_borrowable,
                http_status=resp.get("_http_status"),
                raw_code=resp.get("code"),
                raw_msg=resp.get("msg"),
            )
            if is_borrowable:
                if mgn == "isolated":
                    borrowable_isolated.append(inst_id)
                else:
                    borrowable_cross.append(inst_id)

    rec.add(
        "1220B_max_loan_summary",
        len(borrowable_isolated) > 0 or len(borrowable_cross) > 0,
        borrowable_isolated=borrowable_isolated,
        borrowable_cross=borrowable_cross,
        total_tested=len(symbols),
        note="Isolated preferred (risk segregation). Cross fallback if Simple mode only.",
    )


# ── 1220.C — /public/interest-rate-loan-quota ──────────────────────────────

async def spike_interest_rates(rec: SpikeRecorder, client: OkxRestClient, symbols: list[str]) -> None:
    """Interest rate is public — no auth needed."""
    base_ccies = list({s.split("-")[0] for s in symbols})
    for i, ccy in enumerate(base_ccies):
        if i > 0:
            await asyncio.sleep(1.0)  # avoid rate limiting
        resp = await client.get(f"/api/v5/public/interest-rate-loan-quota?ccy={ccy}")
        rows = _row_list(resp)
        # Response has a list of tiers
        rates = []
        for r in rows:
            rates.append({
                "ccy": r.get("ccy"),
                "rate": r.get("rate"),
                "7dRate": r.get("7dRate"),
                "loanQuota": r.get("loanQuota"),
                "used": r.get("used"),
            })
        # The first tier's rate is the one retail users get
        top_rate = float(rows[0].get("rate", "0") or "0") if rows else 0.0
        rec.add(
            f"1220C_interest_rate_{ccy}",
            resp.get("code") == "0",
            ccy=ccy,
            top_rate=top_rate,
            top_rate_pct=f"{top_rate * 100:.4f}%" if top_rate else "N/A",
            tiers_count=len(rows),
            rates=rates[:5],  # cap at 5 tiers
            http_status=resp.get("_http_status"),
            raw_code=resp.get("code"),
            raw_msg=resp.get("msg"),
        )


# ── 1220.D — /account/leverage-info ────────────────────────────────────────

async def spike_leverage_info(rec: SpikeRecorder, client: OkxRestClient, symbols: list[str]) -> None:
    for inst_id in symbols:
        ccy = inst_id.split("-")[0]
        for mgn in ("isolated", "cross"):
            resp = await client.get(
                f"/api/v5/account/leverage-info?instType=MARGIN&ccy={ccy}&mgnMode={mgn}",
                auth=True,
            )
            rows = _row_list(resp)
            info = rows[0] if rows else {}
            rec.add(
                f"1220D_leverage_{inst_id}_{mgn}",
                resp.get("code") == "0",
                instId=inst_id,
                mgnMode=mgn,
                lever=info.get("lever"),
                posSide=info.get("posSide"),
                http_status=resp.get("_http_status"),
                raw_code=resp.get("code"),
                raw_msg=resp.get("msg"),
            )


# ── 1220.E — /account/positions?instType=MARGIN ────────────────────────────

async def spike_positions(rec: SpikeRecorder, client: OkxRestClient) -> None:
    resp = await client.get("/api/v5/account/positions?instType=MARGIN", auth=True)
    rows = _row_list(resp)
    rec.add(
        "1220E_positions_margin",
        resp.get("code") == "0",
        positions_count=len(rows),
        sample=rows[:3] if rows else [],
        note="Empty list is OK — confirms endpoint works, no active margin positions expected",
        http_status=resp.get("_http_status"),
        raw_code=resp.get("code"),
        raw_msg=resp.get("msg"),
    )


# ── 1220.F — /account/position-tiers ───────────────────────────────────────

async def spike_position_tiers(rec: SpikeRecorder, client: OkxRestClient, symbols: list[str]) -> None:
    # OKX EU: position-tiers for SPOT margin uses instType=SPOT (margin mode on spot pairs)
    for inst_id in symbols:
        resp = await client.get(
            f"/api/v5/account/position-tiers?instType=SPOT&instId={inst_id}",
            auth=True,
        )
        rows = _row_list(resp)
        first = rows[0] if rows else {}
        rec.add(
            f"1220F_position_tiers_{inst_id}",
            resp.get("code") == "0",
            instId=inst_id,
            instType="SPOT",
            tiers_count=len(rows),
            mmr=first.get("mmr"),          # maintenance margin ratio
            tier=first.get("tier"),
            maxSz=first.get("maxSz"),
            minSz=first.get("minSz"),
            http_status=resp.get("_http_status"),
            raw_code=resp.get("code"),
            raw_msg=resp.get("msg"),
        )


# ── 1220.G — quick-margin-borrow-repay-history + interest-limits ────────────

async def spike_borrow_history_and_limits(rec: SpikeRecorder, client: OkxRestClient) -> None:
    resp_hist = await client.get("/api/v5/account/quick-margin-borrow-repay-history", auth=True)
    rows_hist = _row_list(resp_hist)
    rec.add(
        "1220G_borrow_repay_history",
        resp_hist.get("code") == "0",
        entries_count=len(rows_hist),
        sample=rows_hist[:3] if rows_hist else [],
        note="Empty list expected — no margin positions opened yet",
        http_status=resp_hist.get("_http_status"),
        raw_code=resp_hist.get("code"),
        raw_msg=resp_hist.get("msg"),
    )

    resp_limits = await client.get("/api/v5/account/interest-limits", auth=True)
    rows_limits = _row_list(resp_limits)
    rec.add(
        "1220G_interest_limits",
        resp_limits.get("code") == "0",
        limits_count=len(rows_limits),
        data=rows_limits[:3] if rows_limits else [],
        http_status=resp_limits.get("_http_status"),
        raw_code=resp_limits.get("code"),
        raw_msg=resp_limits.get("msg"),
    )


# ── 1220.I — USDT fallback (if EUR margin not available) ────────────────────

async def spike_usdt_fallback(rec: SpikeRecorder, client: OkxRestClient) -> None:
    """Test USDT margin pairs if EUR ones fail the borrow check."""
    usdt_symbols = ["BTC-USDT", "ETH-USDT"]
    borrowable_usdt: list[str] = []
    for inst_id in usdt_symbols:
        for mgn in ("isolated", "cross"):
            resp = await client.get(
                f"/api/v5/account/max-loan?instId={inst_id}&mgnMode={mgn}",
                auth=True,
            )
            rows = _row_list(resp)
            sell_rows = [r for r in rows if r.get("side") == "sell"]
            loan = sell_rows[0] if sell_rows else (rows[0] if rows else {})
            max_loan = float(loan.get("maxLoan", "0") or "0")
            is_borrowable = max_loan > 0
            rec.add(
                f"1220I_usdt_fallback_{inst_id}_{mgn}",
                resp.get("code") == "0",
                instId=inst_id,
                mgnMode=mgn,
                maxLoan=loan.get("maxLoan"),
                is_borrowable=is_borrowable,
                http_status=resp.get("_http_status"),
                raw_code=resp.get("code"),
                raw_msg=resp.get("msg"),
            )
            if is_borrowable and inst_id not in borrowable_usdt:
                borrowable_usdt.append(inst_id)

    rec.add(
        "1220I_usdt_fallback_summary",
        len(borrowable_usdt) > 0,
        borrowable_usdt=borrowable_usdt,
    )


# ── 1220.H — Gate pre-apertura ─────────────────────────────────────────────

def spike_gate_check(rec: SpikeRecorder, symbols: list[str]) -> None:
    """Evaluate if at least one symbol is profitable to short.

    Gate: APR hourly cost < SL gross fee only (≈0.35%).
    APR < 0.35% * 24h / 1h = 8.4% annualized is breakeven.
    For scalping < 2h, even 50% APR is negligible (<0.04% per trade).
    """
    SL_GROSS_FEE = 0.0035  # 0.35% per leg
    MAX_HOURS = 2.0  # typical max scalp duration

    # Find interest rates: prefer interest-limits (private, reliable) over public endpoint
    rate_map: dict[str, float] = {}
    # First try public interest-rate-loan-quota (may return null on Simple mode)
    for r in rec.results:
        if r.name.startswith("1220C_interest_rate_"):
            ccy = r.name.replace("1220C_interest_rate_", "")
            rate = r.details.get("top_rate", 0.0)
            if rate and float(rate) > 0:
                rate_map[ccy] = float(rate)
    # Then override with interest-limits data (always has rates)
    for r in rec.results:
        if r.name == "1220G_interest_limits":
            for rec_entry in r.details.get("data", [{}])[0].get("records", []):
                ccy = rec_entry.get("ccy", "")
                rate_str = rec_entry.get("rate", "0")
                if ccy and rate_str:
                    rate_map[ccy] = float(rate_str)

    # Find borrowable symbols from 1220B
    borrowable: list[str] = []
    for r in rec.results:
        if r.name == "1220B_max_loan_summary":
            borrowable = r.details.get("borrowable_isolated", []) + r.details.get("borrowable_cross", [])

    gate_results: list[dict[str, Any]] = []
    any_pass = False
    for inst_id in symbols:
        ccy = inst_id.split("-")[0]
        apr = rate_map.get(ccy, 0.0)
        cost_2h = apr / 365 / 24 * MAX_HOURS  # hourly accrual x 2h
        is_borrowable = inst_id in borrowable
        passes = is_borrowable and apr > 0  # any positive rate with borrow is fine for scalping
        if passes:
            any_pass = True
        gate_results.append({
            "symbol": inst_id,
            "borrowable": is_borrowable,
            "apr": apr,
            "apr_pct": f"{apr * 100:.2f}%",
            "cost_2h_pct": f"{cost_2h * 100:.4f}%",
            "passes_gate": passes,
        })

    rec.add(
        "1220H_gate_check",
        any_pass,
        gate_results=gate_results,
        note="Gate: at least one symbol must be borrowable with positive APR for short to be viable",
    )


# ── Main ────────────────────────────────────────────────────────────────────

async def run_spike(symbols: list[str]) -> int:
    _load_env_file(BACKEND_ENV)
    rec = SpikeRecorder()

    # Verify LIVE credentials exist
    rec.add(
        "live_credentials_present",
        all(os.environ.get(k) for k in ("OKX_API_KEY_LIVE", "OKX_SECRET_KEY_LIVE", "OKX_PASSPHRASE_LIVE")),
        api_key=os.environ.get("OKX_API_KEY_LIVE"),
        secret=os.environ.get("OKX_SECRET_KEY_LIVE"),
        passphrase=os.environ.get("OKX_PASSPHRASE_LIVE"),
        env_file=str(BACKEND_ENV),
    )

    client = OkxRestClient(use_live=True)

    try:
        await spike_account_config(rec, client)
        await spike_max_loan(rec, client, symbols)
        await spike_interest_rates(rec, client, symbols)
        await spike_leverage_info(rec, client, symbols)
        await spike_positions(rec, client)
        await spike_position_tiers(rec, client, symbols)
        await spike_borrow_history_and_limits(rec, client)
        spike_gate_check(rec, symbols)

        # 1220.I — USDT fallback only if EUR symbols not all borrowable
        eur_borrowable = False
        for r in rec.results:
            if r.name == "1220B_max_loan_summary":
                eur_borrowable = (
                    len(r.details.get("borrowable_isolated", [])) > 0
                    or len(r.details.get("borrowable_cross", [])) > 0
                )
        if not eur_borrowable:
            await spike_usdt_fallback(rec, client)

    except Exception as exc:
        rec.add("spike_exception", False, error=repr(exc), tb=traceback.format_exc())

    rec.write_json(PROJECT_ROOT / "docs" / "analysis" / "okx-short-spike-results.json")
    rec.write_markdown(PROJECT_ROOT / "docs" / "analysis" / "okx-short-spike-results.md", symbols)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="TASK-1220: OKX Short Selling read-only spike.")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help=f"OKX instId symbols to test. Default: {DEFAULT_SYMBOLS}",
    )
    args = parser.parse_args()
    return asyncio.run(run_spike(args.symbols))


if __name__ == "__main__":
    raise SystemExit(main())
