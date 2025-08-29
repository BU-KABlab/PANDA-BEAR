"""The sequence of steps for a pama contact angle drying experiment."""

# Standard imports
import time 
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
    pama_peo_ca(
        experiment=experiment,
        toolkit=toolkit,
    )

def pama_peo_ca(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    The initial screening of the pama contact angle drying solution
    
    Per experiment:
    0. pama_peo_deposition
    1. pama_ipa_rinse
    2. pama_contact_angle

    """

    pama_peo_deposition(experiment=experiment, toolkit=toolkit)

    pama_ipa_contact_angle(experiment=experiment, toolkit=toolkit)

    experiment.set_status_and_save(ExperimentStatus.COMPLETE)


def pama_peo_deposition(
    experiment: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    0. Imaging the well
    1. Depositing pama/peo/electrolyte mix into well
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

    toolkit.global_logger.info("1. Dispensing PAMA/electrolyte mix into well: %s", experiment.well_id)

    # Define which solution keys to use for mixing
    mixing_keys = ["electrolyte", "pama_200", "peo_70"]

    # Read all available vials
    stock_vials, _ = read_vials()

    # Find vials that match the mixing keys and have volume > 0
    mixing_vials = [v for v in stock_vials if v.name in mixing_keys and v.volume > 0]

    # Error if not all required vials are available
    for key in mixing_keys:
        if not any(v.name == key for v in mixing_vials):
            toolkit.global_logger.error(f"No vial available for {key}")
            raise ValueError(f"No vial available for {key}")

    # --- NEW: Build a per-vial composition map (species -> concentration_in_units_per_mL)
    # Units just need to be consistent with target.
    # Here: mg/mL for concentrations, µL for volumes (OK as long as both sides use µL).
    vial_comp = {
        "electrolyte": {"pama": 0.0,   "peo": 0.0},
        "pama_200":    {"pama": 200.0, "peo": 0.0},
        "peo_70":      {"pama": 0.0,   "peo": 70.0},
    }

    # If you store concentrations in `experiment.solutions`, you could also construct `vial_comp`
    # from there—just ensure it maps vial -> {species: conc}. The above is explicit and robust.

    # --- NEW: Total volume and species targets
    v_total = 300.0  # µL

    # Either pull from your experiment (preferred):
    target = {
        "pama": experiment.targets["pama_conc"],
        "peo":  experiment.targets["peo_conc"],
    }
    # Or set explicitly for this run:
    # target = {"pama": 50.0, "peo": 50.0}  # mg/mL

    # --- NEW: Solve (exact first; fall back to slack if min_vol makes exact infeasible)
    vols, devs, obj = solve_multisolute_mix(
        vial_comp=vial_comp,
        v_total=v_total,
        target=target,
        min_vol=10.0,         # enforce ≥10 µL per vial if selected
        allow_slack=False,    # try exact match first
    )

    if vols is None:
        # Allow a small deviation if the 10 µL minimum makes the exact mix impossible
        vols, devs, obj = solve_multisolute_mix(
            vial_comp=vial_comp,
            v_total=v_total,
            target=target,
            min_vol=10.0,
            allow_slack=True,   # minimize sum of absolute species deviations
        )
        if vols is None:
            raise ValueError("No feasible mixture found even with slack allowed.")

    # Log results
    toolkit.global_logger.info("Volumes to draw from each vial (µL): %s", vols)
    if any(v > 0 for v in devs.values()):
        toolkit.global_logger.warning("Species deviations (units of conc): %s", devs)

    # Pipette the calculated volumes from the vials into the well
    for key, volume in vols.items():
        volume = float(volume)
        if volume <= 0:
            continue
        vial: Vial = next(v for v in mixing_vials if v.name == key)
        transfer(
            volume=volume,
            src_vessel=vial,
            dst_vessel=toolkit.wellplate.wells[experiment.well_id],
            toolkit=toolkit,
        )
        toolkit.global_logger.info("Flushing the pipette tip")
        transfer(
            volume=200,
            src_vessel=solution_selector("dmf", 200),
            dst_vessel=waste_selector("waste", 200),
            toolkit=toolkit,
        )
        mix(toolkit=toolkit, well=toolkit.wellplate.wells[experiment.well_id],
            volume=150, mix_count=3, mix_height=2)

    # --- END MIXING STRATEGY ---

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
    clear_well_res(
        toolkit=toolkit, 
        src_vessel=toolkit.wellplate.wells[experiment.well_id], 
        dst_vessel=waste_selector("waste",200), 
        desired_volume=100
    )

    toolkit.global_logger.info("6. Flushing the pipette tip")
    experiment.set_status_and_save(ExperimentStatus.FLUSHING)

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
    clear_well_res(
        toolkit=toolkit, 
        src_vessel=toolkit.wellplate.wells[experiment.well_id], 
        dst_vessel=waste_selector("waste",200), 
        desired_volume=200
    )
    
    toolkit.global_logger.info("8. Rinsing the well 3x with IPA")
    experiment.set_status_and_save(ExperimentStatus.RINSING)
    for i in range(3):
        toolkit.global_logger.info("IPA Rinse %d of 3", i + 1)
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
    clear_well_res(
        toolkit=toolkit, 
        src_vessel=toolkit.wellplate.wells[experiment.well_id], 
        dst_vessel=waste_selector("waste",200), 
        desired_volume=200
    )

    toolkit.global_logger.info("10. Take after image")
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

