"""
Methods and classses related to logging for the ePANDA project
"""
import logging

class CustomLoggingFilter(logging.Filter):
    """This is a filter which injects custom values into the log record.
    From: https://stackoverflow.com/questions/56776576/how-to-add-custom-values-to-python-logging
    The values will be the experiment id and the well id
    """

    def __init__(self, custom1, custom2):
        super().__init__()
        self.custom1 = custom1
        self.custom2 = custom2

    def filter(self, record):
        record.custom1 = self.custom1
        record.custom2 = self.custom2
        return True
