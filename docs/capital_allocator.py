import logging
from typing import List, Dict, Any
from app.execution.schemas import OrderRequest
from app.execution.quantity_calculator import calculate_quantity

logger = logging.getLogger("synthtrade.execution")

class CapitalAllocator:
    """
    Gestisce l'allocazione del capitale iniziale all'attivazione di una strategia.
    Determina quali asset acquistare e in che quantità basandosi sul budget in EUR.
    """
    def __init__(self, exchange_adapter):
        self.exchange = exchange_adapter

    async def get_initial_allocation_orders(
        self, 
        strategy: Dict[str, Any], 
        budget_eur: float
    ) -> List[OrderRequest]:
        """
        Genera una lista di OrderRequest per l'acquisto iniziale degli asset.
        Converte il budget EUR in USDT (tasso mock 1.08) e calcola le quantità.
        Verifica le holdings attuali per evitare acquisti ridondanti.
        """
        try:
            balance_data = await self.exchange.get_balance()
        except Exception as e:
            logger.error(f"Errore recupero balance: {e}")
            balance_data = {}

        # In produzione il tasso verrebbe recuperato real-time (es. EUR/USDT ticker)
        eur_usdt_rate = 1.08 
        total_budget_usdt = budget_eur * eur_usdt_rate
        
        # Recupera l'allocazione dai parametri (default 100% sul pair principale)
        allocations = strategy.get("params", {}).get("allocation")
        if not allocations:
            allocations = [{"symbol": strategy.get("pair", "BTC/USDT"), "pct": 100}]
            
        orders = []
        for alloc in allocations:
            symbol = alloc["symbol"]
            asset = symbol.split('/')[0]
            pct = alloc["pct"]
            target_usdt = total_budget_usdt * (pct / 100.0)
            
            try:
                # Recupera il prezzo corrente per calcolare la quantità esatta
                price = await self.exchange.get_ticker_price(symbol)
                
                # Check se abbiamo già abbastanza asset (TASK-401)
                current_qty = balance_data.get(asset, 0.0)
                target_qty = target_usdt / price
                
                if current_qty >= target_qty:
                    logger.info(f"Salto acquisto per {symbol}: holding attuale ({current_qty}) >= target ({target_qty})")
                    continue

                needed_qty = target_qty - current_qty
                # Rispettiamo i filtri LOT_SIZE dell'exchange
                quantity = calculate_quantity(symbol, needed_qty * price, price)
                
                if quantity > 0:
                    orders.append(OrderRequest(
                        strategy_id=strategy["id"],
                        symbol=symbol,
                        side="buy",
                        quantity=float(quantity),
                        type="MARKET"
                    ))
            except Exception as e:
                logger.error(f"Errore calcolo allocazione per {symbol}: {e}")
                raise
        return orders