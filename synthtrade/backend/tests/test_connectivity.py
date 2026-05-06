"""
Test rapido di connettività a Supabase e Binance.
Esegue chiamate reali (non mockate) per verificare che API key / secret siano validi.
"""

import asyncio
import sys
import os

# Assicura che il backend sia nel path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings


def test_supabase_connection():
    """Verifica che il client Supabase riesca a fare una query semplice."""
    from supabase import create_client

    print(f"\n[Supabase] URL: {settings.SUPABASE_URL}")
    print(f"[Supabase] Anon Key (primi 20): {settings.SUPABASE_ANON_KEY[:20]}...")
    print(f"[Supabase] Service Role Key (primi 20): {settings.SUPABASE_SERVICE_ROLE_KEY[:20]}...")

    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        # Prova a fare una select semplice su una tabella esistente
        result = client.table("strategies").select("count", count="exact").limit(1).execute()
        print(f"[Supabase] ✅ Connessione OK — count strategies: {result.count}")
        return True
    except Exception as e:
        print(f"[Supabase] ❌ Connessione FALLITA — {type(e).__name__}: {e}")
        return False


def test_supabase_tables():
    """Verifica che le tabelle principali esistano."""
    from supabase import create_client

    tables = ["strategies", "trades", "operation_logs", "ohlcv_cache"]
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    all_ok = True
    for table in tables:
        try:
            result = client.table(table).select("count", count="exact").limit(1).execute()
            print(f"[Supabase] ✅ Tabella '{table}' OK (rows: {result.count})")
        except Exception as e:
            print(f"[Supabase] ❌ Tabella '{table}' FALLITA — {e}")
            all_ok = False
    return all_ok


def test_binance_connection():
    """Verifica che l'exchange Binance sia raggiungibile con le credenziali fornite."""
    import ccxt

    print(f"\n[Binance] API Key (primi 20): {settings.BINANCE_API_KEY[:20]}...")
    print(f"[Binance] Testnet: {settings.BINANCE_TESTNET}")

    try:
        exchange = ccxt.binance({
            "apiKey": settings.BINANCE_API_KEY,
            "secret": settings.BINANCE_SECRET_KEY,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })

        if settings.BINANCE_TESTNET:
            exchange.set_sandbox_mode(True)

        # Prova a fetchare il balance
        balance = exchange.fetch_balance()
        print(f"[Binance] ✅ Connessione OK — balance keys: {list(balance['total'].keys())[:5]}...")
        # Mostra solo USDT se presente
        usdt = balance["total"].get("USDT", 0)
        if usdt:
            print(f"[Binance]    USDT balance: {usdt}")
        return True
    except Exception as e:
        print(f"[Binance] ❌ Connessione FALLITA — {type(e).__name__}: {e}")
        return False


def test_binance_ticker():
    """Verifica che si possa ottenere un ticker in tempo reale (endpoint pubblico)."""
    import ccxt

    try:
        exchange = ccxt.binance({"enableRateLimit": True})
        ticker = exchange.fetch_ticker("BTC/USDT")
        print(f"[Binance] ✅ Ticker BTC/USDT: ${ticker['last']} (24h change: {ticker['percentage']:.1f}%)")
        return True
    except Exception as e:
        print(f"[Binance] ❌ Ticker FALLITO — {e}")
        return False


if __name__ == "__main__":
    results = {}

    print("=" * 60)
    print("  TEST CONNETTIVITÀ — SynthTrade")
    print("=" * 60)

    # Binance test pubblico (non richiede chiavi)
    print("\n--- 0. Binance Ticker Pubblico ---")
    results["binance_ticker"] = test_binance_ticker()

    # Supabase
    print("\n--- 1. Supabase Connection ---")
    results["supabase"] = test_supabase_connection()

    if results["supabase"]:
        print("\n--- 2. Supabase Tables ---")
        results["supabase_tables"] = test_supabase_tables()
    else:
        results["supabase_tables"] = False

    # Binance autenticato
    if settings.BINANCE_API_KEY:
        print("\n--- 3. Binance Auth ---")
        results["binance"] = test_binance_connection()
    else:
        print("\n--- 3. Binance Auth ---")
        print("[Binance] ⏭️  Skippato — BINANCE_API_KEY non configurata")
        results["binance"] = None

    # Riepilogo
    print("\n" + "=" * 60)
    print("  RIEPILOGO")
    print("=" * 60)
    all_pass = True
    for name, ok in results.items():
        status = "✅ OK" if ok else ("❌ FAIL" if ok is False else "⏭️  SKIP")
        if ok is False:
            all_pass = False
        print(f"  {name:20s}: {status}")

    sys.exit(0 if all_pass else 1)