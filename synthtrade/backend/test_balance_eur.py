import ccxt
from app.config import settings

print("=== RECUPERO SALDO COMPLETO BINANCE ===")
print()

exchange = ccxt.binance({
    "apiKey": settings.BINANCE_API_KEY,
    "secret": settings.BINANCE_SECRET_KEY,
    "enableRateLimit": True,
})
if not settings.BINANCE_TESTNET:
    exchange.set_sandbox_mode(False)

# Dizionario per accumulare tutti gli asset e il loro valore
all_assets = {}  # asset -> {"total": float, "free": float, "locked": float, "sources": set()}

def add_asset(currency, total, free, locked, source):
    if currency not in all_assets:
        all_assets[currency] = {"total": 0, "free": 0, "locked": 0, "sources": set()}
    all_assets[currency]["total"] += total
    all_assets[currency]["free"] += free
    all_assets[currency]["locked"] += locked
    all_assets[currency]["sources"].add(source)

# Mappa LD -> asset reale
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

# ============================================
# 1. SPOT WALLET (via fetch_balance)
# ============================================
print("--- 1. SPOT WALLET ---")
try:
    b = exchange.fetch_balance()
    for currency in b.get("total", {}):
        total = float(b["total"][currency])
        free = float(b["free"].get(currency, 0))
        if total > 0:
            # Se e' un LD token, lo riconvertiamo all'asset base
            if currency.startswith("LD") and currency in LD_MAP:
                base_asset = LD_MAP[currency]
                add_asset(base_asset, total, free, total - free, "Spot(LD)")
                print(f"   {currency} -> {base_asset}: {total} (mappato da LD)")
            else:
                add_asset(currency, total, free, total - free, "Spot")
                print(f"   {currency}: {total} (free: {free})")
except Exception as e:
    print(f"   ❌ Errore: {e}")

# ============================================
# 2. SIMPLE EARN POSITIONS (FLEXIBLE)
# ============================================
print("\n--- 2. SIMPLE EARN (FLEXIBLE) ---")
try:
    flex = exchange.sapi_get_simple_earn_flexible_position(params={"current": 1, "size": 100})
    if flex and "rows" in flex:
        for row in flex["rows"]:
            asset = row.get("asset", "")
            amount = float(row.get("amount", row.get("totalAmount", 0)))
            if amount > 0:
                add_asset(asset, amount, amount, 0, "Earn(Flex)")
                print(f"   {asset}: {amount}")
    else:
        print(f"   (nessuna posizione flex)")
except Exception as e:
    print(f"   ❌ Errore: {e}")

# ============================================
# 3. SIMPLE EARN POSITIONS (LOCKED)
# ============================================
print("\n--- 3. SIMPLE EARN (LOCKED) ---")
try:
    locked_pos = exchange.sapi_get_simple_earn_locked_position(params={"current": 1, "size": 100})
    if locked_pos and "rows" in locked_pos:
        for row in locked_pos["rows"]:
            asset = row.get("asset", "")
            amount = float(row.get("amount", row.get("totalAmount", 0)))
            if amount > 0:
                add_asset(asset, amount, 0, amount, "Earn(Locked)")
                print(f"   {asset}: {amount}")
    else:
        print(f"   (nessuna posizione locked)")
except Exception as e:
    print(f"   ❌ Errore: {e}")

# ============================================
# 4. CONVERSIONE IN EUR
# ============================================
print("\n\n=== CONVERSIONE IN EUR ===")
total_eur = 0.0
asset_details = []

try:
    exchange.load_markets()
    print(f"   Markets caricati: {len(exchange.symbols)} pairs")
except Exception as e:
    print(f"   ❌ Errore caricamento markets: {e}")

for currency, data in sorted(all_assets.items()):
    total_qty = data["total"]
    if total_qty <= 0:
        continue

    eur_value = 0.0
    source_info = ", ".join(sorted(data["sources"]))
    conv_path = ""

    # Prova 1: Direct EUR pair
    try:
        ticker = exchange.fetch_ticker(f"{currency}/EUR")
        eur_value = total_qty * float(ticker["last"])
        conv_path = f"{currency}/EUR = {ticker['last']}"
    except Exception:
        # Prova 2: Via USDT
        try:
            ticker_usdt = exchange.fetch_ticker(f"{currency}/USDT")
            usdt_value = total_qty * float(ticker_usdt["last"])
            ticker_eur = exchange.fetch_ticker("USDT/EUR")
            eur_value = usdt_value * float(ticker_eur["last"])
            conv_path = f"{currency}/USDT = {ticker_usdt['last']} -> USDT/EUR = {ticker_eur['last']}"
        except Exception:
            # Prova 3: Via BTC
            try:
                ticker_btc = exchange.fetch_ticker(f"{currency}/BTC")
                btc_value = total_qty * float(ticker_btc["last"])
                ticker_eur = exchange.fetch_ticker("BTC/EUR")
                eur_value = btc_value * float(ticker_eur["last"])
                conv_path = f"{currency}/BTC = {ticker_btc['last']} -> BTC/EUR = {ticker_eur['last']}"
            except Exception as e3:
                print(f"   ❌ {currency}: {total_qty} - conversione fallita")
                continue

    total_eur += eur_value
    asset_details.append((currency, total_qty, eur_value, conv_path, source_info))
    print(f"   ✅ {currency}: {total_qty} -> {eur_value:.2f} EUR [{source_info}] ({conv_path})")

print(f"\n{'='*50}")
print(f"🏦 SALDO TOTALE CONTO BINANCE: € {total_eur:.2f}")
print(f"{'='*50}")

# Riepilogo per wallet
print(f"\n=== DETTAGLIO PER WALLET ===")
wallet_eur = {}
for currency, total_qty, eur_value, conv_path, source_info in asset_details:
    for src in sorted(all_assets[currency]["sources"]):
        if src not in wallet_eur:
            wallet_eur[src] = {"assets": [], "total": 0}
        wallet_eur[src]["assets"].append((currency, total_qty, eur_value))
        wallet_eur[src]["total"] += eur_value

for wallet, info in sorted(wallet_eur.items()):
    print(f"\n{wallet}: {info['total']:.2f} EUR")
    for cur, qty, eur in info["assets"]:
        print(f"   {cur}: {qty} = {eur:.2f} EUR")