import asyncio
import logging
from app.config import settings
from app.execution.okx_order_event_stream import OkxOrderEventStream

logging.basicConfig(level=logging.DEBUG)

async def main():
    stream = OkxOrderEventStream(
        api_key=settings.exchange_api_key,
        secret=settings.exchange_secret_key,
        passphrase=settings.exchange_passphrase,
        demo=True,
        eu=True,
    )
    
    async def on_order(event):
        print("ORDER UPDATE:", event)
        
    await stream.start(on_order)
    
    # Let it run for 10 seconds to see if polling kicks in (it should hit WS login error or just poll if we force it)
    await asyncio.sleep(10)
    await stream.stop()

if __name__ == "__main__":
    asyncio.run(main())
