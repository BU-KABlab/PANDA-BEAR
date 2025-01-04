"""Possible errors for the epanda system."""


class WellImportError(Exception):
    """Raised when the wellplate status file does not have the correct number of wells"""

    def __init__(
        self, message="Wellplate status file does not have the correct number of wells"
    ):
        self.message = message
        super().__init__(self.message)


class NoAvailableSolution(Exception):
    """Raised when no available solution is found"""

    def __init__(self, solution_name):
        self.solution_name = solution_name
        self.message = f"No available solution of {solution_name} found"
        super().__init__(self.message)


class OverFillException(Exception):
    """Raised when a vessel if over filled"""

    def __init__(self, name, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.name = name
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self) -> str:
        return f"OverFillException: {self.name} has {self.volume} + {self.added_volume} > {self.capacity}"


class OverDraftException(Exception):
    """Raised when a vessel if over drawn"""

    def __init__(self, name, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.name = name
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self) -> str:
        return f"OverDraftException: {self.name} has {self.volume} + {self.added_volume} < 0"


class MismatchWellplateTypeError(Exception):
    """Raised when the wellplate type does not match the experiment's desired type"""

    def __init__(self, message="Wellplate does not have the correct type of wells"):
        self.message = message
        super().__init__(self.message)


class InsufficientVolumeError(Exception):
    """Raised when the vessel does not have enough volume"""

    def __init__(self, message="Vessel does not have enough volume"):
        self.message = message
        super().__init__(self.message)
