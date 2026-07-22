import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.db.supabase_client import get_supabase
from app.scalping._state import _execution_state
from app.scalping.broadcast import _now

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/binance/exchange-info")
async def binance_exchange_info():
    """Proxy Binance exchangeInfo to frontend (avoids CORS).
    Returns only the fields the frontend needs: symbol, status, baseAsset, quoteAsset.
    """
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://api.binance.com/api/v3/exchangeInfo")
            resp.raise_for_status()
            data = resp.json()
        allowed_quotes = {"USDT", "USDC", "FDUSD", "EUR"}
        symbols = [
            {
                "symbol": s["symbol"],
                "status": s["status"],
                "baseAsset": s["baseAsset"],
                "quoteAsset": s["quoteAsset"],
            }
            for s in data.get("symbols", [])
            if s.get("quoteAsset") in allowed_quotes and s.get("status") == "TRADING"
        ]
        return {"symbols": symbols}
    except Exception as e:
        logger.error(f"Failed to proxy Binance exchangeInfo: {e}")
        raise HTTPException(status_code=502, detail=f"Binance API unreachable: {e}")


@router.get("/exchange/instruments")
async def exchange_instruments(mode: str | None = None):
    """TASK-1109/1116.G: Provider-neutral instruments endpoint.

    OKX: returns spot pairs via /api/v5/public/instruments.
    Adds x-simulated-trading header when in demo mode (mode=test or settings.exchange_demo).
    Accepts optional ?mode=test|live query param to override settings.

    Binance: proxies Binance exchangeInfo.
    """

    provider = settings.EXCHANGE_PROVIDER.lower()

    if provider == "okx":
        import httpx
        base_url = settings.OKX_BASE_URL.rstrip("/")
        try:
            is_demo = (mode == "test") if mode else settings.exchange_demo
            headers = {}
            if is_demo:
                headers["x-simulated-trading"] = "1"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{base_url}/api/v5/public/instruments",
                    params={"instType": "SPOT"},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            raw = data.get("data", [])

            # TASK-1221: Check short availability for EUR pairs (once per discovery cycle)
            # TASK-1224 FIX: also run in demo mode — OKX demo supports short on select symbols
            short_availability: dict[str, dict] = {}
            if settings.EXCHANGE_PROVIDER.lower() == "okx":
                try:
                    from app.execution.exchange_models import SymbolRef, ShortAvailability
                    from app.execution.okx_exchange import OkxExchangeAdapter
                    adapter = OkxExchangeAdapter(
                        api_key=settings.exchange_api_key,
                        secret=settings.exchange_secret_key,
                        passphrase=settings.exchange_passphrase,
                        demo=is_demo,
                    )
                    eur_instruments = [
                        item for item in raw
                        if item.get("quoteCcy") == "EUR" and item.get("state") == "live"
                    ]
                    for item in eur_instruments[:10]:  # cap at 10 to avoid rate limits
                        inst_id = item["instId"]
                        try:
                            sym = SymbolRef.from_okx(inst_id)
                            avail = await adapter.get_short_availability(sym)
                            max_lev = 10  # default
                            if avail.available:
                                try:
                                    max_lev = await adapter.get_max_leverage(sym, mgn_mode="cross")
                                except Exception:
                                    pass
                            short_availability[inst_id] = {
                                "short_available": avail.available,
                                "short_borrow_rate_apr": round(avail.borrow_rate_apr, 4) if avail.borrow_rate_apr else None,
                                "short_max_loan_qty": avail.max_loan_qty,
                                "max_leverage": max_lev,
                            }
                        except Exception as e:
                            logger.debug("Short availability check failed for %s: %s", inst_id, e)
                            short_availability[inst_id] = {"short_available": False}
                except Exception as e:
                    logger.warning("Short availability batch check failed: %s", e)

            instruments = []
            for item in raw:
                if item.get("state") != "live":
                    continue
                inst_id = item["instId"]
                short_info = short_availability.get(inst_id, {})
                instruments.append({
                    "symbol": inst_id,
                    "base": item["baseCcy"],
                    "quote": item["quoteCcy"],
                    "status": item.get("state", "live"),
                    "provider": "okx",
                    "short_available": short_info.get("short_available", False),
                    "short_borrow_rate_apr": short_info.get("short_borrow_rate_apr"),
                    "short_max_loan_qty": short_info.get("short_max_loan_qty"),
                    "max_leverage": short_info.get("max_leverage", 10),
                })
            instruments.sort(key=lambda x: (x["quote"] != "EUR", x["symbol"]))
            eur_pairs = [i["symbol"] for i in instruments if i["quote"] == "EUR"]
            default_symbol = "BTC-EUR" if "BTC-EUR" in eur_pairs else (eur_pairs[0] if eur_pairs else "BTC-EUR")
            return {
                "provider": "okx",
                "demo": is_demo,
                "default_symbol": default_symbol,
                "instruments": instruments,
            }
        except Exception as e:
            logger.error(f"Failed to fetch OKX instruments: {e}")
            raise HTTPException(status_code=502, detail=f"OKX API unreachable: {e}")
    else:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://api.binance.com/api/v3/exchangeInfo")
                resp.raise_for_status()
                data = resp.json()
            allowed_quotes = {"USDT", "USDC", "FDUSD", "EUR"}
            instruments = [
                {"symbol": s["symbol"], "base": s["baseAsset"], "quote": s["quoteAsset"], "status": s["status"], "provider": "binance"}
                for s in data.get("symbols", [])
                if s.get("quoteAsset") in allowed_quotes and s.get("status") == "TRADING"
            ]
            instruments.sort(key=lambda x: x["symbol"])
            eur_pairs = [i["symbol"] for i in instruments if i["quote"] == "EUR"]
            usdc_pairs = [i["symbol"] for i in instruments if i["quote"] == "USDC"]
            default_symbol = eur_pairs[0] if eur_pairs else (usdc_pairs[0] if usdc_pairs else "BTCUSDC")
            return {"provider": "binance", "demo": False, "default_symbol": default_symbol, "instruments": instruments}
        except Exception as e:
            logger.error(f"Failed to proxy Binance exchangeInfo: {e}")
            raise HTTPException(status_code=502, detail=f"Binance API unreachable: {e}")


@router.get("/sessions")
async def list_scalping_sessions(limit: int = 50, offset: int = 0) -> List[Dict]:
    """TASK-880: Lista sessioni scalping storiche, arricchite con totali reali dai trade."""
    try:
        supabase = get_supabase()
        resp = supabase.table("scalping_sessions") \
            .select("id, symbol, mode, status, started_at, stopped_at, total_pnl, trade_count, win_count, strategy, trade_value") \
            .order("started_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        rows = resp.data or []

        session_ids = [r["id"] for r in rows]
        trades_by_session: Dict[str, list] = {}
        if session_ids:
            try:
                tr = supabase.table("scalping_trades") \
                    .select("session_id, pnl, signal_reason, status, entry_price, exit_price, entry_time, quantity") \
                    .in_("session_id", session_ids) \
                    .eq("status", "closed") \
                    .execute()
                for t in (tr.data or []):
                    sid = t["session_id"]
                    trades_by_session.setdefault(sid, []).append(t)
            except Exception as te:
                logger.warning(f"list_sessions trades enrichment error: {te}")

        from datetime import datetime as _dt
        for row in rows:
            started = row.get("started_at")
            stopped = row.get("stopped_at")
            if started and stopped:
                try:
                    s = _dt.fromisoformat(started.replace("Z", "+00:00"))
                    e = _dt.fromisoformat(stopped.replace("Z", "+00:00"))
                    row["duration_seconds"] = int((e - s).total_seconds())
                except Exception:
                    row["duration_seconds"] = None
            else:
                row["duration_seconds"] = None

            session_trades = trades_by_session.get(row["id"], [])
            if session_trades:
                row["trade_count"] = len(session_trades)
                row["win_count"] = len([t for t in session_trades if (t.get("pnl") or 0) > 0])
                row["total_pnl"] = round(sum((t.get("pnl") or 0) for t in session_trades), 4)
                allocated_capital = float(row.get("trade_value") or 0)
                if allocated_capital <= 0:
                    allocated_capital = float(row.get("paper_balance") or 10000.0)
                row["total_pnl_pct"] = round(
                    (row["total_pnl"] / allocated_capital) * 100, 2
                ) if allocated_capital > 0 else None
                sorted_trades = sorted(session_trades, key=lambda t: t.get("entry_time") or "")
                first_entry = float(sorted_trades[0].get("entry_price") or 0)
                last_exit = float(sorted_trades[-1].get("exit_price") or 0)
                if first_entry > 0 and last_exit > 0:
                    row["hold_pnl_pct"] = round((last_exit - first_entry) / first_entry * 100, 2)
                else:
                    row["hold_pnl_pct"] = None

        return rows
    except Exception as e:
        logger.warning(f"list_scalping_sessions error: {e}")
        return []


@router.get("/trade-history")
async def get_trade_history(session_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """TASK-881: Trade history. Se session_id fornito: query DB. Altrimenti: memoria corrente."""
    if session_id:
        try:
            supabase = get_supabase()
            resp = supabase.table("scalping_trades") \
                .select("symbol, side, entry_price, exit_price, quantity, pnl, pnl_pct, entry_time, exit_time, signal_reason, status") \
                .eq("session_id", session_id) \
                .order("entry_time", desc=True) \
                .limit(limit) \
                .execute()
            return resp.data or []
        except Exception as e:
            logger.warning(f"get_trade_history DB error: {e}")
            return []

    trades = _execution_state["trade_history"]
    closed_trades = [t for t in trades if t.get("exit_price") is not None]
    sorted_trades = sorted(closed_trades, key=lambda t: t.get("timestamp", ""), reverse=True)
    result = []
    for t in sorted_trades[:limit]:
        row = dict(t)
        row.setdefault("entry_time", t.get("timestamp"))
        row.setdefault("exit_time", t.get("timestamp"))
        result.append(row)
    return result


@router.get("/candles/{symbol}")
async def get_candles(symbol: str, limit: int = 100) -> List[Dict]:
    """Get candle history for a symbol."""
    try:
        from app.scalping.backtest.historical_loader import HistoricalLoader
        loader = HistoricalLoader()
        past_candles = await loader.load_ohlcv(symbol.upper(), interval="1m", limit=limit)
        if past_candles:
            result = [
                {
                    "symbol": symbol,
                    "open": float(c.open),
                    "high": float(c.high),
                    "low": float(c.low),
                    "close": float(c.close),
                    "volume": float(c.volume),
                    "timestamp": c.timestamp.isoformat(),
                }
                for c in past_candles
            ]
            logger.info(f"Returning {len(result)} candles from HistoricalLoader for {symbol}")
            return result
        return []
    except Exception as e:
        logger.warning(f"HistoricalLoader fetch failed for {symbol}: {e}")
        return []


def _snapshot_to_dict(symbol: str, snapshot: Any) -> Dict[str, Any]:
    """Converte MarketIntelSnapshot in dict per risposta API,
    includendo sia lo score aggregato che i dati grezzi dei collector.
    """
    result: Dict[str, Any] = {
        "symbol": symbol,
        "recorded_at": _now(),
    }

    if snapshot.signal_score:
        score = snapshot.signal_score
        result["signal_score"] = score.total
        result["signal_bias"] = score.bias
        result["tradeable"] = score.tradeable
        result["confidence"] = score.signal_strength or 0.0
        result["breakdown"] = score.breakdown

    if snapshot.funding_rate:
        result["funding_rate"] = float(snapshot.funding_rate.rate)
    if snapshot.open_interest:
        result["open_interest"] = float(snapshot.open_interest.value_usd)
    if snapshot.fear_greed:
        result["fear_greed_value"] = snapshot.fear_greed.value
        result["fear_greed_label"] = snapshot.fear_greed.label
    if snapshot.cvd:
        result["cvd_trend"] = snapshot.cvd.trend or "neutral"
    if snapshot.long_short_ratio:
        result["long_pct"] = float(snapshot.long_short_ratio.long_pct)
        result["short_pct"] = float(snapshot.long_short_ratio.short_pct)

    return result
