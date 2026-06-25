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

    Se BINANCE_PROXY_URL è impostato (es. su Render), tutte le chiamate API
    vengono instradata attraverso il Cloudflare Worker per bypassare il
    geo-blocco US di Binance. In locale la variabile è vuota → connessione diretta.
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

    # Proxy via Cloudflare Worker (bypassare geo-blocco Binance su Render/Oregon)
    proxy_url = settings.BINANCE_PROXY_URL.strip()
    if proxy_url:
        # Sostituisce tutti gli endpoint REST di Binance con il Worker URL.
        # Il Worker fa da reverse proxy trasparente verso api.binance.com.
        # IMPORTANTE: include il path prefix per ogni key.
        # CCXT costruisce l'URL finale come: base_url + endpoint_path
        # Esempio: sapi="https://worker.dev/sapi/v1" + "/capital/config/getall"
        #       => Worker riceve "/sapi/v1/capital/config/getall"
        #       => Worker forward a "https://api.binance.com/sapi/v1/capital/config/getall" ✅
        worker_urls = {
            "public":      f"{proxy_url}/api/v3",
            "private":     f"{proxy_url}/api/v3",
            "v3":          f"{proxy_url}/api/v3",
            "v1":          f"{proxy_url}/api/v1",
            "sapi":        f"{proxy_url}/sapi/v1",
            "sapiV2":      f"{proxy_url}/sapi/v2",
            "sapiV3":      f"{proxy_url}/sapi/v3",
            "sapiV4":      f"{proxy_url}/sapi/v4",
            "fapiPublic":  f"{proxy_url}/fapi/v1",
            "fapiPrivate": f"{proxy_url}/fapi/v1",
            "dapiPublic":  f"{proxy_url}/dapi/v1",
            "dapiPrivate": f"{proxy_url}/dapi/v1",
        }
        if exchange.urls and isinstance(exchange.urls, dict):
            exchange.urls["api"] = worker_urls  # type: ignore[assignment]
        logger.info("ExchangeFactory: proxy Cloudflare Worker attivo → %s", proxy_url)
    else:
        logger.debug("ExchangeFactory: connessione diretta a Binance (no proxy)")

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