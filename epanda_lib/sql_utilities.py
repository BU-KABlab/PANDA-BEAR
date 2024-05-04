"""A 'driver' for ePANDA SQL db. """

from datetime import datetime
import sqlite3
from typing import List, Union
from pathlib import Path
import json
import csv

from epanda_lib.wellplate import Well, WellCoordinates  # , WellCoordinatesEncoder
from epanda_lib.experiment_class import (
    EchemExperimentBase,
    ExperimentStatus,
    ExperimentBase,
    ExperimentResultsRecord,
    ExperimentParameterRecord,
    experiment_types_by_project_id
)

from epanda_lib.config.config_tools import read_testing_config
from epanda_lib.config.config import SQL_DB_PATH
from epanda_lib.utilities import SystemState
# region Utility Functions
def execute_sql_command(sql_command: str, parameters: tuple = None) -> List:
    """
    Execute an SQL command on the database.

    Args:
        sql_command (str): The SQL command to execute.
        parameters (tuple): The parameters for the SQL command.

    Returns:
        List: The result of the SQL command.
    """
    conn = sqlite3.connect(SQL_DB_PATH)
    conn.isolation_level = None  # Manually control transactions
    cursor = conn.cursor()

    cursor.execute("BEGIN TRANSACTION")  # Start a new transaction

    try:
        # Execute the SQL command
        if parameters:
            if isinstance(parameters[0], tuple):
                cursor.executemany(sql_command, parameters)
            else:
                cursor.execute(sql_command, parameters)
        else:
            cursor.execute(sql_command)
        result = cursor.fetchall()

        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()  # Rollback the transaction if error
        raise e
    finally:
        conn.close()

    return result


def execute_sql_command_no_return(sql_command: str, parameters: tuple = None) -> None:
    """
    Execute an SQL command on the database without returning anything.

    Args:
        sql_command (str): The SQL command to execute.
        parameters (tuple): The parameters for the SQL command.
    """
    if sql_command is None:
        return
    conn = sqlite3.connect(SQL_DB_PATH)
    conn.isolation_level = None  # Manually control transactions
    cursor = conn.cursor()

    # Start a new transaction
    cursor.execute("BEGIN TRANSACTION")

    try:
        # Execute the SQL command
        if parameters:
            if isinstance(parameters[0], tuple):
                cursor.executemany(sql_command, parameters)
            else:
                cursor.execute(sql_command, parameters)
        else:
            cursor.execute(sql_command)

        # Commit the transaction
        conn.commit()
    except Exception as e:
        # Rollback the transaction on error
        conn.rollback()
        raise e
    finally:
        # Close the connection
        conn.close()


def check_empty(value):
    """
    Check if a value is empty and return NULL if it is.
    """
    return value if value != "" else "NULL"


# endregion

# region Wellplate Functions


def check_if_wellplate_exists(plate_id: int) -> bool:
    """Check if a wellplate exists in the wellplates table"""
    result = execute_sql_command(
        """
        SELECT * FROM wellplates
        WHERE id = ?
        """,
        (plate_id,),
    )
    return result != []


def update_current_wellplate(new_plate_id: int) -> None:
    """Changes the current wellplate's current value to 0 and sets the new
    wellplate's current value to 1"""
    execute_sql_command_no_return(
        """
        UPDATE wellplates SET current = 0
        WHERE current = 1
        """
    )
    execute_sql_command_no_return(
        """
        UPDATE wellplates SET current = 1
        WHERE id = ?
        """,
        (new_plate_id,),
    )


def add_wellplate_to_table(plate_id: int, type_id: int) -> None:
    """Add a new wellplate to the wellplates table"""
    execute_sql_command_no_return(
        """
        INSERT INTO wellplates (id, type_id, current)
        VALUES (?, ?, 0)
        """,
        (plate_id, type_id),
    )


def check_if_current_wellplate_is_new() -> bool:
    """Check if the current wellplate is new"""
    result = execute_sql_command(
        """
        SELECT status FROM well_hx
        WHERE plate_id = (SELECT id FROM wellplates WHERE current = 1)
        """
    )
    if result == []:
        print("No current wellplate found")
        return False

    # If all the results are 'new' then the wellplate is new
    for row in result:
        if row[0] != "new":
            return False
    return True


def get_number_of_wells(plate_id: int = None) -> int:
    """
    Get the number of wells in the well_hx table for the given or current wellplate.

    Args:
        plate_id (int): The plate ID.

    Returns:
        int: The number of wells.
    """
    if plate_id is None:
        result = execute_sql_command(
            """
            SELECT COUNT(*) FROM well_hx
            WHERE plate_id = (SELECT id FROM wellplates WHERE current = 1)
            """
        )
    else:
        result = execute_sql_command(
            """
            SELECT COUNT(*) FROM well_hx
            WHERE plate_id = ?
            """,
            (plate_id,),
        )
    return int(result[0][0])


def get_number_of_clear_wells(plate_id: int = None) -> int:
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
    if plate_id is None:
        result = execute_sql_command(
            """
            SELECT COUNT(*) FROM well_hx
            WHERE status IN ('new', 'clear','queued')
            AND plate_id = (SELECT id FROM wellplates WHERE current = 1)
            """
        )
    else:
        result = execute_sql_command(
            """
            SELECT COUNT(*) FROM well_hx
            WHERE status IN ('new', 'clear','queued')
            AND plate_id = ?
            """,
            (plate_id,),
        )
    return int(result[0][0])


def select_current_wellplate_info() -> tuple[int, int, bool]:
    """
    Get the current wellplate information from the wellplates table.

    Returns:
        tuple[int, int, bool]: The wellplate ID, the wellplate type ID, and
        whether the wellplate is new.
    """
    result = execute_sql_command(
        """
        SELECT id, type_id FROM wellplates
        WHERE current = 1
        """
    )
    if result == []:
        return 0, 0, False
    is_new = check_if_current_wellplate_is_new()
    return result[0][0], result[0][1], is_new


def select_wellplate_wells(plate_id: int = None) -> list[Well]:
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
    if plate_id is None:
        result = execute_sql_command(
            """
            SELECT 
                plate_id,
                type_number,
                well_id,
                status,
                status_date,
                contents,
                experiment_id,
                project_id,
                volume,
                coordinates,
                capacity,
                height

            FROM well_status
            ORDER BY well_id ASC
            """
        )
    else:
        result = execute_sql_command(
            """
        SELECT 
            a.plate_id,
            b.type_id as type_number,
            a.well_id,
            a.status,
            a.status_date,
            a.contents,
            a.experiment_id,
            a.project_id,
            a.volume,
            a.coordinates,
            c.capacity_ul as capacity,
            c.height_mm as height
        FROM well_hx as a
        JOIN wellplates as b
        ON a.plate_id = b.id
        JOIN well_types as c
        ON b.type_id = c.id
        WHERE a.plate_id = ?
            """,
            (plate_id,),
        )
    if result == []:
        return None

    current_plate_id = select_current_wellplate_info()[0]
    wells = []
    for row in result:
        try:
            incoming_contents = json.loads(row[5])
        except json.JSONDecodeError:
            incoming_contents = {}

        try:
            incoming_coordinates = json.loads(row[9])
            incoming_coordinates = WellCoordinates(**incoming_coordinates)
        except json.JSONDecodeError:
            incoming_coordinates = WellCoordinates(0, 0)

        # well_height, well_capacity,
        # TODO currently the wepplate object applies the well_height and well_capacity
        # If we want the wells to be the primary source of this information, we need to
        # update this script to also pull from well_types and the stop applying the infomation in the wellplate object
        if plate_id is None:
            plate_id = row[0]
            if plate_id is None:
                plate_id = current_plate_id

        wells.append(
            Well(
                well_id=row[2],
                well_type_number=row[1],
                status=row[3],
                status_date=row[4],
                contents=incoming_contents,
                experiment_id=row[6],
                project_id=row[7],
                volume=row[8],
                coordinates=incoming_coordinates,
                capacity=row[10],
                height=row[11],
                plate_id=plate_id,
            )
        )
    return wells


def select_well_status(well_id: str) -> str:
    """
    Get the status of a well from the well_hx table.

    Args:
        well_id (str): The well ID.

    Returns:
        str: The status of the well.
    """
    result = execute_sql_command(
        f"SELECT status FROM well_status WHERE well_id = '{well_id}'"
    )
    return result[0][0]


def count_wells_with_new_status(plate_id: int = None) -> int:
    """
    Count the number of wells with a status of 'new' in the well_hx table.

    Returns:
        int: The number of wells with a status of 'new'.
    """
    if plate_id is not None:
        result = execute_sql_command(
            """
            SELECT COUNT(*) FROM well_hx
            WHERE status = 'new'
            AND plate_id = ?
            """,
            (plate_id,),
        )
    else:
        result = execute_sql_command(
            """
            SELECT COUNT(*) FROM well_status
            WHERE status = 'new'
            """
        )

    return int(result[0][0])


def select_next_available_well() -> str:
    """
    Choose the next available well in the well_hx table.

    Returns:
        str: The well ID of the next available well.
    """
    result = execute_sql_command(
        """
        SELECT well_id FROM well_status
        WHERE status = 'new'
        ORDER BY well_id ASC
        LIMIT 1
        """
    )

    if result == []:
        return None
    return result[0][0]


# endregion


# region Well Functions
def save_well_to_db(well_to_save: Well) -> None:
    """
    First check if the well is in the table. If so update the well where the
        values are different.
    Otherwise insert the well into the table.
    """
    statement = """
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (plate_id, well_id) DO UPDATE SET
        experiment_id = excluded.experiment_id,
        project_id = excluded.project_id,
        status = excluded.status,
        status_date = excluded.status_date,
        contents = excluded.contents,
        volume = excluded.volume,
        coordinates = excluded.coordinates
    """
    if well_to_save.plate_id in [None, 0]:
        well_to_save.plate_id = execute_sql_command(
            "SELECT id FROM wellplates WHERE current = 1"
        )[0][0]

    values = (
        well_to_save.plate_id,
        well_to_save.well_id,
        well_to_save.experiment_id,
        well_to_save.project_id,
        well_to_save.status,
        well_to_save.status_date,
        json.dumps(well_to_save.contents),
        well_to_save.volume,
        json.dumps(well_to_save.coordinates.to_dict()),
    )
    execute_sql_command_no_return(statement, values)


def save_wells_to_db(wells_to_save: List[Well]) -> None:
    """
    First check if the well is in the table. If so update the well where the
        values are different.
    Otherwise insert the well into the table.
    """
    statement = """
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (plate_id, well_id) DO UPDATE SET
        experiment_id = excluded.experiment_id,
        project_id = excluded.project_id,
        status = excluded.status,
        status_date = excluded.status_date,
        contents = excluded.contents,
        volume = excluded.volume,
        coordinates = excluded.coordinates
    """
    values = []
    for well in wells_to_save:
        if well.plate_id in [None, 0]:
            well.plate_id = execute_sql_command(
                "SELECT id FROM wellplates WHERE current = 1"
            )[0][0]

        values.append(
            (
                well.plate_id,
                well.well_id,
                well.experiment_id,
                well.project_id,
                well.status,
                datetime.now().isoformat(timespec="seconds"),
                json.dumps(well.contents),
                well.volume,
                json.dumps(well.coordinates.to_dict()),
            )
        )
    execute_sql_command_no_return(statement, values)


def insert_well(well_to_insert: Well) -> None:
    """
    Get the SQL statement for inserting the entry into the well_hx table.

    Returns:
        str: The SQL statement.
    """
    statement = """
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
        ) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    values = (
        well_to_insert.plate_id,
        well_to_insert.well_id,
        well_to_insert.experiment_id,
        well_to_insert.project_id,
        well_to_insert.status,
        datetime.now().isoformat(timespec="seconds"),
        json.dumps(well_to_insert.contents),
        well_to_insert.volume,
        json.dumps(well_to_insert.coordinates.to_dict()),
    )
    return execute_sql_command_no_return(statement, values)


def update_well(well_to_update: Well) -> None:
    """
    Get the SQL statement for updating the entry in the well_hx table.

    Returns:
        str: The SQL statement.
    """
    statement = """
    UPDATE well_hx 
    SET 
        plate_id = ?,
        well_id = ?,
        experiment_id = ?,
        project_id = ?,
        status = ?,
        status_date = ?,
        contents = ?,
        volume = ?,
        coordinates = ?
    WHERE plate_id = ?
    AND well_id = ?
    """
    values = (
        well_to_update.plate_id,
        well_to_update.well_id,
        well_to_update.experiment_id,
        well_to_update.project_id,
        well_to_update.status,
        datetime.now().isoformat(timespec="seconds"),
        json.dumps(well_to_update.contents),
        well_to_update.volume,
        json.dumps(well_to_update.coordinates.to_dict()),
        well_to_update.plate_id,
        well_to_update.well_id,
    )
    return execute_sql_command_no_return(statement, values)


def get_well(
    well_id: str,
    plate_id: int = None,
) -> Well:
    """
    Get a well from the well_hx table.

    Args:
        plate_id (int): The plate ID.
        well_id (str): The well ID.

    Returns:
        Well: The well.
    """

    if plate_id is None:
        plate_id = execute_sql_command("SELECT id FROM wellplates WHERE current = 1")[
            0
        ][0]

    statement = "SELECT * FROM well_hx WHERE plate_id = ? AND well_id = ?"
    values = (plate_id, well_id)
    return complete_well_information(statement, values)


def get_well_by_experiment_id(experiment_id: str) -> Well:
    """
    Get a well from the well_hx table by experiment ID.

    Args:
        experiment_id (str): The experiment ID.

    Returns:
        Well: The well.
    """
    statement = """
        SELECT 
            plate_id, 
            well_id,
            experiment_id,
            project_id,
            status,
            status_date,
            contents,
            volume,
            coordinates
        
        FROM well_hx WHERE experiment_id = ?"
    )
    """
    values = (experiment_id,)
    return complete_well_information(statement, values)


def complete_well_information(sql_command: str, values: tuple) -> Well:
    """
    Take in the formed sql command from other functions and apply the output to the Well object.
    """
    result = execute_sql_command(sql_command, values)
    (
        plate_id,
        well_id,
        experiment_id,
        project_id,
        status,
        status_date,
        contents,
        volume,
        coordinates,
    ) = result[0]

    if result == []:
        print("Error: No well found in the well_hx table.")
        print("Statment Was: ", sql_command, "Values Were: ", values)
        return None

    # Based on the plate ID, get the well type number, capacity, height
    well_type = execute_sql_command(
        "SELECT type_id FROM wellplates WHERE id = ?", (plate_id,)
    )

    try:
        capacity, height = execute_sql_command(
            "SELECT capacity_ul, height_mm FROM well_types WHERE id = ?",
            (well_type[0][0],),
        )[0]
    except IndexError:
        capacity, height = 300, 6

    return Well(
        plate_id=plate_id,
        well_id=well_id,
        experiment_id=experiment_id,
        project_id=project_id,
        status=status,
        status_date=status_date,
        contents=contents,
        volume=volume,
        coordinates=coordinates,
        capacity=capacity,
        height=height,
    )


def select_well_characteristics(type_id: int) -> tuple[int, int, int, int, str]:
    """
    Select the well characteristics from the well_types table.

    Args:
        type_id (int): The well type ID.

    Returns:
        tuple[int, int, int, int, str]: The well type ID, the radius, the offset,
        the capacity, the height, and the shape.
    """
    return execute_sql_command(
        "SELECT radius_mm, offset_mm, capacity_ul, height_mm, shape FROM well_types WHERE id = ?",
        (type_id,),
    )[0]

def update_well_coordinates(well_id: str, plate_id: int, coordinates: WellCoordinates) -> None:
    """
    Update the coordinates of a well in the well_hx table.

    Args:
        well_id (str): The well ID.
        plate_id (int): The plate ID.
        coordinates (WellCoordinates): The coordinates.
    """
    if plate_id is None:
        plate_id = execute_sql_command(
            "SELECT id FROM wellplates WHERE current = 1"
        )[0][0]
    
    execute_sql_command_no_return(
        """
        UPDATE well_hx
        SET coordinates = ?
        WHERE well_id = ?
        AND plate_id = ?
        """,
        (json.dumps(coordinates.to_dict()), well_id, plate_id),
    )

# endregion

# region Queue Functions

# Note the queue is a view and not a table, so it cannot be updated directly.
# Instead the well_hx table is updated with the experiment_id and status.
# If the status is 'queued' then the experiment is in the queue.
# Otherwise the experiment is not in the queue.
# TODO in the future experiments in the experiments table that are not matched to a well
# in the well_hx table should be added to the queue in some manner but this is not implemented yet.


def select_queue() -> list:
    """
    Selects all the entries from the queue table.

    Returns:
        list: The entries from the queue table.
    """
    result = execute_sql_command(
        """
        SELECT
            experiment_id,
            process_type,
            priority,
            filename
        FROM queue 
        ORDER BY experiment_id ASC
        """
    )
    return result


def get_next_experiment_from_queue(random_pick: bool = False) -> tuple[int, int, str]:
    """
    Reads the next experiment from the queue table, the experiment with the
    highest priority (lowest value).

    If random_pick, a random experiment with highest priority (lowest value) is selected.
    Else, the lowest experiment id with the highest priority (lowest value) is selected.

    Args:
        random_pick (bool): Whether to pick a random experiment from the queue.

    Returns:
        tuple: The experiment ID, the process type, and the filename.
    """
    if random_pick:
        result = execute_sql_command(
            """
            SELECT experiment_id, process_type, filename, project_id, well_id FROM queue
            WHERE priority = (SELECT MIN(priority) FROM queue)
            AND status = 'queued'
            ORDER BY RANDOM()
            LIMIT 1
            """
        )
    else:
        result = execute_sql_command(
            """
            SELECT experiment_id, process_type, filename, project_id, well_id FROM queue
            WHERE priority = (SELECT MIN(priority) FROM queue)
            AND status = 'queued'
            ORDER BY experiment_id ASC
            LIMIT 1
            """
        )

    if result == []:
        return None
    return result[0][0], result[0][1], result[0][2], result[0][3], result[0][4]


def clear_queue() -> None:
    """Go through and change the status of any queued experiment to pending"""
    execute_sql_command_no_return(
        """
        UPDATE well_hx SET status = 'pending'
        WHERE status = 'queued'
        """
    )


def count_queue_length() -> int:
    """Count the number of experiments in the queue"""
    result = execute_sql_command(
        """
        SELECT COUNT(*) FROM queue
        WHERE status = 'queued'
        """
    )
    return int(result[0][0])


# endregion

# region Experiment Functions


def select_next_experiment_id() -> int:
    """Determines the next experiment id by checking the experiment table"""
    result = execute_sql_command(
        """
        SELECT experiment_id FROM experiments
        ORDER BY experiment_id DESC
        LIMIT 1
        """
    )
    if result == []:
        return 10000000
    return result[0][0] + 1


def select_experiment_information(experiment_id: int) -> ExperimentBase:
    """
    Selects the experiment information from the experiments table.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        ExperimentBase: The experiment information.
    """
    values = execute_sql_command(
        """
        SELECT
            experiment_id,
            project_id,
            project_campaign_id,
            well_type,
            protocol_id,
            pin,
            experiment_type,
            jira_issue_key,
            priority,
            process_type,
            filename
        FROM experiments
        WHERE experiment_id = ?
        """,
        (experiment_id,),
    )

    if values == []:
        return None
    else:

        # With the project_id known to determine the experiment type
        # object type
        project_id = values[0][1]
        experiment_object = experiment_types_by_project_id.get(project_id)()

        experiment = experiment_object
        experiment.experiment_id = experiment_id
        experiment.project_id = values[0][1]
        experiment.project_campaign_id = values[0][2]
        experiment.well_type_number = values[0][3]
        experiment.protocol_id = values[0][4]
        experiment.pin = values[0][5]
        experiment.experiment_type = values[0][6]
        experiment.jira_issue_key = values[0][7]
        experiment.priority = values[0][8]
        experiment.process_type = values[0][9]
        experiment.filename = values[0][10]
        return experiment


def select_experiment_paramaters(
    experiment_to_select: Union[int, EchemExperimentBase]
) -> Union[list, EchemExperimentBase]:
    """
    Selects the experiment parameters from the experiment_parameters table.
    If an experiment_object is provided, the parameters are added to the object.

    Args:
        experiment_to_select (Union[int, EchemExperimentBase]): The experiment ID or object.

    Returns:
        EchemExperimentBase: The experiment parameters.
    """
    if isinstance(experiment_to_select, int):
        experiment_id = experiment_to_select
        experiment_object = None
    else:
        experiment_id = experiment_to_select.experiment_id
        experiment_object = experiment_to_select

    values = execute_sql_command(
        """
        SELECT
            experiment_id,
            parameter_name,
            parameter_value
        FROM experiment_parameters
        WHERE experiment_id = ?
        """,
        (experiment_id,),
    )

    if values == []:
        return None

    if not experiment_object:
        return values

    # With the experiment_id known, look up the project_id to determine the experiment
    # object type
    # project_id_result = execute_sql_command(
    #     "SELECT project_id FROM experiments WHERE experiment_id = ?",
    #     (experiment_id,),
    # )
    # if project_id_result:
    #     project_id = project_id_result[0][0]
    #     experiment_object = experiment_types_by_project_id.get(project_id)()
    # else:
    #     pass

    experiment_object.map_parameter_list_to_experiment(values)
    return experiment_object

def select_specific_parameter(experiment_id: int, parameter_name: str):
    """
    Select a specific parameter from the experiment_parameters table.

    Args:
        experiment_id (int): The experiment ID.
        parameter_name (str): The parameter name.

    Returns:
        any: The parameter value.
    """
    result = execute_sql_command(
        """
        SELECT parameter_value FROM experiment_parameters
        WHERE experiment_id = ?
        AND parameter_name = ?
        """,
        (experiment_id, parameter_name),
    )
    if result == []:
        return None
    return result[0][0]

def select_experiment_status(experiment_id: int) -> str:
    """
    Select the status of an experiment from the well_hx table.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        str: The status of the experiment.
    """
    result = execute_sql_command(
        """
        SELECT status FROM well_hx
        WHERE experiment_id = ?
        """,
        (experiment_id,),
    )
    if result == []:
        return ValueError("No experiment found with that ID")
    return result[0][0]

def insert_experiment(experiment: ExperimentBase) -> None:
    """
    Insert an experiment into the experiments table.

    Args:
        experiment (ExperimentBase): The experiment to insert.
    """
    insert_experiments([experiment])


def insert_experiments(experiments: List[ExperimentBase]) -> None:
    """
    Insert a list of experiments into the experiments table.

    Args:
        experiments (List[ExperimentBase]): The experiments to insert.
    """
    parameters = []
    for experiment in experiments:
        parameters.append(
            (
                experiment.experiment_id,
                experiment.project_id,
                experiment.project_campaign_id,
                experiment.well_type_number,
                experiment.protocol_id,
                experiment.pin,
                experiment.experiment_type,
                experiment.jira_issue_key,
                experiment.priority,
                experiment.process_type,
                experiment.filename,
                datetime.now().isoformat(timespec="seconds"),
            )
        )
    execute_sql_command_no_return(
        """
        INSERT INTO experiments (
            experiment_id,
            project_id,
            project_campaign_id,
            well_type,
            protocol_id,
            pin,
            experiment_type,
            jira_issue_key,
            priority,
            process_type,
            filename,
            created
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        parameters,
    )


def insert_experiment_parameters(experiment: ExperimentBase) -> None:
    """
    Insert the experiment parameters into the experiment_parameters table.

    Args:
        experiment (ExperimentBase): The experiment to insert.
    """
    # experiment_parameters: list[ExperimentParameterRecord] = (
    #     experiment.generate_parameter_list()
    # )
    # parameters = [
    #     (
    #         experiment.experiment_id,
    #         parameter.parameter_type,
    #         parameter.parameter_value,
    #         datetime.now().isoformat(timespec="seconds"),
    #     )
    #     for parameter in experiment_parameters
    # ]
    # execute_sql_command_no_return(
    #     """
    #     INSERT INTO experiment_parameters (
    #         experiment_id,
    #         parameter_name,
    #         parameter_value,
    #         created
    #         )
    #     VALUES (?, ?, ?, ?)
    #     """,
    #     parameters,
    # )
    insert_experiments_parameters([experiment])


def insert_experiments_parameters(experiments: List[ExperimentBase]) -> None:
    """
    Insert the experiment parameters into the experiment_parameters table.

    Args:
        experiments (List[ExperimentBase]): The experiments to insert.
    """
    parameters_to_insert = [] # this will be a list of tuples of the parameters to insert
    for experiment in experiments:
        experiment_parameters: list[ExperimentParameterRecord] = (
            experiment.generate_parameter_list()
        )
        for parameter in experiment_parameters:
            parameters_to_insert.append(
                (
                    experiment.experiment_id,
                    parameter.parameter_type,
                    (
                        json.dumps(parameter.parameter_value)
                        if isinstance(parameter.parameter_value, dict)
                        else parameter.parameter_value
                    ),
                    datetime.now().isoformat(timespec="seconds"),
                )
            )
    execute_sql_command_no_return(
        """
        INSERT INTO experiment_parameters (
            experiment_id,
            parameter_name,
            parameter_value,
            created
            )
        VALUES (?, ?, ?, ?)
        """,
        parameters_to_insert,
    )


def update_experiment(experiment: ExperimentBase) -> None:
    """
    Update an experiment in the experiments table.

    Args:
        experiment (ExperimentBase): The experiment to update.
    """
    # execute_sql_command_no_return(
    #     """
    #     UPDATE experiments
    #     SET project_id = ?,
    #         project_campaign_id = ?,
    #         well_type = ?,
    #         protocol_id = ?,
    #         pin = ?,
    #         experiment_type = ?,
    #         jira_issue_key = ?,
    #         priority = ?,
    #         process_type = ?,
    #         filename = ?
    #     WHERE experiment_id = ?
    #     """,
    #     (
    #         experiment.project_id,
    #         experiment.project_campaign_id,
    #         experiment.well_type_number,
    #         experiment.protocol_id,
    #         experiment.pin,
    #         experiment.experiment_type,
    #         experiment.jira_issue_key,
    #         experiment.priority,
    #         experiment.process_type,
    #         experiment.filename,
    #         experiment.experiment_id,
    #     ),
    # )
    update_experiments([experiment])


def update_experiments(experiments: List[ExperimentBase]) -> None:
    """
    Update a list of experiments in the experiments table.

    Args:
        experiments (List[ExperimentBase]): The experiments to update.
    """
    parameters = []
    for experiment in experiments:
        parameters.append(
            (
                experiment.project_id,
                experiment.project_campaign_id,
                experiment.well_type_number,
                experiment.protocol_id,
                experiment.pin,
                experiment.experiment_type,
                experiment.jira_issue_key,
                experiment.priority,
                experiment.process_type,
                experiment.filename,
                experiment.experiment_id,
            )
        )
    execute_sql_command_no_return(
        """
        UPDATE experiments
        SET project_id = ?,
            project_campaign_id = ?,
            well_type = ?,
            protocol_id = ?,
            pin = ?,
            experiment_type = ?,
            jira_issue_key = ?,
            priority = ?,
            process_type = ?,
            filename = ?
        WHERE experiment_id = ?
        """,
        parameters,
    )


def update_experiment_status(
    experiment: Union[ExperimentBase, int],
    status: ExperimentStatus = None,
    status_date: datetime = None,
) -> None:
    """
    Update the status of an experiment in the experiments table.

    When provided with an int, the experiment_id is the int, and the status and status_date are the other two arguments.
    If no status is provided, the function will not make assumptions and will do nothing.

    When provided with an ExperimentBase object, the object's attributes will be used to update the status.
    If an object is provided along with a status and status date, the object's attributes will be updated with the status and status date.

    Args:
        experiment_id (int): The experiment ID.
        status (ExperimentStatus): The status to update to.
    """
    # Handel the case where the experiment is passed as an object or an int
    # If it is an int, then the experiment_id is the int, and the status and the
    # status_date are the other two arguments
    # If it is an object, then use the experimentbase object for the data
    if isinstance(experiment, int):
        experiment_id = experiment
        if status is None:
            return
        if status_date is None:
            status_date = datetime.now().isoformat(timespec="seconds")

        experiment_info = select_experiment_information(experiment_id)
        project_id = experiment_info.project_id
        well_id = experiment_info.well_id

    else:
        experiment_id = experiment.experiment_id
        if status is not None:
            experiment.set_status(status)
        else:
            status = experiment.status
        if status_date is not None:
            experiment.status_date = status_date
        else:
            status_date = experiment.status_date
        project_id = experiment.project_id
        well_id = experiment.well_id

    execute_sql_command(
        """
        UPDATE well_hx
        SET status = ?, status_date = ?, experiment_id = ?, project_id = ?
        WHERE well_id = ?
        AND plate_id = (SELECT id FROM wellplates WHERE current = 1)
        """,
        (
            status.value,
            status_date,
            experiment_id,
            project_id,
            well_id,
        ),
    )


def update_experiments_statuses(
    experiments: List[ExperimentBase],
    exp_status: ExperimentStatus,
    status_date: datetime = None,
) -> None:
    """
    Set the status of a list of experiments in the well_hx table.

    Args:
        experiments (List[ExperimentBase]): The experiments to set the status for.
        status (ExperimentStatus): The status to set for the experiments.
        status_date (datetime): The status date to set for the experiments.
    """
    if status_date is None:
        status_date = datetime.now().isoformat(timespec="seconds")

    for experiment in experiments:
        experiment.set_status(exp_status)

    parameters = [
        (
            exp_status.value,
            status_date,
            experiment.experiment_id,
            experiment.project_id,
            experiment.well_id,
        )
        for experiment in experiments
    ]
    execute_sql_command_no_return(
        """
        UPDATE well_hx
        SET status = ?, status_date = ?, experiment_id = ?, project_id = ?
        WHERE well_id = ?
        AND plate_id = (SELECT id FROM wellplates WHERE current = 1)
        """,
        parameters,
    )


# endregion

# region Result Functions

def insert_experiment_result(entry: ExperimentResultsRecord) -> None:
    """
    Insert an entry into the result table.

    Args:
        entry (ResultTableEntry): The entry to insert.
    """
    command = """
        INSERT INTO experiment_results (
            experiment_id,
            result_type,
            result_value,
            context
            )
        VALUES (?, ?, ?, ?)
        """
    if isinstance(entry.result_value, dict):
        entry.result_value = json.dumps(entry.result_value)
    if isinstance(entry.result_value, Path):
        entry.result_value = str(entry.result_value)
    parameters = (entry.experiment_id, entry.result_type, entry.result_value, entry.context)
    execute_sql_command_no_return(command, parameters)

def insert_experiment_results(entries: List[ExperimentResultsRecord]) -> None:
    """
    Insert a list of entries into the result table.

    Args:
        entries (List[ResultTableEntry]): The entries to insert.
    """
    for entry in entries:
        insert_experiment_result(entry)


def select_results(experiment_id: int) -> List[ExperimentResultsRecord]:
    """
    Select the entries from the result table that are associated with an experiment.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        List[ResultTableEntry]: The entries from the result table.
    """
    result_parameters = execute_sql_command(
        """
        SELECT
            experiment_id,
            result_type,
            result_value,
            context
        FROM experiment_results
        WHERE experiment_id = ?
        """,
        (experiment_id,),
    )
    results = []
    for row in result_parameters:
        results.append(ExperimentResultsRecord(*row))
    return results


def select_specific_result(
    experiment_id: int, result_type: str, context: str = None
) -> ExperimentResultsRecord:
    """
    Select a specific entry from the result table that is associated with an experiment.

    Args:
        experiment_id (int): The experiment ID.
        result_type (str): The result type.

    Returns:
        ResultTableEntry: The entry from the result table.
    """
    if context is None:
        result = execute_sql_command(
            """
            SELECT 
                experiment_id,
                result_type,
                result_value,
                context
            FROM experiment_results
            WHERE experiment_id = ? AND result_type = ?
            """,
            (experiment_id, result_type),
        )
    else:
        result = execute_sql_command(
            """
            SELECT 
                experiment_id,
                result_type,
                result_value,
                context
            FROM experiment_results
            WHERE experiment_id = ? AND result_type = ? AND context = ?
            """,
            (experiment_id, result_type, context),
        )
    if result == []:
        return None
    return ExperimentResultsRecord(*result[0])


# endregion


# region Data backfilling functions
# These functions are used to backfill the database with data from CSV files.
# This is useful when the database is created and the data is not available yet.
# Otherwise we wil not use them. Hence the double underscore in the function name.
def __process_well_hx_csv_into_table():
    """
    Process the well history CSV file into the well_hx table.
    Matching each column:
    0 plate id
    1 type number
    2 well id
    3 experiment id
    4 project id
    5 status
    6 status date
    7 contents
    8 volume
    9 coordinates
    """
    # Read the well history CSV file
    with open(
        r".\epanda_lib\system state\well_history.csv",
        "r",
        encoding="utf-8",
    ) as file:
        lines = file.readlines()

    # Prepare the SQL insert statement and parameters
    sql_command = """
        INSERT or IGNORE INTO well_hx 
        (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    parameters = []

    for csv_line in lines:
        reader = csv.reader([csv_line], delimiter="&")
        for row in reader:
            (
                plate_id,
                _,
                well_id,
                experiment_id,
                project_id,
                status,
                status_date,
                contents,
                volume,
                coordinates,
            ) = map(check_empty, row)

            if contents == "{}":
                contents = "NULL"
            if coordinates == "{}":
                coordinates = "NULL"
            # Convert the JSON strings to single-quoted JSON strings
            if contents != "NULL" and not isinstance(contents, dict):
                try:
                    contents = json.dumps(json.loads(contents), separators=(",", ":"))
                    contents = contents.replace("'", '"')
                except json.decoder.JSONDecodeError:
                    contents = "NULL"

            if coordinates != "NULL" and not isinstance(coordinates, dict):
                try:
                    coordinates = json.dumps(
                        json.loads(coordinates), separators=(",", ":")
                    )
                    coordinates = coordinates.replace("'", '"')
                except json.decoder.JSONDecodeError:
                    coordinates = "NULL"

            # Add the parameters to the list
            parameters.append(
                (
                    plate_id,
                    well_id,
                    experiment_id,
                    project_id,
                    status,
                    status_date,
                    contents,
                    volume,
                    coordinates,
                )
            )

    # Execute the SQL command with the parameters
    execute_sql_command_no_return(sql_command, parameters)


# endregion


# # region System State Classes and Functions
# class SystemState(Enum):
#     """Class for naming of the system states"""

#     IDLE = "idle"
#     BUSY = "running"
#     ERROR = "error"
#     ON = "on"
#     OFF = "off"
#     SHUTDOWN = "shutdown"
#     RESUME = "resume"
#     PAUSE = "pause"


def select_system_status(look_back:int = 1) -> SystemState:
    """
    Get the system status from the system_status table.

    Returns:
        dict: The system status.
    """
    result = execute_sql_command(
        """
        SELECT status FROM system_status
        ORDER BY status_time DESC
        LIMIT ?
        """, (look_back,)
    )
    if result == []:
        return SystemState("off")

    if look_back == 1:
        return SystemState(result[0][0])
    else:
        return [SystemState(row[0]) for row in result]

def set_system_status(
    system_status: SystemState, comment=None, test_mode=read_testing_config()
) -> None:
    """
    Set the system status in the system_status table.

    Args:
        status (SystemState): The system status to set.
    """
    execute_sql_command_no_return(
        """
        INSERT INTO system_status (status, comment, test_mode)
        VALUES (?, ?, ?)
        """,
        (system_status.value, comment, test_mode),
    )


# endregion
