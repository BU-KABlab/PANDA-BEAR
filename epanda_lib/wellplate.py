"""
Wellplate data class for the echem experiment. 
This class is used to store the data for the 
wellplate and the wells in it.
"""

# pylint: disable=line-too-long
# from decimal import Decimal
import json
import logging
import math
import os
from typing import Dict, Optional, Tuple

import matplotlib.pyplot as plt
from .config.config import (
    MILL_CONFIG,
#    PATH_TO_DATA,
    STOCK_STATUS,
    WASTE_STATUS,
#    WELL_HX,
#    WELL_STATUS,
#    WELL_TYPE,
    WELLPLATE_LOCATION,
)
from .vessel import Vessel
from . import sql_utilities

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger("e_panda")
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
# formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(module)s:%(funcName)s:%(lineno)d:%(message)s")
# system_handler = logging.FileHandler(PATH_TO_LOGS + "/ePANDA.log")
# system_handler.setFormatter(formatter)
# logger.addHandler(system_handler)


class WellCoordinates:
    """
    Represents the coordinates of a well.

    Args:
    -----
        x (float): The x-coordinate of the well.
        y (float): The y-coordinate of the well.
        z_top (float): The z-coordinate of top the well.
        z_bottom (float): The z-coordinate of the bottom of the well.
    """

    def __init__(
        self,
        x: float,
        y: float,
        z_top: float = 0,  # z_bottom: float = None
    ) -> None:
        """Initializes a new instance of the Coordinates class."""
        self.x = x
        self.y = y
        self.z_top = z_top
        # self.z_bottom = z_bottom

    def __str__(self) -> str:
        """Returns a string representation of the coordinates."""
        return f'"x"={self.x}, "y"={self.y}, "z_top"={self.z_top}'  # , "z_bottom"={self.z_bottom}'

    def __repr__(self) -> str:
        """Returns a string representation of the coordinates."""
        return f'"x"={self.x}, "y"={self.y}, "z_top"={self.z_top}'  # , "z_bottom"={self.z_bottom}'

    def __dict__(self) -> dict:
        """Returns a dictionary representation of the coordinates."""
        return {
            "x": self.x,
            "y": self.y,
            "z_top": self.z_top,
            # "z_bottom": self.z_bottom,
        }

    def __getitem__(self, key: str) -> float:
        """Returns the value of the specified key."""
        return getattr(self, key)

    def __setitem__(self, key: str, value: float) -> None:
        """Sets the value of the specified key."""
        setattr(self, key, value)

    def __iter__(self):
        return iter([self.x, self.y, self.z_top])  # , self.z_bottom])

    def __len__(self):
        return 4

    def __eq__(self, other: "WellCoordinates") -> bool:
        """Returns True if the coordinates are equal, False otherwise."""
        return all(
            [
                self.x == other.x,
                self.y == other.y,
                self.z_top == other.z_top,
                # self.z_bottom == other.z_bottom,
            ]
        )

    def __ne__(self, other: "WellCoordinates") -> bool:
        """Returns True if the coordinates are not equal, False otherwise."""
        return not self.__eq__(other)


class WellCoordinatesEncoder(json.JSONEncoder):
    """Custom JSON encoder for the WellCoordinates class."""

    def default(self, o) -> dict:
        """Returns a dictionary representation of the WellCoordinates object."""
        if isinstance(o, WellCoordinates):
            return o.__dict__()
        return super().default(o)

    def encode(self, o):
        """Returns a JSON representation of the WellCoordinates object."""
        return json.dumps(o, cls=WellCoordinatesEncoder)


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

    def __init__(
        self,
        well_id: str,
        plate_id: int,
        coordinates: WellCoordinates,
        volume: float,
        status: str,
        contents: dict = {},
        status_date: str = None,
        depth: float = None,
        capacity: float = None,
        height: float = None,
        experiment_id: int = None,
        project_id: int = None,
        density: float = None,
    ):
        """ """
        self.plate_id: int = plate_id
        self.well_id: str = well_id
        self.experiment_id: int = experiment_id
        self.status: str = status
        self.status_date: str = status_date
        self.contents: dict = contents
        self.experiment_id: int = None
        self.project_id: int = project_id
        self.campaign_id: int = None
        self.volume: float = volume
        self.coordinates: WellCoordinates = coordinates
        self.density: float = density
        self.name: str = well_id
        self.height: float = height
        self.depth: float = depth
        self.capacity: float = capacity

        super().__init__(
            name=self.well_id,
            coordinates=coordinates,
            volume=volume,
            capacity=None,
            density=density,
            contents={},
            depth=None,
        )

    def __str__(self) -> str:
        """Returns a string representation of the well."""
        return f"Well {self.well_id} with volume {self.volume} and status {self.status}"

    def __dict__(self) -> dict:
        """Returns a dictionary representation of the well."""
        return {
            "well_id": self.well_id,
            "status": self.status,
            "status_date": self.status_date,
            "contents": self.contents,
            "experiment_id": self.experiment_id,
            "project_id": self.project_id,
            "volume": self.volume,
            "coordinates": self.coordinates,
        }

    def get_contents(self) -> dict:
        """Returns the contents of the well."""
        return self.contents

    def update_contents(self, from_vessel: dict, volume: float) -> None:
        """Updates the contents of the well in the well_status.json file."""

        # If we are removing a volume from a well we assume that the contents are equally mixed
        # and we remove the same proportion of each vessel name AKA solution name
        logger.debug("Updating well contents...")
        if volume < 0:
            try:
                current_content_ratios = {
                    key: value / sum(self.get_contents().values())
                    for key, value in self.get_contents().items()
                }

                for key, value in self.get_contents().items():
                    self.contents[key] = value + round(
                        (volume * current_content_ratios[key]), 6
                    )

                # logger.debug("Well %s is empty", self.name)
            except Exception as e:
                logger.error("Error occurred while updating well contents: %s", e)
                logger.error("Not critical, continuing....")

        elif volume == 0:
            logger.debug("Volume to add was 0 well %s contents unchanged", self.name)

        # If we are adding a volume to a well then we update the provided vessel name AKA solution name
        # with the provided volume
        else:
            for key in from_vessel.keys():
                if key in self.contents.keys():
                    self.contents[key] += from_vessel[key]
                    logger.debug("Updated %s contents: %s", self.name, self.contents)
                else:
                    self.contents[key] = from_vessel[key]
                    logger.debug("New %s contents: %s", self.name, self.contents)

        # Update the well status file
        #self.update_well_status_file()
        self.save_to_db()
        self.log_contents()

    # def update_well_status_file(self) -> None:
    #     """Updates the well in the well_status.json file."""
    #     logger.debug("Updating well file of %s", self.name)

    #     # Load the well status file and update the well
    #     with open(WELL_STATUS, "r", encoding="utf-8") as f:
    #         data = json.load(f)
    #         for well in data["wells"]:
    #             if well["well_id"] == self.well_id:
    #                 well["status"] = self.status
    #                 well["contents"] = self.contents
    #                 well["experiment_id"] = self.experiment_id
    #                 well["project_id"] = self.project_id
    #                 well["status_date"] = datetime.now().isoformat(timespec="seconds")
    #                 well["volume"] = self.volume
    #                 well["coordinates"] = self.coordinates.__dict__()

    #                 logger.debug("Well %s file updated")
    #                 break

    #     # Update the well status file with the new well status
    #     with open(WELL_STATUS, "w", encoding="utf-8") as f:
    #         json.dump(data, f, indent=4)

    #     logger.debug("Well status file updated")

    # def lookup_plate_characteristics(self) -> Tuple[float, float]:
    #     """Lookup the plate characteristics from the well_type.csv file"""
    #     # Get the plate type from the well_history.csv file
    #     well_hx = pd.read_csv(WELL_HX)
    #     well_hx = well_hx[well_hx["plate_id"] == self.plate_id]
    #     well_type = well_hx["type_number"].values[0]

    #     well_type = int(well_type)
    #     # Get the well characteristics from the well_type.csv file
    #     with open(WELL_TYPE, "r", encoding="UTF-8") as f:
    #         next(f)
    #         for line in f:
    #             line = line.strip().split(",")
    #             if int(line[0]) == int(well_type):
    #                 well_capacity = float(line[9])
    #                 height = float(line[7])
    #                 break
    #     return height, well_capacity

    def save_to_db(self) -> None:
        """Inserts or Updates the well in the database"""
        logger.info("Saving well %s to the database", self.name)
        try:
            sql_utilities.WellSQLHandler(self).save_to_db()
            logger.info("Well %s saved to the database", self.name)
        except Exception as e:
            logger.error("Error occurred while saving well to the database: %s", e)
            raise e


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
        new_well_plate: bool = False,
        plate_id: int = 0,
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
        self.echem_height = -70  # for every well
        self.image_height = -35  # The height from which to image the well in mm
        self.type_number = type_number  # The type of well plate
        self.plate_id = plate_id  # The id of the well plate

        # From the well_type.csv file in config but has defaults
        self.z_top = 0
        self.height = 6.0  # The height of the well plate in mm
        self.radius = 3.25  # new circular wells
        self.well_offset = 9.0  # mm from center to center
        self.well_capacity = 300  # ul
        # overwrite the default values with the values from the well_type.csv file
        (
            self.radius,
            self.well_offset,
            self.well_capacity,
            self.height,
            self.shape,
            self.z_top,
        ) = self.read_well_type_characteristics(self.type_number)
        (
            self.a1_x,
            self.a1_y,
            self.z_bottom,
            self.orientation,
            self.rows,
            self.columns,
            self.echem_height,
        ) = self.load_wellplate_location()
        self.a1_coordinates = {
            "x": self.a1_x,
            "y": self.a1_y,
            "z_top": self.z_top,
        }  # coordinates of A1
        self.initial_volume = 0.00
        self.establish_new_wells()  # we need to establish the wells before we can update their status from file
        self.calculate_well_locations()  # now we can calculate the well locations
        if not new_well_plate:
            #self.update_well_status_from_json_file()
            self.update_well_status_from_db()

        else:
            self.save_wells_to_db() # save the new wells to the database

    def recalculate_well_locations(self: "Wellplate") -> None:
        """Recalculates the well locations"""
        (
            self.a1_x,
            self.a1_y,
            self.z_bottom,
            self.orientation,
            self.rows,
            self.columns,
            self.echem_height,
        ) = self.load_wellplate_location()
        self.a1_coordinates = {
            "x": self.a1_x,
            "y": self.a1_y,
            "z_top": self.z_top,
        }  # coordinates of A1
        self.calculate_well_locations()
        # self.update_well_status_from_json_file()

    def calculate_well_locations(self: "Wellplate") -> None:
        """Take the coordinates of A1 and calculate the x,y,z coordinates of the other wells based on the well plate type"""
        for col_idx, col in enumerate(self.columns):
            for row in range(1, self.rows):
                well_id = col + str(row)
                if well_id == "A1":
                    coordinates = self.a1_coordinates
                    depth = self.z_bottom
                    if depth < self.z_bottom:
                        depth = self.z_bottom
                else:
                    x_offset = col_idx * self.well_offset
                    y_offset = (row - 1) * self.well_offset
                    if self.orientation == 0:
                        coordinates = {
                            "x": self.a1_coordinates["x"] - x_offset,
                            "y": self.a1_coordinates["y"] - y_offset,
                            "z_top": self.z_top,
                        }
                    elif self.orientation == 1:
                        coordinates = {
                            "x": self.a1_coordinates["x"] + x_offset,
                            "y": self.a1_coordinates["y"] + y_offset,
                            "z_top": self.z_top,
                        }
                    elif self.orientation == 2:
                        coordinates = {
                            "x": self.a1_coordinates["x"] - x_offset,
                            "y": self.a1_coordinates["y"] - y_offset,
                            "z_top": self.z_top,
                        }
                    elif self.orientation == 3:
                        coordinates = {
                            "x": self.a1_coordinates["x"] + x_offset,
                            "y": self.a1_coordinates["y"] + y_offset,
                            "z_top": self.z_top,
                        }

                    # Round the coordinates to 2 decimal places
                    coordinates["x"] = round(coordinates["x"], 3)
                    coordinates["y"] = round(coordinates["y"], 3)
                    coordinates["z_top"] = round(coordinates["z_top"], 3)

                self.set_coordinates(well_id, coordinates)

    def establish_new_wells(self: "Wellplate") -> None:
        """Establish new wells in the well plate"""
        for col in self.columns:
            for row in range(1, self.rows):
                well_id = col + str(row)
                self.wells[well_id] = Well(
                    plate_id=self.plate_id,
                    well_id=well_id,
                    coordinates=WellCoordinates(x=0, y=0, z_top=0),
                    volume=self.initial_volume,
                    height=self.height,
                    depth=self.z_bottom,
                    status="new",
                    density=1.0,
                    capacity=self.well_capacity,
                    contents={},
                )

    def __getitem__(self, well_id: str) -> Well:
        """Gets a Well object by well ID."""
        return self.wells[well_id.upper()]

    # def update_well_status_from_json_file(self: "Wellplate") -> None:
    #     """Update the well status from a file"""

    #     logger.debug("Updating well status's from file...")
    #     with open(WELL_STATUS, "r", encoding="utf-8") as f:
    #         data = json.load(f)
    #         for saved_well in data["wells"]:
    #             for well_id, well in self.wells.items():
    #                 if saved_well["well_id"] == well_id:
    #                     well.status = saved_well["status"]
    #                     well.status_date = saved_well["status_date"]
    #                     well.contents = saved_well["contents"]
    #                     well.experiment_id = saved_well["experiment_id"]
    #                     well.project_id = saved_well["project_id"]
    #                     well.volume = saved_well["volume"]
    #                     well.coordinates = WellCoordinates(**saved_well["coordinates"])
    #                     self.type_number = data["type_number"]
    #                     self.plate_id = data["plate_id"]
    #                     logger.debug("Well %s updated from file", well.name)
    #                     break

    def update_well_status_from_db(self: "Wellplate") -> None:
        """Update the well status from the database"""
        logger.debug("Updating well status from database...")
        wells = sql_utilities.select_wellplate_wells()
        for well in wells:
            self.wells[well.name.upper()] = well
        logger.debug("Well status updated from database")

    def get_coordinates(self, well_id: str, axis: str = None) -> WellCoordinates:
        """
        Return the coordinate of a specific well
        Args:
            well_id (str): The well ID
        Returns:
            Coordinates: The coordinates of the well
        """
        well_id = well_id.upper()
        if well_id in self.wells:
            if axis:
                return self.wells[well_id].coordinates[axis]
            return self.wells[well_id].coordinates
        else:
            raise KeyError(f"Well {well_id} not found")

    def set_coordinates(self, well_id: str, new_coordinates: WellCoordinates) -> None:
        """Sets the coordinates of a specific well in memory and writes to the status file"""
        self.wells[well_id.upper()].coordinates = new_coordinates
        # self.write_well_status_to_file()

    def get_contents(self, well_id: str) -> dict:
        """Return the contents of a specific well"""
        return self.wells[well_id.upper()].contents

    def get_volume(self, well_id: str) -> float:
        """Return the volume of a specific well"""
        return self.wells[well_id.upper()].volume

    def get_depth(self, well_id: str) -> float:
        """Return the depth of a specific well"""
        return self.wells[well_id.upper()].depth

    def get_density(self, well_id) -> float:
        """Return the density of a specific well"""
        return self.wells[well_id.upper()].density

    def check_volume(self, well_id, added_volume: float) -> bool:
        """Check if a volume can fit in a specific well"""
        info_message = f"Checking if {added_volume} can fit in {well_id} ..."
        logger.info(info_message)
        if self.wells[well_id.upper()].volume + added_volume >= self.well_capacity:
            raise OverFillException(
                well_id, self.get_volume, added_volume, self.well_capacity
            )

        else:
            info_message = f"{added_volume} can fit in {well_id}"
            logger.info(info_message)
            return True

    def update_volume(self, well_id: str, added_volume: float):
        """Update the volume of a specific well"""
        well_id = well_id.upper()
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
            area_mm2 = math.pi * radius_mm**2
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
        return self.wells[well_id.upper()].status

    def set_well_status(self, well_id: str, status: str) -> None:
        """Update the status of a specific well."""
        self.wells[well_id.upper()].status = status

    def check_all_wells_status(self):
        """Check the status of all wells"""
        for well_id, well_data in self.wells.items():
            logger.info("Well %s status: %s", well_id, well_data["status"])

    def _get_well_color(self, status: str) -> str:
        """Get the color of a well based on its status."""
        color_mapping = {
            "empty": "black",
            "new": "grey",
            "queued": "orange",
            "complete": "green",
            "error": "red",
            "running": "gold",
            "paused": "blue",
        }
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

    def read_well_type_characteristics(
        self, type_number: int
    ) -> tuple[float, float, float, float]:
        """Read the well type characteristics from the well_type.csv config file"""

        # file_path = WELL_TYPE

        # # check it exists
        # if not os.path.exists(file_path):
        #     logger.warning(
        #         "Well type file not found at %s. Returning defaults", file_path
        #     )
        #     return (
        #         self.radius,
        #         self.well_offset,
        #         self.well_capacity,
        #         self.height,
        #         self.shape,
        #         self.z_top,
        #     )

        # with open(WELL_TYPE, "r", encoding="UTF-8") as f:
        #     next(f)
        #     for line in f:
        #         line = line.strip().split(",")
        #         if int(line[0]) == int(type_number):
        #             shape = str(line[4]).strip()
        #             radius = float(line[5])
        #             well_offset = float(line[6])
        #             well_capacity = float(line[9])
        #             height = float(line[7])
        #             break

        # Select the well type characteristics from the well_types sql table given the type_number
        radius, well_offset, well_capacity, height, shape = (
            sql_utilities.execute_sql_command(
                "SELECT radius_mm, offset_mm, capacity_ul, height_mm, shape FROM well_types WHERE id = ?",
                (type_number,),
            )[0]
        )

        return (
            radius,
            well_offset,
            well_capacity,
            height,
            shape,
            self.z_bottom + height,  # z_top
        )

    def load_wellplate_location(
        self,
    ) -> tuple[float, float, float, int, int, str, float]:
        """Load the location of the well plate from the well_location json file"""

        # check it exists
        if not os.path.exists(WELLPLATE_LOCATION):
            logger.warning(
                "Well location file not found at %s. Returning defaults",
                WELLPLATE_LOCATION,
            )
            return (
                self.a1_x,
                self.a1_y,
                self.z_bottom,
                self.orientation,
                self.rows,
                self.columns,
                self.echem_height,
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
            echem_height = data["echem_height"]

        return (x, y, z_bottom, orientation, rows, cols, echem_height)

    def write_wellplate_location(self) -> None:
        """Write the location of the well plate to the well_location json file"""
        data_to_write = {
            "x": self.a1_x,
            "y": self.a1_y,
            "orientation": self.orientation,
            "rows": self.rows,
            "cols": self.columns,
            "z-bottom": self.z_bottom,
            "z-top": self.z_top,
            "echem_height": self.echem_height,
        }
        with open(WELLPLATE_LOCATION, "w", encoding="UTF-8") as f:
            json.dump(data_to_write, f, indent=4)
        logger.debug("Well plate location written to file")

    def write_well_status_to_file(self) -> None:
        """Write the well status to the well_status.json file"""
        # data_to_write = {
        #     "plate_id": self.plate_id,
        #     "type_number": self.type_number,
        #     "wells": [well.__dict__() for well in self.wells.values()],
        # }
        # with open(WELL_STATUS, "w", encoding="UTF-8") as f:
        #     json.dump(data_to_write, f, indent=4, cls=WellCoordinatesEncoder)
        # logger.debug("Well status written to file")
        self.save_wells_to_db()

    def save_wells_to_db(self) -> None:
        """Save the wells to the well_hx table. Replaces the write_well_status_to_file method"""
        wells_data = [well.__dict__() for well in self.wells.values()]
        values = [(self.plate_id, well["well_id"], well["experiment_id"], well["project_id"], well["status"], well["status_date"], json.dumps(well["contents"]), well["volume"], json.dumps(well["coordinates"])) for well in wells_data]
        sql_statement = """
            INSERT INTO well_hx (
            plate_id,
            well_id,
            experiment_id,
            project_id,
            status,
            status_date,
            contents,
            volume,
            coordinates
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        sql_utilities.execute_sql_command(sql_statement, values)  # Pass values as a single argument

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

def remove_wellplate_from_db(plate_id: int) -> None:
    """Removed all wells for the given plate id in well_hx, removes the plate id from the wellplate table"""
    user_choicec = input("Are you sure you want to remove the wellplate and all its wells from the database? This is irreversible. (y/n): ").lower().strip()[0]
    if user_choicec != "y":
        return
    sql_utilities.execute_sql_command(
        "DELETE FROM well_hx WHERE plate_id = ?", (plate_id,)
    )
    sql_utilities.execute_sql_command(
        "DELETE FROM wellplates WHERE id = ?", (plate_id,)
    )
def __test_stage_display():
    """Test the well plate"""
    test_wellplate = Wellplate()
    ## Well coordinate
    x_coordinates, y_coordinates, color = (
        test_wellplate.well_coordinates_and_status_color()
    )
    if test_wellplate.shape == "circular":
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
        "z-top": current_location["z-top"],
        "echem_height": current_location["echem_height"],
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
    ) = sql_utilities.get_current_wellplate_info()

    if ask:
        new_plate_id = input(
            f"Enter the new wellplate id (Current id is {current_wellplate_id}): "
        )
        new_wellplate_type_number = input(
            f"Enter the new wellplate type number (Current type is {current_type_number}): "
        )
    else:
        if new_plate_id is None or new_plate_id == "":
            new_plate_id = current_wellplate_id + 1
        if new_wellplate_type_number is None or new_wellplate_type_number == "":
            new_wellplate_type_number = current_type_number

    if current_wellplate_is_new and new_plate_id is None or new_plate_id == "":
        return current_wellplate_id

    ## Check if the new plate id exists in the well hx
    ## If so, then load in that wellplate
    ## If not, then create a new wellplate
    if new_plate_id is None or new_plate_id == "":
        new_plate_id = current_wellplate_id + 1
    else:
        new_plate_id = int(new_plate_id)

    if new_wellplate_type_number is None or new_wellplate_type_number == "":
        new_wellplate_type_number = current_type_number
    else:
        new_wellplate_type_number = int(new_wellplate_type_number)

    ## If the wellplate exists in the well hx, then load it
    # with open(WELL_HX, "r", encoding="UTF-8") as file:
    #     well_hx = file.readlines()
    # wells = []
    # for line in well_hx:
    #     if line.split("&")[0] == str(new_plate_id):
    #         wells.append(line.strip())
    # if len(wells) > 0:

    #     ## A well entry looks like this:
    #     # {
    #     # "well_id": "B2",
    #     # "status": "complete",
    #     # "status_date": "2024-03-08 13:45:15",
    #     # "contents": {
    #     #     "edot": 127.43,
    #     #     "rinse0": 509.72
    #     # },
    #     # "experiment_id": 10000382,
    #     # "project_id": 16,
    #     # "volume": 0.0,
    #     # "coordinates": {
    #     #     "x": -231.65,
    #     #     "y": -87.6,
    #     #     "z_top": -66.0
    #     # }
    #     logger.debug("Loading wellplate")
    #     with open(WELL_STATUS, "w", encoding="UTF-8") as file:
    #         json.dump(
    #             {
    #                 "plate_id": int(new_plate_id),
    #                 "type_number": int(new_wellplate_type_number),
    #                 "wells": [
    #                     {
    #                         "well_id": current_line.split("&")[2],
    #                         "status": current_line.split("&")[5],
    #                         "status_date": current_line.split("&")[6],
    #                         "contents": json.loads(current_line.split("&")[7]),
    #                         # "contents": json.loads(str(current_line.split("&")[7]).replace("'",'"')),
    #                         "experiment_id": (
    #                             None
    #                             if (current_line.split("&")[3]) == "None"
    #                             else int(current_line.split("&")[3])
    #                         ),
    #                         "project_id": (
    #                             None
    #                             if (current_line.split("&")[4]) == "None"
    #                             else int(current_line.split("&")[4])
    #                         ),
    #                         "volume": float(current_line.split("&")[8]),
    #                         "coordinates": {
    #                             "x": float(json.loads(current_line.split("&")[9])["x"]),
    #                             "y": float(json.loads(current_line.split("&")[9])["y"]),
    #                             "z_top": float(
    #                                 json.loads(current_line.split("&")[9])["z_top"]
    #                             ),
    #                         },
    #                     }
    #                     for current_line in wells
    #                 ],
    #             },
    #             file,
    #             indent=4,
    #         )
    #     logger.debug("Wellplate loaded")
    #     logger.info("Wellplate %d loaded", int(new_plate_id))
    #     return new_plate_id

    # ## If the wellplate does not exist in the well hx, then create a new wellplate
    # ## Go through a reset all fields and apply new plate id
    # logger.debug("Creating new wellplate: %d", new_plate_id)
    # logger.debug("Resetting well status file to new")
    # new_wellplate = {
    #     "plate_id": new_plate_id,
    #     "type_number": new_wellplate_type_number,
    #     "wells": [
    #         {
    #             "well_id": chr(65 + (i // 12)) + str(i % 12 + 1),
    #             "status": "new",
    #             "status_date": None,
    #             "contents": {},
    #             "experiment_id": None,
    #             "project_id": None,
    #             "volume": 0.0,
    #             "coordinates": {"x": 0.0, "y": 0.0, "z_top": 0.0},
    #         }
    #         for i in range(96)
    #     ],
    # }

    # with open(WELL_STATUS, "w", encoding="UTF-8") as file:
    #     json.dump(new_wellplate, file, indent=4)
        
    ## Check if the wellplate exists in the well_hx table
    already_exists = sql_utilities.check_if_wellplate_exists(new_plate_id)
    if not already_exists:
        sql_utilities.add_wellplate_to_table(new_plate_id, new_wellplate_type_number)
        sql_utilities.update_current_wellplate(new_plate_id)
        new_wellplate = Wellplate(
            type_number=new_wellplate_type_number, new_well_plate= True, plate_id=new_plate_id
        )
        new_wellplate.recalculate_well_locations()
        #new_wellplate.save_wells_to_db()
    else:
        logger.debug("Wellplate already exists in the database. Setting as current wellplate")
        sql_utilities.update_current_wellplate(new_plate_id)
        return new_plate_id
    # new_wellplate.recalculate_well_locations()
    # new_wellplate.write_well_status_to_file()

    logger.info(
        "Wellplate %d saved and wellplate %d loaded",
        int(current_wellplate_id),
        int(new_plate_id),
    )
    return new_wellplate.plate_id


def load_new_wellplate_sql(
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
    # Get the current wellpate from the wellplates table
    current_wellplate_id, current_type_number, current_wellplate_is_new = (
        sql_utilities.get_current_wellplate_info()
    )

    if ask:
        new_plate_id = input(
            f"Enter the new wellplate id (Current id is {current_wellplate_id}): "
        )
        new_wellplate_type_number = input(
            f"Enter the new wellplate type number (Current type is {current_type_number}): "
        )
    else:
        if new_plate_id is None or new_plate_id == "":
            new_plate_id = current_wellplate_id + 1
        if new_wellplate_type_number is None or new_wellplate_type_number == "":
            new_wellplate_type_number = current_type_number

    if current_wellplate_is_new and new_plate_id is None or new_plate_id == "":
        return current_wellplate_id

    ## Check if the new plate id exists in the well hx
    ## If so, then load in that wellplate
    ## If not, then create a new wellplate
    if new_plate_id is None or new_plate_id == "":
        new_plate_id = current_wellplate_id + 1
    else:
        new_plate_id = int(new_plate_id)

    if new_wellplate_type_number is None:
        new_wellplate_type_number = current_type_number
    else:
        new_wellplate_type_number = int(new_wellplate_type_number)

    ## If the wellplate exists in the well hx, then load it
    new_wellplate = sql_utilities.WellSQLHandler().select_provided_wellplate_wells(
        new_plate_id
    )
    if new_wellplate is not None:
        logger.debug("Wellplate already exists in the database. Returning new_plate_id")
        return new_plate_id
    else:
        logger.debug("Creating new wellplate: %d", new_plate_id)
        new_wellplate = Wellplate(
            type_number=new_wellplate_type_number, new_well_plate=True
        )
        new_wellplate.plate_id = new_plate_id
        new_wellplate.recalculate_well_locations()
        new_wellplate.save_wells_to_db()

        logger.info(
            "Wellplate %d saved and wellplate %d loaded",
            int(current_wellplate_id),
            int(new_plate_id),
        )
        return new_plate_id


def read_current_wellplate_info() -> Tuple[int, int, int]:
    """
    Read the current wellplate

    Returns:
        int: The current wellplate id
        int: The current wellplate type number
        bool: Number of new wells
    """
    # with open(WELL_STATUS, "r", encoding="UTF-8") as file:
    #     current_wellplate = json.load(file)
    # current_plate_id = current_wellplate["plate_id"]
    # current_type_number = current_wellplate["type_number"]
    # new_wells = 0
    # for well in current_wellplate["wells"]:
    #     if well["status"] == "new":
    #         new_wells += 1
    current_plate_id, current_type_number, new_wells = (
        sql_utilities.get_current_wellplate_info()
    )
    new_wells = sql_utilities.count_wells_with_new_status()
    return int(current_plate_id), int(current_type_number), new_wells

# def save_current_wellplate() -> Tuple[int, int, bool]:
#     """
#     Save the current wellplate

#     Returns:
#         int: The current wellplate id
#         int: The current wellplate type number
#         bool: Whether the wellplate is new
#     """
#     wellplate_is_new = True
#     ## Go through a reset all fields and apply new plate id
#     logger.debug("Saving wellplate")
#     ## Open the current status file for the plate id , type number, and wells
#     with open(WELL_STATUS, "r", encoding="UTF-8") as file:
#         current_wellplate = json.load(file)
#     current_plate_id = current_wellplate["plate_id"]
#     current_type_number = current_wellplate["type_number"]
#     ## Check if the wellplate is new still or not
#     for well in current_wellplate["wells"]:
#         if well["status"] != "new":
#             wellplate_is_new = False

#     ## Save each well to the well_history.csv file in the data folder even if it is empty
#     ## plate id, type number, well id, experiment id, project id, status, status date, contents
#     logger.debug("Saving well statuses to well_history.csv")

#     # if the plate has been partially used before then there will be entries in the well_history.csv file
#     # these entries will have the same plate id as the current wellplate
#     # we want to write over these entries with the current well statuses

#     # write back all lines that are not the same plate id as the current wellplate

#     with open(WELL_HX, "r", encoding="UTF-8") as input_file:
#         with open(
#             PATH_TO_DATA / "new_well_history.csv", "w", encoding="UTF-8"
#         ) as output_file:
#             for line in input_file:
#                 # Check if the line has the same plate ID as the current_plate_id
#                 if line.split("&")[0] == str(current_plate_id):
#                     continue  # Skip this line
#                 # If the plate ID is different, write the line to the output file
#                 output_file.write(line)
#     ## delete the old well_history.csv file
#     Path(WELL_HX).unlink()

#     ## rename the new_well_history.csv file to well_history.csv
#     Path(PATH_TO_DATA / "new_well_history.csv").rename(WELL_HX)

#     # write the current well statuses to the well_history.csv file
#     with open(WELL_HX, "a", encoding="UTF-8") as file:
#         for well in current_wellplate["wells"]:
#             file.write(
#                 "{}&{}&{}&{}&{}&{}&{}&{}&{}&{}\n".format(
#                     current_plate_id,
#                     current_type_number,
#                     well["well_id"],
#                     well["experiment_id"],
#                     well["project_id"],
#                     well["status"],
#                     well["status_date"],
#                     json.dumps(well["contents"]),
#                     well["volume"],
#                     json.dumps(well["coordinates"]),
#                 )
#             )

#     logger.debug("Wellplate saved")
#     logger.info("Wellplate %d saved", int(current_plate_id))

#     return int(current_plate_id), int(current_type_number), wellplate_is_new


def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    # well_hx = pd.read_csv(WELL_HX, skipinitialspace=True, sep="&")
    # well_hx = well_hx.dropna(subset=["experiment id"])
    # well_hx = well_hx.drop_duplicates(subset=["experiment id"])
    # well_hx = well_hx[well_hx["experiment id"] != "None"]
    # well_hx["experiment id"] = well_hx["experiment id"].astype(int)
    # last_experiment_id = well_hx["experiment id"].max()
    # return int(last_experiment_id + 1)
    return sql_utilities.determine_next_experiment_id()


if __name__ == "__main__":
    # test_stage_display()
    wellplate = Wellplate()
    load_new_wellplate(ask=False, new_plate_id=109, new_wellplate_type_number=4)
    wellplate.save_wells_to_db()
    # print(wellplate["A1"].coordinates)
    # print(wellplate["A12"].coordinates)

    # wellplate.recalculate_well_locations()
    # print(wellplate["A1"].coordinates)
    # print(wellplate["A12"].coordinates)

    # print(save_current_wellplate())
