"""
This module is used to capture images from the FLIR camera.
"""

# from .camera import FLIRCamera
from logging import Logger
from pathlib import Path
from typing import Optional

import PySpin

from .flir_camera_tools import (
    file_enumeration,
    image_filepath_generator,
    run_single_camera,
)
from .panda_image_tools import add_data_zone, invert_image

__all__ = [
    "add_data_zone",
    "capture_new_image",
    "file_enumeration",
    "image_filepath_generator",
    "invert_image",
]

default_logger = Logger("panda")


def capture_new_image(
    save=True,
    num_images=1,
    file_name: Path = Path("images/test.tiff"),
    logger: Optional[Logger] = default_logger,
) -> Path:
    """Capture a new image from the FLIR camera"""
    # Check the file name and ennumerate if it already exists
    file_name = file_enumeration(file_name)
    result = False  # Initialize result with a default value
    try:
        pyspin_system: PySpin.SystemPtr = PySpin.System.GetInstance()
        camera_list: PySpin.CameraList = pyspin_system.GetCameras()
        if camera_list.GetSize() == 0:
            logger.error("No cameras found.")
            return file_name, result

        # Run example on each camera
        for _, camera in enumerate(camera_list):
            camera: PySpin.CameraPtr
            result = run_single_camera(
                camera, image_path=file_name, num_images=num_images
            )
            if result:
                logger.info("Camera took image...")
            else:
                logger.error("Camera failed to take image...")

    except PySpin.SpinnakerException as ex:
        logger.error(f"Error: {ex}")
        return file_name, False

    finally:
        # Clear camera list before releasing system
        camera_list.Clear()

        # Release system instance
        pyspin_system.ReleaseInstance()

    return file_name, result


if __name__ == "__main__":
    import time

    from PIL import Image

    FILE_NAME = "test image"
    file_path = Path(f"images/{str(FILE_NAME)}").with_suffix(".tiff")
    capture_new_image(save=True, num_images=1, file_name=file_path)
    time.sleep(5)
    # Show the image
    with Image.open(file_path) as img:
        img.show()

    Path.unlink(file_path)
