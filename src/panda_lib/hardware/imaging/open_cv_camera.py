"""Module for controlling webcams using OpenCV"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Union

import cv2
import numpy as np

from .interface import CameraInterface


class OpenCVCamera(CameraInterface):
    """Class for controlling webcams using OpenCV"""

    def __init__(self, camera_id: int = 0, resolution: Tuple[int, int] = (1280, 720)):
        """Initialize the OpenCV camera.

        Args:
            camera_id: The ID of the camera to use (usually 0 for the first webcam)
            resolution: The resolution to capture images at (width, height)
        """
        self.camera_id = camera_id
        self.resolution = resolution
        self.camera = None
        self.logger = logging.getLogger("panda.webcam")

    def connect(self) -> bool:
        """Connect to the camera.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.camera = cv2.VideoCapture(self.camera_id)
            if not self.camera.isOpened():
                self.logger.error(f"Failed to open camera with ID {self.camera_id}")
                return False

            # Set resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])

            self.logger.info(
                f"Connected to webcam ID {self.camera_id} at resolution {self.resolution}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error connecting to webcam: {e}")
            return False

    def close(self) -> None:
        """Disconnect from the camera"""
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            self.logger.info("Disconnected from webcam")

    def __enter__(self) -> "OpenCVCamera":
        """Enter the context manager"""
        if not self.connect():
            raise RuntimeError("Failed to connect to webcam")
        return self
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the context manager"""
        self.close()

    def detect_camera(self) -> int:
        """Detect available cameras

        Returns:
            int: The number of cameras detected
        """
        camera_count = 0
        for i in range(10):
            camera = cv2.VideoCapture(i)
            if camera.isOpened():
                camera_count += 1
                camera.release()
        return camera_count

    def is_connected(self) -> bool:
        """Check if the camera is connected

        Returns:
            bool: True if connected, False otherwise
        """
        return self.camera is not None and self.camera.isOpened()

    def capture_image(self) -> Optional[np.ndarray]:
        """Capture a single image

        Returns:
            np.ndarray: The captured image, or None if capturing failed
        """
        if not self.is_connected():
            self.logger.error("Cannot capture image: Camera not connected")
            return None

        ret, frame = self.camera.read()
        if not ret:
            self.logger.error("Failed to capture image")
            return None

        return frame

    def save_image(self, image: np.ndarray, path: Union[str, Path]) -> bool:
        """Save an image to disk

        Args:
            image: The image to save
            path: The path to save the image to

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            path = Path(path) if isinstance(path, str) else path
            # Make sure the directory exists
            os.makedirs(path.parent, exist_ok=True)
            # Save the image
            cv2.imwrite(str(path), image)
            self.logger.info(f"Image saved to {path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving image: {e}")
            return False

    def capture_and_save(self, path: Union[str, Path]) -> Tuple[Path, bool]:
        """Capture an image and save it to disk

        Args:
            path: The path to save the image to

        Returns:
            Tuple[Path, bool]: The path of the saved image and a boolean indicating success
        """
        path = Path(path) if isinstance(path, str) else path
        image = self.capture_image()
        if image is None:
            return path, False
        success = self.save_image(image, path)
        return path, success


class MockOpenCVCamera(CameraInterface):
    """Mock OpenCV camera for testing"""

    def __init__(self, camera_id: int = 0, resolution: Tuple[int, int] = (1280, 720)):
        """Initialize the mock camera"""
        self.camera_id = camera_id
        self.resolution = resolution
        self.connected = False
        self.logger = logging.getLogger("panda.webcam")

    def connect(self) -> bool:
        """Connect to the mock camera"""
        self.connected = True
        self.logger.info(f"Connected to mock webcam ID {self.camera_id}")
        return True

    def close(self) -> None:
        """Disconnect from the mock camera"""
        self.connected = False
        self.logger.info("Disconnected from mock webcam")

    def is_connected(self) -> bool:
        """Check if the mock camera is connected"""
        return self.connected

    def capture_image(self) -> Optional[np.ndarray]:
        """Capture a mock image (black frame with text)"""
        if not self.is_connected():
            self.logger.error("Cannot capture image: Mock camera not connected")
            return None

        # Create a black image
        image = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)

        # Add text
        cv2.putText(
            image,
            f"MOCK WEBCAM ID {self.camera_id}",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            image,
            f"Time: {datetime.now().strftime('%H:%M:%S')}",
            (50, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            image,
            "This is a simulated camera image for testing",
            (50, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            1,
        )

        # Add border
        cv2.rectangle(
            image,
            (10, 10),
            (self.resolution[0] - 10, self.resolution[1] - 10),
            (255, 255, 255),
            2,
        )

        return image

    def save_image(self, image: np.ndarray, path: Union[str, Path]) -> bool:
        """Save a mock image to disk"""
        try:
            path = Path(path) if isinstance(path, str) else path
            # Make sure the directory exists
            os.makedirs(path.parent, exist_ok=True)
            # Save the image
            cv2.imwrite(str(path), image)
            self.logger.info(f"Mock image saved to {path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving mock image: {e}")
            return False

    def capture_and_save(self, path: Union[str, Path]) -> Tuple[Path, bool]:
        """Capture a mock image and save it to disk"""
        path = Path(path) if isinstance(path, str) else path
        image = self.capture_image()
        if image is None:
            return path, False
        success = self.save_image(image, path)
        return path, success
