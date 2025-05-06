"""Gamry Potentiostat interface package.

This package provides an interface to Gamry potentiostats.
It includes both a real implementation for Windows platforms
and a mock implementation for testing on non-Windows platforms.
"""

import logging
import sys
from typing import Type, Union

from .errors import GamryCOMError, GamryError, GamryPlatformError
from .gamry_adapter import GamryAdapter

logger = logging.getLogger("panda")

# Determine which implementation to use based on platform
if sys.platform == "win32":
    try:
        from .gamry_control import (
            OCP,
            activecheck,
            check_vf_range,
            chrono,
            chrono_parameters,
            cv_parameters,
            cyclic,
            initializepstat,
            potentiostat_ocp_parameters,
            pstatconnect,
            pstatdisconnect,
            setfilename,
        )

        MOCK_MODE = False
    except ImportError as e:
        logger.warning(
            f"Failed to import Gamry control module: {e}. Using mock implementation."
        )
        from .gamry_control_mock import (
            GamryPotentiostat,
            chrono_parameters,
            cv_parameters,
            potentiostat_ocp_parameters,
        )

        MOCK_MODE = True
else:
    logger.info("Non-Windows platform detected. Using mock Gamry implementation.")
    from .gamry_control_mock import (
        GamryPotentiostat,
        chrono_parameters,
        cv_parameters,
        potentiostat_ocp_parameters,
    )

    MOCK_MODE = True


def get_potentiostat() -> Union["GamryPotentiostat", Type]:
    """Get the appropriate potentiostat implementation.

    Returns:
        GamryPotentiostat or functions from gamry_control

    Raises:
        GamryPlatformError: If not running on Windows and mock mode is disabled
    """
    if MOCK_MODE:
        return GamryPotentiostat()
    else:
        # Return the module itself for the real implementation
        # Users will call individual functions
        return sys.modules[__name__]


__all__ = [
    "get_potentiostat",
    "GamryError",
    "GamryCOMError",
    "GamryPlatformError",
    "cv_parameters",
    "chrono_parameters",
    "potentiostat_ocp_parameters",
    "OCP",
    "activecheck",
    "check_vf_range",
    "chrono",
    "cyclic",
    "initializepstat",
    "pstatconnect",
    "pstatdisconnect",
    "setfilename",
    "GamryAdapter",
    "GamryPotentiostat",
    "MOCK_MODE",
    "logger",
]
