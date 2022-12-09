import logging
import os
import sys


def get_logger(
    name="StringEx",
    level=logging.DEBUG,
    c_level=logging.WARNING,
    f_level=logging.ERROR,
    format=None,
):
    main_log = os.path.join("logs", "StringEx.log")
    os.makedirs(os.path("logs"), exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Create handlers
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = logging.FileHandler(main_log, "w")
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
