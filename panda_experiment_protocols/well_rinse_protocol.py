"""The sequence of steps for a pama contact angle drying experiment."""

# Standard imports
import time 
# Non-standard imports
from panda_lib.actions import (
    flush_pipette,
    image_well,
    solution_selector,
    transfer,
    waste_selector,
)
from panda_lib.actions.pipetting import _pipette_action as clear_well_res
from panda_lib.actions.actions_pama import (
    measure_contact_angle,
)
from panda_lib.actions.electrochemistry import (
    CAFailure,
    DepositionFailure,
    OCPError,
)
from panda_lib.actions.electrochemistry import (
    perform_chronoamperometry as chrono_amp,
)
from panda_lib.experiments.experiment_types import EchemExperimentBase, ExperimentStatus
from panda_lib.labware.vials import Vial, read_vials
from panda_lib.toolkit import Toolkit
from panda_lib.utilities import Instruments, solve_vials_ilp
from panda_lib.hardware.panda_pipettes import insert_new_pipette
from panda_shared.db_setup import SessionLocal
from panda_lib.sql_tools.queries.racks import select_current_rack_id
from panda_lib.actions.pipetting import replace_tip


def main(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    Wrapper function for the pama_ca_drying function.
    This function is called by the PANDA scheduler.
    It is the main function for the pama_ca_drying protocol.
    """
    well_rinse_protocol(
        experiment=experiment,
        toolkit=toolkit,
    )

def well_rinse_protocol(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    
    well_rinse_image(
        experiment=experiment,
        toolkit=toolkit,
    )

    experiment.set_status_and_save(ExperimentStatus.COMPLETE)



def well_rinse_image(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    0. Rinse with IPA
    1. Image well
    
    
    Args:
        experiment (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
    """
    toolkit.global_logger.info(
        "Running experiment %s part 3", experiment.experiment_id
    )
    toolkit.global_logger.info("Image well")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)

    measure_contact_angle(
        toolkit=toolkit,
        experiment=experiment,
        session_maker=SessionLocal,           
        tiprack_id=select_current_rack_id(),  
        file_tag="initial_CA_measurement",
    )

    toolkit.global_logger.info("1. Image well")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="AfterRinsing",
    )
    # create a loop for drying times combined with measuring contact angle at each time interval
    toolkit.global_logger.info("2. Drying the well")


    # Generate imaging times (in minutes)
    imaging_times = list(range(1, 60))

    # Track elapsed time
    previous_time = 0

    for time_min in imaging_times:
        wait_time = (time_min - previous_time) * 60  # seconds to wait
        toolkit.global_logger.info("Drying for %d minutes", time_min - previous_time)
        time.sleep(wait_time)
        toolkit.global_logger.info("Imaging after %d minutes", time_min)
        image_well(toolkit=toolkit, experiment=experiment, image_label=f"AfterDrying_{time_min}min")
        previous_time = time_min

    measure_contact_angle(
        toolkit=toolkit,
        experiment=experiment,
        session_maker=SessionLocal,           
        tiprack_id=select_current_rack_id(),  
        file_tag="final_CA_measurement",
    )

    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="AfterContactAngle",
    )
    
    toolkit.global_logger.info("Drying imaging complete\n\n")
