"""
Vial class for creating vial objects with their position and contents
"""
# pylint: disable=line-too-long
import json
import logging
import math

from config.file_locations import STOCK_STATUS_FILE, WASTE_STATUS_FILE

# set up A logger for the vials module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

class Vial:
    """
    Class for creating vial objects with their position and contents

    Args:
        x
        y
        contents
        volume in ml
        capacity in ml

    """

    def __init__(
        self,
        position: str,
        x_coord: float,
        y_coord: float,
        contents: str,
        volume=0.00,
        capacity=20000,
        radius=14,
        height=-20,
        z_bottom=-75,
        name="vial",
        contamination=0,
        filepath=None,
        density=1.0,  # g/ml
    ):
        self.name = name
        self.position_name = position
        self.coordinates = {"x": x_coord, "y": y_coord, "z": height}
        self.bottom = z_bottom
        self.contents = contents
        self.capacity = capacity
        self.radius = radius
        self.height = height
        self.volume = volume
        self.density = density
        self.base = math.pi * math.pow(self.radius, 2.0)
        self.depth = (
            self.vial_height_calculator(self.radius * 2, self.volume) + self.bottom
        )
        self.contamination = contamination
        self.filepath = filepath

    @property
    def position(self):
        """
        Returns
        -------
        DICT
            x, y, z-height

        """
        return self.coordinates

    def check_volume(self, added_volume: float):
        """
        Updates the volume of the vial
        """
        logging_msg = f"Checking if {added_volume} can fit in {self.name} ..."
        logger.info(logging_msg)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )
        else:
            logging_msg = f"{added_volume} can fit in {self.name}"
            logger.info(logging_msg)
            return True

    def write_volume_to_disk(self):
        """
        Writes the current volume to a json file
        """
        # logging.info(f'Writing {self.name} volume to {self.filepath}...')
        # with open(self.filepath, 'w') as f:
        #     json.dump(self.volume, f, indent=4)
        # return 0
        logger.info("Writing %s volume to vial file...", self.name)

        ## Open the file and read the contents
        with open(self.filepath, "r", encoding="UTF-8") as file:
            solutions = json.load(file)

        ## Find matching solution name and update the volume
        # solutions = solutions['solutions']
        for solution in solutions:
            if solution["name"] == self.name:
                solution["volume"] = self.volume
                solution["contamination"] = self.contamination
                break

        ## Write the updated contents back to the file
        with open(self.filepath, "w", encoding="UTF-8") as file:
            json.dump(solutions, file, indent=4)
        return 0

    def update_volume(self, added_volume_ul: float):
        """
        Updates the volume of the vial.
        Args:
            added_volume (float): volume (ul) to be added to the vial
        """
        logger.info("Updating %s volume...", self.name)
        if self.volume + added_volume_ul > self.capacity:
            raise OverFillException(
                self.name, self.volume, added_volume_ul, self.capacity
            )
        if self.volume + added_volume_ul < 0:
            raise OverDraftException(
                self.name, self.volume, added_volume_ul, self.capacity
            )
        self.volume += round(added_volume_ul, 3)
        # self.write_volume_to_disk()
        self.depth = (
            self.vial_height_calculator((self.radius * 2), self.volume) + self.bottom
        )
        if self.depth < self.bottom:
            self.depth = self.bottom
        logger.debug(
            "%s: New volume: %s | New depth: %s", self.name, self.volume, self.depth
        )
        self.contamination += 1
        return 0

    def vial_height_calculator(self, diameter_mm, volume_ul):
        """
        Calculates the height of a volume of liquid in a vial given its diameter (in mm).
        """
        radius_mm = diameter_mm / 2
        area_mm2 = 3.141592653589793 * radius_mm**2
        volume_mm3 = volume_ul  # 1 ul = 1 mm3
        liquid_height_mm = round(volume_mm3 / area_mm2, 3)
        return liquid_height_mm
class Vessel:
    """
    The vessel class is a simple container for holding liquid
    It has the following attributes:
    - name
    - volume
    - capacity
    - density
    - coordinates
    """

    def __init__(
        self,
        name: str,
        volume: float,
        capacity: float,
        density: float,
        coordinates: dict,
    ) -> None:
        self.name = name
        self.volume = volume
        self.capacity = capacity
        self.density = density
        self.coordinates = coordinates

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"

    def update_volume(self, added_volume: float) -> None:
        """
        Updates the volume of the vessel
        """
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )
        else:
            self.volume += added_volume
            return self

class Vial2(Vessel):
    """A vial object that inherits from the Vessel class"""

    def __init__(
        self,
        name: str,
        category: int,
        volume: float,
        capacity: float,
        density: float,
        coordinates: dict,
        radius: float,
        height: float,
        z_bottom: float,
    ) -> None:
        super().__init__(name, volume, capacity, density, coordinates)
        self.radius = radius
        self.height = height
        self.z_bottom = z_bottom
        self.base = round(math.pi * math.pow(self.radius, 2.0),6)
        self.depth = self.vial_depth_calculator()
        self.contamination = 0
        self.category = category

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"

    def vial_depth_calculator(self):
        """
        Calculates the depth of a volume of liquid in a vial given the vial diameter (in mm).
        """
        radius_mm = self.radius
        area_mm2 = math.pi * radius_mm**2
        volume_mm3 = self.volume  # 1 ul = 1 mm3
        self.depth = round(volume_mm3 / area_mm2, 3)
        return self.depth

    def check_volume(self, volume_to_add: float):
        """
        Updates the volume of the vial
        """
        logging_msg = f"Checking if {volume_to_add} can fit in {self.name} ..."
        logger.debug(logging_msg)
        if self.volume + volume_to_add > self.capacity:
            raise OverFillException(self.name, self.volume, volume_to_add, self.capacity)
        elif self.volume + volume_to_add < 0:
            raise OverDraftException(
                self.name, self.volume, volume_to_add, self.capacity
            )
        else:
            logging_msg = f"{volume_to_add} can fit in {self.name}"
            logger.debug(logging_msg)
            return True

    def update_volume(self, added_volume: float) -> None:
        """
        Updates the volume of the vial and updates the contamination
        """
        logger.debug("Updating %s volume...", self.name)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )
        else:
            self.volume += added_volume
            self.depth = self.vial_depth_calculator()
            self.contamination += 1
            logger.debug("%s: New volume: %s | New depth: %s", self.name, self.volume, self.depth)
            return self

    def write_volume_to_disk(self):
        """
        Writes the current volume to a json file
        """
        logger.info("Writing %s volume to vial file...", self.name)

        # Get the correct file path
        if self.category == 0:
            vial_file_path = STOCK_STATUS_FILE
        elif self.category == 1:
            vial_file_path = WASTE_STATUS_FILE

        ## Open the file and read the contents
        with open(vial_file_path, "r", encoding="UTF-8") as file:
            solutions = json.load(file)

        ## Find matching solution name and update the volume
        # solutions = solutions['solutions']
        for solution in solutions:
            if solution["name"] == self.name:
                solution["volume"] = self.volume
                solution["contamination"] = self.contamination
                break

        ## Write the updated contents back to the file
        with open(vial_file_path, "w", encoding="UTF-8") as file:
            json.dump(solutions, file, indent=4)
        return 0

    def update_contamination(self, new_contamination: int = None):
        """
        Updates the contamination of the vial
        """
        if new_contamination is not None:
            self.contamination = new_contamination
        self.contamination += 1
        return self

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
