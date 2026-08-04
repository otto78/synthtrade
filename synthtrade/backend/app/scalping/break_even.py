"""TASK-1243: Break-even profit lock logic.

Logica di trigger e amend OCO per il profit lock dopo break-even.

Regole invarianti:
- Identità ordine = algoId (pos.oco_order_list_id). Mai match per simbolo/lato.
- Transizione break_even_triggered è MONOTONA: false -> true, mai il contrario.
- L'amend viene confermato SOLO con HTTP success + code=="0" + sCode=="0".
- Stato in memoria e DB vengono aggiornati SOLO dopo conferma OKX.
- Solo su candela chiusa (v1), non su spike intra-candle.
- Solo per posizioni OPEN live con oco_order_list_id valorizzato.
- Il nuovo SL deve essere strettamente > SL attuale per un long (mai allentare uno stop).
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_UP

from app.scalping._state import _execution_state
from app.scalping.pricing import _expected_net_pct_at_exit, _exit_price_ratio, _get_fee_rate
from app.scalping.db_ops import _update_break_even_in_db
from app.scalping.broadcast import broadcast_scalping_event
from app.scalping.config_loader import get_scalping_config
from app.scalping.engine.position_manager import PositionStatus
from app.execution.exchange_models import SymbolRef
from app.execution.exchange import ExchangeOrderError

logger = logging.getLogger(__name__)

# Lock per-algoId: impedisce doppio amend in caso di candele rapide
_break_even_locks: dict[str, asyncio.Lock] = {}


def _get_lock_for_algo(algo_id: str) -> asyncio.Lock:
    if algo_id not in _break_even_locks:
        _break_even_locks[algo_id] = asyncio.Lock()
    return _break_even_locks[algo_id]


def _quantize_price(price: float, tick_sz: float, side: str) -> float:
    """Quantizza il prezzo al tick_sz usando Decimal per evitare errori floating-point.

    Per un long, il nuovo SL deve essere il tick più basso che rimane sopra lo SL attuale:
    arrotondiamo al ribasso (ROUND_DOWN) per garantire che il trigger sia valido su OKX.
    """
    if tick_sz <= 0:
        return price
    d_price = Decimal(str(price))
    d_tick = Decimal(str(tick_sz))
    # ROUND_DOWN per long (vogliamo il tick più basso reale)
    quantized = (d_price / d_tick).quantize(Decimal("1"), rounding=ROUND_DOWN) * d_tick
    return float(quantized)


async def _check_and_apply_break_even(
    pos,
    current_price: float,
    session: dict,
) -> None:
    """Valuta se applicare il break-even profit lock alla posizione corrente.

    Chiamare su ogni candela chiusa dal candle_processor.
    Ritorna immediatamente (no-op) se qualsiasi guard fallisce.

    Args:
        pos: oggetto Position corrente (da position_manager.get_open())
        current_price: prezzo di chiusura candela corrente
        session: dict della sessione (_execution_state["session"])
    """
    # ── Guard 1: solo OPEN live con algoId ──────────────────────────────────
    if pos.status != PositionStatus.OPEN:
        return
    if session.get("mode", "paper") != "live":
        return
    algo_id = pos.oco_order_list_id
    if not algo_id:
        return

    # ── Guard 2: non già attivato ────────────────────────────────────────────
    if pos.break_even_triggered:
        return

    # ── Guard 3: feature flag ────────────────────────────────────────────────
    cfg = get_scalping_config()
    be_enabled = cfg.get("BREAK_EVEN_ENABLED", False)
    if not be_enabled:
        return

    trigger_net_pct = float(cfg.get("BREAK_EVEN_TRIGGER_NET_PCT", 0.15))
    lock_net_pct = float(cfg.get("BREAK_EVEN_LOCK_NET_PCT", 0.05))

    # ── Calcola rendimento netto corrente ────────────────────────────────────
    entry_f = float(pos.entry_price)
    if entry_f <= 0 or current_price <= 0:
        return

    fee_tier = _execution_state.get("fee_tier", {"maker": 0.001, "taker": 0.001})
    ef = _get_fee_rate(fee_tier, "taker", 0.001)
    xf = _get_fee_rate(fee_tier, "taker", 0.001)  # OKX OCO = market (taker)

    net_pct = _expected_net_pct_at_exit(entry_f, current_price, pos.side, ef, xf)

    if net_pct < trigger_net_pct:
        logger.debug(
            "[BE] net_pct=%.4f%% < trigger=%.4f%% — nessun amend per %s",
            net_pct, trigger_net_pct, algo_id,
        )
        return

    # ── Calcola nuovo SL ─────────────────────────────────────────────────────
    # Prezzo che corrisponde a lock_net_pct% netto (sopra entry per long)
    ratio = _exit_price_ratio(lock_net_pct, ef, xf)
    new_sl_raw = entry_f * ratio if pos.side.upper() == "BUY" else entry_f / ratio

    # Ottieni tick_sz per quantizzazione
    exchange = _execution_state.get("exchange")
    if not exchange:
        logger.warning("[BE] Exchange non disponibile, impossibile applicare break-even per %s", algo_id)
        return

    symbol_str = pos.symbol
    try:
        sym_ref = SymbolRef.from_okx(symbol_str) if "-" in symbol_str else SymbolRef.from_compact(symbol_str)
        rules = await exchange.get_symbol_rules(sym_ref)
        tick_sz = rules.tick_sz
    except Exception as e:
        logger.warning("[BE] Impossibile ottenere symbol rules per %s: %s — uso tick_sz=0.01", symbol_str, e)
        tick_sz = 0.01
        sym_ref = SymbolRef.from_okx(symbol_str) if "-" in symbol_str else SymbolRef.from_compact(symbol_str)

    new_sl_price = _quantize_price(new_sl_raw, tick_sz, pos.side)

    # Guard: nuovo SL deve essere strettamente > SL attuale per un long
    current_sl = float(pos.sl_price) if pos.sl_price else 0.0
    if pos.side.upper() == "BUY":
        if new_sl_price <= current_sl and current_sl > 0:
            logger.warning(
                "[BE] Nuovo SL %.4f <= SL attuale %.4f per algoId=%s — amend non inviato (non si allenta uno stop)",
                new_sl_price, current_sl, algo_id,
            )
            return
        if new_sl_price >= current_price:
            logger.warning(
                "[BE] Nuovo SL %.4f >= prezzo corrente %.4f per algoId=%s — amend non sicuro, skip",
                new_sl_price, current_price, algo_id,
            )
            return
    else:  # SELL / short (simmetrico)
        if new_sl_price >= current_sl and current_sl > 0:
            logger.warning(
                "[BE] Nuovo SL (short) %.4f >= SL attuale %.4f per algoId=%s — amend non inviato",
                new_sl_price, current_sl, algo_id,
            )
            return

    # ── Acquisisce lock per-algoId ───────────────────────────────────────────
    lock = _get_lock_for_algo(algo_id)
    if lock.locked():
        logger.debug("[BE] Lock già acquisito per algoId=%s, skip candela corrente", algo_id)
        return

    async with lock:
        # Ri-check dentro il lock (idempotenza)
        if pos.break_even_triggered:
            return

        req_id = uuid.uuid4().hex[:32]
        logger.info(
            "[BE] TRIGGER: algoId=%s entry=%.4f current=%.4f net_pct=%.4f%% "
            "trigger=%.4f%% newSL=%.4f (lock_net=%.4f%%) reqId=%s",
            algo_id, entry_f, current_price, net_pct,
            trigger_net_pct, new_sl_price, lock_net_pct, req_id,
        )

        # ── Chiama OKX amend ──────────────────────────────────────────────────
        try:
            await exchange.amend_exit_bracket_stop_loss(
                symbol=sym_ref,
                algo_id=algo_id,
                new_sl_trigger_px=new_sl_price,
                req_id=req_id,
            )
        except (ExchangeOrderError, NotImplementedError) as e:
            logger.error(
                "[BE] amend_algos FALLITO per algoId=%s: %s — stato locale invariato, "
                "OCO originale ancora attivo.",
                algo_id, e,
            )
            return
        except Exception as e:
            logger.error("[BE] Errore inatteso nell'amend per algoId=%s: %s", algo_id, e)
            return

        # ── Solo dopo conferma OKX: aggiorna memoria ─────────────────────────
        activated_at = datetime.now(timezone.utc)
        old_sl = current_sl

        pos.break_even_triggered = True
        pos.break_even_activated_at = activated_at
        pos.break_even_sl_price = Decimal(str(new_sl_price))
        pos.sl_price = Decimal(str(new_sl_price))

        logger.info(
            "[BE] SUCCESS: algoId=%s oldSL=%.4f newSL=%.4f reqId=%s",
            algo_id, old_sl, new_sl_price, req_id,
        )

        # ── Persisti su DB (best-effort — stop OKX già protetto) ─────────────
        try:
            await _update_break_even_in_db(
                exchange_bracket_id=algo_id,
                new_sl_price=new_sl_price,
                activated_at=activated_at,
            )
        except Exception as db_e:
            logger.error(
                "[BE] DB persist fallito per algoId=%s: %s — SL su OKX è aggiornato, retry al prossimo reconcile",
                algo_id, db_e,
            )

        # ── Broadcast evento WS ───────────────────────────────────────────────
        try:
            await broadcast_scalping_event("trailing_stop_activated", {
                "algo_id": algo_id,
                "symbol": pos.symbol,
                "side": pos.side,
                "entry_price": entry_f,
                "current_price": current_price,
                "old_sl_price": round(old_sl, 4),
                "new_sl_price": round(new_sl_price, 4),
                "trigger_net_pct": round(trigger_net_pct, 4),
                "lock_net_pct": round(lock_net_pct, 4),
                "net_pct_at_trigger": round(net_pct, 4),
                "req_id": req_id,
                "activated_at": activated_at.isoformat(),
            })
        except Exception as ws_e:
            logger.warning("[BE] Broadcast WS fallito: %s", ws_e)
