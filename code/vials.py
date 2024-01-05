"""
Vial class for creating vial objects with their position and contents
"""
# pylint: disable=line-too-long
import json
import logging
import math

from config.file_locations import STOCK_STATUS_FILE, WASTE_STATUS_FILE

# set up A logger for the vials module
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
# formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
# system_handler = logging.FileHandler("code/logs/ePANDA.log")
# system_handler.setFormatter(formatter)
# logger.addHandler(system_handler)
vial_logger = logging.getLogger("e_panda")

class Vial:
    """
    Class for creating vial objects with their position and contents

    Args:
        position (str): The position of the vial.
        x_coord (float): The x-coordinate of the vial's position.
        y_coord (float): The y-coordinate of the vial's position.
        contents (str): The contents of the vial.
        volume (float, optional): The current volume of the vial in ml. Defaults to 0.00.
        capacity (int, optional): The maximum capacity of the vial in ml. Defaults to 20000.
        radius (int, optional): The radius of the vial in mm. Defaults to 14.
        height (int, optional): The height of the vial in mm. Defaults to -20.
        z_bottom (int, optional): The z-coordinate of the bottom of the vial. Defaults to -75.
        name (str, optional): The name of the vial. Defaults to "vial".
        contamination (int, optional): The contamination level of the vial. Defaults to 0.
        filepath (str, optional): The filepath to the vial file. Defaults to None.
        density (float, optional): The density of the vial's contents in g/ml. Defaults to 1.0.

    Attributes:
        name (str): The name of the vial.
        position_name (str): The position name of the vial.
        coordinates (dict): The coordinates of the vial {x:#, y:#, z:#}.
        bottom (int): The z-coordinate of the bottom of the vial.
        contents (str): The contents of the vial.
        capacity (int): The maximum capacity of the vial in ml.
        radius (int): The radius of the vial in mm.
        height (int): The height of the vial in mm.
        volume (float): The current volume of the vial in ml.
        density (float): The density of the vial's contents in g/ml.
        base (float): The base area of the vial.
        depth (float): The current depth of the liquid in the vial.
        contamination (int): The contamination level of the vial.
        filepath (str): The filepath to the vial file.

    Methods:
        position() -> dict:
            Returns the coordinates of the vial.
        check_volume(added_volume: float) -> bool:
            Checks if the added volume can fit in the vial.
        write_volume_to_disk() -> int:
            Writes the current volume to a json file.
        update_volume(added_volume_ul: float) -> int:
            Updates the volume of the vial.
        vial_depth_calculator(diameter_mm, volume_ul) -> float:
            Calculates the height of a volume of liquid in a vial given its diameter (in mm).

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
            self.vial_depth_calculator(self.radius * 2, self.volume)
        )
        self.contamination = contamination
        self.filepath = filepath

    @property
    def position(self) -> dict:
        """
        Returns
        -------
        DICT
            x, y, z-height

        """
        return self.coordinates

    def check_volume(self, added_volume: float) -> bool:
        """
        Updates the volume of the vial
        """
        logging_msg = f"Checking if {added_volume} can fit in {self.name} ..."
        vial_logger.info(logging_msg)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )
        else:
            logging_msg = f"{added_volume} can fit in {self.name}"
            vial_logger.info(logging_msg)
            return True

    def write_volume_to_disk(self) -> int:
        """
        Writes the current volume to a json file
        """
        # logging.info(f'Writing {self.name} volume to {self.filepath}...')
        # with open(self.filepath, 'w') as f:
        #     json.dump(self.volume, f, indent=4)
        # return 0
        vial_logger.info("Writing %s volume to vial file...", self.name)

        ## Open the file and read the contents
        with open(self.filepath, "r", encoding="UTF-8") as file:
            solutions = json.load(file)

        ## Find matching solution name and update the volume
        # solutions = solutions['solutions']
        for solution in solutions:
            if solution["name"] == self.name and solution["position"] == self.position_name:
                solution["volume"] = self.volume
                solution["contamination"] = self.contamination
                break

        ## Write the updated contents back to the file
        with open(self.filepath, "w", encoding="UTF-8") as file:
            json.dump(solutions, file, indent=4)
        return 0

    def update_volume(self, added_volume_ul: float) -> int:
        """
        Updates the volume of the vial.
        Args:
            added_volume (float): volume (ul) to be added to the vial
        """
        vial_logger.info("Updating %s volume...", self.name)
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
            self.vial_depth_calculator((self.radius * 2), self.volume)
        )
        if self.depth < self.bottom:
            self.depth = self.bottom
        vial_logger.debug(
            "%s: New volume: %s | New depth: %s", self.name, self.volume, self.depth
        )
        self.contamination += 1
        return 0

    def vial_depth_calculator(self, diameter_mm, volume_ul) -> float:
        """
        Calculates the height of a volume of liquid in a vial given its diameter (in mm).
        """
        # radius_mm = diameter_mm / 2
        # area_mm2 = 3.141592653589793 * radius_mm**2
        # volume_mm3 = abs(volume_ul)  # 1 ul = 1 mm3
        # liquid_height_mm = round(volume_mm3 / area_mm2, 3)
        # return liquid_height_mm + self.bottom
        return self.bottom

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

    def update_contents(self, solution: 'Vessel', volume: float) -> None:
        """
        Updates the contents of the vessel.

        Parameters:
        -----------
        solution_name (str): The name of the solution to be added to the vessel.
        volume (float): The volume of the solution to be added to the vessel.
        """
        # check if the solution_name already exists in the vessel's contents dict, if so update the volume by adding the new volume
        pass

class Vial2(Vessel):
    """
    Represents a vial object that inherits from the Vessel class.

    Attributes:
        name (str): The name of the vial.
        category (int): The category of the vial (0 for stock, 1 for waste).
        volume (float): The current volume of the vial.
        capacity (float): The maximum capacity of the vial.
        density (float): The density of the solution in the vial.
        coordinates (dict): The coordinates of the vial.
        radius (float): The radius of the vial.
        height (float): The height of the vial.
        z_bottom (float): The z-coordinate of the bottom of the vial.
        base (float): The base area of the vial.
        depth (float): The current depth of the solution in the vial.
        contamination (int): The number of times the vial has been contaminated.
        category (int): The category of the vial (0 for stock, 1 for waste).

    Methods:
    --------
    update_volume(added_volume: float) -> None
        Updates the volume of the vial by adding the specified volume.
    calculate_depth() -> float
        Calculates the current depth of the solution in the vial.
    check_volume(volume_to_add: float) -> bool
        Checks if the volume to be added to the vial is within the vial's capacity.
    write_volume_to_disk() -> None
        Writes the current volume and contamination of the vial to the appropriate file.
    update_contamination(new_contamination: int = None) -> None
        Updates the contamination count of the vial.
    update_contents(solution: 'Vessel', volume: float) -> None
        Updates the contents of the vial.

    """

    def __init__(self, name: str, category: int, position: str, volume: float, capacity: float, density: float,
                 coordinates: dict, radius: float, height: float, z_bottom: float, contamination: int, contents, viscocity_rank: int = 0, x: float = 0, y: float = 0, depth: float = 0) -> None:
        """
        Initializes a new instance of the Vial2 class.

        Args:
            name (str): The name of the vial.
            category (int): The category of the vial (0 for stock, 1 for waste).
            position (str): The position of the vial.
            volume (float): The current volume of the vial.
            capacity (float): The maximum capacity of the vial.
            density (float): The density of the solution in the vial.
            coordinates (dict): The coordinates of the vial.
            radius (float): The radius of the vial.
            height (float): The height of the vial.
            z_bottom (float): The z-coordinate of the bottom of the vial.
            contamination (int): The number of times the vial has been contaminated.
            contents: The contents of the vial.
            viscocity_rank (int, optional): The viscosity rank of the vial. Defaults to 0.
            x (float, optional): The x-coordinate of the vial. Defaults to 0.
            y (float, optional): The y-coordinate of the vial. Defaults to 0.
        """
        super().__init__(name, volume, capacity, density, coordinates, contents=contents)
        self.position = position
        self.radius = radius
        self.height = height
        self.z_bottom = z_bottom
        self.base = round(math.pi * math.pow(self.radius, 2.0), 6)
        self.depth = self.calculate_depth()
        self.contamination = contamination
        self.category = category
        self.viscosity_rank = viscocity_rank
        self.x = x
        self.y = y

    def calculate_depth(self) -> float:
        """
        Calculates the current depth of the solution in the vial.

        Returns:
        --------
            float: The current depth of the solution in the vial.
        """
        radius_mm = self.radius
        area_mm2 = math.pi * radius_mm ** 2
        volume_mm3 = self.volume
        height = round(volume_mm3 / area_mm2, 4)
        depth = height + self.z_bottom - 2
        if depth < self.z_bottom + 1:
            depth = self.z_bottom + 1
        # FIXME return depth
        return self.z_bottom

    def check_volume(self, volume_to_add: float) -> bool:
        """
        Checks if the volume to be added to the vial is within the vial's capacity.

        Args:
        -----
        volume_to_add (float): The volume to be added to the vial.

        Returns:
            bool: True if the volume to be added is within the vial's capacity, False otherwise.
        """
        if self.volume + volume_to_add > self.capacity:
            raise OverFillException(self.name, self.volume, volume_to_add, self.capacity)
        elif self.volume + volume_to_add < 0:
            raise OverDraftException(self.name, self.volume, volume_to_add, self.capacity)
        else:
            return True

    def update_volume(self, added_volume: float) -> None:
        """
        Updates the volume of the vial by adding the specified volume.

        Parameters:
        -----------
        added_volume : float
            The volume to be added to the vial.
        """
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(self.name, self.volume, added_volume, self.capacity)
        else:
            self.volume += added_volume
            self.depth = self.calculate_depth()
            self.contamination += 1
            vial_logger.debug("%s: New volume: %s | New depth: %s", self.name, self.volume, self.depth)
            return self

    def write_volume_to_disk(self) -> None:
        """
        Writes the current volume and contamination of the vial to the appropriate file.
        """
        vial_logger.info("Writing %s volume to vial file...", self.name)
        vial_file_path = STOCK_STATUS_FILE if self.category == 0 else WASTE_STATUS_FILE

        with open(vial_file_path, "r", encoding="UTF-8") as file:
            solutions = json.load(file)

        for solution in solutions:
            if solution["name"] == self.name and solution["position"] == self.position:
                solution["volume"] = self.volume
                solution["contamination"] = self.contamination
                solution["depth"] = self.depth
                #solution["contents"] = self.contents
                break

        with open(vial_file_path, "w", encoding="UTF-8") as file:
            json.dump(solutions, file, indent=4)

    def update_contamination(self, new_contamination: int = None) -> None:
        """
        Updates the contamination count of the vial.

        Parameters:
        -----------
        new_contamination (int, optional): The new contamination count of the vial.
        """
        if new_contamination is not None:
            self.contamination = new_contamination
        else:
            self.contamination += 1
        return self

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"

class StockVial(Vial2):
    """
    Represents a stock vial object that inherits from the Vial2 class.

    Attributes:
        name (str): The name of the stock vial.
        volume (float): The current volume of the stock vial.
        capacity (float): The maximum capacity of the stock vial.
        density (float): The density of the solution in the stock vial.
        coordinates (dict): The coordinates of the stock vial.
        radius (float): The radius of the stock vial.
        height (float): The height of the stock vial.
        z_bottom (float): The z-coordinate of the bottom of the stock vial.
        base (float): The base area of the stock vial.
        depth (float): The current depth of the solution in the stock vial.
        contamination (int): The number of times the stock vial has been contaminated.
        category (int): The category of the stock vial (0 for stock, 1 for waste).
    """

    def __init__(self, name: str, position:str, volume: float, capacity: float, density: float,
                 coordinates: dict, radius: float, height: float, z_bottom: float, contamination: int, contents:str) -> None:
        """
        Initializes a new instance of the StockVial class.

        Args:
        name (str): The name of the stock vial.
        volume (float): The current volume of the stock vial.
        capacity (float): The maximum capacity of the stock vial.
        density (float): The density of the solution in the stock vial.
        coordinates (dict): The coordinates of the stock vial.
        radius (float): The radius of the stock vial.
        height (float): The height of the stock vial.
        z_bottom (float): The z-coordinate of the bottom of the stock vial.
        """
        super().__init__(name, 0, position, volume, capacity, density, coordinates, radius, height, z_bottom, contamination, contents=contents)
        self.category = 0
    def update_contents(self, solution: Vessel, volume: float) -> None:
        "Stock vial contents don't change"
        return self
class WasteVial(Vial2):
    """
    Represents a waste vial object that inherits from the Vial2 class.

    Attributes:
        name (str): The name of the waste vial.
        volume (float): The current volume of the waste vial.
        capacity (float): The maximum capacity of the waste vial.
        density (float): The density of the solution in the waste vial.
        coordinates (dict): The coordinates of the waste vial.
        radius (float): The radius of the waste vial.
        height (float): The height of the waste vial.
        z_bottom (float): The z-coordinate of the bottom of the waste vial.
        base (float): The base area of the waste vial.
        depth (float): The current depth of the solution in the waste vial.
        contamination (int): The number of times the waste vial has been contaminated.
        category (int): The category of the waste vial (0 for stock, 1 for waste).
    """

    def __init__(self, name: str, position:str, volume: float, capacity: float, density: float,
                 coordinates: dict, radius: float, height: float, z_bottom: float, contamination: int, contents: dict = {}) -> None:
        """
        Initializes a new instance of the WasteVial class.

        Args:
        name (str): The name of the waste vial.
        volume (float): The current volume of the waste vial.
        capacity (float): The maximum capacity of the waste vial.
        density (float): The density of the solution in the waste vial.
        coordinates (dict): The coordinates of the waste vial.
        radius (float): The radius of the waste vial.
        height (float): The height of the waste vial.
        z_bottom (float): The z-coordinate of the bottom of the waste vial.
        """
        super().__init__(name, 1, position, volume, capacity, density, coordinates, radius, height, z_bottom, contamination, contents=contents)
        self.category = 1

    def update_contents(self, solution: Vessel, volume: float) -> None:
        vial_logger.debug("Updating %s %s contents...", self.name, self.position)
        if solution.name in self.contents:
            self.contents[solution.name] += volume

        # otherwise, add the solution to the vessel's contents dictionary
        else:
            self.contents[solution.name] = volume
        vial_logger.debug("%s %s: New contents: %s", self.name, self.position, self.contents)
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
