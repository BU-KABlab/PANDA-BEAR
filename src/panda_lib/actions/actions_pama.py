"""Custom functions for the PANDA_SDL library which are specific to a particular experiment type."""

from panda_lib.exceptions import (
    ContactAngleFailure,
)
from panda_lib.experiments.experiment_types import EchemExperimentBase
from panda_lib.actions.electrochemistry import (
    ExperimentStatus,
)
from panda_lib.actions.imaging import (
    image_well
)
from panda_lib.actions.vessel_handling import (
    solution_selector,
    waste_selector,
)
from panda_lib.actions.pipetting import (
    transfer,
    contact_angle_transfer,
)
from panda_lib.toolkit import Toolkit
from panda_lib.utilities import Instruments


def measure_contact_angle(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
    file_tag: str = "ContactAngle",
) -> EchemExperimentBase:
    """
    0. Dispense 10µL droplet of water into well
    1. Measure contact angle by capturing images
    2. Clear well contents into waste
    3. Rinse the well 3x with IPA
    """
    try:
        toolkit.global_logger.info("0. Dispensing 10µL droplet of water into well")
        experiment.set_status_and_save(ExperimentStatus.DEPOSITING)
        contact_angle_transfer(
            volume=10,
            src_vessel=solution_selector("water", 10),
            dst_vessel=toolkit.wellplate.wells[experiment.well_id],
            toolkit=toolkit,
            ca_dispense_height=toolkit.wellplate.bottom + 4,
        )

        toolkit.global_logger.info("1. Imaging the well")
        experiment.set_status_and_save(ExperimentStatus.IMAGING)
        image_well(
            toolkit=toolkit,
            experiment=experiment,
            image_label=file_tag,
            curvature_image=True,
            add_datazone=False,
        )

        toolkit.global_logger.info("2. Clearing well contents into waste")
        experiment.set_status_and_save(ExperimentStatus.CLEARING)
        contact_angle_transfer(
            volume=10,
            src_vessel=toolkit.wellplate.wells[experiment.well_id],
            dst_vessel=waste_selector("waste", 10),
            toolkit=toolkit,
            ca_dispense_height=toolkit.wellplate.bottom + 1, 
        )

        toolkit.global_logger.info("3. Rinsing the well 3x with IPA")
        experiment.set_status_and_save(ExperimentStatus.RINSING)
        for i in range(3):
            toolkit.global_logger.info("Rinse %d of 3", i + 1)
            transfer(
                volume=200,
                src_vessel=solution_selector("ipa", 200),
                dst_vessel=toolkit.wellplate.wells[experiment.well_id],
                toolkit=toolkit,
            )

            toolkit.mill.safe_move(
                x_coord=toolkit.wellplate.get_coordinates(experiment.well_id, "x"),
                y_coord=toolkit.wellplate.get_coordinates(experiment.well_id, "y"),
                z_coord=toolkit.wellplate.top,
                tool=Instruments.PIPETTE,
            )
            transfer(
                volume=200,
                src_vessel=toolkit.wellplate.wells[experiment.well_id],
                dst_vessel=waste_selector("waste", 200),
                toolkit=toolkit,
            )

        return experiment

    except Exception as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        toolkit.global_logger.error("Exception occurred during contact angle measurement: %s", e)
        raise ContactAngleFailure(experiment.experiment_id, experiment.well_id) from e

def measure_contact_angle_norinse(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
    file_tag: str = "ContactAngle",
) -> EchemExperimentBase:
    """
    0. Dispense 10µL droplet of water into well
    1. Measure contact angle by capturing images
    2. Clear well contents into waste
    3. Rinse the well 3x with IPA
    """
    try:
        toolkit.global_logger.info("0. Dispensing 10µL droplet of water into well")
        experiment.set_status_and_save(ExperimentStatus.DEPOSITING)
        contact_angle_transfer(
            volume=10,
            src_vessel=solution_selector("water", 10),
            dst_vessel=toolkit.wellplate.wells[experiment.well_id],
            toolkit=toolkit,
            ca_dispense_height=toolkit.wellplate.bottom + 4,
        )

        toolkit.global_logger.info("1. Imaging the well")
        experiment.set_status_and_save(ExperimentStatus.IMAGING)
        image_well(
            toolkit=toolkit,
            experiment=experiment,
            image_label=file_tag,
            curvature_image=True,
            add_datazone=False,
        )

        toolkit.global_logger.info("2. Clearing well contents into waste")
        experiment.set_status_and_save(ExperimentStatus.CLEARING)
        contact_angle_transfer(
            volume=10,
            src_vessel=toolkit.wellplate.wells[experiment.well_id],
            dst_vessel=waste_selector("waste", 10),
            toolkit=toolkit,
            ca_dispense_height=toolkit.wellplate.bottom + 0.1, 
        )

        return experiment

    except Exception as e:
        experiment.set_status_and_save(ExperimentStatus.ERROR)
        toolkit.global_logger.error("Exception occurred during contact angle measurement: %s", e)
        raise ContactAngleFailure(experiment.experiment_id, experiment.well_id) from e



