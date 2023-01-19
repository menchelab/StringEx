import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_RUNTIME_FORMAT = "%(message)s"


def get_logger(
    name: str = "StringEx",
    level: int = logging.DEBUG,
    c_level: int = logging.WARNING,
    f_level: int = logging.ERROR,
    r_level: int = logging.DEBUG,
    format: str = None,
    log_file: str = "StringEx.log",
    runtimes_files: str = "StringEx_runtimes.log",
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
    os.makedirs("logs", exist_ok=True)
    main_log = os.path.join("logs", log_file)
    runtimes_log = os.path.join("logs", runtimes_files)
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
    r_handler = RotatingFileHandler(
        runtimes_log,
        mode="a",
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
        encoding=None,
        delay=0,
    )
    c_handler.setLevel(c_level)
    f_handler.setLevel(f_level)
    r_handler.setLevel(r_level)
    # Create formatters and add it to handlers
    if format:
        log_format = logging.Formatter(format)
        c_handler.setFormatter(log_format)
        f_handler.setFormatter(log_format)

    r_handler.setFormatter(logging.Formatter(_RUNTIME_FORMAT))

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)
    logger.addHandler(r_handler)

    return logger
