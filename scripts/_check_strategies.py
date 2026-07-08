"""Check for existing strategies in Supabase."""
import sys, os, json, httpx
from pathlib import Path
from dotenv import load_dotenv

env_path = Path('synthtrade/backend/.env')
load_dotenv(env_path)

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
headers = {'apikey': key, 'Authorization': 'Bearer ' + key, 'Accept': 'application/json'}
rest_url = url + '/rest/v1'

print('=== STRATEGIE ESISTENTI ===')
r = httpx.get(rest_url + '/strategies', headers=headers, params={
    'select': 'id,pair,status,budget_eur,strategy_type,created_at',
    'order': 'created_at.desc',
    'limit': 20
})
data = r.json() if r.text and r.text != '[]' else []
for s in data:
    sid = s['id'][:8]
    pair = s.get('pair', '?')
    status = s.get('status', '?')
    stype = s.get('strategy_type', '?')
    budget = s.get('budget_eur', '?')
    created = str(s.get('created_at', '?'))[:19]
    print(f'ID: {sid} | Pair: {pair} | Status: {status} | Type: {stype} | Budget: {budget} | Created: {created}')
if not data:
    print('Nessuna strategia trovata.')

print()
print('=== SESSIONI SCALPING RECENTI ===')
r2 = httpx.get(rest_url + '/scalping_sessions', headers=headers, params={
    'select': 'id,mode,symbol,status,trade_count,started_at',
    'order': 'started_at.desc',
    'limit': 5
})
data2 = r2.json() if r2.text and r2.text != '[]' else []
for s in data2:
    sid = s['id'][:8]
    print(f'ID: {sid} | Mode: {s["mode"]} | Symbol: {s["symbol"]} | Status: {s["status"]} | Trades: {s.get("trade_count",0)} | Started: {str(s["started_at"])[:19]}')
if not data2:
    print('Nessuna sessione scalping.')

# Cleanup
os.remove(__file__)