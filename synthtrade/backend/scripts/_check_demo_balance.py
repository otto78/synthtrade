import asyncio, sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
from app.execution.okx_exchange import OkxExchangeAdapter

async def check():
    a = OkxExchangeAdapter(
        api_key=os.environ['OKX_API_KEY'],
        secret=os.environ['OKX_SECRET_KEY'],
        passphrase=os.environ['OKX_PASSPHRASE'],
        demo=True
    )
    bal = await a.get_balance('EUR')
    print('EUR balance:', bal)
    holdings = await a.get_holdings()
    print('Holdings:', holdings)

asyncio.run(check())
