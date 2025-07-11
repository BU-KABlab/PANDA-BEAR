# panda_lib/hardware/imaging/flir_camera.py
"""
FLIR camera implementation using PySpin.
This module provides a wrapper around the PySpin library for FLIR cameras.
It uses openCV for image saving and numpy for image handling due to PySpin's unreliability and crashing.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Union

from .interface import CameraInterface
from .flir_camera_tools import file_enumeration

# Try to import PySpin, but make it optional
try:
    import PySpin  # PySpin only works with Python <=3.10
    import cv2
    import numpy as np
    PYSPIN_AVAILABLE = True
except ImportError:
    PYSPIN_AVAILABLE = False


class FlirCamera(CameraInterface):
    """
    Implementation of CameraInterface for FLIR cameras using PySpin
    """

    @staticmethod
    def is_available() -> bool:
        """Check if PySpin is available

        Returns:
            bool: True if PySpin is available, False otherwise
        """
        return PYSPIN_AVAILABLE

    def __init__(self, camera_id: int = 0):
        """Initialize FLIR camera

        Args:
            camera_id: The ID of the camera to use

        Raises:
            ImportError: If PySpin is not available
        """
        if not PYSPIN_AVAILABLE:
            raise ImportError("PySpin library is required for FLIR camera support")

        self.camera_id = camera_id
        self.logger = logging.getLogger("panda.flir_camera")
        self.system = None
        self.camera_list = None
        self.camera = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to the FLIR camera

        Returns:
            bool: True if connection successful, False otherwise
        """
        if not PYSPIN_AVAILABLE:
            self.logger.error("PySpin library not available")
            return False

        try:
            self.system = PySpin.System.GetInstance()
            self.camera_list = self.system.GetCameras()

            if self.camera_list.GetSize() == 0:
                self.logger.error("No FLIR cameras found")
                return False

            if self.camera_id < self.camera_list.GetSize():
                self.camera = self.camera_list[self.camera_id]
            else:
                self.logger.warning(
                    f"Camera ID {self.camera_id} out of range, using first camera"
                )
                self.camera = self.camera_list[0]

            self.camera.Init()
            self.connected = True
            self.logger.info(f"Connected to FLIR camera ID {self.camera_id}")
            return True

        except PySpin.SpinnakerException as ex:
            self.logger.error(f"Error connecting to FLIR camera: {ex}")
            return False

    def close(self) -> None:
        """Disconnect from the FLIR camera"""
        if not PYSPIN_AVAILABLE or not self.connected:
            return

        try:
            if self.camera is not None:
                self.camera.DeInit()
                self.camera = None

            if self.camera_list is not None:
                self.camera_list.Clear()
                self.camera_list = None

            if self.system is not None:
                self.system.ReleaseInstance()
                self.system = None

            self.connected = False
            self.logger.info("Disconnected from FLIR camera")

        except PySpin.SpinnakerException as ex:
            self.logger.error(f"Error disconnecting from FLIR camera: {ex}")

    def is_connected(self) -> bool:
        """Check if the FLIR camera is connected

        Returns:
            bool: True if connected, False otherwise
        """
        return self.connected and self.camera is not None

    def capture_image(self) -> Optional[np.ndarray]:
        """Capture a single image from the FLIR camera using RGB8 color processing"""
        if not PYSPIN_AVAILABLE or not self.is_connected():
            self.logger.error("Cannot capture image: Camera not connected")
            return None


        try:
            nodemap = self.camera.GetNodeMap()
            pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode("PixelFormat"))
            if PySpin.IsAvailable(pixel_format) and PySpin.IsWritable(pixel_format):
                rgb8_entry = pixel_format.GetEntryByName("RGB8")
                if rgb8_entry and PySpin.IsAvailable(rgb8_entry):
                    pixel_format.SetIntValue(rgb8_entry.GetValue())
                    self.logger.info("Set camera to RGB8 format - using built-in color processing")

            self.camera.BeginAcquisition()
            image_result = self.camera.GetNextImage(1000)

            if image_result.IsIncomplete():
                self.logger.error(
                    f"Image incomplete with status {image_result.GetImageStatus()}"
                )
                image_result.Release()
                self.camera.EndAcquisition()
                return None

            image_data = image_result.GetNDArray()
            image_result.Release()
            self.camera.EndAcquisition()

            return image_data

        except PySpin.SpinnakerException as ex:
            self.logger.error(f"Error capturing image from FLIR camera: {ex}")
            try:
                self.camera.EndAcquisition()
            except:
                pass
            return None

    def save_image(self, image: np.ndarray, path: Union[str, Path]) -> bool:
        """Save an image to disk


        Args:
            image: The image to save
            path: The path to save the image to


        Returns:
            bool: True if successful, False otherwise
        """
        if not PYSPIN_AVAILABLE:
            self.logger.error("PySpin library not available")
            return False


        try:
            path = Path(path) if isinstance(path, str) else path
            path.parent.mkdir(parents=True, exist_ok=True)

            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(path), image_bgr)
            self.logger.info(f"Image saved with OpenCV to {path}")
            return True

        except Exception as ex:
            self.logger.error(f"Error saving image from FLIR camera: {ex}")
            return False


    def capture_and_save(self, path: Union[str, Path]) -> Tuple[Path, bool]:
        """Capture an image and save it to disk


        Args:
            path: The path to save the image to


        Returns:
            Tuple[Path, bool]: The path of the saved image and a boolean indicating success
        """
        if not PYSPIN_AVAILABLE:
            self.logger.error("PySpin library not available")
            return Path(path), False


        path = Path(path) if isinstance(path, str) else path
        path = file_enumeration(path)

        if not self.is_connected():
            self.logger.error("Cannot capture image: Camera not connected")
            return path, False

        image = self.capture_image()
        if image is not None:
            success = self.save_image(image, path)
            return path, success
        else:
            return path, False
