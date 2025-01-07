"""running pycapture-test.py from python 3.11"""

from logging import Logger
from pathlib import Path
from typing import Optional

from PySpin import PySpin

from .camera import run_single_camera


def file_enumeration(file_path: Path) -> Path:
    """Enumerate a file path if it already exists"""
    i = 1
    while file_path.exists():
        file_path = file_path.with_name(
            file_path.stem + "_" + str(i) + file_path.suffix
        )
        i += 1
    return file_path


def image_filepath_generator(
    exp_id: int = "test",
    project_id: int = "test",
    project_campaign_id: int = "test",
    well_id: str = "test",
    step_description: str = None,
    data_path: Path = Path("images"),
) -> Path:
    """
    Generate the file path for the image
    """
    # create file name
    if step_description is not None:
        file_name = f"{project_id}_{project_campaign_id}_{exp_id}_{well_id}_{step_description}_image"
    else:
        file_name = f"{project_id}_{project_campaign_id}_{exp_id}_{well_id}_image"
    file_name = file_name.replace(" ", "_")  # clean up the file name
    file_name_start = file_name + "_0"  # enumerate the file name
    filepath = Path(data_path / str(file_name_start)).with_suffix(".tiff")
    i = 1
    while filepath.exists():
        filepath = file_enumeration(filepath)
    return filepath


def capture_new_image(
    save=True,
    num_images=1,
    file_name: Path = Path("images/test.tiff"),
    logger: Optional[Logger] = None,
) -> Path:
    """Capture a new image from the FLIR camera"""
    # Check the file name and ennumerate if it already exists
    file_name = file_enumeration(file_name)
    pyspin_system: PySpin.SystemPtr = PySpin.System.GetInstance()
    camera_list: PySpin.CameraList = pyspin_system.GetCameras()
    # Run example on each camera
    for _, camera in enumerate(camera_list):
        camera: PySpin.CameraPtr
        result = run_single_camera(camera, image_path=file_name, num_images=num_images)
        if result:
            logger.info(f"Camera {camera.DeviceSerialNumber} took image...")
        else:
            logger.error(f"Camera {camera.DeviceSerialNumber} failed to take image...")
    # Clear camera list before releasing system
    camera_list.Clear()

    # Release system instance
    pyspin_system.ReleaseInstance()

    return file_name


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
