"""
Methods and classses related to logging for the PANDA_SDL project
"""

import logging
import os
import time
from panda_lib.config import config_tools
from functools import wraps
from typing import Optional

config = config_tools.read_config()


if config.getboolean("OPTIONS", "testing"):
    PANDA_SDL_LOG = config.get("TESTING", "logging_dir")
else:
    PANDA_SDL_LOG = config.get("PRODUCTION", "logging_dir")


def setup_default_logger(
    log_file="panda.log",
    log_name="panda",
    file_level=config.get("LOGGING", "file_level"),
    console_level=config.get("LOGGING", "console_level"),
):
    """Setup a default logger for the PANDA_SDL project"""

    if not os.path.exists(PANDA_SDL_LOG):
        os.makedirs(PANDA_SDL_LOG)
    logger = logging.getLogger(log_name)
    if not logger.handlers:  # Check if the logger already has handlers attached
        logger.setLevel(file_level)
        formatter = logging.Formatter(
            "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&&&&%(message)s&"
        )
        # Set the converter to use UTC
        formatter.converter = time.gmtime
        file_handler = logging.FileHandler(PANDA_SDL_LOG + "/" + log_name + ".log")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(file_level)
        file_handler.set_name("file_handler")
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.set_name("console_handler")
        console_formatter = logging.Formatter("%(message)s")
        console_formatter.converter = time.gmtime
        console_handler.setFormatter(
            console_formatter
        )  # Ensure console output is formatted
        logger.addHandler(console_handler)

    return logger


default_logger = setup_default_logger()


class CustomLoggingFilter(logging.Filter):
    """This is a filter which injects custom values into the log record.
    From: https://stackoverflow.com/questions/56776576/how-to-add-custom-values-to-python-logging
    The values will be the experiment id and the well id
    """

    def __init__(self, custom1, custom2, custom3, custom4):
        super().__init__()
        self.custom1 = custom1
        self.custom2 = custom2
        self.custom3 = custom3
        self.custom4 = custom4

    def filter(self, record):
        record.custom1 = self.custom1
        record.custom2 = self.custom2
        record.custom3 = self.custom3
        record.custom4 = self.custom4
        return True


def apply_log_filter(
    logger: logging.Logger,
    experiment_id: int = None,
    target_well: Optional[str] = None,
    campaign_id: Optional[str] = None,
    test: Optional[bool] = config.getboolean("OPTIONS", "testing"),
):
    """Add custom value to log format"""
    experiment_formatter = logging.Formatter(
        "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(custom1)s&%(custom2)s&%(custom3)s&%(message)s&%(custom4)s"
    )

    logger_handlers = logger.handlers
    for handler in logger_handlers:
        if handler.get_name() == "console_handler":
            # Dont add the filter to the console handler
            continue
        handler.setFormatter(experiment_formatter)
        custom_filter = CustomLoggingFilter(
            campaign_id, experiment_id, target_well, test
        )
        handler.addFilter(custom_filter)


def timing_wrapper(func):
    """A decorator that logs the time taken for a function to execute"""
    timing_logger = setup_default_logger(
        log_file="timing.log",
        log_name="timing",
        file_level=logging.DEBUG,
        console_level=logging.ERROR,
    )

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        timing_logger.info(
            "%s,%s,%s, %.4f", func.__name__, start_time, end_time, elapsed_time
        )
        return result

    return wrapper
