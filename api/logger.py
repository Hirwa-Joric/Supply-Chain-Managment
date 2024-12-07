import logging
import sys
from .config import settings

def setup_logger(name: str) -> logging.Logger:
    """Setup and return a logger instance"""
    logger = logging.getLogger(name)
    
    # Set log level from settings
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

# Create a default logger instance
logger = setup_logger("scm_api")
