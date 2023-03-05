import logging
import os
import sys
from logging import StreamHandler
from logging.handlers import RotatingFileHandler

_RUNTIME_FORMAT = "%(message)s"


class CustomLogger(logging.Logger):
    def __init__(self, name, console_format="%(message)s", level=logging.NOTSET):
        super().__init__(name, level)
        self.console_format = console_format

    def _log(
        self,
        level,
        msg,
        args,
        exc_info=None,
        extra=None,
        stack_info=False,
        runtime=False,
        flush=False,
    ):
        if runtime:
            msg = f"{self.name} - {msg}"
        # for idx, handler in enumerate(self.handlers):
        #     if not isinstance(handler, RotatingFileHandler):
        #         LINE_UP = "\033[1A"
        #         LINE_CLEAR = "\x1b[2K"
        #         format = logging.Formatter(LINE_UP + LINE_CLEAR + self.console_format)
        #         self.handlers[idx].setFormatter(format)
        #         self.handlers[idx].terminator = "\n"
        #     if not flush:
        #         self.handlers[idx].terminator = "\n\n"
        super()._log(level, msg, args, exc_info, extra, stack_info)


def get_logger(
    name: str = "StringEx",
    level: int = logging.DEBUG,
    c_level: int = logging.WARNING,
    f_level: int = logging.ERROR,
    r_level: int = logging.INFO,
    format: str = None,
    c_format: str = None,
    log_file: str = "StringEx.log",
    runtimes_files: str = "StringEx_runtimes.log",
) -> logging.Logger:
    """Initialize the StringEx Logger.

    Args:
        name (str, optional): Name of the Logger. Defaults to "StringEx".
        level (int, optional): Level of the Logging. Defaults to logging.DEBUG.
        c_level (int, optional): Level of the console logging. Defaults to logging.WARNING.
        f_level (int, optional): Level of the log file logging. Defaults to logging.ERROR.
        r_level (int, optional): Level of the runtimes file logging. Defaults to logging.DEBUG.
        format (str, optional): Format string to use for printing logs. Defaults to None.
        log_file (str, optional): Name of the log file. Defaults to "StringEx.log".
        runtimes_files (str, optional): Name of the runtimes file. Defaults to "StringEx_runtimes.log".

    Returns:
        logging.Logger: logger object
    """
    os.makedirs("logs", exist_ok=True)
    main_log = os.path.join("logs", log_file)
    runtimes_log = os.path.join("logs", runtimes_files)
    logger = CustomLogger(name, c_format, level)

    # Create handlers
    c_handler = StreamHandler(sys.stdout)
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

    if c_format:
        c_format = logging.Formatter(c_format)
        c_handler.setFormatter(c_format)

    r_handler.setFormatter(logging.Formatter(_RUNTIME_FORMAT))

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)
    logger.addHandler(r_handler)

    return logger
