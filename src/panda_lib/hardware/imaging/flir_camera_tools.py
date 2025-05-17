"""
Requires the PySpin library to be installed and run in a python <=3.10 environment.
This script is used to capture images from the FLIR camera.
"""

import logging
from pathlib import Path

from panda_shared.log_tools import setup_default_logger

logger = setup_default_logger(
    log_file="FLIRCamera.log",
    log_name="camera",
    console_level=logging.ERROR,
    file_level=logging.DEBUG,
)


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
    # i = 1
    while filepath.exists():
        filepath = file_enumeration(filepath)
    return filepath
