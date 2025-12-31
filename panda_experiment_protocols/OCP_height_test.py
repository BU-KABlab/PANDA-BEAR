"""The sequence of steps for a dmfc system check experiment."""

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
from panda_lib.actions.electrochemistry import (
    CAFailure,
    DepositionFailure,
    OCPError,
)
from panda_lib.actions.electrochemistry import (
    perform_cyclic_voltammetry as cyclic_voltammetry,
)
from panda_lib.experiments.experiment_types import EchemExperimentBase, ExperimentStatus
from panda_lib.toolkit import Toolkit
from panda_lib.utilities import Instruments
from panda_shared.db_setup import SessionLocal
from panda_lib.sql_tools.queries.racks import select_current_rack_id
from panda_lib.actions.pipetting import replace_tip


PROTOCOL_ID = 41


def main(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    Wrapper function
    """
    dmfc_cv_protocol(
        experiment=experiment,
        toolkit=toolkit,
    )


def dmfc_cv_protocol(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    The initial screening of the dmfc cv protocol

    Per experiment:
    0. fecn_cv
    1. fecn_cv_rinse

    """

    dmfc_cv(experiment=experiment, toolkit=toolkit)

    experiment.set_status_and_save(ExperimentStatus.COMPLETE)


def dmfc_cv(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    1. Image well
    2. Dispense dmfc solution into well
    3. Perform CV
    4. Rinse electrode
    5. Clear well contents into waste
    6. Flush the pipette tip
    7. Rinse the well 3x with DMF
    8. Rinse the well 3x with ACN
    9. Rinse the well 3x with IPA
    10. Take image of well
    """
    toolkit.global_logger.info("Running fecn_cv protocol")
    experiment.set_status_and_save(ExperimentStatus.RUNNING)

    # Set up timer thread for tracking time ellapsed during electrochemistry experiments
    def timer_thread(stop_event):
        start = time.time()
        while not stop_event.is_set():
            elapsed = int(time.time() - start)
            mins, secs = divmod(elapsed, 60)
            # Send to Debug Console (stderr) and overwrite in place
            sys.stderr.write(f"\rElapsed: {mins:02d}:{secs:02d}")
            sys.stderr.flush()
            time.sleep(1)
        # drop a newline when stopping so the next log starts cleanly
        sys.stderr.write("\n")
        sys.stderr.flush()

    toolkit.global_logger.info("Running experiment %s part 1", experiment.experiment_id)
    stop_event = threading.Event()
    t = threading.Thread(target=timer_thread, args=(stop_event,), daemon=True)
    t.start()
    if not toolkit.pipette.has_tip:
        replace_tip(
            toolkit, session_maker=SessionLocal, tiprack_id=select_current_rack_id()
        )

    toolkit.global_logger.info("0. Imaging the well")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit, experiment, "BeforeCV", curvature_image=False, add_datazone=False
    )

    experiment.set_status_and_save(new_status=ExperimentStatus.DISPENSING)

    volume = 300
    transfer(
        volume=volume,
        src_vessel=solution_selector("dmfc", 300),
        dst_vessel=toolkit.wellplate.wells[experiment.well_id],
        toolkit=toolkit,
    )
    transfer(
        volume=200,
        src_vessel=solution_selector("dmf", 200),
        dst_vessel=waste_selector("waste", 200),
        toolkit=toolkit,
    )

    ## Move the electrode to the well
    toolkit.global_logger.info("2. Moving electrode to well: %s", experiment.well_id)

    # Move the electrode to above the well
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(experiment.well_id, "x"),
        y_coord=toolkit.wellplate.get_coordinates(experiment.well_id, "y"),
        z_coord=toolkit.wellplate.top,
        tool=Instruments.ELECTRODE,
    )
    # Set the feed rate to 100 to avoid overflowing the well
    toolkit.mill.set_feed_rate(100)
    toolkit.mill.safe_move(
        x_coord=toolkit.wellplate.get_coordinates(experiment.well_id, "x"),
        y_coord=toolkit.wellplate.get_coordinates(experiment.well_id, "y"),
        z_coord=toolkit.wellplate.echem_height,
        tool=Instruments.ELECTRODE,
    )
    # Set the feed rate back to 3000
    toolkit.mill.set_feed_rate(3000)

    toolkit.global_logger.info("Performing Cyclic Voltammetry")
    try:
        stop_event = threading.Event()
        t = threading.Thread(target=timer_thread, args=(stop_event,), daemon=True)
        t.start()
        cyclic_voltammetry(experiment, file_tag="CV_characterization")
    except (OCPError, CAFailure, DepositionFailure) as e:
        toolkit.global_logger.error(
            "Error occurred during cyclic_voltammetry: %s", str(e)
        )
        raise e
    except Exception as e:
        toolkit.global_logger.error(
            "Unknown error occurred during cyclic_voltammetry: %s", str(e)
        )
        raise e

    toolkit.global_logger.info("Rinsing electrode")
    experiment.set_status_and_save(new_status=ExperimentStatus.ERINSING)
    toolkit.mill.rinse_electrode(3)

    toolkit.global_logger.info("Clearing well contents into waste")
    experiment.set_status_and_save(ExperimentStatus.CLEARING)
    transfer(
        volume=toolkit.wellplate.wells[experiment.well_id].volume,
        src_vessel=toolkit.wellplate.wells[experiment.well_id],
        dst_vessel=waste_selector(
            "waste",
            toolkit.wellplate.wells[experiment.well_id].volume,
        ),
        toolkit=toolkit,
    )
    clear_well_res(
        toolkit=toolkit,
        src_vessel=toolkit.wellplate.wells[experiment.well_id],
        dst_vessel=waste_selector("waste", 200),
        desired_volume=200,
    )
    image_well(
        toolkit,
        experiment,
        "AfterCVbeforeRinse",
        curvature_image=False,
        add_datazone=False,
    )

    toolkit.global_logger.info("Rinsing the well 3x with DMF")
    experiment.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(3):
        toolkit.global_logger.info("DMF Rinse %d of 3", i + 1)
        transfer(
            volume=200,
            src_vessel=solution_selector("dmf", 200),
            dst_vessel=toolkit.wellplate.wells[experiment.well_id],
            toolkit=toolkit,
        )
        transfer(
            volume=200,
            src_vessel=toolkit.wellplate.wells[experiment.well_id],
            dst_vessel=waste_selector("waste", 200),
            toolkit=toolkit,
        )

    toolkit.global_logger.info("Clearing residual liquid from well")
    clear_well_res(
        toolkit=toolkit,
        src_vessel=toolkit.wellplate.wells[experiment.well_id],
        dst_vessel=waste_selector("waste", 200),
        desired_volume=200,
    )

    toolkit.global_logger.info("Rinsing the well 3x with ACN")
    experiment.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(3):
        toolkit.global_logger.info("ACN Rinse %d of 3", i + 1)
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

    toolkit.global_logger.info("Clearing residual liquid from well")
    clear_well_res(
        toolkit=toolkit,
        src_vessel=toolkit.wellplate.wells[experiment.well_id],
        dst_vessel=waste_selector("waste", 200),
        desired_volume=200,
    )

    toolkit.global_logger.info("Take after rinse image")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="AfterRinse",
        curvature_image=False,
        add_datazone=False,
    )
    stop_event.set()
    t.join(timeout=2)
    toolkit.global_logger.info("dmfc CV System Check Complete.\n\n")
