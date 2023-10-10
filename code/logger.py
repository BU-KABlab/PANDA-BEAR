"""Singleton logger for the ePANDDA project."""
import logging

class CustomLogger:
    _logger = None

    @classmethod
    def get_logger(cls):
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
            cls._logger.setLevel(logging.DEBUG)  # Change as needed
            formatter = logging.Formatter(
                "%(asctime)s:%(name)s:%(levelname)s:%(custom1)s:%(custom2)s:%(message)s"
            )
            system_handler = logging.FileHandler("code/logs/ePANDA.log")
            system_handler.setFormatter(formatter)
            cls._logger.addHandler(system_handler)

        return cls._logger