"""Adapter for Gamry potentiostat implementation."""

import logging
import pathlib
from typing import Tuple

from .errors import check_platform_compatibility
from .gamry_control import (
    OCP,
    activecheck,
    check_vf_range,
    chrono,
    cyclic,
    pstatconnect,
    pstatdisconnect,
    setfilename,
)

logger = logging.getLogger("panda")


class GamryAdapter:
    """Adapter for the function-based Gamry implementation."""

    def __init__(self):
        """Initialize the adapter."""
        check_platform_compatibility()
        self.connected = False
        self.complete_file_name = None

    def connect(self) -> bool:
        """Connect to the potentiostat.

        Returns:
            bool: True if connection was successful
        """
        try:
            self.connected = pstatconnect()
            return self.connected
        except Exception as e:
            logger.error(f"Failed to connect to potentiostat: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from the potentiostat."""
        if self.connected:
            try:
                pstatdisconnect()
                self.connected = False
            except Exception as e:
                logger.error(f"Error disconnecting from potentiostat: {e}")
                raise

    def setfilename(self, *args, **kwargs) -> pathlib.Path:
        """Set the filename for data storage."""
        self.complete_file_name = setfilename(*args, **kwargs)
        return self.complete_file_name

    def OCP(self, ocp_params) -> None:
        """Run open circuit potential measurement."""
        OCP(ocp_params.OCPvi, ocp_params.OCPti, ocp_params.OCPrate)

    def activecheck(self) -> None:
        """Check if experiment is active."""
        return activecheck()

    def check_vf_range(self, filename) -> Tuple[bool, float]:
        """Check Vf range."""
        return check_vf_range(filename)

    def cyclic(self, cv_params) -> None:
        """Run cyclic voltammetry."""
        cyclic(cv_params)

    def chrono(self, chrono_params) -> None:
        """Run chronoamperometry."""
        chrono(chrono_params)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
