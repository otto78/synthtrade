"""Quick check for scalping sessions after cleanup."""
import sys
from pathlib import Path

sys.path = [p for p in sys.path if p not in ('.', '', str(Path.cwd()))]

from dotenv import load_dotenv
load_dotenv('synthtrade/backend/.env')

import os
import importlib
supabase_pkg = importlib.import_module('supabase')

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
client = supabase_pkg.create_client(url, key)

print('=== TUTTE LE SESSIONI (ultime 10) ===')
res = client.table('scalping_sessions').select('*').order('started_at', desc=True).limit(10).execute()
if res.data:
    for s in res.data:
        sid = str(s.get('id', '?'))[:8]
        print(
            f"ID: {sid} | "
            f"Mode: {s.get('mode','?')} | "
            f"Symbol: {s.get('symbol','?')} | "
            f"Status: {s.get('status','?')} | "
            f"Started: {s.get('started_at','?')} | "
            f"Stopped: {s.get('stopped_at','?')} | "
            f"PnL: {s.get('total_pnl','?')} | "
            f"Trades: {s.get('trade_count','?')}"
        )
else:
    print('Nessuna sessione trovata.')

print()
print('=== TRADE ASSOCIATI (ultimi 10) ===')
res2 = client.table('scalping_trades').select('*').order('entry_time', desc=True).limit(10).execute()
if res2.data:
    for t in res2.data:
        tid = str(t.get('id', '?'))[:8]
        sid = str(t.get('session_id', ''))[:8] if t.get('session_id') else 'N/A'
        print(
            f"ID: {tid} | "
            f"Session: {sid} | "
            f"Symbol: {t.get('symbol','?')} | "
            f"Side: {t.get('side','?')} | "
            f"Status: {t.get('status','?')} | "
            f"Entry: {t.get('entry_price','?')} | "
            f"Exit: {t.get('exit_price','?')} | "
            f"PnL: {t.get('pnl','?')}"
        )
else:
    print('Nessun trade trovato.')