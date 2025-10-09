"""Protocol for solid handling."""

from panda_lib.experiments.experiment_types import EchemExperimentBase, ExperimentStatus
from panda_lib.hardware.panda_pipettes import insert_new_pipette
from panda_lib.toolkit import Toolkit
from panda_lib.actions.pipetting import replace_tip
from panda_shared.db_setup import SessionLocal
# Standard imports
import time 
import threading
import sys
# Non-standard imports
from panda_lib.actions import (
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
    move_to_and_perform_ca
)
from panda_lib.actions.electrochemistry import (
    perform_chronoamperometry as chrono_amp,
)
from panda_lib.experiments.experiment_types import EchemExperimentBase, ExperimentStatus
from panda_lib.labware.vials import Vial, read_vials
from panda_lib.toolkit import Toolkit
from panda_lib.utilities import Instruments, solve_multisolute_mix
from panda_lib.hardware.panda_pipettes import insert_new_pipette
from panda_shared.db_setup import SessionLocal
from panda_lib.sql_tools.queries.racks import select_current_rack_id



PROTOCOL_ID = 45
produces_images = False



def main(experiment: EchemExperimentBase, toolkit: Toolkit):
    solid_handling_test(experiment=experiment, toolkit=toolkit)



def solid_handling_test(experiment: EchemExperimentBase, toolkit: Toolkit):
    toolkit.global_logger.info("Starting solid handling test.")
    experiment.set_status_and_save(ExperimentStatus.RUNNING)

    # Ensure a pipette entry exists in the database
    insert_new_pipette()
    tiprack_id = 1

    replace_tip(toolkit, session_maker=SessionLocal, tiprack_id=tiprack_id, tip_id=None)

    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(experiment.well_id, "x"),
        y_coord=toolkit.wellplate.get_coordinates(experiment.well_id, "y"),
        z_coord=toolkit.wellplate.top, 
        tool=Instruments.PIPETTE,
    )

    '''
    tip_ids = ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6"]

    # Use the active rack if available
    tiprack_id = 1
    # tiprack_id = select_current_rack_id()

    for tip in tip_ids:
        try:
            toolkit.global_logger.info("Replacing tip with %s on rack %s", tip, tiprack_id)
            # Pass the correct factory; match the parameter name expected by replace_tip
            replace_tip(toolkit, session_maker=SessionLocal, tiprack_id=tiprack_id, tip_id=tip)
            
        except Exception as e:
            toolkit.global_logger.error("Failed replace_tip for %s: %s", tip, e)
    '''
    experiment.set_status_and_save(ExperimentStatus.COMPLETE)
    toolkit.global_logger.info("Pipette tip test complete.")
