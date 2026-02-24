import logging
from backend.utils.config import config

def setup_logger(name: str) -> logging.Logger:
    """Set up and return a configured logger."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        level = config.get('logging.level', 'INFO')
        format_str = config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, level))

        formatter = logging.Formatter(format_str)
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level))

    return logger
