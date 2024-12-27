"""
Wellplate data class for the echem experiment.
This class is used to store the data for the
wellplate and the wells in it.
"""

import logging

# pylint: disable=line-too-long
from typing import Optional, Tuple, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from panda_lib.errors import OverDraftException, OverFillException
from panda_lib.schemas import (
    PlateTypeModel,
    WellplateReadModel,
    WellplateWriteModel,
    WellReadModel,
    WellWriteModel,
)
from panda_lib.services import WellplateService, WellService
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import (
    ExperimentParameters,
    ExperimentResults,
    Experiments,
    MillConfig,
    WellModel,
    Wellplates,
)

## set up logging to log to both the pump_control.log file and the PANDA_SDL.log file
logger = logging.getLogger("panda")


# Define TypedDict for Well kwargs
class WellKwargs(TypedDict, total=False):
    """
    TypedDict for Well kwargs

    Attributes:
    -----------
    name: str
    volume: float
    capacity: float
    height: float
    radius: float
    contamination: int
    dead_volume: float
    contents: dict
    coordinates: dict
    """

    name: str
    volume: float
    capacity: float
    height: float
    radius: float
    contamination: int
    dead_volume: float
    contents: dict
    coordinates: dict


# Define TypedDict for WellPlate kwargs
class WellplateKwargs(TypedDict, total=False):
    """
    TypedDict for WellPlate kwargs

    Attributes:
    -----------
    type_id: int
    a1_x: float
    a1_y: float
    orientation: int
    rows: str
    cols: int
    echem_height: float
    image_height: float
    coordinates: dict
    """

    name: str
    type_id: int
    a1_x: float = 0.0
    a1_y: float = 0.0
    orientation: int = 0
    rows: str = "ABCDEFGH"
    cols: int = 12
    echem_height: float = 0.0
    image_height: float = 0.0
    coordinates: dict = {"x": 0.0, "y": 0.0, "z": 0.0}


class Well:
    """
    Class to represent a well in a wellplate.

    Attributes:
    -----------
    well_id: str
        The well id
    plate_id: int
        The plate id
    session: Session
        The database session
    create_new: bool
        If True, create a new well
    kwargs: WellKwargs
        Keyword arguments for making the well
    well_data: Optional[WellReadModel]
        The well data

    Methods:
    --------
    create_new_well(**kwargs: WellKwargs)
        Create a new well
    load_well()
        Load the well
    save()
        Save the well
    add_contents(from_vessel: dict, volume: float)
        Add contents to the well
    remove_contents(volume: float) -> dict
        Remove contents from the well
    update_status(new_status: str)
        Update the status of the well
    update_coordinates(new_coordinates: dict)
        Update the coordinates of the well
    __repr__()
        Return a string representation of the well

    """

    def __init__(
        self,
        well_id: str,
        plate_id: int,
        active_session: Session = SessionLocal(),
        create_new: bool = False,
        **kwargs: WellKwargs,
    ):
        self.well_id = well_id
        self.plate_id = plate_id
        self.active_session = active_session
        self.service = WellService(self.active_session)
        self.well_data: Optional[WellReadModel] = None

        if create_new:
            self.create_new_well(**kwargs)
        else:
            self.load_well()

    def create_new_well(self, **kwargs: WellKwargs):
        if "type_id" in kwargs:
            plate_type = self.service.fetch_well_type_characteristics(
                db_session=self.active_session,
                plate_id=self.plate_id,
                type_id=kwargs.get("type_id"),
            )
        else:
            plate_type = self.service.fetch_well_type_characteristics(
                db_session=self.active_session, plate_id=self.plate_id
            )
        new_well = WellWriteModel(
            well_id=self.well_id,
            plate_id=self.plate_id,
            base_thickness=plate_type.base_thickness,
            height=plate_type.gasket_height_mm,
            radius=plate_type.radius_mm,
            capacity=plate_type.capacity_ul,
            **kwargs,
        )
        self.well_data = WellWriteModel.model_validate(
            self.service.create_well(new_well)
        )
        self.load_well()

    def load_well(self):
        self.well_data = self.service.get_well(self.well_id, self.plate_id)

    def save(self):
        self.service.update_well(
            self.well_id, self.plate_id, self.well_data.model_dump()
        )

    def add_contents(self, from_vessel: dict, volume: float):
        if self.well_data.volume + volume > self.well_data.capacity:
            raise OverFillException(
                self.well_data.name,
                self.well_data.volume,
                volume,
                self.well_data.capacity,
            )

        for key, val in from_vessel.items():
            if key in self.well_data.contents:
                self.well_data.contents[key] += val
            else:
                self.well_data.contents[key] = val

        self.well_data.volume += volume
        self.save()

    def remove_contents(self, volume: float) -> dict:
        if self.well_data.volume - volume < 0:
            raise OverDraftException(
                self.well_data.name,
                self.well_data.volume,
                -volume,
                self.well_data.capacity,
            )

        current_content_ratios = {
            key: value / sum(self.well_data.contents.values())
            for key, value in self.well_data.contents.items()
        }
        removed_contents = {}
        for key in self.well_data.contents:
            removed_volume = round(volume * current_content_ratios[key], 6)
            self.well_data.contents[key] -= removed_volume
            removed_contents[key] = removed_volume

        self.well_data.volume -= volume
        self.save()
        return removed_contents

    def update_status(self, new_status: str):
        self.well_data.status = new_status
        self.save()

    def update_coordinates(self, new_coordinates: dict):
        self.well_data.coordinates = new_coordinates
        self.save()

    def __repr__(self):
        return f"<Well(well_id={self.well_id}, volume={self.well_data.volume}, contents={self.well_data.contents})>"


class Wellplate:
    def __init__(
        self,
        session: Session = SessionLocal(),
        type_id: Optional[int] = None,
        plate_id: Optional[int] = None,
        create_new: bool = False,
        **kwargs: WellplateKwargs,
    ):
        self.session = session
        self.service = WellplateService(self.session)
        self.plate_data: WellplateReadModel = None
        self.plate_type: PlateTypeModel = None
        self.wells: dict[str, Well] = {}

        # Check for the incoming plate_id and type_id. If the combo exists then don't create a new plate.
        # If the combo does not exist, then create a new plate but use an autoincremented plate_id
        existing_plate = self.service.get_plate(plate_id)
        if (
            existing_plate and create_new
        ):  # There is an existing plate but we want to create a new one, so we need to check if the type_id is the same
            if (existing_plate.type_id == type_id) and (existing_plate.id == plate_id):
                create_new = False
            elif (existing_plate.type_id != type_id) and (
                existing_plate.id == plate_id
            ):
                print(
                    "An existing plate with the same plate_id but different type_id was found."
                )
                print("Please provide a new plate_id or type_id.")
                new_plate_id = input(
                    "Enter a new plate_id (or enter to remain the same): "
                )
                new_type_id = input(
                    "Enter a new type_id (or enter to remain the same): "
                )
                if not new_plate_id and not new_type_id:
                    print("No changes made. Loading existing plate.")
                    create_new = False

                elif new_plate_id:
                    plate_id = int(new_plate_id)

                elif new_type_id:
                    type_id = int(new_type_id)

        if create_new:
            # If creating a new plate, must provide a plate_type_id
            # If a plate ID is not provided, it will be autoincremented
            if type_id is None and "plate_id" not in kwargs:
                raise ValueError("Must provide a plate_type_id to create a new plate.")
            self.create_new_plate(id=plate_id, type_id=type_id, **kwargs)
        else:
            # If loading an existing plate, must provide a plate_id
            if plate_id is None:
                raise ValueError("Must provide a plate_id to load an existing plate.")
            self.load_plate(plate_id)

    def create_new_plate(self, **kwargs: WellplateKwargs):
        # If there is a currently active wellplate, fetch its characteristics
        active_plate = self.service.get_active_plate()
        if active_plate:
            kwargs["a1_x"] = active_plate.a1_x
            kwargs["a1_y"] = active_plate.a1_y
            kwargs["orientation"] = active_plate.orientation
            kwargs["echem_height"] = active_plate.echem_height
            kwargs["image_height"] = active_plate.image_height
            kwargs["coordinates"] = active_plate.coordinates
        # First create the wellplate
        kwargs["name"] = f"{kwargs.get('id', 'default')}"
        self.plate_type = self.service.get_plate_type(kwargs.get("type_id"))
        for key, value in self.plate_type.model_dump().items():
            if key == "id":
                continue
            if key == "gasket_height_mm":
                key = "height"
            if key == "radius_mm":
                key = "radius"
            if key == "capacity_ul":
                key = "capacity"
            if key not in kwargs:
                kwargs[key] = value

        new_plate = WellplateWriteModel(**kwargs)

        self.plate_data = WellplateWriteModel.model_validate(
            self.service.create_plate(new_plate)
        )
        # Second create the wells
        self.wells = self._create_wells_from_type()

        self.load_plate(self.plate_data.id)

    def load_plate(self, plate_id: int):
        self.plate_data = self.service.get_plate(plate_id)
        self.plate_type = self.service.get_plate_type(self.plate_data.type_id)
        self.load_wells()

    def load_wells(self):
        wells_data = self.service.get_wells(self.plate_data.id)
        self.wells = {
            well_data.well_id: Well(
                plate_id=self.plate_data.id,  # TODO: could add assuming the current plate ID
                well_id=well_data.well_id,
                active_session=self.session,
            )
            for well_data in wells_data
        }

    def save(self):
        self.service.update_plate(self.plate_data.id, self.plate_data.model_dump())

    def _create_wells_from_type(self):
        """Create wells based on the type of wellplate."""
        wells: dict[str:Well] = {}
        rows: list = list(self.plate_data.rows)
        cols: range = range(1, int(self.plate_data.cols) + 1)

        for row in rows:
            for col in cols:
                coordinates = self.calculate_well_coordinates(row, col)
                wells[str(row) + str(col)] = Well(
                    create_new=True,
                    active_session=self.session,
                    plate_id=self.plate_data.id,
                    well_id=f"{row}{col}",
                    experiment_id=0,
                    project_id=0,
                    status="new",
                    contents={},
                    volume=0.0,
                    coordinates=coordinates,
                    contamination=0,
                    dead_volume=0.0,
                    name=f"{self.plate_data.id}_{row}{col}",
                )
        return wells

    def update_coordinates(self, new_coordinates: dict):
        self.plate_data.coordinates = new_coordinates
        self.plate_data.a1_x = new_coordinates["x"]
        self.plate_data.a1_y = new_coordinates["y"]
        # self.recalculate_well_positions()

    def recalculate_well_positions(self):
        for well_id, well in self.wells.items():
            row, col = well_id[0], int(well_id[1:])
            well.update_coordinates(self.calculate_well_coordinates(row, col))

    def calculate_well_coordinates(self, row: str, col: int) -> dict:
        x = (col - 1) * self.plate_type.x_spacing
        y = (ord(row.upper()) - ord("A")) * self.plate_type.y_spacing
        x, y = self.__calculate_rotated_position(
            x,
            y,
            self.plate_data.orientation,
            self.plate_data.a1_x,
            self.plate_data.a1_y,
        )
        return {"x": x, "y": y, "z": self.plate_data.coordinates["z"]}

    def __calculate_rotated_position(
        self, x: float, y: float, orientation: int, a1_x: float, a1_y: float
    ) -> tuple:
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

    def activate_plate(self):
        self.plate_data = self.service.activate_plate(self.plate_data.id)

    def deactivate_plate(self, new_active_plate_id: int = None):
        self.plate_data = self.service.deactivate_plate(
            self.plate_data.id, new_active_plate_id
        )

    def __repr__(self):
        return f"<WellPlate(id={self.plate_data.id}, type_id={self.plate_data.type_id}, wells={len(self.wells)})>"


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
            session.execute(select(MillConfig).order_by(MillConfig.id.desc()))
            .scalar()
            .config
        )
        working_volume = {
            "x": float(mill_config["$130"]),
            "y": float(mill_config["$131"]),
            "z": float(mill_config["$132"]),
        }

        ## Get the current plate id and location
        statement = select(Wellplates).filter_by(current=1)

        result: Wellplates = session.execute(statement).first()
        current_plate_id = result.id
        current_type_number = result.type_id

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
            new_location_x = wellplate.plate_data.a1_x
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
            new_location_y = wellplate.plate_data.a1_y
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

    wellplate.plate_data.a1_x = new_location_x
    wellplate.plate_data.a1_y = new_location_y
    wellplate.plate_data.orientation = new_orientation
    wellplate.plate_data.coordinates = {
        "x": new_location_x,
        "y": new_location_y,
        "z": wellplate.plate_data.coordinates["z"],
    }
    wellplate.recalculate_well_positions()
    wellplate.save()


def read_current_wellplate_info(
    session: Session = SessionLocal,
) -> Tuple[int, int, int]:
    """
    Read the current wellplate

    Returns:
        int: The current wellplate id
        int: The current wellplate type number
        int: Number of new wells
    """

    with SessionLocal() as session:
        statement = select(Wellplates).filter_by(current=1)

        result: Wellplates = session.execute(statement).scalar_one_or_none()
        current_plate_id = result.id
        current_type_number = result.type_id

        new_wells = (
            session.query(WellModel)
            .filter(WellModel.status == "new")
            .filter(WellModel.plate_id == current_plate_id)
            .count()
        )

    return int(current_plate_id), int(current_type_number), new_wells


if __name__ == "__main__":
    # Lets add a wellplate to the database
    pass
