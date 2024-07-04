"""
SQL Utilities for the PANDA_SDL project

This module contains utility functions for executing SQL commands on the database.

"""

from configparser import ConfigParser
import logging
import sqlite3
from decimal import Decimal

from panda_lib.log_tools import setup_default_logger

logger: logging.Logger = setup_default_logger(log_name="sql_logger")
config = ConfigParser()
config.read("panda_lib/config/panda_sdl_config.ini")

if config.getboolean("OPTIONS", "TESTING"):
    SQL_DB_ADDR = config.get("PATHS_TESTING", "testing_db_address")
    LOCAL_REPO_PATH = config.get("PATHS_GENERAL", "local_dir")
else:
    SQL_DB_ADDR = config.get("PATHS_PRODUCTION", "production_db_address")
    LOCAL_REPO_PATH = config.get("PATHS_GENERAL", "local_dir")

# region Utility Functions
def execute_sql_command(
    sql_command: str, parameters: tuple = None
) -> list:
    """
    Execute an SQL command on the database.

    Args:
        sql_command (str): The SQL command to execute.
        parameters (tuple): The parameters for the SQL command.

    Returns:
        List: The result of the SQL command.
    """
    conn = sqlite3.connect(SQL_DB_ADDR)

    conn.isolation_level = None  # Manually control transactions
    cursor = conn.cursor()

    cursor.execute("BEGIN TRANSACTION")  # Start a new transaction

    try:
        # Log the SQL command
        logger.debug("Executing SQL command: %s", sql_command)
        logger.debug("Parameters: %s", parameters)
        # Execute the SQL command
        if parameters:
            if isinstance(parameters[0], tuple):
                parameters = convert_decimals(parameters)
                cursor.executemany(sql_command, parameters)
            else:
                parameters = convert_decimals(parameters)
                cursor.execute(sql_command, parameters)
        else:
            cursor.execute(sql_command)
        result = cursor.fetchall()

        conn.commit()

        # Log the result
        logger.debug("SQL command executed successfully. Result: %s", result)
    except sqlite3.Error as e:
        logger.error("An error occurred: %s", e)
        logger.error("SQL command: %s", sql_command)
        logger.error("Parameters: %s", parameters)
        conn.rollback()  # Rollback the transaction if error
        raise e
    finally:
        conn.close()

    # time.sleep(1)

    return result


def execute_sql_command_no_return(
    sql_command: str, parameters: tuple = None
) -> None:
    """
    Execute an SQL command on the database without returning anything.

    Args:
        sql_command (str): The SQL command to execute.
        parameters (tuple): The parameters for the SQL command.
    """
    if sql_command is None:
        return

    conn = sqlite3.connect(SQL_DB_ADDR)

    # Manually control transactions
    conn.isolation_level = None

    cursor = conn.cursor()

    # Start a new transaction
    cursor.execute("BEGIN TRANSACTION")

    try:
        # Execute the SQL command

        # Log the SQL command
        logger.debug("Executing SQL command: %s", sql_command)
        logger.debug("Parameters: %s", parameters)

        if parameters:
            parameters = convert_decimals(parameters)

            if isinstance(parameters[0], tuple):
                cursor.executemany(sql_command, parameters)
            else:
                cursor.execute(sql_command, parameters)
        else:
            cursor.execute(sql_command)
        result = cursor.fetchall()
        # Commit the transaction
        conn.commit()

        # Log the result
        logger.debug("SQL command executed successfully.")
        logger.debug("Result: %s", result)
    except Exception as e:
        logger.error("An error occurred: %s", e)
        logger.error("SQL command: %s", sql_command)
        logger.error("Parameters: %s", parameters)
        # Rollback the transaction on error
        conn.rollback()
        raise e
    finally:
        # Close the connection
        conn.close()

    # time.sleep(1)


def convert_decimals(parameters):
    """
    Convert Decimal objects to floats in a list of parameters.

    Args:
        parameters (list): The list of parameters.

    Returns:
        list: The list of parameters with Decimal objects converted to floats.
    """
    new_parameters = []
    if isinstance(parameters[0], tuple):
        for parameter in parameters:
            new_parameter = []
            for item in parameter:
                if isinstance(item, Decimal):
                    new_parameter.append(float(item))
                else:
                    new_parameter.append(item)
            new_parameters.append(tuple(new_parameter))
    else:
        for item in parameters:
            if isinstance(item, Decimal):
                new_parameters.append(float(item))
            else:
                new_parameters.append(item)
    return new_parameters
