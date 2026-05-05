from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.config import settings

ALGORITHM = "HS256"


def create_access_token(expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta if expires_delta is not None
        else timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    return jwt.encode({"exp": expire, "sub": "user"}, settings.JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> bool:
    try:
        jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False
