from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.core.auth_utils import create_access_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login(body: LoginRequest):
    if not body.password or body.password != settings.APP_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    return {"access_token": create_access_token(), "token_type": "bearer"}
