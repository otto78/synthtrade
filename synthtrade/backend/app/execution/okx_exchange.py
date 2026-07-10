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
from typing import Any, Dict, Optional, cast

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

    async def _direct_fetch_balance(self) -> list[dict]:
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
            return {asset: float(amt) for asset, amt in free.items() if float(amt or 0) > 0}
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
            price = float(ticker["last"])
            self._price_cache[symbol] = {"price": price, "ts": now}
            return price
        except Exception as e:
            if cached:
                logger.warning("get_ticker_price(%s) stale cache fallback: %s", symbol, e)
                return cached["price"]
            raise ExchangeOrderError(f"OKX ticker fetch failed for {symbol}: {e}") from e

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

            info = market.get("info", {})
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
            info = instruments[0]
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

            price = float(ticker.get("last", 0.0))
            change_24h_pct = float(ticker.get("percentage", 0.0))

            # Klines 1h for 1h change
            klines = await self.client.fetch_ohlcv(btc_symbol, timeframe="1h", limit=2)
            change_1h_pct = 0.0
            if len(klines) >= 2:
                close_prev = float(klines[0][4])
                close_now = float(klines[1][4])
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
                    ticker = ticker_data.get("data", [{}])[0]
                    price = float(ticker.get("last", 0.0))
                    change_24h_pct = float(ticker.get("chg", 0.0)) * 100

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

                change_1h_pct = 0.0
                if len(candles) >= 2:
                    close_prev = float(candles[1][4])  # OKX candles are newest-first
                    close_now = float(candles[0][4])
                    if close_prev > 0:
                        change_1h_pct = ((close_now - close_prev) / close_prev) * 100

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
            maker = float(fee_data[0].get("maker", 0.001))
            taker = float(fee_data[0].get("taker", 0.001))
            logger.info(
                "[OKX FEE DIRECT] %s maker=%.4f taker=%.4f (negative=rebate)",
                symbol.okx, maker, taker,
            )
            return FeeTier(
                maker=maker,
                taker=taker,
                certified=True,
                source="okx_trade_fee_direct",
                raw=fee_data[0],
            )

    async def get_trade_fee(self, symbol: SymbolRef) -> FeeTier:
        """
        Fetch fee tier from OKX GET /api/v5/account/trade-fee.

        OKX returns negative values for rebates (maker=-0.002 means -0.2% rebate).
        We preserve the sign: negative = rebate (exchange pays you).
        Falls back to direct REST if CCXT fails (50119 on EU accounts).
        """
        try:
            response = await self.client.fetch_trading_fee(symbol.ccxt)
            if not response or response.get("maker") is None:
                logger.warning("OKX get_trade_fee: empty response for %s", symbol.ccxt)
                return await self._direct_fetch_trade_fee(symbol)

            maker = float(response["maker"])
            taker = float(response["taker"])
            logger.info(
                "[OKX FEE] %s maker=%.4f taker=%.4f (negative=rebate)",
                symbol.ccxt, maker, taker,
            )
            return FeeTier(
                maker=maker,
                taker=taker,
                certified=True,
                source="okx_trade_fee",
                raw=response,
            )
        except Exception as e:
            logger.warning("OKX get_trade_fee failed for %s: %s — trying direct REST fallback", symbol.ccxt, e)
            try:
                return await self._direct_fetch_trade_fee(symbol)
            except Exception as fallback_e:
                logger.error("OKX get_trade_fee direct fallback also failed: %s — using hardcoded fallback", fallback_e)
                return _FALLBACK_FEE

    # ── Orders ────────────────────────────────────────────────────────────────

    async def _direct_place_market_order(self, symbol: SymbolRef, side: str, quantity: float, quote_amount: Optional[float] = None) -> dict:
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
        """
        Place a spot market order on OKX.

        Uses tdMode=cash for spot. If quote_amount is set, uses tgtCcy=quote_ccy
        so OKX handles the base quantity calculation internally.
        """
        symbol = request.symbol
        rules: SymbolRules | None = None
        try:
            rules = await self.get_symbol_rules(symbol)
            params: dict[str, Any] = {"tdMode": "cash"}

            if request.quote_amount and request.side == "buy":
                # Buy with quote amount (e.g. spend 10 EUR to buy BTC)
                params["tgtCcy"] = "quote_ccy"
                qty = request.quote_amount
            else:
                qty = rules.round_qty(request.quantity)
                if qty <= 0:
                    raise ExchangeOrderError(f"OKX: rounded qty=0 for {symbol.okx}")

            order = await self.client.create_order(
                symbol=symbol.ccxt,
                type="market",
                side=request.side,
                amount=qty,
                params=params,
            )

            commission, commission_asset = self._extract_commission(order)
            logger.info(
                "[OKX ORDER] %s %s qty=%s avg=%s commission=%s %s",
                request.side, symbol.okx, qty,
                order.get("average"), commission, commission_asset,
            )

            return ExchangeOrder(
                provider="okx",
                symbol=symbol,
                order_id=str(order.get("id", "")),
                side=request.side,
                order_type="market",
                status=order.get("status", "unknown"),
                quantity=float(order.get("amount") or qty),
                filled=float(order.get("filled") or 0),
                average_price=float(order.get("average") or order.get("price") or 0),
                commission=commission,
                commission_asset=commission_asset or symbol.quote,
                raw=order,
            )
        except (ExchangeOrderError, UnsupportedInstrumentError):
            raise
        except ccxt.InsufficientFunds as e:
            raise ExchangeOrderError(f"OKX insufficient funds: {e}", original_exception=e) from e
        except Exception as e:
            # Se CCXT fallisce con 50119, usa il fallback REST diretto
            if "50119" in str(e) or "API key doesn't exist" in str(e):
                logger.warning(f"CCXT create_order failed with 50119, using direct REST fallback for {symbol.okx}")
                try:
                    qty_val: float = request.quote_amount if request.quote_amount and request.side == "buy" else (rules.round_qty(request.quantity) if rules else request.quantity)
                    order_data = await self._direct_place_market_order(symbol, request.side, qty_val, request.quote_amount)
                    return ExchangeOrder(
                        provider="okx",
                        symbol=symbol,
                        order_id=str(order_data.get("ordId", "")),
                        side=request.side,
                        order_type="market",
                        status="filled" if order_data.get("state") == "filled" else "open",
                        quantity=float(order_data.get("sz", qty_val)),
                        filled=float(order_data.get("accFillSz", 0)),
                        average_price=float(order_data.get("avgPx", 0)),
                        commission=float(order_data.get("fee", 0)),
                        commission_asset=symbol.quote,
                        raw=order_data,
                    )
                except Exception as rest_e:
                    raise ExchangeOrderError(f"OKX market order failed (REST fallback also failed): {rest_e}", original_exception=rest_e) from rest_e
            raise ExchangeOrderError(f"OKX market order failed: {e}", original_exception=e) from e

    async def close_position(self, request: ClosePositionRequest) -> ExchangeOrder:
        opp_side: OrderSide = "sell" if request.side == "buy" else "buy"
        return await self.place_market_order(
            MarketOrderRequest(symbol=request.symbol, side=opp_side, quantity=request.quantity)
        )

    # ── Exit bracket (TP/SL algo order) ──────────────────────────────────────

    async def place_exit_bracket(self, request: ExitBracketRequest) -> ExitBracketOrder:
        """
        Place TP/SL bracket on OKX using order-algo (POST /api/v5/trade/order-algo).

        Uses attachAlgoOrds approach via ccxt create_order with params.
        If bracket placement fails, executes emergency market close and raises
        ExitProtectionError — no open position is left unprotected.

        NOTE: TASK-1100.F (bracket spike) is still pending. This implementation
        uses the most common OKX algo approach; validate in Demo Trading before
        enabling in live mode.
        """
        symbol = request.symbol
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
                raw=order,
            )

        except (ExchangeOrderError, UnsupportedInstrumentError):
            # Re-raise without emergency close — caller decides
            raise
        except Exception as e:
            logger.error(
                "[OKX BRACKET FAILED] %s: %s — executing emergency market close",
                symbol.okx, e,
            )
            # Emergency close: never leave an open position without protection
            try:
                await self.close_position(
                    ClosePositionRequest(
                        symbol=symbol,
                        side=request.side,
                        quantity=request.quantity,
                    )
                )
                logger.info("[OKX EMERGENCY CLOSE] executed for %s", symbol.okx)
            except Exception as close_e:
                logger.error("[OKX EMERGENCY CLOSE FAILED] %s: %s", symbol.okx, close_e)
            raise ExitProtectionError(
                f"OKX bracket failed for {symbol.okx}: {e}. Emergency close attempted."
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
                    side=o.get("side", ""),
                    order_type=o.get("type", ""),
                    status=o.get("status", ""),
                    quantity=float(o.get("amount") or 0),
                    filled=float(o.get("filled") or 0),
                    average_price=float(o.get("average") or o.get("price") or 0),
                    commission=0.0,
                    commission_asset=symbol.quote,
                    raw=o,
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
                    await self.client.cancel_order(o["id"], symbol.ccxt)
                except Exception as ce:
                    logger.warning("OKX cancel_order %s failed: %s", o.get("id"), ce)
            if orders:
                logger.info("OKX: cancelled %d open orders for %s", len(orders), symbol.okx)
        except Exception as e:
            logger.warning("OKX cancel_open_exit_orders failed for %s: %s", symbol.okx, e)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_commission(order: dict[str, Any]) -> tuple[float, str | None]:
        """Extract commission from ccxt order response."""
        try:
            fees_list = order.get("fees") or ([order["fee"]] if order.get("fee") else [])
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
