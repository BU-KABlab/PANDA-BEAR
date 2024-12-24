"""
Wellplate data class for the echem experiment.
This class is used to store the data for the
wellplate and the wells in it.
"""

import logging

# pylint: disable=line-too-long
from typing import Tuple

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from panda_lib.errors import OverDraftException, OverFillException
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import (
    ExperimentParameters,
    ExperimentResults,
    Experiments,
    MillConfig,
    PlateTypes,
    WellModel,
    Wellplates,
)

from .sql_tools.sql_wellplate import (
    check_if_wellplate_exists,
    count_wells_with_new_status,
    select_current_wellplate_info,
)

## set up logging to log to both the pump_control.log file and the PANDA_SDL.log file
logger = logging.getLogger("panda")


class Well_v2(WellModel):
    """
    Represents a well object. Inherits from the WellHx model class.
    """

    def __init__(self, *args, **kwards):
        super().__init__(*args, **kwards)
        self.campaign_id: int = 0
        self.type_number: int = 0
        self.session: Session = SessionLocal()

    def __str__(self) -> str:
        """Returns a string representation of the well."""
        return f"Well {self.well_id} - Experiment:{self.experiment_id} with volume {self.volume} and status {self.status}"

    def update_volume(self, added_volume: float) -> None:
        """Updates the volume of the vessel by adding the specified volume."""
        added_volume = round(added_volume, 6)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        if self.volume + added_volume < float(0):
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )

        self.volume = self.volume + added_volume
        logger.debug(
            "%s&%s",
            self.name + "_" + self.position if self.position is not None else self.name,
            self.volume,
        )
        self.session.commit()

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
            raise OverFillException(
                self.name, self.volume, volume_to_add, self.capacity
            )
        if self.volume + volume_to_add < float(0):
            raise OverDraftException(
                self.name, self.volume, volume_to_add, self.capacity
            )
        return True

    def add_contents(self, from_vessel: dict, volume: float) -> None:
        """Adds contents to the well in the database."""
        if volume <= 0:
            logger.debug("Volume must be positive to add contents.")
            return

        logger.debug("Adding contents to well...")

        # Check if adding the volume will exceed the well's capacity
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

    def update_status(self, new_status: str) -> None:
        """Updates the status of the well in the well_hx table."""
        self.status = new_status
        logger.debug("Well %s status updated to %s", self.name, self.status)
        self.session.commit()

    def update_well_coordinates(self, new_coordinates: dict) -> None:
        """Update the coordinates of a specific well"""
        self.coordinates = new_coordinates
        logger.debug("Well %s coordinates updated to %s", self.name, self.coordinates)
        self.session.commit()


class Wellplate(Wellplates):
    """
    Represents a well plate and each well in it.
    Is defined by by the Wellplates model class of the database, but also
    contains the well objects in a dictionary. The well objects themselves are defined by the Well_v2 class.

    Attributes:
        id (int): The well plate ID.
        type_id (int): The well plate type ID.
        current (bool): Is the wellplate the currently active wellplate on the deck.
        a1_x (float): The x-coordinate of well A1.
        a1_y (float): The y-coordinate of well A1.
        orientation (int): The orientation of the well plate.
        rows (str): The rows of the well plate.
        cols (int): The columns of the well plate.
        echem_height (float): The height of the electrochemical cell.
        image_height (float): The height of the image.
        coordinates (dict): The object coordinates.
        base_thickness (float): The base thickness of the object.
        height (float): The height of the object.
        top (float): The top of the object.
        bottom (float): The bottom of the object.
        name (str): The name of the object.
        wells (dict): The wells in the well plate.
    """

    def __init__(
        self,
        session: Session = SessionLocal,
        plate_id=None,
        type_id=None,
        create_new=False,
        plate: Wellplates = None,
        type: PlateTypes = None,
        wells: dict[str:Well_v2] = None,
        orientation: int = 0,
        **kwargs,
    ):
        """
        Initialize the Wellplate_v2 object.

        Args:
            session (Session): SQLAlchemy session for database operations.
            plate_id (int, optional): ID of the wellplate to load from the database.
            type_id (int, optional): Type ID of the wellplate (required for new creation).
            create_new (bool): Whether to create a new wellplate.
            **kwargs: Additional attributes for new wellplates.
        """
        self.session = session
        self.orientation = orientation
        self.plate_id: int = plate_id
        self.plate: Wellplates = plate
        self.type: PlateTypes = type
        self.wells: dict[str:Well_v2] = wells

        # Verify when create_new is True and plate_id is specified that the plate_id does not exist
        if create_new and self.plate_id:
            if check_if_wellplate_exists(plate_id):
                create_new = False

        if create_new:
            if not type_id:
                raise ValueError("type_id is required to create a new wellplate.")
            self.type: PlateTypes = session.query(PlateTypes).get(type_id)
            if not self.type:
                raise ValueError(f"PlateType with id {type_id} does not exist.")

            # Create a new WellPlates entry
            if self.plate_id:
                # The user wants a new plate but is specifying a plate_id. This is allowed.
                self.plate: Wellplates = Wellplates(
                    id=self.plate_id, type_id=type_id, **kwargs
                )
            else:
                # Create a new wellplate in the database and let the database assign the id
                self.plate: Wellplates = Wellplates(type_id=type_id, **kwargs)
            session.add(self.plate)

            # Initialize wells
            self.wells = self._create_wells_from_type()
            for well in self.wells.values():
                session.add(well)
            session.commit()

        elif self.plate_id:
            # Load an existing wellplate from the database
            self.plate: Wellplates = session.query(Wellplates).get(self.plate_id)
            if not self.plate:
                raise ValueError(f"Wellplate with id {self.plate_id} does not exist.")
            self.type: PlateTypes = session.query(PlateTypes).get(self.plate.type_id)
            self.wells = self._load_wells_from_db()
        else:
            # Assume the user wants the current wellplate
            plate_id, type_id, _ = select_current_wellplate_info()
            self.plate: Wellplates = session.query(Wellplates).get(plate_id)
            self.type: PlateTypes = session.query(PlateTypes).get(type_id)
            self.wells = self._load_wells_from_db()

        # else:
        #     raise ValueError("Either plate_id or create_new must be specified.")

    def _create_wells_from_type(self):
        """Create wells based on the type of wellplate."""
        wells: dict[str:Well_v2] = {}
        rows: list = list(self.plate.rows)
        cols: range = range(1, int(self.plate.cols) + 1)

        for row in rows:
            for col in cols:
                coordinates = self.calculate_coordinates(row, col)
                wells[str(row) + str(col)] = Well_v2(
                    well_id=f"{row}{col}",
                    plate_id=self.plate.id,
                    coordinates=coordinates,
                    capacity=self.type.capacity_ul,
                )
        return wells

    def _load_wells_from_db(self):
        """Load wells from the database for the current plate."""
        wells = {}
        with self.session as session:
            query = (
                session.execute(select(Well_v2).filter_by(plate_id=self.plate.id))
                .scalars()
                .all()
            )
        for well in query:
            wells[(well.well_id)] = well
        return wells

    def __calculate_rotated_position(
        self, x: float, y: float, orientation: int, a1_x: float, a1_y: float
    ) -> tuple:
        """Rotate coordinates based on the orientation of the well plate."""
        if orientation == 0:
            return a1_x - x, a1_y - y
        elif orientation == 1:
            return a1_x + x, a1_y + y
        elif orientation == 2:
            return a1_x + y, a1_y - x
        elif orientation == 3:
            return a1_x - y, a1_y + x
        else:
            raise ValueError("Invalid orientation value. Must be 0, 1, 2, or 3.")

    def calculate_coordinates(self, row: str, col: int) -> dict:
        """Calculate well coordinates based on the wellplate type and orientation."""
        x = (col - 1) * self.type.x_spacing
        y = (ord(row.upper()) - ord("A")) * self.type.y_spacing
        x, y = self.__calculate_rotated_position(
            x, y, self.orientation, self.plate.a1_x, self.plate.a1_y
        )
        return {
            "x": x,
            "y": y,
            "z": self.plate.coordinates["z"],
        }  # TODO see if you can use coordinate.z

    def recalculate_well_positions(self):
        """Update all well coordinates based on the current plate a1 x,y position."""
        for well_id, well in self.wells.items():
            well: Well_v2
            row: str = well_id[0]
            col: int = int(well_id[1:])
            well.coordinates = self.calculate_coordinates(row, col)

    def update_db(self):
        """Update the wellplate and wells in the database."""
        self.session.commit()

    def __repr__(self):
        return f"<Wellplate_v2(id={self.plate.id}, type_id={self.plate.type_id}, wells={len(self.wells)})>"

    def print_well_grid(self):
        """Print a grid of well positions."""
        rows = list(self.plate.rows)
        cols = range(1, int(self.plate.cols) + 1)
        for row in rows:
            for col in cols:
                print(f"{row}{col}", end=" ")
            print()

    def change_orientation(self, new_orientation: int):
        """Change the orientation of the wellplate."""
        self.orientation = new_orientation
        self.recalculate_well_positions()
        self.update_db()

    def activate_wellplate(self):
        """Set the wellplate as the current wellplate."""
        # Set the current wellplate to false for all wellplates

        # Set all wellplates to not current
        with self.session as session:
            session.execute(update(Wellplates).values(current=False))

        # Set the current wellplate to true and update the database
        self.plate.current = True
        self.update_db()

    def deactivate_wellplate(self, new_active_plate_id: int = None):
        """Deactivate the wellplate."""

        # Set the current wellplate to false and update the database
        self.plate.current = False
        self.update_db()
        if new_active_plate_id:
            # Set the new active wellplate to true and update the database
            with self.session as session:
                new_active_plate = session.execute(
                    select(Wellplates).filter_by(id=new_active_plate_id)
                ).scalar_one_or_none()
                if new_active_plate:
                    new_active_plate.current = True

    # NOTE: Probably not needed as it will be a rare operation
    # def remove_wellplate(self):
    #     """Remove the wellplate and all of its wells from the database. This is irreversible."""
    #     self.session.delete(self.plate)
    #     self.update_db()


def _remove_wellplate_from_db(plate_id: int, session: Session = SessionLocal()) -> None:
    """Removed all wells for the given plate id in well_hx, removes the plate id from the wellplate table"""
    user_choice = input(
        "Are you sure you want to remove the wellplate and all its wells from the database? This is irreversible. (y/n): "
    )
    if not user_choice:
        print("No action taken")
        return
    if user_choice.strip().lower()[0] != "y":
        print("No action taken")
        return
    with session as session:
        wells_to_delete = (
            session.execute(select(WellModel).filter_by(plate_id=plate_id))
            .scalars()
            .all()
        )
        for well in wells_to_delete:
            session.delete(well)

        plate_to_delete = session.execute(
            select(Wellplates).filter_by(id=plate_id)
        ).scalar_one_or_none()
        if plate_to_delete:
            session.delete(plate_to_delete)

        session.commit()

        # Confirm by checking if the wells and plate still exist
        wells = (
            session.execute(select(WellModel).filter_by(plate_id=plate_id))
            .scalars()
            .all()
        )
        plate = session.execute(
            select(Wellplates).filter_by(id=plate_id)
        ).scalar_one_or_none()
        if not wells and not plate:
            print(
                f"Wellplate {plate_id} and its wells have been removed from the database"
            )
        else:
            print(f"Error occurred while deleting wellplate {plate_id}")


def _remove_experiment_from_db(
    experiment_id: int, session: Session = SessionLocal()
) -> tuple[bool, str]:
    """Removes the experiment from the database"""

    # Check that no experiment_results exist for this experiment. If they do, do not delete the experiment
    results = None
    with session as session:
        results = (
            session.execute(
                select(ExperimentResults).filter_by(experiment_id=experiment_id)
            )
            .scalars()
            .all()
        )

    if results:
        return False, "Experiment has associated results"

    # Remove the experiment from the database in three steps:
    # 1. Remove the experiment from the experiments table
    # 2. Remove the experiment parameters from the experiment_parameters table
    # 3. Update the well_hx table to remove the experiment_id and project_id
    try:
        with session as session:
            out_experiments = (
                session.query(Experiments)
                .filter(Experiments.experiment_id == experiment_id)
                .delete()
            )
            out_params = (
                session.query(ExperimentParameters)
                .filter(ExperimentParameters.experiment_id == experiment_id)
                .delete()
            )
            out_wells = (
                session.query(WellModel)
                .filter(WellModel.experiment_id == experiment_id)
                .update({"experiment_id": None, "project_id": None, "status": "new"})
            )
            session.commit()

        if (out_experiments + out_params + out_wells) > 0:
            return True, "Experiment deleted successfully"
        else:
            return False, "Experiment not found"
    except Exception as e:
        print(f"Error occurred while deleting the experiment: {e}")
        return False, f"Error occurred while deleting the experiment: {e}"


def change_wellplate_location(session: Session = SessionLocal()):
    """Change the location of the wellplate"""

    with session as session:
        mill_config = (
            session.query(MillConfig).order_by(MillConfig.id.desc()).first()
        ).config
        working_volume = {
            "x": float(mill_config["$130"]),
            "y": float(mill_config["$131"]),
            "z": float(mill_config["132"]),
        }

    ## Get the current plate id and location
    current_plate_id, current_type_number, _ = select_current_wellplate_info()

    print(f"Current wellplate id: {current_plate_id}")
    print(f"Current wellplate type number: {current_type_number}")

    wellplate = Wellplate(
        session=session,
        plate_id=current_plate_id,
    )

    ## Ask for the new location
    while True:
        new_location_x = input("Enter the new x location of the wellplate: ")
        if new_location_x == "":
            new_location_x = wellplate.a1_x
            break
        try:
            new_location_x = float(new_location_x)
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue
        if new_location_x > working_volume["x"] and new_location_x < 0:
            break

        print(
            f"Invalid input. Please enter a value between {working_volume['x']} and 0."
        )

    while True:
        new_location_y = input("Enter the new y location of the wellplate: ")

        if new_location_y == "":
            new_location_y = wellplate.a1_y
            break
        else:
            try:
                new_location_y = float(new_location_y)
            except ValueError:
                print("Invalid input. Please enter a number.")
                continue

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
Enter the new orientation of the wellplate: """
            )  # TODO Use these instructions to fix the current rotation function
        )
        if new_orientation in [0, 1, 2, 3]:
            break
        else:
            print("Invalid input. Please enter 0, 1, 2, or 3.")

    wellplate.a1_x = new_location_x
    wellplate.a1_y = new_location_y
    wellplate.orientation = new_orientation
    wellplate.coordinates = {
        "x": new_location_x,
        "y": new_location_y,
        "z": wellplate.coordinates["z"],
    }
    wellplate.recalculate_well_positions()
    wellplate.update_db()


# def load_new_wellplate(
#     ask: bool = False,
#     new_plate_id: Optional[int] = None,
#     new_wellplate_type_number: Optional[int] = None,
# ) -> int:
#     """
#     Save the current wellplate, reset the well statuses to new.
#     If no plate id or type number given assume same type number as the current wellplate and increment wellplate id by 1

#     Args:
#         new_plate_id (int, optional): The plate id being loaded. Defaults to None. If None, the plate id will be incremented by 1
#         new_wellplate_type_number (int, optional): The type of wellplate. Defaults to None. If None, the type number will not be changed

#     Returns:
#         int: The new wellplate id
#     """
#     (
#         current_wellplate_id,
#         current_type_number,
#         current_wellplate_is_new,
#     ) = select_current_wellplate_info()

#     if ask:
#         new_plate_id = input(
#             f"Enter the new wellplate id (Current id is {current_wellplate_id}): "
#         )
#         new_wellplate_type_number = input(
#             f"Enter the new wellplate type number (Current type is {current_type_number}): "
#         )

#     else:
#         if new_plate_id is None or new_plate_id == "":
#             new_plate_id = current_wellplate_id + 1
#         if new_wellplate_type_number is None or new_wellplate_type_number == "":
#             new_wellplate_type_number = current_type_number

#     if current_wellplate_is_new and new_plate_id is None or new_plate_id == "":
#         return current_wellplate_id

#     ## Check if the new plate id exists in the well hx
#     ## If so, then load in that wellplate
#     ## If not, then create a new wellplate
#     if new_plate_id is None or new_plate_id == "":
#         new_plate_id = current_wellplate_id + 1
#     else:
#         new_plate_id = int(new_plate_id)

#     if new_wellplate_type_number is None or new_wellplate_type_number == "":
#         new_wellplate_type_number = current_type_number
#     else:
#         new_wellplate_type_number = int(new_wellplate_type_number)

#     ## Check if the wellplate exists in the well_hx table
#     already_exists = check_if_wellplate_exists(new_plate_id)
#     logger.debug("Wellplate exists: %s", already_exists)
#     if not already_exists:
#         add_wellplate_to_table(new_plate_id, new_wellplate_type_number)
#         update_current_wellplate(new_plate_id)
#         new_wellplate = Wellplate(
#             type_number=new_wellplate_type_number,
#             new_well_plate=True,
#             plate_id=new_plate_id,
#         )

#     else:
#         logger.debug(
#             "Wellplate already exists in the database. Setting as current wellplate"
#         )
#         update_current_wellplate(new_plate_id)
#         # TODO: Possibly run recaclulate well locations here
#         return new_plate_id

#     logger.info(
#         "Wellplate %d saved and wellplate %d loaded",
#         int(current_wellplate_id),
#         int(new_plate_id),
#     )
#     return new_wellplate.plate_id


# def load_new_wellplate_sql(
#     ask: bool = False,
#     new_plate_id: Optional[int] = None,
#     new_wellplate_type_number: Optional[int] = None,
# ) -> int:
#     """
#     Save the current wellplate, reset the well statuses to new.
#     If no plate id or type number given assume same type number as the current wellplate and increment wellplate id by 1

#     Args:
#         new_plate_id (int, optional): The plate id being loaded. Defaults to None. If None, the plate id will be incremented by 1
#         new_wellplate_type_number (int, optional): The type of wellplate. Defaults to None. If None, the type number will not be changed

#     Returns:
#         int: The new wellplate id
#     """
#     # Get the current wellpate from the wellplates table
#     current_wellplate_id, current_type_number, current_wellplate_is_new = (
#         select_current_wellplate_info()
#     )

#     if ask:
#         new_plate_id = int(
#             input(
#                 f"Enter the new wellplate id (Current id is {current_wellplate_id}): "
#             )
#         )
#         new_wellplate_type_number = int(
#             input(
#                 f"Enter the new wellplate type number (Current type is {current_type_number}): "
#             )
#         )
#     else:
#         if new_plate_id is None or new_plate_id == "":
#             new_plate_id = current_wellplate_id + 1
#         if new_wellplate_type_number is None or new_wellplate_type_number == "":
#             new_wellplate_type_number = current_type_number

#     if current_wellplate_is_new and new_plate_id is None or new_plate_id == "":
#         return current_wellplate_id

#     ## Check if the new plate id exists in the well hx
#     ## If so, then load in that wellplate
#     ## If not, then create a new wellplate
#     if new_plate_id is None or new_plate_id == "":
#         new_plate_id = current_wellplate_id + 1
#     else:
#         new_plate_id = int(new_plate_id)

#     if new_wellplate_type_number is None:
#         new_wellplate_type_number = current_type_number
#     else:
#         new_wellplate_type_number = int(new_wellplate_type_number)

#     ## If the wellplate exists in the well hx, then load it
#     wellplate_exists = check_if_wellplate_exists(new_plate_id)
#     if wellplate_exists:
#         logger.debug("Wellplate already exists in the database. Returning new_plate_id")
#         logger.debug("Loading wellplate")
#         update_current_wellplate(new_plate_id)
#     else:
#         logger.debug("Creating new wellplate: %d", new_plate_id)
#         new_wellplate = Wellplate(
#             type_number=new_wellplate_type_number, new_well_plate=True
#         )
#         new_wellplate.plate_id = new_plate_id
#         new_wellplate.recalculate_well_locations()
#         new_wellplate.save_wells_to_db()

#         logger.info(
#             "Wellplate %d saved and wellplate %d loaded",
#             int(current_wellplate_id),
#             int(new_plate_id),
#         )
#     return new_plate_id


def read_current_wellplate_info() -> Tuple[int, int, int]:
    """
    Read the current wellplate

    Returns:
        int: The current wellplate id
        int: The current wellplate type number
        int: Number of new wells
    """
    current_plate_id, current_type_number, _ = select_current_wellplate_info()
    new_wells = count_wells_with_new_status(current_plate_id)
    return int(current_plate_id), int(current_type_number), new_wells


if __name__ == "__main__":
    # Lets add a wellplate to the database
    pass
