from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.auth_utils import verify_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if not credentials or not verify_token(credentials.credentials):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return "user"


def get_engine(request: Request):
    """TASK-409: Restituisce il singleton ExecutionEngine da app.state."""
    return request.app.state.engine


def get_exchange(request: Request):
    """TASK-409: Restituisce il singleton BinanceExchangeAdapter da app.state."""
    return request.app.state.exchange
