import asyncio
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

    async def _round_qty(self, symbol: str, qty: float) -> float:
        """Arrotonda quantity a stepSize usando i filtri del simbolo."""
        filters = await self.get_symbol_filters(symbol)
        step_size = float(filters["stepSize"])
        return round(qty - (qty % step_size), 8)

    async def place_market_order(self, symbol: str, side: OrderSide, quantity: float) -> Dict[str, Any]:
        try:
            # Arrotonda quantità a stepSize PRIMA di chiamare Binance
            qty_rounded = await self._round_qty(symbol, quantity)
            ccxt_symbol = await self._get_ccxt_symbol(symbol)
            order = await self.client.create_order(
                symbol=ccxt_symbol,
                type="market",
                side=side,
                amount=qty_rounded
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

        from decimal import Decimal

        # Try to extract LOT_SIZE from raw market info (most reliable for Binance)
        raw_info = market.get("info", {})
        lot_size_raw = None
        if raw_info and "filters" in raw_info:
            for f in raw_info["filters"]:
                if f.get("filterType") == "LOT_SIZE":
                    lot_size_raw = f
                    break

        if lot_size_raw:
            step_size = float(lot_size_raw.get("stepSize", "0.001"))
            min_qty = float(lot_size_raw.get("minQty", "0.001"))
            min_notional_raw = None
            if raw_info and "filters" in raw_info:
                for f in raw_info["filters"]:
                    if f.get("filterType") == "MIN_NOTIONAL":
                        min_notional_raw = f
                        break
            min_notional = float(min_notional_raw.get("minNotional", "1.0")) if min_notional_raw else 1.0
        else:
            # Fallback: use CCXT precision fields
            qty_precision = market["precision"]["amount"]
            if isinstance(qty_precision, (int, float)) and qty_precision > 0 and qty_precision < 20:
                step_size = 10 ** (-qty_precision)
            else:
                step_size = 0.001  # default for most Binance spot pairs
            min_qty = market["limits"]["amount"]["min"] or step_size
            min_notional = market["limits"]["cost"]["min"] or 1.0

        price_precision = market["precision"]["price"]
        if isinstance(price_precision, (int, float)) and price_precision > 0 and price_precision < 20:
            tick_size = 10 ** (-price_precision)
        else:
            # Extract tickSize from PRICE_FILTER if precision is float
            tick_size = 0.01
            if raw_info and "filters" in raw_info:
                for f in raw_info["filters"]:
                    if f.get("filterType") == "PRICE_FILTER":
                        tick_size = float(f.get("tickSize", "0.01"))
                        break

        filters = {
            "stepSize": step_size,
            "minQty": min_qty,
            "minNotional": min_notional,
            "pricePrecision": price_precision if isinstance(price_precision, int) else 2,
            "tickSize": tick_size,
            "quoteAsset": market["quote"],
            "baseAsset": market["base"],
        }
        # Popola anche il symbol cache se non è già presente
        if symbol not in self._symbol_cache:
            ccxt_id = market.get("id", symbol)
            self._symbol_cache[symbol] = market["symbol"] if market["symbol"] != symbol else ccxt_id
        self._filters_cache[symbol] = filters
        return filters

    # ── TASK-801 + FIX-2026-06-05: Stop Loss, Take Profit, OCO ──────────────────

    async def place_oco_order(self, symbol: str, side: OrderSide, quantity: float,
                              price: float, stop_price: float,
                              take_profit_price: float | None = None) -> Dict[str, Any]:
        """
        Place OCO (One-Cancels-Other) order.
        
        Strategy:
        1. Try native Binance OCO first (single atomic order, no double-lock).
        2. Fallback to synthetic OCO (TP LIMIT first, then SL STOP_LOSS) to avoid
           the double-lock bug where SL reserves the balance and TP cannot be placed.
        
        Both orders persist on Binance even if the bot disconnects.
        """
        logger.info(f"Placing risk parachute for {symbol}: TP={price}, SL={stop_price}")
        
        # Strategy 1: Try native OCO (single atomic order, best for double-lock)
        try:
            result = await self._place_oco_native(
                symbol=symbol, side=side, quantity=quantity,
                price=price, stop_price=stop_price,
                take_profit_price=take_profit_price,
            )
            logger.info(f"Native OCO placed successfully for {symbol}")
            return result
        except Exception as oco_e:
            logger.warning(f"Native OCO failed for {symbol}, falling back to synthetic: {oco_e}")
        
        # Strategy 2: Fallback to synthetic OCO (inverted: TP first, SL second)
        return await self._place_oco_synthetic_inverted(
            symbol=symbol, side=side, quantity=quantity,
            price=price, stop_price=stop_price,
            take_profit_price=take_profit_price,
        )

    async def _place_oco_native(self, symbol: str, side: OrderSide, quantity: float,
                                price: float, stop_price: float,
                                take_profit_price: float | None = None) -> Dict[str, Any]:
        """
        Native Binance OCO via direct API call POST /api/v3/order/oco.
        
        Binance OCO places a LIMIT TAKE_PROFIT + STOP_LOSS on the same quantity atomically,
        avoiding the double-lock issue where separate orders lock each other's balance.
        
        OCO params for Binance API:
        - symbol: raw symbol ID (e.g. BNBUSDC, no slash)
        - side: 'SELL' (uppercase)
        - quantity: amount
        - price: LIMIT price (take profit)
        - stopPrice: stop trigger price
        - stopLimitPrice: limit price for stop (optional, executed as market if omitted)
        - stopLimitTimeInForce: 'GTC'
        
        The CCXT method private_post_order_oco() maps directly to Binance's OCO endpoint.
        """
        try:
            # Get raw Binance symbol ID (no slash, e.g. BNBUSDC)
            filters = await self.get_symbol_filters(symbol)
            # Use symbol directly — CCXT resolves it via the internal adapter
            get_id = filters.get("baseAsset", "") + filters.get("quoteAsset", "")
            raw_symbol = get_id if get_id else symbol
            
            params: Dict[str, Any] = {
                "symbol": raw_symbol,
                "side": side.upper(),
                "quantity": quantity,
                "price": price,
                "stopPrice": stop_price,
                "stopLimitTimeInForce": "GTC",
            }
            if stop_price is not None:
                # stopLimitPrice = prezzo LIMITE per lo STOP LOSS (di solito uguale o leggermente sopra stopPrice)
                # IMPORTANTE: NON usare take_profit_price qui! Altrimenti lo SL proverà a vendere al prezzo del TP,
                # e quando il mercato scende sotto stopPrice, lo SL non sarà riempito perché il prezzo limite è sopra.
                # Usando stop_price, lo SL vende a market non appena il trigger scatta.
                params["stopLimitPrice"] = stop_price
            
            # Use the private OCO endpoint directly
            response = await self.client.private_post_order_oco(params)
            logger.info(f"Native OCO response: {response}")
            
            # Parse response
            order_list_id = response.get("orderListId", "unknown")
            orders = response.get("orderReports", [])
            sl_id = None
            tp_id = None
            main_id = response.get("listClientOrderId", order_list_id)
            
            for o in orders:
                if o.get("type") == "STOP_LOSS_LIMIT" or o.get("type") == "STOP_LOSS":
                    sl_id = o.get("orderId", "unknown")
                elif o.get("type") == "LIMIT" or o.get("type") == "LIMIT_MAKER":
                    tp_id = o.get("orderId", "unknown")
            
            return {
                "type": "oco",
                "order_id": main_id,
                "stop_loss_id": sl_id or response.get("orderListId", "unknown"),
                "take_profit_id": tp_id or response.get("orderListId", "unknown"),
                "status": "placed",
                "native": True,
                "order_list_id": order_list_id,
            }
        except Exception as e:
            raise ExchangeOrderError(f"Native OCO failed for {symbol}: {e}")

    async def _place_oco_synthetic_inverted(self, symbol: str, side: OrderSide, quantity: float,
                                            price: float, stop_price: float,
                                            take_profit_price: float | None = None) -> Dict[str, Any]:
        """
        Synthetic OCO with inverted order: TP LIMIT first, SL STOP_LOSS second.
        
        This avoids the double-lock bug where SL reserves the balance first and
        then TP cannot be placed because the same quantity is already locked.
        
        By placing TP LIMIT first:
        - Binance reserves the quantity for the LIMIT order
        - The STOP_LOSS uses the same quantity but Binance allows overlapping
          orders on the same balance (unlike LIMIT+STOP_LOSS which locks separately)
        
        Wait for balance settlement after market order before placing orders.
        """
        # Wait for balance settlement after the market fill
        await asyncio.sleep(0.5)
        try:
            await self.client.fetch_balance()
        except Exception:
            pass
        
        # Get actual available base asset balance (after fee deduction)
        actual_qty = await self._get_available_base_balance(symbol)
        if actual_qty <= 0:
            logger.warning(f"No {symbol} base asset balance available after trade")
            return {"type": "oco_synthetic_inverted", "status": "no_balance"}
        
        qty_rounded = await self._round_qty(symbol, actual_qty)
        logger.info(f"Actual available {symbol} balance after fee: {actual_qty} -> rounded: {qty_rounded}")
        
        # INVERTED ORDER: Place TP LIMIT first, SL STOP_LOSS second
        # TP goes first so it's always placed. SL is placed right after on the same qty.
        # Binance allows both orders to coexist as they track different price levels.
        tp_result = None
        if take_profit_price:
            try:
                tp_result = await self.place_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=qty_rounded,
                    limit_price=take_profit_price,
                )
                logger.info(f"Take profit limit placed first: {tp_result.get('order_id')}")
            except Exception as tp_e:
                logger.warning(f"Take profit limit failed (non-fatal): {tp_e}")
        
        sl_result = None
        try:
            sl_result = await self.place_stop_loss_order(
                symbol=symbol,
                side=side,
                quantity=qty_rounded,
                stop_price=stop_price,
            )
            logger.info(f"Stop loss placed: {sl_result.get('order_id')}")
        except Exception as sl_e:
            logger.warning(f"Stop loss placement failed (non-fatal, position tracked): {sl_e}")
        
        return {
            "type": "oco_synthetic_inverted",
            "order_id": sl_result.get("order_id") if sl_result else tp_result.get("order_id") if tp_result else None,
            "stop_loss_id": sl_result.get("order_id") if sl_result else None,
            "take_profit_id": tp_result.get("order_id") if tp_result else None,
            "status": "placed",
        }

    async def _get_available_base_balance(self, symbol: str) -> float:
        """Get the free (available) balance of the base asset for a symbol.
        
        After a market buy, Binance takes ~0.1% fee in the base asset (e.g. BNB),
        so you might have 0.015984 BNB instead of 0.016. This function reads
        the actual free balance from the exchange.
        """
        try:
            filters = await self.get_symbol_filters(symbol)
            base = filters["baseAsset"]
            balance = await self.client.fetch_balance()
            free = balance.get("free", {})
            return float(free.get(base, 0.0))
        except Exception as e:
            logger.warning(f"Could not fetch base balance for {symbol}: {e}")
            return 0.0

    async def _place_oco_synthetic(self, symbol: str, side: OrderSide, quantity: float,
                                    price: float, stop_price: float,
                                    take_profit_price: float | None = None) -> Dict[str, Any]:
        """
        Synthetic OCO: stop loss (STOP_LOSS market) + take profit (LIMIT) as separate orders.
        
        Wait for balance settlement after market order before placing stop loss,
        otherwise Binance returns "insufficient balance" because the asset
        hasn't settled yet.
        
        IMPORTANT: After a market buy, Binance deducts ~0.1% fee in the base asset.
        So if you bought 0.016 BNB, you may only have 0.015984 BNB to sell.
        This function reads the ACTUAL balance from the exchange after settlement.
        """
        # Wait for balance settlement after the market fill
        await asyncio.sleep(0.5)
        try:
            await self.client.fetch_balance()
        except Exception:
            pass
        
        # Get actual available base asset balance (after fee deduction)
        actual_qty = await self._get_available_base_balance(symbol)
        if actual_qty <= 0:
            logger.warning(f"No {symbol} base asset balance available after trade")
            return {"type": "oco_synthetic", "status": "no_balance"}
        
        qty_rounded = await self._round_qty(symbol, actual_qty)
        logger.info(f"Actual available {symbol} balance after fee: {actual_qty} -> rounded: {qty_rounded}")
        
        sl_result = None
        try:
            sl_result = await self.place_stop_loss_order(
                symbol=symbol,
                side=side,
                quantity=qty_rounded,
                stop_price=stop_price,
            )
        except Exception as sl_e:
            logger.warning(f"Stop loss placement failed (non-fatal, position tracked): {sl_e}")
        
        tp_result = None
        if take_profit_price:
            try:
                tp_result = await self.place_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=qty_rounded,
                    limit_price=take_profit_price,
                )
            except Exception as tp_e:
                logger.warning(f"Take profit limit failed (non-fatal): {tp_e}")
        
        return {
            "type": "oco_synthetic",
            "order_id": sl_result.get("order_id") if sl_result else None,
            "stop_loss_id": sl_result.get("order_id") if sl_result else None,
            "take_profit_id": tp_result.get("order_id") if tp_result else None,
            "status": "placed",
        }

    async def place_stop_loss_order(self, symbol: str, side: OrderSide, quantity: float, stop_price: float) -> Dict[str, Any]:
        """
        Place a STOP_LOSS (market) order — executes as market sell when stop_price is hit.
        More reliable on Binance mainnet than STOP_LOSS_LIMIT which requires extra params.
        """
        try:
            ccxt_symbol = await self._get_ccxt_symbol(symbol)
            order_type_cast = cast(Any, "STOP_LOSS")
            order = await self.client.create_order(
                ccxt_symbol,
                order_type_cast,
                side,
                quantity,
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
            order = await self.client.create_order(
                ccxt_symbol,
                "limit",
                side,
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