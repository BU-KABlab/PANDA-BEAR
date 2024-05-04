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

from .config.config import (
    MILL_CONFIG,
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

    def to_dict(self) -> dict:
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

    def to_json_string(self) -> str:
        """Returns a JSON string representation of the coordinates."""
        return json.dumps(self.to_dict())


class WellCoordinatesEncoder(json.JSONEncoder):
    """Custom JSON encoder for the WellCoordinates class."""

    def default(self, o) -> dict:
        """Returns a dictionary representation of the WellCoordinates object."""
        if isinstance(o, WellCoordinates):
            return o.to_dict()
        return super().default(o)

    def encode(self, o) -> str:
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
        campaign_id: int = None,
        well_type_number: int = None,
    ):
        """ """
        self.plate_id: int = plate_id
        self.well_id: str = well_id
        self.experiment_id: int = experiment_id
        self.status: str = status
        self.status_date: str = status_date
        self.contents: dict = contents
        self.project_id: int = project_id
        self.campaign_id: int = campaign_id
        self.volume: float = volume
        self.coordinates: WellCoordinates = coordinates
        self.density: float = density
        self.name: str = well_id
        self.height: float = height
        self.depth: float = depth
        self.capacity: float = capacity
        self.type_number: int = well_type_number

        super().__init__(
            name=self.well_id,
            volume=volume,
            capacity=capacity,
            density=density,
            coordinates=coordinates,
            contents=contents,
            depth=depth,
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
            "contents": json.dumps(self.contents),
            "experiment_id": self.experiment_id,
            "project_id": self.project_id,
            "volume": self.volume,
            "coordinates": self.coordinates.to_json_string(),
        }

    def __repr__(self) -> str:
        """Returns a string representation of the well."""
        return f"Well({self.well_id}, {self.status}, {self.status_date}, {self.contents}, {self.experiment_id}, {self.project_id}, {self.volume}, {self.coordinates})"
    def get_contents(self) -> dict:
        """Returns the contents of the well."""
        return self.contents

    def update_contents(self, from_vessel: dict, volume: float) -> None:
        """Updates the contents of the well in the well_status.json file."""

        # If we are removing a volume from a well we assume that the contents are equally mixed
        # and we remove the same proportion of each vessel name AKA solution name
        logger.debug("Updating well contents...")

        # If we are removing a volume from a well then we update the Self contents accordingly
        # We are assuming a well is equally mixed and we remove the same proportion of each vessel name AKA solution name
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
        # in the well contents with the provided volume
        else:
            for key in from_vessel.keys():
                if key in self.contents.keys():
                    self.contents[key] += from_vessel[key]
                    logger.debug("Updated %s contents: %s", self.name, self.contents)
                else:
                    self.contents[key] = from_vessel[key]
                    logger.debug("New %s contents: %s", self.name, self.contents)
        # Update the well in the db and log its new contents
        self.save_to_db()
        self.log_contents()

    def save_to_db(self) -> None:
        """Inserts or Updates the well in the database"""
        logger.info("Saving well %s to the database", self.name)
        try:
            sql_utilities.save_well_to_db(self)
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
    -----------
        wells (Dict[str, Well]): A dictionary of well objects.
        a1_x (float): The x-coordinate of well A1.
        a1_y (float): The y-coordinate of well A1.
        orientation (int): The orientation of the well plate (0-3).
        columns (str): The string representation of well plate columns.
        rows (int): The number of rows in the well plate.
        type_number (int): The type of well plate.
        new_well_plate (bool): A flag to indicate if the well plate is new.
        plate_id (int): The ID of the well plate.


    """

    def __init__(
        self,
        x_a1: float = 0,
        y_a1: float = 0,
        orientation: int = 0,
        columns: str = "ABCDEFGH",
        rows: int = 13,
        type_number: int = 4,
        new_well_plate: bool = False,
        plate_id: int = None,
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
        self.plate_id = 0 if plate_id is None else plate_id  # The id of the well plate

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
        current_wellplate_id, current_wellplate_type, _ = (
            sql_utilities.select_current_wellplate_info()
        )
        if not new_well_plate:
            # self.update_well_status_from_json_file()
            self.plate_id = current_wellplate_id
            self.type_number = current_wellplate_type
            self.update_well_status_from_db()

        else:
            if plate_id is None:
                self.plate_id = plate_id + 1
            self.save_wells_to_db()  # save the new wells to the database

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
                new_coordinates = WellCoordinates(
                    coordinates["x"], coordinates["y"], coordinates["z_top"]
                )
                self.set_coordinates(well_id, new_coordinates)

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
        incoming_wells = sql_utilities.select_wellplate_wells()
        for saved_well in incoming_wells:
            well = self.wells[saved_well.name.upper()]
            well = saved_well
            well.plate_id = self.plate_id
            well.depth = self.z_bottom
            #well.height = self.height
            #well.capacity = self.well_capacity
            well.name = well.well_id.upper()

            # TODO this might be redundant
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
        """Sets the coordinates of a specific well in memory and in the db"""
        # validate the coordinates
        if not isinstance(new_coordinates, WellCoordinates):
            raise TypeError("Coordinates must be a WellCoordinates object")
        self.wells[well_id.upper()].coordinates = new_coordinates
        sql_utilities.update_well_coordinates(well_id, self.plate_id, new_coordinates)

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

    # def _get_well_color(self, status: str) -> str:
    #     """Get the color of a well based on its status."""
    #     color_mapping = {
    #         "empty": "black",
    #         "new": "grey",
    #         "queued": "orange",
    #         "complete": "green",
    #         "error": "red",
    #         "running": "gold",
    #         "paused": "blue",
    #     }
    #     return color_mapping.get(status, "black")

    # def get_well_coordinates_and_status_color(self):
    #     """Plot the well plate on a coordinate plane."""
    #     x_coordinates = []
    #     y_coordinates = []
    #     color = []
    #     for _, well_data in self.wells.items():
    #         x_coordinates.append(well_data.coordinates["x"])
    #         y_coordinates.append(well_data.coordinates["y"])
    #         color.append(self._get_well_color(well_data.status))

    #     return x_coordinates, y_coordinates, color

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
            sql_utilities.select_well_characteristics(type_number)
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
        # wells_data = [well.__dict__() for well in self.wells.values()]
        # # if isinstance(wells_data[0]["coordinates"], WellCoordinates):
        # #     for well in wells_data:
        # #         well["coordinates"] = well["coordinates"].to_json_string()
        # # elif isinstance(wells_data[0]["coordinates"], dict):
        # #     for well in wells_data:
        # #         well["coordinates"] = json.dumps(well["coordinates"])
        # values = [
        #     (
        #         self.plate_id,
        #         well["well_id"],
        #         well["experiment_id"],
        #         well["project_id"],
        #         well["status"],
        #         well["status_date"],
        #         json.dumps(
        #             well["contents"]
        #         ),  # Contents is a dictionary and needs to turn into a string
        #         well["volume"],
        #         well[
        #             "coordinates"
        #         ],  # Coordinates are a WellCoordinate object and need to be encoded into a json string
        #     )
        #     for well in wells_data
        # ]
        # sql_statement = """
        #     INSERT INTO well_hx (
        #     plate_id,
        #     well_id,
        #     experiment_id,
        #     project_id,
        #     status,
        #     status_date,
        #     contents,
        #     volume,
        #     coordinates
        #     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        #     ON CONFLICT (plate_id, well_id) DO UPDATE SET
        #     experiment_id = excluded.experiment_id,
        #     project_id = excluded.project_id,
        #     status = excluded.status,
        #     status_date = excluded.status_date,
        #     contents = excluded.contents,
        #     volume = excluded.volume,
        #     coordinates = excluded.coordinates
        # """
        # sql_utilities.execute_sql_command(
        #     sql_statement, values
        # )  # Pass values as a single argument
        list_of_wells = [well for well in self.wells.values()]
        sql_utilities.save_wells_to_db(list_of_wells)

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

def _remove_wellplate_from_db(plate_id: int) -> None:
    """Removed all wells for the given plate id in well_hx, removes the plate id from the wellplate table"""
    user_choice = (
        input(
            "Are you sure you want to remove the wellplate and all its wells from the database? This is irreversible. (y/n): "
        )
    )
    if not user_choice:
        print("No action taken")
        return
    if user_choice.strip().lower()[0] != "y":
        print("No action taken")
        return
    sql_utilities.execute_sql_command(
        "DELETE FROM well_hx WHERE plate_id = ?", (plate_id,)
    )
    sql_utilities.execute_sql_command(
        "DELETE FROM wellplates WHERE id = ?", (plate_id,)
    )

def _remove_experiment_from_db(experiment_id: int) -> None:
    """Removes the experiment from the database"""

    # Check that no experiment_results exist for this experiment
    results = sql_utilities.select_results(experiment_id)
    if results:
        print(
            """
            This experiment has associated results. If you really want to delete the experiment,
            please delete the results before deleting the experiment."""
        )
        input("Press enter to continue...")
        return

    user_choice = (
        input(
            "Are you sure you want to remove the experiment and all its data from the database? This is irreversible. (y/n): "
        )
    )
    if not user_choice:
        print("No action taken")
        return
    if user_choice.strip().lower()[0] != "y":
        print("No action taken")
        return
    # Delete the experiment and all its data from the experiment tables
    sql_utilities.execute_sql_command(
        "DELETE FROM experiments WHERE experiment_id = ?", (experiment_id,)
    )
    sql_utilities.execute_sql_command(
        "DELETE FROM experiment_parameters WHERE id = ?", (experiment_id,)
    )

    # Update the well in the well_hx table with the experiment id to NULL
    sql_utilities.execute_sql_command(
        "UPDATE well_hx SET experiment_id = NULL, project_id = NULL, status = 'new' WHERE experiment_id = ?",
        (experiment_id,),
    )

    input("Experiment deleted. Press enter to continue...")

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
    ) = sql_utilities.select_current_wellplate_info()

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

    ## Check if the wellplate exists in the well_hx table
    already_exists = sql_utilities.check_if_wellplate_exists(new_plate_id)
    logger.debug("Wellplate exists: %s", already_exists)
    if not already_exists:
        sql_utilities.add_wellplate_to_table(new_plate_id, new_wellplate_type_number)
        sql_utilities.update_current_wellplate(new_plate_id)
        new_wellplate = Wellplate(
            type_number=new_wellplate_type_number,
            new_well_plate=True,
            plate_id=new_plate_id,
        )

    else:
        logger.debug(
            "Wellplate already exists in the database. Setting as current wellplate"
        )
        sql_utilities.update_current_wellplate(new_plate_id)
        # TODO: Possibly run recaclulate well locations here
        return new_plate_id

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
        sql_utilities.select_current_wellplate_info()
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
    wellplate_exists = sql_utilities.check_if_wellplate_exists(new_plate_id)
    if wellplate_exists:
        logger.debug("Wellplate already exists in the database. Returning new_plate_id")
        logger.debug("Loading wellplate")
        sql_utilities.update_current_wellplate(new_plate_id)
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
    current_plate_id, current_type_number, _ = (
        sql_utilities.select_current_wellplate_info()
    )
    new_wells = sql_utilities.count_wells_with_new_status()
    return int(current_plate_id), int(current_type_number), new_wells

if __name__ == "__main__":
    pass
