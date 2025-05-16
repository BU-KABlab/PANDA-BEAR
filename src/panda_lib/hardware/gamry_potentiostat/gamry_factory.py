"""Factory for creating Gamry potentiostat instances."""

import logging
import sys
from typing import Union

from .errors import GamryPlatformError
from .gamry_control_mock import GamryPotentiostat

logger = logging.getLogger("panda")


class GamryFactory:
    """Factory for creating Gamry potentiostat instances."""

    @staticmethod
    def create_potentiostat(
        force_mock: bool = False,
    ) -> Union["GamryPotentiostat", object]:
        """Create a potentiostat instance.

        Args:
            force_mock: Force using mock implementation even on Windows

        Returns:
            A potentiostat instance (either real or mock)

        Raises:
            GamryPlatformError: If not on Windows and mock is not forced
        """
        if sys.platform != "win32" and not force_mock:
            logger.error(
                "Attempted to use real Gamry implementation on non-Windows platform"
            )
            raise GamryPlatformError(
                "Gamry potentiostats are only supported on Windows platforms. "
                f"Current platform: {sys.platform}. Use force_mock=True for testing."
            )

        if sys.platform == "win32" and not force_mock:
            try:
                # Use context manager for real implementation to ensure proper cleanup
                from .gamry_adapter import GamryAdapter

                logger.info("Creating real Gamry potentiostat instance")
                return GamryAdapter()
            except ImportError as e:
                logger.warning(
                    f"Failed to import Gamry module: {e}. Using mock implementation."
                )
                force_mock = True

        # Use mock implementation
        from .gamry_control_mock import GamryPotentiostat

        logger.info("Creating mock Gamry potentiostat instance")
        return GamryPotentiostat()
