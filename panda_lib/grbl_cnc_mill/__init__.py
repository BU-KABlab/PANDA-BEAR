"""grbl_cnc_mill – GRBL CNC Mill Interfacing Library for Python 3.7+."""

VERSION = '1.0.0'
"""Version of grbl_cnc_mill."""

from .driver import Mill
from .exceptions import *
from .instruments import Instruments
from .mock import MockMill
from .status_codes import AlarmStatus, ErrorCodes, Status
