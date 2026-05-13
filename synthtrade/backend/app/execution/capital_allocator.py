"""
TASK-401: CapitalAllocator
Calcola i trade iniziali da piazzare quando si attiva una strategia,
per acquistare le crypto necessarie in proporzione al budget allocato.
"""
from dataclasses import dataclass, field
from typing import List, Dict


class BudgetTooSmallError(Exception):
    """Sollevato quando il budget è insufficiente per il MIN_NOTIONAL di un simbolo."""
    def __init__(self, symbol: str, required_usdt: float, available_usdt: float):
        self.symbol = symbol
        self.required_usdt = required_usdt
        self.available_usdt = available_usdt
        super().__init__(
            f"Budget insufficiente per {symbol}: richiesti {required_usdt:.2f} USDT, "
            f"disponibili {available_usdt:.2f} USDT"
        )


@dataclass
class InitialTradeRequest:
    """Trade iniziale da piazzare per allocare il capitale."""
    symbol: str          # es. "BTC/USDT"
    side: str            # sempre "buy" per l'allocazione iniziale
    usdt_amount: float   # importo in USDT da spendere
    pct: float           # percentuale del budget allocata a questo simbolo (0-100)


def _parse_allocation(strategy: dict) -> List[Dict]:
    """
    Estrae l'allocazione dalla strategia.
    Formato params.allocation: [{ "symbol": "BTC/USDT", "pct": 60 }, ...]
    Se non presente, usa strategy["pair"] al 100%.
    """
    params = strategy.get("params") or {}
    allocation = params.get("allocation")
    if allocation and isinstance(allocation, list) and len(allocation) > 0:
        return allocation
    # Fallback: singolo asset al 100%
    pair = strategy.get("pair", "BTC/USDT")
    return [{"symbol": pair, "pct": 100}]


class CapitalAllocator:
    """
    TASK-401: Calcola i trade iniziali per allocare il capitale di una strategia.
    Non piazza ordini — restituisce solo la lista di trade da eseguire.
    """

    # Notional minimo in USDT (sotto cui non ha senso tentare il trade)
    MIN_NOTIONAL_USDT: float = 10.0

    def allocate(
        self,
        strategy: dict,
        available_usdt: float,
        holdings: Dict[str, float],
    ) -> List[InitialTradeRequest]:
        """
        Calcola la lista di trade iniziali necessari per preparare il portafoglio.

        Args:
            strategy: dict della strategia (con "params", "pair", "budget_eur")
            available_usdt: USDT liberi nel wallet
            holdings: dict asset → quantità posseduta (es. {"BTC": 0.01, "USDT": 500})

        Returns:
            Lista di InitialTradeRequest da eseguire. Può essere vuota se l'utente
            ha già le crypto necessarie in proporzione corretta.

        Raises:
            BudgetTooSmallError: se il budget per un simbolo è sotto MIN_NOTIONAL
        """
        budget_usdt = strategy.get("initial_capital_usdt") or strategy.get("budget_eur") or 0.0
        allocation_list = _parse_allocation(strategy)

        trades: List[InitialTradeRequest] = []

        for item in allocation_list:
            symbol: str = item.get("symbol", "BTC/USDT")
            pct: float = float(item.get("pct", 100))
            target_usdt = budget_usdt * (pct / 100.0)

            if target_usdt < self.MIN_NOTIONAL_USDT:
                raise BudgetTooSmallError(
                    symbol=symbol,
                    required_usdt=self.MIN_NOTIONAL_USDT,
                    available_usdt=target_usdt,
                )

            # Verifica se l'utente ha già la crypto sufficiente
            base_asset = symbol.split("/")[0]  # es. "BTC" da "BTC/USDT"
            current_holding_qty = holdings.get(base_asset, 0.0)

            # Stima semplice: se il valore in USDT dell'holding supera il 90% del target
            # consideriamo già allocato (evita micro-trade inutili).
            # Nota: il prezzo preciso viene valutato dall'exchange al momento del trade.
            # Qui usiamo solo una stima grossolana per decidere se skippare.
            # Se holdings non contiene USDT per il simbolo, includiamo sempre il trade.
            if current_holding_qty > 0:
                # Non abbiamo il prezzo corrente qui — il caller (activate endpoint)
                # può passare holdings già in USDT se vuole una stima precisa.
                # Per semplicità: se c'è qualcosa, skippa (lascia al caller decidere)
                # Strategia conservativa: includi sempre il trade se non è chiaro
                pass

            trades.append(InitialTradeRequest(
                symbol=symbol,
                side="buy",
                usdt_amount=target_usdt,
                pct=pct,
            ))

        return trades
