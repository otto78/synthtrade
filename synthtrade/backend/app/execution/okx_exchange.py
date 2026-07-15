"""
TASK-1164: OkxExchangeAdapter — REST-only adapter for OKX via httpx.

Implements ExchangeAdapterProtocol from exchange_models.py.
Supports Demo Trading (x-simulated-trading: 1) and Live mode.
Base URL must be eea.okx.com for EU accounts.

CCXT removed (TASK-1164): all calls go through direct REST (httpx).
CCXT was failing with 50119 on OKX EU accounts for fetch_balance/fetch_currencies.
BinanceExchangeAdapter remains in standby for when Binance returns to EU.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

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
    ) -> None:
        self.trading_mode = "test" if demo else "live"
        self._demo = demo
        self._base_url = base_url or "https://eea.okx.com"

        self._api_key = api_key
        self._secret = secret
        self._passphrase = passphrase

        self._rules_cache: dict[str, SymbolRules] = {}
        self._rules_cache_ts: dict[str, float] = {}
        self._rules_cache_ttl = 300  # 5 min
        self._price_cache: dict[str, dict[str, Any]] = {}
        self._price_cache_ttl = 15
        self._macro_cache: dict[str, Any] = {"timestamp": 0, "data": None}

    async def close(self) -> None:
        pass  # TASK-1164: CCXT client removed, no resources to close

    # ── Balance ───────────────────────────────────────────────────────────────

    # Task-1162: instance method — uses self._api_key/_secret/_passphrase
    # instead of settings (supports multi-account / custom credentials)
    def _sign_headers(self, method: str, path: str, body: str = "") -> dict:
        """Firma le richieste OKX con il body incluso per POST."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        if body:
            prehash = ts + method + path + body
        else:
            prehash = ts + method + path
        sig = base64.b64encode(
            hmac.new(
                self._secret.encode(),
                prehash.encode(),
                hashlib.sha256,
            ).digest()
        ).decode()
        headers = {
            "OK-ACCESS-KEY": self._api_key,
            "OK-ACCESS-SIGN": sig,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self._passphrase,
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
        """Get available balance for all assets via direct REST (TASK-1164)."""
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
        except Exception as e:
            raise ExchangeOrderError(f"OKX holdings fetch failed: {e}", original_exception=e) from e

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
        """Get ticker price via direct REST (TASK-1164)."""
        now = time.time()
        cached = self._price_cache.get(symbol)
        if cached and (now - cached["ts"]) < self._price_cache_ttl:
            return cached["price"]
        try:
            # Normalize symbol to OKX instId format (BTC-EUR, BTC-USDT, etc.)
            inst_id = symbol.replace("/", "-").upper() if "/" in symbol else symbol.upper()
            path = f"/api/v5/market/ticker?instId={inst_id}"
            url = self._base_url.rstrip("/") + path
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != "0" or not data.get("data"):
                    raise RuntimeError(f"OKX ticker error {data.get('code')}: {data.get('msg')}")
                price = float(data["data"][0].get("last", 0))
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

    async def get_long_short_ratio(self, base_asset: str, period: str = "5m") -> Optional[float]:
        """Long/Short account ratio for the base asset (OKX rubik endpoint).

        Used by LongShortRatioCollector when EXCHANGE_PROVIDER=okx.
        Endpoint is public (no auth):
          GET /api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=<BASE>&period=5m
        Returns a RATIO (long/short), e.g. 2.45 ≈ 71% long / 29% short.
        Returns None on any error or empty data.

        Note: OKX returns a ratio, NOT separate long/short percentages like Binance.
        The collector converts ratio -> long_pct/short_pct via ratio/(1+ratio).
        """
        path = f"/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy={base_asset.upper()}&period={period}"
        url = settings.OKX_BASE_URL.rstrip("/") + path
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") != "0":
                    logger.warning(
                        "OKX long-short-ratio API error %s: %s", data.get("code"), data.get("msg")
                    )
                    return None
                items = data.get("data") or []
                if not items:
                    return None
                # items are [ts_ms, ratio] pairs, most recent first
                latest = items[0]
                ratio = latest[1] if isinstance(latest, (list, tuple)) and len(latest) > 1 else None
                if ratio in (None, ""):
                    return None
                return float(ratio)
        except Exception as e:
            logger.warning("OkxExchangeAdapter.get_long_short_ratio(%s) failed: %s", base_asset, e)
            return None

    # ── Symbol rules ──────────────────────────────────────────────────────────

    async def get_symbol_rules(self, symbol: SymbolRef) -> SymbolRules:
        """Get symbol rules via direct REST (TASK-1164)."""
        key = symbol.okx
        now = time.time()
        cached_ts = self._rules_cache_ts.get(key, 0)
        if key in self._rules_cache and (now - cached_ts) < self._rules_cache_ttl:
            return self._rules_cache[key]

        try:
            rules = await self._direct_fetch_symbol_rules(symbol)
            self._rules_cache[key] = rules
            self._rules_cache_ts[key] = now
            return rules
        except Exception as e:
            raise ExchangeOrderError(f"OKX get_symbol_rules failed for {symbol.okx}: {e}") from e

    # ── Direct REST fallback for symbol rules ─────────────────────────────────

    async def _direct_fetch_symbol_rules(self, symbol: SymbolRef) -> SymbolRules:
        """Fetch OKX symbol rules via direct REST (TASK-1164)."""
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
        """Fetch BTC macro context via direct REST (TASK-1164).

        Uses BTC-USDT (or BTC-EUR if available) for price and changes.
        60-second cache to avoid rate limits.
        """
        now = time.time()
        if now - self._macro_cache.get("timestamp", 0) < 60 and self._macro_cache.get("data"):
            return self._macro_cache["data"]

        try:
            data = await self._direct_fetch_btc_macro_context()
            self._macro_cache["timestamp"] = now
            self._macro_cache["data"] = data
            return data
        except Exception as e:
            logger.warning("Failed to fetch BTC macro context: %s", e)
            return {
                "btc_price_at_entry": 0.0,
                "btc_change_1h_pct": 0.0,
                "btc_change_24h_pct": 0.0,
                "macro_regime": "unknown",
            }

    async def _direct_fetch_btc_macro_context(self) -> Dict[str, Any]:
        """Fetch BTC macro context via direct REST (TASK-1164)."""
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
        """Fetch fee tier via direct REST (TASK-1164).

        OKX returns negative values for rebates (maker=-0.002 means -0.2% rebate).
        For base level accounts (Lv1), we convert to positive since they don't have rebates.
        """
        try:
            return await self._direct_fetch_trade_fee(symbol)
        except Exception as e:
            logger.warning("OKX get_trade_fee failed for %s: %s — using hardcoded fallback", symbol.okx, e)
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
        """Place a market order on OKX via direct REST (TASK-1164)."""
        symbol = request.symbol
        side = request.side
        quantity = request.quantity
        quote_amount = request.quote_amount

        rules = await self.get_symbol_rules(symbol)
        qty = rules.round_qty(quantity) if quantity else 0.0

        if qty <= 0 and not quote_amount:
            raise ExchangeOrderError(f"OKX place_market_order: rounded qty=0 for {symbol.okx}")

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

        # 2. Check regular open orders via direct REST (TASK-1164)
        try:
            path = "/api/v5/trade/orders-pending"
            url = settings.OKX_BASE_URL.rstrip("/") + path
            headers = self._sign_headers("GET", path)
            params = {"instType": "SPOT", "instId": sym_ref.okx}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "0":
                        results.extend(data.get("data", []))
        except Exception as e:
            logger.debug("get_open_orders: regular orders check failed: %s", e)

        return results

    async def get_algo_orders_history(self, symbol: str) -> list[dict[str, Any]]:
        """Return algo orders history for a symbol (OCO/TP/SL fills).

        Used by _on_uds_reconnect_sync to detect if a bracket was executed
        during disconnection. Returns filled/cancelled algo orders.
        
        NOTE: OKX EU accounts may have limited permissions on algo endpoints.
        Falls back to /api/v5/trade/fills endpoint which shows actual fills.
        """
        sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
        results: list[dict] = []

        # Try fills endpoint first (shows actual trade executions)
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
                        if results:
                            return results
        except Exception as e:
            logger.debug("get_algo_orders_history fills fallback failed for %s: %s", symbol, e)

        # Fallback: try orders-history for any filled algo orders
        try:
            path = "/api/v5/trade/orders-history"
            url = settings.OKX_BASE_URL.rstrip("/") + path
            headers = self._sign_headers("GET", path)
            params = {"instType": "SPOT", "instId": sym_ref.okx, "state": "filled"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "0":
                        for order in data.get("data", []):
                            # Check if this is an algo order (has algoId)
                            if order.get("algoId"):
                                results.append({
                                    "algoId": order.get("algoId"),
                                    "state": "effective",
                                    "avgPx": order.get("avgPx"),
                                    "fillPx": order.get("fillPx"),
                                    "ordType": order.get("ordType", "oco"),
                                    "side": order.get("side"),
                                    "instId": order.get("instId"),
                                })
        except Exception as e:
            logger.debug("get_algo_orders_history orders-history fallback failed for %s: %s", symbol, e)

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
        """Place TP/SL bracket on OKX via direct REST (TASK-1164).

        Uses order-algo endpoint (POST /api/v5/trade/order-algo).
        If the adapter fails, raises ExitProtectionError with NO internal
        emergency close — the caller (router) handles emergency close.
        """
        symbol = request.symbol
        try:
            rules = await self.get_symbol_rules(symbol)
            tp_price = rules.round_price(request.tp_price)
            sl_price = rules.round_price(request.sl_price)
            qty = rules.round_qty(request.quantity)

            if qty <= 0:
                raise ExchangeOrderError(f"OKX bracket: rounded qty=0 for {symbol.okx}")

            result = await self._direct_place_exit_bracket(
                symbol=symbol,
                side=request.side,
                quantity=qty,
                tp_price=tp_price,
                sl_price=sl_price,
            )
            algo_id = str(result.get("algoId", ""))
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
                raw=cast(dict[str, Any], result),
            )
        except (ExchangeOrderError, UnsupportedInstrumentError):
            raise
        except Exception as e:
            logger.error("[OKX BRACKET] Failed for %s: %s", symbol.okx, e)
            raise ExitProtectionError(
                f"OKX bracket failed for {symbol.okx}: {e}. "
                "No emergency close attempted by adapter — caller must handle."
            ) from e

    # ── Open exit orders ──────────────────────────────────────────────────────

    async def get_open_exit_orders(self, symbol: SymbolRef) -> list[ExchangeOrder]:
        """Fetch pending regular orders via direct REST (TASK-1164)."""
        try:
            path = "/api/v5/trade/orders-pending"
            url = settings.OKX_BASE_URL.rstrip("/") + path
            headers = self._sign_headers("GET", path)
            params = {"instType": "SPOT", "instId": symbol.okx}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    logger.warning("OKX get_open_exit_orders HTTP %s for %s", resp.status_code, symbol.okx)
                    return []
                data = resp.json()
                if data.get("code") != "0":
                    logger.warning("OKX get_open_exit_orders API error %s for %s", data.get("msg"), symbol.okx)
                    return []
                raw_orders = data.get("data", [])
            return [
                ExchangeOrder(
                    provider="okx",
                    symbol=symbol,
                    order_id=str(o.get("ordId", "")),
                    side=cast(OrderSide, o.get("side") or "buy"),
                    order_type=o.get("ordType") or "",
                    status=o.get("state") or "",
                    quantity=float(o.get("sz") or 0),
                    filled=float(o.get("fillSz") or 0),
                    average_price=float(o.get("avgPx") or 0),
                    commission=0.0,
                    commission_asset=symbol.quote,
                    raw=cast(dict[str, Any], o),
                )
                for o in raw_orders
            ]
        except Exception as e:
            logger.warning("OKX get_open_exit_orders failed for %s: %s", symbol.okx, e)
            return []

    async def cancel_open_exit_orders(self, symbol: SymbolRef) -> None:
        """Cancel all pending regular orders via direct REST (TASK-1164)."""
        try:
            # 1. Fetch pending orders
            path = "/api/v5/trade/orders-pending"
            url = settings.OKX_BASE_URL.rstrip("/") + path
            headers = self._sign_headers("GET", path)
            params = {"instType": "SPOT", "instId": symbol.okx}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    logger.warning("OKX cancel_open_exit_orders fetch HTTP %s for %s", resp.status_code, symbol.okx)
                    return
                data = resp.json()
                if data.get("code") != "0":
                    logger.warning("OKX cancel_open_exit_orders fetch error %s for %s", data.get("msg"), symbol.okx)
                    return
                raw_orders = data.get("data", [])

            if not raw_orders:
                return

            # 2. Cancel each order
            cancelled = 0
            for o in raw_orders:
                order_id = o.get("ordId")
                if not order_id:
                    continue
                try:
                    c_path = "/api/v5/trade/cancel-order"
                    c_url = settings.OKX_BASE_URL.rstrip("/") + c_path
                    c_body = {"instType": "SPOT", "instId": symbol.okx, "ordId": order_id}
                    c_headers = self._sign_headers("POST", c_path, json.dumps(c_body))
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        c_resp = await client.post(c_url, headers=c_headers, json=c_body)
                        if c_resp.status_code == 200 and c_resp.json().get("code") == "0":
                            cancelled += 1
                        else:
                            logger.warning("OKX cancel order %s failed: %s", order_id, c_resp.text)
                except Exception as ce:
                    logger.warning("OKX cancel_order %s failed: %s", order_id, ce)
            if cancelled:
                logger.info("OKX: cancelled %d open orders for %s", cancelled, symbol.okx)
        except Exception as e:
            logger.warning("OKX cancel_open_exit_orders failed for %s: %s", symbol.okx, e)

    async def _direct_fetch_order_detail(self, order_id: str) -> Optional[dict[str, Any]]:
        """Fetch order details via direct OKX REST (TASK-1164)."""
        try:
            path = "/api/v5/trade/order"
            url = settings.OKX_BASE_URL.rstrip("/") + path
            headers = self._sign_headers("GET", path)
            params = {"instType": "SPOT", "ordId": order_id}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "0" and data.get("data"):
                        return data["data"][0]
        except Exception as e:
            logger.debug("_direct_fetch_order_detail failed for %s: %s", order_id, e)
        return None

    async def _direct_fetch_closed_orders(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch closed orders via direct OKX REST (TASK-1164)."""
        sym_ref = SymbolRef.from_okx(symbol) if "-" in symbol else SymbolRef.from_compact(symbol)
        try:
            path = "/api/v5/trade/orders-history-archive"
            url = settings.OKX_BASE_URL.rstrip("/") + path
            headers = self._sign_headers("GET", path)
            params = {"instType": "SPOT", "instId": sym_ref.okx, "limit": str(limit)}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "0":
                        return data.get("data", [])
        except Exception as e:
            logger.debug("_direct_fetch_closed_orders failed for %s: %s", symbol, e)
        return []

    async def _fetch_fill_price_by_order_id(self, symbol: str, order_id: str) -> Optional[float]:
        """Fetch fill price of a specific order via direct OKX REST (TASK-1164).

        Used by session restore to find the closing price of an OCO
        via sl_order_id or tp_order_id saved in DB.
        """
        try:
            path = "/api/v5/trade/fills"
            url = settings.OKX_BASE_URL.rstrip("/") + path
            headers = self._sign_headers("GET", path)
            params = {"instType": "SPOT", "ordId": order_id}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "0" and data.get("data"):
                        fills = data["data"]
                        avg = sum(float(f.get("fillPx", 0)) for f in fills) / len(fills)
                        return avg
        except Exception as e:
            logger.debug("_fetch_fill_price_by_order_id failed for %s orderId=%s: %s", symbol, order_id, e)
        return None

    async def fetch_closed_orders_with_rest_fallback(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch closed orders via direct OKX REST (TASK-1164)."""
        return await self._direct_fetch_closed_orders(symbol, limit)

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
