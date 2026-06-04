import os
from pathlib import Path
from dotenv import load_dotenv
import ccxt.async_support as ccxt
import asyncio

base = Path('synthtrade/backend')
load_dotenv(base / '.env')
api_key = os.getenv('BINANCE_API_KEY_LIVE') or os.getenv('BINANCE_API_KEY')
secret = os.getenv('BINANCE_SECRET_KEY_LIVE') or os.getenv('BINANCE_SECRET_KEY')
print('api', bool(api_key), 'secret', bool(secret))
if not api_key or not secret:
    raise SystemExit('missing api keys')

async def main():
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'},
    })
    exchange.set_sandbox_mode(False)
    bal = await exchange.fetch_balance()
    total = bal.get('total', {})
    free = bal.get('free', {})

    print('balance keys', list(bal.keys())[:20])
    print('total type', type(total))
    print('total count', len(total))
    for name in ['USDC', 'USDT', 'BUSD', 'FDUSD']:
        print(f'{name} total raw =', repr(total.get(name)))
    print('free type', type(free))
    print('free count', len(free))
    for name in ['USDC', 'USDT', 'BUSD', 'FDUSD']:
        print(f'{name} free raw =', repr(free.get(name)))

    print('Nonzero total assets')
    nonzero_total = [(k, v) for k, v in total.items() if isinstance(v, (int, float)) and v > 0]
    nonzero_total.sort(key=lambda x: x[1], reverse=True)
    print(nonzero_total[:40])

    print('LD assets with total >0')
    ld_assets = [(k, v) for k, v in total.items() if k.startswith('LD') and isinstance(v, (int, float)) and v > 0]
    print(ld_assets[:40])

    print('Assets containing USDC/USDT/BUSD/FDUSD')
    found = [(k, v) for k, v in total.items() if any(x in k for x in ['USDC', 'USDT', 'BUSD', 'FDUSD'])]
    print(found[:80])
    await exchange.close()

asyncio.run(main())
