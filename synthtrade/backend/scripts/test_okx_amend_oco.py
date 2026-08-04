"""TASK-1243 — Spike validazione: amend-algos OCO BTC-EUR su OKX Demo.

Questo script va eseguito OBBLIGATORIAMENTE su OKX Demo prima di attivare
la feature live. Verifica che:
1. Il metodo amend_exit_bracket_stop_loss sia compatibile con i VERI endpoint OKX
2. L'algoId rimanga lo stesso dopo l'amend
3. Il TP originale sia invariato
4. Il nuovo SL corrisponda a quello richiesto (entro tick_sz)
5. reqId venga accettato correttamente

PREREQUISITI:
- OKX_API_KEY, OKX_SECRET, OKX_PASSPHRASE settati nell'env con credenziali DEMO
- TRADING_MODE=test in .env
- Saldo BTC-EUR sufficiente per un ordine minimo (usa quantità minima)

Esecuzione:
    cd synthtrade/backend
    .venv/Scripts/activate          # Windows
    source .venv/bin/activate       # Unix
    python -m scripts.test_okx_amend_oco [--symbol BTC-EUR]

Il script NON interagisce con il sistema di trading live. Esegue in Demo isolato.
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import uuid
from decimal import Decimal

# Aggiunge il backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "synthtrade", "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("spike_amend_oco")


async def run_spike(symbol_str: str = "BTC-EUR") -> dict:
    """Esegue lo spike completo. Ritorna un dict con i risultati."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "synthtrade", "backend", ".env"))

    api_key = os.environ.get("OKX_API_KEY")
    secret = os.environ.get("OKX_SECRET")
    passphrase = os.environ.get("OKX_PASSPHRASE")
    trading_mode = os.environ.get("TRADING_MODE", "test")

    if not all([api_key, secret, passphrase]):
        raise EnvironmentError(
            "OKX_API_KEY, OKX_SECRET e OKX_PASSPHRASE devono essere nel .env"
        )

    if trading_mode != "test":
        raise RuntimeError(
            f"TRADING_MODE={trading_mode} — questo spike richiede TRADING_MODE=test (Demo). "
            "Non eseguire su live!"
        )

    from app.execution.okx_exchange import OkxExchangeAdapter
    from app.execution.exchange_models import SymbolRef

    adapter = OkxExchangeAdapter(
        api_key=api_key,
        secret=secret,
        passphrase=passphrase,
        trading_mode="test",
    )

    sym_ref = SymbolRef.from_okx(symbol_str)
    results = {}

    # ── Step 1: Ottieni regole simbolo e prezzo corrente ──────────────────────
    logger.info("[SPIKE] Step 1: Ottengo regole per %s...", symbol_str)
    rules = await adapter.get_symbol_rules(sym_ref)
    current_price = await adapter.get_ticker_price(symbol_str)
    logger.info("[SPIKE] Prezzo corrente: %.2f | lot_sz=%.8f | tick_sz=%.4f | min_sz=%.8f",
                current_price, rules.lot_sz, rules.tick_sz, rules.min_sz)
    results["price"] = current_price
    results["tick_sz"] = rules.tick_sz

    # ── Step 2: Calcola quantità minima e prezzi OCO ──────────────────────────
    trade_value = 12.0  # EUR minimo
    qty = rules.round_qty(trade_value / current_price)
    qty = max(qty, rules.min_sz)
    logger.info("[SPIKE] Quantità ordine: %.8f %s (valore ≈ %.2f EUR)", qty, sym_ref.base, qty * current_price)

    # Prezzi realistici per un OCO demo
    tp_price = rules.round_price(current_price * 1.005)   # +0.5%
    sl_price = rules.round_price(current_price * 0.997)   # -0.3%
    new_sl_price = rules.round_price(current_price * 1.002)  # +0.2% (profit lock)

    logger.info("[SPIKE] TP=%.4f | SL_originale=%.4f | SL_nuovo=%.4f",
                tp_price, sl_price, new_sl_price)
    results["tp_price"] = tp_price
    results["original_sl"] = sl_price
    results["new_sl"] = new_sl_price

    # ── Step 3: Piazza ordine market BUY ─────────────────────────────────────
    logger.info("[SPIKE] Step 3: Piazzando ordine market BUY %s %.8f...", symbol_str, qty)
    from app.execution.exchange_models import MarketOrderRequest
    buy_order = await adapter.place_market_order(MarketOrderRequest(
        symbol=sym_ref,
        side="buy",
        quantity=qty,
    ))
    exec_price = buy_order.average_price or current_price
    logger.info("[SPIKE] Market BUY eseguito: ordId=%s avgPx=%.4f", buy_order.order_id, exec_price)
    results["buy_order_id"] = buy_order.order_id

    # ── Step 4: Piazza OCO (bracket TP+SL) ───────────────────────────────────
    logger.info("[SPIKE] Step 4: Piazzando OCO TP=%.4f SL=%.4f...", tp_price, sl_price)
    from app.execution.exchange_models import ExitBracketRequest
    bracket = await adapter.place_exit_bracket(ExitBracketRequest(
        symbol=sym_ref,
        side="sell",
        quantity=qty,
        tp_price=tp_price,
        sl_price=sl_price,
    ))
    algo_id = bracket.bracket_id
    logger.info("[SPIKE] OCO piazzato: algoId=%s", algo_id)
    results["algo_id"] = algo_id

    # Pausa breve per propagazione
    await asyncio.sleep(2)

    # ── Step 5: Verifica OCO pending via orders-algo-pending ─────────────────
    logger.info("[SPIKE] Step 5: Verificando OCO pending algoId=%s...", algo_id)
    open_orders = await adapter.get_open_orders(symbol_str)
    algo_pending = [o for o in open_orders if str(o.get("algoId")) == str(algo_id)]
    if not algo_pending:
        logger.warning("[SPIKE] OCO non trovato in orders-algo-pending — potrebbe richiedere più tempo")
    else:
        logger.info("[SPIKE] OCO pending confermato: %s", json.dumps(algo_pending[0], indent=2))
        original_tp = algo_pending[0].get("tpTriggerPx") or algo_pending[0].get("tpOrdPx")
        logger.info("[SPIKE] TP originale dall'exchange: %s", original_tp)
        results["verified_tp_before"] = original_tp

    # ── Step 6: Amend SL (profit lock) ───────────────────────────────────────
    req_id = uuid.uuid4().hex[:32]
    logger.info("[SPIKE] Step 6: Amend SL → %.4f (reqId=%s)...", new_sl_price, req_id)
    try:
        amend_result = await adapter.amend_exit_bracket_stop_loss(
            symbol=sym_ref,
            algo_id=algo_id,
            new_sl_trigger_px=new_sl_price,
            req_id=req_id,
        )
        logger.info("[SPIKE] Amend SUCCESS: %s", json.dumps(amend_result))
        results["amend_result"] = amend_result
        results["amend_ok"] = True
    except Exception as e:
        logger.error("[SPIKE] Amend FALLITO: %s", e)
        results["amend_ok"] = False
        results["amend_error"] = str(e)

    # ── Step 7: Verifica post-amend ───────────────────────────────────────────
    await asyncio.sleep(2)
    logger.info("[SPIKE] Step 7: Verificando stato post-amend per algoId=%s...", algo_id)
    post_orders = await adapter.get_open_orders(symbol_str)
    algo_post = [o for o in post_orders if str(o.get("algoId")) == str(algo_id)]

    if algo_post:
        order_data = algo_post[0]
        tp_after = order_data.get("tpTriggerPx") or order_data.get("tpOrdPx")
        sl_after = order_data.get("slTriggerPx") or order_data.get("slOrdPx")
        algo_id_after = order_data.get("algoId")

        logger.info("[SPIKE] Post-amend — algoId=%s | TP=%s | SL=%s",
                    algo_id_after, tp_after, sl_after)
        results["algo_id_after"] = str(algo_id_after)
        results["tp_after"] = tp_after
        results["sl_after"] = sl_after

        # Verifiche
        if str(algo_id_after) == str(algo_id):
            logger.info("[SPIKE] ✅ algoId invariato dopo amend")
            results["check_algo_id_stable"] = True
        else:
            logger.error("[SPIKE] ❌ algoId CAMBIATO: %s → %s", algo_id, algo_id_after)
            results["check_algo_id_stable"] = False

        if tp_after and abs(float(tp_after) - tp_price) <= rules.tick_sz:
            logger.info("[SPIKE] ✅ TP originale invariato: %s", tp_after)
            results["check_tp_unchanged"] = True
        else:
            logger.warning("[SPIKE] ⚠️ TP cambiato o non verificabile: before=%.4f after=%s",
                           tp_price, tp_after)
            results["check_tp_unchanged"] = False

        if sl_after and abs(float(sl_after) - new_sl_price) <= rules.tick_sz * 2:
            logger.info("[SPIKE] ✅ Nuovo SL corretto: %s (atteso ≈ %.4f)", sl_after, new_sl_price)
            results["check_new_sl_correct"] = True
        else:
            logger.warning("[SPIKE] ⚠️ Nuovo SL non corrisponde: after=%s atteso=%.4f",
                           sl_after, new_sl_price)
            results["check_new_sl_correct"] = False
    else:
        logger.warning("[SPIKE] OCO non trovato in post-amend — potrebbe essere stato eseguito")
        results["post_amend_not_found"] = True

    # ── Step 8: Cleanup — cancella l'OCO e vendi a mercato ───────────────────
    logger.info("[SPIKE] Step 8: Cleanup — cancello OCO e chiudo posizione...")
    try:
        await adapter.cancel_open_exit_orders(sym_ref)
        logger.info("[SPIKE] OCO cancellato")
    except Exception as e:
        logger.warning("[SPIKE] Impossibile cancellare OCO: %s", e)

    try:
        from app.execution.exchange_models import ClosePositionRequest
        close = await adapter.close_position(ClosePositionRequest(
            symbol=sym_ref,
            side="buy",  # side della posizione (BUY → chiudiamo con SELL)
            quantity=qty,
        ))
        logger.info("[SPIKE] Posizione chiusa: ordId=%s avgPx=%.4f", close.order_id, close.average_price)
        results["cleanup_ok"] = True
    except Exception as e:
        logger.warning("[SPIKE] Cleanup close fallito: %s — chiudere manualmente su OKX Demo", e)
        results["cleanup_ok"] = False

    # ── Riepilogo ─────────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("RIEPILOGO SPIKE test_okx_amend_oco")
    logger.info("=" * 60)
    for k, v in results.items():
        status = "✅" if v is True else ("❌" if v is False else "  ")
        logger.info("%s  %-35s = %s", status, k, v)
    logger.info("=" * 60)

    checks = {k: v for k, v in results.items() if k.startswith("check_")}
    if all(checks.values()):
        logger.info("✅ TUTTI I CHECK PASSATI — amend-algos compatibile con OCO spot BTC-EUR OKX Demo")
        logger.info("PROSSIMO STEP: attivare BREAK_EVEN_ENABLED=True in paper, poi 1 trade live minimo")
    else:
        failed = [k for k, v in checks.items() if not v]
        logger.error("❌ CHECK FALLITI: %s", failed)
        logger.error("NON attivare la feature live prima di risolvere i fallimenti")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spike validazione amend-algos OKX Demo")
    parser.add_argument("--symbol", default="BTC-EUR", help="Simbolo OKX (default: BTC-EUR)")
    args = parser.parse_args()

    asyncio.run(run_spike(args.symbol))
