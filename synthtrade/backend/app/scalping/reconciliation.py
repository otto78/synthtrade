import asyncio
import logging
from typing import Dict, Any, Optional
from app.scalping._state import _execution_state
from app.execution.exchange_models import SymbolRef

logger = logging.getLogger(__name__)


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

    Source priority: algo_history > ticker > entry_price_fallback.
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
                    algo_history = await _exchange.get_algo_orders_history(symbol)
                    for algo in algo_history:
                        if algo.get("algoId") == bracket_id and algo.get("state") == "effective":
                            fill_price = float(algo.get("avgPx") or algo.get("fillPx") or 0)
                            if fill_price > 0:
                                source = "algo_history"
                                ord_type = algo.get("ordType", "").lower()
                                if "tp" in ord_type:
                                    reason = "take_profit"
                                elif "sl" in ord_type:
                                    reason = "stop_loss"
                                else:
                                    reason = "bracket_filled"
                                logger.info(
                                    "[POSITION_RECONCILE] Balance check failed but recovered fill from algo history: "
                                    "algoId=%s fill=%.4f reason=%s (attempt %d)",
                                    bracket_id, fill_price, reason, attempt + 1,
                                )
                                return {"fill_price": fill_price, "source": source, "reason": reason}
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

    fill_price: Optional[float] = None
    source = "entry_price_fallback"
    reason = "external_close_unknown_price"

    # Priority 1: real fills from OKX (most accurate)
    # Always fetch fills — match by bracket_id first, then by exit side
    exit_side = "sell" if pos_side == "BUY" else "buy"
    try:
        fills = await _exchange.get_algo_orders_history(symbol)

        # Priority 1a: match by bracket_id if available
        if bracket_id:
            for fill in fills:
                if fill.get("algoId") == bracket_id and fill.get("state") == "effective":
                    fp = float(fill.get("avgPx") or fill.get("fillPx") or 0)
                    if fp > 0:
                        fill_price = fp
                        source = "fills"
                        ord_type = fill.get("ordType", "").lower()
                        if "tp" in ord_type:
                            reason = "take_profit"
                        elif "sl" in ord_type:
                            reason = "stop_loss"
                        else:
                            reason = "bracket_filled"
                        logger.info(
                            "[POSITION_RECONCILE] Recovered fill by bracket_id: "
                            "algoId=%s fill=%.4f reason=%s",
                            bracket_id, fill_price, reason,
                        )
                        break

        # Priority 1b: match by exit side (most recent fill for the closing side)
        if fill_price is None or fill_price <= 0:
            for fill in fills:
                if fill.get("side", "").lower() == exit_side:
                    fp = float(fill.get("avgPx") or fill.get("fillPx") or 0)
                    if fp > 0:
                        fill_price = fp
                        source = "fills"
                        ord_type = fill.get("ordType", "").lower()
                        if "tp" in ord_type:
                            reason = "take_profit"
                        elif "sl" in ord_type:
                            reason = "stop_loss"
                        else:
                            reason = "external_close"
                        logger.info(
                            "[POSITION_RECONCILE] Recovered fill by exit side (%s): "
                            "fill=%.4f reason=%s",
                            exit_side, fill_price, reason,
                        )
                        break
    except Exception as hist_e:
        logger.warning("[POSITION_RECONCILE] Fills fetch failed: %s", hist_e)

    # Priority 2: entry price fallback (PnL unreliable)
    if fill_price is None or fill_price <= 0:
        fill_price = entry_price
        source = "entry_price_fallback"
        reason = "external_close_unknown_price"
        logger.warning(
            "[POSITION_RECONCILE] No fill price recovered — using entry_price=%.4f as fallback. "
            "PnL will be inaccurate!",
            entry_price,
        )

    logger.info(
        "[POSITION_RECONCILE] %s %s closed externally | fill=%.4f source=%s reason=%s",
        pos_side, symbol, fill_price, source, reason,
    )

    return {"fill_price": fill_price, "source": source, "reason": reason}
