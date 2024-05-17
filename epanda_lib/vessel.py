"""
Vessel module.
"""

from decimal import Decimal
import logging
from typing import Union
from .config.config import PATH_TO_LOGS
from .errors import OverFillException, OverDraftException


class VesselLogger:
    """
    A class to create a logger for vessel-like objects.
    """

    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s&%(name)s&%(module)s&%(funcName)s&%(lineno)d&%(message)s"
        )
        file_handler = logging.FileHandler(PATH_TO_LOGS / f"{name}.log")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)


# Create an instance of the logger for the vessel module
logger = VesselLogger("vessel").logger


class VesselCoordinates:
    """
    Represents the coordinates of a vessel.

    Args:
    -----
        x (Decimal): The x-coordinate of the vessel.
        y (Decimal): The y-coordinate of the vessel.
        z_top (Decimal): The z-coordinate of top the vessel.
        z_bottom (Decimal): The z-coordinate of the bottom of the vessel.
    """

    def __init__(
        self,
        x: Decimal,
        y: Decimal,
        z_top: Decimal = Decimal(0),
        z_bottom: Decimal = None,
    ) -> None:
        """Initializes a new instance of the Coordinates class."""
        self.x = x
        self.y = y
        self.z_top = z_top
        self.z_bottom = z_bottom

    def __str__(self) -> str:
        """Returns a string representation of the coordinates."""
        return f'"x"={self.x}, "y"={self.y}, "z_top"={self.z_top}, "z_bottom"={self.z_bottom}'

    def __repr__(self) -> str:
        """Returns a string representation of the coordinates."""
        return f'"x"={self.x}, "y"={self.y}, "z_top"={self.z_top}, "z_bottom"={self.z_bottom}'

    def __dict__(self) -> dict:
        """Returns a dictionary representation of the coordinates."""
        return {
            "x": self.x,
            "y": self.y,
            "z_top": self.z_top,
            "z_bottom": self.z_bottom,
        }

    def __getitem__(self, key: str) -> Decimal:
        """Returns the value of the specified key."""
        return getattr(self, key)

    def __setitem__(self, key: str, value: Decimal) -> None:
        """Sets the value of the specified key."""
        setattr(self, key, value)

    def __iter__(self):
        return iter([self.x, self.y, self.z_top, self.z_bottom])

    def __len__(self):
        return 4

    def __eq__(self, other: "VesselCoordinates") -> bool:
        """Returns True if the coordinates are equal, False otherwise."""
        return all(
            [
                self.x == other.x,
                self.y == other.y,
                self.z_top == other.z_top,
                self.z_bottom == other.z_bottom,
            ]
        )

    def __ne__(self, other: "VesselCoordinates") -> bool:
        """Returns True if the coordinates are not equal, False otherwise."""
        return not self.__eq__(other)


class Vessel:
    """
    Represents a vessel object.

    Attributes:
        name (str): The name of the vessel.
        volume (Decimal): The current volume of the vessel.
        capacity (Decimal): The maximum capacity of the vessel.
        density (Decimal): The density of the solution in the vessel.
        coordinates (Union[VesselCoordinates, dict]): The coordinates of the vessel.
        contents (dict): The contents of the vessel.
        depth (Decimal): The current depth of the solution in the vessel.

    Methods:
    --------
    update_volume(added_volume: Decimal) -> None
        Updates the volume of the vessel by adding the specified volume.
    calculate_depth() -> Decimal
        Calculates the current depth of the solution in the vessel.
    check_volume(volume_to_add: Decimal) -> bool
        Checks if the volume to be added to the vessel is within the vessel's capacity.
    write_volume_to_disk() -> None
        Writes the current volume of the vessel to the appropriate file.
    update_contamination(new_contamination: int = None) -> None
        Updates the contamination count of the vessel.
    update_contents(from_vessel: str, volume: Decimal) -> None
        Updates the contents of the vessel.
    get_contents() -> dict
        Returns the contents of the vessel.
    log_contents() -> None
        Logs the contents of the vessel.

    """

    def __init__(
        self,
        name: str,
        volume: Decimal,
        capacity: Decimal,
        density: Decimal,
        coordinates: Union[VesselCoordinates, dict],
        contents={},
        depth: Decimal = Decimal(0),
    ) -> None:
        self.name = name.lower() if name is not None else ""
        self.position = None
        self.volume = volume
        self.capacity = capacity
        self.density = density
        self.viscosity_cp = Decimal(0.0)
        if isinstance(coordinates, dict):
            self.coordinates = VesselCoordinates(**coordinates)
        else:
            self.coordinates = coordinates

        self.contents = contents
        self.depth = depth

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"

    def update_volume(self, added_volume: Decimal) -> None:
        """Updates the volume of the vessel by adding the specified volume."""
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        if self.volume + added_volume < Decimal(0):
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )

        self.volume += added_volume
        logger.info(
            "%s&%s",
            self.name + "_" + self.position if self.position is not None else self.name,
            self.volume,
        )

        return self

    def calculate_depth(self) -> Decimal:
        """Calculates the current depth of the solution in the vessel."""
        # Add your implementation here
        pass

    def check_volume(self, volume_to_add: Decimal) -> bool:
        """
        Checks if the volume to be added to the vessel is within the vessel's capacity.

        Args:
        -----
        volume_to_add (Decimal): The volume to be added to the vessel.

        Returns:
            bool: True if the volume to be added is within the vessel's capacity, False otherwise.
        """
        if self.volume + volume_to_add > self.capacity:
            raise OverFillException(
                self.name, self.volume, volume_to_add, self.capacity
            )
        if self.volume + volume_to_add < Decimal(0):
            raise OverDraftException(
                self.name, self.volume, volume_to_add, self.capacity
            )
        return True

    def write_volume_to_disk(self) -> None:
        """
        Writes the current volume of the vessel to the appropriate file.
        """
        # Add your implementation here
        pass

    def update_contamination(self, new_contamination: int = None) -> None:
        """
        Updates the contamination count of the vessel.

        Parameters:
        -----------
        new_contamination (int, optional): The new contamination count of the vessel.
        """
        # Add your implementation here
        pass

    def update_contents(self, from_vessel: str, volume: Decimal) -> None:
        """
        Updates the contents of the vessel.

        Parameters:
        -----------
        from_vessel (str): The name of the vessel from which the solution is being transferred.
        volume (Decimal): The volume of the solution to be added to the vessel.
        """
        # Add your implementation here
        pass

    def get_contents(self) -> dict:
        """
        Returns the contents of the vessel.

        Returns:
        --------
        dict: The contents of the vessel.
        """
        return self.contents

    def log_contents(self) -> None:
        """Logs the contents of the vessel."""
        logger.info(
            "%s&%s&%s",
            self.name + "_" + self.position if self.position is not None else self.name,
            self.volume,
            self.contents,
        )
