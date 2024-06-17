"""grbl_cnc_mill – GRBL CNC Mill Interfacing Library for Python 3.7+."""

VERSION = '1.0.0'
"""Version of grbl_cnc_mill."""

from .instruments import Instruments
from .driver import Mill
from .mock import MockMill
from .states_codes import Status, AlarmStatus, ErrorCodes
from .exceptions import *
