"""
Vial class for creating vial objects with their position and contents
"""
# pylint: disable=line-too-long
import json
import logging
import math
from typing import Sequence, Union
from pathlib import Path
from config.config import STOCK_STATUS, WASTE_STATUS
from vessel import Vessel, OverDraftException, OverFillException

# set up A logger for the vials module
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
# formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
# system_handler = logging.FileHandler("code/logs/ePANDA.log")
# system_handler.setFormatter(formatter)
# logger.addHandler(system_handler)
vial_logger = logging.getLogger("e_panda")

class Vial2(Vessel):
    """
    Represents a vial object that inherits from the Vessel class.

    Attributes:
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
        viscosity_cp (float, optional): The viscosity of the vial contents. Defaults to 0.0.
        x (float, optional): The x-coordinate of the vial. Defaults to 0.
        y (float, optional): The y-coordinate of the vial. Defaults to 0.

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
                 coordinates: dict, radius: float, height: float, z_bottom: float, contamination: int, contents, viscosity_cp: float = 0.0, x: float = 0, y: float = 0, depth: float = 0) -> None:
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
            viscosity_cp (float, optional): The viscosity of the vial contents. Defaults to 0.0.
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
        self.viscosity_cp = viscosity_cp
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
        super().update_volume(added_volume)
        self.depth = self.calculate_depth()
        self.write_volume_to_disk()
        return self

    def write_volume_to_disk(self) -> None:
        """
        Writes the current volume and contamination of the vial to the appropriate file.
        """
        vial_logger.info("Writing %s volume to vial file...", self.name)
        vial_file_path = STOCK_STATUS if self.category == 0 else WASTE_STATUS

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
                 coordinates: dict, radius: float, height: float, z_bottom: float, contamination: int, contents:str, viscosity_cp:float = 0.0) -> None:
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
        super().__init__(name, 0, position, volume, capacity, density, coordinates, radius, height, z_bottom, contamination, contents=contents, viscosity_cp=viscosity_cp)
        self.category = 0
    def update_contents(self, from_vessel: str, volume: float) -> None:
        "Stock vial contents don't change"
        self.log_contents()
        return self

    def get_contents(self) -> dict:
        """Return the contents of the stock vial as a dictionary"""
        return {self.name: self.volume}

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
                 coordinates: dict, radius: float, height: float, z_bottom: float, contamination: int, contents: dict = {}, viscosity_cp:float = 0.0) -> None:
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
        super().__init__(name, 1, position, volume, capacity, density, coordinates, radius, height, z_bottom, contamination, contents=contents, viscosity_cp=viscosity_cp)
        self.category = 1

    def update_contents(self, from_vessel: Union[str,dict], volume: float) -> None:
        """Update the contentes of the waste vial"""
        vial_logger.debug("Updating %s %s contents...", self.name, self.position)

        if isinstance(from_vessel, dict):
            try:
                # incoming_content_ratios = {
                #     key: value / sum(from_vessel.values()) for key, value in from_vessel.items()
                # }

                for key, value in from_vessel.items():
                    if key in self.contents:
                        self.contents[key] += round((value), 6)
                    else:
                        self.contents[key] = round((value), 6)

            except Exception as e:
                vial_logger.error("Error occurred while updating well contents: %s", e)
                vial_logger.error("Not critical, continuing....")

        else: # from_vessel is a string
            if from_vessel in self.contents:
                self.contents[from_vessel] += volume
            else:
                self.contents[from_vessel] = volume
        vial_logger.debug("%s %s: New contents: %s", self.name, self.position, self.contents)

        # Update the file
        update_vial_state_file([self], WASTE_STATUS)
        self.log_contents()
        
        return self

def read_vials(filename) -> Sequence[Union[StockVial, WasteVial]]:
    """
    Read in the virtual vials from the json file
    """
    filename_ob = Path.cwd() / filename
    with open(filename_ob, "r", encoding="ascii") as file:
        vial_parameters = json.load(file)

    list_of_solutions = []
    for items in vial_parameters:
        if items["name"] is not None:
            if items["category"] == 0:
                read_vial = StockVial(
                    name=str(items["name"]).lower(),
                    position=str(items["position"]).lower(),
                    volume=items["volume"],
                    capacity=items["capacity"],
                    density=items["density"],
                    coordinates={"x": items["x"], "y": items["y"]},
                    z_bottom=items["z_bottom"],
                    radius=items["radius"],
                    height=items["height"],
                    contamination=items["contamination"],
                    contents=items["contents"],
                    viscosity_cp=items["viscosity_cp"],
                )
                list_of_solutions.append(read_vial)
            elif items["category"] == 1:
                read_vial = WasteVial(
                    name=str(items["name"]).lower(),
                    position=str(items["position"]).lower(),
                    volume=items["volume"],
                    capacity=items["capacity"],
                    density=items["density"],
                    coordinates={"x": items["x"], "y": items["y"]},
                    z_bottom=items["z_bottom"],
                    radius=items["radius"],
                    height=items["height"],
                    contamination=items["contamination"],
                    contents=items["contents"],
                    viscosity_cp=items["viscosity_cp"],
                )
                list_of_solutions.append(read_vial)
    return list_of_solutions


def update_vial_state_file(vial_objects: Sequence[Vial2], filename):
    """
    Update the vials in the json file. This is used to update the volume, contents, and contamination of the vials
    """
    filename_ob = Path.cwd() / filename
    with open(filename_ob, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    for vial in vial_objects:
        for vial_param in vial_parameters:
            if str(vial_param["position"]) == vial.position.lower():
                vial_param["volume"] = vial.volume
                vial_param["contamination"] = vial.contamination
                vial_param["contents"] = vial.contents
                break

    with open(filename_ob, "w", encoding="UTF-8") as file:
        json.dump(vial_parameters, file, indent=4)

    return 0


def input_new_vial_values(vialgroup: str):
    """For user inputting the new vial values for the state file"""
    ## Fetch the current state file
    filename = ""
    if vialgroup == "stock":
        filename = STOCK_STATUS
    elif vialgroup == "waste":
        filename = WASTE_STATUS
    else:
        vial_logger.error("Invalid vial group")
        raise ValueError

    with open(filename, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    ## Print the current vials and their values
    print("Current vials:")
    print(
        f"{'Position':<10} {'Name':<20} {'Contents':<20} {'Density':<15} {'Volume':<15} {'Capacity':<15} {'Contamination':<15}"
    )
    for vial in vial_parameters:
        vial = Vial2(**vial)
        if vial.contents is None:
            vial.contents = {}
        if vial.name is None:
            # All parameters are blank except for position
            vial.name = ""
            vial.contents = ""
            vial.density = ""
            vial.volume = ""
            vial.capacity = ""
            vial.contamination = ""

        print(
            f"{vial.position:<10} {vial.name:<20} {vial.contents:<20} {vial.density:<15} {vial.volume:<15} {vial.capacity:<15} {vial.contamination:<15}"
        )
        # for key, value in vial.items():
        #     if value is None:
        #         vial[key] = ""
        # print(
        #     f"{vial['position']:<10} {vial['name']:<20} {vial['contents']:<20} {vial["density"]} {vial['volume']:<10} {vial['capacity']:<10} {vial['contamination']:<15}"
        # )
    while True:
        choice = input(
            "Which vial would you like to change? Enter the position of the vial or 'q' if finished: "
        )
        if choice == "q":
            break
        for vial in vial_parameters:
            if vial["position"] == choice:
                print(
                    "Please enter the new values for the vial, if you leave any blank the value will not be changed"
                )
                print(f"\nVial {vial['position']}:")
                new_name = input(
                    f"Enter the new name of the vial (Current name is {vial['name']}): "
                )
                if new_name != "":
                    vial["name"] = new_name
                new_contents = input(
                    f"Enter the new contents of the vial (Current contents are {vial['contents']}): "
                )
                if new_contents != "":
                    vial["contents"] = new_contents
                new_density = input(
                    f"Enter the new density of the vial (Current density is {vial['density']}): "
                )
                if new_density != "":
                    vial["density"] = float(new_density)
                new_volume = input(
                    f"Enter the new volume of the vial (Current volume is {vial['volume']}): "
                )
                if new_volume != "":
                    vial["volume"] = int(new_volume)
                new_capacity = input(
                    f"Enter the new capacity of the vial (Current capacity is {vial['capacity']}): "
                )
                if new_capacity != "":
                    vial["capacity"] = int(new_capacity)
                new_contamination = input(
                    f"Enter the new contamination of the vial (Current contamination is {vial['contamination']}): "
                )
                if new_contamination != "":
                    vial["contamination"] = int(new_contamination)
                # print("\r" + " " * 100 + "\r", end="")  # Clear the previous table
                print("\nCurrent vials:")
                print(
                    f"{'Position':<10} {'Name':<20} {'Contents':<20} {'Density':<15} {'Volume':<15} {'Capacity':<15} {'Contamination':<15}"
                )
                for vial in vial_parameters:
                    vial = Vial2(**vial)
                    if vial.contents is None:
                        vial.contents = {}
                    if vial.name is None:
                        # All parameters are blank except for position
                        vial.name = ""
                        vial.contents = ""
                        vial.density = ""
                        vial.volume = ""
                        vial.capacity = ""
                        vial.contamination = ""

                    print(
                        f"{vial.position:<10} {vial.name:<20} {vial.contents:<20} {vial.density:<15} {vial.volume:<15} {vial.capacity:<15} {vial.contamination:<15}"
                    )
                break
        else:
            print("Invalid vial position")
            continue

    ## Write the new values to the state file
    with open(filename, "w", encoding="UTF-8") as file:
        json.dump(vial_parameters, file, indent=4)


def reset_vials(vialgroup: str):
    """
    Resets the volume and contamination of the current vials to their capacity and 0 respectively

    Args:
        vialgroup (str): The group of vials to be reset. Either "stock" or "waste"
    """
    ## Fetch the current state file
    filename = ""
    if vialgroup == "stock":
        filename = STOCK_STATUS
    elif vialgroup == "waste":
        filename = WASTE_STATUS
    else:
        vial_logger.error("Invalid vial group")
        raise ValueError

    with open(filename, "r", encoding="UTF-8") as file:
        vial_parameters = json.load(file)

    ## Loop through each vial and set the volume and contamination
    for vial in vial_parameters:
        if vialgroup == "stock":
            vial["volume"] = vial["capacity"]
        elif vialgroup == "waste":
            vial["volume"] = 1000
            vial["contents"] = {}
        vial["contamination"] = 0

    ## Write the new values to the state file
    with open(filename, "w", encoding="UTF-8") as file:
        json.dump(vial_parameters, file, indent=4)
