"""
ExchangeFactory — Centralizza la creazione e riconnessione delle istanze ccxt.binance().

TASK-431: Tutti i moduli che necessitano di una connessione Binance importano da qui
invece di creare ccxt.binance() direttamente. Al cambio di modalità (TEST ↔ LIVE),
chiamare reconnect() per ricreare la connessione con le key/URL corretti.
"""

import logging
import ccxt
from app.config import settings

logger = logging.getLogger(__name__)

_exchange: ccxt.binance | None = None
_current_mode: str | None = None


def _build_exchange() -> ccxt.binance:
    """Crea una nuova istanza ccxt.binance con le configurazioni correnti.

    Usa le proprietà dinamiche di settings che selezionano automaticamente
    le key/URL giuste in base a TRADING_MODE.
    """
    api_key = settings.binance_api_key
    secret_key = settings.binance_secret_key

    if not api_key or not secret_key:
        logger.warning("Binance API key o secret non configurate")

    exchange = ccxt.binance({
        "apiKey": api_key,
        "secret": secret_key,
        "enableRateLimit": True,
    })

    # Imposta sandbox/testnet se in modalità test
    if settings.TRADING_MODE == 'test':
        exchange.set_sandbox_mode(True)
        logger.info("ExchangeFactory: istanza TESTNET creata")
    else:
        logger.info("ExchangeFactory: istanza LIVE creata")

    return exchange


def get_exchange() -> ccxt.binance:
    """Restituisce l'istanza singleton dell'exchange.

    Se la modalità è cambiata (es. da un reconnect manuale), ricrea l'istanza.
    """
    global _exchange, _current_mode

    if _exchange is None or _current_mode != settings.TRADING_MODE:
        _exchange = _build_exchange()
        _current_mode = settings.TRADING_MODE

    return _exchange


def reconnect(mode: str | None = None) -> ccxt.binance:
    """Forza la riconnessione dell'exchange.

    Args:
        mode: "test" o "live". Se None, usa settings.TRADING_MODE.

    Returns:
        La nuova istanza ccxt.binance.

    Nota: reconnect() non modifica settings.TRADING_MODE — lo fa il chiamante
    (es. l'endpoint POST /api/config/mode) prima di chiamare reconnect().
    """
    global _exchange, _current_mode

    logger.info("ExchangeFactory: riconnessione forzata (mode=%s)", mode or settings.TRADING_MODE)
    if mode is not None and mode != settings.TRADING_MODE:
        logger.warning(
            "ExchangeFactory: mode=%s diverso da settings.TRADING_MODE=%s. "
            "Assicurati che settings sia già stato aggiornato.",
            mode, settings.TRADING_MODE,
        )

    _exchange = _build_exchange()
    _current_mode = settings.TRADING_MODE
    return _exchange


def reset() -> None:
    """Azzera il singleton (utile nei test)."""
    global _exchange, _current_mode
    _exchange = None
    _current_mode = None