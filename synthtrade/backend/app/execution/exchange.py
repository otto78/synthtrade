import asyncio
import ccxt.async_support as ccxt
from typing import Protocol, Dict, Any, List, Literal, Optional, cast
import logging
import time

logger = logging.getLogger(__name__)

OrderSide = Literal["buy", "sell"]
OrderType = Literal["limit", "market", "stop_loss_limit"]

class ExchangeOrderError(Exception):
    """Exception wrapper for exchange order errors with original details."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None, original_details: Optional[str] = None):
        super().__init__(message)
        self.original_exception = original_exception
        self.original_details = original_details

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

class BinanceExchangeAdapter:
    """
    TASK-082, TASK-083: Implementazione BinanceExchangeAdapter via CCXT
    TASK-413: Aggiunto get_holdings()
    TASK-877: Aggiunto get_trade_fee() per recupero fee tier account
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
        self._macro_cache = {"timestamp": 0.0, "data": {}}
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._price_cache_ttl = 15  # seconds

    async def close(self):
        await self.client.close()

    async def get_holdings(self) -> Dict[str, float]:
        try:
            balance = await self.client.fetch_balance()
            free = balance.get("free", {})
            return {asset: float(amt) for asset, amt in free.items() if float(amt) > 0}
        except Exception as e:
            # TASK-908: preserve original error details
            error_details = str(e)
            if hasattr(e, 'args') and e.args:
                error_details = str(e.args[0]) if len(e.args) > 0 else str(e)
            raise ExchangeOrderError(f"Holdings fetch failed: {error_details}", original_exception=e, original_details=error_details) from e

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
            # TASK-908: preserve original CCXT error details
            error_details = str(e)
            if hasattr(e, 'args') and e.args:
                error_details = str(e.args[0]) if len(e.args) > 0 else str(e)
            raise ExchangeOrderError(f"Balance fetch failed: {error_details}", original_exception=e, original_details=error_details) from e

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
        now = time.time()
        cached = self._price_cache.get(symbol)
        if cached and (now - cached["timestamp"]) < self._price_cache_ttl:
            return cached["price"]

        ccxt_symbol = await self._get_ccxt_symbol(symbol)
        try:
            ticker = await self.client.fetch_ticker(ccxt_symbol)
            price = float(ticker["last"])
            self._price_cache[symbol] = {"price": price, "timestamp": now}
            return price
        except Exception as e:
            # If fetch fails, return stale cached price if available (better than raising)
            if cached is not None:
                logger.warning(f"get_ticker_price({symbol}) fetch failed: {e} — returning stale cached price ({now - cached['timestamp']:.0f}s old)")
                return cached["price"]
            raise

    async def get_btc_macro_context(self) -> Dict[str, Any]:
        """
        Fetch BTC macro context (price, 1h change %, 24h change %, regime).
        Uses a 60-second cache to avoid rate limits during rapid polling.
        """
        import time
        now = time.time()
        if now - self._macro_cache["timestamp"] < 60 and self._macro_cache["data"]:
            return self._macro_cache["data"]

        try:
            # Ticker 24h for 24h change and current price
            ticker_24h = await self.client.fetch_ticker("BTC/USDT")
            price = float(ticker_24h.get("last", 0.0))
            change_24h_pct = float(ticker_24h.get("percentage", 0.0))

            # Klines 1h for 1h change
            klines = await self.client.fetch_ohlcv("BTC/USDT", timeframe="1h", limit=2)
            change_1h_pct = 0.0
            if len(klines) >= 2:
                # kline format: [timestamp, open, high, low, close, volume]
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
                "macro_regime": regime
            }
            self._macro_cache["timestamp"] = now
            self._macro_cache["data"] = data
            return data

        except Exception as e:
            logger.warning(f"Failed to fetch BTC macro context: {e}")
            return {
                "btc_price_at_entry": 0.0,
                "btc_change_1h_pct": 0.0,
                "btc_change_24h_pct": 0.0,
                "macro_regime": "unknown"
            }

    async def _round_qty(self, symbol: str, qty: float) -> float:
        """Arrotonda quantity a stepSize (floor) usando i filtri del simbolo."""
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
            result = cast(Dict[str, Any], order)

            # TASK-886: Estrai commissione reale dell'ordine market.
            # CCXT normalizza la fee Binance in order["fee"] (singolo fill) o
            # order["fees"] (lista, se l'ordine market si è riempito in più fill
            # a prezzi diversi — comune su qty piccole). Somma tutte le fee
            # dello stesso asset; se ci sono asset diversi nella lista (raro),
            # prendiamo quello con costo maggiore come principale e logghiamo un warning.
            commission = 0.0
            commission_asset = None
            try:
                fees_list = order.get("fees") or ([order["fee"]] if order.get("fee") else [])
                fees_by_asset: Dict[str, float] = {}
                for f in fees_list:
                    if not f:
                        continue
                    cost = float(f.get("cost", 0) or 0)
                    currency = f.get("currency")
                    if currency and cost > 0:
                        fees_by_asset[currency] = fees_by_asset.get(currency, 0.0) + cost
                if fees_by_asset:
                    if len(fees_by_asset) > 1:
                        logger.warning(
                            f"place_market_order: multiple fee currencies in single order "
                            f"for {symbol}: {fees_by_asset} — using largest"
                        )
                    commission_asset, commission = max(fees_by_asset.items(), key=lambda kv: kv[1])
            except Exception as fee_e:
                logger.warning(f"place_market_order: failed to extract commission for {symbol}: {fee_e}")

            result["commission"] = commission
            result["commission_asset"] = commission_asset
            if commission > 0:
                logger.info(f"Market order commission for {symbol}: {commission} {commission_asset}")
            else:
                logger.warning(
                    f"Market order for {symbol} returned no commission data in CCXT response — "
                    f"entry_commission will fall back to fee tier estimate"
                )
            return result
        except ccxt.InsufficientFunds as e:
            # TASK-908: preserve original CCXT error details
            error_details = str(e)
            if hasattr(e, 'args') and e.args:
                error_details = str(e.args[0]) if len(e.args) > 0 else str(e)
            raise ExchangeOrderError(f"Insufficient funds: {error_details}", original_exception=e, original_details=error_details) from e
        except Exception as e:
            # TASK-908: preserve original CCXT error details
            error_details = str(e)
            if hasattr(e, 'args') and e.args:
                error_details = str(e.args[0]) if len(e.args) > 0 else str(e)
            raise ExchangeOrderError(f"Market order failed: {error_details}", original_exception=e, original_details=error_details) from e

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

    # ── TASK-801 + OCO_FLOW v2: Solo OCO nativo Binance ──────────────────────

    async def place_oco_order(self, symbol: str, side: OrderSide, quantity: float,
                              price: float, stop_price: float,
                              take_profit_price: float | None = None) -> Dict[str, Any]:
        """
        Place OCO (One-Cancels-Other) order — solo nativo Binance, nessun fallback sintetico.

        USA la `quantity` passata dal chiamante (calcolata con math.floor NEL ROUTER
        prima del buy) senza leggere il balance del wallet.

        ⚠️  MOTIVAZIONE: leggere _get_available_base_balance() includeva polvere di
        trade precedenti, causando OCO per quantità superiori a quelle acquistate.
        Es: buy 0.033 BNB + 0.001 BNB polvere old → balance 0.034 → OCO per 0.034 ❌
            buy 0.033 BNB, exec_qty=0.033 → OCO per 0.033 ✅

        Se OCO nativo fallisce, solleva ExchangeOrderError: il chiamante (router.py)
        gestisce il caso B (market sell di emergenza + broadcast error).
        """
        logger.info(f"Placing OCO for {symbol}: TP={price}, SL={stop_price}, qty={quantity}")

        # Applica floor al stepSize sulla qty già calcolata dal router.
        # Non leggiamo il balance del wallet — conterrebbe polvere di trade precedenti.
        qty_rounded = await self._round_qty(symbol, quantity)
        if qty_rounded <= 0:
            raise ExchangeOrderError(
                f"Rounded quantity is 0 for {symbol} OCO (input={quantity})"
            )

        logger.info(f"OCO qty after rounding: {qty_rounded} (input={quantity})")
        return await self._place_oco_native(
            symbol=symbol, side=side, quantity=qty_rounded,
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
            }
            # ⚠️ IMPORTANTE: NON includere stopLimitPrice!
            # Se includiamo stopLimitPrice, Binance crea un ordine STOP_LOSS_LIMIT invece di STOP_LOSS.
            # Con STOP_LOSS_LIMIT, quando stopPrice viene triggerato, Binance piazza un LIMIT order
            # a stopLimitPrice. Se il mercato salta sotto quel prezzo (slippage rapido), l'ordine
            # NON viene eseguito e la posizione rimane aperta senza protezione.
            # Con STOP_LOSS (senza stopLimitPrice), quando stopPrice viene triggerato, Binance piazza
            # un MARKET order che viene SEMPRE eseguito al mejor prezzo disponibile.
            # 
            # CORREZIONE BUG 2026-06-20: Rimosso stopLimitPrice per usare STOP_LOSS (market) invece
            # di STOP_LOSS_LIMIT (limit). Il bug causava lo stop loss che non veniva eseguito quando
            # il prezzo scendeva rapidamente sotto lo stop.

            # Use the private OCO endpoint directly
            response = await self.client.private_post_order_oco(params)
            order_list_id = response.get("orderListId", "unknown")
            logger.info(f"Native OCO placed: orderListId={order_list_id}")

            # Parse response
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
            # TASK-908: preserve original error details
            error_details = str(e)
            if hasattr(e, 'args') and e.args:
                error_details = str(e.args[0]) if len(e.args) > 0 else str(e)
            raise ExchangeOrderError(f"Native OCO failed for {symbol}: {error_details}", original_exception=e, original_details=error_details) from e

    async def _get_available_base_balance(self, symbol: str) -> float:
        """Get the free (available) balance of the base asset for a symbol.

        Nota: questo metodo NON viene più usato da place_oco_order (vedi docstring).
        Rimane disponibile per usi diagnostici (es. _handle_oco_failed nel router).
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

    async def _fetch_fill_price_by_order_id(self, symbol: str, order_id: str) -> Optional[float]:
        """Recupera il fill price di un ordine specifico tramite orderId.

        Usato da restore sessione per trovare il prezzo di chiusura dell'OCO
        tramite sl_order_id o tp_order_id salvati in DB.
        """
        try:
            ccxt_symbol = await self._get_ccxt_symbol(symbol)
            orders = await self.client.fetch_closed_orders(ccxt_symbol, limit=50)
            for o in orders:
                if str(o.get("id")) == str(order_id):
                    fill = float(o.get("price") or o.get("average") or 0)
                    if fill > 0:
                        return fill
        except Exception as e:
            logger.warning(f"_fetch_fill_price_by_order_id failed for {symbol} orderId={order_id}: {e}")
        return None

    async def get_trade_fee(self, symbol: str) -> Dict[str, float]:
        """Recupera il fee tier corrente dell'account per un symbol specifico.

        TASK-877: Chiama l'endpoint Binance GET /sapi/v1/asset/tradeFee per ottenere
        makerCommission e takerCommission esatti per l'account, inclusi sconti BNB.

        Args:
            symbol: Symbol da interrogare (es. "BNBUSDC")

        Returns:
            Dict con "maker" e "taker" come percentuali (es. 0.001 per 0.1%)
        """
        try:
            # CCXT ha il metodo nativo fetchTradingFee per ottenere le fee
            # Converti il symbol nel formato CCXT (es. BNBUSDC -> BNB/USDC)
            ccxt_symbol = await self._get_ccxt_symbol(symbol)
            response = await self.client.fetch_trading_fee(ccxt_symbol)
            
            if not response or response.get("maker") is None or response.get("taker") is None:
                logger.warning(f"get_trade_fee: invalid response for {symbol}: {response}")
                return {"maker": 0.001, "taker": 0.001}  # fallback default
            
            maker_comm = float(response.get("maker", 0.001))
            taker_comm = float(response.get("taker", 0.001))
            
            logger.info(f"Fee tier for {symbol}: maker={maker_comm}, taker={taker_comm}")
            return {"maker": maker_comm, "taker": taker_comm}
            
        except Exception as e:
            logger.error(f"get_trade_fee failed for {symbol}: {e}")
            # Fallback al default 0.1% se l'endpoint fallisce
            return {"maker": 0.001, "taker": 0.001}