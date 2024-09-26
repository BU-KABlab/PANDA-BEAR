"""
Reading and writing the system state to the database.
"""

import datetime

from pytz import utc
from panda_lib.config.config_tools import read_config
from panda_lib.utilities import SystemState
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import SystemStatus, SystemVersions

# from panda_lib.sql_tools.sql_utilities import execute_sql_command, execute_sql_command_no_return

# region System State
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

# def get_current_pin() -> int:
#     """
#     Get the current pin from the system_status table.

#     Returns:
#         int: The current pin.
#     """
#     result = execute_sql_command(
#         """
#         SELECT pin
#         FROM system_versions
#         WHERE id = (SELECT MAX(id) FROM system_versions)
#         """
#         )
#     if result == []:
#         return None
#     result = str(result[0][0]).replace(" ", "")
#     return str(int(result))

# def select_system_status(look_back:int = 1) -> SystemState:
#     """
#     Get the system status from the system_status table.

#     Returns:
#         dict: The system status.
#     """
#     result = execute_sql_command(
#         """
#         SELECT status FROM system_status
#         ORDER BY status_time DESC
#         LIMIT ?
#         """, (look_back,)
#     )
#     if result == []:
#         return SystemState("off")

#     if look_back == 1:
#         return SystemState(result[0][0])
#     else:
#         return [SystemState(row[0]) for row in result]

# def set_system_status(
#     system_status: SystemState, comment=None, test_mode=config_tools.read_testing_config()
# ) -> None:
#     """
#     Set the system status in the system_status table.

#     Args:
#         status (SystemState): The system status to set.
#     """
#     execute_sql_command_no_return(
#         """
#         INSERT INTO system_status (status, comment, test_mode)
#         VALUES (?, ?, ?)
#         """,
#         (system_status.value, comment, test_mode),
#     )

config = read_config()

TESTING = config.getboolean("OPTIONS", "testing")


def get_current_pin() -> int:
    """
    Get the current pin from the system_status table.

    Returns:
        int: The current pin.
    """
    with SessionLocal() as session:
        # result = session.execute(
        #     "SELECT pin FROM system_status ORDER BY status_time DESC LIMIT 1"
        # )
        # for row in result:
        #     return row[0]

        result = (
            session.query(SystemVersions.pin)
            .order_by(SystemVersions.id.desc())
            .limit(1)
            .all()
        )

        return result[0][0] if result else None


def select_system_status(look_back: int = 1) -> SystemState:
    """
    Get the system status from the system_status table.

    Returns:
        dict: The system status.
    """
    with SessionLocal() as session:
        result = (
            session.query(SystemStatus.status)
            .order_by(SystemStatus.id.desc())
            .limit(look_back)
            .all()
        )
        return [SystemState(row[0]) for row in result]


def set_system_status(
    system_status: SystemState, comment=None, test_mode=TESTING
) -> None:
    """
    Set the system status in the system_status table.

    Args:
        status (SystemState): The system status to set.
    """
    with SessionLocal() as session:
        session.add(
            SystemStatus(
                status=system_status.value, comment=comment, status_time=datetime.datetime.now(tz= utc)  ,test_mode=test_mode
            )
        )
        session.commit()


# endregion
