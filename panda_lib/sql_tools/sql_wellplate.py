"""SQL Functions for the wellplates and well_hx tables."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Tuple, Union

from sqlalchemy import Integer, cast, func, select

from panda_lib import wellplate as wellplate_module
from panda_lib.sql_tools import sql_reports
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import PlateTypes, WellModel, Wellplates

logger = sql_reports.logger


# region Wellplate Functions
def check_if_wellplate_exists(plate_id: int) -> bool:
    """Check if a wellplate exists in the wellplates table"""

    with SessionLocal() as session:
        return (
            session.execute(
                select(Wellplates).filter(Wellplates.id == plate_id)
            ).scalar()
            is not None
        )


def check_if_plate_type_exists(type_id: int) -> bool:
    """Check if a plate type exists in the plate_types table"""

    with SessionLocal() as session:
        return (
            session.execute(
                select(PlateTypes).filter(PlateTypes.id == type_id)
            ).scalar()
            is not None
        )


def select_wellplate_location(
    plate_id: Union[int, None] = None,
) -> Tuple[float, float, float, float, int, float, float]:
    """Select the location and characteristics of the wellplate from the wellplate
     table. If no plate_id is given, the current wellplate is assumed

    Args:
        plate_id (int): The plate ID.

    Returns:
        x (float): The x coordinate of A1.
        y (float): The y coordinate of A1.
        z_bottom (float): The z coordinate of the bottom of the wellplate.
        z_top (float): The z coordinate of the top of the wellplate.
        orientation (int): The orientation of the wellplate.
        echem_height(float): The height of performing electrochemistry in a well.
        image_height(float): The height of the image taken of the wellplate.

    """

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = session.execute(
                select(Wellplates.id).filter(Wellplates.current == 1)
            ).scalar()
        wellplate: Wellplates = session.execute(
            select(Wellplates).filter(Wellplates.id == plate_id)
        ).scalar_one_or_none()
        if wellplate is None:
            return None
        return (
            wellplate.a1_x,
            wellplate.a1_y,
            wellplate.bottom,
            wellplate.top,
            wellplate.orientation,
            wellplate.echem_height,
            wellplate.image_height,
        )


def update_wellplate_location(plate_id: Union[int, None], **kwargs) -> None:
    """Update the location and characteristics of the wellplate in the wellplates table"""
    with SessionLocal() as session:
        if plate_id is None:
            logger.info("No plate_id provided, updating the current wellplate")
            plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )

        wellplate = session.query(Wellplates).filter(Wellplates.id == plate_id).first()
        if wellplate is None:
            raise ValueError(f"Wellplate {plate_id} does not exist")
        for key, value in kwargs.items():
            if hasattr(wellplate, key):
                setattr(wellplate, key, value)
            else:
                raise ValueError(f"Invalid characteristic: {key}")
        session.commit()


def update_current_wellplate(new_plate_id: int) -> None:
    """Changes the current wellplate's current value to 0 and sets the new
    wellplate's current value to 1"""

    with SessionLocal() as session:
        session.query(Wellplates).filter(Wellplates.current == 1).update(
            {Wellplates.current: 0}
        )
        session.query(Wellplates).filter(Wellplates.id == new_plate_id).update(
            {Wellplates.current: 1}
        )
        session.commit()


def add_wellplate_to_table(plate_id: int, type_id: int) -> None:
    """Add a new wellplate to the wellplates table"""

    with SessionLocal() as session:
        # Fetch the information about the type of wellplate
        well_type = session.query(PlateTypes).filter(PlateTypes.id == type_id).first()

        session.add(
            Wellplates(
                id=plate_id,
                type_id=type_id,
                current=0,
                cols=well_type.cols,
                rows=well_type.rows,
                a1_x=0,
                a1_y=0,
                z_bottom=0,
                z_top=0,
                orientation=0,
                echem_height=0,
                image_height=0,
            )
        )
        session.commit()


def check_if_current_wellplate_is_new() -> bool:
    """Check if the current wellplate is new"""

    with SessionLocal() as session:
        current_plate_id = session.execute(
            select(Wellplates.id).filter(Wellplates.current == 1)
        ).scalar_one_or_none()

        if current_plate_id is None:
            logger.info("No current wellplate found")
            return False

        result = session.execute(
            select(WellModel.status).filter(WellModel.plate_id == current_plate_id)
        ).all()

        if not result:
            return False

        for row in result:
            if row[0] != "new":
                return False
        return True


def get_number_of_wells(plate_id: Union[int, None] = None) -> int:
    """
    Get the number of wells in the well_hx table for the given or current wellplate.

    Args:
        plate_id (int): The plate ID.

    Returns:
        int: The number of wells.
    """

    with SessionLocal() as session:
        if plate_id is None:
            result = (
                session.query(WellModel)
                .filter(
                    WellModel.plate_id
                    == session.query(Wellplates.id)
                    .filter(Wellplates.current == 1)
                    .scalar_subquery()
                )
                .count()
            )
        else:
            result = (
                session.query(WellModel).filter(WellModel.plate_id == plate_id).count()
            )
        return result


def get_number_of_clear_wells(plate_id: Union[int, None] = None) -> int:
    """
    Query the well_hx table and count the number of wells with status in
    'new', 'clear','queued' for the current wellplate.

    If plate_id is provided, count the wells of the specified wellplate in
    well_hx instead of the current wellplate.

    Args:
        plate_id (int): The plate ID.

    Returns:
        int: The number of wells with status in 'new', 'clear','queued'.
    """

    with SessionLocal() as session:
        if plate_id is None:
            result = (
                session.query(WellModel)
                .filter(
                    WellModel.plate_id
                    == session.query(Wellplates.id)
                    .filter(Wellplates.current == 1)
                    .scalar_subquery()
                )
                .filter(WellModel.status.in_(["new", "clear", "queued"]))
                .count()
            )
        else:
            result = (
                session.query(WellModel)
                .filter(WellModel.plate_id == plate_id)
                .filter(WellModel.status.in_(["new", "clear", "queued"]))
                .count()
            )
        return result


def select_current_wellplate_info() -> tuple[int, int, bool]:
    """
    Get the current wellplate information from the wellplates table.

    Returns:
        tuple[int, int, bool]: The wellplate ID, the wellplate type ID, and
        whether the wellplate is new.
    """

    with SessionLocal() as session:
        statement = select(Wellplates).filter_by(Wellplates.current == 1)

        result: Wellplates = session.execute(statement).first()
        current_plate_id = result.id
        current_type_number = result.type_id
        is_new = check_if_current_wellplate_is_new()

    return current_plate_id, current_type_number, is_new


def select_wellplate_info(plate_id: int) -> Wellplates:
    """
    Get the wellplate information from the wellplates table.

    Args:
        plate_id (int): The plate ID.

    Returns:
        tuple[int, int]: The wellplate ID and the wellplate type ID.
    """

    with SessionLocal() as session:
        result = session.query(Wellplates).filter(Wellplates.id == plate_id).first()
        return result


def select_well_ids(plate_id: Union[int, None] = None) -> List[str]:
    """
    Get the well IDs from the well_hx table for the given or current wellplate.

    Args:
        plate_id (int): The plate ID.

    Returns:
        List[str]: The well IDs.
    """

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )
        result = (
            session.query(WellModel.well_id)
            .filter(WellModel.plate_id == plate_id)
            .order_by(WellModel.well_id.asc())
            .all()
        )
        return [row[0] for row in result]


def select_wellplate_wells(plate_id: Union[int, None] = None) -> List[object]:
    """
    Selects all wells from the well_hx table for a specific wellplate.
    Or if no plate_id is provided, all wells of the current wellplate are
    selected.
    """

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )
        result = (
            session.query(
                WellModel.plate_id,
                Wellplates.type_id,
                WellModel.well_id,
                WellModel.status,
                WellModel.status_date,
                WellModel.contents,
                WellModel.experiment_id,
                WellModel.project_id,
                WellModel.volume,
                WellModel.coordinates,
                PlateTypes.capacity_ul,
                PlateTypes.gasket_height_mm,
            )
            .join(Wellplates, WellModel.plate_id == Wellplates.id)
            .join(PlateTypes, Wellplates.type_id == PlateTypes.id)
            .filter(WellModel.plate_id == plate_id)
            .order_by(WellModel.well_id.asc())
            .all()
        )
        if result == []:
            return None

        wells = []
        for row in result:
            try:
                if isinstance(row[5], str):
                    incoming_contents = json.loads(row[5])
                else:
                    incoming_contents = row[5]
            except json.JSONDecodeError:
                incoming_contents = {}
            except TypeError:
                incoming_contents = {}

            try:
                if isinstance(row[9], str):
                    incoming_coordinates = json.loads(row[9])
                else:
                    incoming_coordinates = row[9]
            except json.JSONDecodeError:
                incoming_coordinates = (0, 0)

            well_type_number = int(row[1]) if row[1] else 0
            volume = int(row[8]) if row[8] else 0
            capacity = int(row[10]) if row[10] else 0
            height = int(row[11]) if row[11] else 0
            experiment_id = int(row[6]) if row[6] else None
            project_id = int(row[7]) if row[7] else None

            wells.append(
                wellplate_module.Well(
                    well_id=str(row[2]),
                    well_type_number=well_type_number,
                    status=str(row[3]),
                    status_date=str(row[4]),
                    contents=incoming_contents,
                    experiment_id=experiment_id,
                    project_id=project_id,
                    volume=volume,
                    coordinates=incoming_coordinates,
                    capacity=capacity,
                    height=height,
                    plate_id=int(plate_id),
                )
            )
        return wells


def select_well_status(well_id: str, plate_id: Union[int, None] = None) -> str:
    """
    Get the status of a well from the well_hx table.

    Args:
        well_id (str): The well ID.

    Returns:
        str: The status of the well.
    """
    # if plate_id is None:
    #     plate_id = sql_utilities.execute_sql_command(
    #         "SELECT id FROM wellplates WHERE current = 1"
    #     )[0][0]
    # result = sql_utilities.execute_sql_command(
    #     "SELECT status FROM well_status WHERE well_id = ? AND plate_id = ?",
    #     (
    #         well_id,
    #         plate_id,
    #     ),
    # )
    # return result[0][0]

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )
        result = (
            session.query(WellModel.status)
            .filter(WellModel.plate_id == plate_id)
            .filter(WellModel.well_id == well_id)
            .first()
        )
        return result[0]


def count_wells_with_new_status(plate_id: Union[int, None] = None) -> int:
    """
    Count the number of wells with a status of 'new' in the well_hx table.

    Returns:
        int: The number of wells with a status of 'new'.
    """
    # if plate_id is not None:
    #     result = sql_utilities.execute_sql_command(
    #         """
    #         SELECT COUNT(*) FROM well_hx
    #         WHERE status = 'new'
    #         AND plate_id = ?
    #         """,
    #         (plate_id,),
    #     )
    # else:
    #     result = sql_utilities.execute_sql_command(
    #         """
    #         SELECT COUNT(*) FROM well_status
    #         WHERE status = 'new'
    #         """
    #     )

    # return int(result[0][0])

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )

        result = (
            session.query(WellModel)
            .filter(WellModel.status == "new")
            .filter(WellModel.plate_id == plate_id)
            .count()
        )
        return result


def select_next_available_well(plate_id: Union[int, None] = None) -> str:
    """
    Choose the next available well in the well_hx table.

    Returns:
        str: The well ID of the next available well.
    """
    # if plate_id is None:
    #     plate_id = sql_utilities.execute_sql_command(
    #         "SELECT id FROM wellplates WHERE current = 1"
    #     )[0][0]

    # result = sql_utilities.execute_sql_command(
    #     """
    #     SELECT well_id FROM well_hx
    #     WHERE status = 'new'
    #     AND plate_id = ?
    #     ORDER BY SUBSTR(well_id, 1, 1),
    #           CAST(SUBSTR(well_id, 2) AS UNSIGNED) ASC
    #     LIMIT 1
    #     """,
    #     (plate_id,),
    # )

    # if result == []:
    #     return None
    # return result[0][0]

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )
        result = (
            session.query(WellModel.well_id)
            .filter(WellModel.status == "new")
            .filter(WellModel.plate_id == plate_id)
            .order_by(
                func.substr(WellModel.well_id, 1, 1),
                cast(func.substr(WellModel.well_id, 2), Integer).asc(),
            )
            .first()
        )
        if result is None:
            return None
        return result[0]


# endregion


# region Well Functions
def save_well_to_db(well_to_save: object) -> None:
    """
    First check if the well is in the table. If so update the well where the
        values are different.
    Otherwise insert the well into the table.
    """

    with SessionLocal() as session:
        if well_to_save.plate_id in [None, 0]:
            well_to_save.plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )

        # Leaving this commented if we want to change how the table is structured.
        # Currently the table is unique on plate_id and well_id, but we could in the future
        # Allow for multiple entries with the same well_id and plate_id but different status
        # Then use a view to get the most recent status for each well_id and plate_id
        # session.add(WellHx(
        #     plate_id=well_to_save.plate_id,
        #     well_id=well_to_save.well_id,
        #     experiment_id=well_to_save.experiment_id,
        #     project_id=well_to_save.project_id,
        #     status=well_to_save.status,
        #     status_date=datetime.strptime(well_to_save.status_date,'%Y-%m-%dT%H:%M:%S'),
        #     contents=well_to_save.contents,
        #     volume=well_to_save.volume,
        #     coordinates=well_to_save.coordinates.__dict__
        # ))

        # Instead we will update the status of the well if it already exists
        session.query(WellModel).filter(
            WellModel.plate_id == well_to_save.plate_id
        ).filter(WellModel.well_id == well_to_save.well_id).update(
            {
                WellModel.experiment_id: well_to_save.experiment_id,
                WellModel.project_id: well_to_save.project_id,
                WellModel.status: well_to_save.status,
                WellModel.status_date: datetime.now(tz=timezone.utc).isoformat(),
                WellModel.contents: json.dumps(well_to_save.contents),
                WellModel.volume: well_to_save.volume,
                WellModel.coordinates: json.dumps(asdict(well_to_save.coordinates)),
            }
        )
        session.commit()


def save_wells_to_db(wells_to_save: List[object]) -> None:
    """
    First check if the well is in the table. If so update the well where the
        values are different.
    Otherwise insert the well into the table.
    """

    with SessionLocal() as session:
        for well in wells_to_save:
            if well.plate_id in [None, 0]:
                well.plate_id = (
                    session.query(Wellplates).filter(Wellplates.current == 1).first().id
                )

            session.add(
                WellModel(
                    plate_id=well.plate_id,
                    well_id=well.well_id,
                    experiment_id=well.experiment_id,
                    project_id=well.project_id,
                    status=well.status,
                    contents=json.dumps(well.contents),
                    volume=well.volume,
                    coordinates=json.dumps(asdict(well.coordinates)),
                )
            )
        session.commit()


def insert_well(well_to_insert: object) -> None:
    """
    Insert a well into the well_hx table.

    Insert_well will accept a well object, and using its attributes, insert a new
    row into the well_hx table.

    Args:
        well_to_insert (Well): The well to insert.

    Returns:
        None
    """

    with SessionLocal() as session:
        session.add(WellModel(**well_to_insert.__dict__))
        session.commit()


def update_well(well_to_update: object) -> None:
    """
    Updating the entry in the well_hx table that matches the well and plate ids.

    Args:
        well_to_update (Well): The well to update.

    Returns:
        None
    """

    with SessionLocal() as session:
        session.query(WellModel).filter(
            WellModel.plate_id == well_to_update.plate_id
        ).filter(WellModel.well_id == well_to_update.well_id).update(
            {
                WellModel.experiment_id: well_to_update.experiment_id,
                WellModel.project_id: well_to_update.project_id,
                WellModel.status: well_to_update.status,
                WellModel.status_date: datetime.now().isoformat(timespec="seconds"),
                WellModel.contents: json.dumps(well_to_update.contents),
                WellModel.volume: well_to_update.volume,
                WellModel.coordinates: json.dumps(asdict(well_to_update.coordinates)),
            }
        )
        session.commit()


def get_well_by_id(
    well_id: str,
    plate_id: Union[int, None] = None,
) -> object:
    """
    Get a well from the well_hx table.

    Args:
        plate_id (int): The plate ID.
        well_id (str): The well ID.

    Returns:
        Well: The well.
    """

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )
        result = (
            session.query(WellModel)
            .filter(WellModel.plate_id == plate_id)
            .filter(WellModel.well_id == well_id)
            .all()
        )
        if result == []:
            return None

        # Convert coordinates to a WellCoordinates object
        result[0].coordinates = wellplate_module.WellCoordinates(
            **json.loads(result[0].coordinates)
        )
        return result[0]


def get_well_by_experiment_id(experiment_id: str) -> Tuple:
    """
    Get a well from the well_hx table by experiment ID.

    Args:
        experiment_id (str): The experiment ID.

    Returns:
        Well: The well.
    """

    with SessionLocal() as session:
        result = (
            session.query(WellModel)
            .filter(WellModel.experiment_id == experiment_id)
            .all()
        )
        if result == []:
            return None
        return result[0]


def select_well_characteristics(type_id: int) -> PlateTypes:
    """
    Select the well characteristics from the well_types table.

    Args:
        type_id (int): The well type ID.

    Returns:
        The SQL Alchemy object for the well type.
    """

    with SessionLocal() as session:
        result = session.query(PlateTypes).filter(PlateTypes.id == type_id).first()
        return result


def update_well_coordinates(
    well_id: str, plate_id: Union[int, None], coordinates: object
) -> None:
    """
    Update the coordinates of an individal well in the well_hx table.

    Args:
        well_id (str): The well ID.
        plate_id (int): The plate ID.
        coordinates (WellCoordinates): The coordinates.
    """

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )
        session.query(WellModel).filter(WellModel.plate_id == plate_id).filter(
            WellModel.well_id == well_id
        ).update({WellModel.coordinates: json.dumps(asdict(coordinates))})
        session.commit()


def update_well_status(
    well_id: str, plate_id: Union[None, int] = None, status: Union[None, str] = None
) -> None:
    """
    Update the status of a well in the well_hx table.

    Args:
        well_id (str): The well ID.
        plate_id (int): The plate ID.
        status (str): The status.
    """

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(Wellplates).filter(Wellplates.current == 1).first().id
            )
        if status is None:
            status = select_well_status(well_id, plate_id)
        session.query(WellModel).filter(WellModel.plate_id == plate_id).filter(
            WellModel.well_id == well_id
        ).update(
            {
                WellModel.status: status,
                WellModel.status_date: datetime.now().isoformat(timespec="seconds"),
            }
        )
        session.commit()


# endregion
