"""
Vessel module.
"""
import logging
from config.config import PATH_TO_LOGS
# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
file_handler = logging.FileHandler(PATH_TO_LOGS / 'vessel.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class Vessel:
    """
    Represents a vessel object.

    Attributes:
        name (str): The name of the vessel.
        volume (float): The current volume of the vessel.
        capacity (float): The maximum capacity of the vessel.
        density (float): The density of the solution in the vessel.
        coordinates (dict): The coordinates of the vessel. 
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
    update_contents(solution: 'Vessel', volume: float) -> None
        Updates the contents of the vessel.

    """
    def __init__(self, name: str, volume: float, capacity: float, density: float, coordinates: dict, contents, depth: float = 0) -> None:
        self.name = name
        self.volume = volume
        self.capacity = capacity
        self.density = density
        self.viscosity_cp = 0.0
        self.coordinates = coordinates
        self.contents = contents
        self.depth = depth

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"

    def update_volume(self, added_volume: float) -> None:
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(self.name, self.volume, added_volume, self.capacity)
        else:
            self.volume += added_volume
            logger.info("%s:%s", self.name, self.volume)

            return self
    def calculate_depth(self) -> float:
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
            raise OverFillException(self.name, self.volume, volume_to_add, self.capacity)
        elif self.volume + volume_to_add < 0:
            raise OverDraftException(self.name, self.volume, volume_to_add, self.capacity)
        else:
            return True

    def write_volume_to_disk(self) -> None:
        """
        Writes the current volume of the vessel to the appropriate file.
        """
        pass

    def update_contamination(self, new_contamination: int = None) -> None:
        """
        Updates the contamination count of the vessel.

        Parameters:
        -----------
        new_contamination (int, optional): The new contamination count of the vessel.
        """
        pass

    def update_contents(self, solution_name: str, volume: float) -> None:
        """
        Updates the contents of the vessel.

        Parameters:
        -----------
        solution_name (str): The name of the solution to be added to the vessel.
        volume (float): The volume of the solution to be added to the vessel.
        """
        # check if the solution_name already exists in the vessel's contents dict, if so update the volume by adding the new volume
        pass

    def get_contents(self) -> dict:
        """
        Returns the contents of the vessel.

        Returns:
        --------
        dict: The contents of the vessel.
        """
        return self.contents

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