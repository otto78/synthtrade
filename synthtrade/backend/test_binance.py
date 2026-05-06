import ccxt
from app.config import settings

print("=== Test Connettivita Binance ===")
print(f"TESTNET: {settings.BINANCE_TESTNET}")
print(f"API Key: {settings.BINANCE_API_KEY[:12]}...")
print(f"Secret:  {settings.BINANCE_SECRET_KEY[:8]}...")
print()

# Crea exchange
exchange = ccxt.binance({
    "apiKey": settings.BINANCE_API_KEY,
    "secret": settings.BINANCE_SECRET_KEY,
    "enableRateLimit": True,
})

# Se non e testnet, disabilita sandbox
if not settings.BINANCE_TESTNET:
    exchange.set_sandbox_mode(False)

# Test 1: Ticker pubblico
try:
    t = exchange.fetch_ticker("BTC/USDT")
    print(f"✅ Ticker BTC/USDT: {t['last']} USDT")
except Exception as e:
    print(f"❌ Ticker: {type(e).__name__}: {e}")

# Test 2: Balance completo (autenticato)
try:
    b = exchange.fetch_balance()
    
    # USDT specifico
    usdt_total = b.get("USDT", {}).get("total", 0)
    usdt_free  = b.get("USDT", {}).get("free", 0)
    print(f"✅ Balance USDT -> totale: {usdt_total}, free: {usdt_free}")
    
    # Mostra TUTTI gli asset con saldo > 0
    print("\n   Asset con saldo > 0:")
    found = False
    for currency in list(b.get("total", {}).keys()):
        data = float(b["total"][currency])
        if data > 0:
            free = float(b["free"].get(currency, 0))
            print(f"     {currency}: totale={data}, free={free}")
            found = True
    if not found:
        print("     (nessun asset con saldo > 0)")
        
    # Stampa anche le keys raw di binance per debug
    if isinstance(b.get("info"), dict):
        print(f"\n   Raw 'info' keys: {list(b['info'].keys())}")
except Exception as e:
    print(f"❌ Balance: {type(e).__name__}: {e}")

# Test 3: Order book (pubblico)
try:
    ob = exchange.fetch_order_book("BTC/USDT")
    bid = ob["bids"][0][0] if ob["bids"] else "N/A"
    ask = ob["asks"][0][0] if ob["asks"] else "N/A"
    print(f"✅ Order book BTC/USDT -> bid: {bid}, ask: {ask}")
except Exception as e:
    print(f"❌ Order book: {type(e).__name__}: {e}")

# Test 4: Open orders (con symbol per evitare rate-limit warning)
try:
    exchange.options["warnOnFetchOpenOrdersWithoutSymbol"] = False
    o = exchange.fetch_open_orders()
    print(f"✅ Open orders: {len(o)}")
except Exception as e:
    print(f"❌ Open orders: {type(e).__name__}: {e}")

# Test 5: Trades history (ultimi 5)
try:
    trades = exchange.fetch_my_trades(symbol="BTC/USDT", limit=5)
    print(f"✅ My trades (ultimi 5): {len(trades)} trades")
except Exception as e:
    print(f"❌ My trades: {type(e).__name__}: {e}")
