"""
Wellplate data class for the echem experiment. 
This class is used to store the data for the 
wellplate and the wells in it.
"""
# pylint: disable=line-too-long

import logging
import math
import json
import os
from typing import Dict, List, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
from numpy import save
import pandas as pd
from typing import Optional
#from config.file_locations import *
from config.config import (
    MILL_CONFIG,
    WELL_STATUS,
    STOCK_STATUS,
    WASTE_STATUS,
    WELL_TYPE,
    WELLPLATE_LOCATION,
    WELL_HX,
    PATH_TO_DATA,

)
from vials import Vessel

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger("e_panda")
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
# formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(module)s:%(funcName)s:%(lineno)d:%(message)s")
# system_handler = logging.FileHandler(PATH_TO_LOGS + "/ePANDA.log")
# system_handler.setFormatter(formatter)
# logger.addHandler(system_handler)

class Well(Vessel):
    """
    Represents a well object. Inherits from the Vessel class.
    
    Args:
    -----
        well_id (str): The ID of the well.
        coordinates (dict): The coordinates of the well.
        contents (dict): The contents of the well.
        volume (float): The volume of the well.
        height (float): The height of the well.
        depth (float): The depth of the well.
        status (str): The status of the well.
        density (float): The density of the well.
        capacity (float): The capacity of the well.
    """
    def __init__(self, well_id: str, coordinates: dict, volume: float, height: float, depth: float, status: str, density: float, capacity: float, contents: dict = {}):
        """
        """
        self.well_id:str = well_id
        self.experiment_id:int = None
        self.project_id:int = None
        self.status:str = status
        self.status_date:str = None
        self.height:float = height
        self.depth:float = depth
        self.name:str = well_id
        super().__init__(name = self.well_id, coordinates=coordinates, volume = volume, capacity=capacity, density = density, contents= {}, depth = depth)

    def __str__(self) -> str:
        """Returns a string representation of the well."""
        return f"Well {self.well_id} with volume {self.volume} and status {self.status}"

    def update_contents(self, solution: Vessel, volume: float) -> None:
        """Updates the contents of the well in the well_status.json file."""
        # Check if the solution is already in the well
        logger.debug("Updating contents of %s with %s", self.name, solution.name)
        if solution.name in self.contents:
            self.contents[solution.name] += volume
        else:
            self.contents[solution.name] = volume
        logger.debug("New %s contents: %s", self.name, self.contents)
        # Update the well status file
        logger.debug("Updating well status file...")
        with open(WELL_STATUS, "r", encoding="utf-8") as f:
            data = json.load(f)
            for well in data["wells"]:
                if well["well_id"] == self.well_id:
                    well["contents"] = self.contents
                    logger.debug("Well %s contents updated to %s", self.name, self.contents)
                    break

        with open(WELL_STATUS, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.debug("Well status file updated")

class Wellplate:
    """
    Represents a well plate and each well in it.
    To access the atributes of an individual well, use the well ID as the key.
    Ex. to get the volume of well A1, use well_plate["A1"].volume

    Attributes:
        a1_x (float): X-coordinate of well A1.
        a1_y (float): Y-coordinate of well A1.
        orientation (int): Orientation of the well plate (0-3).
        columns (str): String representation of well plate columns.
        rows (int): Number of rows in the well plate.
        type_number (int): Type of well plate.

    Methods:
        __init__(self, a1_x: float = 0, a1_y: float = 0, orientation: int = 0,
                 columns: str = "ABCDEFGH", rows: int = 13, type_number: int = 1) -> None:
            Initializes a new instance of the Wells2 class.

        __getitem__(self, well_id: str) -> Well:
            Gets a Well object by well ID.

        update_well_status_from_json_file(self) -> None:
            Updates well status from a JSON file.

        get_coordinates(self, well_id: str) -> Dict[str, float]:
            Returns the coordinates of a specific well.

        contents(self, well_id: str) -> List[Optional[str]]:
            Returns the contents of a specific well.

        volume(self, well_id: str) -> float:
            Returns the volume of a specific well.

        depth(self, well_id: str) -> float:
            Returns the depth of a specific well.

        density(self, well_id: str) -> float:
            Returns the density of a specific well.

        check_volume(self, well_id: str, added_volume: float) -> bool:
            Checks if a volume can fit in a specific well.

        update_volume(self, well_id: str, added_volume: float) -> None:
            Updates the volume of a specific well.

        check_well_status(self, well_id: str) -> str:
            Checks the status of a specific well.

        set_well_status(self, well_id: str, status: str) -> None:
            Updates the status of a specific well.

        check_all_wells_status(self) -> None:
            Checks the status of all wells.

        well_coordinates_and_status_color(self) -> Tuple[List[float], List[float], List[str]]:
            Plots the well plate on a coordinate plane.
    """

    def __init__(
        self,
        x_a1: float = 0,
        y_a1: float = 0,
        orientation: int = 0,
        columns: str = "ABCDEFGH",
        rows: int = 13,
        type_number: int = 3,
    ) -> None:
        """
        Initializes a new instance of the Wells2 class.

        Args:
            a1_x (float): X-coordinate of well A1.
            a1_y (float): Y-coordinate of well A1.
            orientation (int): Orientation of the well plate (0-3).
            columns (str): String representation of well plate columns.
            rows (int): Number of rows in the well plate.
            type_number (int): Type of well plate.
        """
        self.wells: Dict[str, Well] = {}
        self.a1_x = x_a1
        self.a1_y = y_a1
        self.rows = rows
        self.columns = columns
        self.orientation = orientation
        self.z_bottom = -72
        self.echem_height = -71  # for every well
        self.image_height = -35  # The height from which to image the well in mm
        self.type_number = type_number  # The type of well plate
        self.plate_id = 0  # The id of the well plate

        # From the well_type.csv file in config but has defaults
        self.z_top = 0
        self.height = 6.0  # The height of the well plate in mm
        self.radius = 3.25  # new circular wells
        self.well_offset = 9  # mm from center to center
        self.well_capacity = 300  # ul
        # overwrite the default values with the values from the well_type.csv file
        (
            self.radius,
            self.well_offset,
            self.well_capacity,
            self.height,
            self.shape,
            self.z_top,
        ) = read_well_type_characteristics(self.type_number, self)
        (self.a1_x,
            self.a1_y,
            self.z_bottom,
            self.orientation,
            self.rows,
            self.columns,
         ) = load_wellplate_location(self)
        a1_coordinates = {"x": self.a1_x, "y": self.a1_y, "z": self.z_top}  # coordinates of A1
        volume = 0.00
        for col_idx, col in enumerate(columns):
            for row in range(1, rows):
                well_id = col + str(row)
                if well_id == "A1":
                    coordinates = a1_coordinates
                    depth = self.z_bottom
                    if depth < self.z_bottom:
                        depth = self.z_bottom
                else:
                    x_offset = col_idx * self.well_offset
                    y_offset = (row - 1) * self.well_offset
                    if orientation == 0:
                        coordinates = {
                            "x": a1_coordinates["x"] - x_offset,
                            "y": a1_coordinates["y"] - y_offset,
                            "z": self.z_top,
                        }
                    elif orientation == 1:
                        coordinates = {
                            "x": a1_coordinates["x"] + x_offset,
                            "y": a1_coordinates["y"] + y_offset,
                            "z": self.z_top,
                        }
                    elif orientation == 2:
                        coordinates = {
                            "x": a1_coordinates["x"] - x_offset,
                            "y": a1_coordinates["y"] - y_offset,
                            "z": self.z_top,
                        }
                    elif orientation == 3:
                        coordinates = {
                            "x": a1_coordinates["x"] + x_offset,
                            "y": a1_coordinates["y"] + y_offset,
                            "z": self.z_top,
                        }
                    # the depth is set here for each well instead of the well plate as a whole
                    depth = self.z_bottom

                self.wells[well_id] = Well(
                    well_id=well_id,
                    coordinates=coordinates,
                    volume=volume,
                    height=self.z_top,
                    depth=depth,
                    status="new",
                    density=1.0,
                    capacity=self.well_capacity,
                    contents={},
                )

        # Update the well info from file
        self.update_well_status_from_json_file()

    def __getitem__(self, well_id: str) -> Well:
        """Gets a Well object by well ID."""
        return self.wells[well_id]

    def update_well_status_from_json_file(self: "Wellplate") -> None:
        """Update the well status from a file"""

        logger.debug("Updating well status's from file...")
        with open(WELL_STATUS, "r", encoding="utf-8") as f:
            data = json.load(f)
            for saved_well in data["wells"]:
                for well_id, well in self.wells.items():
                    if saved_well["well_id"] == well_id:
                        well.status = saved_well["status"]
                        well.contents = saved_well["contents"]
                        well.experiment_id = saved_well["experiment_id"]
                        well.project_id = saved_well["project_id"]
                        well.status_date = saved_well["status_date"]
                        self.type_number = data["type_number"]
                        self.plate_id = data["plate_id"]
                        logger.debug("Well %s updated from file", well.name)
                        break

    def get_coordinates(self, well_id) -> dict:
        """
        Return the coordinate of a specific well
        Args:
            well_id (str): The well ID
        Returns:
            dict: The coordinates of the well in the form
            {"x": x, "y": y, "z": z, "depth": depth, "echem_height": echem_height}
        """
        coordinates_dict = self.wells[well_id].coordinates
        coordinates_dict["depth"] = self.wells[well_id].depth
        coordinates_dict["echem_height"] = self.echem_height
        coordinates_dict["image_height"] = self.image_height
        return coordinates_dict

    def get_contents(self, well_id) -> dict:
        """Return the contents of a specific well"""
        return self.wells[well_id].contents

    def get_volume(self, well_id) -> float:
        """Return the volume of a specific well"""
        return self.wells[well_id].volume

    def get_depth(self, well_id) -> float:
        """Return the depth of a specific well"""
        return self.wells[well_id].depth

    def get_density(self, well_id) -> float:
        """Return the density of a specific well"""
        return self.wells[well_id].density

    def check_volume(self, well_id, added_volume: float) -> bool:
        """Check if a volume can fit in a specific well"""
        info_message = f"Checking if {added_volume} can fit in {well_id} ..."
        logger.info(info_message)
        if self.wells[well_id].volume + added_volume >= self.well_capacity:
            raise OverFillException(
                well_id, self.get_volume, added_volume, self.well_capacity
            )

        else:
            info_message = f"{added_volume} can fit in {well_id}"
            logger.info(info_message)
            return True

    def update_volume(self, well_id, added_volume: float):
        """Update the volume of a specific well"""
        if self.wells[well_id].volume + added_volume > self.well_capacity:
            raise OverFillException(
                well_id,
                self.wells[well_id].volume,
                added_volume,
                self.well_capacity,
            )

        # elif self.wells[well_id].volume + added_volume < 0:
        #    raise OverDraftException(self.name, self.volume, added_volume, self.capacity)
        else:
            self.wells[well_id].volume += added_volume
            radius_mm = self.radius
            area_mm2 = math.pi * radius_mm ** 2
            volume_mm3 = self.wells[well_id].volume
            depth = round(float(volume_mm3) / float(area_mm2), 2) + self.z_bottom
            if depth < self.z_bottom:
                depth = self.z_bottom
            if depth - 0.05 > self.z_bottom:
                depth -= 0.05
            self.wells[well_id].depth = depth

            # self.wells[well_id].depth = (self.wells[well_id].volume / 1000000) / (
            #     math.pi * math.pow(self.radius, 2.0)
            # ) + self.z_bottom
            if self.wells[well_id].depth < self.z_bottom:
                self.wells[well_id].depth = self.z_bottom
            debug_message = f"New volume: {self.wells[well_id].volume} | New depth: {self.wells[well_id].depth}"
            logger.debug(debug_message)

    def check_well_status(self, well_id: str) -> str:
        """Check the status of a specific well."""
        return self.wells[well_id].status

    def set_well_status(self, well_id: str, status: str) -> None:
        """Update the status of a specific well."""
        self.wells[well_id].status = status

    def check_all_wells_status(self):
        """Check the status of all wells"""
        for well_id, well_data in self.wells.items():
            logger.info("Well %s status: %s", well_id, well_data["status"])

    def _get_well_color(self, status: str) -> str:
        """Get the color of a well based on its status."""
        color_mapping = {"empty": "black", "new": "grey", "queued": "orange", "complete": "green", "error": "red", "running": "gold"}
        return color_mapping.get(status, "black")

    def well_coordinates_and_status_color(self):
        """Plot the well plate on a coordinate plane."""
        x_coordinates = []
        y_coordinates = []
        color = []
        for _, well_data in self.wells.items():
            x_coordinates.append(well_data.coordinates["x"])
            y_coordinates.append(well_data.coordinates["y"])
            color.append(self._get_well_color(well_data.status))

        return x_coordinates, y_coordinates, color

class GraceBioLabsWellPlate(Wellplate):
    """
    Well type for the Grace BioLabs 96 well plate
    Type 1 is gold
    Type 2 is ito
    """

    def __init__(
        self,
        a1_x: float = 0,
        a1_y: float = 0,
        orientation: int = 0,
        columns: str = "ABCDEFGH",
        rows: int = 13,
        type_number: int = 1,
    ):
        super().__init__(a1_x, a1_y, orientation, columns, rows, type_number)

        self.type_number = type_number

        ## Get the well plate parameters from the well_type.csv file in config
        (
            self.radius,
            self.well_offset,
            self.well_capacity,
            self.height,
            self.shape,
            self.z_top,
        ) = read_well_type_characteristics(self.type_number, self)


class CircularWellPlate(Wellplate):
    """
    A Wells class with different radius and well offset.
    This also changes capacity, and echem height.
    """

    def __init__(
        self,
        a1_x: float = 0,
        a1_y: float = 0,
        orientation: int = 0,
        columns: str = "ABCDEFGH",
        rows: int = 13,
        type_number: int = 3,
    ):
        super().__init__(a1_x, a1_y, orientation, columns, rows, type_number)
        (
            self.radius,
            self.well_offset,
            self.well_capacity,
            self.height,
            self.shape,
            self.z_top,
        ) = read_well_type_characteristics(self.type_number, self)
        self.echem_height = -73  # for every well
        self.z_top = self.z_bottom + self.height


def read_well_type_characteristics(
    type_number: int, current_well: Wellplate
) -> tuple[float, float, float, float]:
    """Read the well type characteristics from the well_type.csv config file"""

    file_path = WELL_TYPE

    # check it exists
    if not os.path.exists(file_path):
        logger.warning("Well type file not found at %s. Returning defaults", file_path)
        return (
            current_well.radius,
            current_well.well_offset,
            current_well.well_capacity,
            current_well.height,
            current_well.shape,
            current_well.z_top,
        )

    with open(WELL_TYPE, "r", encoding="UTF-8") as f:
        next(f)
        for line in f:
            line = line.strip().split(",")
            if int(line[0]) == int(type_number):
                shape = str(line[4]).strip()
                radius = float(line[5])
                well_offset = float(line[6])
                well_capacity = float(line[9])
                height = float(line[7])
                break
    return (
        radius,
        well_offset,
        well_capacity,
        height,
        shape,
        current_well.z_bottom + height,
    )

def load_wellplate_location(current_well: Wellplate) -> tuple[float, float, float, int, int, str]:
    """Load the location of the well plate from the well_location.csv file"""

    # check it exists
    if not os.path.exists(WELLPLATE_LOCATION):
        logger.warning("Well location file not found at %s. Returning defaults", WELLPLATE_LOCATION)
        return (
            current_well.a1_x,
            current_well.a1_y,
            current_well.z_bottom,
            current_well.orientation,
            current_well.rows,
            current_well.columns,
        )
    # Looks like this:
    # {
    # "x": -233,
    # "y": -35,
    # "orientation": 0,
    # "rows": 13,
    # "cols": "ABCDEFGH",
    # "z-bottom": -77
    # }
    with open(WELLPLATE_LOCATION, "r", encoding="UTF-8") as f:
        data = json.load(f)
        x = data["x"]
        y = data["y"]
        z_bottom = data["z-bottom"]
        orientation = data["orientation"]
        rows = data["rows"]
        cols = data["cols"]

    return (x, y, z_bottom, orientation, rows, cols)
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


def test_stage_display():
    """Test the well plate"""
    wellplate = CircularWellPlate(
        a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13, type_number=3
    )
    ## Well coordinate
    x_coordinates, y_coordinates, color = wellplate.well_coordinates_and_status_color()
    if wellplate.shape == "circular":
        marker = "o"
    else:
        marker = "s"

    ## Vial coordinates
    vial_x = []
    vial_y = []
    vial_color = []
    vial_marker = []  # a circle for these circular vials
    ## Vials
    stock_vial_path = STOCK_STATUS
    waste_vial_path = WASTE_STATUS
    with open(stock_vial_path, "r", encoding="utf-8") as stock:
        data = json.load(stock)
        for vial in data:
            vial_x.append(vial["x"])
            vial_y.append(vial["y"])
            volume = vial["volume"]
            capacity = vial["capacity"]
            if volume / capacity > 0.5:
                vial_color.append("green")
            elif volume / capacity > 0.25:
                vial_color.append("yellow")
            else:
                vial_color.append("red")
            vial_marker.append("o")

    with open(waste_vial_path, "r", encoding="utf-8") as stock:
        data = json.load(stock)
        for vial in data:
            vial_x.append(vial["x"])
            vial_y.append(vial["y"])
            volume = vial["volume"]
            capacity = vial["capacity"]
            if volume / capacity > 0.75:
                vial_color.append("red")
            elif volume / capacity > 0.50:
                vial_color.append("yellow")
            else:
                vial_color.append("green")
            vial_marker.append("o")

    rinse_vial = {"x": -411, "y": -30}
    vial_x.append(rinse_vial["x"])
    vial_y.append(rinse_vial["y"])
    vial_color.append("blue")
    ## combine the well and vial coordinates
    # x_coordinates.extend(stock_vial_x)
    # y_coordinates.extend(stock_vial_y)
    # color.extend(vial_color)

    # Plot the well plate
    plt.scatter(x_coordinates, y_coordinates, marker=marker, c=color, s=75, alpha=0.5)
    plt.scatter(vial_x, vial_y, marker="o", c=vial_color, s=200, alpha=1)
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.title("Status of Stage Items")
    plt.grid(True, "both")
    plt.xlim(-420, 0)
    plt.ylim(-310, 0)
    plt.show()

def change_wellplate_location():
    """Change the location of the wellplate"""
    ## Load the working volume from mill_config.json
    with open(MILL_CONFIG, "r", encoding="UTF-8") as file:
        mill_config = json.load(file)
    working_volume = mill_config["working_volume"]

    ## Ask for the new location
    while True:
        new_location_x = float(input("Enter the new x location of the wellplate: "))

        if new_location_x > working_volume["x"] and new_location_x < 0:
            break

        print(
            f"Invalid input. Please enter a value between {working_volume['x']} and 0."
        )

    while True:
        new_location_y = float(input("Enter the new y location of the wellplate: "))

        if new_location_y > working_volume["y"] and new_location_y < 0:
            break

        print(
            f"Invalid input. Please enter a value between {working_volume['y']} and 0."
        )

    # Keep asking for input until the user enters a valid input
    while True:
        new_orientation = int(
            input(
                """
                Orientation of the wellplate:
                    0 - Vertical, wells become more negative from A1
                    1 - Vertical, wells become less negative from A1
                    2 - Horizontal, wells become more negative from A1
                    3 - Horizontal, wells become less negative from A1
                Enter the new orientation of the wellplate: 
                """
            )
        )
        if new_orientation in [0, 1, 2, 3]:
            break
        else:
            print("Invalid input. Please enter 0, 1, 2, or 3.")

    ## Get the current location config
    with open(WELLPLATE_LOCATION, "r", encoding="UTF-8") as file:
        current_location = json.load(file)

    new_location = {
        "x": new_location_x,
        "y": new_location_y,
        "orientation": new_orientation,
        "rows": current_location["rows"],
        "cols": current_location["cols"],
        "z-bottom": current_location["z-bottom"],
    }
    ## Write the new location to the wellplate_location.txt file
    with open(WELLPLATE_LOCATION, "w", encoding="UTF-8") as file:
        json.dump(new_location, file, indent=4)


def load_new_wellplate(
    ask: bool = False,
    new_plate_id: Optional[int] = None,
    new_wellplate_type_number: Optional[int] = None,
) -> int:
    """
    Save the current wellplate, reset the well statuses to new.
    If no plate id or type number given assume same type number as the current wellplate and increment wellplate id by 1

    Args:
        new_plate_id (int, optional): The plate id being loaded. Defaults to None. If None, the plate id will be incremented by 1
        new_wellplate_type_number (int, optional): The type of wellplate. Defaults to None. If None, the type number will not be changed

    Returns:
        int: The new wellplate id
    """
    (
        current_wellplate_id,
        current_type_number,
        current_wellplate_is_new,
    ) = save_current_wellplate()

    if ask:
        new_plate_id = int(
            input(
                f"Enter the new wellplate id (Current id is {current_wellplate_id}): "
            )
        )
        new_wellplate_type_number = int(
            input(
                f"Enter the new wellplate type number (Current type is {current_type_number}): "
            )
        )
    else:
        if new_plate_id is None:
            new_plate_id = current_wellplate_id + 1
        if new_wellplate_type_number is None:
            new_wellplate_type_number = current_type_number

    if current_wellplate_is_new and new_plate_id is None:
        return current_wellplate_id

    ## Check if the new plate id exists in the well hx
    ## If so, then load in that wellplate
    ## If not, then create a new wellplate
    if new_plate_id is None:
        new_plate_id = current_wellplate_id + 1
    else:
        new_plate_id = int(new_plate_id)

    if new_wellplate_type_number is None:
        new_wellplate_type_number = current_type_number
    else:
        new_wellplate_type_number = int(new_wellplate_type_number)

    if Path(WELL_HX).exists():
        with open(WELL_HX, "r", encoding="UTF-8") as file:
            well_hx = file.readlines()
        wells = []
        for line in well_hx:
            if line.split("&")[0] == str(new_plate_id):
                wells.append(line.strip())
        if len(wells) > 0:
            ## If the wellplate exists in the well hx, then load it
            logger.debug("Loading wellplate")
            with open(WELL_STATUS, "w", encoding="UTF-8") as file:
                json.dump(
                    {
                        "plate_id": int(new_plate_id),
                        "type_number": int(new_wellplate_type_number),
                        "wells": [
                            {
                                "well_id": current_line.split("&")[2],
                                "status": current_line.split("&")[5],
                                "status_date": current_line.split("&")[6],
                                "contents": json.loads(current_line.split("&")[7].replace("'", '"')),
                                "experiment_id": (current_line.split("&")[3]),
                                "project_id": (current_line.split("&")[4]),
                            }
                            for current_line in wells
                        ],
                    },
                    file,
                    indent=4,
                )
            logger.debug("Wellplate loaded")
            logger.info("Wellplate %d loaded", int(new_plate_id))
        return new_plate_id

    ## If the wellplate does not exist in the well hx, then create a new wellplate
    ## Go through a reset all fields and apply new plate id
    logger.debug("Resetting well statuses to new")
    new_wellplate = {
        "plate_id": new_plate_id,
        "type_number": new_wellplate_type_number,
        "wells": [
            {
                "well_id": chr(65 + (i // 12)) + str(i % 12 + 1),
                "status": "new",
                "status_date": "",
                "contents": {},
                "experiment_id": "",
                "project_id": "",
            }
            for i in range(96)
        ],
    }

    with open(WELL_STATUS, "w", encoding="UTF-8") as file:
        json.dump(new_wellplate, file, indent=4)

    logger.debug("Well statuses reset to new")
    logger.info(
        "Wellplate %d saved and wellplate %d loaded",
        int(current_wellplate_id),
        int(new_plate_id),
    )
    return new_plate_id


def save_current_wellplate():
    """Save the current wellplate"""
    wellplate_is_new = True
    ## Go through a reset all fields and apply new plate id
    logger.debug("Saving wellplate")
    ## Open the current status file for the plate id , type number, and wells
    with open(WELL_STATUS, "r", encoding="UTF-8") as file:
        current_wellplate = json.load(file)
    current_plate_id = current_wellplate["plate_id"]
    current_type_number = current_wellplate["type_number"]
    ## Check if the wellplate is new still or not
    for well in current_wellplate["wells"]:
        if well["status"] != "new":
            wellplate_is_new = False

    ## Save each well to the well_history.csv file in the data folder even if it is empty
    ## plate id, type number, well id, experiment id, project id, status, status date, contents
    logger.debug("Saving well statuses to well_history.csv")

    # if the plate has been partially used before then there will be entries in the well_history.csv file
    # these entries will have the same plate id as the current wellplate
    # we want to write over these entries with the current well statuses

    # write back all lines that are not the same plate id as the current wellplate

    with open(WELL_HX, "r", encoding="UTF-8") as input_file:
        with open(
            PATH_TO_DATA / "new_well_history.csv", "w", encoding="UTF-8"
        ) as output_file:
            for line in input_file:
                # Check if the line has the same plate ID as the current_plate_id
                if line.split("&")[0] == str(current_plate_id):
                    continue  # Skip this line
                # If the plate ID is different, write the line to the output file
                output_file.write(line)
    ## delete the old well_history.csv file
    Path(WELL_HX).unlink()

    ## rename the new_well_history.csv file to well_history.csv
    Path(PATH_TO_DATA / "new_well_history.csv").rename(WELL_HX)

    # write the current well statuses to the well_history.csv file
    with open(WELL_HX, "a", encoding="UTF-8") as file:
        for well in current_wellplate["wells"]:
            # if the well is still queued then there is nothing in it and we can unallocated it
            if well["status"] == "queued":
                well["status"] = "new"
                well["experiment_id"] = ""
                well["project_id"] = ""

            file.write(f"{current_plate_id}&{current_type_number}&{str(well['well_id'])}&{well['experiment_id']}&{well['project_id']}&{str(well['status'])}&{str(well['status_date'])}&{well['contents']}\n")

    logger.debug("Wellplate saved")
    logger.info("Wellplate %d saved", int(current_plate_id))
    return int(current_plate_id), int(current_type_number), wellplate_is_new

def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    well_hx = pd.read_csv(WELL_HX, skipinitialspace=True, sep="&")
    well_hx = well_hx.dropna(subset=["experiment id"])
    well_hx = well_hx.drop_duplicates(subset=["experiment id"])
    well_hx = well_hx[well_hx["experiment id"] != "None"]
    well_hx["experiment id"] = well_hx["experiment id"].astype(int)
    last_experiment_id = well_hx["experiment id"].max()
    return int(last_experiment_id + 1)

if __name__ == "__main__":
    #test_stage_display()
    print(load_new_wellplate(False,106,3))
    #print(save_current_wellplate())