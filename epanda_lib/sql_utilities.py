"""A 'driver' for connecting to the project SQL database and executing SQL commands. """

from datetime import datetime
import sqlite3
from typing import List, Union
from pathlib import Path
import json
import csv
import dataclasses
import time
from enum import Enum

from epanda_lib.nesp_lib_local import status
from epanda_lib.wellplate import Well
from epanda_lib.experiment_class import (
    ExperimentStatus,
    ExperimentBase,
    ExperimentResultsRecord,
    ExperimentParameterRecord,
)

# from epanda_lib.config.config import SQL_DB_PATH
from epanda_lib.config.config_tools import read_testing_config

SQL_DB_PATH = Path("P:/epanda_dev.db")


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

        cursor.execute("COMMIT")  # Commit the transaction
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        cursor.execute("ROLLBACK")  # Rollback the transaction in case of error
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
    """Changes the current wellplate's current value to 0 and sets the new wellplate's current value to 1"""
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


def determine_next_experiment_id() -> int:
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


def select_wellplate_wells(plate_id: int = None) -> list[Well]:
    """
    Selects all wells from the well_hx table for a specific wellplate.
    Or if no plate_id is provided, all wells of the current wellplate are selected.

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
            SELECT * FROM well_status
            ORDER BY well_id ASC
            """
        )
    else:
        result = execute_sql_command(
            """
            SELECT * FROM well_hx
            WHERE plate_id = ?
            ORDER BY well_id ASC
            """,
            (plate_id),
        )
    if result == []:
        return None

    wells = []
    for row in result:
        wells.append(
            Well(
                plate_id=row[0],  # plate_id
                # row[1],  # type_number
                well_id=str(row[2]).upper(),  # well_id
                status=row[3],  # status
                status_date=row[4],  # status_date
                contents=row[5],  # contents
                experiment_id=row[6],  # experiment_id
                project_id=row[7],  # project_id
                volume=row[8],  # volume
                coordinates=row[9],  # coordinates
            )
        )
    return wells


def get_well_status(well_id: str) -> str:
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


def select_queue() -> list:
    """
    Selects all the entries from the queue table.

    Returns:
        list: The entries from the queue table.
    """
    result = execute_sql_command(
        "SELECT experiment_id, process_type, priority, filename FROM queue ORDER BY experiment_id ASC"
    )
    return result


def get_next_experiment_from_queue(random_pick: bool = False) -> tuple[int, int, str]:
    """
    Reads the next experiment from the queue table, the experiment with the highest priority (lowest number).
        If random_pick is True, then a random experiment with the highest priority is selected.
        Otherwise, the lowest experiment id in the queue with the highest priority is selected.

    Args:
        random_pick (bool): Whether to pick a random experiment from the queue.

    Returns:
        tuple: The experiment ID, the process type, and the filename.
    """
    if random_pick:
        result = execute_sql_command(
            """
            SELECT experiment_id, process_type, filename FROM queue
            WHERE priority = (SELECT MAX(priority) FROM queue)
            ORDER BY RANDOM()
            LIMIT 1
            """
        )
    else:
        result = execute_sql_command(
            """
            SELECT experiment_id, process_type, filename FROM queue
            WHERE priority = (SELECT MAX(priority) FROM queue)
            ORDER BY experiment_id ASC
            LIMIT 1
            """
        )

    if result == []:
        return None
    return result[0][0], result[0][1], result[0][2]


def select_experiment_paramaters(experiment_id: int) -> ExperimentBase:
    """
    Selects the experiment parameters from the experiment_parameters table.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        ExperimentBase: The experiment parameters.
    """
    values = execute_sql_command(
        """
        SELECT experiment_id, parameter_name, parameter_value, filename FROM experiment_parameters
        WHERE experiment_id = ?
        """,
        (experiment_id,),
    )

    if values == []:
        return None
    return values  # FIXME - needs validation


def update_experiment_status(
    experiment: Union[ExperimentBase, int],
    status: ExperimentStatus = None,
    status_date: datetime = None,
) -> None:
    """
    Update the status of an experiment in the experiments table.

    Args:
        experiment_id (int): The experiment ID.
        status (ExperimentStatus): The status to update to.
    """
    if isinstance(experiment, int):
        experiment_id = experiment
    else:
        experiment_id = experiment.id

    if status is None:
        status = experiment.status
    if status_date is None:
        status_date = experiment.status_date

    execute_sql_command_no_return(
        """
        UPDATE well_hx SET status = ?, status_date = ?
        WHERE experiment_id = ?
        AND well_id = ?
        AND plate_id = ?
        """,
        (
            status.value,
            experiment_id,
            experiment.well_id,
            experiment.plate_id,
            status_date,
        ),
    )
def get_number_of_wells(plate_id: int = None) -> int:
    """
    Get the number of wells in the well_hx table.

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
    """Query the well_hx table and count the number of wells with status in 'new', 'clear','queued' for the current wellplate.
    If plate_id is provided, count the wells of the specified wellplate in well_hx instead of the current wellplate.

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

def get_current_wellplate_info() -> tuple[int, int, bool]:
    """
    Get the current wellplate information from the wellplates table.

    Returns:
        tuple[int, int, bool]: The wellplate ID, the wellplate type ID, and whether the wellplate is new.
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


def insert_experiment(experiment: ExperimentBase) -> None:
    """
    Insert an experiment into the experiments table.

    Args:
        experiment (ExperimentBase): The experiment to insert.
    """
    execute_sql_command_no_return(
        """
        INSERT INTO experiments (experiment_id, project_id, project_campaign_id, well_type, protocol_id, pin, experiment_type, jira_issue_key, priority, process_type, filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            experiment.id,
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
        ),
    )


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
                experiment.id,
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
        INSERT INTO experiments (experiment_id, project_id, project_campaign_id, well_type, protocol_id, pin, experiment_type, jira_issue_key, priority, process_type, filename, created)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        parameters,
    )


def update_experiment(experiment: ExperimentBase) -> None:
    """
    Update an experiment in the experiments table.

    Args:
        experiment (ExperimentBase): The experiment to update.
    """
    execute_sql_command_no_return(
        """
        UPDATE experiments SET project_id = ?, project_campaign_id = ?, well_type = ?, protocol_id = ?, pin = ?, experiment_type = ?, jira_issue_key = ?, priority = ?, process_type = ?, filename = ?
        WHERE experiment_id = ?
        """,
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
            experiment.id,
        ),
    )


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
                experiment.id,
            )
        )
    execute_sql_command_no_return(
        """
        UPDATE experiments SET project_id = ?, project_campaign_id = ?, well_type = ?, protocol_id = ?, pin = ?, experiment_type = ?, jira_issue_key = ?, priority = ?, process_type = ?, filename = ?
        WHERE experiment_id = ?
        """,
        parameters,
    )


def insert_experiment_parameters(experiment: ExperimentBase) -> None:
    """
    Insert the experiment parameters into the experiment_parameters table.

    Args:
        experiment (ExperimentBase): The experiment to insert.
    """
    experiment_parameters: list[ExperimentParameterRecord] = experiment.get_parameters()
    parameters = [
        (
            experiment.id,
            parameter.parameter_type,
            parameter.parameter_value,
            datetime.now().isoformat(timespec="seconds"),
        )
        for parameter in experiment_parameters
    ]
    execute_sql_command_no_return(
        """
        INSERT INTO experiment_parameters (experiment_id, parameter_name, parameter_value, created)
        VALUES (?, ?, ?, ?)
        """,
        parameters,
    )


def insert_experiments_parameters(experiments: List[ExperimentBase]) -> None:
    """
    Insert the experiment parameters into the experiment_parameters table.

    Args:
        experiments (List[ExperimentBase]): The experiments to insert.
    """
    parameters = []
    for experiment in experiments:
        experiment_parameters: list[ExperimentParameterRecord] = (
            experiment.get_parameters()
        )
        for parameter in experiment_parameters:
            parameters.append(
                (
                    experiment.id,
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
        INSERT INTO experiment_parameters (experiment_id, parameter_name, parameter_value, created)
        VALUES (?, ?, ?,?)
        """,
        parameters,
    )


def set_experiments_statuses(
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
        (exp_status.value, status_date, experiment.id, experiment.project_id, experiment.well_id)
        for experiment in experiments
    ]
    execute_sql_command_no_return(
        """
        UPDATE well_hx SET status = ?, status_date = ?, experiment_id = ?, project_id = ?
        WHERE well_id = ? AND plate_id = (SELECT id FROM wellplates WHERE current = 1)
        """,
        parameters,
    )



class WellSQLHandler:
    """
    A class for handling the well history table.
    The table has columns:
    plate_id,
    well_id,
    experiment_id,
    project_id,
    status,
    status_date
    contents,
    volume,
    coordinates

    For the values status, status_date, and project_id, they are stored in the experiments table.

    """

    def __init__(self, well: Well = None):
        """
        Initialize the WellHxHandler class.
        """
        # if the well is None, use the current wellplate for the plate_id
        if isinstance(well, str):
            self.plate_id, _, _ = get_current_wellplate_info()
            self.well_id = well

            # with the well_id and plate_id set, get the rest of the well information
            well = self.get_well()
            if well is not None:
                self.experiment_id = well.experiment_id
                self.project_id = well.project_id
                self.status = well.status
                self.status_date = well.status_date
                self.contents = well.contents
                self.volume = well.volume
                self.coordinates = well.coordinates

        else:
            self.plate_id = well.plate_id
            self.well_id = well.well_id
            self.experiment_id = well.experiment_id
            self.project_id = well.project_id
            self.status = well.status
            self.status_date = well.status_date
            self.contents = well.contents
            self.volume = well.volume
            self.coordinates = well.coordinates
            self.wellplate: list[Well] = []

    def __str__(self):
        return f"Plate ID: {self.plate_id}, Well ID: {self.well_id}, Experiment ID: {self.experiment_id}, Project ID: {self.project_id}, Contents: {self.contents}, Volume: {self.volume}, Coordinates: {self.coordinates}"

    def __repr__(self):
        return f"WellHxHandler({self.plate_id}, {self.well_id}, {self.experiment_id}, {self.project_id}, {self.contents}, {self.volume}, {self.coordinates})"

    def save_to_db(self) -> None:
        """
        First check if the well is in the table. If so update the well where the values are different.
        Otherwise insert the well into the table.
        """
        statement = """
            INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (plate_id, well_id) DO UPDATE SET
            experiment_id = excluded.experiment_id,
            project_id = excluded.project_id,
            status = excluded.status,
            status_date = excluded.status_date,
            contents = excluded.contents,
            volume = excluded.volume,
            coordinates = excluded.coordinates
        """
        values = (
            self.plate_id,
            self.well_id,
            self.experiment_id,
            self.project_id,
            self.status,
            self.status_date,
            json.dumps(self.contents),
            self.volume,
            json.dumps(self.coordinates),
        )
        execute_sql_command_no_return(statement, values)

    def insert_well(self) -> str:
        """
        Get the SQL statement for inserting the entry into the well_hx table.

        Returns:
            str: The SQL statement.
        """
        statement = "INSERT INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        values = (
            self.plate_id,
            self.well_id,
            self.experiment_id,
            self.project_id,
            self.status,
            self.status_date,
            json.dumps(self.contents),
            self.volume,
            json.dumps(self.coordinates),
        )
        return execute_sql_command_no_return(statement, values)

    def update_well(self) -> str:
        """
        Get the SQL statement for updating the entry in the well_hx table.

        Returns:
            str: The SQL statement.
        """
        statement = "UPDATE well_hx SET plate_id = ?, well_id = ?, experiment_id = ?, project_id = ?, status = ?, status_date = ?, contents = ?, volume = ?, coordinates = ? WHERE plate_id = ? AND well_id = ?"
        values = (
            self.plate_id,
            self.well_id,
            self.experiment_id,
            self.project_id,
            self.status,
            self.status_date,
            json.dumps(self.contents),
            self.volume,
            json.dumps(self.coordinates),
            self.plate_id,
            self.well_id,
        )
        return execute_sql_command_no_return(statement, values)

    def get_well(self, plate_id: int = None, well_id: str = None) -> Well:
        """
        Get a well from the well_hx table.

        Args:
            plate_id (int): The plate ID.
            well_id (str): The well ID.

        Returns:
            Well: The well.
        """
        if plate_id is None:
            plate_id = self.plate_id
        if well_id is None:
            well_id = self.well_id

        result = execute_sql_command(
            f"SELECT * FROM well_hx WHERE plate_id = {plate_id} AND well_id = '{well_id}'"
        )

        if result == []:
            return None
        return Well(
            plate_id=result[0][0],
            well_id=result[0][1],
            experiment_id=result[0][2],
            project_id=result[0][3],
            status=result[0][4],
            status_date=result[0][5],
            contents=result[0][6],
            volume=result[0][7],
            coordinates=result[0][8],
        )

    def get_well_by_experiment_id(self, experiment_id: str) -> Well:
        """
        Get a well from the well_hx table by experiment ID.

        Args:
            experiment_id (str): The experiment ID.

        Returns:
            Well: The well.
        """
        result = execute_sql_command(
            f"SELECT * FROM well_hx WHERE experiment_id = '{experiment_id}'"
        )
        return Well(
            plate_id=result[0][0],
            well_id=result[0][1],
            experiment_id=result[0][2],
            project_id=result[0][3],
            status=result[0][4],
            status_date=result[0][5],
            contents=result[0][6],
            volume=result[0][7],
            coordinates=result[0][8],
        )

    def select_provided_wellplate_wells(self, plate_id: int) -> List[Well]:
        """
        Get a wellplate from the well_hx table.

        Args:
            plate_id (int): The plate ID.

        Returns:
            List[Well]: The wellplate.
        """
        result = select_wellplate_wells(plate_id)
        if result == []:
            return None
        for row in result:
            self.wellplate.append(
                Well(
                    plate_id=row[0],
                    well_id=row[1],
                    experiment_id=row[2],
                    project_id=row[3],
                    status=row[4],
                    status_date=row[5],
                    contents=row[6],
                    volume=row[7],
                    coordinates=row[8],
                )
            )
        return self.wellplate


def insert_experiment_results(entry: ExperimentResultsRecord) -> None:
    """
    Insert an entry into the result table.

    Args:
        entry (ResultTableEntry): The entry to insert.
    """
    command = (
        "INSERT INTO result_table (experiment_id, result_type, result) VALUES (?, ?, ?)"
    )
    parameters = (entry.experiment_id, entry.result_type, entry.result_value)
    execute_sql_command_no_return(command, parameters)


def select_results(experiment_id: int) -> List[ExperimentResultsRecord]:
    """
    Select the entries from the result table that are associated with an experiment.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        List[ResultTableEntry]: The entries from the result table.
    """
    result_parameters = execute_sql_command(
        "SELECT experiment_id, result_type, result_value FROM result_table WHERE experiment_id = ?",
        (experiment_id,),
    )
    results = []
    for row in result_parameters:
        results.append(ExperimentResultsRecord(*row))
    return results


def select_specific_result(
    experiment_id: int, result_type: str
) -> ExperimentResultsRecord:
    """
    Select a specific entry from the result table that is associated with an experiment.

    Args:
        experiment_id (int): The experiment ID.
        result_type (str): The result type.

    Returns:
        ResultTableEntry: The entry from the result table.
    """
    result = execute_sql_command(
        "SELECT experiment_id, result_type, result_value FROM experiment_results WHERE experiment_id = ? AND result_type = ?",
        (experiment_id, result_type),
    )
    return ExperimentResultsRecord(*result[0])


def process_well_hx_csv_into_table():
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
        r"C:\Users\Gregory Robben\SynologyDrive\Documents\GitHub\PANDA-BEAR\epanda_lib\system state\well_history.csv",
        "r",
    ) as file:
        lines = file.readlines()

    for csv_line in lines:
        reader = csv.reader([csv_line], delimiter="&")
        for row in reader:
            (
                plate_id,
                _,  # This is not used, it is found via the plate_id
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

            # Prepare the SQL insert statement
            sql_command = f"INSERT or IGNORE INTO well_hx (plate_id, well_id, experiment_id, project_id, status, status_date, contents, volume, coordinates) VALUES ({plate_id}, '{well_id}', '{experiment_id}', '{project_id}', '{status}', '{status_date}', '{contents}', {volume}, '{coordinates}')"
            execute_sql_command_no_return(sql_command)


def check_empty(value):
    """
    Check if a value is empty and return NULL if it is.
    """
    return value if value != "" else "NULL"


@dataclasses.dataclass
class SystemState(Enum):
    """Class for naming of the system states"""

    IDLE = "idle"
    BUSY = "running"
    ERROR = "error"
    OFF = "off"


def get_system_status() -> SystemState:
    """
    Get the system status from the system_status table.

    Returns:
        dict: The system status.
    """
    result = execute_sql_command(
        """
                                 SELECT status FROM system_status
                                 ORDER BY status_time DESC
                                 LIMIT 1"""
    )
    return SystemState(result[0][0])


def set_system_status(
    status: SystemState, comment=None, test_mode=read_testing_config()
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
        (status.value, comment, test_mode),
    )


if __name__ == "__main__":
    # Process the well history CSV file into the well_hx table
    # process_well_hx_csv_into_table()

    # Test adding two of the same records to the queue table and see what the result looks like
    # try:
    #     execute_sql_command_no_return(
    #     "INSERT INTO queue (id, process_type, priority, filename) VALUES (1, 1, 1, 'test')"
    #     )
    #     returned = execute_sql_command(
    #         "INSERT INTO queue (id, process_type, priority, filename) VALUES (1, 1, 1, 'test')"
    #     )
    # except sqlite3.IntegrityError as e:
    #     returned = e

    # print(returned)

    # Test getting the system status from the system_status table
    (set_system_status(SystemState.IDLE, "Test", True))
    print(get_system_status())
    time.sleep(1)
    (set_system_status(SystemState.ERROR, "Test", True))
    time.sleep(1)
    print(get_system_status())
    (set_system_status(SystemState.IDLE, "Test", True))
    time.sleep(1)
    print(get_system_status())
