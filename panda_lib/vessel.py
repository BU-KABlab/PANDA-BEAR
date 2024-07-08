"""
Vessel module.
"""
from dataclasses import dataclass
from typing import Any, Union, Optional
from panda_lib.errors import OverFillException, OverDraftException
from panda_lib.log_tools import setup_default_logger

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
        z_top (Union[int, float, float], optional): The z-coordinate of top the vessel.
        z_bottom (Union[int, float, float], optional): The z-coordinate of the bottom of the vessel.
    """

    x: Union[int, float]
    y: Union[int, float]
    z_top: Union[int, float] = 0
    z_bottom: Optional[Union[int, float]] = None

    def __post_init__(self):
        if self.z_bottom is None:
            self.z_bottom = 0

        self.x = round(self.x, 6)
        self.y = round(self.y, 6)
        self.z_top = round(self.z_top, 6)
        self.z_bottom = round(self.z_bottom, 6)

    def __getitem__(self, key: str) -> Union[int, float]:
        """Allows subscripting the WellCoordinates for attributes."""
        return getattr(self, key)

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
        depth: float = float(0),
    ) -> None:
        self.name = name.lower() if name is not None else ""
        self.position = None
        self.volume = volume
        self.capacity = capacity
        self.density = density
        self.viscosity_cp = float(0.0)
        if isinstance(coordinates, dict):
            self.coordinates = VesselCoordinates(**coordinates)
        else:
            self.coordinates = coordinates

        self.contents = contents
        self.depth = depth

        # Round all floats to 6 decimal places
        self.volume = round(self.volume, 6) if self.volume is not None else 0
        self.capacity = round(self.capacity, 6) if self.capacity is not None else 0
        self.density = round(self.density, 6) if self.density is not None else 0
        self.depth = round(self.depth, 6) if self.depth is not None else 0

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"

    def update_volume(self, added_volume: float) -> None:
        """Updates the volume of the vessel by adding the specified volume."""
        added_volume = round(added_volume,6)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        if self.volume + added_volume < float(0):
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )

        self.volume = round(self.volume + added_volume, 6)
        logger.info(
            "%s&%s",
            self.name + "_" + self.position if self.position is not None else self.name,
            self.volume,
        )

        return self

    def calculate_depth(self) -> float:
        """Calculates the current depth of the solution in the vessel."""
        # Different vessels will have different implementations of this method
        pass

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

    def update_contents(self, from_vessel: str, volume: float, save:bool = False) -> None:
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
        logger.info(
            "%s&%s&%s",
            self.name + "_" + self.position if self.position is not None else self.name,
            self.volume,
            self.contents,
        )
