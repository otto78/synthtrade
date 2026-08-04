"""TASK-1246 — Spike: 6 amend consecutivi su OKX Demo per validare rate limit.

Verifica che amend-algos non ritorni 429 o rate-limit sCode su chiamate
ravvicinate (~15s di distanza) sulla stessa posizione OCO.

Prerequisiti:
- TRADING_MODE=test nel .env
- Saldo BTC-EUR sufficiente per quantità minima

Esecuzione:
    cd synthtrade/backend
    .venv/Scripts/activate
    python -m scripts.test_okx_amend_rate [--symbol BTC-EUR] [--interval 15]
"""

import asyncio
import argparse
import logging
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("spike_amend_rate")


async def run_spike(symbol_str: str = "BTC-EUR", interval_sec: int = 15) -> dict:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    trading_mode = os.environ.get("TRADING_MODE", "test")
    if trading_mode != "test":
        raise RuntimeError(f"TRADING_MODE={trading_mode} — richiede TRADING_MODE=test (Demo)")

    from app.execution.okx_exchange import OkxExchangeAdapter
    from app.execution.exchange_models import (
        SymbolRef, MarketOrderRequest, ExitBracketRequest, ClosePositionRequest
    )

    adapter = OkxExchangeAdapter(
        api_key=os.environ["OKX_API_KEY"],
        secret=os.environ["OKX_SECRET_KEY"],
        passphrase=os.environ["OKX_PASSPHRASE"],
        demo=True,
    )

    sym = SymbolRef.from_okx(symbol_str)
    results: dict = {"amends": [], "errors": [], "passed": 0, "failed": 0}

    # ── Setup: buy minimo + OCO ───────────────────────────────────────────────
    logger.info("[RATE_SPIKE] Ottengo regole e prezzo corrente per %s...", symbol_str)
    rules = await adapter.get_symbol_rules(sym)
    price = await adapter.get_ticker_price(symbol_str)

    trade_value = 25.0  # EUR — usa quote_amount per evitare errori di quantità minima
    qty = max(rules.round_qty(trade_value / price), rules.min_sz)

    logger.info("[RATE_SPIKE] BUY %s qty=%.8f @ %.2f (o quote_amount=%.2f EUR)", symbol_str, qty, price, trade_value)
    buy = await adapter.place_market_order(MarketOrderRequest(
        symbol=sym, side="buy", quantity=qty, quote_amount=trade_value
    ))
    exec_price = buy.average_price or price

    tp_price = rules.round_price(exec_price * 1.008)   # +0.8%
    sl_price = rules.round_price(exec_price * 0.993)   # -0.7%

    logger.info("[RATE_SPIKE] Piazzo OCO TP=%.4f SL=%.4f...", tp_price, sl_price)
    bracket = await adapter.place_exit_bracket(ExitBracketRequest(
        symbol=sym, side="sell", quantity=qty,
        tp_price=tp_price, sl_price=sl_price,
    ))
    algo_id = bracket.bracket_id
    logger.info("[RATE_SPIKE] OCO attivo algoId=%s", algo_id)

    await asyncio.sleep(2)

    # ── 6 amend consecutivi ──────────────────────────────────────────────────
    # Ogni amend alza lo SL di un tick (simulazione step trailing)
    current_sl = sl_price
    for i in range(1, 7):
        new_sl = rules.round_price(current_sl + rules.tick_sz * 10)  # +10 tick
        # Guard: non superare exec_price
        if new_sl >= exec_price:
            logger.info("[RATE_SPIKE] Step %d: new_sl=%.4f >= exec_price=%.4f, stop", i, new_sl, exec_price)
            break

        req_id = uuid.uuid4().hex[:32]
        logger.info("[RATE_SPIKE] Amend %d/%d: algoId=%s newSL=%.4f reqId=%s",
                    i, 6, algo_id, new_sl, req_id)

        try:
            result = await adapter.amend_exit_bracket_stop_loss(
                symbol=sym,
                algo_id=algo_id,
                new_sl_trigger_px=new_sl,
                req_id=req_id,
            )
            results["amends"].append({
                "step": i, "new_sl": new_sl, "req_id": req_id,
                "sCode": result.get("sCode"), "ok": True,
            })
            results["passed"] += 1
            current_sl = new_sl
            logger.info("[RATE_SPIKE] ✅ Amend %d OK sCode=%s", i, result.get("sCode"))
        except Exception as e:
            results["amends"].append({"step": i, "new_sl": new_sl, "error": str(e), "ok": False})
            results["failed"] += 1
            logger.error("[RATE_SPIKE] ❌ Amend %d FALLITO: %s", i, e)

        if i < 6:
            logger.info("[RATE_SPIKE] Attendo %ds...", interval_sec)
            await asyncio.sleep(interval_sec)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    logger.info("[RATE_SPIKE] Cleanup — cancello OCO e chiudo posizione...")
    try:
        await adapter.cancel_open_exit_orders(sym)
    except Exception as e:
        logger.warning("[RATE_SPIKE] Cancel OCO: %s", e)

    try:
        await adapter.close_position(ClosePositionRequest(symbol=sym, side="buy", quantity=qty))
        results["cleanup"] = True
    except Exception as e:
        logger.warning("[RATE_SPIKE] Close position: %s — chiudere manualmente su OKX Demo", e)
        results["cleanup"] = False

    # ── Riepilogo ─────────────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("RIEPILOGO SPIKE test_okx_amend_rate")
    logger.info("=" * 60)
    logger.info("Amend OK: %d/6 | Falliti: %d/6", results["passed"], results["failed"])
    for a in results["amends"]:
        status = "✅" if a.get("ok") else "❌"
        logger.info("%s Step %d — SL=%.4f %s",
                    status, a["step"], a.get("new_sl", 0),
                    f"sCode={a.get('sCode')}" if a.get("ok") else f"err={a.get('error','')[:60]}")

    if results["failed"] == 0:
        logger.info("✅ RATE LIMIT OK — 6 amend consecutivi a %ds completati senza errori", interval_sec)
        logger.info("TRAILING STEP_NET_PCT=0.15%% stimato: ~1 amend ogni 8-15 candele in condizioni normali")
    else:
        logger.error("❌ %d amend falliti — verificare prima di implementare il trailing", results["failed"])

    logger.info("=" * 60)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spike rate limit amend-algos OKX Demo")
    parser.add_argument("--symbol", default="BTC-EUR")
    parser.add_argument("--interval", type=int, default=15, help="Secondi tra un amend e il prossimo")
    args = parser.parse_args()
    asyncio.run(run_spike(args.symbol, args.interval))
