"""
Vial class for creating vial objects with their position and contents
"""

# pylint: disable=line-too-long
import csv
import logging
from pathlib import Path
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from panda_lib.utilities import directory_picker, file_picker

from .sql_tools.db_setup import SessionLocal as LocalSession
from .sql_tools.panda_models import Vials
from .vessel import OverFillException

logger = logging.getLogger("panda")


class Vial(Vials):
    """
    Represents a vial object that inherits from the Vials database model class.

    Vials are stored in the db as unique records, where the position is the primary key.
    When changes are made to a vial the record is updated, or if it is a new position, the record is inserted.

    When a vial isntance is created, three paths may be taken like with a wellplate:
        1. A new vial is created with the given parameters.
        2. An existing vial is fetched from the db.
        3. The vial is reset to its defualt state. Defined as a vial with maximum volume and no contamination, and either no contents or contents at the max volume.

    As changes are made to a vial, the db is triggered to insert the old record into the vials_log table.
    This is not handled in this class, but in the db trigger, and mentioned here as a note.

    Attributes:
        position (str): The position of the vial.
        category (int): The category of the vial (0 for stock, 1 for waste).
        name (str): The name of the vial.
        contents(dict): The contents of the vial. Note: Stock vials have immutable contents.
        viscosity_cp (float, optional): The viscosity of the vial contents. Defaults to float(0.0).
        concentration (float, optional): The concentration of the vial contents. Defaults to float(0.0).
        density (float): The density of the solution in the vial.
        height (float): The height of the vial.
        radius (float): The radius of the vial.
        volume (float): The current volume of the vial.
        capacity (float): The maximum capacity of the vial.
        contamination (int): The number of times the vial has been contaminated.
        coordinates (VesselCoordinates): The coordinates of the vial.
        base_thickness (float): The thickness of the base of the vial.
        dead_volume (float): The dead volume of the vial.
        volume_height (float): The height of the volume in the vial.
        top (float): The top of the vial.
        bottom (float): The bottom of the vial.

    """

    def __init__(
        self,
        position: str,
        category: int,
        create_new: bool,
        activate: bool = True,
        session: Session = LocalSession(),
        **kwargs,
    ) -> None:
        """
        Initializes a new instance of the Vial class which inherits from the Vials database model class.
        ...
        """
        self.position = position
        self.category = category
        self.session = session
        self._contents = kwargs.get("contents", {})
        self._volume = kwargs.get("volume", 0.0)
        self._contamination = kwargs.get("contamination", 0)

        if create_new:
            self._create_or_update_vial(activate=activate, **kwargs)
        else:
            self._fetch_vial_from_db(activate=activate)

    def _create_or_update_vial(self, activate, **kwargs) -> None:
        with self.session as session:
            try:
                vial = session.execute(
                    select(Vials).filter_by(position=self.position)
                ).scalar_one_or_none()

                if vial is None:
                    # Insert new vial
                    super().__init__(
                        position=self.position,
                        category=self.category,
                        name=kwargs.get("name", ""),
                        contents=kwargs.get("contents", {}),
                        viscosity_cp=kwargs.get("viscosity_cp", 0.0),
                        concentration=kwargs.get("concentration", 1.0),
                        density=kwargs.get("density", 1.0),
                        height=kwargs.get("height", 64.0),
                        radius=kwargs.get("radius", 14.0),
                        volume=kwargs.get("volume", 20000.0),
                        capacity=kwargs.get("capacity", 20000.0),
                        contamination=kwargs.get("contamination", 0),
                        coordinates=kwargs.get("coordinates", {"x": 0, "y": 0, "z": 0}),
                        base_thickness=kwargs.get("base_thickness", 1.0),
                        dead_volume=kwargs.get("dead_volume", 1000.0),
                        active=kwargs.get("active", True if activate else False),
                    )
                    session.add(self)
                    # session.execute(insert(Vials).values(self.to_dict()))
                else:
                    # Update existing vial
                    for key, value in kwargs.items():
                        setattr(vial, key, value)
                    session.add(vial)

                session.commit()
                # self._fetch_vial_from_db()
            except SQLAlchemyError as e:
                session.rollback()
                raise e

    def _fetch_vial_from_db(
        self,
        activate: bool = True,
    ) -> None:
        with self.session as session:
            vial = session.execute(
                select(Vials).filter_by(position=self.position)
            ).scalar_one_or_none()
            if vial is not None:
                super().__init__(
                    position=vial.position,
                    category=vial.category,
                    name=vial.name,
                    contents=vial.contents,
                    viscosity_cp=vial.viscosity_cp,
                    concentration=vial.concentration,
                    density=vial.density,
                    height=vial.height,
                    radius=vial.radius,
                    volume=vial.volume,
                    capacity=vial.capacity,
                    contamination=vial.contamination,
                    coordinates=vial.coordinates,
                    base_thickness=vial.base_thickness,
                    dead_volume=vial.dead_volume,
                    volume_height=vial.volume_height,
                    top=vial.top,
                    bottom=vial.bottom,
                )
            else:
                raise ValueError(
                    f"Vial with position {self.position} does not exist in the db"
                )

            if activate:
                self.activeate_vial()

    def __str__(self) -> str:
        return f"{self.position}-{self.name} has {self.volume} ul liquid"

    def to_dict(self) -> dict:
        """Return the vial as a dictionary"""
        return {
            "position": self.position,
            "category": self.category,
            "name": self.name,
            "contents": self.contents,
            "viscosity_cp": self.viscosity_cp,
            "concentration": self.concentration,
            "density": self.density,
            "height": self.height,
            "radius": self.radius,
            "volume": self.volume,
            "capacity": self.capacity,
            "contamination": self.contamination,
            "coordinates": self.coordinates,
            "base_thickness": self.base_thickness,
            "dead_volume": self.dead_volume,
            "volume_height": self.volume_height,
            "top": self.top,
            "bottom": self.bottom,
        }

    # Although maybe inefficient we will update the vial record in the db with any change
    # to volume, contamination, or contents, we will do this with setters and getters
    # for the volume, contamination, and contents attributes

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = value
        self._update_vial_in_db()

    @property
    def contamination(self) -> int:
        return self._contamination

    @contamination.setter
    def contamination(self, value: int) -> None:
        self._contamination = value
        self._update_vial_in_db()

    @property
    def contents(self) -> dict:
        return self._contents

    @contents.setter
    def contents(self, value: dict) -> None:
        self._contents = value
        self._update_vial_in_db()

    def activeate_vial(self) -> None:
        """Activate the vial in the db"""
        with self.session as session:
            try:
                vial = session.execute(
                    select(Vials).filter_by(position=self.position)
                ).scalar_one_or_none()
                if vial is not None:
                    vial.active = True
                    session.add(vial)
                    session.commit()
                else:
                    raise ValueError(
                        f"Vial with position {self.position} does not exist in the db"
                    )
            except SQLAlchemyError as e:
                session.rollback()
                raise e

    def deactiveate_vial(self) -> None:
        """Deactivate the vial in the db"""
        with self.session as session:
            try:
                vial = session.execute(
                    select(Vials).filter_by(position=self.position)
                ).scalar_one_or_none()
                if vial is not None:
                    vial.active = False
                    session.add(vial)
                    session.commit()
                else:
                    raise ValueError(
                        f"Vial with position {self.position} does not exist in the db"
                    )
            except SQLAlchemyError as e:
                session.rollback()
                raise e

    def _update_vial_in_db(self) -> None:
        with self.session as session:
            try:
                vial = session.execute(
                    select(Vials).filter_by(position=self.position)
                ).scalar_one_or_none()
                if vial is not None:
                    vial.volume = self.volume
                    vial.contamination = self.contamination
                    vial.contents = self.contents
                    session.add(vial)  # Update or insert a new one if it doesn't exist
                    session.commit()
                else:
                    # raise ValueError(
                    #     f"Vial with position {self.position} does not exist in the db"
                    # )
                    logger.warning(
                        f"Vial with position {self.position} does not exist in the db"
                    )
                    logger.warning("Might be a new vial, creating a new record...")
            except SQLAlchemyError as e:
                session.rollback()
                raise e

    def reset_vial(self) -> None:
        """Reset the vial to its default state"""
        self.volume = self.capacity
        self.contamination = 0
        if self.category == 1:
            self.contents = {}  # Is a waste vial that starts empty
        else:
            self.contents = {self.contents[0]: self.capacity}
        self._update_vial_in_db()

    def add_contents(self, from_vessel: dict, volume: float) -> None:
        """Adds contents to the well in the database."""
        if volume <= 0:
            logger.debug("Volume must be positive to add contents.")
            return

        logger.debug("Adding contents to well...")

        # Check if adding the volume will exceed the vial's capacity
        if self.volume + volume > self.capacity:
            raise OverFillException(self.name, self.volume, volume, self.capacity)

        for key, val in from_vessel.items():
            if key in self.contents:
                self.contents[key] += val
            else:
                self.contents[key] = val

        self.volume += volume

        logger.debug("Updated contents: %s", self.contents)
        self.session.commit()

    def remove_contents(self, volume: float) -> dict:
        """Removes contents from the well in the database and returns the removed contents."""
        if volume == 0:
            logger.debug("Volume must be negative to remove contents.")
            return {}

        logger.debug("Removing contents from well...")

        if not self.contents or sum(self.contents.values()) == 0:
            logger.debug("Well %s is empty, nothing to remove.", self.name)
            return {}

        current_content_ratios = {
            key: value / sum(self.contents.values())
            for key, value in self.contents.items()
        }

        removed_contents = {}
        for key in self.contents:
            removed_volume = round(volume * current_content_ratios[key], 6)
            if key in self.contents:
                self.contents[key] += removed_volume
                if self.contents[key] < 0:
                    self.contents[key] = 0
                removed_contents[key] = removed_volume
            else:
                logger.debug(
                    "Key %s does not exist in well %s contents.", key, self.name
                )

        logger.debug("Removed contents: %s", removed_contents)
        self.session.commit()
        return removed_contents

    def check_volume(self, volume_to_add: float) -> bool:
        """
        Checks if the volume to be added to the vial is within the vial's capacity.

        Args:
            volume_to_add (float): The volume to be added or removed from the vial.

        Returns:
            bool: True if the volume will not exceed the vial's capacity or go below 0, False otherwise.
        """
        volume_to_add = float(volume_to_add)
        if (
            self.volume + volume_to_add > self.capacity
            or self.volume + volume_to_add < 0
        ):
            return False
        else:
            return True


class StockVial(Vial):
    """
    Represents a stock vial object that inherits from the Vial class.

    Stock vials are stored in the db as unique records, where the position is the primary key.
    When changes are made to a stock vial the record is updated, or if it is a new position, the record is inserted.

    As changes are made to a stock vial, the db is triggered to insert the old record into the vials_log table.
    This is not handled in this class, but in the db trigger, and mentioned here as a note.

    Attributes:
        position (str): The position of the vial.
        category (int): The category of the vial (0 for stock, 1 for waste).
        name (str): The name of the vial.
        contents(dict): The contents of the vial. Note: Stock vials have immutable contents.
        viscosity_cp (float, optional): The viscosity of the vial contents. Defaults to float(0.0).
        concentration (float, optional): The concentration of the vial contents. Defaults to float(0.0).
        density (float): The density of the solution in the vial.
        height (float): The height of the vial.
        radius (float): The radius of the vial.
        volume (float): The current volume of the vial.
        capacity (float): The maximum capacity of the vial.
        contamination (int): The number of times the vial has been contaminated.
        coordinates (VesselCoordinates): The coordinates of the vial.
        base_thickness (float): The thickness of the base of the vial.
        dead_volume (float): The dead volume of the vial.
        volume_height (float): The height of the volume in the vial.
        top (float): The top of the vial.
        bottom (float): The bottom of the vial.

    """

    def __init__(
        self,
        position: str,
        create_new: bool,
        **kwargs,
    ) -> None:
        """
        Initializes a new instance of the StockVial class which inherits from the Vial class.
        ...
        """
        super().__init__(position, 0, create_new, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"


class WasteVial(Vial):
    """
    Represents a waste vial object that inherits from the Vial class.

    Waste vials are stored in the db as unique records, where the position is the primary key.
    When changes are made to a waste vial the record is updated, or if it is a new position, the record is inserted.

    As changes are made to a waste vial, the db is triggered to insert the old record into the vials_log table.
    This is not handled in this class, but in the db trigger, and mentioned here as a note.

    Attributes:
        position (str): The position of the vial.
        category (int): The category of the vial (0 for stock, 1 for waste).
        name (str): The name of the vial.
        contents(dict): The contents of the vial. Note: Stock vials have immutable contents.
        viscosity_cp (float, optional): The viscosity of the vial contents. Defaults to float(0.0).
        concentration (float, optional): The concentration of the vial contents. Defaults to float(0.0).
        density (float): The density of the solution in the vial.
        height (float): The height of the vial.
        radius (float): The radius of the vial.
        volume (float): The current volume of the vial.
        capacity (float): The maximum capacity of the vial.
        contamination (int): The number of times the vial has been contaminated.
        coordinates (VesselCoordinates): The coordinates of the vial.
        base_thickness (float): The thickness of the base of the vial.
        dead_volume (float): The dead volume of the vial.
        volume_height (float): The height of the volume in the vial.
        top (float): The top of the vial.
        bottom (float): The bottom of the vial.

    """

    def __init__(
        self,
        position: str,
        create_new: bool,
        **kwargs,
    ) -> None:
        """
        Initializes a new instance of the WasteVial class which inherits from the Vial class.
        ...
        """
        super().__init__(position, 1, create_new, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} has {self.volume} ul of {self.density} g/ml liquid"


def get_active_vials(session: Session = LocalSession()) -> List[Vial]:
    """
    Get the active vials from the db
    """
    vials = []
    try:
        with session as session:
            vials = (
                session.execute(select(Vials).filter_by(active=True)).scalars().all()
            )
    except Exception as e:
        logger.error("Error occurred while reading vials from the db: %s", e)
        logger.error("Continuing with empty vial list....")
        logger.exception(e)

    return vials


def read_vials() -> Tuple[List[StockVial], List[WasteVial]]:
    """
    Read in the virtual vials from the json file
    """

    # Get the vial information from the vials table in the db
    active_vials = get_active_vials()

    list_of_stock_solutions = []
    list_of_waste_solutions = []
    for vial in active_vials:
        if vial.category == 0:
            list_of_stock_solutions.append(StockVial(**vial))
        elif vial.category == 1:
            list_of_waste_solutions.append(WasteVial(**vial))

    return list_of_stock_solutions, list_of_waste_solutions


def reset_vials(vialgroup: str) -> None:
    """
    Resets the volume and contamination of the current vials to their capacity and 0 respectively

    Args:
        vialgroup (str): The group of vials to be reset. Either "stock" or "waste"
    """

    if vialgroup not in ["stock", "waste", "test"]:
        logger.error("Invalid vial group %s given for resetting vials", vialgroup)
        raise ValueError

    stock, waste = read_vials()

    if vialgroup == "stock":
        vials = stock
    elif vialgroup == "waste":
        vials = waste
    else:
        vials = stock + waste

    for vial in vials:
        vial.reset_vial()


def delete_vial_position_from_db(
    position: str, session: Session = LocalSession()
) -> None:
    """Delete the vial position from the db"""
    with session as session:
        try:
            vial = session.execute(
                select(Vials).filter_by(position=position)
            ).scalar_one_or_none()
            if vial is not None:
                session.delete(vial)
                session.commit()
            else:
                raise ValueError(
                    f"Vial with position {position} does not exist in the db"
                )
        except SQLAlchemyError as e:
            session.rollback()
            raise e


def input_new_vial_values(vialgroup: str) -> None:
    """A command line interface to input new vial values into the db

    Args:
        vialgroup (str): The group of vials to be input. Either "stock" or "waste"
    """

    stock, waste = read_vials()

    if vialgroup == "stock":
        vials = stock
    elif vialgroup == "waste":
        vials = waste
    else:
        vials = stock + waste

    # Print the current vials and their values
    print("Current vials:")

    max_lengths = [10, 20, 20, 15, 15, 15, 15]  # Initialize max lengths for each column
    vial_lines = []
    for vial in vials:
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

        values = [
            vial.position,
            vial.name,
            str(vial.contents),
            vial.density,
            vial.volume,
            vial.capacity,
            vial.contamination,
        ]
        max_lengths = [
            max(max_lengths[i], len(str(values[i])) + 2) for i in range(len(values))
        ]  # Update max lengths

        vial_lines.append(
            f"{values[0]:<{max_lengths[0]}} {values[1]:<{max_lengths[1]}} {values[2]:<{max_lengths[2]}} {values[3]:<{max_lengths[3]}} {values[4]:<{max_lengths[4]}} {values[5]:<{max_lengths[5]}} {values[6]:<{max_lengths[6]}}"
        )

    header_string = f"{'Position':<{max_lengths[0]}} {'Name':<{max_lengths[1]}} {'Contents':<{max_lengths[2]}} {'Density':<{max_lengths[3]}} {'Volume':<{max_lengths[4]}} {'Capacity':<{max_lengths[5]}} {'Contamination':<{max_lengths[6]}}"
    print(header_string)
    for line in vial_lines:
        print(line)

    # Prompt the user for the position of the vial to change
    while True:
        choice = input(
            "Which vial would you like to change? Enter the position of the vial or 'q' if finished: "
        )
        if choice == "q":
            break
        for vial in vials:
            if vial.position == choice:
                print(
                    "Please enter the new values for the vial, if you leave any blank the value will not be changed"
                )
                print(f"\nVial {vial.position}:")
                new_name = input(
                    f"Enter the new name of the vial (Current name is {vial.name}): "
                )
                if new_name != "":
                    vial.name = new_name
                new_contents = input(
                    f"Enter the new contents of the vial (Current contents are {vial.contents}): "
                )
                if new_contents != "":
                    vial.contents = new_contents
                new_density = input(
                    f"Enter the new density of the vial (Current density is {vial.density}): "
                )
                if new_density != "":
                    vial.density = float(new_density)
                new_volume = input(
                    f"Enter the new volume of the vial (Current volume is {vial.volume}): "
                )
                if new_volume != "":
                    vial.volume = float(new_volume)
                new_capacity = input(
                    f"Enter the new capacity of the vial (Current capacity is {vial.capacity}): "
                )
                if new_capacity != "":
                    vial.capacity = float(new_capacity)
                new_contamination = input(
                    f"Enter the new contamination of the vial (Current contamination is {vial.contamination}): "
                )
                if new_contamination != "":
                    try:
                        vial.contamination = int(new_contamination)
                    except ValueError:
                        print("Invalid value for contamination. Should be integer")
                        continue

                vial._update_vial_in_db()
                # print("\r" + " " * 100 + "\r", end="")  # Clear the previous table
                print("\nCurrent vials:")
                print(header_string)
                for line in vial_lines:
                    print(line)
                break
        else:
            print("Invalid vial position")
            continue


def generate_template_vial_csv_file() -> None:
    """
    Generate a template vial csv file that can be filled with
    multiple vials and their values
    """
    filename = "vials.csv"

    # Prompt the user to idenitfy the directory to save the file
    directory = directory_picker()

    filename = Path(directory) / Path(filename)  # Convert to a Path object

    with open(filename, "w", encoding="UTF-8", newline="") as file:
        csv_writer = csv.writer(file)
        # Write out the header from the Vials table in the db
        csv_writer.writerow(
            [
                "position",
                "category",
                "name",
                "contents",
                "viscosity_cp",
                "concentration",
                "density",
                "height",
                "radius",
                "volume",
                "capacity",
                "contamination",
                "coordinates",
                "base_thickness",
                "dead_volume",
                "volume_height",
                "active",
            ]
        )

        # Write out a template vial for s0
        csv_writer.writerow(
            [
                "s0",
                0,
                "chemicalA",
                "{}",
                0.0,
                1.0,
                1.0,
                64.0,
                14.0,
                20000.0,
                20000.0,
                0,
                '{"x": 0, "y": 0, "z": 0}',
                1.0,
                1000.0,
                0.0,
                True,
            ]
        )

        # Write out a template vial for w0
        csv_writer.writerow(
            [
                "w0",
                1,
                "waste",
                "{}",
                0.0,
                1.0,
                1.0,
                64.0,
                14.0,
                20000.0,
                20000.0,
                0,
                '{"x": 0, "y": 0, "z": 0}',
                1.0,
                1000.0,
                0.0,
                True,
            ]
        )

    print(f"Template vial csv file saved as {filename}")


def import_vial_csv_file(filename: str = None) -> None:
    """
    Import the vial csv file and add the vials to the db
    """
    if not filename:
        filename = file_picker("csv")
    if not filename:
        return

    set_as_active = input("Set the vials as active? (y/n): ")
    if set_as_active.lower() == "y":
        set_as_active = True
    else:
        set_as_active = False

    with open(filename, "r", encoding="UTF-8") as file:
        csv_reader = csv.DictReader(file)
        vials = []
        for row in csv_reader:
            # By setting create_new to True, the vial will be inserted into the db
            vials.append(
                Vial(
                    **row,
                    create_new=True,
                )
            )

    print(f"{len(vials)} Vials imported from {filename}")
    print("Vials:")
    for vial in vials:
        print(vial)
    return vials
