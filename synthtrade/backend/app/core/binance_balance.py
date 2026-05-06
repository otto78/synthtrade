"""
Binance portfolio balance aggregator.
Recupera il saldo totale del conto Binance (Spot + LD tokens),
convertendo tutto in EUR usando i prezzi correnti di mercato.
NOTA: fetch_balance().total include già Earn e altri wallet,
quindi NON si aggiungono chiamate separate a Simple Earn per evitare double counting.
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
    ex = ccxt.binance({
        "apiKey": settings.BINANCE_API_KEY,
        "secret": settings.BINANCE_SECRET_KEY,
        "enableRateLimit": True,
    })
    if not settings.BINANCE_TESTNET:
        ex.set_sandbox_mode(False)
    return ex


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
    exchange.load_markets()

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

    # --- Conversione in EUR ---
    total_eur = 0.0
    asset_details = []
    wallet_totals = {}

    for asset, info in sorted(all_assets.items()):
        qty = info["total"]
        if qty <= 0:
            continue

        eur_value = _convert_to_eur(exchange, asset, qty)
        if eur_value is None:
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


def _convert_to_eur(exchange: ccxt.Exchange, asset: str, qty: float) -> float | None:
    """Prova a convertire qty di asset in EUR, tentando EUR -> USDT -> BTC."""
    try:
        ticker = exchange.fetch_ticker(f"{asset}/EUR")
        return qty * float(ticker["last"])
    except Exception:
        pass
    try:
        ticker = exchange.fetch_ticker(f"{asset}/USDT")
        usdt_val = qty * float(ticker["last"])
        eur_ticker = exchange.fetch_ticker("USDT/EUR")
        return usdt_val * float(eur_ticker["last"])
    except Exception:
        pass
    try:
        ticker = exchange.fetch_ticker(f"{asset}/BTC")
        btc_val = qty * float(ticker["last"])
        eur_ticker = exchange.fetch_ticker("BTC/EUR")
        return btc_val * float(eur_ticker["last"])
    except Exception as e:
        logger.debug(f"Cannot convert {asset} to EUR: {e}")
        return None