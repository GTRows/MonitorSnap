import logging
import sys
from display_presets.config import get_app_dir

_LOG_FILE = get_app_dir() / 'debug.log'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stderr),
    ],
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
