from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.auth_utils import verify_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if not credentials or not verify_token(credentials.credentials):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return "user"


from app.db.supabase_client import get_supabase
from app.db.repositories.strategy_repository import StrategyRepository
from app.db.repositories.trade_repository import TradeRepository
from app.db.repositories.ohlcv_repository import OhlcvRepository
from app.services.market_data_service import MarketDataService

def get_db():
    """TASK-033: Returns the Supabase client singleton."""
    return get_supabase()


def get_strategy_repo(db=Depends(get_db)):
    """TASK-035: Returns the StrategyRepository."""
    return StrategyRepository(db)


def get_trade_repo(db=Depends(get_db)):
    """TASK-035: Returns the TradeRepository."""
    return TradeRepository(db)


def get_ohlcv_repo(db=Depends(get_db)):
    """TASK-038: Returns the OhlcvRepository."""
    return OhlcvRepository(db)


def get_engine(request: Request):
    """TASK-409: Restituisce il singleton ExecutionEngine da app.state."""
    return request.app.state.engine


def get_exchange(request: Request):
    """TASK-409: Restituisce il singleton BinanceExchangeAdapter da app.state."""
    return request.app.state.exchange


def get_market_data_service(
    repo=Depends(get_ohlcv_repo),
    exchange=Depends(get_exchange)
):
    """TASK-038: Returns the MarketDataService."""
    return MarketDataService(repo, exchange)
