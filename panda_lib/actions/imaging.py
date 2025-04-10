import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from hardware.grbl_cnc_mill import Instruments
from shared_utilities.config.config_tools import (
    ConfigParserError,
    read_config,
    read_testing_config,
)
from shared_utilities.log_tools import timing_wrapper

from ..experiments.experiment_types import (
    EchemExperimentBase,
    ExperimentStatus,
)
from ..imaging import add_data_zone, capture_new_image, image_filepath_generator
from ..toolkit import Toolkit


class ImageFailure(Exception):
    pass


TESTING = read_testing_config()

if TESTING:
    pass
else:
    pass

config = read_config()

# Constants
try:
    AIR_GAP = config.getfloat("DEFAULTS", "air_gap")
    DRIP_STOP = config.getfloat("DEFAULTS", "drip_stop_volume")
    if TESTING:
        PATH_TO_DATA = Path(config.get("TESTING", "data_dir"))
        PATH_TO_LOGS = Path(config.get("TESTING", "logging_dir"))
    else:
        PATH_TO_DATA = Path(config.get("PRODUCTION", "data_dir"))
        PATH_TO_LOGS = Path(config.get("PRODUCTION", "logging_dir"))
except ConfigParserError as e:
    logging.error("Failed to read config file. Error: %s", e)
    raise e

# Set up logging
logger = logging.getLogger("panda")
testing_logging = logging.getLogger("panda")


@timing_wrapper
def image_well(
    toolkit: Toolkit,
    instructions: Optional[EchemExperimentBase] = None,
    step_description: Optional[str] = None,
    curvature_image: bool = False,
) -> None:
    """Capture and save an image of a well.

    Parameters
    ----------
    toolkit : Toolkit
        Hardware control toolkit
    instructions : EchemExperimentBase, optional
        Experiment instructions containing well information
    step_description : str, optional
        Description of the experimental step for file naming
    curvature_image : bool, optional
        Whether to use curvature lighting, by default False

    Notes
    -----
    - Images are saved to configured data directory
    - Two images are saved: raw and with data zone overlay
    - Failed image capture will not halt experiment execution
    """
    if toolkit.flir_camera is None:
        logger.warning("No camera connected. Skipping imaging")
        return

    try:
        instructions.set_status_and_save(ExperimentStatus.IMAGING)
        logger.info("Imaging well %s", instructions.well_id)
        exp_id = instructions.experiment_id or "test"
        well_id = instructions.well_id or "test"
        pjct_id = instructions.project_id or "test"
        cmpgn_id = instructions.project_campaign_id or "test"
        # create file path
        filepath = image_filepath_generator(
            exp_id, pjct_id, cmpgn_id, well_id, step_description, PATH_TO_DATA
        )

        # position lens above the well
        logger.debug("Moving camera above well %s", well_id)
        if well_id != "test":
            toolkit.mill.safe_move(
                x_coord=instructions.well.well_data.x,
                y_coord=instructions.well.well_data.y,
                z_coord=toolkit.wellplate.plate_data.image_height,
                tool=Instruments.LENS,
            )
        else:
            pass

        if TESTING:
            Path(filepath).touch()
        else:
            if curvature_image:
                toolkit.arduino.curvature_lights_on()
            else:
                toolkit.arduino.white_lights_on()
            logger.debug("Capturing image of well %s", instructions.well_id)
            filepath, result = capture_new_image(
                save=True, num_images=1, file_name=filepath, logger=logger
            )
            toolkit.arduino.lights_off()

            if not result:
                raise ImageFailure("Failed to capture image")

            dz_filename = filepath.stem + "_dz" + filepath.suffix
            dz_filepath = filepath.with_name(dz_filename)

            img: Image = add_data_zone(
                experiment=instructions,
                image=Image.open(filepath),
                context=step_description,
            )
            img.save(dz_filepath)
            instructions.results.append_image_file(
                dz_filepath, context=step_description + "_dz"
            )
        logger.debug("Image of well %s captured", instructions.well_id)

        instructions.results.append_image_file(filepath, context=step_description)

    except ImageFailure as e:
        logger.exception("Failed to image well %s. Error %s occured", well_id, e)
        # raise ImageCaputreFailure(instructions.well_id) from e
        # don't raise anything and continue with the experiment. The image is not critical to the experiment

    except Exception as e:
        logger.exception(
            "Failed to image well %s. Error %s occured", instructions.well_id, e
        )
        # raise ImageCaputreFailure(instructions.well_id) from e
        # don't raise anything and continue with the experiment. The image is not critical to the experiment
    finally:
        # move camera to safe position
        if well_id != "test":
            logger.debug("Moving camera to safe position")
            toolkit.mill.move_to_safe_position()  # move to safe height above target well


if __name__ == "__main__":
    pass
