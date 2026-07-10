import logging
import sys
from core.config import settings

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("autotrip")
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    
    if settings.debug:
        level = logging.DEBUG
        
    logger.setLevel(level)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.propagate = False
    
    return logger

logger = setup_logger()
