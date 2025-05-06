"""Utility functions for working with different camera types"""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np

from .camera_factory import CameraFactory, CameraType
from .interface import CameraInterface
from shared_utilities.config.config_tools import read_camera_type, read_webcam_settings

# Check if PySpin is available
try:
    import PySpin
    PYSPIN_AVAILABLE = True
except ImportError:
    PYSPIN_AVAILABLE = False


def capture_image_flir(camera: 'PySpin.Camera') -> Optional[np.ndarray]:
    """Capture an image from a FLIR camera

    Args:
        camera: The FLIR camera to capture from

    Returns:
        np.ndarray: The captured image, or None if failed
    """
    if not PYSPIN_AVAILABLE:
        logging.getLogger("panda.camera").error("PySpin library not available")
        return None
        
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
    except Exception as ex:
        logger.error(f"Error capturing image from FLIR camera: {ex}")
        return None


def setup_camera(
    use_mock: bool = False,
) -> Tuple[Union[CameraInterface, None], str]:
    """Set up the appropriate camera based on configuration

    Args:
        use_mock: Whether to use mock cameras

    Returns:
        tuple: (camera_object, camera_type)
    """
    logger = logging.getLogger("panda.camera")
    config_camera_type = read_camera_type().lower()
    
    # Map configuration camera type to CameraType enum
    if config_camera_type == "webcam":
        camera_type_enum = CameraType.OPENCV
    elif config_camera_type == "flir":
        camera_type_enum = CameraType.FLIR
    else:
        # Default to OpenCV
        logger.warning(f"Unknown camera type '{config_camera_type}', defaulting to OpenCV")
        camera_type_enum = CameraType.OPENCV
        config_camera_type = "webcam"
    
    # Use the mock camera if requested
    if use_mock:
        camera_type_enum = CameraType.MOCK
    
    # Create camera based on type
    if camera_type_enum == CameraType.OPENCV or camera_type_enum == CameraType.MOCK:
        webcam_id, resolution = read_webcam_settings()
        camera = CameraFactory.create_camera(
            camera_type=camera_type_enum, 
            camera_id=webcam_id, 
            resolution=resolution
        )
    else:  # FLIR camera
        camera = CameraFactory.create_camera(camera_type=camera_type_enum)
        
        # If FLIR camera creation failed, fallback to OpenCV
        if camera is None:
            logger.warning("Failed to create FLIR camera, falling back to OpenCV")
            webcam_id, resolution = read_webcam_settings()
            camera = CameraFactory.create_camera(
                camera_type=CameraType.OPENCV,
                camera_id=webcam_id,
                resolution=resolution
            )
            config_camera_type = "webcam"
    
    # Connect to the camera
    if camera is not None and not camera.connect():
        logger.error("Failed to connect to camera")
        return None, config_camera_type
    
    return camera, config_camera_type


def capture_image(
    camera: CameraInterface, camera_type: str
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
    
    return camera.capture_image()


def save_image(
    image: np.ndarray,
    path: Union[str, Path],
    camera: Optional[CameraInterface] = None,
    camera_type: str = "",
) -> bool:
    """Save an image to disk

    Args:
        image: The image to save
        path: The path to save the image to
        camera: The camera object
        camera_type: The type of camera ('flir' or 'webcam')

    Returns:
        bool: True if successful, False otherwise
    """
    logger = logging.getLogger("panda.camera")

    if image is None:
        logger.error("Cannot save image: No image data")
        return False

    try:
        path = Path(path) if isinstance(path, str) else path
        
        # If camera object provided, use its save method
        if camera is not None:
            return camera.save_image(image, path)

        # Otherwise use generic approach
        os.makedirs(path.parent, exist_ok=True)
        import cv2
        cv2.imwrite(str(path), image)
        logger.info(f"Image saved to {path}")
        return True
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return False


def capture_and_save(
    camera: CameraInterface,
    camera_type: str,
    path: Union[str, Path],
) -> Tuple[Path, bool]:
    """Capture an image and save it to disk

    Args:
        camera: The camera object
        camera_type: The type of camera ('flir' or 'webcam')
        path: Path to save the image to

    Returns:
        Tuple[Path, bool]: The path of the saved image and a boolean indicating success
    """
    path = Path(path) if isinstance(path, str) else path
    
    if camera is None:
        return path, False
    
    return camera.capture_and_save(path)
