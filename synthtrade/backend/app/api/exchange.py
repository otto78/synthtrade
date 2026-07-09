from fastapi import APIRouter, Depends, HTTPException, Request
from app.dependencies import get_current_user, get_exchange
from app.config import settings
from app.execution.exchange_factory import build_exchange_adapter
from app.execution.exchange import ExchangeAuthError, ExchangeNetworkError

router = APIRouter(prefix="/exchange", tags=["exchange"])


@router.get("/status")
async def get_exchange_status(_user: str = Depends(get_current_user)):
    """
    TASK-090: GET /api/exchange/status
    """
    adapter = build_exchange_adapter()
    try:
        balance = await adapter.get_balance()
        provider = settings.EXCHANGE_PROVIDER.upper()
        mode_label = "Demo" if settings.TRADING_MODE == 'test' else "Live"
        return {
            "mode": mode_label,
            "provider": provider,
            "base_url": settings.OKX_BASE_URL if settings.EXCHANGE_PROVIDER == "okx" else settings.binance_base_url,
            "usdt_balance": balance,
        }
    finally:
        await adapter.close()


@router.get("/holdings")
async def get_holdings(
    request: Request,
    _user: str = Depends(get_current_user),
):
    """
    TASK-413: GET /api/exchange/holdings
    Restituisce il saldo libero di tutte le crypto nel wallet.
    Esempio: { "BTC": 0.015, "ETH": 0.5, "USDT": 1200.0 }
    Usa il singleton exchange da app.state (TASK-409).
    """
    exchange = get_exchange(request)
    try:
        holdings = await exchange.get_holdings()
        return {"holdings": holdings, "mode": "testnet" if settings.TRADING_MODE == 'test' else "live"}
    except ExchangeAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ExchangeNetworkError as e:
        raise HTTPException(status_code=503, detail=f"Exchange non raggiungibile: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
