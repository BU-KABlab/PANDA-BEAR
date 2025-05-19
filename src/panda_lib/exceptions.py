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


class OCPError(Exception):
    """Raised when OCP fails"""

    def __init__(self, stage):
        self.stage = stage
        self.message = f"OCP failed before {stage}"
        super().__init__(self.message)


class OCPFailure(Exception):
    """Raised when OCP fails"""

    def __init__(self, experiment_id, well_id):
        self.experiment_id = experiment_id
        self.well_id = well_id
        self.message = f"OCP failed for experiment {experiment_id} well {well_id}"
        super().__init__(self.message)


class NoAvailableSolution(Exception):
    """Raised when no available solution is found"""

    def __init__(self, solution_name):
        self.solution_name = solution_name
        self.message = f"No available solution of {solution_name} found"
        super().__init__(self.message)


class ImageCaptureError(Exception):
    """Raised when image capture fails"""

    def __init__(self, well_id):
        self.well_id = well_id
        self.message = f"Image capture failed for well {well_id}"
        super().__init__(self.message)


class DepositionFailure(Exception):
    """Raised when deposition fails"""

    def __init__(self, experiment_id, well_id):
        self.experiment_id = experiment_id
        self.well_id = well_id
        self.message = (
            f"Deposition failed for experiment {experiment_id} well {well_id}"
        )
        super().__init__(self.message)


class CAFailure(Exception):
    """Raised when CA fails"""

    def __init__(self, experiment_id, well_id):
        self.experiment_id = experiment_id
        self.well_id = well_id
        self.message = f"CA failed for experiment {experiment_id} well {well_id}"
        super().__init__(self.message)


class CVFailure(Exception):
    """Raised when CV fails"""

    def __init__(self, experiment_id, well_id):
        self.experiment_id = experiment_id
        self.well_id = well_id
        self.message = f"CV failed for experiment {experiment_id} well {well_id}"
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


class StopCommand(Exception):
    """Raised when a stop command is issued"""

    def __init__(self, message="Stop command issued"):
        self.message = message
        super().__init__(self.message)


class InstrumentConnectionError(Exception):
    """Raised when the instrument connection fails"""

    def __init__(self, message="Instrument connection fails"):
        self.message = message
        super().__init__(self.message)


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


class ExperimentNotFoundError(Exception):
    """Raised when the experiment is not found"""

    def __init__(self, message="Experiment not found"):
        self.message = message
        super().__init__(self.message)


class ExperimentError(Exception):
    """Raised when the experiment fails"""

    def __init__(self, message="Experiment failed"):
        self.message = message
        super().__init__(self.message)
