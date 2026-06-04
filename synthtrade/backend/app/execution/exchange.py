import ccxt.async_support as ccxt
from typing import Protocol, Dict, Any, List, Literal, cast
import logging

logger = logging.getLogger(__name__)

OrderSide = Literal["buy", "sell"]
OrderType = Literal["limit", "market", "stop_loss_limit"]

class ExchangeOrderError(Exception): pass
class ExchangeAuthError(Exception): pass
class ExchangeNetworkError(Exception): pass

class ExchangeProtocol(Protocol):
    async def get_balance(self, asset: str = "USDT") -> float: ...
    async def get_holdings(self) -> Dict[str, float]: ...
    async def get_ticker_price(self, symbol: str) -> float: ...
    async def place_market_order(self, symbol: str, side: OrderSide, quantity: float) -> Dict[str, Any]: ...
    async def close_position(self, symbol: str, side: OrderSide, quantity: float) -> Dict[str, Any]: ...
    async def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]: ...
    async def get_symbol_filters(self, symbol: str) -> Dict[str, Any]: ...
    async def place_oco_order(self, symbol: str, side: OrderSide, quantity: float,
                              price: float, stop_price: float,
                              take_profit_price: float | None = None) -> Dict[str, Any]: ...
    async def place_stop_loss_order(self, symbol: str, side: OrderSide,
                                    quantity: float, stop_price: float) -> Dict[str, Any]: ...
    async def place_limit_order(self, symbol: str, side: OrderSide,
                                quantity: float, limit_price: float) -> Dict[str, Any]: ...

class BinanceExchangeAdapter:
    """
    TASK-082, TASK-083: Implementazione BinanceExchangeAdapter via CCXT
    TASK-413: Aggiunto get_holdings()
    """
    def __init__(self, api_key: str, secret: str, testnet: bool = True, client=None):
        if client:
            self.client = client
        else:
            self.client = ccxt.binance({
                "apiKey": api_key,
                "secret": secret,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                },
            })
            if testnet:
                self.client.set_sandbox_mode(True)
                # Forza gli URL per evitare redirect su Future (bug CCXT 4.3.90+)
                vision_url = "https://testnet.binance.vision/api/v3"
                if self.client.urls and isinstance(self.client.urls, dict):
                    self.client.urls["api"] = {
                        "public": vision_url,
                        "private": vision_url,
                        "v3": vision_url,
                        "v1": vision_url,
                        "sapi": vision_url,
                        "fapiPublic": vision_url,
                        "fapiPrivate": vision_url,
                        "dapiPublic": vision_url,
                        "dapiPrivate": vision_url,
                    }
            else:
                self.client.set_sandbox_mode(False)
        self._filters_cache = {}
        self._symbol_cache = {}

    async def close(self):
        await self.client.close()

    async def get_holdings(self) -> Dict[str, float]:
        try:
            balance = await self.client.fetch_balance()
            return {asset: float(data["free"]) for asset, data in balance["total"].items() if float(data["free"]) > 0}
        except Exception as e:
            raise ExchangeOrderError(f"Holdings fetch failed: {e}")

    async def get_balance(self, asset: str = "USDT") -> float:
        try:
            balance = await self.client.fetch_balance()
            free_bal = balance.get("free", {})
            return float(free_bal.get(asset, 0.0))
        except ccxt.AuthenticationError as e:
            raise ExchangeAuthError(f"Auth error: {e}")
        except ccxt.NetworkError as e:
            raise ExchangeNetworkError(f"Network error: {e}")
        except Exception as e:
            raise ExchangeOrderError(str(e))

    async def _get_ccxt_symbol(self, symbol: str) -> str:
        """Cache-backed symbol resolver."""
        if symbol in self._symbol_cache:
            return self._symbol_cache[symbol]

        markets = await self.client.load_markets()
        if symbol in markets:
            self._symbol_cache[symbol] = symbol
            return symbol

        # ID-based lookup (e.g. BNBUSDC -> BNB/USDC)
        for ccxt_id, market in markets.items():
            if market.get("id") == symbol:
                self._symbol_cache[symbol] = ccxt_id
                return ccxt_id

        # Fallback: if we have filters, baseAsset/quoteAsset might be there
        try:
            filters = await self.get_symbol_filters(symbol)
            ccxt_id = f"{filters['baseAsset']}/{filters['quoteAsset']}"
            self._symbol_cache[symbol] = ccxt_id
            return ccxt_id
        except:
            pass

        return symbol

    async def get_ticker_price(self, symbol: str) -> float:
        ccxt_symbol = await self._get_ccxt_symbol(symbol)
        ticker = await self.client.fetch_ticker(ccxt_symbol)
        return float(ticker["last"])

    async def place_market_order(self, symbol: str, side: OrderSide, quantity: float) -> Dict[str, Any]:
        try:
            ccxt_symbol = await self._get_ccxt_symbol(symbol)
            order = await self.client.create_order(
                symbol=ccxt_symbol,
                type="market",
                side=side.lower(),
                amount=quantity
            )
            return cast(Dict[str, Any], order)
        except ccxt.InsufficientFunds as e:
            raise ExchangeOrderError(f"Insufficient funds: {e}")
        except Exception as e:
            raise ExchangeOrderError(str(e))

    async def close_position(self, symbol: str, side: OrderSide, quantity: float) -> Dict[str, Any]:
        # Per chiudere una posizione SELL (short), compriamo (BUY)
        opp_side: OrderSide = "sell" if side == "buy" else "buy"
        return await self.place_market_order(symbol, opp_side, quantity)

    async def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        ccxt_symbol = await self._get_ccxt_symbol(symbol)
        orders = await self.client.fetch_open_orders(ccxt_symbol)
        return cast(List[Dict[str, Any]], orders)

    async def get_symbol_filters(self, symbol: str) -> Dict[str, Any]:
        """
        TASK-089: Recupera filtri LOT_SIZE e MIN_NOTIONAL.
        Returns stepSize, minQty, minNotional as floats, plus pricePrecision.
        """
        if symbol in self._filters_cache:
            return self._filters_cache[symbol]

        markets = await self.client.load_markets()
        if symbol not in markets:
            # Try with slash format (e.g. BNB/USDC)
            slash_symbol = None
            for mk in markets:
                if markets[mk]["id"] == symbol:
                    slash_symbol = mk
                    break
            if not slash_symbol:
                raise ValueError(f"Symbol {symbol} not found on Binance")
            market = markets[slash_symbol]
        else:
            market = markets[symbol]

        # CCXT precision.amount = number of decimals for quantity
        # Convert to stepSize: e.g. precision 2 → stepSize 0.01
        qty_precision = market["precision"]["amount"]
        step_size = 10 ** (-qty_precision) if isinstance(qty_precision, (int, float)) else 0.001

        price_precision = market["precision"]["price"]
        tick_size = 10 ** (-price_precision) if isinstance(price_precision, (int, float)) else 0.01

        filters = {
            "stepSize": step_size,
            "minQty": market["limits"]["amount"]["min"] or step_size,
            "minNotional": market["limits"]["cost"]["min"] or 1.0,
            "pricePrecision": price_precision,
            "tickSize": tick_size,
            "quoteAsset": market["quote"],
            "baseAsset": market["base"],
        }
        self._filters_cache[symbol] = filters
        return filters

    # ── TASK-801: OCO, Stop Loss, Limit Orders ─────────────────────────

    async def place_oco_order(self, symbol: str, side: OrderSide, quantity: float,
                              price: float, stop_price: float,
                              take_profit_price: float | None = None) -> Dict[str, Any]:
        """
        TASK-801: Place OCO (One-Cancels-Other) on Binance Spot.

        For a BUY entry → OCO SELL: price = TP (limit sell), stopPrice = SL trigger.
        Uses Binance's native /api/v3/order/oco endpoint.
        Falls back to synthetic (SL + TP as separate orders) if OCO fails.
        """
        # stopLimitPrice: the actual limit price after stop triggers (slightly worse than stopPrice)
        slippage = 0.001  # 0.1% slippage buffer
        if side.lower() == "sell":
            stop_limit_price = round(stop_price * (1 - slippage), 8)
        else:
            stop_limit_price = round(stop_price * (1 + slippage), 8)

        try:
            ccxt_symbol = await self._get_ccxt_symbol(symbol)
            side_cast = cast(Literal["buy", "sell"], side.lower())
            order = await self.client.create_order(
                ccxt_symbol,
                "limit",  # the limit (TP) leg type
                side_cast,
                quantity,
                price,          # TP limit price
                params={
                    "stopPrice": stop_price,
                    "stopLimitPrice": stop_limit_price,
                    "stopLimitTimeInForce": "GTC",
                    "type": "oco",
                },
            )
            logger.info(f"OCO order placed: {order.get('id', 'unknown')} for {symbol}")
            return {
                "order_id": order.get("id", "unknown"),
                "type": "oco",
                "status": order.get("status", "unknown"),
                "price": price,
                "stop_price": stop_price,
                "take_profit_price": take_profit_price or price,
                "quantity": quantity,
            }
        except Exception as oco_err:
            logger.warning(f"OCO nativo fallito per {symbol}, fallback synthetic: {oco_err}")
            return await self._place_oco_synthetic(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_price=stop_price,
                take_profit_price=take_profit_price,
            )

    async def _place_oco_synthetic(self, symbol: str, side: OrderSide, quantity: float,
                                    price: float, stop_price: float,
                                    take_profit_price: float | None = None) -> Dict[str, Any]:
        """
        Synthetic OCO: stop loss (STOP_LOSS_LIMIT) + take profit (LIMIT) as separate orders.
        NOTE: these are NOT truly linked — both could theoretically fill. The main loop
        should cancel the remaining order when either fills.
        """
        sl_result = await self.place_stop_loss_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
        )
        tp_result = None
        if take_profit_price:
            tp_result = await self.place_limit_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                limit_price=take_profit_price,
            )
        return {
            "type": "oco_synthetic",
            "order_id": sl_result.get("order_id"),
            "stop_loss_id": sl_result.get("order_id"),
            "take_profit_id": tp_result.get("order_id") if tp_result else None,
            "status": "placed",
        }

    async def place_stop_loss_order(self, symbol: str, side: OrderSide, quantity: float, stop_price: float) -> Dict[str, Any]:
        """
        TASK-801: Place a STOP_LOSS_LIMIT order.
        """
        # slippage buffer for stop limit
        slippage = 0.001
        if side.lower() == "sell":
            stop_limit_price = round(stop_price * (1 - slippage), 8)
        else:
            stop_limit_price = round(stop_price * (1 + slippage), 8)

        try:
            ccxt_symbol = await self._get_ccxt_symbol(symbol)
            side_cast = cast(Literal["buy", "sell"], side.lower())
            order_type_cast = cast(Any, "STOP_LOSS_LIMIT")
            order = await self.client.create_order(
                ccxt_symbol,
                order_type_cast,
                side_cast,
                quantity,
                stop_limit_price,
                params={"stopPrice": stop_price}
            )
            return {
                "order_id": order.get("id", "unknown"),
                "type": "stop_loss",
                "status": order.get("status", "unknown"),
                "stop_price": stop_price,
                "quantity": order.get("amount", quantity),
            }
        except Exception as e:
            raise ExchangeOrderError(f"Stop loss failed for {symbol}: {e}")

    async def place_limit_order(self, symbol: str, side: OrderSide,
                                quantity: float, limit_price: float) -> Dict[str, Any]:
        """
        TASK-801: Place a standard LIMIT order.
        """
        try:
            ccxt_symbol = await self._get_ccxt_symbol(symbol)
            side_cast = cast(Literal["buy", "sell"], side.lower())
            order = await self.client.create_order(
                ccxt_symbol,
                "limit",
                side_cast,
                quantity,
                limit_price
            )
            return {
                "order_id": order.get("id", "unknown"),
                "type": "limit",
                "status": order.get("status", "unknown"),
                "price": order.get("price", limit_price),
                "quantity": order.get("amount", quantity),
            }
        except Exception as e:
            raise ExchangeOrderError(f"Limit order failed for {symbol}: {e}")
