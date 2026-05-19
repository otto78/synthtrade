import logging
import sys
# from pythonjsonlogger import jsonlogger

def setup_logging():
    # Ensure stdout uses UTF-8 encoding for Unicode characters like emojis
    sys.stdout.reconfigure(encoding='utf-8')
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
