import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.scalping._state import _execution_state
from app.execution.exchange_models import SymbolRef

logger = logging.getLogger(__name__)


def _fill_time_from_ms(fill_time_ms) -> Optional[str]:
    """Convert OKX fillTime (ms string/int) to ISO 8601 UTC string."""
    if not fill_time_ms:
        return None
    try:
        ts = int(fill_time_ms)
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        return None


async def _get_verified_bracket_fills(exchange, symbol: str, bracket_id: str) -> list[dict[str, Any]]:
    """Fetch only fills causally linked to ``bracket_id``.

    ``get_algo_orders_history`` gained the optional id argument with the OKX
    adapter.  The TypeError fallback keeps old third-party/test adapters working,
    while the caller still performs an exact ``algoId`` match below.
    """
    try:
        return await exchange.get_algo_orders_history(symbol, bracket_id=bracket_id)
    except TypeError:
        return await exchange.get_algo_orders_history(symbol)


def _matched_bracket_fill(fills: list[dict[str, Any]], bracket_id: str) -> Optional[Dict[str, Any]]:
    """Return a usable fill only when its parent OCO id is exactly matched."""
    for fill in fills:
        if str(fill.get("algoId")) != str(bracket_id) or fill.get("state") != "effective":
            continue
        try:
            fill_price = float(fill.get("avgPx") or fill.get("fillPx") or 0)
        except (TypeError, ValueError):
            continue
        if fill_price <= 0:
            continue
        order_type = (fill.get("ordType") or "").lower()
        reason = "take_profit" if "tp" in order_type else "stop_loss" if "sl" in order_type else "bracket_filled"
        return {
            "fill_price": fill_price,
            "source": "oco_verified_fill",
            "reason": reason,
            "fill_time": _fill_time_from_ms(fill.get("fillTime") or fill.get("ts")),
            "exit_order_id": fill.get("ordId"),
        }
    return None


async def _reconcile_position_with_exchange(
    symbol: str,
    pos_side: str,
    entry_price: float,
    quantity: float,
    *,
    exchange=None,
    bracket_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Verify on the exchange whether a position is still open.

    Returns None if the position is still alive (no action needed).
    Returns a dict with fill_price, source, reason if the position was
    closed externally (TP/SL hit while bot was offline).

    A persisted bracket_id is an identity boundary: only a fill linked to that
    exact OCO may close the local trade.  If it cannot be verified yet, return
    None and retain the trade open locally rather than corrupting its history.
    """
    _exchange = exchange or _execution_state.get("exchange")
    if not _exchange:
        logger.warning("[POSITION_RECONCILE] No exchange adapter available, skipping check")
        return None

    try:
        sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
    except Exception:
        sym_ref = SymbolRef.from_compact(symbol)

    try:
        rules = await _exchange.get_symbol_rules(sym_ref)
        min_qty = float(rules.min_sz)
        base_asset = sym_ref.base

        # Use get_holdings (more reliable during reconnection) to check if position still exists
        try:
            holdings = await _exchange.get_holdings()
            total_bal = holdings.get(base_asset, 0.0)
            logger.debug("[POSITION_RECONCILE] Holdings check: %s = %.6f (minQty=%.6f)", base_asset, total_bal, min_qty)
        except Exception as holdings_e:
            logger.warning("[POSITION_RECONCILE] Holdings check failed, falling back to get_balance: %s", holdings_e)
            try:
                total_bal = await _exchange.get_balance(base_asset)
            except Exception:
                total_bal = None

        if total_bal is not None and total_bal >= min_qty:
            logger.info(
                "[POSITION_RECONCILE] %s %s still open on exchange (balance=%.6f >= minQty=%.6f)",
                pos_side, symbol, total_bal, min_qty,
            )
            return None

        logger.info(
            "[POSITION_RECONCILE] %s %s balance=%.6f < minQty=%.6f — position closed externally",
            pos_side, symbol, total_bal or 0, min_qty,
        )
    except Exception as bal_e:
        logger.warning("[POSITION_RECONCILE] Balance check failed: %s", bal_e)
        # FALLBACK: Try algo history with retry when balance check fails
        # This handles the case where network was down during startup but bracket executed.
        # TASK-1175: Always retry 3 times — OKX can take 1-5s to propagate fills.
        if bracket_id:
            for attempt in range(3):
                try:
                    match = _matched_bracket_fill(
                        await _get_verified_bracket_fills(_exchange, symbol, bracket_id), bracket_id
                    )
                    if match:
                        logger.info(
                            "[POSITION_RECONCILE] Balance check failed but recovered verified OCO fill: "
                            "algoId=%s fill=%.4f reason=%s (attempt %d)",
                            bracket_id, match["fill_price"], match["reason"], attempt + 1,
                        )
                        return match
                    # No match in this attempt — retry if attempts remain
                    if attempt < 2:
                        await asyncio.sleep(1.5)
                        continue
                    logger.warning(
                        "[POSITION_RECONCILE] Algo history: no fill found for bracket_id=%s after 3 attempts",
                        bracket_id,
                    )
                except Exception as hist_e:
                    if attempt < 2:
                        await asyncio.sleep(1.0)
                        continue
                    logger.warning("[POSITION_RECONCILE] Algo history fallback failed after 3 attempts: %s", hist_e)
        return None

    # Never infer an exit from the instrument's generic order stream.  In a
    # multi-session setup this is actively unsafe, and it is already ambiguous
    # when the account has manual trades on the same pair.
    if not bracket_id:
        logger.error(
            "[POSITION_RECONCILE] %s appears closed but has no persisted OCO algoId; "
            "retaining local trade rather than associating an unrelated fill",
            symbol,
        )
        return None

    try:
        match = _matched_bracket_fill(
            await _get_verified_bracket_fills(_exchange, symbol, bracket_id), bracket_id
        )
        if match:
            logger.info(
                "[POSITION_RECONCILE] Recovered verified OCO fill: algoId=%s fill=%.4f reason=%s",
                bracket_id, match["fill_price"], match["reason"],
            )
            return match
        logger.warning(
            "[POSITION_RECONCILE] Balance indicates %s is closed, but no verified fill exists for OCO algoId=%s; retaining local trade for retry",
            symbol, bracket_id,
        )
    except Exception as hist_e:
        logger.warning("[POSITION_RECONCILE] Verified OCO fill lookup failed: %s", hist_e)
    return None
