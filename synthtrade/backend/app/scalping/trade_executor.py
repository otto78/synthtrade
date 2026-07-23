import asyncio
import logging
from typing import Any, Dict
from datetime import datetime, timezone
from decimal import Decimal

from app.config import settings
from app.scalping._state import _execution_state
from app.scalping.pricing import _get_fee_rate, _convert_bnb_commission_to_usdc
from app.scalping.reconciliation import _reconcile_position_with_exchange
from app.scalping.db_ops import _save_open_position_to_db, _update_closed_position_in_db
from app.scalping.broadcast import broadcast_scalping_event
from app.scalping.session_lifecycle import _refresh_session_balance

logger = logging.getLogger(__name__)

async def _live_close_position(exchange, pos, qty: float) -> float:
    """Execute live close on exchange: cancel open orders + market sell (with retry).

    TASK-1107: Provider-neutral implementation.
    Uses ExchangeAdapterProtocol methods only — works for OKX and Binance.

    Returns the actual execution price on success.
    Raises Exception if close fails after all retries.

    Scenarios handled:
    1. Bracket already executed → no base balance → use current ticker price
    2. Balance check fails → fallback to original qty parameter
    3. Balance >= min_sz → use actual balance, round to lot_sz, market close
    """
    from app.execution.exchange_models import ClosePositionRequest, SymbolRef

    # Parse symbol to SymbolRef (provider-neutral)
    sym_str = pos.symbol.upper()
    try:
        sym_ref = SymbolRef.from_okx(sym_str) if "-" in sym_str else SymbolRef.from_compact(sym_str)
    except Exception:
        sym_ref = SymbolRef.from_compact(sym_str)

    base_asset = sym_ref.base

    # 1. Cancel any open exit orders (bracket TP/SL) before attempting close
    try:
        await exchange.cancel_open_exit_orders(sym_ref)
        logger.info(f"Cancelled open exit orders for {sym_str}")
    except Exception as order_e:
        logger.warning(f"Could not cancel open exit orders (non-blocking): {order_e}")

    # 2. Get actual available balance to determine if bracket already filled
    try:
        holdings = await exchange.get_holdings()
        actual_qty = holdings.get(base_asset, 0.0)
        rules = await exchange.get_symbol_rules(sym_ref)
        min_qty = rules.min_sz

        if actual_qty < min_qty:
            # ── SCENARIO 1: Bracket already executed ──
            # Exchange already sold (TP or SL filled). Only dust remains.
            # Delegate to shared reconciliation helper for consistent fill price logic.
            logger.info(
                f"Balance {actual_qty} {base_asset} < minSz {min_qty}. "
                f"Position already closed by exchange bracket."
            )
            bracket_id = getattr(pos, 'oco_order_list_id', None)
            reconcile = await _reconcile_position_with_exchange(
                symbol=pos.symbol,
                pos_side=pos.side,
                entry_price=float(pos.entry_price),
                quantity=float(pos.quantity),
                exchange=exchange,
                bracket_id=bracket_id,
            )
            if reconcile is not None:
                return reconcile["fill_price"]
            return float(pos.entry_price)

        # ── SCENARIO 3: Position still open, balance >= min_sz ──
        qty = actual_qty
        logger.info(f"Using actual balance for {sym_str} close: {qty}")

    except Exception as bal_err:
        # ── SCENARIO 2: Balance check failed → use original qty parameter ──
        logger.warning(f"Balance check failed (fallback to original qty {qty}): {bal_err}")

    # 3. Round qty to lot_sz precision
    try:
        rules = await exchange.get_symbol_rules(sym_ref)
        qty = rules.round_qty(qty)
        if qty <= 0:
            logger.warning(f"Rounded qty=0 for {sym_str}, using original")
            qty = float(pos.quantity)
    except Exception as round_e:
        logger.warning(f"Could not get symbol rules for rounding ({round_e}), using raw qty")

    # 4. Execute Market Close — retry up to 3 times with delay
    close_res = None
    for attempt in range(3):
        try:
            close_req = ClosePositionRequest(
                symbol=sym_ref,
                side=pos.side.lower(),  # side of the POSITION (not the close order)
                quantity=qty,
            )
            close_res = await exchange.close_position(close_req)
            break
        except Exception as retry_e:
            logger.warning(f"Market close attempt {attempt + 1}/3 failed for {sym_str}: {retry_e}")
            if attempt < 2:
                await asyncio.sleep(0.5)

    if close_res is None:
        raise RuntimeError(f"Failed to close live position for {sym_str} after 3 attempts")

    close_price = float(close_res.average_price or pos.entry_price)
    logger.info(f"LIVE Market Close executed @ {close_price} [{settings.EXCHANGE_PROVIDER.upper()}]")
    return close_price


from app.scalping.db_ops import _save_open_position_to_db, _update_closed_position_in_db


async def _on_order_update(event: dict):
    """Handler UDS — chiamato su ogni executionReport FILLED/EXPIRED.

    TASK-826: Implementa la logica di chiusura posizione via User Data Stream.
    Sostituisce il polling OCO su ogni candela (rimosso in TASK-824).

    Gestione ordine eventi Binance:
    - Se arriva FILLED → chiudiamo la posizione (TP o SL)
    - Se arriva EXPIRED → log informativo. L'altro leg (FILLED) arriverà dopo.
      Se la posizione è già chiusa (pos=None), usciamo silenziosamente.
    """
    symbol = event.get("symbol")
    order_id = event.get("order_id")
    # provider-neutral: OKX uses bracket_id/order_list_id, Binance uses order_list_id
    order_list_id = event.get("bracket_id") or event.get("order_list_id")
    leg = event.get("leg")  # "take_profit" | "stop_loss" | "market" | "algo" (OKX)
    status = event.get("status")   # "filled" / "expired"
    fill_price = event.get("fill_price", 0.0)

    pos = _execution_state["position_manager"].get_open()
    # ⚠️ Se la posizione è già chiusa o non è il nostro bracket → exit silenzioso
    if not pos:
        return
    if pos.oco_order_list_id and order_list_id != pos.oco_order_list_id:
        logger.debug(f"[TradeExec] ORDER_STREAM: event bracket_id={order_list_id} != pos.bracket_id={pos.oco_order_list_id} — skip")
        return

    if status == "filled":
        # Determina se è TP o SL:
        # 1. Da campo leg (OKX algo-orders lo fornisce direttamente)
        # 2. Da orderId matching (Binance legacy)
        if leg == "take_profit":
            reason = "take_profit"
        elif leg == "stop_loss":
            reason = "stop_loss"
        elif order_id and pos.tp_order_id and order_id == pos.tp_order_id:
            reason = "take_profit"
        elif order_id and pos.sl_order_id and order_id == pos.sl_order_id:
            reason = "stop_loss"
        else:
            reason = "bracket_filled"

        if fill_price <= 0:
            logger.warning(f"[TradeExec] ORDER_STREAM: FILLED event with fill_price=0 for {symbol} orderId={order_id} — skip close")
            return

        # TASK-878: Calcola PnL con commissioni reali
        entry_f = float(pos.entry_price)
        qty_f = float(pos.quantity)
        gross_pnl = (fill_price - entry_f) * qty_f if pos.side == "BUY" else (entry_f - fill_price) * qty_f
        
        # Commissione di uscita reale dal WebSocket (TASK-876 / TASK-1107)
        exit_commission = event.get("commission", 0.0)
        exit_commission_asset = event.get("commission_asset")
        
        # OKX: fee is already in quote currency (EUR) or may be in native token.
        # Binance: fee may be in BNB. Generic conversion: try get_ticker_price if not quote.
        session_symbol = _execution_state["session"].get("symbol", "")
        from app.execution.exchange_models import SymbolRef
        try:
            sym_ref = SymbolRef.from_okx(session_symbol) if "-" in session_symbol else SymbolRef.from_compact(session_symbol)
            quote_asset = sym_ref.quote
        except Exception:
            quote_asset = "EUR"
        
        if exit_commission_asset and exit_commission_asset != quote_asset and exit_commission > 0:
            try:
                exchange = _execution_state.get("exchange")
                if exchange:
                    # Try to convert commission asset to quote via ticker
                    ticker_sym = f"{exit_commission_asset}/{quote_asset}"  # e.g. OKB/EUR or BNB/USDT
                    asset_price = await exchange.get_ticker_price(ticker_sym)
                    converted = exit_commission * asset_price
                    logger.debug(
                        "Converted commission %s %s to %.4f %s @ %.4f",
                        exit_commission, exit_commission_asset, converted, quote_asset, asset_price,
                    )
                    exit_commission = converted
            except Exception as e:
                logger.warning("Failed to convert commission %s %s to %s: %s",
                               exit_commission, exit_commission_asset, quote_asset, e)
        
        # Commissione di entrata: usa fee tier se non disponibile da WebSocket
        # (Nota: l'ordine market di entrata non passa attraverso UDS, quindi non abbiamo
        # la commissione reale di entrata. Usiamo il fee tier come costo atteso.)
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        entry_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # market order = taker
        entry_commission = entry_f * qty_f * entry_fee_rate
        
        # Totale fee = entrata (attesa) + uscita (reale)
        total_fees = entry_commission + exit_commission
        
        pnl = gross_pnl - total_fees
        pnl_pct = (pnl / (entry_f * qty_f)) * 100 if entry_f > 0 else 0.0
        
        logger.debug(f"[TASK-878] PnL calc: gross={gross_pnl:.4f}, entry_fee={entry_commission:.4f}, exit_fee={exit_commission:.4f}, total_fees={total_fees:.4f}, pnl={pnl:.4f}")

        # Chiudi posizione in memoria
        _execution_state["position_manager"].close_position(Decimal(str(fill_price)))

        # Aggiorna trade history
        trade_record = {
            "symbol": pos.symbol,
            "side": pos.side,
            "entry_price": entry_f,
            "exit_price": fill_price,
            "quantity": qty_f,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signal_reason": reason,
        }
        _execution_state["trade_history"].append(trade_record)

        # Aggiorna DB
        await _update_closed_position_in_db(pos, fill_price, pnl, pnl_pct, reason)

        # Refresh live balance
        await _refresh_session_balance()

        # Broadcast UI
        await broadcast_scalping_event("trade_closed", {
            "symbol": pos.symbol,
            "side": pos.side,
            "position_side": "SHORT" if pos.side == "SELL" else "LONG",
            "entry_price": entry_f,
            "exit_price": fill_price,
            "quantity": qty_f,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "signal_reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(f"\033[92m[TradeExec] Trade closed {reason}: {pos.symbol} @ {fill_price} | PnL={pnl:.2f} ({pnl_pct:.2f}%)\033[0m")

    elif status == "expired":
        # ⚠️ Binance NON garantisce l'ordine FILLED/EXPIRED.
        # Se arriva prima EXPIRED, la posizione è ancora aperta — il FILLED arriverà dopo.
        # Se la posizione è già chiusa (pos=None sopra), usciamo silenziosamente.
        logger.info(f"[TradeExec] OCO leg EXPIRED (attesa FILLED dell'altro leg): {symbol} orderId={order_id}")


async def _on_uds_reconnect_sync():
    """Chiamato dopo ogni riconnessione UDS (TASK-830).

    Verifica se l'OCO è stato eseguito durante la finestra di disconnessione.
    Se sì, chiude la posizione in memoria, aggiorna DB e broadcast UI.
    """
    pos = _execution_state["position_manager"].get_open()
    if not pos:
        return  # Nessuna posizione aperta, nulla da sincronizzare

    exchange = _execution_state.get("exchange")
    if not exchange:
        return

    try:
        bracket_id = getattr(pos, 'oco_order_list_id', None)
        reconcile = await _reconcile_position_with_exchange(
            symbol=pos.symbol,
            pos_side=pos.side,
            entry_price=float(pos.entry_price),
            quantity=float(pos.quantity),
            exchange=exchange,
            bracket_id=bracket_id,
        )
        if reconcile is None:
            return  # Position still open on exchange

        fill_price = reconcile["fill_price"]
        reason = reconcile["reason"]
        entry_f = float(pos.entry_price)
        qty_f = float(pos.quantity)

        gross_pnl = (
            (fill_price - entry_f) * qty_f
            if pos.side == "BUY"
            else (entry_f - fill_price) * qty_f
        )
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        entry_fee = _get_fee_rate(fee_tier, "taker", 0.001)
        exit_fee = _get_fee_rate(fee_tier, "taker", 0.001)  # OKX OCO = market (taker)
        total_fees = (entry_f * qty_f * entry_fee) + (fill_price * qty_f * exit_fee)
        pnl = gross_pnl - total_fees
        pnl_pct = (pnl / (entry_f * qty_f)) * 100 if entry_f > 0 else 0.0

        logger.info(
            "[TradeExec] RECONCILE: UDS reconnect: %s closed externally | "
            "fill=%.4f source=%s reason=%s pnl=%.2f",
            pos.symbol, fill_price, reconcile["source"], reason, pnl,
        )

        _execution_state["position_manager"].close_position(Decimal(str(fill_price)))
        await _update_closed_position_in_db(pos, fill_price, pnl, pnl_pct, reason)
        await _refresh_session_balance()
        # FIX: append to trade_history so session counters are accurate
        _execution_state["trade_history"].append({
            "symbol": pos.symbol,
            "side": pos.side,
            "entry_price": entry_f,
            "exit_price": fill_price,
            "quantity": qty_f,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signal_reason": reason,
        })

        await broadcast_scalping_event("position_reconciled_externally", {
            "symbol": pos.symbol,
            "side": pos.side,
            "entry_price": entry_f,
            "exit_price": fill_price,
            "quantity": qty_f,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "source": reconcile["source"],
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as e:
        logger.warning(f"UDS reconnect sync error (non-fatal): {e}")


async def _start_uds_if_needed():
    """Avvia order event stream singleton se non già attivo (TASK-827 / TASK-1107).

    TASK-1107: provider-neutral — uses build_order_stream() factory.
    Per OKX: OkxOrderEventStream (orders + algo-orders WS).
    Per Binance: UserDataStreamManager (legacy).

    Deve essere chiamato dopo bracket confermato.
    Passa sia on_order_update che on_reconnect_sync al manager.
    """
    if _execution_state.get("user_data_stream"):
        return  # Già attivo — singleton check

    session = _execution_state["session"]
    # OKX Demo needs order stream even in test mode (bracket fills come via WS)
    # Binance: only in live mode
    provider = settings.EXCHANGE_PROVIDER.lower()
    if provider == "binance" and session.get("mode") != "live":
        return  # Binance UDS solo in live

    try:
        from app.execution.exchange_factory import build_order_stream
        order_stream = build_order_stream()
        if order_stream is None:
            return  # Paper mode, no stream needed
        await order_stream.start(
            on_order_update=_on_order_update,
            on_reconnect_sync=_on_uds_reconnect_sync,
        )
        _execution_state["user_data_stream"] = order_stream
        logger.info("\033[96m[TradeExec] ORDER STREAM active: avviato post-bracket confermato [%s]\033[0m", provider)
    except Exception as uds_e:
        logger.warning("[TradeExec] ORDER_STREAM: Avvio fallito (non-fatal): %s", uds_e)


async def _handle_bracket_failed(exchange, symbol: str):
    """Gestione Caso B — Exit bracket fallito (TASK-828 / TASK-1107 provider-neutral).

    1. Cancella ordini orfani aperti (provider-neutral: cancel_open_exit_orders).
    2. Market sell con qty reale post-fee da adapter balance.
    3. Broadcast error a UI.
    4. Nessun salvataggio DB (posizione non è mai stata valida).
    """
    # 1. Cancella ordini orfani (provider-neutral)
    try:
        from app.execution.exchange_models import SymbolRef
        sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
        await exchange.cancel_open_exit_orders(sym_ref)
        logger.info(f"[TradeExec] BRACKET_FAILED: Cancelled open exit orders for {symbol}")
    except Exception as e:
        logger.warning(f"[TradeExec] BRACKET_FAILED: cancel_open_exit_orders failed (non-blocking): {e}")

    # 2. Market sell con qty reale post-fee (provider-neutral)
    try:
        # Get holdings directly from adapter (works for OKX and Binance)
        holdings = await exchange.get_holdings()
        from app.execution.exchange_models import SymbolRef
        sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
        base_asset = sym_ref.base
        actual_qty = holdings.get(base_asset, 0.0)
        
        if actual_qty > 0:
            sym_rules = await exchange.get_symbol_rules(sym_ref)
            min_qty = sym_rules.min_sz
            if actual_qty >= min_qty:
                from app.execution.exchange_models import ClosePositionRequest
                close_req = ClosePositionRequest(
                    symbol=sym_ref,
                    side="buy",  # side is position side, close is opposite
                    quantity=actual_qty,
                )
                await exchange.close_position(close_req)
                logger.info(f"[TradeExec] BRACKET_FAILED: Emergency market sell executed: {actual_qty} {base_asset}")
            else:
                logger.warning(f"[TradeExec] BRACKET_FAILED: qty={actual_qty} < minQty={min_qty} for {symbol} — impossible to sell")
        else:
            logger.error(f"[TradeExec] BRACKET_FAILED: Balance={actual_qty} for {base_asset} — no asset to sell")
    except Exception as e:
        logger.error(f"[TradeExec] BRACKET_FAILED: Emergency market sell failed for {symbol}: {e}")

    # 3. Broadcast error a UI
    await broadcast_scalping_event("error", {
        "code": "BRACKET_FAILED",
        "message": f"Exit bracket failed for {symbol}. Trade closed with emergency market sell, no assets locked.",
    })


async def _close_position_and_record(pm, close_price: float, pos, reason: str = "signal"):
    """Helper to close position, deduct fees, calculate PnL and record trade."""
    qty = float(pos.quantity)
    mode = _execution_state["session"].get("mode", "paper")
    exchange = _execution_state.get("exchange")

    # --- LIVE EXECUTION OVERRIDE ---
    if mode == "live" and exchange:
        close_price = await _live_close_position(exchange, pos, qty)
    # -------------------------------

    entry_val = float(pos.entry_price) * qty
    exit_val = close_price * qty
    gross_pnl = (close_price - float(pos.entry_price)) * qty * (1 if pos.side == "BUY" else -1)
    
    # TASK-880: Usa commissioni reali/attese invece di hardcode
    # Entry: commissione reale se disponibile da WebSocket (TASK-876), altrimenti fee tier
    if pos.entry_commission is not None and pos.entry_commission > 0:
        entry_commission = float(pos.entry_commission)
        # Converti BNB to USDC se necessario
        if pos.entry_commission_asset == "BNB" and exchange:
            entry_commission = await _convert_bnb_commission_to_usdc(
                exchange, entry_commission, context="Close position: "
            )
    else:
        # Fallback: usa fee tier per entrata (costo atteso)
        fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
        entry_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # market order = taker
        entry_commission = entry_val * entry_fee_rate
    
    # Exit: usa fee tier (costo atteso, dato che non abbiamo la commissione reale di uscita in questo scenario)
    fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
    exit_fee_rate = _get_fee_rate(fee_tier, "taker", 0.001)  # market order per chiusura manuale = taker
    exit_commission = exit_val * exit_fee_rate
    
    total_fees = entry_commission + exit_commission
    pnl = gross_pnl - total_fees
    pnl_pct = (pnl / entry_val) * 100
    
    logger.debug(f"[TASK-880] Close position PnL: gross={gross_pnl:.4f}, entry_fee={entry_commission:.4f}, exit_fee={exit_commission:.4f}, total_fees={total_fees:.4f}, pnl={pnl:.4f}")
    pm.close_position(Decimal(str(close_price)))
    now_ts = datetime.now(timezone.utc)
    trade_record = {
        "symbol": pos.symbol,
        "side": pos.side,
        "position_side": "SHORT" if pos.side == "SELL" else "LONG",
        "entry_price": float(pos.entry_price),
        "exit_price": close_price,
        "quantity": qty,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "timestamp": now_ts.isoformat(),
        "signal_reason": reason,
    }
    _execution_state["trade_history"].append(trade_record)

    # Refresh live balance after trade close
    await _refresh_session_balance()
    
    if mode == "paper":
        _execution_state["session"]["paper_balance"] += (entry_val + pnl)
        await broadcast_scalping_event("session_restored", _execution_state["session"].copy())

    # Update DB: change status from 'open' to 'closed' with exit data
    await _update_closed_position_in_db(pos, close_price, pnl, pnl_pct, reason)

    await broadcast_scalping_event("trade_closed", trade_record)
    logger.info(f"Position closed ({reason}): {pos.side} {pos.symbol} PnL: {pnl:.2f} ({pnl_pct:.2f}%)")

def _check_daily_loss() -> bool:
    """Return True if max daily loss is exceeded."""
    risk_cfg = _execution_state.get("risk_config", {})
    max_loss = float(risk_cfg.get("max_daily_loss", 50.0))
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total_pnl = sum(t.get("pnl") or 0.0 for t in _execution_state["trade_history"] if t["timestamp"].startswith(now_str))
    return total_pnl <= -max_loss


def _check_drawdown() -> bool:
    """Return True if max drawdown from peak equity is exceeded."""
    risk_cfg = _execution_state.get("risk_config", {})
    max_dd_pct = float(risk_cfg.get("max_drawdown", 10.0))
    trades = [t for t in _execution_state["trade_history"] if t.get("exit_price") is not None]
    if not trades:
        return False
    base = float(_execution_state["session"].get("paper_balance") or
                 _execution_state["session"].get("live_balance") or 10000.0)
    equity = base
    peak = base
    for t in trades:
        equity += (t.get("pnl") or 0.0)
        if equity > peak:
            peak = equity
    if peak <= 0:
        return False
    dd_pct = (peak - equity) / peak * 100
    return dd_pct >= max_dd_pct
