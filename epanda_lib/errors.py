"""Possible errors for the epanda system."""
class ProtocolNotFoundError(Exception):
    """Error raised when a protocol is not found in the database."""
    def __init__(self, message="Protocol not found in the database"):
        self.message = message
        super().__init__(self.message)

class WellImportError(Exception):
    """Raised when the wellplate status file does not have the correct number of wells"""

    def __init__(
        self, message="Wellplate status file does not have the correct number of wells"
    ):
        self.message = message
        super().__init__(self.message)


class ShutDownCommand(Exception):
    """Raised when the system is commanded to shut down"""

    def __init__(self, message="The system has been commanded to shut down"):
        self.message = message
        super().__init__(self.message)

class NoExperimentFromModel(Exception):
    """Raised when the ML model does not generate a new experiment"""

    def __init__(self, message="The ML model did not generate a new experiment"):
        self.message = message
        super().__init__(self.message)