"""Protocol for picking up and dropping pipette tips to test hardware and database handling."""

from panda_lib.experiments.experiment_types import EchemExperimentBase, ExperimentStatus
from panda_lib.hardware.panda_pipettes import insert_new_pipette
from panda_lib.toolkit import Toolkit
from panda_lib.actions.pipetting import replace_tip
from panda_shared.db_setup import SessionLocal
# Optional, if you want the current rack dynamically:
# from panda_lib.sql_tools.queries.racks import select_current_rack_id

PROTOCOL_ID = 9999

def main(experiment: EchemExperimentBase, toolkit: Toolkit):
    pipette_tip_test(experiment=experiment, toolkit=toolkit)

def pipette_tip_test(experiment: EchemExperimentBase, toolkit: Toolkit):
    """Pick up and drop a sequence of pipette tips to validate replace_tip."""
    toolkit.global_logger.info("Starting pipette tip pick up/drop test.")
    experiment.set_status_and_save(ExperimentStatus.RUNNING)

    # Ensure a pipette entry exists in the database
    insert_new_pipette()

    # Deterministic order (update to 5 if that is the intended count)
    tip_ids = ["A1", "A2", "A3", "B1", "B2", "B3"]

    # Use the active rack if available
    tiprack_id = 1
    # tiprack_id = select_current_rack_id()

    for tip in tip_ids:
        try:
            toolkit.global_logger.info("Replacing tip with %s on rack %s", tip, tiprack_id)
            # Pass the correct factory; match the parameter name expected by replace_tip
            replace_tip(toolkit, session_maker=SessionLocal, tiprack_id=tiprack_id, tip_id=tip)
            # If replace_tip already drops the current tip before picking up the next, nothing else needed here
        except Exception as e:
            toolkit.global_logger.error("Failed replace_tip for %s: %s", tip, e)

    experiment.set_status_and_save(ExperimentStatus.COMPLETE)
    toolkit.global_logger.info("Pipette tip test complete.")
