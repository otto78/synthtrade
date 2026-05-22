import ccxt.async_support as ccxt
from typing import Protocol, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ExchangeOrderError(Exception): pass
class ExchangeAuthError(Exception): pass
class ExchangeNetworkError(Exception): pass

class ExchangeProtocol(Protocol):
    async def get_balance(self) -> float: ...
    async def get_holdings(self) -> Dict[str, float]: ...
    async def get_ticker_price(self, symbol: str) -> float: ...
    async def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]: ...
    async def close_position(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]: ...
    async def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]: ...
    async def get_symbol_filters(self, symbol: str) -> Dict[str, Any]: ...
    async def place_oco_order(self, symbol: str, side: str, quantity: float,
                              price: float, stop_price: float,
                              take_profit_price: float | None = None) -> Dict[str, Any]: ...
    async def place_stop_loss_order(self, symbol: str, side: str,
                                    quantity: float, stop_price: float) -> Dict[str, Any]: ...
    async def place_limit_order(self, symbol: str, side: str,
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

    async def close(self):
        await self.client.close()

    async def get_holdings(self) -> Dict[str, float]:
        """
        TASK-413: Restituisce saldo libero di tutte le asset nel wallet.
        Esclude asset con balance = 0.
        Esempio: { "BTC": 0.015, "ETH": 0.5, "USDT": 1200.0 }
        """
        try:
            balance = await self.client.fetch_balance()
            free = balance.get("free", {})
            return {asset: float(qty) for asset, qty in free.items() if float(qty or 0) > 0}
        except ccxt.AuthenticationError as e:
            raise ExchangeAuthError(f"Auth error: {e}")
        except ccxt.NetworkError as e:
            raise ExchangeNetworkError(f"Network error: {e}")
        except Exception as e:
            raise ExchangeOrderError(str(e))

    async def get_balance(self) -> float:
        try:
            balance = await self.client.fetch_balance()
            return float(balance["free"].get("USDT", 0.0))
        except ccxt.AuthenticationError as e:
            raise ExchangeAuthError(f"Auth error: {e}")
        except ccxt.NetworkError as e:
            raise ExchangeNetworkError(f"Network error: {e}")
        except Exception as e:
            raise ExchangeOrderError(str(e))

    async def get_ticker_price(self, symbol: str) -> float:
        ticker = await self.client.fetch_ticker(symbol)
        return float(ticker["last"])

    async def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        try:
            order = await self.client.create_order(
                symbol=symbol,
                type="market",
                side=side.lower(),
                amount=quantity
            )
            return {
                "order_id": order["id"],
                "status": order["status"],
                "price": order.get("price") or order.get("average"),
                "quantity": order["amount"]
            }
        except ccxt.InsufficientFunds as e:
            raise ExchangeOrderError(f"Insufficient funds: {e}")
        except Exception as e:
            raise ExchangeOrderError(str(e))

    async def close_position(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        # Per chiudere una posizione BUY (long), vendiamo (SELL)
        # Per chiudere una posizione SELL (short), compriamo (BUY)
        opp_side = "sell" if side.upper() == "BUY" else "buy"
        return await self.place_market_order(symbol, opp_side, quantity)

    async def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        orders = await self.client.fetch_open_orders(symbol)
        return orders

    async def get_symbol_filters(self, symbol: str) -> Dict[str, Any]:
        """
        TASK-089: Recupera filtri LOT_SIZE e MIN_NOTIONAL
        """
        if symbol in self._filters_cache:
            return self._filters_cache[symbol]

        markets = await self.client.load_markets()
        if symbol not in markets:
            raise ValueError(f"Symbol {symbol} not found on Binance")

        market = markets[symbol]
        filters = {
            "stepSize": market["precision"]["amount"],
            "minQty": market["limits"]["amount"]["min"],
            "minNotional": market["limits"]["cost"]["min"]
        }
        self._filters_cache[symbol] = filters
        return filters

    # ── TASK-801: OCO, Stop Loss, Limit Orders ─────────────────────────

    async def place_oco_order(self, symbol: str, side: str, quantity: float,
                              price: float, stop_price: float,
                              take_profit_price: float | None = None) -> Dict[str, Any]:
        """
        TASK-801: Piazzare un ordine OCO (One-Cancels-Other).

        Prova prima con l'ordine OCO nativo CCXT.
        Se fallisce (es. Binance spot non supporta OCO via CCXT),
        usa un synthetic OCO: market order + stop loss separato.
        """
        try:
            params: dict = {
                "type": "oco",
                "price": price,
                "stopPrice": stop_price,
                "takeProfitPrice": take_profit_price,
                "amount": quantity,
            }
            order = await self.client.create_order(
                symbol,
                "oco",
                side.lower(),
                quantity,
                price,
                params=params,
            )
            return {
                "order_id": order.get("id", "unknown"),
                "type": "oco",
                "status": order.get("status", "unknown"),
                "price": order.get("price", price),
                "stop_price": stop_price,
                "take_profit_price": take_profit_price,
                "quantity": order.get("amount", quantity),
            }
        except Exception as oco_err:
            logger.warning(f"OCO non supportato per {symbol}, fallback synthetic: {oco_err}")
            return await self._place_oco_synthetic(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_price=stop_price,
                take_profit_price=take_profit_price,
            )

    async def _place_oco_synthetic(self, symbol: str, side: str,
                                    quantity: float, price: float,
                                    stop_price: float,
                                    take_profit_price: float | None = None) -> Dict[str, Any]:
        """
        Synthetic OCO: place market order + stop loss + limit take profit.
        """
        main_order = await self.place_market_order(symbol, side, quantity)
        sl_result = await self.place_stop_loss_order(
            symbol=symbol,
            side="sell" if side.lower() == "buy" else "buy",
            quantity=quantity,
            stop_price=stop_price,
        )
        tp_result = None
        if take_profit_price:
            tp_result = await self.place_limit_order(
                symbol=symbol,
                side="sell" if side.lower() == "buy" else "buy",
                quantity=quantity,
                limit_price=take_profit_price,
            )
        return {
            "type": "oco_synthetic",
            "main_order_id": main_order.get("order_id"),
            "stop_loss_id": sl_result.get("order_id"),
            "take_profit_id": tp_result.get("order_id") if tp_result else None,
            "status": "placed",
        }

    async def place_stop_loss_order(self, symbol: str, side: str,
                                    quantity: float, stop_price: float) -> Dict[str, Any]:
        """
        TASK-801: Piazzare uno stop loss order.

        Usa stop_market (o stop_loss) di CCXT per piazzare
        un ordine che si attiva quando il prezzo raggiunge stop_price.
        """
        try:
            order = await self.client.create_order(
                symbol=symbol,
                type="stop_market",
                side=side.lower(),
                amount=quantity,
                params={"stopPrice": stop_price},
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

    async def place_limit_order(self, symbol: str, side: str,
                                quantity: float, limit_price: float) -> Dict[str, Any]:
        """
        TASK-801: Piazzare un limit order.

        Usato come take profit (limit sell per long position).
        """
        try:
            order = await self.client.create_order(
                symbol=symbol,
                type="limit",
                side=side.lower(),
                amount=quantity,
                price=limit_price,
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
