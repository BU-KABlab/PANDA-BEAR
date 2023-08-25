'''
Wellplate data class for the echem experiment. This class is used to store the data for the wellplate and the wells in it.
'''
import logging
import math
import matplotlib.pyplot as plt

class Wells:
    """
    Position of well plate and each well in it.
    Orientation is defined by:
        0 - Vertical, wells become more negative from A1

        1 - Vertical, wells become less negative from A1

        2 - Horizontal, wells become more negative from A1

        3 - Horizontal, wells become less negative from A1
    """

    def __init__(self, a1_x=0, a1_y=0, orientation=0, columns = 'ABCDEFGH', rows = 13):
        self.wells = {}
        self.orientation = orientation
        self.z_bottom = -77  # -64
        self.z_top = 0
        self.radius = 4.0
        self.well_offset = 9  # mm from center to center
        self.well_capacity = 300  # ul
        self.echem_height = -73 #-68

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

                    depth = self.z_bottom

                self.wells[well_id] = {
                    "coordinates": coordinates,
                    "contents": contents,
                    "volume": volume,
                    "depth": depth,
                    "status": "empty",
                    "CV-results": None,
                }

    def visualize_well_coordinates(self):
        """Plot the well plate on a coordinate plane"""
        x_coordinates = []
        y_coordinates = []
        for well_id, well_data in self.wells.items():
            x_coordinates.append(well_data["coordinates"]["x"])
            y_coordinates.append(well_data["coordinates"]["y"])
        plt.scatter(x_coordinates, y_coordinates)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Well Coordinates")
        plt.grid(True)
        plt.xlim(-400, 0)
        plt.ylim(-300, 0)
        plt.show()

    def get_coordinates(self, well_id):
        """Return the coordinate of a specific well"""
        coordinates_dict = self.wells[well_id]["coordinates"]
        # coordinates_list = [coordinates_dict["x"], coordinates_dict["y"], coordinates_dict["z"]]
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

    def check_volume(self, well_id, added_volume: float):
        """Check if a volume can fit in a specific well"""
        info_message = f"Checking if {added_volume} can fit in {well_id} ..."
        logging.info(info_message)
        if self.wells[well_id]["volume"] + added_volume >= self.well_capacity:
            raise OverFillException(
                well_id, self.volume, added_volume, self.well_capacity
            )

        # elif self.wells[well_id]["volume"] + added_volume < 0:
        #    raise OverDraftException(well_id, self.volume, added_volume, self.well_capacity)
        else:
            info_message = f"{added_volume} can fit in {well_id}"
            logging.info(info_message)
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
            logging.debug(debug_message)


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
    