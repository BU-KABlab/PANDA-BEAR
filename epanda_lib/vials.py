"""
Vial class for creating vial objects with their position and contents
"""

# pylint: disable=line-too-long
import ast
# import json
import logging
import math
from decimal import Decimal, getcontext
# from pathlib import Path
from typing import Sequence, Union, List, Tuple

from requests import get

from .sql_tools.sql_utilities import execute_sql_command#, convert_decimals
from .vessel import OverDraftException, OverFillException, Vessel, VesselCoordinates

# set up A logger for the vials module
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
# formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
# system_handler = logging.FileHandler("code/logs/ePANDA.log")
# system_handler.setFormatter(formatter)
# logger.addHandler(system_handler)
vial_logger = logging.getLogger("e_panda")
getcontext().prec = 6


class Vial2(Vessel):
    """
    Represents a vial object that inherits from the Vessel class.

    Attributes:
        name (str): The name of the vial.
        category (int): The category of the vial (0 for stock, 1 for waste).
        position (str): The position of the vial.
        volume (Decimal): The current volume of the vial.
        capacity (Decimal): The maximum capacity of the vial.
        density (Decimal): The density of the solution in the vial.
        coordinates (VesselCoordinates): The coordinates of the vial.
        radius (Decimal): The radius of the vial.
        height (Decimal): The height of the vial.
        z_bottom (Decimal): The z-coordinate of the bottom of the vial.
        contamination (int): The number of times the vial has been contaminated.
        contents: The contents of the vial.
        viscosity_cp (Decimal, optional): The viscosity of the vial contents. Defaults to Decimal(0.0).
        x (Decimal, optional): The x-coordinate of the vial. Defaults to Decimal(0).
        y (Decimal, optional): The y-coordinate of the vial. Defaults to Decimal(0).

    Methods:
    --------
    update_volume(added_volume: Decimal) -> None
        Updates the volume of the vial by adding the specified volume.
    calculate_depth() -> Decimal
        Calculates the current depth of the solution in the vial.
    check_volume(volume_to_add: Decimal) -> bool
        Checks if the volume to be added to the vial is within the vial's capacity.
    write_volume_to_disk() -> None
        Writes the current volume and contamination of the vial to the appropriate file.
    update_contamination(new_contamination: int = None) -> None
        Updates the contamination count of the vial.
    update_contents(solution: 'Vessel', volume: Decimal) -> None
        Updates the contents of the vial.

    """

    def __init__(
        self,
        name: str,
        category: int,
        position: str,
        volume: Decimal,
        capacity: Decimal,
        density: Decimal,
        vial_coordinates: Union[VesselCoordinates],
        radius: Decimal,
        height: Decimal,
        contamination: int = 0,
        contents=None,
        viscosity_cp: Decimal = Decimal(0.0),
        depth: Decimal = Decimal(0),
        concentration: Decimal = Decimal(0.0),
    ) -> None:
        """
        Initializes a new instance of the Vial2 class.

        Args:
            name (str): The name of the vial.
            category (int): The category of the vial (0 for stock, 1 for waste).
            position (str): The position of the vial.
            volume (Decimal): The current volume of the vial.
            capacity (Decimal): The maximum capacity of the vial.
            density (Decimal): The density of the solution in the vial.
            coordinates (VesselCoordinates): The coordinates of the vial.
            radius (Decimal): The radius of the vial.
            height (Decimal): The height of the vial.
            z_bottom (Decimal): The z-coordinate of the bottom of the vial.
            contamination (int): The number of times the vial has been contaminated.
            contents: The contents of the vial.
            viscosity_cp (Decimal, optional): The viscosity of the vial contents. Defaults to Decimal(0.0).
            x (Decimal, optional): The x-coordinate of the vial. Defaults to Decimal(0).
            y (Decimal, optional): The y-coordinate of the vial. Defaults to Decimal(0).
        """
        super().__init__(
            name, volume, capacity, density, vial_coordinates, contents=contents
        )
        self.position = position
        self.radius = radius
        self.height = height
        self.coordinates.z_top = Decimal(self.coordinates.z_bottom) + Decimal(
            self.height
        )
        self.base = round(math.pi * math.pow(self.radius, 2.0), 6)
        self.depth = self.calculate_depth()
        self.contamination = contamination
        self.category = category
        self.viscosity_cp = viscosity_cp
        self.concentration = concentration

        # loop through the attributes and any of type Decimal should be quantized to 6 decimal places
        for key, value in self.__dict__.items():
            if isinstance(value, Decimal):
                if (
                    value == value.to_integral_value()
                ):  # Check if the value is an integer
                    setattr(self, key, value)
                else:
                    precision = len(str(value).split(".")[1])
                    getcontext().prec = precision
                    d = Decimal(str(value))
                    setattr(self, key, d.__round__(6))
                    getcontext().prec = 6

    def calculate_depth(self) -> Decimal:
        """
        Calculates the current depth of the solution in the vial.

        Returns:
            Decimal: The current depth of the solution in the vial.
        """
        radius_mm = self.radius
        area_mm2 = Decimal(math.pi) * Decimal(radius_mm) ** 2
        volume_mm3 = self.volume
        height = round(volume_mm3 / area_mm2, 4)
        depth = height + self.coordinates.z_bottom - 2
        if depth < self.coordinates.z_bottom + 1:
            depth = self.coordinates.z_bottom + 1
        # FIXME return depth
        return self.coordinates.z_bottom

    def check_volume(self, volume_to_add: Decimal) -> bool:
        """
        Checks if the volume to be added to the vial is within the vial's capacity.

        Args:
            volume_to_add (Decimal): The volume to be added to the vial.

        Returns:
            bool: True if the volume to be added is within the vial's capacity, False otherwise.
        """
        volume_to_add = Decimal(str(volume_to_add))
        if self.volume + volume_to_add > self.capacity:
            raise OverFillException(
                self.name, self.volume, volume_to_add, self.capacity
            )
        elif self.volume + volume_to_add < 0:
            raise OverDraftException(
                self.name, self.volume, volume_to_add, self.capacity
            )
        else:
            return True

    def update_volume(self, added_volume: Decimal) -> None:
        """
        Updates the volume of the vial by adding the specified volume.

        Parameters:
            added_volume (Decimal): The volume to be added to the vial.
        """
        super().update_volume(added_volume)
        self.depth = self.calculate_depth()
        self.update_contamination()
        # self.write_volume_to_disk()
        self.insert_updated_vial_in_db()
        return self

    def write_volume_to_disk(self) -> None:  # TODO replace with using the db
        """
        Writes the current volume and contamination of the vial to the appropriate file.
        """
        # vial_logger.info("Writing %s volume to vial file...", self.name)
        # vial_file_path = STOCK_STATUS if self.category == 0 else WASTE_STATUS

        # with open(vial_file_path, "r", encoding="UTF-8") as file:
        #     solutions = json.load(file)

        # for solution in solutions:
        #     if solution["name"] == self.name and solution["position"] == self.position:
        #         solution["volume"] = self.volume
        #         solution["contamination"] = self.contamination
        #         solution["depth"] = self.depth
        #         # solution["contents"] = self.contents
        #         break

        # with open(vial_file_path, "w", encoding="UTF-8") as file:
        #     json.dump(solutions, file, indent=4)
        self.insert_updated_vial_in_db()

    def insert_updated_vial_in_db(self) -> None:  # Update with a db method
        """
        Inserts a new vial record into the 'vials' table in the db. This will be used by
        the vial_status view as the most recent vial status.
        """
        try:
            execute_sql_command(
                """
                INSERT INTO vials (
                    name,
                    category,
                    position,
                    volume,
                    capacity,
                    density,
                    vial_coordinates,
                    radius,
                    height,
                    contamination,
                    contents,
                    viscosity_cp,
                    depth,
                    concentration
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    self.name,
                    self.category,
                    self.position,
                    self.volume,
                    self.capacity,
                    self.density,
                    str(self.coordinates.standard_dict()),
                    self.radius,
                    self.height,
                    self.contamination,
                    str(self.contents),
                    self.viscosity_cp,
                    self.depth,
                    self.concentration,
                ),
            )
        except Exception as e:
            vial_logger.error(
                "Error occurred while updating vial status in the db: %s", e
            )
            vial_logger.error("Continuing....")
            vial_logger.exception(e)

    def update_contamination(
        self, new_contamination: int = None
    ) -> None:  # Update with a db method
        """
        Updates the contamination count of the vial.

        Parameters:
            new_contamination (int, optional): The new contamination count of the vial.
        """
        if new_contamination is not None:
            self.contamination = new_contamination
        else:
            self.contamination += 1

        # Update the db
        self.insert_updated_vial_in_db()
        return self

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"

    def to_dict(self) -> dict:
        """Return the vial as a dictionary"""
        return {
            "name": self.name,
            "category": self.category,
            "position": self.position,
            "volume": self.volume,
            "capacity": self.capacity,
            "density": self.density,
            "vial_coordinates": self.coordinates,
            "radius": self.radius,
            "height": self.height,
            "contamination": self.contamination,
            "contents": self.contents,
            "viscosity_cp": self.viscosity_cp,
            "depth": self.depth,
            "concentration": self.concentration,
        }


class StockVial(Vial2):
    """
    Represents a stock vial object that inherits from the Vial2 class.

    Attributes:
        name (str): The name of the stock vial.
        volume (Decimal): The current volume of the stock vial.
        capacity (Decimal): The maximum capacity of the stock vial.
        density (Decimal): The density of the solution in the stock vial.
        coordinates (dict): The coordinates of the stock vial.
        radius (Decimal): The radius of the stock vial.
        height (Decimal): The height of the stock vial.
        z_bottom (Decimal): The z-coordinate of the bottom of the stock vial.
        base (Decimal): The base area of the stock vial.
        depth (Decimal): The current depth of the solution in the stock vial.
        contamination (int): The number of times the stock vial has been contaminated.
        category (int): The category of the stock vial (0 for stock, 1 for waste).
    """

    def __init__(
        self,
        name: str,
        position: str,
        volume: Decimal,
        capacity: Decimal,
        density: Decimal,
        vial_coordinates: Union[VesselCoordinates, dict],
        radius: Decimal,
        height: Decimal,
        contamination: int,
        contents: str,
        viscosity_cp: Decimal = Decimal(0.0),
        category: int = 0,
        depth: Decimal = Decimal(0),
        concentration: Decimal = Decimal(0.0),
    ) -> None:
        """
        Initializes a new instance of the StockVial class.

        Args:
        name (str): The name of the stock vial.
        volume (Decimal): The current volume of the stock vial.
        capacity (Decimal): The maximum capacity of the stock vial.
        density (Decimal): The density of the solution in the stock vial.
        coordinates (dict): The coordinates of the stock vial.
        radius (Decimal): The radius of the stock vial.
        height (Decimal): The height of the stock vial.
        z_bottom (Decimal): The z-coordinate of the bottom of the stock vial.
        """
        super().__init__(
            name,
            0,
            position,
            volume,
            capacity,
            density,
            vial_coordinates,
            radius,
            height,
            contamination,
            contents=contents,
            viscosity_cp=viscosity_cp,
            concentration=concentration,
        )
        self.category = 0

    def update_contents(self, from_vessel: str, volume: Decimal) -> None:
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
        volume (Decimal): The current volume of the waste vial.
        capacity (Decimal): The maximum capacity of the waste vial.
        density (Decimal): The density of the solution in the waste vial.
        coordinates (dict): The coordinates of the waste vial.
        radius (Decimal): The radius of the waste vial.
        height (Decimal): The height of the waste vial.
        z_bottom (Decimal): The z-coordinate of the bottom of the waste vial.
        base (Decimal): The base area of the waste vial.
        depth (Decimal): The current depth of the solution in the waste vial.
        contamination (int): The number of times the waste vial has been contaminated.
        category (int): The category of the waste vial (0 for stock, 1 for waste).
    """

    def __init__(
        self,
        name: str,
        position: str,
        volume: Decimal,
        capacity: Decimal,
        density: Decimal,
        vial_coordinates: Union[VesselCoordinates, dict],
        radius: Decimal,
        height: Decimal,
        contamination: int,
        contents: dict = {},
        viscosity_cp: Decimal = Decimal(0.0),
        category: int = 1,
        depth: Decimal = Decimal(0),
        concentration: Decimal = Decimal(0.0),
    ) -> None:
        """
        Initializes a new instance of the WasteVial class.

        Args:
        name (str): The name of the waste vial.
        volume (Decimal): The current volume of the waste vial.
        capacity (Decimal): The maximum capacity of the waste vial.
        density (Decimal): The density of the solution in the waste vial.
        coordinates (dict): The coordinates of the waste vial.
        radius (Decimal): The radius of the waste vial.
        height (Decimal): The height of the waste vial.
        z_bottom (Decimal): The z-coordinate of the bottom of the waste vial.
        """
        super().__init__(
            name,
            1,
            position,
            volume,
            capacity,
            density,
            vial_coordinates,
            radius,
            height,
            contamination,
            contents=contents,
            viscosity_cp=viscosity_cp,
            concentration=concentration,
        )
        self.category = category

    def update_contents(self, from_vessel: Union[str, dict], volume: Decimal) -> None:
        """Update the contentes of the waste vial"""
        vial_logger.debug("Updating %s %s contents...", self.name, self.position)

        if isinstance(from_vessel, dict):
            try:
                for key, value in from_vessel.items():
                    if key in self.contents:
                        self.contents[key] += value
                    else:
                        self.contents[key] = value

            except Exception as e:
                vial_logger.error("Error occurred while updating well contents: %s", e)
                vial_logger.error("Not critical, continuing....")

        else:  # from_vessel is a string
            if from_vessel in self.contents:
                self.contents[from_vessel] += volume
            else:
                self.contents[from_vessel] = volume
        vial_logger.debug(
            "%s %s: New contents: %s", self.name, self.position, self.contents
        )

        # Update the file
        self.insert_updated_vial_in_db()
        self.log_contents()

        return self


def get_current_vials(group: str = None) -> List[dict]:
    """
    Get the current vials from the db

    Args:
        group (str, optional): The group of vials to get. Either "stock" or "waste". Defaults to None.

    """
    vial_parameters = []
    try:
        vial_parameters = execute_sql_command(
            """
            SELECT
                name,
                category,
                position,
                volume,
                capacity,
                density,
                vial_coordinates,
                radius,
                height,
                contamination,
                contents,
                viscosity_cp 
            FROM vial_status
            """
        )
    except Exception as e:
        vial_logger.error("Error occurred while reading vials from the db: %s", e)
        vial_logger.error("Continuing with empty vial list....")
        vial_logger.exception(e)

    vial_parameters_copy = list(vial_parameters)  # Convert the tuple to a list
    vial_parameters = []
    for vial in vial_parameters_copy:
        coordinate_string = ast.literal_eval(vial[6])
        vial_dict = {
            "name": vial[0],
            "category": vial[1],
            "position": vial[2],
            "volume": Decimal(round(vial[3], 6)),
            "capacity": Decimal(round(vial[4], 6)),
            "density": Decimal(round(vial[5], 6)),
            "vial_coordinates": VesselCoordinates(**coordinate_string),
            "radius": Decimal(round(vial[7], 6)),
            "height": Decimal(round(vial[8], 6)),
            "contamination": Decimal(round(vial[9], 6)),
            "contents": vial[10],
            "viscosity_cp": Decimal(round(vial[11], 6)),
        }
        # vial = Vial2(**vial_dict)
        if group is not None:  # Filter by group
            if vial_dict["category"] == get_vial_category(group):
                vial_parameters.append(vial_dict)

    return vial_parameters

def get_vial_category(group_name: str) -> int:
    """Get the category of the vial"""
    if group_name.lower() == "stock":
        return 0
    elif group_name.lower() == "waste":
        return 1
    elif group_name.lower() == "test":
        return 99
    else:
        return None

def read_vials() -> Tuple[List[StockVial], List[WasteVial]]:
    """
    Read in the virtual vials from the json file
    """
    # filename_ob = Path.cwd() / filename
    # with open(filename_ob, "r", encoding="ascii") as file:
    #     vial_parameters = json.load(file)

    # Get the vial information from the vials table in the db
    vial_parameters = get_current_vials()

    list_of_stock_solutions = []
    list_of_waste_solutions = []
    for items in vial_parameters:
        if items["name"] is not None:
            if items["category"] == 0:  # Stock vial
                read_vial = StockVial(
                    #     name=str(items["name"]).lower(),
                    #     position=str(items["position"]).lower(),
                    #     volume=items["volume"],
                    #     capacity=items["capacity"],
                    #     density=items["density"],
                    #     coordinates=Vessel_Coordinates(**items["vial_coordinates"]),
                    #     radius=items["radius"],
                    #     height=items["height"],
                    #     contamination=items["contamination"],
                    #     contents=items["contents"],
                    #     viscosity_cp=items["viscosity_cp"],
                    # )
                    **items
                )
                list_of_stock_solutions.append(read_vial)
            elif items["category"] == 1:  # Waste vial
                read_vial = WasteVial(
                    #     name=str(items["name"]).lower(),
                    #     position=str(items["position"]).lower(),
                    #     volume=items["volume"],
                    #     capacity=items["capacity"],
                    #     density=items["density"],
                    #     coordinates=Vessel_Coordinates(**items["vial_coordinates"]),
                    #     radius=items["radius"],
                    #     height=items["height"],
                    #     contamination=items["contamination"],
                    #     contents=items["contents"],
                    #     viscosity_cp=items["viscosity_cp"],
                    # )
                    **items
                )
                list_of_waste_solutions.append(read_vial)
    return list_of_stock_solutions, list_of_waste_solutions


# def update_vial_state_file(
#     vial_objects: Sequence[Vial2], filename
# ):  # Update with a db method
#     """
#     Update the vials in the json file. This is used to update the volume, contents, and contamination of the vials
#     """
    # filename_ob = Path.cwd() / filename
    # with open(filename_ob, "r", encoding="UTF-8") as file:
    #     vial_parameters = json.load(file)

    # for vial in vial_objects:
    #     for vial_param in vial_parameters:
    #         if str(vial_param["position"]) == vial.position.lower():
    #             vial_param["volume"] = vial.volume
    #             vial_param["contamination"] = vial.contamination
    #             vial_param["contents"] = vial.contents
    #             break

    # with open(filename_ob, "w", encoding="UTF-8") as file:
    #     json.dump(vial_parameters, file, indent=4)

    # return 0
    # input_new_vials_into_db(vial_objects)


def input_new_vials_into_db(vial_objects: Sequence[Vial2]) -> None:
    """Insert the given vials in the vial objects into the vials table in the db"""
    # for vial in vial_objects:
    #     try:
    #         execute_sql_command(
    #             """
    #             INSERT INTO vials (
    #                 name,
    #                 category,
    #                 position,
    #                 volume,
    #                 capacity,
    #                 density,
    #                 vial_coordinates,
    #                 radius,
    #                 height,
    #                 contamination,
    #                 contents,
    #                 viscosity_cp,
    #                 depth,
    #                 concentration
    #             )
    #             VALUES (
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?,
    #                 ?
    #             )
    #             """,
    #             (
    #                 vial.name,
    #                 vial.category,
    #                 vial.position,
    #                 vial.volume,
    #                 vial.capacity,
    #                 vial.density,
    #                 vial.coordinates,
    #                 vial.radius,
    #                 vial.height,
    #                 vial.contamination,
    #                 vial.contents,
    #                 vial.viscosity_cp,
    #                 vial.depth,
    #                 vial.concentration,
    #             ),
    #         )
    #     except Exception as e:
    #         vial_logger.error("Error occurred while updating vial status in the db: %s", e)
    #         vial_logger.error("Continuing....")
    #         vial_logger.exception(e)
    for vial in vial_objects:
        vial.insert_updated_vial_in_db()


def update_vial_state_files(
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    stock_filename: str,
    waste_filename: str,
) -> None:
    """
    Update the vials in the json file. This is used to update the volume, contents, and contamination of the vials
    """
    # stock_filename_ob = Path.cwd() / stock_filename
    # with open(stock_filename_ob, "r", encoding="UTF-8") as file:
    #     stock_vial_parameters = json.load(file)

    # for vial in stock_vials:
    #     for vial_param in stock_vial_parameters:
    #         if str(vial_param["position"]) == vial.position.lower():
    #             vial_param["volume"] = vial.volume
    #             vial_param["contamination"] = vial.contamination
    #             vial_param["contents"] = vial.contents
    #             break

    # with open(stock_filename_ob, "w", encoding="UTF-8") as file:
    #     json.dump(stock_vial_parameters, file, indent=4)

    # waste_filename_ob = Path.cwd() / waste_filename
    # with open(waste_filename_ob, "r", encoding="UTF-8") as file:
    #     waste_vial_parameters = json.load(file)

    # for vial in waste_vials:
    #     for vial_param in waste_vial_parameters:
    #         if str(vial_param["position"]) == vial.position.lower():
    #             vial_param["volume"] = vial.volume
    #             vial_param["contamination"] = vial.contamination
    #             vial_param["contents"] = vial.contents
    #             break

    # with open(waste_filename_ob, "w", encoding="UTF-8") as file:
    #     json.dump(waste_vial_parameters, file, indent=4)

    # return 0
    input_new_vials_into_db(stock_vials)
    input_new_vials_into_db(waste_vials)


def input_new_vial_values(vialgroup: str) -> None:
    """For user inputting the new vial values for the state file"""
    ## Fetch the current state file
    # filename = ""
    # if vialgroup == "stock":
    #     filename = STOCK_STATUS
    # elif vialgroup == "waste":
    #     filename = WASTE_STATUS
    # else:
    #     vial_logger.error("Invalid vial group")
    #     raise ValueError

    # with open(filename, "r", encoding="UTF-8") as file:
    #     vial_parameters = json.load(file)

    vial_parameters = get_current_vials(vialgroup)
    vial_list = []
    ## Print the current vials and their values
    print("Current vials:")
    print(
        f"{'Position':<10} {'Name':<20} {'Contents':<20} {'Density':<15} {'Volume':<15} {'Capacity':<15} {'Contamination':<15}"
    )
    for vial in vial_parameters:
        vial = Vial2(**vial)
        vial_list.append(vial)
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
            f"{vial.position:<10} {vial.name:<20} {str(vial.contents):<20} {vial.density:<15} {vial.volume:<15} {vial.capacity:<15} {vial.contamination:<15}"
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
                    vial["density"] = Decimal(new_density)
                new_volume = input(
                    f"Enter the new volume of the vial (Current volume is {vial['volume']}): "
                )
                if new_volume != "":
                    vial["volume"] = Decimal(new_volume)
                new_capacity = input(
                    f"Enter the new capacity of the vial (Current capacity is {vial['capacity']}): "
                )
                if new_capacity != "":
                    vial["capacity"] = Decimal(new_capacity)
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

    ## Insert the new values to the db
    # with open(filename, "w", encoding="UTF-8") as file:
    #     json.dump(vial_parameters, file, indent=4)
    input_new_vials_into_db(vial_list)


def reset_vials(vialgroup: str) -> None:
    """
    Resets the volume and contamination of the current vials to their capacity and 0 respectively

    Args:
        vialgroup (str): The group of vials to be reset. Either "stock" or "waste"
    """
    ## Fetch the current state file
    filename = ""
    # if vialgroup == "stock":
    # filename = STOCK_STATUS
    # elif vialgroup == "waste":
    # filename = WASTE_STATUS
    # else:
    #     vial_logger.error("Invalid vial group")
    #     raise ValueError

    if vialgroup not in ["stock", "waste","test"]:
        vial_logger.error("Invalid vial group %s given for resetting vials", vialgroup)
        raise ValueError

    # with open(filename, "r", encoding="UTF-8") as file:
    #     vial_parameters = json.load(file)
    vial_parameters = get_current_vials(vialgroup)

    ## Loop through each vial and set the volume and contamination
    for vial in vial_parameters:
        vial = Vial2(**vial)

        if vialgroup == "stock":
            vial.volume = vial.capacity
        elif vialgroup == "waste":
            vial.volume = Decimal(1000)
            vial.contents = {}
        vial.contamination = Decimal(0)

        vial.insert_updated_vial_in_db()

    ## Write the new values to the state file
    # with open(filename, "w", encoding="UTF-8") as file:
    #     json.dump(vial_parameters, file, indent=4)


def delete_vial_position_and_hx_from_db(position: str) -> None:
    """Delete the vial position and hx from the db"""
    try:
        execute_sql_command(
            """
            DELETE FROM vials WHERE position = ?
            """,
            (position,),
        )
    except Exception as e:
        vial_logger.error(
            "Error occurred while deleting vial position and hx from the db: %s", e
        )
        vial_logger.error("Continuing....")
        vial_logger.exception(e)
