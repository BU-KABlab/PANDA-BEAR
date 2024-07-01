"""
Methods and classses related to logging for the ePANDA project
"""

import logging
import configparser

config = configparser.ConfigParser()
config.read("config/panda_sdl_config.ini")

if config.getboolean("OPTIONS", "testing"):
    EPANDA_LOG = config.get("PATHS_TESTING", "logging_dir")
else:
    EPANDA_LOG = config.get("PATHS_PRODUCTION", "logging_dir")


def setup_default_logger(
    log_file=EPANDA_LOG,
    log_name="panda_logger",
    file_level=logging.DEBUG,
    console_level=logging.INFO,
):
    """
    Set up a logger with a file handler and a stream handler.

    Args:
        log_file (str): The path to the log file.
        log_name (str): The name of the logger.

    Returns:
        logging.Logger: The logger.

    """
    logger = logging.getLogger(log_name)
    logger.setLevel(file_level)  # change to INFO to reduce verbosity
    formatter = logging.Formatter(
        "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&&&&%(message)s&"
    )
    # The file handler will write to the log file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # The stream handler will print to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)
    return logger


default_logger = setup_default_logger(EPANDA_LOG)


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
