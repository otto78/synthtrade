"""
TASK-1103: OkxExchangeAdapter — REST adapter for OKX via ccxt + direct REST fallback.

Implements ExchangeAdapterProtocol from exchange_models.py.
Supports Demo Trading (x-simulated-trading: 1) and Live mode.
Base URL must be eea.okx.com for EU accounts.

NOTE: CCXT's fetch_balance() calls fetch_currencies() first, which fails with
50119 on OKX EU live accounts. We fall back to direct REST /api/v5/account/balance.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union, cast

import ccxt.async_support as ccxt
import httpx
from app.config import settings
from app.execution.exchange_models import (
    ClosePositionRequest,
    ExchangeOrder,
    ExitBracketOrder,
    ExitBracketRequest,
    ExitProtectionError,
    FeeTier,
    MarketOrderRequest,
    OrderSide,
    SymbolRef,
    SymbolRules,
    UnsupportedInstrumentError,
)
from app.execution.exchange import ExchangeOrderError
from app.scalping.intelligence.collectors._provider_maps import OKX_PERPETUAL_MAP

logger = logging.getLogger(__name__)

_FALLBACK_FEE = FeeTier(maker=0.001, taker=0.001, certified=False, source="fallback")


class OkxExchangeAdapter:
    """
    OKX exchange adapter implementing ExchangeAdapterProtocol.

    Demo Trading:  TRADING_MODE=test  → header x-simulated-trading: 1
    Live Trading:  TRADING_MODE=live  → no demo header, live credentials
    EU accounts:   base_url=https://eea.okx.com
    """

    provider = "okx"

    def __init__(
        self,
        api_key: str,
        secret: str,
        passphrase: str,
        demo: bool = True,
        base_url: str = "https://eea.okx.com",
        client: Any = None,
    ) -> None:
        self.trading_mode = "test" if demo else "live"
        self._demo = demo

        if client:
            self.client = client
        else:
            config: dict[str, Any] = {
                "apiKey": api_key,
                "secret": secret,
                "password": passphrase,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                    # TASK-1100 fix: OKX Demo has instruments with base=None (margin/futures).
                    # Restricting to SPOT avoids parse_market() crash in load_markets().
                    "fetchMarkets": ["spot"],
                },
            }
            if demo:
                config["headers"] = {"x-simulated-trading": "1"}

            self.client = ccxt.okx(config)

            # Override base URL for EU accounts
            # Guard against None urls (ccxt may return None in certain modes) and
            # None values in urls["api"] dict. isinstance guard skips non-string values.
            if base_url and "eea.okx.com" in base_url and self.client.urls is not None:
                self.client.urls["api"] = {
                    k: v.replace("www.okx.com", "eea.okx.com") if isinstance(v, str) else v
                    for k, v in (self.client.urls.get("api") or {}).items()
                }

            if demo:
                # Do NOT call set_sandbox_mode() after EU URL override —
                # it rebuilds urls["api"] from scratch and can crash on None values.
                # OKX demo is fully controlled via the x-simulated-trading header.
                self.client.headers = {
                    **getattr(self.client, "headers", {}),
                    "x-simulated-trading": "1",
                }

        self._rules_cache: dict[str, SymbolRules] = {}
        self._rules_cache_ts: dict[str, float] = {}
        self._rules_cache_ttl = 300  # 5 min
        self._price_cache: dict[str, dict[str, Any]] = {}
        self._price_cache_ttl = 15
        self._macro_cache: dict[str, Any] = {"timestamp": 0, "data": None}

    async def close(self) -> None:
        await self.client.close()

    # ── Balance ───────────────────────────────────────────────────────────────

    @staticmethod
    def _sign_headers(method: str, path: str, body: str = "") -> dict:
        """Firma le richieste OKX con il body incluso per POST."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        if body:
            prehash = ts + method + path + body
        else:
            prehash = ts + method + path
        sig = base64.b64encode(
            hmac.new(
                settings.exchange_secret_key.encode(),
                prehash.encode(),
                hashlib.sha256,
            ).digest()
        ).decode()
        headers = {
            "OK-ACCESS-KEY": settings.exchange_api_key,
            "OK-ACCESS-SIGN": sig,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": settings.exchange_passphrase,
            "Content-Type": "application/json",
        }
        if settings.exchange_demo:
            headers["x-simulated-trading"] = "1"
        return headers

    async def _direct_fetch_balance(self) -> list[dict[str, Any]]:
        """Direct REST fallback for OKX balance when CCXT fetch_balance fails.

        CCXT fetch_balance() calls fetch_currencies() first, which returns
        50119 on OKX EU live accounts. This bypasses CCXT entirely.
        """
        path = "/api/v5/account/balance"
        url = settings.OKX_BASE_URL.rstrip("/") + path
        headers = self._sign_headers("GET", path)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != "0":
                raise RuntimeError(f"OKX API error {data.get('code')}: {data.get('msg')}")
            return data.get("data", [])

    async def _balance_from_rest(self, asset: str) -> float:
        """Get balance for a specific asset via direct OKX REST.

        Uses only availBal (available balance) to match get_holdings() behavior
        and okx_balance.py dashboard logic. This prevents double-counting.
        """
        raw = await self._direct_fetch_balance()
        for account in raw:
            for detail in account.get("details", []):
                if detail.get("ccy") == asset:
                    # Use only available balance (availBal) to avoid double-counting
                    # cashBal + frozenBal are already included in total calculations elsewhere
                    return float(detail.get("availBal", 0) or 0)
        return 0.0

    async def get_holdings(self) -> dict[str, float]:
        try:
            balance = await self.client.fetch_balance()
            free = balance.get("free", {})
            return {asset: float(amt) if amt is not None else 0.0 for asset, amt in free.items() if amt is not None and float(amt) > 0}
        except Exception as e:
            logger.warning("CCXT fetch_balance failed (%s), falling back to direct REST", e)
            try:
                raw = await self._direct_fetch_balance()
                holdings: dict[str, float] = {}
                for account in raw:
                    for detail in account.get("details", []):
                        asset = detail.get("ccy", "")
                        avail = float(detail.get("availBal", 0) or 0)
                        if asset and avail > 0:
                            holdings[asset] = holdings.get(asset, 0.0) + avail
                return holdings
            except Exception as e2:
                raise ExchangeOrderError(f"OKX holdings fetch failed: {e2}", original_exception=e2) from e2

    async def get_balance(self, asset: str = "EUR") -> float:
        """Get available balance for an asset.

        Uses direct REST to match okx_balance.py dashboard logic.
        CCXT fetch_balance() can return inconsistent totals on OKX EU accounts.
        """
        try:
            return await self._balance_from_rest(asset)
        except Exception as e:
            logger.warning("OKX balance fetch failed: %s", e)
            raise ExchangeOrderError(f"OKX balance fetch failed: {e}") from e

    # ── Ticker ────────────────────────────────────────────────────────────────

    async def get_ticker_price(self, symbol: str) -> float:
        now = time.time()
        cached = self._price_cache.get(symbol)
        if cached and (now - cached["ts"]) < self._price_cache_ttl:
            return cached["price"]
        try:
            ref = SymbolRef.from_compact(symbol) if "/" not in symbol and "-" not in symbol else None
            ccxt_sym = ref.ccxt if ref else symbol.replace("-", "/")
            ticker = await self.client.fetch_ticker(ccxt_sym)
            price = float(ticker.get("last") or 0)
            self._price_cache[symbol] = {"price": price, "ts": now}
            return price
        except Exception as e:
            if cached:
                logger.warning("get_ticker_price(%s) stale cache fallback: %s", symbol, e)
                return cached["price"]
            raise ExchangeOrderError(f"OKX ticker fetch failed for {symbol}: {e}") from e

    # ── Futures perpetual read-only (TASK-1153) ───────────────────────────────
    # Funding rate / Open Interest exist ONLY on USDT perpetual futures (SWAP).
    # The perpetual is quoted in USDT, NOT in EUR, so these data reflect sentiment
    # on the base asset (BTC/ETH) and are used as a PROXY for the EUR pair — never
    # presented as literal BTC-EUR data. Consumed by the intelligence collectors.

    async def get_open_interest(self, base_asset: str) -> Optional[float]:
        """Open interest (USD) for the base asset's USDT perpetual SWAP.

        Used by OpenInterestCollector when EXCHANGE_PROVIDER=okx.
        Returns None if no perpetual exists for the base asset, or on any error.
        """
        inst_id = OKX_PERPETUAL_MAP.get(base_asset.upper())
        if not inst_id:
            return None
        path = f"/api/v5/public/open-interest?instType=SWAP&instId={inst_id}"
        url = settings.OKX_BASE_URL.rstrip("/") + path
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != "0":
                    logger.warning(
                        "OKX open-interest API error %s: %s", data.get("code"), data.get("msg")
                    )
                    return None
                items = data.get("data") or []
                if not items:
                    return None
                entry = items[0]
                for key in ("oiUsd", "oiCcy", "oi"):
                    value = entry.get(key)
                    if value not in (None, ""):
                        return float(value)
                return None
        except Exception as e:
            logger.warning("OkxExchangeAdapter.get_open_interest(%s) failed: %s", base_asset, e)
            return None

    async def get_funding_rate(self, base_asset: str) -> Optional[float]:
        """Current funding rate for the base asset's USDT perpetual SWAP.

        Used by FundingRateCollector when EXCHANGE_PROVIDER=okx.
        Returns None if no perpetual exists for the base asset, or on any error.
        """
        inst_id = OKX_PERPETUAL_MAP.get(base_asset.upper())
        if not inst_id:
            return None
        path = f"/api/v5/public/funding-rate?instId={inst_id}"
        url = settings.OKX_BASE_URL.rstrip("/") + path
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != "0":
                    logger.warning(
                        "OKX funding-rate API error %s: %s", data.get("code"), data.get("msg")
                    )
                    return None
                items = data.get("data") or []
                if not items:
                    return None
                entry = items[0]
                rate = entry.get("fundingRate")
                if rate in (None, ""):
                    return None
                return float(rate)
        except Exception as e:
            logger.warning("OkxExchangeAdapter.get_funding_rate(%s) failed: %s", base_asset, e)
            return None

    # ── Symbol rules ──────────────────────────────────────────────────────────

    async def get_symbol_rules(self, symbol: SymbolRef) -> SymbolRules:
        key = symbol.okx
        now = time.time()
        cached_ts = self._rules_cache_ts.get(key, 0)
        if key in self._rules_cache and (now - cached_ts) < self._rules_cache_ttl:
            return self._rules_cache[key]

        try:
            markets = await self.client.load_markets()
            market = markets.get(symbol.ccxt)
            if not market:
                raise UnsupportedInstrumentError(f"OKX: {symbol.ccxt} not found in markets")

            info = cast(dict[str, Any], market.get("info", {}))
            rules = SymbolRules(
                symbol=symbol,
                lot_sz=float(info.get("lotSz", 0.00000001)),
                min_sz=float(info.get("minSz", 0.00001)),
                tick_sz=float(info.get("tickSz", 0.01)),
                max_mkt_sz=float(info.get("maxMktSz", 1_000_000)),
                max_mkt_amt=float(info.get("maxMktAmt", 1_000_000)),
                raw=info,
            )
            self._rules_cache[key] = rules
            self._rules_cache_ts[key] = now
            return rules
        except UnsupportedInstrumentError:
            raise
        except Exception as e:
            logger.warning(f"CCXT load_markets failed for {symbol.okx} ({e}), trying direct REST fallback")
            try:
                return await self._direct_fetch_symbol_rules(symbol)
            except Exception as e2:
                raise ExchangeOrderError(f"OKX get_symbol_rules failed for {symbol.okx}: {e2}") from e2

    # ── Direct REST fallback for symbol rules ─────────────────────────────────

    async def _direct_fetch_symbol_rules(self, symbol: SymbolRef) -> SymbolRules:
        """Direct REST fallback for OKX symbol rules when CCXT load_markets fails.

        Uses /api/v5/public/instruments endpoint.
        """
        path = f"/api/v5/public/instruments?instType=SPOT&instId={symbol.okx}"
        url = settings.OKX_BASE_URL.rstrip("/") + path
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != "0":
                raise RuntimeError(f"OKX API error {data.get('code')}: {data.get('msg')}")
            instruments = data.get("data", [])
            if not instruments:
                raise UnsupportedInstrumentError(f"OKX: {symbol.okx} not found in instruments")
            info = cast(dict[str, Any], instruments[0])
            return SymbolRules(
                symbol=symbol,
                lot_sz=float(info.get("lotSz", 0.00000001)),
                min_sz=float(info.get("minSz", 0.00001)),
                tick_sz=float(info.get("tickSz", 0.01)),
                max_mkt_sz=float(info.get("maxMktSz", 1_000_000)),
                max_mkt_amt=float(info.get("maxMktAmt", 1_000_000)),
                raw=info,
            )

    # ── Symbol filters (router compatibility) ───────────────────────────────

    async def get_symbol_filters(self, symbol: str) -> Dict[str, Any]:
        """Get symbol filters for router compatibility.

        Returns dict with stepSize, minQty, minNotional, quoteAsset, baseAsset.
        Wraps get_symbol_rules() for BinanceExchangeAdapter compatibility.
        Note: OKX doesn't have minNotional - using minSz * typical_price as proxy.
        """
        try:
            sym_ref = SymbolRef.from_any(symbol)
            rules = await self.get_symbol_rules(sym_ref)
            # OKX doesn't have minNotional - use minSz * 100 as reasonable minimum
            # (typical minimum order value is ~1-10 EUR)
            min_notional = max(1.0, rules.min_sz * 100)
            return {
                "stepSize": rules.lot_sz,
                "minQty": rules.min_sz,
                "minNotional": min_notional,
                "tickSize": rules.tick_sz,
                "quoteAsset": sym_ref.quote,
                "baseAsset": sym_ref.base,
            }
        except Exception as e:
            raise ExchangeOrderError(f"OKX get_symbol_filters failed for {symbol}: {e}") from e

    # ── BTC macro context (router compatibility) ─────────────────────────────

    async def get_btc_macro_context(self) -> Dict[str, Any]:
        """Fetch BTC macro context for supervisor compatibility.

        Uses BTC-USDT (or BTC-EUR if available) for price and changes.
        60-second cache to avoid rate limits.
        """
        now = time.time()
        if now - self._macro_cache.get("timestamp", 0) < 60 and self._macro_cache.get("data"):
            return self._macro_cache["data"]

        try:
            # Try BTC-USDT first (more liquid), fallback to BTC-EUR
            btc_symbol = "BTC-USDT"
            try:
                ticker = await self.client.fetch_ticker(btc_symbol)
            except Exception:
                btc_symbol = "BTC-EUR"
                ticker = await self.client.fetch_ticker(btc_symbol)

            price = float(ticker.get("last") or 0.0)
            change_24h_pct = float(ticker.get("percentage") or 0.0)

            # Klines 1h for 1h change
            klines = await self.client.fetch_ohlcv(btc_symbol, timeframe="1h", limit=2)
            change_1h_pct = 0.0
            if len(klines) >= 2:
                close_prev = float(klines[0][4] or 0)
                close_now = float(klines[1][4] or 0)
                if close_prev > 0:
                    change_1h_pct = ((close_now - close_prev) / close_prev) * 100

            # Determine regime
            regime = "normal"
            if change_1h_pct < -2.0:
                regime = "crash"
            elif change_1h_pct > 2.0:
                regime = "rally"

            data = {
                "btc_price_at_entry": price,
                "btc_change_1h_pct": round(change_1h_pct, 2),
                "btc_change_24h_pct": round(change_24h_pct, 2),
                "macro_regime": regime,
            }
            self._macro_cache["timestamp"] = now
            self._macro_cache["data"] = data
            return data

        except Exception as e:
            logger.warning(f"CCXT failed for BTC macro context ({e}), trying direct REST fallback")
            try:
                # Direct REST fallback for EU accounts
                return await self._direct_fetch_btc_macro_context()
            except Exception as e2:
                logger.warning(f"Failed to fetch BTC macro context: {e2}")
                return {
                    "btc_price_at_entry": 0.0,
                    "btc_change_1h_pct": 0.0,
                    "btc_change_24h_pct": 0.0,
                    "macro_regime": "unknown",
                }

    async def _direct_fetch_btc_macro_context(self) -> Dict[str, Any]:
        """Direct REST fallback for BTC macro context on EU accounts."""
        # Try BTC-USDT first, then BTC-EUR
        for btc_symbol in ["BTC-USDT", "BTC-EUR"]:
            try:
                # Get current ticker
                ticker_path = f"/api/v5/market/ticker?instId={btc_symbol}"
                ticker_url = settings.OKX_BASE_URL.rstrip("/") + ticker_path
                async with httpx.AsyncClient(timeout=10.0) as client:
                    ticker_resp = await client.get(ticker_url)
                    ticker_resp.raise_for_status()
                    ticker_data = ticker_resp.json()
                    if ticker_data.get("code") != "0":
                        continue
                    ticker = cast(dict[str, Any], ticker_data.get("data", [{}])[0])
                    price = float(ticker.get("last") or 0.0)
                    change_24h_pct = float(ticker.get("chg") or 0.0) * 100

                # Get 1h candles for 1h change
                candles_path = f"/api/v5/market/candles?instId={btc_symbol}&bar=1H&limit=2"
                candles_url = settings.OKX_BASE_URL.rstrip("/") + candles_path
                async with httpx.AsyncClient(timeout=10.0) as client:
                    candles_resp = await client.get(candles_url)
                    candles_resp.raise_for_status()
                    candles_data = candles_resp.json()
                    if candles_data.get("code") != "0":
                        continue
                    candles = candles_data.get("data", [])

                # Calculate 1h change from candles
                change_1h_pct = 0.0
                if len(candles) >= 2:
                    close_prev = float(candles[0][4] or 0)
                    close_now = float(candles[1][4] or 0)
                    if close_prev > 0:
                        change_1h_pct = ((close_now - close_prev) / close_prev) * 100

                # Determine regime
                regime = "normal"
                if change_1h_pct < -2.0:
                    regime = "crash"
                elif change_1h_pct > 2.0:
                    regime = "rally"

                return {
                    "btc_price_at_entry": price,
                    "btc_change_1h_pct": round(change_1h_pct, 2),
                    "btc_change_24h_pct": round(change_24h_pct, 2),
                    "macro_regime": regime,
                }
            except Exception:
                continue
        raise RuntimeError("Could not fetch BTC macro context from any endpoint")

    # ── Fee tier ──────────────────────────────────────────────────────────────

    async def _direct_fetch_trade_fee(self, symbol: SymbolRef) -> FeeTier:
        """Direct REST fallback for OKX trade fee when CCXT fetch_trading_fee fails.

        CCXT fetch_trading_fee() can fail with 50119 on OKX EU accounts.
        This bypasses CCXT entirely and calls the OKX REST endpoint directly.
        """
        path = f"/api/v5/account/trade-fee?instType=SPOT&instId={symbol.okx}"
        url = settings.OKX_BASE_URL.rstrip("/") + path
        headers = self._sign_headers("GET", path)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") != "0":
                raise RuntimeError(f"OKX API error {data.get('code')}: {data.get('msg')}")
            fee_data = data.get("data", [])
            if not fee_data:
                raise RuntimeError("No fee data returned")
            # OKX returns fee in maker/taker fields (negative = rebate)
            maker = float(fee_data[0].get("maker") or 0.001)
            taker = float(fee_data[0].get("taker") or 0.001)
            
            # TASK-1127: Convert negative fees to positive for base level accounts
            # OKX API returns negative fees even for regular accounts (Lv1), but regular accounts
            # don't actually have rebates. We convert to positive for base VIP levels.
            vip_level = fee_data[0].get("level", "")
            if vip_level in ["Lv1", ""] or not any(char.isalpha() for char in vip_level):
                # Base level - convert to positive fees
                maker = abs(maker)
                taker = abs(taker)
                logger.info(
                    "[OKX FEE DIRECT] %s maker=%.4f taker=%.4f (base level, converted to positive)",
                    symbol.okx, maker, taker,
                )
            else:
                # VIP level with actual rebates - keep negative
                logger.info(
                    "[OKX FEE DIRECT] %s maker=%.4f taker=%.4f (VIP level %s, keeping negative)",
                    symbol.okx, maker, taker, vip_level,
                )
            
            return FeeTier(
                maker=maker,
                taker=taker,
                certified=True,
                source="okx_trade_fee_direct",
                raw=cast(dict[str, Any], fee_data[0]),
            )

    async def get_trade_fee(self, symbol: SymbolRef) -> FeeTier:
        """
        Fetch fee tier from OKX GET /api/v5/account/trade-fee.

        OKX returns negative values for rebates (maker=-0.002 means -0.2% rebate).
        For base level accounts (Lv1), we convert to positive since they don't have rebates.
        Falls back to direct REST if CCXT fails (50119 on EU accounts).
        """
        try:
            response = await self.client.fetch_trading_fee(symbol.ccxt)
            if not response or response.get("maker") is None:
                logger.warning("OKX get_trade_fee: empty response for %s", symbol.ccxt)
                return await self._direct_fetch_trade_fee(symbol)

            maker = float(response.get("maker") or 0)
            taker = float(response.get("taker") or 0)
            
            # TASK-1127: Convert negative fees to positive for base level accounts
            # CCXT response doesn't include VIP level, so we check the sign and context
            # If we're in live mode and fees are negative, it's likely API returning wrong data
            if not self._demo and (maker < 0 or taker < 0):
                # Live mode with negative fees - likely base level account with API bug
                maker = abs(maker)
                taker = abs(taker)
                logger.info(
                    "[OKX FEE] %s maker=%.4f taker=%.4f (live mode, converted to positive)",
                    symbol.ccxt, maker, taker,
                )
            else:
                logger.info(
                    "[OKX FEE] %s maker=%.4f taker=%.4f (negative=rebate)",
                    symbol.ccxt, maker, taker,
                )
                
            return FeeTier(
                maker=maker,
                taker=taker,
                certified=True,
                source="okx_trade_fee",
                raw=cast(dict[str, Any], response),
            )
        except Exception as e:
            logger.warning("OKX get_trade_fee failed for %s: %s — trying direct REST fallback", symbol.ccxt, e)
            try:
                return await self._direct_fetch_trade_fee(symbol)
            except Exception as fallback_e:
                logger.error("OKX get_trade_fee direct fallback also failed: %s — using hardcoded fallback", fallback_e)
                return _FALLBACK_FEE

    # ── Orders ────────────────────────────────────────────────────────────────

    async def _direct_place_market_order(self, symbol: SymbolRef, side: str, quantity: float, quote_amount: Optional[float] = None) -> dict[str, Any]:
        """Direct REST fallback per OKX market order quando CCXT fallisce."""
        path = "/api/v5/trade/order"
        url = settings.OKX_BASE_URL.rstrip("/") + path
        
        # Prepara il body
        body = {
            "instId": symbol.okx,
            "tdMode": "cash",
            "side": side,
            "ordType": "market",
            "sz": str(quantity),
        }
        
        if quote_amount and side == "buy":
            body["tgtCcy"] = "quote_ccy"
            body["sz"] = str(quote_amount)
        
        headers = self._sign_headers("POST", path, json.dumps(body))
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                logger.error("OKX order POST failed [%s]: %s", resp.status_code, resp.text)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != "0":
                s_code = data.get("sCode")
                s_msg = data.get("sMsg")
                raise RuntimeError(
                    f"OKX API error {data.get('code')}: {data.get('msg')} "
                    f"| sCode={s_code} sMsg={s_msg} | full_data={data}"
                )

            return data.get("data", [{}])[0]

    async def place_market_order(self, request: MarketOrderRequest) -> ExchangeOrder:
        """Place a market order on OKX.

        Tries CCXT first, falls back to direct REST for EU accounts.
        """
        symbol = request.symbol
        side = request.side
        quantity = request.quantity
        quote_amount = request.quote_amount

        rules = await self.get_symbol_rules(symbol)
        qty = rules.round_qty(quantity) if quantity else 0.0

        if qty <= 0 and not quote_amount:
            raise ExchangeOrderError(f"OKX place_market_order: rounded qty=0 for {symbol.okx}")

        try:
            params: dict[str, Any] = {"tdMode": "cash"}
            order = await self.client.create_order(
                symbol=symbol.ccxt,
                type="market",
                side=side,
                amount=qty or quote_amount or 0,
                params=params,
            )
            result = cast(dict[str, Any], order)
        except Exception as e:
            logger.warning("OKX CCXT create_order failed for %s: %s — trying direct REST fallback", symbol.okx, e)
            result = await self._direct_place_market_order(
                symbol=symbol,
                side=side,
                quantity=qty or quantity,
                quote_amount=quote_amount,
            )

        commission, commission_asset = self._extract_commission(result)
        return ExchangeOrder(
            provider="okx",
            symbol=symbol,
            order_id=str(result.get("id") or result.get("ordId", "")),
            side=side,
            order_type="market",
            status=result.get("status", ""),
            quantity=qty or quantity,
            filled=float(result.get("filled") or result.get("fillSz") or 0),
            average_price=float(result.get("average") or result.get("avgPx") or 0),
            commission=commission,
            commission_asset=commission_asset or symbol.quote,
            raw=result,
        )

    async def close_position(self, request: ClosePositionRequest) -> ExchangeOrder:
        opp_side: OrderSide = "sell" if request.side == "buy" else "buy"
        return await self.place_market_order(
            MarketOrderRequest(symbol=request.symbol, side=opp_side, quantity=request.quantity)
        )

    async def get_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        """Return open orders for a symbol (both regular and algo/OCO).

        Used by _on_uds_reconnect_sync to detect if the OCO bracket is still active.
        Returns a combined list of open regular orders and pending algo orders.
        """
        sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
        results: list[dict] = []

        # 1. Check pending algo orders (OCO brackets via order-algo)
        try:
            path = "/api/v5/trade/orders-algo-pending"
            url = settings.OKX_BASE_URL.rstrip("/") + path
            headers = self._sign_headers("GET", path)
            params = {"instType": "SPOT", "instId": sym_ref.okx, "ordType": "oco"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "0":
                        results.extend(data.get("data", []))
        except Exception as e:
            logger.debug("get_open_orders: algo-pending check failed: %s", e)

        # 2. Check regular open orders via CCXT
        try:
            ccxt_sym = sym_ref.ccxt
            orders = await self.client.fetch_open_orders(ccxt_sym)
            results.extend(orders)
        except Exception as e:
            logger.debug("get_open_orders: CCXT fetch_open_orders failed: %s", e)

        return results

    async def get_algo_orders_history(self, symbol: str) -> list[dict[str, Any]]:
        """Return algo orders history for a symbol (OCO/TP/SL fills).

        Used by _on_uds_reconnect_sync to detect if a bracket was executed
        during disconnection. Returns filled/cancelled algo orders.
        
        NOTE: OKX EU accounts may return 400 for orders-algo-history with ordType=oco.
        Falls back to /api/v5/trade/fills endpoint which shows actual fills.
        """
        sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
        results: list[dict] = []

        # Try fills endpoint first (works on OKX EU)
        try:
            path = "/api/v5/trade/fills"
            url = settings.OKX_BASE_URL.rstrip("/") + path
            headers = self._sign_headers("GET", path)
            params = {"instType": "SPOT", "instId": sym_ref.okx}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "0":
                        # Convert fills to algo-like format for compatibility
                        for fill in data.get("data", []):
                            results.append({
                                "algoId": fill.get("algoId"),
                                "state": "effective",  # fills are always filled
                                "avgPx": fill.get("fillPx"),
                                "fillPx": fill.get("fillPx"),
                                "ordType": fill.get("ordType", "oco"),
                                "side": fill.get("side"),
                                "instId": fill.get("instId"),
                            })
        except Exception as e:
            logger.debug("get_algo_orders_history fills fallback failed for %s: %s", symbol, e)

        return results


    # ── Exit bracket (TP/SL algo order) ──────────────────────────────────────

    async def _direct_place_exit_bracket(
        self,
        symbol: SymbolRef,
        side: str,
        quantity: float,
        tp_price: float,
        sl_price: float,
    ) -> dict[str, Any]:
        """Direct REST fallback for OKX exit bracket when CCXT create_order fails.

        POST /api/v5/trade/order-algo with tdMode=cash for spot.
        Uses tpTriggerPx/slTriggerPx with -1 for market execution.
        """
        path = "/api/v5/trade/order-algo"
        url = settings.OKX_BASE_URL.rstrip("/") + path

        body = {
            "instId": symbol.okx,
            "tdMode": "cash",
            "side": side,
            "ordType": "oco",          # REQUIRED by OKX /api/v5/trade/order-algo (50014 without it)
            "sz": str(quantity),
            "tpTriggerPx": str(tp_price),
            "tpOrdPx": "-1",
            "slTriggerPx": str(sl_price),
            "slOrdPx": "-1",
            "tpTriggerPxType": "last",
            "slTriggerPxType": "last",
        }

        headers = self._sign_headers("POST", path, json.dumps(body))

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                logger.error(
                    "OKX order-algo POST failed [%s]: %s",
                    resp.status_code, resp.text,
                )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != "0":
                s_code = data.get("sCode")
                s_msg = data.get("sMsg")
                raise RuntimeError(
                    f"OKX API error {data.get('code')}: {data.get('msg')} "
                    f"| sCode={s_code} sMsg={s_msg} | full_data={data}"
                )

            result = data.get("data", [{}])[0]
            if result.get("sCode", "0") != "0":
                raise RuntimeError(
                    f"OKX Order failed with sCode={result.get('sCode')}: {result.get('sMsg')} "
                    f"| full_data={data}"
                )

            return result

    async def place_exit_bracket(self, request: ExitBracketRequest) -> ExitBracketOrder:
        """
        Place TP/SL bracket on OKX using order-algo (POST /api/v5/trade/order-algo).

        Uses attachAlgoOrds approach via ccxt create_order with params.
        If CCXT fails with 50119 (EU routing quirk), falls back to direct REST.
        If both fail, raises ExitProtectionError with NO internal emergency close
        — the caller (router) is the sole owner of the emergency close procedure,
        preventing race conditions from dual close attempts.
        """
        symbol = request.symbol
        # Initialize variables to avoid unbound errors in exception handler
        qty = 0.0
        tp_price = 0.0
        sl_price = 0.0
        
        try:
            rules = await self.get_symbol_rules(symbol)
            tp_price = rules.round_price(request.tp_price)
            sl_price = rules.round_price(request.sl_price)
            qty = rules.round_qty(request.quantity)

            if qty <= 0:
                raise ExchangeOrderError(f"OKX bracket: rounded qty=0 for {symbol.okx}")

            # OKX algo order: tpOrdPx / slTriggerPx
            params: dict[str, Any] = {
                "tdMode": "cash",
                "tpTriggerPx": str(tp_price),
                "tpOrdPx": "-1",        # -1 = market order at trigger
                "slTriggerPx": str(sl_price),
                "slOrdPx": "-1",        # -1 = market order at trigger
                "tpTriggerPxType": "last",
                "slTriggerPxType": "last",
            }

            order = await self.client.create_order(
                symbol=symbol.ccxt,
                type=cast(Any, "oco"),  # OKX supports oco via order-algo
                side=request.side,
                amount=qty,
                price=tp_price,
                params=params,
            )

            algo_id = str(order.get("id") or order.get("info", {}).get("algoId", ""))
            logger.info(
                "[OKX BRACKET] %s TP=%s SL=%s qty=%s algoId=%s",
                symbol.okx, tp_price, sl_price, qty, algo_id,
            )

            return ExitBracketOrder(
                provider="okx",
                symbol=symbol,
                bracket_id=algo_id,
                tp_order_id=algo_id,
                sl_order_id=algo_id,
                status="placed",
                raw=cast(dict[str, Any], order),
            )

        except (ExchangeOrderError, UnsupportedInstrumentError):
            raise
        except Exception as e:
            # Try direct REST fallback for 50119 (EU routing quirk) before giving up
            if "50119" in str(e) or "API key doesn't exist" in str(e):
                logger.warning(
                    "[OKX BRACKET] CCXT failed with 50119 for %s — trying direct REST fallback",
                    symbol.okx,
                )
                try:
                    result = await self._direct_place_exit_bracket(
                        symbol=symbol,
                        side=request.side,
                        quantity=qty,
                        tp_price=tp_price,
                        sl_price=sl_price,
                    )
                    algo_id = str(result.get("algoId", ""))
                    logger.info(
                        "[OKX BRACKET DIRECT] %s algoId=%s — bracket placed via direct REST",
                        symbol.okx, algo_id,
                    )
                    return ExitBracketOrder(
                        provider="okx",
                        symbol=symbol,
                        bracket_id=algo_id,
                        tp_order_id=algo_id,
                        sl_order_id=algo_id,
                        status="placed",
                        raw=cast(dict[str, Any], result),
                    )
                except Exception as rest_e:
                    logger.error(
                        "[OKX BRACKET] Direct REST fallback also failed for %s: %s",
                        symbol.okx, rest_e,
                    )
                    # Both failed — raise ExitProtectionError without internal close.
                    # The caller (router) handles emergency close as the single owner.
                    raise ExitProtectionError(
                        f"OKX bracket failed for {symbol.okx}: CCXT error={e}, REST fallback error={rest_e}. "
                        "No emergency close attempted by adapter — caller must handle."
                    ) from rest_e
            else:
                raise ExitProtectionError(
                    f"OKX bracket failed for {symbol.okx}: {e}. "
                    "No emergency close attempted by adapter — caller must handle."
                ) from e

    # ── Open exit orders ──────────────────────────────────────────────────────

    async def get_open_exit_orders(self, symbol: SymbolRef) -> list[ExchangeOrder]:
        try:
            orders = await self.client.fetch_open_orders(symbol.ccxt)
            return [
                ExchangeOrder(
                    provider="okx",
                    symbol=symbol,
                    order_id=str(o.get("id", "")),
                    side=cast(OrderSide, o.get("side") or "buy"),
                    order_type=o.get("type") or "",
                    status=o.get("status") or "",
                    quantity=float(o.get("amount") or 0),
                    filled=float(o.get("filled") or 0),
                    average_price=float(o.get("average") or o.get("price") or 0),
                    commission=0.0,
                    commission_asset=symbol.quote,
                    raw=cast(dict[str, Any], o),
                )
                for o in orders
            ]
        except Exception as e:
            logger.warning("OKX get_open_exit_orders failed for %s: %s", symbol.okx, e)
            return []

    async def cancel_open_exit_orders(self, symbol: SymbolRef) -> None:
        try:
            orders = await self.client.fetch_open_orders(symbol.ccxt)
            for o in orders:
                try:
                    order_id = o.get("id")
                    if order_id:
                        await self.client.cancel_order(order_id, symbol.ccxt)
                except Exception as ce:
                    logger.warning("OKX cancel_order %s failed: %s", o.get("id"), ce)
            if orders:
                logger.info("OKX: cancelled %d open orders for %s", len(orders), symbol.okx)
        except Exception as e:
            logger.warning("OKX cancel_open_exit_orders failed for %s: %s", symbol.okx, e)

    def _get_ccxt_symbol(self, symbol: str) -> str:
        """Convert symbol to CCXT format (e.g., 'BTC-EUR' -> 'BTC/EUR')."""
        return symbol.replace("-", "/")

    async def _direct_fetch_order_detail(self, order_id: str) -> Optional[dict[str, Any]]:
        """Fetch order details via direct OKX REST.

        TEMPORARY: Disabled for OKX EU due to 401/50119 authentication issues.
        """
        # TEMPORARY: Disable all REST fetch attempts for OKX EU due to authentication issues
        logger.debug(f"_direct_fetch_order_detail disabled for {order_id} (OKX EU auth issues)")
        return None

    async def _direct_fetch_closed_orders(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch closed orders via direct OKX REST.

        TEMPORARY: Disabled for OKX EU due to 401/50119 authentication issues.
        """
        # TEMPORARY: Disable all REST fetch attempts for OKX EU due to authentication issues
        logger.debug(f"_direct_fetch_closed_orders disabled for {symbol} (OKX EU auth issues)")
        return []

    async def _fetch_fill_price_by_order_id(self, symbol: str, order_id: str) -> Optional[float]:
        """Recupera il fill price di un ordine specifico tramite orderId.

        Usato da restore sessione per trovare il prezzo di chiusura dell'OCO
        tramite sl_order_id o tp_order_id salvati in DB.

        TEMPORARY: Disabled for OKX EU due to 401/50119 authentication issues.
        Fill price will be recovered via WS private or trade close log.
        """
        # TEMPORARY: Disable all fetch attempts for OKX EU due to authentication issues
        logger.debug(f"_fetch_fill_price_by_order_id disabled for {symbol} orderId={order_id} (OKX EU auth issues)")
        return None

    async def fetch_closed_orders_with_rest_fallback(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch closed orders with REST fallback for OKX EU accounts.

        TEMPORARY: Disabled for OKX EU due to 401/50119 authentication issues.
        """
        # TEMPORARY: Disable all fetch attempts for OKX EU due to authentication issues
        logger.debug(f"fetch_closed_orders_with_rest_fallback disabled for {symbol} (OKX EU auth issues)")
        return []

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_commission(order: dict[str, Any] | Any) -> tuple[float, str | None]:
        """Extract commission from ccxt order response."""
        try:
            # Handle both dict and ccxt Order objects
            order_dict = order if isinstance(order, dict) else dict(order)
            fees_list = order_dict.get("fees") or ([order_dict["fee"]] if order_dict.get("fee") else [])
            fees_by_asset: dict[str, float] = {}
            for f in fees_list:
                if not f:
                    continue
                cost = float(f.get("cost", 0) or 0)
                currency = f.get("currency")
                if currency and cost > 0:
                    fees_by_asset[currency] = fees_by_asset.get(currency, 0.0) + cost
            if fees_by_asset:
                asset, amount = max(fees_by_asset.items(), key=lambda kv: kv[1])
                return amount, asset
        except Exception as e:
            logger.debug("_extract_commission failed: %s", e)
        return 0.0, None

    # ── Factory classmethod ───────────────────────────────────────────────────

    @classmethod
    def from_settings(cls) -> "OkxExchangeAdapter":
        """Build adapter from app settings (TASK-1101 config)."""
        return cls(
            api_key=settings.exchange_api_key,
            secret=settings.exchange_secret_key,
            passphrase=settings.exchange_passphrase,
            demo=settings.exchange_demo,
            base_url=settings.OKX_BASE_URL,
        )
