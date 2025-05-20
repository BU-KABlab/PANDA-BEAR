"""
Factory class for creating camera instances based on camera type.
"""

import logging
from enum import Enum, auto
from typing import Optional, Union

from .interface import CameraInterface
from .open_cv_camera import OpenCVCamera, MockOpenCVCamera

# Logger for the camera factory
logger = logging.getLogger("panda.camera_factory")


class CameraType(Enum):
    """Enum for camera types"""

    OPENCV = auto()
    FLIR = auto()
    MOCK = auto()


class CameraFactory:
    """Factory for creating camera instances"""

    @staticmethod
    def create_camera(
        camera_type: Union[str, CameraType] = CameraType.OPENCV, **kwargs
    ) -> Optional[CameraInterface]:
        """Create a camera instance based on camera type

        Args:
            camera_type: The type of camera to create (OPENCV, FLIR, or MOCK)
            **kwargs: Additional arguments to pass to the camera constructor

        Returns:
            CameraInterface: The camera instance, or None if creation failed
        """
        # Convert string to enum if needed
        if isinstance(camera_type, str):
            try:
                camera_type = CameraType[camera_type.upper()]
            except KeyError:
                logger.error(f"Invalid camera type: {camera_type}")
                return None

        if camera_type == CameraType.OPENCV:
            logger.info("Creating OpenCV camera")
            return OpenCVCamera(**kwargs)

        elif camera_type == CameraType.FLIR:
            # Import FlirCamera here to avoid circular imports
            from .flir_camera import FlirCamera, PYSPIN_AVAILABLE

            if not PYSPIN_AVAILABLE:
                logger.warning("PySpin not available, falling back to OpenCV camera")
                return OpenCVCamera(**kwargs)

            logger.info("Creating FLIR camera")
            return FlirCamera(**kwargs)

        elif camera_type == CameraType.MOCK:
            logger.info("Creating mock camera")
            return MockOpenCVCamera(**kwargs)

        else:
            logger.error(f"Unknown camera type: {camera_type}")
            return None
