import logging
import sys
from pythonjsonlogger import jsonlogger
from app.config import settings

def setup_logging():
    """
    TASK-296: Configura il logging strutturato in formato JSON.
    """
    handler = logging.StreamHandler(sys.stdout)
    
    # Formato JSON con i campi richiesti
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    
    handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # Disabilitiamo i log ridondanti di uvicorn/access se necessario
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.error").handlers = [handler]

    logging.info("Structured logging initialized")
