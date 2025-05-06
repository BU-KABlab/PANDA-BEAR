"""
This module is used to capture images from cameras.
Supports OpenCV cameras by default, with optional support for FLIR cameras via PySpin.
"""

import logging
from logging import Logger
from pathlib import Path
from typing import Optional, Tuple, Union

# Import shared tools
from .flir_camera_tools import (
    file_enumeration,
    image_filepath_generator,
)
from .panda_image_tools import add_data_zone, invert_image
from .camera_factory import CameraFactory, CameraType

__all__ = [
    "add_data_zone",
    "capture_new_image",
    "file_enumeration",
    "image_filepath_generator",
    "invert_image",
    "CameraFactory",
    "CameraType",
]

default_logger = logging.getLogger("panda")


def capture_new_image(
    save=True,
    num_images=1,
    file_name: Union[str, Path] = Path("images/test.tiff"),
    logger: Optional[Logger] = default_logger,
    camera_type: Union[str, CameraType] = CameraType.OPENCV,
    camera_id: int = 0,
) -> Tuple[Path, bool]:
    """Capture a new image from a camera
    
    Args:
        save: Whether to save the image
        num_images: Number of images to capture (only used for FLIR cameras)
        file_name: Path to save the image to
        logger: Logger to use
        camera_type: Type of camera to use (OPENCV, FLIR, or MOCK)
        camera_id: ID of the camera to use
        
    Returns:
        Tuple[Path, bool]: Path to the saved image and whether the operation was successful
    """
    # Convert string to Path if needed
    file_name = Path(file_name) if isinstance(file_name, str) else file_name
    
    # Check the file name and enumerate if it already exists
    file_name = file_enumeration(file_name)
    
    # Create the camera
    camera = CameraFactory.create_camera(camera_type=camera_type, camera_id=camera_id)
    if camera is None:
        logger.error(f"Failed to create camera of type {camera_type}")
        return file_name, False
    
    try:
        # Connect to the camera
        if not camera.connect():
            logger.error("Failed to connect to camera")
            return file_name, False
        
        # Capture and save the image
        file_path, result = camera.capture_and_save(file_name)
        
        if result:
            logger.info(f"Image captured and saved to {file_path}")
        else:
            logger.error("Failed to capture or save image")
        
        return file_path, result
        
    except Exception as e:
        logger.error(f"Error capturing image: {e}")
        return file_name, False
    
    finally:
        # Make sure to close the camera
        if camera is not None:
            camera.close()


if __name__ == "__main__":
    import time
    from PIL import Image

    FILE_NAME = "test_image"
    file_path = Path(f"images/{str(FILE_NAME)}").with_suffix(".tiff")
    
    # Test with OpenCV camera (default)
    print("Testing with OpenCV camera (default)...")
    path, success = capture_new_image(
        save=True, 
        num_images=1, 
        file_name=file_path,
        camera_type=CameraType.OPENCV
    )
    
    if success:
        print(f"Image captured with OpenCV camera and saved to {path}")
        # Show the image
        with Image.open(path) as img:
            img.show()
        time.sleep(2)
    
    # Test with FLIR camera if available
    try:
        from .flir_camera import PYSPIN_AVAILABLE
        if PYSPIN_AVAILABLE:
            print("Testing with FLIR camera...")
            path, success = capture_new_image(
                save=True, 
                num_images=1, 
                file_name=file_path.with_name(f"{file_path.stem}_flir{file_path.suffix}"),
                camera_type=CameraType.FLIR
            )
            
            if success:
                print(f"Image captured with FLIR camera and saved to {path}")
                # Show the image
                with Image.open(path) as img:
                    img.show()
                time.sleep(2)
        else:
            print("PySpin not available, skipping FLIR camera test")
    except ImportError:
        print("PySpin not available, skipping FLIR camera test")
    
    # Cleanup
    try:
        Path.unlink(path)
        print(f"Removed test image: {path}")
    except Exception as e:
        print(f"Failed to remove test image: {e}")
