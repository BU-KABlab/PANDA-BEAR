"""
Responsible for calling the appropirate interfaces to perform a given experiment.

Args:
    Expriment instructions : Experiment
        All parameters to run the experiment
    Mill: Mill object
    Pump: Pump object
    Potentiostat: Potentiostat object
    Camera: Camera object
    OBS: OBS object
    Wellplate: Wellplate object
    Vials: Vials object
    Scale: Scale object

Returns:
    ExperimentResult: The results of the experiment.
    Wellplate: The updated wellplate object.
    Vials: The updated vials object.
"""

# pylint: disable=line-too-long, too-many-arguments, too-many-lines, broad-exception-caught

# Standard library imports
import logging
import math
from logging import Logger

# Third party or custom imports
from pathlib import Path
from typing import List, Optional, Tuple, Union

from PIL import Image
from sqlalchemy.orm import Session

from hardware.grbl_cnc_mill import Instruments
from hardware.pipette.syringepump import MockPump, SyringePump
from panda_lib.config.config_tools import (
    ConfigParserError,
    read_config,
    read_testing_config,
)
from panda_lib.errors import (
    CAFailure,
    CVFailure,
    DepositionFailure,
    NoAvailableSolution,
    OCPFailure,
)
from panda_lib.experiment_class import (
    EchemExperimentBase,
    ExperimentBase,
    ExperimentStatus,
)

# First party imports
from panda_lib.imaging import add_data_zone, capture_new_image, image_filepath_generator
from panda_lib.instrument_toolkit import ArduinoLink, Hardware, Labware, Toolkit
from panda_lib.labware.vials import StockVial, Vial, WasteVial, read_vials
from panda_lib.labware.wellplate import Coordinates, Well
from panda_lib.log_tools import timing_wrapper
from panda_lib.panda_gantry import MockPandaMill as MockMill
from panda_lib.panda_gantry import PandaMill as Mill
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.tools.obs_controls import MockOBSController, OBSController
from panda_lib.utilities import correction_factor, solve_vials_ilp

TESTING = read_testing_config()

if TESTING:
    from hardware.gamry_potentiostat.gamry_control_mock import (
        GamryPotentiostat as echem,
    )
    from hardware.gamry_potentiostat.gamry_control_mock import (
        chrono_parameters,
        cv_parameters,
        potentiostat_ocp_parameters,
    )
else:
    import hardware.gamry_potentiostat.gamry_control as echem
    from hardware.gamry_potentiostat.gamry_control import (
        chrono_parameters,
        cv_parameters,
        potentiostat_ocp_parameters,
    )

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


def _handle_source_vessels(
    volume: float,
    src_vessel: Union[str, Well, StockVial],
    pjct_logger: Logger = logger,
    source_concentration: Optional[float] = None,
    db_session: Session = SessionLocal,
) -> Tuple[List[Union[Vial, Well]], List[Tuple[Union[Vial, Well], float]]]:
    selected_source_vessels: List[Union[Vial, Well]] = []
    source_vessel_volumes: List[Tuple[Union[Vial, Well], float]] = []

    if isinstance(src_vessel, (str, Vial)):
        if isinstance(src_vessel, Vial):
            src_vessel = src_vessel.name.lower()
        else:
            src_vessel = src_vessel.lower()
        stock_vials, _ = read_vials(db_session())
        selected_source_vessels = [
            vial
            for vial in stock_vials
            if vial.name == src_vessel and vial.volume > 0.0
        ]

        if not selected_source_vessels:
            pjct_logger.error("No %s vials available", src_vessel)
            raise ValueError(f"No {src_vessel} vials available")

        if source_concentration is None:
            pjct_logger.warning(
                "Source concentration not provided, using database value"
            )
            if selected_source_vessels[0].category == 0:
                try:
                    source_concentration = float(
                        selected_source_vessels[0].concentration
                    )
                except ValueError:
                    pjct_logger.error(
                        "Source concentration not provided and not available in the database"
                    )
                    raise ValueError(
                        "Source concentration not provided and not available in the database"
                    )

        source_vessel_volumes, deviation, volumes_by_position = solve_vials_ilp(
            vial_concentration_map={
                vial.position: vial.concentration for vial in selected_source_vessels
            },
            v_total=volume,
            c_target=source_concentration,
        )

        if source_vessel_volumes is None:
            raise ValueError(
                f"No solution combinations found for {src_vessel} {source_concentration} mM"
            )

        pjct_logger.info("Deviation from target concentration: %s mM", deviation)

        source_vessel_volumes = [
            (vial, volumes_by_position[vial.position])
            for vial in selected_source_vessels
        ]

    elif isinstance(src_vessel, (Well, Vial)):
        source_vessel_volumes = [(src_vessel, volume)]
        pjct_logger.info(
            "Pipetting %f uL from %s", volume, src_vessel.name or src_vessel
        )

    return selected_source_vessels, source_vessel_volumes


def _pipette_action(
    toolkit: Union[Toolkit, Hardware],
    src_vessel: Union[Vial, Well],
    dst_vessel: Union[Well, WasteVial],
    desired_volume: float,
):
    """
    Perform the pipetting action from the source vessel to the destination vessel

    Args:
        toolkit (Toolkit): The toolkit object
        vessel (Union[Vial, Well]): The source vessel
        dst_vessel (Union[Well, WasteVial]): The destination vessel
        desired_volume (float): The volume to be pipetted
    """

    repetitions = math.ceil(
        desired_volume / (toolkit.pump.pipette.capacity_ul - DRIP_STOP)
    )
    if isinstance(src_vessel, Well):
        repetition_vol = correction_factor(desired_volume / repetitions, 1.0)
    else:
        repetition_vol = correction_factor(
            desired_volume / repetitions, src_vessel.viscosity_cp
        )
    logger.info(
        "Pipetting %f uL from %s to %s",
        desired_volume,
        src_vessel.name,
        dst_vessel.name,
    )

    for j in range(repetitions):
        logger.info("Repetition %d of %d", j + 1, repetitions)

        if isinstance(src_vessel, StockVial):
            decapping_sequence(
                toolkit.mill,
                Coordinates(src_vessel.x, src_vessel.y, src_vessel.top),
                toolkit.arduino,
            )

        toolkit.pump.withdraw(volume_to_withdraw=AIR_GAP)
        toolkit.mill.safe_move(
            src_vessel.x,
            src_vessel.y,
            src_vessel.withdrawal_height,
            tool=Instruments.PIPETTE,
        )
        toolkit.pump.withdraw(volume_to_withdraw=repetition_vol, solution=src_vessel)
        if isinstance(src_vessel, Well):
            toolkit.pump.withdraw(volume_to_withdraw=20)
        toolkit.mill.move_to_safe_position()
        toolkit.pump.withdraw(volume_to_withdraw=DRIP_STOP)

        if isinstance(src_vessel, StockVial):
            capping_sequence(
                toolkit.mill,
                Coordinates(src_vessel.x, src_vessel.y, src_vessel.top),
                toolkit.arduino,
            )

        if isinstance(dst_vessel, WasteVial):
            decapping_sequence(
                toolkit.mill,
                Coordinates(dst_vessel.x, dst_vessel.y, dst_vessel.top),
                toolkit.arduino,
            )

        toolkit.mill.safe_move(
            dst_vessel.x,
            dst_vessel.y,
            dst_vessel.top,
            tool=Instruments.PIPETTE,
        )
        toolkit.pump.infuse(
            volume_to_infuse=repetition_vol,
            being_infused=src_vessel,
            infused_into=dst_vessel,
            blowout_ul=(
                AIR_GAP + DRIP_STOP + 20
                if isinstance(src_vessel, Well)
                else AIR_GAP + DRIP_STOP
            ),
        )

        for _, vol in toolkit.pump.pipette.contents.items():
            if vol > 0.0:
                logger.warning("Pipette has residual volume of %f ul. Purging...", vol)
                toolkit.pump.infuse(
                    volume_to_infuse=vol,
                    being_infused=None,
                    infused_into=dst_vessel,
                    blowout_ul=vol,
                )

        if toolkit.pump.pipette.volume > 0.0:
            logger.warning(
                "Pipette has residual volume of %f ul. Purging...",
                toolkit.pump.pipette.volume,
            )
            toolkit.pump.infuse(
                volume_to_infuse=toolkit.pump.pipette.volume,
                being_infused=None,
                infused_into=dst_vessel,
                blowout_ul=toolkit.pump.pipette.volume,
            )
            toolkit.pump.pipette.volume = 0.0

        if isinstance(dst_vessel, WasteVial):
            capping_sequence(
                toolkit.mill,
                Coordinates(dst_vessel.x, dst_vessel.y, dst_vessel.top),
                toolkit.arduino,
            )


@timing_wrapper
def _forward_pipette_v3(
    volume: float,
    src_vessel: Union[str, Well, StockVial],
    dst_vessel: Union[Well, WasteVial],
    toolkit: Union[Toolkit, Hardware],
    source_concentration: float = None,
    labware: Optional[Labware] = None,
) -> int:
    try:
        if volume <= 0.0:
            return

        selected_source_vessels, source_vessel_volumes = _handle_source_vessels(
            volume=volume,
            src_vessel=src_vessel,
            source_concentration=source_concentration,
            pjct_logger=toolkit.global_logger,
        )

        for origin_vessel, _ in source_vessel_volumes:
            if isinstance(origin_vessel, Well) and isinstance(dst_vessel, StockVial):
                raise ValueError("Cannot pipette from a well to a stock vial")
            if isinstance(origin_vessel, WasteVial) and isinstance(dst_vessel, Well):
                raise ValueError("Cannot pipette from a waste vial to a well")
            if isinstance(origin_vessel, StockVial) and isinstance(
                dst_vessel, StockVial
            ):
                raise ValueError("Cannot pipette from a stock vial to a stock vial")

        for vessel, desired_volume in source_vessel_volumes:
            if desired_volume <= 0.0:
                continue
            _pipette_action(toolkit, vessel, dst_vessel, desired_volume)

    except Exception as e:
        toolkit.global_logger.error("Exception occurred during pipetting: %s", e)
        raise e
    return 0


# No timer wrapper for this function since its a wrapper itself
def transfer(
    volume: float,
    src_vessel: Union[str, Well, StockVial],
    dst_vessel: Union[Well, WasteVial],
    toolkit: Toolkit,
    source_concentration: float = None,
) -> int:
    return _forward_pipette_v3(
        volume, src_vessel, dst_vessel, toolkit, source_concentration
    )


@timing_wrapper
def rinse_well(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
    alt_sol_name: Optional[str] = None,
    alt_vol: Optional[float] = None,
    alt_count: Optional[int] = None,
):
    """
    Rinse the well with rinse_vol ul.
    Involves pipetteing and then clearing the well with no purging steps

    Args:
        instructions (Experiment): The experiment instructions
        toolkit (Toolkit): The toolkit object

    Returns:
        None (void function) since the objects are passed by reference
    """
    sol_name = instructions.rinse_sol_name if alt_sol_name is None else alt_sol_name
    vol = instructions.rinse_vol if alt_vol is None else alt_vol
    count = instructions.rinse_count if alt_count is None else alt_count

    logger.info(
        "Rinsing well %s %dx...", instructions.well_id, instructions.rinse_count
    )
    instructions.set_status_and_save(ExperimentStatus.RINSING)
    for _ in range(count):
        logger.info("Rinse %d of %d", _ + 1, count)
        # Pipette the rinse solution into the well
        _forward_pipette_v3(
            volume=vol,
            src_vessel=sol_name,
            dst_vessel=instructions.well,
            toolkit=toolkit,
        )

        # Clear the well
        _forward_pipette_v3(
            volume=vol,
            src_vessel=instructions.well,
            dst_vessel=waste_selector(
                "waste",
                instructions.rinse_vol,
            ),
            toolkit=toolkit,
        )

    return 0


# @timing_wrapper
# def __flush_v2(
#     flush_solution_name: str,
#     toolkit: Toolkit,
#     flush_volume: float = float(120.0),
#     flush_count: int = 1,
#     instructions: Optional[ExperimentBase] = None,
# ):
#     """
#     Flush the pipette tip with the designated flush_volume ul to remove any residue
#     Args:
#         waste_vials (list): The list of waste vials
#         stock_vials (list): The list of stock vials
#         flush_solution_name (str): The name of the solution to flush with
#         mill (object): The mill object
#         pump (object): The pump object
#         pumping_rate (float): The pumping rate in ml/min
#         flush_volume (float): The volume to flush with in microliters
#         flush_count (int): The number of times to flush

#     Returns:
#         None (void function) since the objects are passed by reference
#     """

#     if flush_volume > 0.000:
#         if instructions is not None:
#             instructions.set_status_and_save(ExperimentStatus.FLUSHING)
#         logger.info(
#             "Flushing pipette tip with %f ul of %s...",
#             flush_volume,
#             flush_solution_name,
#         )

#         for _ in range(flush_count):
#             __forward_pipette_v2(
#                 flush_volume,
#                 from_vessel=solution_selector(flush_solution_name, flush_volume),
#                 to_vessel=waste_selector("waste", flush_volume),
#                 toolkit=toolkit,
#             )

#         logger.debug(
#             "Flushed pipette tip with %f ul of %s %dx times...",
#             flush_volume,
#             flush_solution_name,
#             flush_count,
#         )
#     else:
#         logger.info("No flushing required. Flush volume is 0. Continuing...")
#     return 0


@timing_wrapper
def flush_pipette(
    flush_with: str,
    toolkit: Toolkit,
    flush_volume: float = 120.0,
    flush_count: int = 1,
    instructions: Optional[ExperimentBase] = None,
):
    """
    Flush the pipette tip with the designated flush_volume ul to remove any residue
    Args:
        flush_solution_name (str): The name of the solution to flush with
        toolkit (Toolkit): The toolkit object
        flush_volume (float): The volume to flush with in microliters
        flush_count (int): The number of times to flush
        instructions (ExperimentBase): The experiment instructions for setting the status

    Returns:
        None (void function) since the objects are passed by reference
    """

    if flush_volume > 0.000:
        if instructions is not None:
            instructions.set_status_and_save(ExperimentStatus.FLUSHING)
        logger.info(
            "Flushing pipette tip with %f ul of %s...",
            flush_volume,
            flush_with,
        )

        for _ in range(flush_count):
            _forward_pipette_v3(
                flush_volume,
                src_vessel=flush_with,
                dst_vessel=waste_selector("waste", flush_volume),
                toolkit=toolkit,
            )

        logger.debug(
            "Flushed pipette tip with %f ul of %s %dx times...",
            flush_volume,
            flush_with,
            flush_count,
        )
    else:
        logger.info("No flushing required. Flush volume is 0. Continuing...")
    return 0


@timing_wrapper
def purge_pipette(
    mill: Union[Mill, MockMill],
    pump: Union[SyringePump, MockPump],
):
    """
    Move the pipette over an available waste vessel and purge its contents

    Args:
        mill (Union[Mill, MockMill]): _description_
        pump (Union[Pump, MockPump]): _description_
    """
    liquid_volume = pump.pipette.liquid_volume()
    total_volume = pump.pipette.volume
    purge_vial = waste_selector("waste", liquid_volume)

    # Move to the purge vial
    mill.safe_move(
        purge_vial.x,
        purge_vial.y,
        purge_vial.top,
        tool=Instruments.PIPETTE,
    )

    # Purge the pipette
    pump.infuse(
        volume_to_infuse=liquid_volume,
        being_infused=None,
        infused_into=purge_vial,
        blowout_ul=total_volume - liquid_volume,
    )


@timing_wrapper
def solution_selector(
    solution_name: str,
    volume: float,
    db_session: Session = SessionLocal,
) -> StockVial:
    """
    Select the solution from which to withdraw from, from the list of solution objects
    Args:
        solutions (list): The list of solution objects
        solution_name (str): The name of the solution to select
        volume (float): The volume to be pipetted
    Returns:
        solution (object): The solution object
    """
    # Fetch updated solutions from the db
    stock_vials, _ = read_vials("stock", db_session)

    for solution in stock_vials:
        # if the solution names match and the requested volume is less than the available volume (volume - 10% of capacity)
        if solution.name.lower() == solution_name.lower() and round(
            float(solution.volume) - float(0.10) * float(solution.capacity), 6
        ) > (volume):
            logger.debug(
                "Selected stock vial: %s in position %s",
                solution.name,
                solution.position,
            )
            return solution
    raise NoAvailableSolution(solution_name)


@timing_wrapper
def waste_selector(
    solution_name: str,
    volume: float,
    db_session: Session = SessionLocal,
) -> WasteVial:
    """
    Select the solution in which to deposit into from the list of solution objects
    Args:
        solutions (list): The list of solution objects
        solution_name (str): The name of the solution to select
        volume (float): The volume to be pipetted
    Returns:
        solution (object): The solution object
    """
    # Fetch updated solutions from the db
    _, wate_vials = read_vials(db_session())
    solution_name = solution_name.lower()
    for waste_vial in wate_vials:
        if (
            waste_vial.name.lower() == solution_name
            and round((float(waste_vial.volume) + float(str(volume))), 6)
            < waste_vial.capacity
        ):
            logger.debug(
                "Selected waste vial: %s in position %s",
                waste_vial.name,
                waste_vial.position,
            )
            return waste_vial
    raise NoAvailableSolution(solution_name)


@timing_wrapper
def chrono_amp(
    ca_instructions: EchemExperimentBase,
    file_tag: str = None,
    custom_parameters: Union[chrono_parameters, None] = None,
) -> Tuple[EchemExperimentBase]:
    """
    Deposition of the solutions onto the substrate. This includes the OCP and CA steps.

    No pipetting is performed in this step.

    Args:
        dep_instructions (Experiment): The experiment instructions
        file_tag (str): The file tag to be used for the data files
    Returns:
        dep_instructions (Experiment): The updated experiment instructions
        dep_results (ExperimentResult): The updated experiment results
    """
    try:
        if TESTING:
            pstat = echem()
        else:
            pstat = echem
        pstat.pstatconnect()

        # echem OCP
        logger.info("Beginning eChem OCP of well: %s", ca_instructions.well_id)
        ca_instructions.set_status_and_save(ExperimentStatus.OCPCHECK)

        base_filename = pstat.setfilename(
            ca_instructions.experiment_id,
            file_tag + "_OCP_CA" if file_tag else "OCP_CA",
            ca_instructions.project_id,
            ca_instructions.project_campaign_id,
            ca_instructions.well_id,
        )
        ca_results = ca_instructions.results
        pstat.OCP(
            potentiostat_ocp_parameters.OCPvi,
            potentiostat_ocp_parameters.OCPti,
            potentiostat_ocp_parameters.OCPrate,
        )  # OCP
        pstat.activecheck()
        ocp_dep_pass, ocp_char_final_voltage = pstat.check_vf_range(base_filename)
        ca_results.set_ocp_ca_file(
            base_filename, ocp_dep_pass, ocp_char_final_voltage, file_tag
        )
        logger.info(
            "OCP of well %s passed: %s",
            ca_instructions.well_id,
            ocp_dep_pass,
        )

        # echem CA - deposition
        if not ocp_dep_pass:
            ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
            raise OCPFailure("CA")

        try:
            ca_instructions.set_status_and_save(ExperimentStatus.EDEPOSITING)
            logger.info(
                "Beginning eChem deposition of well: %s", ca_instructions.well_id
            )
            deposition_data_file = pstat.setfilename(
                ca_instructions.experiment_id,
                file_tag + "_CA" if file_tag else "CA",
                ca_instructions.project_id,
                ca_instructions.project_campaign_id,
                ca_instructions.well_id,
            )

            # FEATURE have chrono return the max and min values for the deposition
            # and save them to the results
            if custom_parameters:  # if not none then use the custom parameters
                chrono_params = custom_parameters
            else:
                chrono_params = chrono_parameters(
                    CAvi=ca_instructions.ca_prestep_voltage,
                    CAti=ca_instructions.ca_prestep_time_delay,
                    CAv1=ca_instructions.ca_step_1_voltage,
                    CAt1=ca_instructions.ca_step_1_time,
                    CAv2=ca_instructions.ca_step_2_voltage,
                    CAt2=ca_instructions.ca_step_2_time,
                    CAsamplerate=ca_instructions.ca_sample_period,
                )  # CA
            pstat.chrono(chrono_params)
            pstat.activecheck()
            ca_results.set_ca_data_file(deposition_data_file, context=file_tag)
        except Exception as e:
            ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during deposition: %s", e)
            raise CAFailure(
                ca_instructions.experiment_id, ca_instructions.well_id
            ) from e

    except OCPFailure as e:
        ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", ca_instructions.well_id)
        raise e

    except CAFailure as e:
        ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("CA of well %s failed", ca_instructions.well_id)
        raise e

    except Exception as e:
        ca_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("Exception occurred during deposition: %s", e)
        raise DepositionFailure(
            ca_instructions.experiment_id, ca_instructions.well_id
        ) from e

    finally:
        pstat.pstatdisconnect()

    return ca_instructions


@timing_wrapper
def cyclic_volt(
    cv_instructions: EchemExperimentBase,
    file_tag: str = None,
    overwrite_inital_voltage: bool = True,
    custom_parameters: cv_parameters = None,
) -> Tuple[EchemExperimentBase]:
    """
    Cyclicvoltamety in a well. This includes the OCP and CV steps.
    Will perform OCP and then set the initial voltage for the CV based on the final OCP voltage.
    To not change the instructions object, set overwrite_inital_voltage to False.
    No pipetting is performed in this step.
    Rinse the electrode after characterization.

    WARNING: Do not change the instructions initial voltage during a custom CV unless you are sure that the instructions
    are meant to be changed. The initial voltage should only be changed during regular CV step.

    Args:
        char_instructions (Experiment): The experiment instructions
        file_tag (str): The file tag to be used for the data files
        overwrite_inital_voltage (bool): Whether to overwrite the initial voltage with the final OCP voltage
        custom_parameters (potentiostat_cv_parameters): The custom CV parameters to be used

    Returns:
        char_instructions (Experiment): The updated experiment instructions
        char_results (ExperimentResult): The updated experiment results
    """
    try:
        # echem OCP
        if file_tag:
            logger.info(
                "Beginning %s OCP of well: %s", file_tag, cv_instructions.well_id
            )
        else:
            logger.info("Beginning OCP of well: %s", cv_instructions.well_id)
        if TESTING:
            pstat = echem()
        else:
            pstat = echem

        pstat.pstatconnect()
        cv_instructions.set_status_and_save(ExperimentStatus.OCPCHECK)
        ocp_char_file = pstat.setfilename(
            cv_instructions.experiment_id,
            file_tag + "_OCP_CV" if file_tag else "OCP_CV",
            cv_instructions.project_id,
            cv_instructions.project_campaign_id,
            cv_instructions.well_id,
        )

        try:
            pstat.OCP(
                OCPvi=potentiostat_ocp_parameters.OCPvi,
                OCPti=potentiostat_ocp_parameters.OCPti,
                OCPrate=potentiostat_ocp_parameters.OCPrate,
            )  # OCP
            pstat.activecheck()

        except Exception as e:
            cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during OCP: %s", e)
            raise OCPFailure("CV") from e
        (
            ocp_char_pass,
            ocp_final_voltage,
        ) = pstat.check_vf_range(ocp_char_file)
        cv_instructions.results.set_ocp_cv_file(
            ocp_char_file, ocp_char_pass, ocp_final_voltage, file_tag
        )
        logger.info(
            "OCP of well %s passed: %s",
            cv_instructions.well_id,
            ocp_char_pass,
        )

        if not ocp_char_pass:
            cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("OCP of well %s failed", cv_instructions.well_id)
            raise OCPFailure("CV")

        # echem CV - characterization
        if cv_instructions.baseline == 1:
            test_type = "CV_baseline"
            cv_instructions.set_status_and_save(ExperimentStatus.BASELINE)
        else:
            test_type = "CV"
            cv_instructions.set_status_and_save(ExperimentStatus.CHARACTERIZING)

        logger.info(
            "Beginning eChem %s of well: %s", test_type, cv_instructions.well_id
        )

        characterization_data_file = pstat.setfilename(
            cv_instructions.experiment_id,
            file_tag + "_CV" if file_tag else test_type,
            cv_instructions.project_id,
            cv_instructions.project_campaign_id,
            cv_instructions.well_id,
        )
        cv_instructions.results.set_cv_data_file(characterization_data_file, file_tag)
        # FEATURE have cyclic return the max and min values for the characterization
        # and save them to the results
        if overwrite_inital_voltage:
            cv_instructions.cv_initial_voltage = ocp_final_voltage

        if custom_parameters:  # if not none then use the custom parameters
            cv_params = custom_parameters
            cv_params.CVvi = ocp_final_voltage  # still need to set the initial voltage, not overwriting the original
        else:
            cv_params = cv_parameters(
                CVvi=cv_instructions.cv_initial_voltage,
                CVap1=cv_instructions.cv_first_anodic_peak,
                CVap2=cv_instructions.cv_second_anodic_peak,
                CVvf=cv_instructions.cv_final_voltage,
                CVsr1=cv_instructions.cv_scan_rate_cycle_1,
                CVsr2=cv_instructions.cv_scan_rate_cycle_2,
                CVsr3=cv_instructions.cv_scan_rate_cycle_3,
                CVcycle=cv_instructions.cv_cycle_count,
            )

        try:
            pstat.cyclic(cv_params)
            pstat.activecheck()

        except Exception as e:
            cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
            logger.error("Exception occurred during CV: %s", e)
            raise CVFailure(
                cv_instructions.experiment_id, cv_instructions.well_id
            ) from e

    except OCPFailure as e:
        cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("OCP of well %s failed", cv_instructions.well_id)
        raise e
    except CVFailure as e:
        cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("CV of well %s failed", cv_instructions.well_id)
        raise e
    except Exception as e:
        cv_instructions.set_status_and_save(ExperimentStatus.ERROR)
        logger.error("An unknown exception occurred during CV: %s", e)
        raise CVFailure(cv_instructions.experiment_id, cv_instructions.well_id) from e
    finally:
        pstat.pstatdisconnect()

    return cv_instructions


@timing_wrapper
def volume_correction(
    volume: float, density: float = None, viscosity: float = None
) -> float:
    """
    Corrects the volume of the solution based on the density and viscosity of the solution

    Args:
        volume (float): The volume to be corrected
        density (float): The density of the solution
        viscosity (float): The viscosity of the solution

    Returns:
        corrected_volume (float): The corrected volume
    """
    if density is None:
        density = float(1.0)
    if viscosity is None:
        viscosity = float(1.0)
    corrected_volume = round(
        volume * (float(1.0) + (float(1.0) - density) * (float(1.0) - viscosity)), 6
    )
    return float(corrected_volume)


@timing_wrapper
def image_well(
    toolkit: Toolkit,
    instructions: EchemExperimentBase = None,
    step_description: str = None,
    curvature_image: bool = False,
):
    """
    Image the well with the camera

    Args:
        toolkit (Toolkit): The toolkit object
        instructions (Experiment): The experiment instructions
        step_description (str): The description of the step
        curvature_image (bool): Whether to take a curvature image

    Returns:
        None (void function) since the objects are passed by reference
    """
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
            capture_new_image(
                save=True, num_images=1, file_name=filepath, logger=logger
            )
            toolkit.arduino.lights_off()
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

        # Post to obs
        try:
            if config.getboolean("OPTIONS", "testing") or config.getboolean(
                "OPTIONS", "use_obs"
            ):
                obs = MockOBSController()
            else:
                obs = OBSController()
            obs.change_image(new_image_path=filepath)
        except Exception as e:
            # Not critical if the image is not posted to OBS
            logger.exception("Failed to post image to OBS")
            logger.exception(e)

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


@timing_wrapper
def mix(
    toolkit: Union[Toolkit, Hardware],
    well: Well,
    volume: float,
    mix_count: int = 3,
    mix_height: float = None,
):
    """
    Mix the solution in the well by pipetting it up and down

    Args:
        toolkit (object): The toolkit object for hardware control
        well (Well, str): The well to be mixed
        volume (float): The volume to be mixed
        mix_count (int): The number of times to mix
        mix_height (float): The height to mix at
    """
    if mix_height is None:
        mix_height = well.well_data.bottom + well.well_data.height
    else:
        mix_height = well.well_data.bottom + mix_height

    if isinstance(well, str):
        well = toolkit.wellplate.get_well(well)

    logger.info("Mixing well %s %dx...", well.name, mix_count)

    # Withdraw air for blow out volume
    toolkit.pump.withdraw_air(40)

    for i in range(mix_count):
        logger.info("Mixing well %s %d of %d...", well.name, i + 1, mix_count)
        # Move to the bottom of the target well
        toolkit.mill.safe_move(
            x_coord=well.x,
            y_coord=well.y,
            z_coord=well.bottom,
            tool=Instruments.PIPETTE,
        )

        # Withdraw the solutions from the well
        toolkit.pump.withdraw(
            volume_to_withdraw=volume,
            solution=well,
            rate=toolkit.pump.max_pump_rate,
        )

        toolkit.mill.safe_move(
            x_coord=well.x,
            y_coord=well.y,
            z_coord=well.top,
            tool=Instruments.PIPETTE,
        )

        # Deposit the solution back into the well
        toolkit.pump.infuse(
            volume_to_infuse=volume,
            being_infused=None,
            infused_into=well,
            rate=toolkit.pump.max_pump_rate,
            blowout_ul=0,
        )

    toolkit.pump.infuse_air(40)
    toolkit.mill.move_to_safe_position()
    return 0


def clear_well(
    toolkit: Union[Toolkit, Hardware],
    well: Well,
):
    """
    Clear the well by pipetting the solution out of the well

    Args:
        toolkit (object): The toolkit object for hardware control
        well (Well, str): The well to be cleared
        volume (float): The volume to be cleared
    """
    if isinstance(well, str):
        well = toolkit.wellplate.get_well(well)

    logger.info("Clearing well %s...", well.name)

    transfer(
        volume=well.volume,
        src_vessel=well,
        dst_vessel=waste_selector("waste", well.volume),
        toolkit=toolkit,
    )
    return 0


def decapping_sequence(mill: Mill, target_coords: Coordinates, ard_link: ArduinoLink):
    """
    The decapping sequence is as follows:
    - Move to the target coordinates
    - Activate the decapper
    - Move the decapper up 20mm
    """

    # Move to the target coordinates
    mill.safe_move(target_coords.x, target_coords.y, target_coords.z, tool="decapper")

    # Activate the decapper
    ard_link.no_cap()

    # Move the decapper up 20mm
    mill.move_to_position(
        target_coords.x,
        target_coords.y,
        target_coords.z + 20,
        tool="decapper",
    )


def capping_sequence(mill: Mill, target_coords: Coordinates, ard_link: ArduinoLink):
    """
    The capping sequence is as follows:
    - Move to the target coordinates
    - deactivate the decapper
    - Move the decapper +10mm in the y direction
    - Move the decapper to 0 z
    """

    # Move to the target coordinates
    mill.safe_move(target_coords.x, target_coords.y, target_coords.z, tool="decapper")

    # Deactivate the decapper
    ard_link.ALL_CAP()

    # Move the decapper +10mm in the y direction
    mill.move_to_position(target_coords.x, target_coords.y + 10, 0, tool="decapper")


if __name__ == "__main__":
    pass
