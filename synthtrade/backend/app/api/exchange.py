from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.config import settings
from app.execution.exchange import BinanceExchangeAdapter

router = APIRouter(prefix="/exchange", tags=["exchange"])

@router.get("/status")
async def get_exchange_status(_user: str = Depends(get_current_user)):
    """
    TASK-090: GET /api/exchange/status
    """
    adapter = BinanceExchangeAdapter(
        api_key=settings.BINANCE_API_KEY,
        secret=settings.BINANCE_SECRET_KEY,
        testnet=settings.BINANCE_TESTNET
    )
    
    try:
        balance = await adapter.get_balance()
        status_data = {
            "mode": "testnet" if settings.BINANCE_TESTNET else "live",
            "base_url": settings.binance_base_url,
            "usdt_balance": balance
        }
        return status_data
    finally:
        await adapter.close()
