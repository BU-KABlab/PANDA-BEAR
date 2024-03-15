"""A 'driver' for connecting to the project SQL database and executing SQL commands. """

import sqlite3
from typing import List
from epanda_lib.config.config import SQL_DB_PATH


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
    cursor = conn.cursor()

    # Execute the SQL command
    if parameters:
        cursor.execute(sql_command, parameters)
    else:
        cursor.execute(sql_command)
    result = cursor.fetchall()

    conn.close()

    return result


def execute_sql_command_no_return(sql_command: str, parameters: tuple = None) -> None:
    """
    Execute an SQL command on the database without returning anything.

    Args:
        sql_command (str): The SQL command to execute.
        parameters (tuple): The parameters for the SQL command.
    """
    conn = sqlite3.connect(SQL_DB_PATH)
    cursor = conn.cursor()

    # Execute the SQL command
    if parameters:
        cursor.execute(sql_command, parameters)
    else:
        cursor.execute(sql_command)

    conn.commit()
    conn.close()


class ResultTableEntry:
    """
    A class for representing a single entry in a result table.
    The table has columns:
    id,
    experiment_id,
    result_type,
    result_value
    """

    def __init__(
        self,
        experiment_id: int,
        result_type: str,
        result_value: str,
    ):
        self.experiment_id = experiment_id
        self.result_type = result_type
        self.result_value = result_value

    def __str__(self):
        return f"Experiment ID: {self.experiment_id}, Result Type: {self.result_type}, Result Value: {self.result_value}"

    def __repr__(self):
        return f"ResultTableEntry({self.experiment_id}, {self.result_type}, {self.result_value})"

    def sql_statement(self) -> str:
        """
        Get the SQL statement for inserting the entry into the result table.

        Returns:
            str: The SQL statement.
        """
        return f"INSERT INTO result (experiment_id, result_type, result_value) VALUES ({self.experiment_id}, '{self.result_type}', '{self.result_value}')"


def insert_result_table_entry(entry: ResultTableEntry) -> None:
    """
    Insert an entry into the result table.

    Args:
        entry (ResultTableEntry): The entry to insert.
    """
    execute_sql_command_no_return(entry.sql_statement())


def add_result_type(result_type: str) -> None:
    """
    Add a result type to the result_types table.

    Args:
        result_type (str): The result type to add.
    """
    execute_sql_command_no_return(
        f"INSERT INTO result_type (result_type) VALUES ('{result_type}')"
    )
