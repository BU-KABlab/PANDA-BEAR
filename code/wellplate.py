"""
Wellplate data class for the echem experiment. This class is used to store the data for the wellplate and the wells in it.
"""
# pylint: disable=line-too-long

import logging
import math
import json
import os

import matplotlib.pyplot as plt
from config.file_locations import *

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)


class Wells:
    """
    Position of well plate and each well in it.
    Orientation is defined by:
        0 - Vertical, wells become more negative from A1

        1 - Vertical, wells become less negative from A1

        2 - Horizontal, wells become more negative from A1

        3 - Horizontal, wells become less negative from A1
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
        self.wells = {}
        self.rows = rows
        self.columns = columns
        self.orientation = orientation
        self.z_bottom = -76
        self.z_top = 0
        self.radius = 3.25  # new circular wells
        self.well_offset = 9  # mm from center to center
        self.well_capacity = 300  # ul
        self.echem_height = -73  # for every well
        self.type_number = type_number  # The type of wellplate
        self.plate_id = 0  # The id of the wellplate
        self.height = 6.0  # The height of the wellplate in mm

        # overwrite the default values with the values from the well_type.csv file
        (
            self.radius,
            self.well_offset,
            self.well_capacity,
            self.height,
            self.shape,
            self.z_top,
        ) = read_well_type_characteristics(self.type_number, self)

        a1_coordinates = {"x": a1_x, "y": a1_y, "z": self.z_top}  # coordinates of A1
        volume = 0.00
        for col_idx, col in enumerate(columns):
            for row in range(1, rows):
                well_id = col + str(row)
                if well_id == "A1":
                    coordinates = a1_coordinates
                    contents = None
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
                    contents = []
                    # the depth is set here for each well instead of the wellpate as a whole
                    depth = self.z_bottom

                self.wells[well_id] = {
                    "coordinates": coordinates,
                    "contents": contents,
                    "volume": volume,
                    "depth": depth,
                    "status": "empty",
                    "CV-results": None,
                    "density": 1.0,
                }

        ## update the well info from file
        self.update_well_status_from_json_file()

    def update_well_status_from_json_file(self):
        """Update the well status from a file"""
        with open("code\\system state\\well_status.json", "r", encoding="UTF-8") as f:
            data = json.load(f)
            for well in data["wells"]:
                well_id = well["well_id"]
                status = well["status"]
                self.update_well_status(well_id, status)
                self.plate_id = data["plate_id"]
                self.type_number = data["type_number"]

    def get_coordinates(self, well_id) -> dict:
        """
        Return the coordinate of a specific well
        Args:
            well_id (str): The well ID
        Returns:
            dict: The coordinates of the well in the form
            {"x": x, "y": y, "z": z, "depth": depth, "echem_height": echem_height}
        """
        coordinates_dict = self.wells[well_id]["coordinates"]
        coordinates_dict["depth"] = self.wells[well_id]["depth"]
        coordinates_dict["echem_height"] = self.echem_height
        return coordinates_dict

    def contents(self, well_id):
        """Return the contents of a specific well"""
        return self.wells[well_id]["contents"]

    def volume(self, well_id):
        """Return the volume of a specific well"""
        return self.wells[well_id]["volume"]

    def depth(self, well_id):
        """Return the depth of a specific well"""
        return self.wells[well_id]["depth"]

    def density(self, well_id):
        """Return the density of a specific well"""
        return self.wells[well_id]["density"]

    def check_volume(self, well_id, added_volume: float):
        """Check if a volume can fit in a specific well"""
        info_message = f"Checking if {added_volume} can fit in {well_id} ..."
        logger.info(info_message)
        if self.wells[well_id]["volume"] + added_volume >= self.well_capacity:
            raise OverFillException(
                well_id, self.volume, added_volume, self.well_capacity
            )

        else:
            info_message = f"{added_volume} can fit in {well_id}"
            logger.info(info_message)
            return True

    def update_volume(self, well_id, added_volume: float):
        """Update the volume of a specific well"""
        if self.wells[well_id]["volume"] + added_volume > self.well_capacity:
            raise OverFillException(
                self.wells[well_id],
                self.wells[well_id]["volume"],
                added_volume,
                self.well_capacity,
            )

        # elif self.wells[well_id]["volume"] + added_volume < 0:
        #    raise OverDraftException(self.name, self.volume, added_volume, self.capacity)
        else:
            self.wells[well_id]["volume"] += added_volume
            self.wells[well_id]["depth"] = (self.wells[well_id]["volume"] / 1000000) / (
                math.pi * math.pow(self.radius, 2.0)
            ) + self.z_bottom
            if self.wells[well_id]["depth"] < self.z_bottom:
                self.wells[well_id]["depth"] = self.z_bottom
            debug_message = f"New volume: {self.wells[well_id]['volume']} | New depth: {self.wells[well_id]['depth']}"
            logger.debug(debug_message)

    def check_well_status(self, well_id):
        """Check the status of a specific well"""
        return self.wells[well_id]["status"]

    def update_well_status(self, well_id, status):
        """Update the status of a specific well"""
        self.wells[well_id]["status"] = status

    def check_all_wells_status(self):
        """Check the status of all wells"""
        for well_id, well_data in self.wells.items():
            logger.info("Well %s status: %s", well_id, well_data["status"])

    def well_coordinates_and_status_color(self):
        """Plot the well plate on a coordinate plane"""
        x_coordinates = []
        y_coordinates = []
        color = []
        for _, well_data in self.wells.items():
            x_coordinates.append(well_data["coordinates"]["x"])
            y_coordinates.append(well_data["coordinates"]["y"])
            ## designate the color of the well based on its status
            if well_data["status"] in ["empty", "new"]:
                color.append("black")
            elif well_data["status"] == "in use":
                color.append("yellow")
            elif well_data["status"] == "complete":
                color.append("green")
            elif well_data["status"] == "error":
                color.append("red")
            else:
                color.append("black")

        return x_coordinates, y_coordinates, color


class GraceBioLabsWellPlate(Wells):
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


class CircularWellPlate(Wells):
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
    type_number: int, current_well: Wells
) -> tuple[float, float, float, float]:
    """Read the well type characteristics from the well_type.csv config file"""

    file_path = "code\\config\\well_type.csv"

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

    with open("code\\config\\well_type.csv", "r", encoding="UTF-8") as f:
        next(f)
        for line in f:
            line = line.strip().split(",")
            if int(line[0]) == type_number:
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
    stock_vial_path = "code\\system state\\stock_status.json"
    waste_vial_path = "code\\system state\\waste_status.json"
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


if __name__ == "__main__":
    test_stage_display()
