from decimal import Decimal

from epanda_lib.sql_tools.sql_utilities import (
    execute_sql_command,
    execute_sql_command_no_return,
)

# region Pipette


def select_pipette_status():
    """
    Get the pipette status from the pipette_status table.

    And return a pipette instance to be applied to the pipette that
    is in memory.

    Returns:
        Pipette: The current pipette status.

    """
    result = execute_sql_command(
        """
        SELECT 
        capacity_ul,
        capacity_ml,
        volume_ul  ,
        volume_ml  ,
        contents   
 
        FROM pipette_status
        ORDER BY updated DESC
        LIMIT 1
        """
    )
    if result == []:
        return None

    return result[0]


def insert_pipette_status(
    capacity_ul: Decimal,
    capacity_ml: Decimal,
    volume: Decimal,
    volume_ml: Decimal,
    contents: str,
):
    """
    Insert the pipette status into the pipette_status table.

    Args:
        pipette (Pipette): The pipette status to insert.
    """
    execute_sql_command_no_return(
        """
        INSERT INTO pipette (
            capacity_ul,
            capacity_ml,
            volume_ul,
            volume_ml,
            contents
            )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            capacity_ul,
            capacity_ml,
            volume,
            volume_ml,
            contents,
        ),
    )


# endregion
