"""The sequence of steps for a pama contact angle drying experiment."""

# Standard imports

# Non-standard imports
from panda_lib.actions import (
    image_well,
)
from panda_lib.actions.actions_pama import (
    measure_contact_angle,
)
from panda_lib.experiments.experiment_types import EchemExperimentBase, ExperimentStatus
from panda_lib.toolkit import Toolkit
from panda_shared.db_setup import SessionLocal
from panda_lib.sql_tools.queries.racks import select_current_rack_id



PROTOCOL_ID = 30


def main(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    Wrapper function for the pama_ca_drying function.
    This function is called by the PANDA scheduler.
    It is the main function for the pama_ca_drying protocol.
    """
    contact_angle_measure(
        experiment=experiment,
        toolkit=toolkit,
    )


def contact_angle_measure(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    Follow up contact angle measurements

    Per experiment:
    1. Measure contact angle
    2. Rinse well with IPA


    """

    contact_angle(experiment=experiment, toolkit=toolkit)

    experiment.set_status_and_save(ExperimentStatus.COMPLETE)


def contact_angle(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """

    0. Image well
    1. Contact angle measurement
    2. Rinse with IPA

    Args:
        experiment (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
    """
    toolkit.global_logger.info(
        "Running experiment %s - measure contact angle", experiment.experiment_id
    )

    toolkit.global_logger.info("Image well")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="BeforeContactAngle",
    )

    toolkit.global_logger.info("Measuring contact angle")
    experiment.set_status_and_save(ExperimentStatus.MEASURING_CA)
    measure_contact_angle(
        toolkit=toolkit,
        experiment=experiment,
        session_maker=SessionLocal,
        tiprack_id=select_current_rack_id(),
        file_tag="CA_followup",
    )
    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="AfterContactAngle",
    )
    toolkit.global_logger.info("Contact angle measurement complete\n\n")


"""
    replace_tip(toolkit, session_maker=SessionLocal, tiprack_id=1)

    transfer(
        volume=200,
        src_vessel=solution_selector("acn", 200),
        dst_vessel=toolkit.wellplate.wells[experiment.well_id],
        toolkit=toolkit,
    )

    transfer(
        volume=200,
        src_vessel=toolkit.wellplate.wells[experiment.well_id],
        dst_vessel=waste_selector("waste", 200),
        toolkit=toolkit,
    )

"""
