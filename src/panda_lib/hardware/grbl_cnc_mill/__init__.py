"""grbl_cnc_mill – GRBL CNC Mill Interfacing Library for Python 3.7+."""

import os

from .driver import Mill
from .exceptions import (
    CNCMillException,
    CommandExecutionError,
    LocationNotFound,
    MillConfigError,
    MillConfigNotFound,
    MillConnectionError,
    StatusReturnError,
)
from .logger import set_up_mill_logger
from .mock import MockMill
from .status_codes import AlarmStatus, ErrorCodes, Status
from .tools import Coordinates, Instruments, ToolManager, ToolOffset, Tools

VERSION = "1.0.0"  # Version of grbl_cnc_mill

__all__ = [
    "Mill",
    "MockMill",
    "AlarmStatus",
    "Coordinates",
    "ErrorCodes",
    "Instruments",
    "Status",
    "ToolManager",
    "ToolOffset",
    "Tools",
    "set_up_mill_logger",
    "CNCMillException",
    "CommandExecutionError",
    "LocationNotFound",
    "MillConfigError",
    "MillConfigNotFound",
    "MillConnectionError",
    "StatusReturnError",
    "VERSION",
]

# Set up non-tracked files
files_to_make = ["_configuration.json", "mill_port.txt"]

# Get the directory where the package is installed
package_dir = os.path.dirname(__file__)

# Create the files if they do not exist
for file in files_to_make:
    file_path = os.path.join(package_dir, file)
    # Check if the file exists
    if not os.path.exists(file_path):
        # Create the file
        with open(file_path, "w") as new_file:
            new_file.write("")
