"""
Vessel module.
"""

from dataclasses import dataclass
from typing import Union

from panda_lib.errors import OverDraftException, OverFillException
from panda_shared.log_tools import setup_default_logger

# Set up the logger
logger = setup_default_logger(log_name="vessel")


class VesselLogger:
    """
    A class to create a logger for vessel-like objects.
    """

    def __init__(self, name):
        self.logger = setup_default_logger(log_name=name)


# Create an instance of the logger for the vessel module
logger = VesselLogger("vessel").logger


@dataclass
class VesselCoordinates:
    """
    Represents the coordinates of a vessel.

    Args:
    -----
        x (Union[int, float, float]): The x-coordinate of the vessel.
        y (Union[int, float, float]): The y-coordinate of the vessel.
        z (Union[int, float, float]): The z-coordinate of the vessel base.
    """

    x: Union[int, float]
    y: Union[int, float]
    z: Union[int, float]
    top: Union[int, float] = 0
    bottom: Union[int, float] = 0

    def __post_init__(self):
        self.x = round(self.x, 6)
        self.y = round(self.y, 6)
        self.z = round(self.z, 6)
        self.top = round(self.top, 6)
        self.bottom = round(self.bottom, 6)

    def __getitem__(self, key: str) -> Union[int, float]:
        """Allows subscripting the WellCoordinates for attributes."""
        return getattr(self, key)

    def as_json(self):
        """Returns the VesselCoordinates as a dictionary with double quotes."""
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
        }


class Vessel:
    """
    Represents a vessel object.

    Attributes:
        name (str): The name of the vessel.
        volume (float): The current volume of the vessel.
        capacity (float): The maximum capacity of the vessel.
        density (float): The density of the solution in the vessel.
        coordinates (Union[VesselCoordinates, dict]): The coordinates of the vessel.
        contents (dict): The contents of the vessel.
        depth (float): The current depth of the solution in the vessel.

    Methods:
    --------
    update_volume(added_volume: float) -> None
        Updates the volume of the vessel by adding the specified volume.
    calculate_depth() -> float
        Calculates the current depth of the solution in the vessel.
    check_volume(volume_to_add: float) -> bool
        Checks if the volume to be added to the vessel is within the vessel's capacity.
    write_volume_to_disk() -> None
        Writes the current volume of the vessel to the appropriate file.
    update_contamination(new_contamination: int = None) -> None
        Updates the contamination count of the vessel.
    update_contents(from_vessel: str, volume: float) -> None
        Updates the contents of the vessel.
    get_contents() -> dict
        Returns the contents of the vessel.
    log_contents() -> None
        Logs the contents of the vessel.

    """

    def __init__(
        self,
        name: str,
        volume: float,
        capacity: float,
        density: float,
        coordinates: Union[VesselCoordinates, dict],
        contents={},
    ) -> None:
        self.position = None
        self.category = None
        self.name = name.lower() if name is not None else ""
        self.contents = contents
        self.viscosity_cp = float(0.0)
        self.concentration = float(0.0)
        self._density = density
        self.height = 0.0
        self.radius = 0.0
        self._volume = volume
        self.capacity = capacity
        self.contamination = 0
        self.coordinates = coordinates
        self.base_thickness = 0.0
        self.volume_height = 0.0
        self.top = 0.0
        self.bottom = 0.0

        if isinstance(self.coordinates, dict):
            self.coordinates = VesselCoordinates(**coordinates)
        else:
            pass

    def round_to_6(func):
        def wrapper(self, value):
            return func(self, round(value, 6) if value is not None else 0)

        return wrapper

    @property
    def volume(self):
        return self._volume

    @volume.setter
    @round_to_6
    def volume(self, value):
        self._volume = value

    @property
    def density(self):
        return self._density

    @density.setter
    @round_to_6
    def density(self, value):
        self._density = value

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"

    def update_volume(self, added_volume: float) -> None:
        """Updates the volume of the vessel by adding the specified volume."""
        added_volume = round(added_volume, 6)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        if self.volume + added_volume < float(0):
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )

        self.volume = self.volume + added_volume
        logger.debug(
            "%s&%s",
            self.name + "_" + self.position if self.position is not None else self.name,
            self.volume,
        )

    def check_volume(self, volume_to_add: float) -> bool:
        """
        Checks if the volume to be added to the vessel is within the vessel's capacity.

        Args:
        -----
        volume_to_add (float): The volume to be added to the vessel.

        Returns:
            bool: True if the volume to be added is within the vessel's capacity, False otherwise.
        """
        if self.volume + volume_to_add > self.capacity:
            raise OverFillException(
                self.name, self.volume, volume_to_add, self.capacity
            )
        if self.volume + volume_to_add < float(0):
            raise OverDraftException(
                self.name, self.volume, volume_to_add, self.capacity
            )
        return True

    def write_volume_to_disk(self) -> None:
        """
        Writes the current volume of the vessel to the appropriate file.
        """
        # Different vessels will have different implementations of this method
        pass

    def update_contamination(self, new_contamination: int = None) -> None:
        """
        Updates the contamination count of the vessel.

        Parameters:
        -----------
        new_contamination (int, optional): The new contamination count of the vessel.
        """
        # Different vessels will have different implementations of this method due to
        # the different ways they save to the db
        pass

    def update_contents(
        self, from_vessel: str, volume: float, save: bool = False
    ) -> None:
        """
        Updates the contents of the vessel.

        Parameters:
        -----------
        from_vessel (str): The name of the vessel from which the solution is being transferred.
        volume (float): The volume of the solution to be added to the vessel.
        """
        # Different vessels will have different implementations of this method
        pass

    def log_contents(self) -> None:
        """Logs the contents of the vessel."""
        logger.debug(
            "%s&%s&%s",
            self.name + "_" + self.position if self.position is not None else self.name,
            self.volume,
            self.contents,
        )
