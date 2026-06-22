from typing import Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from httpx import RemoteProtocolError, ConnectError as HttpxConnectError
import logging
import traceback

logger = logging.getLogger(__name__)

# Errori di connessione transitori (DB, API esterne) — no stack trace
# RemoteProtocolError: connessione HTTP/2 drop
# HttpxConnectError: DNS non risolvibile (getaddrinfo failed)
_QUIET_ERRORS = (RemoteProtocolError, HttpxConnectError)

class SynthTradeError(Exception):
    """Base exception for SynthTrade"""
    def __init__(self, message: str, code: str = "internal_error"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class RiskViolationError(SynthTradeError):
    """Raised when a risk limit is violated"""
    def __init__(self, message: str):
        super().__init__(message, code="risk_violation")

class ModelUnavailableError(SynthTradeError):
    """Raised when AI models are unavailable"""
    def __init__(self, message: str):
        super().__init__(message, code="ai_unavailable")

class OrderExecutionError(SynthTradeError):
    """Raised when an order fails to execute"""
    def __init__(self, message: str):
        super().__init__(message, code="order_failed")

async def global_exception_handler(request: Request, exc: Exception):
    """
    TASK-301: Handler globale Exception
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    # Errori di connessione transitori (es. Supabase HTTP/2 drop) — log ridotto
    if isinstance(exc, _QUIET_ERRORS):
        logger.warning(
            f"Transient connection error: {exc} [request_id={request_id}]"
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "error": "upstream_disconnected",
                "message": "Servizio temporaneamente non disponibile, riprova.",
                "request_id": request_id
            }
        )
    
    logger.error(f"Unhandled error: {exc}", extra={"request_id": request_id, "stack_trace": traceback.format_exc()})
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": request_id
        }
    )

async def http_exception_handler(request: Request, exc: Any):
    """
    TASK-302: Handler HTTPException
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail,
            "request_id": request_id
        }
    )

async def validation_exception_handler(request: Request, exc: Any):
    """
    TASK-303: Handler RequestValidationError
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "details": errors,
            "request_id": request_id
        }
    )

async def synthtrade_exception_handler(request: Request, exc: Any):
    """Custom exception handler for SynthTrade specific errors"""
    request_id = request.headers.get("X-Request-ID", "unknown")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": exc.code,
            "message": exc.message,
            "request_id": request_id
        }
    )
