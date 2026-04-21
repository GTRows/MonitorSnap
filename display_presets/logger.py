import logging
import sys
from logging.handlers import RotatingFileHandler
from display_presets.config import get_app_dir

_LOG_FILE = get_app_dir() / 'debug.log'
_MAX_BYTES = 1_000_000  # ~1 MB
_BACKUP_COUNT = 1

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding='utf-8',
        ),
        logging.StreamHandler(sys.stderr),
    ],
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
