import os
from dotenv import load_dotenv
load_dotenv('.env')
from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

print("=== Sessioni Scalping IN ESECUZIONE ===")
res = sb.table('scalping_sessions').select('*').eq('status', 'running').execute()
if res.data:
    for s in res.data:
        print(f"ID: {s['id'][:8]}... Symbol: {s['symbol']} Mode: {s['mode']} Started: {s.get('started_at', 'N/A')}")
else:
    print("NESSUNA sessione scalping in esecuzione (status=running)")

print("\n=== Sessioni Scalping IN PAUSA ===")
res = sb.table('scalping_sessions').select('*').eq('status', 'paused').execute()
if res.data:
    for s in res.data:
        print(f"ID: {s['id'][:8]}... Symbol: {s['symbol']} Mode: {s['mode']}")
else:
    print("Nessuna sessione in pausa")

print("\n=== Ultimi 5 trades chiusi ===")
res = sb.table('scalping_trades').select('*').eq('status', 'closed').limit(5).execute()
for t in (res.data or []):
    print(f"{t['symbol']} {t['side']} P&L: {t['pnl_pct']}% ({t['entry_time'][:16]})")

print("\n=== Strategie disponibili nel registry ===")
res = sb.table('strategies').select('*').eq('status', 'ACTIVE').execute()
print(res.data if res.data else 'Nessuna strategia con status ACTIVE')