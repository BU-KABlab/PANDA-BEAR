"""Utility functions for working with different camera types"""

import logging
import os
from typing import Optional, Tuple, Union

import numpy as np
import PySpin

from panda_lib.imaging.open_cv_camera import MockOpenCVCamera, OpenCVCamera
from shared_utilities.config.config_tools import read_camera_type, read_webcam_settings


def capture_image_flir(camera: PySpin.Camera) -> Optional[np.ndarray]:
    """Capture an image from a FLIR camera

    Args:
        camera: The FLIR camera to capture from

    Returns:
        np.ndarray: The captured image, or None if failed
    """
    logger = logging.getLogger("panda.camera")

    if camera is None:
        logger.error("Cannot capture image: FLIR camera not initialized")
        return None

    try:
        # Initialize camera
        camera.Init()

        # Acquire and retrieve image
        camera.BeginAcquisition()
        image_result = camera.GetNextImage()

        if image_result.IsIncomplete():
            logger.error(f"Image incomplete: {image_result.GetImageStatus()}")
            image_result.Release()
            camera.EndAcquisition()
            camera.DeInit()
            return None

        # Convert image
        converted_image = image_result.Convert(PySpin.PixelFormat_BGR8)
        image_data = converted_image.GetNDArray()

        # Clean up
        image_result.Release()
        camera.EndAcquisition()
        camera.DeInit()

        return image_data
    except PySpin.SpinnakerException as ex:
        logger.error(f"Error capturing image from FLIR camera: {ex}")
        return None


def setup_camera(
    use_mock: bool = False,
) -> Tuple[Union[PySpin.Camera, OpenCVCamera, MockOpenCVCamera, None], str]:
    """Set up the appropriate camera based on configuration

    Args:
        use_mock: Whether to use mock cameras

    Returns:
        tuple: (camera_object, camera_type)
    """
    logger = logging.getLogger("panda.camera")
    camera_type = read_camera_type().lower()

    if camera_type == "webcam":
        webcam_id, resolution = read_webcam_settings()

        if use_mock:
            camera = MockOpenCVCamera(camera_id=webcam_id, resolution=resolution)
        else:
            camera = OpenCVCamera(camera_id=webcam_id, resolution=resolution)

        if not camera.connect():
            logger.error(f"Failed to connect to webcam with ID {webcam_id}")
            return None, camera_type

        return camera, camera_type
    else:
        # Default to FLIR camera
        if use_mock:
            # No mock implementation for FLIR yet
            logger.warning("No mock implementation for FLIR camera")
            return None, camera_type

        try:
            system = PySpin.System.GetInstance()
            cam_list = system.GetCameras()

            if cam_list.GetSize() == 0:
                logger.error("No FLIR Camera found")
                return None, camera_type

            camera = cam_list.GetByIndex(0)
            cam_list.Clear()

            return camera, camera_type
        except Exception as e:
            logger.error(f"Error setting up FLIR camera: {e}")
            return None, camera_type


def capture_image(
    camera: Union[PySpin.Camera, OpenCVCamera, MockOpenCVCamera], camera_type: str
) -> Optional[np.ndarray]:
    """Capture an image from either camera type

    Args:
        camera: The camera object
        camera_type: The type of camera ('flir' or 'webcam')

    Returns:
        np.ndarray: The captured image, or None if failed
    """
    if camera is None:
        return None

    if camera_type.lower() == "webcam":
        return camera.capture_image()
    else:
        return capture_image_flir(camera)


def save_image(
    image: np.ndarray,
    path: str,
    camera: Union[OpenCVCamera, MockOpenCVCamera, None] = None,
    camera_type: str = "",
) -> bool:
    """Save an image to disk

    Args:
        image: The image to save
        path: The path to save the image to
        camera: The camera object (only needed for webcam)
        camera_type: The type of camera ('flir' or 'webcam')

    Returns:
        bool: True if successful, False otherwise
    """
    logger = logging.getLogger("panda.camera")

    if image is None:
        logger.error("Cannot save image: No image data")
        return False

    try:
        # If webcam and camera object provided, use its save method
        if camera_type.lower() == "webcam" and camera is not None:
            return camera.save_image(image, path)

        # Otherwise use generic approach
        os.makedirs(os.path.dirname(path), exist_ok=True)
        import cv2

        cv2.imwrite(path, image)
        logger.info(f"Image saved to {path}")
        return True
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return False


def capture_and_save(
    camera: Union[PySpin.Camera, OpenCVCamera, MockOpenCVCamera],
    camera_type: str,
    path: str,
) -> bool:
    """Capture an image and save it to disk

    Args:
        camera: The camera object
        camera_type: The type of camera ('flir' or 'webcam')
        path: Path to save the image to

    Returns:
        bool: True if successful, False otherwise
    """
    # For webcams, use the built-in method if available
    if camera_type.lower() == "webcam":
        return camera.capture_and_save(path)

    # For FLIR or other cameras, use the separate functions
    image = capture_image(camera, camera_type)
    if image is None:
        return False

    return save_image(image, path, camera, camera_type)
