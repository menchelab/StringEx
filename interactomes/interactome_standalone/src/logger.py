import logging
import os
import sys
from logging import DEBUG
from logging.handlers import RotatingFileHandler

_LOG_DEBUG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)s - %(funcName)s()] %(message)s"
_LOG_DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_LOG_LEVEL = DEBUG

_LOG_FORMAT = _LOG_DEBUG_FORMAT
F_LOG_LEVEL = _LOG_LEVEL
C_LOG_LEVEL = _LOG_LEVEL

def get_logger(
    name: str = "StringEx",
    level: int = logging.DEBUG,
    c_level: int = logging.WARNING,
    f_level: int = logging.ERROR,
    format: str = None,
) -> logging.Logger:
    """Initialize the StringEx Logger.

    Args:
        name (str, optional): Name of the Logger. Defaults to "StringEx".
        level (int, optional): Level of the Logging. Defaults to logging.DEBUG.
        c_level (int, optional): Level of the console logging. Defaults to logging.WARNING.
        f_level (int, optional): Level of the log file logging. Defaults to logging.ERROR.
        format (str, optional): Format string to use for printing logs. Defaults to None.

    Returns:
        logging.Logger: _description_
    """
    main_log = os.path.join("logs", "StringEx.log")
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Create handlers
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = RotatingFileHandler(
        main_log,
        mode="a",
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding=None,
        delay=0,
    )
    c_handler.setLevel(c_level)
    f_handler.setLevel(f_level)

    # Create formatters and add it to handlers
    if format:
        log_format = logging.Formatter(format)
        c_handler.setFormatter(log_format)
        f_handler.setFormatter(log_format)
    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger

log = get_logger(
    level=_LOG_LEVEL, f_level=F_LOG_LEVEL, c_level=C_LOG_LEVEL, format=_LOG_FORMAT
)