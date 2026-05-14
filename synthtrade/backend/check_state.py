import os
from supabase import create_client
from dotenv import load_dotenv

# Load env from backend/.env
load_dotenv("synthtrade/backend/.env")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

print("=== Strategie ATTIVE ===")
res_strat = supabase.table("strategies").select("*").eq("status", "ACTIVE").execute()
if res_strat.data:
    for s in res_strat.data:
        print(f"ID: {s['id']}, Pair: {s['pair']}, Budget: {s['budget_eur']}")
else:
    print("Nessuna strategia attiva.")

print("\n=== Ultimi 10 Log Operativi ===")
res_logs = supabase.table("operation_logs").select("*").order("created_at", desc=True).limit(10).execute()
if res_logs.data:
    for l in res_logs.data:
        print(f"[{l['created_at']}] {l['action']} - Strategy: {l['strategy_id']} - Reason: {l['reason']}")
else:
    print("Nessun log operativo trovato.")

print("\n=== Posizioni Aperte (Trades) ===")
res_trades = supabase.table("trades").select("*").is_("pnl_pct", "null").execute()
if res_trades.data:
    for t in res_trades.data:
        print(f"ID: {t['id']}, Strategy: {t['strategy_id']}, Action: {t['action']}, Qty: {t['quantity']} @ {t['price']}")
else:
    print("Nessuna posizione aperta.")
