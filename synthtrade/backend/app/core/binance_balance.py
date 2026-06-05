"""
Binance portfolio balance aggregator.
Recupera il saldo totale del conto Binance (Spot + LD tokens),
convertendo tutto in EUR usando i prezzi correnti di mercato.

Ottimizzato: usa fetch_tickers() per ottenere TUTTI i prezzi in ~2 chiamate
invece di fetch_ticker() per ogni singolo asset (che impiega minuti con 400+ asset).
"""
import logging
import ccxt
from app.config import settings

logger = logging.getLogger(__name__)

# Mappa token LD (Locked Deposit) -> asset reale
LD_MAP = {
    "LDBNB": "BNB",
    "LDBTC": "BTC",
    "LDETH": "ETH",
    "LDSOL": "SOL",
    "LDXRP": "XRP",
    "LDADA": "ADA",
    "LDDOT": "DOT",
    "LDLINK": "LINK",
    "LDUSDT": "USDT",
    "LDUSDC": "USDC",
    "LDBUSD": "BUSD",
    "LDPE": "PE",
    "LDPEPE": "PEPE",
    "LDPIXEL": "PIXEL",
    "LDW": "W",
    "LDTRX": "TRX",
    "LDDOGE": "DOGE",
    "LDSHIB": "SHIB",
    "LDMATIC": "MATIC",
    "LDAPT": "APT",
    "LDARB": "ARB",
    "LDOP": "OP",
}


def _get_exchange() -> ccxt.Exchange:
    """Restituisce istanza exchange via ExchangeFactory (TASK-431).
    
    Usa la factory singleton che gestisce correttamente la riconnessione
    al cambio di modalità TEST ↔ LIVE e applica set_sandbox_mode() in modo
    pulito (senza sovrascrivere manualmente gli URL).
    """
    from app.core.exchange_factory import get_exchange as _get_factory_exchange
    ex = _get_factory_exchange()
    if ex is None:
        raise RuntimeError("Exchange factory returned None")
    # ccxt type stub defines options values as dict[str, dict[str, str]],
    # but at runtime they accept plain str values like "spot"
    ex.options["defaultType"] = "spot"  # type: ignore[arg-type]
    ex.timeout = 5000
    return ex


def _build_ticker_map(exchange: ccxt.Exchange) -> dict:
    """
    Recupera TUTTI i ticker disponibili in una singola chiamata
    e costruisce un dict: symbol -> last price.
    """
    try:
        tickers = exchange.fetch_tickers()
        return {
            symbol: float(info["last"])
            for symbol, info in tickers.items()
            if info.get("last") is not None
        }
    except Exception as e:
        logger.warning(f"fetch_tickers failed: {e}, falling back to individual lookups")
        return {}


def _convert_to_eur_via_tickers(
    asset: str, qty: float, ticker_map: dict, eur_usdt: float | None
) -> float | None:
    """
    Converte qty di asset in EUR usando la mappa ticker pre-caricata.
    eur_usdt è il tasso di cambio EUR/USDT pre-calcolato.
    """
    if asset == "EUR":
        return qty

    # Se abbiamo eur_usdt, prova prima via USDT (la strada più comune)
    if eur_usdt is not None:
        # Asset -> USDT
        usdt_price = ticker_map.get(f"{asset}/USDT")
        if usdt_price is not None:
            return qty * usdt_price * eur_usdt

        # Inverso EUR/{asset}
        eur_price = ticker_map.get(f"EUR/{asset}")
        if eur_price is not None:
            return qty / eur_price

        # Diretto {asset}/EUR
        direct_price = ticker_map.get(f"{asset}/EUR")
        if direct_price is not None:
            return qty * direct_price

    # Se non abbiamo eur_usdt, usa la via classica
    direct_price = ticker_map.get(f"{asset}/EUR")
    if direct_price is not None:
        return qty * direct_price

    eur_price = ticker_map.get(f"EUR/{asset}")
    if eur_price is not None:
        return qty / eur_price

    # Via USDT senza eur_usdt
    usdt_price = ticker_map.get(f"{asset}/USDT")
    if usdt_price is not None:
        usdt_val = qty * usdt_price
        # Prova USDT/EUR o EUR/USDT
        usdt_eur = ticker_map.get("USDT/EUR")
        if usdt_eur is not None:
            return usdt_val * usdt_eur
        eur_usdt_inv = ticker_map.get("EUR/USDT")
        if eur_usdt_inv is not None:
            return usdt_val / eur_usdt_inv

    # Via BTC
    btc_price = ticker_map.get(f"{asset}/BTC")
    if btc_price is not None:
        btc_val = qty * btc_price
        btc_eur = ticker_map.get("BTC/EUR")
        if btc_eur is not None:
            return btc_val * btc_eur
        eur_btc = ticker_map.get("EUR/BTC")
        if eur_btc is not None:
            return btc_val / eur_btc

    return None


def get_total_balance_eur() -> dict:
    """
    Calcola il saldo totale del conto Binance in EUR
    a partire da fetch_balance() (include Spot, Earn, ecc.).

    Returns:
        dict con:
          - total_eur: float (saldo totale)
          - assets: list di dict (dettaglio per asset)
          - breakdown: dict (ripartizione per wallet)
    """
    exchange = _get_exchange()

    all_assets = {}  # asset -> {"total": float, "sources": set}

    def _add(asset: str, qty: float, source: str):
        if asset not in all_assets:
            all_assets[asset] = {"total": 0.0, "sources": set()}
        all_assets[asset]["total"] += qty
        all_assets[asset]["sources"].add(source)

    # --- 1. Spot wallet ---
    try:
        bal = exchange.fetch_balance()
        for currency in bal.get("total", {}):
            total = float(bal["total"][currency])
            if total > 0:
                if currency.startswith("LD") and currency in LD_MAP:
                    _add(LD_MAP[currency], total, "Spot(LD)")
                else:
                    _add(currency, total, "Spot")
    except Exception as e:
        logger.warning(f"Spot balance fetch failed: {e}")

    # --- Pre-carica TUTTI i ticker in una volta sola ---
    ticker_map = _build_ticker_map(exchange)

    # Pre-calcola EUR/USDT
    eur_usdt = None
    usdt_eur = ticker_map.get("USDT/EUR")
    if usdt_eur is not None:
        eur_usdt = usdt_eur
    else:
        eur_usdt_inv = ticker_map.get("EUR/USDT")
        if eur_usdt_inv is not None:
            eur_usdt = 1.0 / eur_usdt_inv

    # --- Conversione in EUR usando la mappa ticker ---
    total_eur = 0.0
    asset_details = []
    wallet_totals = {}

    for asset, info in sorted(all_assets.items()):
        qty = info["total"]
        if qty <= 0:
            continue

        eur_value = _convert_to_eur_via_tickers(asset, qty, ticker_map, eur_usdt)
        if eur_value is None:
            logger.debug(f"Cannot convert {asset} to EUR")
            continue

        total_eur += eur_value
        asset_details.append({
            "asset": asset,
            "quantity": round(qty, 8),
            "value_eur": round(eur_value, 2),
        })

        for src in info["sources"]:
            if src not in wallet_totals:
                wallet_totals[src] = {"value_eur": 0.0, "assets": []}
            wallet_totals[src]["value_eur"] += eur_value
            wallet_totals[src]["assets"].append({
                "asset": asset,
                "quantity": round(qty, 8),
                "value_eur": round(eur_value, 2),
            })

    return {
        "total_eur": round(total_eur, 2),
        "assets": asset_details,
        "breakdown": {
            wallet: {
                "value_eur": round(info["value_eur"], 2),
                "assets": info["assets"],
            }
            for wallet, info in sorted(wallet_totals.items())
        },
    }