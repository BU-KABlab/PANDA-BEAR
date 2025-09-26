"""The sequence of steps for a pama contact angle drying experiment."""

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
from panda_lib.actions.pipetting import replace_tip, mix
from panda_shared.db_setup import SessionLocal


PROTOCOL_ID = 37 


def main(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    Wrapper function for the pama_ca_drying function.
    This function is called by the PANDA scheduler.
    It is the main function for the pama_peo_ca protocol.
    """
    pgma_ca(
        experiment=experiment,
        toolkit=toolkit,
    )

def pgma_ca(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    The initial screening of the pgma contact angle drying solution
    
    Per experiment:
    0. pgma_deposition
    1. pgma_ipa_rinse
    2. pgma_contact_angle

    """

    pgma_deposition(experiment=experiment, toolkit=toolkit)

    pgma_contact_angle(experiment=experiment, toolkit=toolkit)

    experiment.set_status_and_save(ExperimentStatus.COMPLETE)


def pgma_deposition(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    0. Imaging the well
    1. Depositing pgma into well
    2. Move electrode to well
    3. Perform CA
    4. Rinse electrode
    5. Clear well contents into waste
    6. Flush the pipette tip
    7. Rinse the well 3x with rinse
    8. Rinse the well 3x with flush
    9. Take image of well
    """
    def timer_thread(stop_event):
        start = time.time()
        while not stop_event.is_set():
            elapsed = int(time.time() - start)
            mins, secs = divmod(elapsed, 60)
            sys.stdout.write(f"\rElapsed: {mins:02d}:{secs:02d}")
            sys.stdout.flush()
            time.sleep(1)
        print()

    toolkit.global_logger.info(
        "Running experiment %s part 1", experiment.experiment_id
    )
    
    if not toolkit.pipette.has_tip:
        replace_tip(
            toolkit,
            session_maker=SessionLocal,
            tiprack_id=select_current_rack_id()
        )
    
    toolkit.global_logger.info("0. Imaging the well")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, experiment, "BeforeDeposition", curvature_image=False, add_datazone=False)

    experiment.set_status_and_save(new_status=ExperimentStatus.DEPOSITING)
    
    volume = 300
    transfer(
        volume=volume,
        src_vessel=solution_selector("pgma", 300),
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

    toolkit.global_logger.info("3. Performing CA deposition")
    try:
        stop_event = threading.Event()
        t = threading.Thread(target=timer_thread, args=(stop_event,), daemon=True)
        t.start()
        
        move_to_and_perform_ca(
            exp=experiment,
            toolkit=toolkit,
            file_tag="CA_deposition",
            well=toolkit.wellplate.wells[experiment.well_id],
            log=toolkit.global_logger,  
        )
        #chrono_amp(experiment, file_tag="CA_deposition") --- IGNORE --- this is used if we don't need to confirm electrode is in the correct position
    except (OCPError, CAFailure, DepositionFailure) as e:
        toolkit.global_logger.error("Error occurred during chrono_amp: %s", str(e))
        raise e
    except Exception as e:
        toolkit.global_logger.error(
            "Unknown error occurred during chrono_amp: %s", str(e)
        )
        raise e

    toolkit.global_logger.info("4. Rinsing electrode")
    experiment.set_status_and_save(new_status=ExperimentStatus.ERINSING)
    toolkit.mill.rinse_electrode(3)

    toolkit.global_logger.info("5. Clearing well contents into waste")
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
        dst_vessel=waste_selector("waste",200), 
        desired_volume=200
    )
    image_well(toolkit, experiment, "AfterDepBeforeRinse", curvature_image=False, add_datazone=False)

    toolkit.global_logger.info("7. Rinsing the well 3x with DMF")
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
    clear_well_res(
        toolkit=toolkit, 
        src_vessel=toolkit.wellplate.wells[experiment.well_id], 
        dst_vessel=waste_selector("waste",200), 
        desired_volume=200
    )

    toolkit.global_logger.info("8. Rinsing the well 3x with ACN")
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
    clear_well_res(
        toolkit=toolkit, 
        src_vessel=toolkit.wellplate.wells[experiment.well_id], 
        dst_vessel=waste_selector("waste",200), 
        desired_volume=200
    )
    stop_event.set()
    t.join(timeout=2)
    toolkit.global_logger.info("10. Take after image")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="AfterDeposition", curvature_image=False, add_datazone=False
    )

    toolkit.global_logger.info("PAMA deposition complete\n\n")
 

def pgma_contact_angle(
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
        "Running experiment %s part 2", experiment.experiment_id
    )
    toolkit.global_logger.info("Image well")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="BeforeContactAngle",
    )
    # create a loop for drying times combined with measuring contact angle at each time interval
    toolkit.global_logger.info("Drying the well and measuring contact angle")
    time_min = 60  # in minutes
    toolkit.global_logger.info("Drying for %d minutes", time_min)
    time.sleep(time_min * 60)
    toolkit.global_logger.info("Measuring contact angle after %d minutes", time_min)    
    experiment.set_status_and_save(ExperimentStatus.MEASURING_CA)
    measure_contact_angle(
        toolkit=toolkit,
        experiment=experiment,
        session_maker=SessionLocal,           
        tiprack_id=select_current_rack_id(),  
        file_tag=f"ContactAngle_AfterDrying_{time_min}min",
    )
    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="AfterContactAngle",
    )
    toolkit.global_logger.info("Contact angle measurement complete\n\n")

