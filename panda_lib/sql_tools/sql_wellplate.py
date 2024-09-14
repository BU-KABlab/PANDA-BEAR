"""SQL Functions for the wellplates and well_hx tables."""

import json
from dataclasses import asdict
from datetime import datetime
from typing import List, Tuple, Union

from sqlalchemy import DateTime, Integer, func, cast

from panda_lib import wellplate as wellplate_module
from panda_lib.sql_tools import sql_utilities
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import WellHx, WellPlates, WellTypes

logger = sql_utilities.logger


# region Wellplate Functions
def check_if_wellplate_exists(plate_id: int) -> bool:
    """Check if a wellplate exists in the wellplates table"""
    # result = sql_utilities.execute_sql_command(
    #     """
    #     SELECT * FROM wellplates
    #     WHERE id = ?
    #     """,
    #     (plate_id,),
    # )
    # return result != []

    with SessionLocal() as session:
        return session.query(WellPlates).filter(WellPlates.id == plate_id).count() > 0


def select_wellplate_location(plate_id: Union[int, None] = None) -> Tuple[float, float, float, float, int, float, float]:
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

    """

    # if plate_id is None:
    #     plate_id = sql_utilities.execute_sql_command(
    #         "SELECT id FROM wellplates WHERE current = 1"
    #     )[0][0]

    # result = sql_utilities.execute_sql_command(
    #     """
    #     SELECT
    #         a1_x,
    #         a1_y,
    #         z_bottom,
    #         z_top,
    #         orientation,
    #         rows,
    #         cols,
    #         echem_height
    #     FROM wellplates
    #     WHERE id = ?
    #     """,
    #     (plate_id,),
    # )
    # if result == []:
    #     return None

    # # Validate the types of the results
    # x = float(result[0][0])
    # y = float(result[0][1])
    # z_bottom = float(result[0][2])
    # z_top = float(result[0][3])
    # orientation = int(result[0][4])
    # rows = int(result[0][5])
    # cols = result[0][6]
    # echem_height = float(result[0][7])
    # return x, y, z_bottom,z_top, orientation, rows, cols, echem_height

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )
        wellplate = session.query(WellPlates).filter(WellPlates.id == plate_id).first()
        if wellplate is None:
            return None
        return (
            wellplate.a1_x,
            wellplate.a1_y,
            wellplate.z_bottom,
            wellplate.z_top,
            wellplate.orientation,
            wellplate.echem_height,
            wellplate.image_height
        )


def update_wellplate_location(plate_id: Union[int,None], **kwargs) -> None:
    """Update the location and characteristics of the wellplate in the wellplates table"""
    with SessionLocal() as session:

        if plate_id is None:
            logger.info("No plate_id provided, updating the current wellplate")
            plate_id = (
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )

        wellplate = session.query(WellPlates).filter(WellPlates.id == plate_id).first()
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
    # sql_utilities.execute_sql_command_no_return(
    #     """
    #     UPDATE wellplates SET current = 0
    #     WHERE current = 1
    #     """
    # )
    # sql_utilities.execute_sql_command_no_return(
    #     """
    #     UPDATE wellplates SET current = 1
    #     WHERE id = ?
    #     """,
    #     (new_plate_id,),
    # )

    with SessionLocal() as session:
        session.query(WellPlates).filter(WellPlates.current == 1).update(
            {WellPlates.current: 0}
        )
        session.query(WellPlates).filter(WellPlates.id == new_plate_id).update(
            {WellPlates.current: 1}
        )
        session.commit()


def add_wellplate_to_table(plate_id: int, type_id: int) -> None:
    """Add a new wellplate to the wellplates table"""
    # sql_utilities.execute_sql_command_no_return(
    #     """
    #     INSERT INTO wellplates (id, type_id, current)
    #     VALUES (?, ?, 0)
    #     """,
    #     (plate_id, type_id),
    # )

    with SessionLocal() as session:

        # Fetch the information about the type of wellplate
        well_type = session.query(WellTypes).filter(WellTypes.id == type_id).first()

        session.add(
            WellPlates(
                id=plate_id,
                type_id=type_id,
                current=0,
                cols = well_type.cols,
                rows = well_type.rows,
                a1_x = 0,
                a1_y = 0,
                z_bottom = 0,
                z_top = 0,
                orientation = 0,
                echem_height = 0
            )
            )
        session.commit()


def check_if_current_wellplate_is_new() -> bool:
    """Check if the current wellplate is new"""
    # result = sql_utilities.execute_sql_command(
    #     """
    #     SELECT status FROM well_hx
    #     WHERE plate_id = (SELECT id FROM wellplates WHERE current = 1)
    #     """
    # )
    # if result == []:
    #     logger.info("No current wellplate found")
    #     return False

    # # If all the results are 'new' then the wellplate is new
    # for row in result:
    #     if row[0] != "new":
    #         return False
    # return True

    with SessionLocal() as session:
        result = (
            session.query(WellHx.status)
            .filter(
            WellHx.plate_id
            == session.query(WellPlates.id).filter(WellPlates.current == 1).scalar_subquery()
            )
            .all()
        )
        if result == []:
            logger.info("No current wellplate found")
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
    # if plate_id is None:
    #     result = sql_utilities.execute_sql_command(
    #         """
    #         SELECT COUNT(*) FROM well_hx
    #         WHERE plate_id = (SELECT id FROM wellplates WHERE current = 1)
    #         """
    #     )
    # else:
    #     result = sql_utilities.execute_sql_command(
    #         """
    #         SELECT COUNT(*) FROM well_hx
    #         WHERE plate_id = ?
    #         """,
    #         (plate_id,),
    #     )
    # return int(result[0][0])

    with SessionLocal() as session:
        if plate_id is None:
            result = (
                session.query(WellHx)
                .filter(
                    WellHx.plate_id
                    == session.query(WellPlates.id).filter(WellPlates.current == 1).scalar_subquery()
                )
                .count()
            )
        else:
            result = session.query(WellHx).filter(WellHx.plate_id == plate_id).count()
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
    # if plate_id is None:
    #     result = sql_utilities.execute_sql_command(
    #         """
    #         SELECT COUNT(*) FROM well_hx
    #         WHERE status IN ('new', 'clear','queued')
    #         AND plate_id = (SELECT id FROM wellplates WHERE current = 1)
    #         """
    #     )
    # else:
    #     result = sql_utilities.execute_sql_command(
    #         """
    #         SELECT COUNT(*) FROM well_hx
    #         WHERE status IN ('new', 'clear','queued')
    #         AND plate_id = ?
    #         """,
    #         (plate_id,),
    #     )
    # return int(result[0][0])

    with SessionLocal() as session:
        if plate_id is None:
            result = (
                session.query(WellHx)
                .filter(
                    WellHx.plate_id
                    == session.query(WellPlates.id).filter(WellPlates.current == 1).scalar_subquery()
                )
                .filter(WellHx.status.in_(["new", "clear", "queued"]))
                .count()
            )
        else:
            result = (
                session.query(WellHx)
                .filter(WellHx.plate_id == plate_id)
                .filter(WellHx.status.in_(["new", "clear", "queued"]))
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
    # result = sql_utilities.execute_sql_command(
    #     """
    #     SELECT id, type_id FROM wellplates
    #     WHERE current = 1
    #     """
    # )
    # if result == []:
    #     return 0, 0, False
    # is_new = check_if_current_wellplate_is_new()
    # return result[0][0], result[0][1], is_new

    with SessionLocal() as session:
        result = session.query(WellPlates).filter(WellPlates.current == 1).first()
        if result is None:
            return 0, 0, False
        is_new = check_if_current_wellplate_is_new()
        return result.id, result.type_id, is_new


def select_wellplate_wells(plate_id: Union[int, None] = None) -> List[object]:
    """
    Selects all wells from the well_hx table for a specific wellplate.
    Or if no plate_id is provided, all wells of the current wellplate are
    selected.

    The table has columns:
    plate_id,
    type_number,
    well_id,
    status,
    status_date,
    contents,
    experiment_id,
    project_id,
    volume,
    coordinates
    """
    # if plate_id is None:
    #     result = sql_utilities.execute_sql_command(
    #         """
    #         SELECT
    #             plate_id,
    #             type_number,
    #             well_id,
    #             status,
    #             status_date,
    #             contents,
    #             experiment_id,
    #             project_id,
    #             volume,
    #             coordinates,
    #             capacity,
    #             height

    #         FROM well_status
    #         ORDER BY well_id ASC
    #         """
    #     )
    # else:
    #     result = sql_utilities.execute_sql_command(
    #         """
    #     SELECT
    #         a.plate_id,
    #         b.type_id as type_number,
    #         a.well_id,
    #         a.status,
    #         a.status_date,
    #         a.contents,
    #         a.experiment_id,
    #         a.project_id,
    #         a.volume,
    #         a.coordinates,
    #         c.capacity_ul as capacity,
    #         c.height_mm as height
    #     FROM well_hx as a
    #     JOIN wellplates as b
    #     ON a.plate_id = b.id
    #     JOIN well_types as c
    #     ON b.type_id = c.id
    #     WHERE a.plate_id = ?
    #         """,
    #         (plate_id,),
    #     )
    # if result == []:
    #     return None

    # current_plate_id = select_current_wellplate_info()[0]
    # wells = []
    # for row in result:
    #     try:
    #         incoming_contents = json.loads(row[5])
    #     except json.JSONDecodeError:
    #         incoming_contents = {}
    #     except TypeError:
    #         incoming_contents = {}

    #     try:
    #         incoming_coordinates = json.loads(row[9])
    #         # incoming_coordinates = wellplate.WellCoordinates(**incoming_coordinates)
    #     except json.JSONDecodeError:
    #         incoming_coordinates = (0, 0)

    #     # Convert NULL or blank cells to 0 for integer fields
    #     well_type_number = int(row[1]) if row[1] else 0
    #     volume = int(row[8]) if row[8] else 0
    #     capacity = int(row[10]) if row[10] else 0
    #     height = int(row[11]) if row[11] else 0
    #     experiment_id = int(row[6]) if row[6] else None
    #     project_id = int(row[7]) if row[7] else None
    #     # well_height, well_capacity,
    #     # TODO currently the wepplate object applies the well_height and well_capacity
    #     # If we want the wells to be the primary source of this information, we need to
    #     # update this script to also pull from well_types and the stop applying
    #     # the infomation in the wellplate object
    #     if plate_id is None:
    #         plate_id = row[0]
    #         if plate_id is None:
    #             plate_id = current_plate_id

    #     wells.append(
    #         wellplate.Well(
    #             well_id=str(row[2]),
    #             well_type_number=well_type_number,
    #             status=str(row[3]),
    #             status_date=str(row[4]),
    #             contents=incoming_contents,
    #             experiment_id=experiment_id,
    #             project_id=project_id,
    #             volume=volume,
    #             coordinates=incoming_coordinates,
    #             capacity=capacity,
    #             height=height,
    #             plate_id=int(plate_id),
    #         )
    #     )
    # return wells

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )
        result = (
            session.query(
                WellHx.plate_id,
                WellPlates.type_id,
                WellHx.well_id,
                WellHx.status,
                WellHx.status_date,
                WellHx.contents,
                WellHx.experiment_id,
                WellHx.project_id,
                WellHx.volume,
                WellHx.coordinates,
                WellTypes.capacity_ul,
                WellTypes.gasket_height_mm,
            )
            .join(WellPlates, WellHx.plate_id == WellPlates.id)
            .join(WellTypes, WellPlates.type_id == WellTypes.id)
            .filter(WellHx.plate_id == plate_id)
            .order_by(WellHx.well_id.asc())
            .all()
        )
        if result == []:
            return None

        wells = []
        for row in result:
            try:
                if isinstance(row[5],str):
                    incoming_contents = json.loads(row[5])
                else:
                    incoming_contents = row[5]
            except json.JSONDecodeError:
                incoming_contents = {}
            except TypeError:
                incoming_contents = {}

            try:
                if isinstance(row[9],str):
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
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )
        result = (
            session.query(WellHx.status)
            .filter(WellHx.plate_id == plate_id)
            .filter(WellHx.well_id == well_id)
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
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )

        result = (
            session.query(WellHx)
            .filter(WellHx.status == "new")
            .filter(WellHx.plate_id == plate_id)
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
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )
        result = (
            session.query(WellHx.well_id)
            .filter(WellHx.status == "new")
            .filter(WellHx.plate_id == plate_id)
            .order_by(func.substr(WellHx.well_id, 1, 1), cast(func.substr(WellHx.well_id, 2), Integer).asc())
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
    # statement = """
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
    # if well_to_save.plate_id in [None, 0]:
    #     well_to_save.plate_id = sql_utilities.execute_sql_command(
    #         "SELECT id FROM wellplates WHERE current = 1"
    #     )[0][0]

    # values = (
    #     well_to_save.plate_id,
    #     well_to_save.well_id,
    #     well_to_save.experiment_id,
    #     well_to_save.project_id,
    #     well_to_save.status,
    #     well_to_save.status_date,
    #     json.dumps(well_to_save.contents),
    #     well_to_save.volume,
    #     json.dumps(asdict(well_to_save.coordinates)),
    # )
    # sql_utilities.execute_sql_command_no_return(statement, values)

    with SessionLocal() as session:
        if well_to_save.plate_id in [None, 0]:
            well_to_save.plate_id = (
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
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
        session.query(WellHx).filter(WellHx.plate_id == well_to_save.plate_id).filter(
            WellHx.well_id == well_to_save.well_id
        ).update(
            {
                WellHx.experiment_id: well_to_save.experiment_id,
                WellHx.project_id: well_to_save.project_id,
                WellHx.status: well_to_save.status,
                WellHx.status_date: datetime.strptime(well_to_save.status_date,'%Y-%m-%dT%H:%M:%S'),
                WellHx.contents: json.dumps(well_to_save.contents),
                WellHx.volume: well_to_save.volume,
                WellHx.coordinates: json.dumps(asdict(well_to_save.coordinates)),
            }
        )
        session.commit()


def save_wells_to_db(wells_to_save: List[object]) -> None:
    """
    First check if the well is in the table. If so update the well where the
        values are different.
    Otherwise insert the well into the table.
    """
    # statement = """
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
    # values = []
    # for well in wells_to_save:
    #     if well.plate_id in [None, 0]:
    #         well.plate_id = sql_utilities.execute_sql_command(
    #             "SELECT id FROM wellplates WHERE current = 1"
    #         )[0][0]

    #     values.append(
    #         (
    #             well.plate_id,
    #             well.well_id,
    #             well.experiment_id,
    #             well.project_id,
    #             well.status,
    #             datetime.now().isoformat(timespec="seconds"),
    #             json.dumps(well.contents),
    #             well.volume,
    #             json.dumps(asdict(well.coordinates)),
    #         )
    #     )
    # sql_utilities.execute_sql_command_no_return(statement, values)

    with SessionLocal() as session:
        for well in wells_to_save:
            if well.plate_id in [None, 0]:
                well.plate_id = (
                    session.query(WellPlates).filter(WellPlates.current == 1).first().id
                )

            session.add(WellHx(
                plate_id=well.plate_id,
                well_id=well.well_id,
                experiment_id=well.experiment_id,
                project_id=well.project_id,
                status=well.status,
                contents=json.dumps(well.contents),
                volume=well.volume,
                coordinates=json.dumps(asdict(well.coordinates)),
            ))
        session.commit()


def insert_well(well_to_insert: object) -> None:
    """
    Get the SQL statement for inserting the entry into the well_hx table.

    Returns:
        str: The SQL statement.
    """
    # statement = """
    # INSERT INTO well_hx (
    #     plate_id,
    #     well_id,
    #     experiment_id,
    #     project_id,
    #     status,
    #     status_date,
    #     contents,
    #     volume,
    #     coordinates

    #     )
    # VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    # """
    # values = (
    #     well_to_insert.plate_id,
    #     well_to_insert.well_id,
    #     well_to_insert.experiment_id,
    #     well_to_insert.project_id,
    #     well_to_insert.status,
    #     datetime.now().isoformat(timespec="seconds"),
    #     json.dumps(well_to_insert.contents),
    #     well_to_insert.volume,
    #     json.dumps(asdict(well_to_insert.coordinates)),
    # )
    # return sql_utilities.execute_sql_command_no_return(statement, values)

    with SessionLocal() as session:
        session.add(WellHx(**well_to_insert.__dict__))
        session.commit()


def update_well(well_to_update: object) -> None:
    """
    Updating the entry in the well_hx table that matches the well and plate ids.

    Returns:
        str: The SQL statement.
    """
    # statement = """
    # UPDATE well_hx
    # SET
    #     plate_id = ?,
    #     well_id = ?,
    #     experiment_id = ?,
    #     project_id = ?,
    #     status = ?,
    #     status_date = ?,
    #     contents = ?,
    #     volume = ?,
    #     coordinates = ?
    # WHERE plate_id = ?
    # AND well_id = ?
    # """
    # values = (
    #     well_to_update.plate_id,
    #     well_to_update.well_id,
    #     well_to_update.experiment_id,
    #     well_to_update.project_id,
    #     well_to_update.status,
    #     datetime.now().isoformat(timespec="seconds"),
    #     json.dumps(well_to_update.contents),
    #     well_to_update.volume,
    #     json.dumps(asdict(well_to_update.coordinates)),
    #     well_to_update.plate_id,
    #     well_to_update.well_id,
    # )
    # return sql_utilities.execute_sql_command_no_return(statement, values)

    with SessionLocal() as session:
        session.query(WellHx).filter(WellHx.plate_id == well_to_update.plate_id).filter(
            WellHx.well_id == well_to_update.well_id
        ).update(
            {
                WellHx.experiment_id: well_to_update.experiment_id,
                WellHx.project_id: well_to_update.project_id,
                WellHx.status: well_to_update.status,
                WellHx.status_date: datetime.now().isoformat(timespec="seconds"),
                WellHx.contents: json.dumps(well_to_update.contents),
                WellHx.volume: well_to_update.volume,
                WellHx.coordinates: json.dumps(asdict(well_to_update.coordinates)),
            }
        )
        session.commit()


def delete_well_from_db(well_id: str, plate_id: Union[int, None] = None) -> None:
    """
    Delete a well from the well_hx table.

    Args:
        well_id (str): The well ID.
        plate_id (int): The plate ID.
    """
    # if plate_id is None:
    #     plate_id = sql_utilities.execute_sql_command(
    #         "SELECT id FROM wellplates WHERE current = 1"
    #     )[0][0]

    # sql_utilities.execute_sql_command_no_return(
    #     """
    #     DELETE FROM well_hx
    #     WHERE well_id = ?
    #     AND plate_id = ?
    #     """,
    #     (well_id, plate_id),
    # )

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )
        session.query(WellHx).filter(WellHx.plate_id == plate_id).filter(
            WellHx.well_id == well_id
        ).delete()
        session.commit()


def get_well(
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

    # if plate_id is None:
    #     plate_id = sql_utilities.execute_sql_command(
    #         "SELECT id FROM wellplates WHERE current = 1"
    #     )[0][0]

    # statement = "SELECT * FROM well_hx WHERE plate_id = ? AND well_id = ?"
    # values = (plate_id, well_id)
    # return complete_well_information(statement, values)

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )
        result = (
            session.query(WellHx)
            .filter(WellHx.plate_id == plate_id)
            .filter(WellHx.well_id == well_id)
            .all()
        )
        if result == []:
            return None
        return result[0]


def get_well_by_experiment_id(experiment_id: str) -> Tuple:
    """
    Get a well from the well_hx table by experiment ID.

    Args:
        experiment_id (str): The experiment ID.

    Returns:
        Well: The well.
    """
    # statement = """
    #     SELECT
    #         plate_id,
    #         well_id,
    #         experiment_id,
    #         project_id,
    #         status,
    #         status_date,
    #         contents,
    #         volume,
    #         coordinates

    #     FROM well_hx WHERE experiment_id = ?"
    # )
    # """
    # values = (experiment_id,)
    # return complete_well_information(statement, values)

    with SessionLocal() as session:
        result = (
            session.query(WellHx).filter(WellHx.experiment_id == experiment_id).all()
        )
        if result == []:
            return None
        return result[0]


# def complete_well_information(returned_well_model: WellHx) -> Tuple:
#     """
#     Take in the well model from other functions and turn the output into the Well object.
#     """
#     result = sql_utilities.execute_sql_command(sql_command, values)
#     (
#         plate_id,
#         well_id,
#         experiment_id,
#         project_id,
#         status,
#         status_date,
#         contents,
#         volume,
#         coordinates,
#         _,
#     ) = result[0]

#     if result == []:
#         logger.error("Error: No well found in the well_hx table.")
#         logger.error("Statment Was: %s, Values Were: %s", sql_command, values)
#         return None

#     # Based on the plate ID, get the well type number, capacity, height
#     well_type = sql_utilities.execute_sql_command(
#         "SELECT type_id FROM wellplates WHERE id = ?", (plate_id,)
#     )

#     try:
#         capacity, height = sql_utilities.execute_sql_command(
#             "SELECT capacity_ul, height_mm FROM well_types WHERE id = ?",
#             (well_type[0][0],),
#         )[0]
#     except IndexError:
#         capacity, height = 300, 6
#     return Tuple(
#         plate_id,
#         well_id,
#         experiment_id,
#         project_id,
#         status,
#         status_date,
#         contents,
#         volume,
#         (json.loads(coordinates)),
#         capacity,
#         height,
#     )


def select_well_characteristics(type_id: int) -> WellTypes:
    """
    Select the well characteristics from the well_types table.

    Args:
        type_id (int): The well type ID.

    Returns:
        The SQL Alchemy object for the well type.
    """
    # return sql_utilities.execute_sql_command(
    #     "SELECT radius_mm, offset_mm, capacity_ul, height_mm, shape FROM well_types WHERE id = ?",
    #     (type_id,),
    # )[0]

    with SessionLocal() as session:
        result = session.query(WellTypes).filter(WellTypes.id == type_id).first()
        return result


def update_well_coordinates(
    well_id: str, plate_id: Union[int, None], coordinates: object
) -> None:
    """
    Update the coordinates of a well in the well_hx table.

    Args:
        well_id (str): The well ID.
        plate_id (int): The plate ID.
        coordinates (WellCoordinates): The coordinates.
    """
    # if plate_id is None:
    #     plate_id = sql_utilities.execute_sql_command(
    #         "SELECT id FROM wellplates WHERE current = 1"
    #     )[0][0]

    # sql_utilities.execute_sql_command(
    #     """
    #     UPDATE well_hx
    #     SET coordinates = ?
    #     WHERE well_id = ?
    #     AND plate_id = ?
    #     """,
    #     (json.dumps(asdict(coordinates)), well_id, plate_id),
    # )

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )
        session.query(WellHx).filter(WellHx.plate_id == plate_id).filter(
            WellHx.well_id == well_id
        ).update({WellHx.coordinates: json.dumps(asdict(coordinates))})
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
    # if plate_id is None:
    #     plate_id = sql_utilities.execute_sql_command(
    #         "SELECT id FROM wellplates WHERE current = 1"
    #     )[0][0]
    # if status is None:
    #     status = select_well_status(well_id, plate_id)

    # sql_utilities.execute_sql_command_no_return(
    #     """
    #     UPDATE well_hx
    #     SET status = ?,
    #         status_date = datetime('now', 'localtime')
    #     WHERE well_id = ?
    #     AND plate_id = ?
    #     """,
    #     (status, well_id, plate_id),
    # )

    with SessionLocal() as session:
        if plate_id is None:
            plate_id = (
                session.query(WellPlates).filter(WellPlates.current == 1).first().id
            )
        if status is None:
            status = select_well_status(well_id, plate_id)
        session.query(WellHx).filter(WellHx.plate_id == plate_id).filter(
            WellHx.well_id == well_id
        ).update(
            {
                WellHx.status: status,
                WellHx.status_date: datetime.now().isoformat(timespec="seconds"),
            }
        )
        session.commit()


# endregion
