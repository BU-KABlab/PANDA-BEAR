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

PROTOCOL_ID = 31 


def main(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    Wrapper function for the pama_ca_drying function.
    This function is called by the PANDA scheduler.
    It is the main function for the pama_ca_drying protocol.
    """
    pama_ca_drying(
        experiment=experiment,
        toolkit=toolkit,
    )

def pama_ca_drying(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    The initial screening of the pama contact angle drying solution
    
    Per experiment:
    0. pama_deposition
    1. pama_ipa_rinse
    2. pama_ca_drying
    3. pama_contact_angle
    
    
    
    pama_deposition(
        experiment=experiment,
        toolkit=toolkit,
    )
    """
    pama_ipa_contact_angle(
        experiment=experiment,
        toolkit=toolkit,
    )

    experiment.set_status_and_save(ExperimentStatus.COMPLETE)


def pama_deposition(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    0. Imaging the well
    1. Depositing pama/electrolyte mix into well
    2. Move electrode to well
    3. Perform CA
    4. Rinse electrode
    5. Clear well contents into waste
    6. Flush the pipette tip
    7. Rinse the well 3x with rinse
    8. Rinse the well 3x with flush
    9. Take image of well
    """
    
    toolkit.global_logger.info(
        "Running experiment %s part 1", experiment.experiment_id
    )
    toolkit.global_logger.info("0. Imaging the well")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(toolkit, experiment, "BeforeDeposition", curvature_image=False, add_datazone=False)

    experiment.set_status_and_save(new_status=ExperimentStatus.DEPOSITING)
    toolkit.global_logger.info("1. Dispensing PAMA/electrolyte mix into well: %s", experiment.well_id)

    # Define which solution keys to use for mixing
    mixing_keys = ["pama_200", "electrolyte"]

    # Read all available vials
    stock_vials, _ = read_vials()
    # Find vials that match the mixing keys and have volume > 0
    mixing_vials = [
        vial for vial in stock_vials if vial.name in mixing_keys and vial.volume > 0
    ]

    # Error if not all required vials are available
    for key in mixing_keys:
        if not any(vial.name == key for vial in mixing_vials):
            toolkit.global_logger.error(f"No vial available for {key}")
            raise ValueError(f"No vial available for {key}")

    # Build concentration map from experiment
    vial_concentration_map = {
        key: experiment.solutions[key]["concentration"] for key in mixing_keys
    }

    v_total = 300
    # Set your target concentration here (example: 100)
    c_target = 100

    # Solve for mixing volumes
    vial_vol_by_conc, deviation_value, vial_vol_by_location = solve_vials_ilp(
        vial_concentration_map=vial_concentration_map,
        v_total=v_total,
        c_target=c_target,
    )

    if vial_vol_by_location is None:
        raise ValueError(
            f"No solution combinations found for target {c_target} (deviation: {deviation_value})"
        )
    toolkit.global_logger.info(
        "Volumes to draw from each vial: %s uL", vial_vol_by_location
    )
    toolkit.global_logger.info("Deviation from target concentration: %s", deviation_value)

    # Pipette the calculated volumes from the vials into the well
    for key, volume in vial_vol_by_location.items():
        if volume == 0:
            continue
        # Find the matching vial object
        vial: Vial = next(vial for vial in mixing_vials if vial.name == key)
        transfer(
            volume=volume,
            src_vessel=vial,
            dst_vessel=toolkit.wellplate.wells[experiment.well_id],
            toolkit=toolkit,
        )
    # --- END MIXING STRATEGY ---
    toolkit.global_logger.info("Flushing the pipette tip")
    experiment.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_pipette(flush_with="dmf", toolkit=toolkit)
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
        chrono_amp(experiment, file_tag="CA_deposition")
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

    toolkit.global_logger.info("6. Flushing the pipette tip")
    experiment.set_status_and_save(ExperimentStatus.FLUSHING)
    flush_pipette(flush_with="dmf", toolkit=toolkit)

    toolkit.global_logger.info("7. Rinsing the well 3x with DMF")
    experiment.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(3):
        toolkit.global_logger.info("Rinse %d of 3", i + 1)
        transfer(
            volume=200,
            src_vessel=solution_selector("dmf", 200),
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

    toolkit.global_logger.info("8. Rinsing the well 3x with ACN")
    experiment.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(3):
        toolkit.global_logger.info("Rinse %d of 3", i + 1)
        transfer(
            volume=200,
            src_vessel=solution_selector("acn", 200),
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

    toolkit.global_logger.info("9. Take after image")
    experiment.set_status_and_save(ExperimentStatus.IMAGING)
    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="AfterDeposition", curvature_image=False, add_datazone=False
    )

    toolkit.global_logger.info("PAMA deposition complete\n\n")


def pama_ipa_contact_angle(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    0. Rinse with IPA
    1. Image well
    2. Contact angle measurement
    
    Args:
        experiment (EchemExperimentBase): _description_
        toolkit (Toolkit): _description_
    """
    toolkit.global_logger.info(
        "Running experiment %s part 2", experiment.experiment_id
    )
    image_well(
        toolkit=toolkit,
        experiment=experiment,
        image_label="BeforeIPARinsing", curvature_image=False, add_datazone=False
    )
    toolkit.global_logger.info("0. Rinse with IPA")
    experiment.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(3):
        # Pipette the rinse solution into the well
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
        # Clear the well
        transfer(
            volume=200,
            src_vessel=toolkit.wellplate.wells[experiment.well_id],
            dst_vessel=waste_selector(
                "waste",
                200,
            ),
            toolkit=toolkit,
        )
        toolkit.global_logger.info("1. Image well")
        experiment.set_status_and_save(ExperimentStatus.IMAGING)
        image_well(
            toolkit=toolkit,
            experiment=experiment,
            image_label=f"AfterRinsing_{i}x",
        )

    # create a loop for drying times combined with measuring contact angle at each time interval
    toolkit.global_logger.info("2. Drying the well and measuring contact angle")
    drying_times = [0,1,2,3,5,8,13,22,36,60]  # in minutes
    for time_min in drying_times:
        toolkit.global_logger.info("Drying for %d minutes", time_min)
        time.sleep(time_min * 60)
        toolkit.global_logger.info("Measuring contact angle after %d minutes", time_min)    
        experiment.set_status_and_save(ExperimentStatus.MEASURING_CA)
        measure_contact_angle(
            toolkit=toolkit,
            experiment=experiment,
            file_tag=f"AfterDrying_{time_min}min",
        )

    toolkit.global_logger.info("Contact angle measurement complete\n\n")
