import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Coroutine, Any

logger = logging.getLogger("synthtrade.ai.retry")

P = ParamSpec("P")
R = TypeVar("R")

def async_retry(max_retries: int = 3, backoff_base: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Decoratore per retry asincrono con exponential backoff.
    """
    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries.")
                        raise e
                    
                    delay = backoff_base ** attempt
                    logger.warning(f"Retry {attempt+1}/{max_retries} for {func.__name__} due to {e}. Waiting {delay}s...")
                    await asyncio.sleep(delay)
            # This line should logically not be reached if max_retries is respected
            return await func(*args, **kwargs)
        return wrapper
    return decorator
