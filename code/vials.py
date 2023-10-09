'''
Vial class for creating vial objects with their position and contents
'''
# pylint: disable=line-too-long
import json
import logging
import math
import pathlib
from vials import Vial as Vials

def read_vials(filename) -> list[Vials]:
    """
    Read in the virtual vials from the json file
    """
    cwd = pathlib.Path(__file__).parents[0]
    filename_ob = cwd / filename
    with open(filename_ob, "r", encoding="ascii") as file:
        vial_parameters = json.load(file)

    sol_objects = []
    for items in vial_parameters:
        sol_objects.append(
            Vial(
                position=items["position"],
                x_coord=items["x"],
                y_coord=items["y"],
                volume=items["volume"],
                name=items["name"],
                contents=items["contents"],
                # capacity=items["capacity"],
                # bottom=items["bottom"],
                # height=items["height"],
                filepath=filename,
            )
        )
    return sol_objects

def update_vials(vial_objects: list[Vials], filename):
    """
    Update the vials in the json file
    """
    cwd = pathlib.Path(__file__).parents[0]
    filename_ob = cwd / filename
    with open(filename_ob, "r", encoding="ascii") as file:
        vial_parameters = json.load(file)

    for vial in vial_objects:
        for items in vial_parameters:
            if items["name"] == vial.name:
                items["volume"] = vial.volume
                items["contamination"] = vial.contamination
                break

    with open(filename_ob, "w", encoding="ascii") as file:
        json.dump(vial_parameters, file, indent=4)

    return 0

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
        filepath=None,
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
        self.base = math.pi * math.pow(self.radius, 2.0)
        self.depth = self.vial_height_calculator(self.radius*2,self.volume) + self.bottom
        self.contamination = 0
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
        logging.info(logging_msg)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )
        else:
            logging_msg = f"{added_volume} can fit in {self.name}"
            logging.info(logging_msg)
            return True

    def write_volume_to_disk(self):
        """
        Writes the current volume to a json file
        """
        # logging.info(f'Writing {self.name} volume to {self.filepath}...')
        # with open(self.filepath, 'w') as f:
        #     json.dump(self.volume, f, indent=4)
        # return 0
        logging.info("Writing %s volume to vial file...", self.name)

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

    def update_volume(self, added_volume: float):
        """
        Updates the volume of the vial
        """
        logging.info("Updating %s volume...", self.name)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        if self.volume + added_volume < 0:
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )
        self.volume += added_volume
        self.write_volume_to_disk()
        self.depth = (
            self.vial_height_calculator((self.radius * 2), self.volume)
            + self.bottom
        )
        if self.depth < self.bottom:
            self.depth = self.bottom
        logging.debug("New volume: %s | New depth: %s", self.volume, self.depth)
        self.contamination += 1
        return 0

    def vial_height_calculator(self, diameter_mm, volume_ul):
        """
        Calculates the height of a volume of liquid in a vial given its diameter (in mm).
        """
        radius_mm = diameter_mm / 2
        area_mm2 = 3.141592653589793 * radius_mm**2
        volume_mm3 = volume_ul  # 1 ul = 1 mm3
        liquid_height_mm = volume_mm3 / area_mm2
        return liquid_height_mm


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
