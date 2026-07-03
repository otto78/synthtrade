"""
TASK-1103: OkxExchangeAdapter — REST adapter for OKX via ccxt.

Implements ExchangeAdapterProtocol from exchange_models.py.
Supports Demo Trading (x-simulated-trading: 1) and Live mode.
Base URL must be eea.okx.com for EU accounts.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import ccxt.async_support as ccxt

from app.execution.exchange_models import (
    ClosePositionRequest,
    ExchangeOrder,
    ExitBracketOrder,
    ExitBracketRequest,
    ExitProtectionError,
    FeeTier,
    MarketOrderRequest,
    SymbolRef,
    SymbolRules,
    UnsupportedInstrumentError,
)
from app.execution.exchange import ExchangeOrderError, ExchangeAuthError, ExchangeNetworkError

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
            # Use isinstance guard to skip None values in urls["api"] dict
            if base_url and "eea.okx.com" in base_url:
                self.client.urls["api"] = {
                    k: v.replace("www.okx.com", "eea.okx.com") if isinstance(v, str) else v
                    for k, v in self.client.urls.get("api", {}).items()
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

    async def close(self) -> None:
        await self.client.close()

    # ── Balance ───────────────────────────────────────────────────────────────

    async def get_holdings(self) -> dict[str, float]:
        try:
            balance = await self.client.fetch_balance()
            free = balance.get("free", {})
            return {asset: float(amt) for asset, amt in free.items() if float(amt or 0) > 0}
        except ccxt.AuthenticationError as e:
            raise ExchangeAuthError(f"OKX auth error: {e}") from e
        except Exception as e:
            raise ExchangeOrderError(f"OKX holdings fetch failed: {e}", original_exception=e) from e

    async def get_balance(self, asset: str = "EUR") -> float:
        try:
            balance = await self.client.fetch_balance()
            return float(balance.get("free", {}).get(asset, 0.0))
        except ccxt.AuthenticationError as e:
            raise ExchangeAuthError(f"OKX auth error: {e}") from e
        except ccxt.NetworkError as e:
            raise ExchangeNetworkError(f"OKX network error: {e}") from e
        except Exception as e:
            raise ExchangeOrderError(f"OKX balance fetch failed: {e}", original_exception=e) from e

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
            raise ExchangeOrderError(f"OKX get_symbol_rules failed for {symbol.okx}: {e}") from e

    # ── Fee tier ──────────────────────────────────────────────────────────────

    async def get_trade_fee(self, symbol: SymbolRef) -> FeeTier:
        """
        Fetch fee tier from OKX GET /api/v5/account/trade-fee.

        OKX returns negative values for rebates (maker=-0.002 means -0.2% rebate).
        We preserve the sign: negative = rebate (exchange pays you).
        """
        try:
            response = await self.client.fetch_trading_fee(symbol.ccxt)
            if not response or response.get("maker") is None:
                logger.warning("OKX get_trade_fee: empty response for %s", symbol.ccxt)
                return _FALLBACK_FEE

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
            logger.error("OKX get_trade_fee failed for %s: %s — using fallback", symbol.ccxt, e)
            return _FALLBACK_FEE

    # ── Orders ────────────────────────────────────────────────────────────────

    async def place_market_order(self, request: MarketOrderRequest) -> ExchangeOrder:
        """
        Place a spot market order on OKX.

        Uses tdMode=cash for spot. If quote_amount is set, uses tgtCcy=quote_ccy
        so OKX handles the base quantity calculation internally.
        """
        symbol = request.symbol
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
            raise ExchangeOrderError(f"OKX market order failed: {e}", original_exception=e) from e

    async def close_position(self, request: ClosePositionRequest) -> ExchangeOrder:
        opp_side = "sell" if request.side == "buy" else "buy"
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
                type="oco",
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
        from app.config import settings
        return cls(
            api_key=settings.exchange_api_key,
            secret=settings.exchange_secret_key,
            passphrase=settings.exchange_passphrase,
            demo=settings.exchange_demo,
            base_url=settings.OKX_BASE_URL,
        )
