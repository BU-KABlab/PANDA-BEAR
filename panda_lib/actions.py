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

# Third party or custom imports
from pathlib import Path
from typing import Optional, Tuple, Union
from PIL import Image

# First party imports
from panda_lib.imaging import capture_new_image, add_data_zone, image_filepath_generator
from panda_lib.config.config_tools import (
    read_testing_config,
    read_config,
    ConfigParserError,
)
from panda_lib.correction_factors import correction_factor
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
    ExperimentResult,
    ExperimentStatus,
)
from panda_lib.log_tools import timing_wrapper
from panda_lib.movement import Instruments, Mill, MockMill
from panda_lib.obs_controls import OBSController, MockOBSController
from panda_lib.syringepump import MockPump, SyringePump
from panda_lib.instrument_toolkit import Toolkit
from panda_lib.vials import StockVial, WasteVial, read_vials, Vessel, Vial2
from panda_lib.wellplate import Well
from panda_lib.utilities import solve_vials_ilp

TESTING = read_testing_config()

if TESTING:
    from panda_lib.gamry_potentiostat.gamry_control_mock import (
        GamryPotentiostat as echem,
    )
    from panda_lib.gamry_potentiostat.gamry_control_mock import (
        chrono_parameters,
        cv_parameters,
        potentiostat_ocp_parameters,
    )
else:
    import panda_lib.gamry_potentiostat.gamry_control as echem
    from panda_lib.gamry_potentiostat.gamry_control import (
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


@timing_wrapper
def forward_pipette_v2(
    volume: float,
    from_vessel: Union[Well, StockVial, WasteVial],
    to_vessel: Union[Well, WasteVial],
    toolkit: Toolkit,
    pumping_rate: float = None,
):
    """
    Pipette a volume from one vessel to another

    Depending on the supplied vessels, this function will perform one of the following:
    1. Pipette from a stock vial to a well
    2. Pipette from a well to a waste vial*
    3. Pipette from a stock vial to a waste vial*
        * When pipetting to a waste vial the dispesnsing height will be above the solution depth to avoid contamination

    It will not allow:
    1. Pipetting from a waste vial to a well
    2. Pipetting from a well to a stock vial
    3. Pipetting from a stock vial toa  stock vial

    The steps that this function will perform:
    1. Determine the number of repetitions
    2. Withdraw the solution from the source
        a. Withdraw an air gap to engage the screw
        b. Move to the source
        c. Withdraw the solution
        d. Move back to safe height
        e. Withdraw an air gap to prevent dripping
    3. Deposit the solution into the destination vessel
        a. Move to the destination
        b. Deposit the solution and blow out
        c. Move back to safe height
        d. If depositing stock solution into a well, the recorded weight change will be saved to the target well
            in the wellplate object and the stock vial object will be updated with a corrected new volume based on the density of the solution.
    4. Repeat 2-3 until all repetitions are complete

    Args:
        volume (float): The volume to be pipetted in microliters
        from_vessel (Vial or Well): The vessel object to be pipetted from (must be selected before calling this function)
        to_vessel (Vial or Well): The vessel object to be pipetted to (must be selected before calling this function)
        pumping_rate (float): The pumping rate in ml/min
        pump (object): The pump object
        mill (object): The mill object
        wellplate (Wells object): The wellplate object

    Returns:
        None (void function) since the objects are passed by reference

    """
    if volume <= 0.0:
        return

    logger.info(
        "Forward pipetting %f ul from %s to %s",
        volume,
        from_vessel.name,
        to_vessel.name,
    )

    # Check to ensure that the from_vessel and to_vessel are an allowed combination
    if isinstance(from_vessel, Well) and isinstance(to_vessel, StockVial):
        raise ValueError("Cannot pipette from a well to a stock vial")
    if isinstance(from_vessel, WasteVial) and isinstance(to_vessel, Well):
        raise ValueError("Cannot pipette from a waste vial to a well")
    if isinstance(from_vessel, StockVial) and isinstance(to_vessel, StockVial):
        raise ValueError("Cannot pipette from a stock vial to a stock vial")

    # Calculate the number of repetitions

    repetitions = math.ceil(volume / (toolkit.pump.pipette.capacity_ul - DRIP_STOP))
    repetition_vol = volume / repetitions

    for j in range(repetitions):
        logger.info("Repetition %d of %d", j + 1, repetitions)

        # Decap the source vial
        if isinstance(from_vessel, StockVial):
            toolkit.mill.safe_move(
                from_vessel.coordinates.x,
                from_vessel.coordinates.y,
                from_vessel.coordinates.z_top,
                Instruments.DECAPPER,
            )
            toolkit.arduino.no_cap()

        # Withdraw solution
        toolkit.pump.withdraw(volume_to_withdraw=AIR_GAP)
        toolkit.mill.safe_move(
            from_vessel.coordinates["x"],
            from_vessel.coordinates["y"],
            from_vessel.coordinates.z_bottom,
            Instruments.PIPETTE,
        )
        toolkit.pump.withdraw(
            volume_to_withdraw=repetition_vol, solution=from_vessel, rate=pumping_rate
        )
        if isinstance(from_vessel, Well):
            # Withdraw extra to try and remove of all solution
            toolkit.pump.withdraw(volume_to_withdraw=20)
        toolkit.mill.move_to_safe_position()
        toolkit.pump.withdraw(volume_to_withdraw=DRIP_STOP)

        # Cap the source vial
        if isinstance(from_vessel, StockVial):
            toolkit.mill.safe_move(
                from_vessel.coordinates.x,
                from_vessel.coordinates.y,
                from_vessel.coordinates.z_top,
                Instruments.DECAPPER,
            )
            toolkit.arduino.ALL_CAP()

        # Deposit solution

        # If the to_vessel is a waste_vial decap the vial
        if isinstance(to_vessel, WasteVial):
            toolkit.mill.safe_move(
                to_vessel.coordinates.x,
                to_vessel.coordinates.y,
                to_vessel.coordinates.z_top,
                Instruments.DECAPPER,
            )
            toolkit.arduino.no_cap()

        toolkit.mill.safe_move(
            to_vessel.coordinates.x,
            to_vessel.coordinates.y,
            to_vessel.coordinates.z_top,
            Instruments.PIPETTE,
        )
        toolkit.pump.infuse(
            volume_to_infuse=repetition_vol,
            being_infused=from_vessel,
            infused_into=to_vessel,
            blowout_ul=(
                AIR_GAP + DRIP_STOP + 20
                if isinstance(from_vessel, Well)
                else AIR_GAP + DRIP_STOP
            ),
        )

        # Purge residual solution
        for _, vol in toolkit.pump.pipette.contents.items():
            if vol > 0.0:
                logger.warning("Pipette has residual volume of %f ul. Purging...", vol)
                toolkit.pump.infuse(
                    volume_to_infuse=vol,
                    being_infused=None,
                    infused_into=to_vessel,
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
                infused_into=to_vessel,
                blowout_ul=toolkit.pump.pipette.volume,
            )
            toolkit.pump.pipette.volume = 0.0

        # Cap the destination vial
        if isinstance(to_vessel, WasteVial):
            toolkit.mill.safe_move(
                to_vessel.coordinates.x,
                to_vessel.coordinates.y,
                to_vessel.coordinates.z_top,
                Instruments.DECAPPER,
            )
            toolkit.arduino.ALL_CAP()


@timing_wrapper
def forward_pipette_v3(
    volume: float,
    src_vessel: Union[str, Well, StockVial],
    dst_vessel: Union[Well, WasteVial],
    toolkit: Toolkit,
    source_concentration: float = None,
) -> int:
    """
    Forward pipette from a given source to a given destination.
    The source may be one of the following:
        - A string representing the name of a solution
        - A Well object
        - A StockVial object
    The destination may be one of the following:
        - A Well object
        - A WasteVial object

    If the source is given as as string, the function will look up the solution in the stock vials and use it as the source.
    If a concentration is provided for the solution, multiple source vials may be used to achieve the desired concentration.

    Args:
        volume (float): The desired volume to be pipetted in microliters. Will be corrected for viscocity.
        source (Union[str, Well, StockVial]): The source vessel. Assumes a vial if a string is provided
        destination (Union[Well, WasteVial]): The destination vessel
        solution_concentration (float): The concentration of the solution to be used
        toolkit (Toolkit): The toolkit object conatining the mill, pump, arduino and wellplate
        solution_concentration (float): The concentration of the solution to be used in mol/L

    Returns:
        int: 0 if the function completes successfully
    """
    try:
        if volume <= 0.0:
            return

        # Handle when a source solution name and concentration is provided (even if concentration is none)
        selected_source_vessels: list[Vessel] = None
        source_vessel_volumes: list = None
        if isinstance(src_vessel, str):
            # Fetch updated solutions from the db
            selected_source_vessels: list[Vial2]
            stock_vials, _ = read_vials()
            selected_source_vessels = [
                vial
                for vial in stock_vials
                if vial.name == src_vessel and vial.volume > 0
            ]

            # If there are no desired stock solutions, raise an error
            if not selected_source_vessels:
                toolkit.global_logger.error("No %s vials available", src_vessel)
                raise ValueError(f"No {src_vessel} vials available")
            
            # If the source concentration is not provided, raise an error
            if source_concentration is None:
                toolkit.global_logger.error("Source concentration not provided")
                if selected_source_vessels[0].category == 0:
                    try:
                        source_concentration = float(selected_source_vessels[0].concentration)
                    except ValueError:
                        raise ValueError("Source concentration not provided")
   
            # There are one or more vials, let's calculate the volume to be pipetted from each
            # vial to get the desired volume and concentration
            source_vessel_volumes, deviation, volumes_by_position = solve_vials_ilp(
                # Concentrations of each vial position in mM
                vial_concentration_map={
                    vial.position: vial.concentration
                    for vial in selected_source_vessels
                },
                # Total volume to achieve in uL
                v_total=volume,
                # Target concentration in mM
                c_target=source_concentration,
            )

            # If the volumes are not found, raise an error
            if source_vessel_volumes is None:
                raise ValueError(
                    f"No solution combinations found for {src_vessel} {source_concentration} mM"
                )

            toolkit.global_logger.info(
                "Deviation from target concentration: %s mM", deviation
            )

            # Pair the source vessels with their respective volumes base don the volumes by position
            source_vessel_volumes = [
                (vial, volumes_by_position[vial.position])
                for vial in selected_source_vessels
            ]

            for vessel, source_vessel_volume in source_vessel_volumes:
                if source_vessel_volume > 0:
                    toolkit.global_logger.info(
                        "Pipetting %f uL from %s to achieve %f mM",
                        source_vessel_volume,
                        vessel.name,
                        source_concentration,
                    )
        else:  # If the source is a single vessel
            source_vessel_volumes = [(src_vessel, volume)]
            toolkit.global_logger.info(
                "Pipetting %f uL from %s to %s",
                volume,
                src_vessel.name,
                dst_vessel.name,
            )

        # Check to ensure that the source and destination are an allowed combination
        for origin_vessel, _ in source_vessel_volumes:
            if isinstance(origin_vessel, Well) and isinstance(dst_vessel, StockVial):
                raise ValueError("Cannot pipette from a well to a stock vial")
            if isinstance(origin_vessel, WasteVial) and isinstance(dst_vessel, Well):
                raise ValueError("Cannot pipette from a waste vial to a well")
            if isinstance(origin_vessel, StockVial) and isinstance(dst_vessel, StockVial):
                raise ValueError("Cannot pipette from a stock vial to a stock vial")

        # Cycle through the source_vials and pipette the volumes
        for vessel, desired_volume in source_vessel_volumes:
            if desired_volume <= 0.0:
                continue
            # Calculate repetitions
            vessel: Vessel
            try:
                repetitions = math.ceil(
                    desired_volume / (toolkit.pump.pipette.capacity_ul - DRIP_STOP)
                )
            except ZeroDivisionError:
                continue
            
            # We correct the volume for the viscosity of the solution at this point
            # to ensure that the correct volume is withdrawn but also to ensure that the same
            # volume is sent to the pump for deposition so that the pump returns to the same position
            # and doesn't drift over time.

            # We dont do it at the pump level so that we dont need to passs the viscosity of the solution
            # to the pump every time we withdraw or infuse.
            repetition_vol = correction_factor(
                desired_volume / repetitions, vessel.viscosity_cp
            )
            logger.info(
                "Pipetting %f uL from %s to %s",
                desired_volume,
                vessel.name,
                dst_vessel.name,
            )
            for j in range(repetitions):
                logger.info("Repetition %d of %d", j + 1, repetitions)

                # Decap the source vial
                if isinstance(vessel, StockVial):
                    toolkit.mill.safe_move(
                        vessel.coordinates.x,
                        vessel.coordinates.y,
                        vessel.coordinates.z_top,
                        Instruments.DECAPPER,
                    )
                    toolkit.arduino.no_cap()

                # Withdraw solution
                toolkit.pump.withdraw(volume_to_withdraw=AIR_GAP)
                toolkit.mill.safe_move(
                    vessel.coordinates["x"],
                    vessel.coordinates["y"],
                    vessel.coordinates.z_bottom,
                    Instruments.PIPETTE,
                )
                toolkit.pump.withdraw(
                    volume_to_withdraw=repetition_vol, solution=vessel
                )
                if isinstance(vessel, Well):
                    # Withdraw extra to try and remove of all solution
                    toolkit.pump.withdraw(volume_to_withdraw=20)
                toolkit.mill.move_to_safe_position()
                toolkit.pump.withdraw(volume_to_withdraw=DRIP_STOP)

                # Cap the source vial
                if isinstance(vessel, StockVial):
                    toolkit.mill.safe_move(
                        vessel.coordinates.x,
                        vessel.coordinates.y,
                        vessel.coordinates.z_top,
                        Instruments.DECAPPER,
                    )
                    toolkit.arduino.ALL_CAP()

                # Deposit solution

                # If the to_vessel is a waste_vial decap the vial
                if isinstance(dst_vessel, WasteVial):
                    toolkit.mill.safe_move(
                        dst_vessel.coordinates.x,
                        dst_vessel.coordinates.y,
                        dst_vessel.coordinates.z_top,
                        Instruments.DECAPPER,
                    )
                    toolkit.arduino.no_cap()

                toolkit.mill.safe_move(
                    dst_vessel.coordinates.x,
                    dst_vessel.coordinates.y,
                    dst_vessel.coordinates.z_top,
                    Instruments.PIPETTE,
                )
                toolkit.pump.infuse(
                    volume_to_infuse=repetition_vol,
                    being_infused=vessel,
                    infused_into=dst_vessel,
                    blowout_ul=(
                        AIR_GAP + DRIP_STOP + 20
                        if isinstance(vessel, Well)
                        else AIR_GAP + DRIP_STOP
                    ),
                )

                # Purge residual solution
                for _, vol in toolkit.pump.pipette.contents.items():
                    if vol > 0.0:
                        logger.warning(
                            "Pipette has residual volume of %f ul. Purging...", vol
                        )
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

                # Cap the destination vial
                if isinstance(dst_vessel, WasteVial):
                    toolkit.mill.safe_move(
                        dst_vessel.coordinates.x,
                        dst_vessel.coordinates.y,
                        dst_vessel.coordinates.z_top,
                        Instruments.DECAPPER,
                    )
                    toolkit.arduino.ALL_CAP()
    except Exception as e:
        toolkit.global_logger.error("Exception occurred during pipetting: %s", e)
        raise e
    return 0


@timing_wrapper
def rinse_v2(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    Rinse the well with rinse_vol ul.
    Involves pipetteing and then clearing the well with no purging steps

    Args:
        instructions (Experiment): The experiment instructions
        toolkit (Toolkit): The toolkit object
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
    Returns:
        None (void function) since the objects are passed by reference
    """

    logger.info(
        "Rinsing well %s %dx...", instructions.well_id, instructions.rinse_count
    )
    instructions.set_status_and_save(ExperimentStatus.RINSING)
    for _ in range(instructions.rinse_count):
        # Pipette the rinse solution into the well
        forward_pipette_v2(
            volume=correction_factor(instructions.rinse_vol),
            from_vessel=solution_selector(
                "rinse",
                instructions.rinse_vol,
            ),
            to_vessel=toolkit.wellplate.wells[instructions.well_id],
            toolkit=toolkit,
            pumping_rate=toolkit.pump.max_pump_rate,
        )
        toolkit.mill.safe_move(
            x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
            y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
            z_coord=toolkit.wellplate.z_top,
            instrument=Instruments.PIPETTE,
        )
        # Clear the well
        forward_pipette_v2(
            volume=correction_factor(instructions.rinse_vol),
            from_vessel=toolkit.wellplate.wells[instructions.well_id],
            to_vessel=waste_selector(
                "waste",
                instructions.rinse_vol,
            ),
            toolkit=toolkit,
        )

    return 0

@timing_wrapper
def rinse_v3(
    instructions: EchemExperimentBase,
    toolkit: Toolkit,
):
    """
    Rinse the well with rinse_vol ul.
    Involves pipetteing and then clearing the well with no purging steps

    Args:
        instructions (Experiment): The experiment instructions
        toolkit (Toolkit): The toolkit object
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
    Returns:
        None (void function) since the objects are passed by reference
    """

    logger.info(
        "Rinsing well %s %dx...", instructions.well_id, instructions.rinse_count
    )
    instructions.set_status_and_save(ExperimentStatus.RINSING)
    for _ in range(instructions.rinse_count):
        # Pipette the rinse solution into the well
        forward_pipette_v3(
            volume=instructions.rinse_vol,
            src_vessel="rinse",
            dst_vessel=toolkit.wellplate.wells[instructions.well_id],
            toolkit=toolkit,
        )
        # toolkit.mill.safe_move(
        #     x_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
        #     y_coord=toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
        #     z_coord=toolkit.wellplate.z_top,
        #     instrument=Instruments.PIPETTE,
        # )
        # Clear the well
        forward_pipette_v3(
            volume=instructions.rinse_vol,
            src_vessel=toolkit.wellplate.wells[instructions.well_id],
            dst_vessel=waste_selector(
                "waste",
                instructions.rinse_vol,
            ),
            toolkit=toolkit,
        )

    return 0

@timing_wrapper
def flush_v2(
    flush_solution_name: str,
    toolkit: Toolkit,
    flush_volume: float = float(120.0),
    flush_count: int = 1,
    instructions: Optional[ExperimentBase] = None,
):
    """
    Flush the pipette tip with the designated flush_volume ul to remove any residue
    Args:
        waste_vials (list): The list of waste vials
        stock_vials (list): The list of stock vials
        flush_solution_name (str): The name of the solution to flush with
        mill (object): The mill object
        pump (object): The pump object
        pumping_rate (float): The pumping rate in ml/min
        flush_volume (float): The volume to flush with in microliters
        flush_count (int): The number of times to flush

    Returns:
        None (void function) since the objects are passed by reference
    """

    if flush_volume > 0.000:
        if instructions is not None:
            instructions.set_status_and_save(ExperimentStatus.FLUSHING)
        logger.info(
            "Flushing pipette tip with %f ul of %s...",
            flush_volume,
            flush_solution_name,
        )

        for _ in range(flush_count):
            forward_pipette_v2(
                flush_volume,
                from_vessel=solution_selector(flush_solution_name, flush_volume),
                to_vessel=waste_selector("waste", flush_volume),
                toolkit=toolkit,
            )

        logger.debug(
            "Flushed pipette tip with %f ul of %s %dx times...",
            flush_volume,
            flush_solution_name,
            flush_count,
        )
    else:
        logger.info("No flushing required. Flush volume is 0. Continuing...")
    return 0


@timing_wrapper
def flush_v3(
    flush_solution_name: str,
    toolkit: Toolkit,
    flush_volume: float = 120.0,
    flush_count: int = 1,
    instructions: Optional[ExperimentBase] = None,
):
    """
    Flush the pipette tip with the designated flush_volume ul to remove any residue
    Args:
        waste_vials (list): The list of waste vials
        stock_vials (list): The list of stock vials
        flush_solution_name (str): The name of the solution to flush with
        mill (object): The mill object
        pump (object): The pump object
        pumping_rate (float): The pumping rate in ml/min
        flush_volume (float): The volume to flush with in microliters
        flush_count (int): The number of times to flush

    Returns:
        None (void function) since the objects are passed by reference
    """

    if flush_volume > 0.000:
        if instructions is not None:
            instructions.set_status_and_save(ExperimentStatus.FLUSHING)
        logger.info(
            "Flushing pipette tip with %f ul of %s...",
            flush_volume,
            flush_solution_name,
        )

        for _ in range(flush_count):
            forward_pipette_v3(
                flush_volume,
                src_vessel=flush_solution_name,
                dst_vessel=waste_selector("waste", flush_volume),
                toolkit=toolkit,
            )

        logger.debug(
            "Flushed pipette tip with %f ul of %s %dx times...",
            flush_volume,
            flush_solution_name,
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
        waste_vials (Sequence[WasteVial]): _description_
        mill (Union[Mill, MockMill]): _description_
        pump (Union[Pump, MockPump]): _description_
    """
    liquid_volume = pump.pipette.liquid_volume()
    total_volume = pump.pipette.volume
    purge_vial = waste_selector("waste", liquid_volume)

    # Move to the purge vial
    mill.safe_move(
        purge_vial.coordinates.x,
        purge_vial.coordinates.y,
        purge_vial.coordinates.z_top,
        Instruments.PIPETTE,
    )

    # Purge the pipette
    pump.infuse(
        volume_to_infuse=liquid_volume,
        being_infused=None,
        infused_into=purge_vial,
        blowout_ul=total_volume - liquid_volume,
    )


@timing_wrapper
def solution_selector(solution_name: str, volume: float) -> StockVial:
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
    stock_vials, _ = read_vials()

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
def waste_selector(solution_name: str, volume: float) -> WasteVial:
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
    _, wate_vials = read_vials()
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
) -> Tuple[EchemExperimentBase, ExperimentResult]:
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

    return ca_instructions, ca_results


@timing_wrapper
def cyclic_volt(
    cv_instructions: EchemExperimentBase,
    file_tag: str = None,
    overwrite_inital_voltage: bool = True,
    custom_parameters: cv_parameters = None,
) -> Tuple[EchemExperimentBase, ExperimentResult]:
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

    return cv_instructions, cv_instructions.results


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
                toolkit.wellplate.get_coordinates(instructions.well_id, "x"),
                toolkit.wellplate.get_coordinates(instructions.well_id, "y"),
                toolkit.wellplate.image_height,
                Instruments.LENS,
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
            capture_new_image(save=True, num_images=1, file_name=filepath)
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


# @timing_wrapper
# def image_filepath_generator(
#     exp_id: int = "test",
#     project_id: int = "test",
#     project_campaign_id: int = "test",
#     well_id: str = "test",
#     step_description: str = None,
# ) -> Path:
#     """
#     Generate the file path for the image
#     """
#     # create file name
#     if step_description is not None:
#         file_name = f"{project_id}_{project_campaign_id}_{exp_id}_{well_id}_{step_description}_image"
#     else:
#         file_name = f"{project_id}_{project_campaign_id}_{exp_id}_{well_id}_image"
#     file_name = file_name.replace(" ", "_")  # clean up the file name
#     file_name_start = file_name + "_0"  # enumerate the file name
#     filepath = Path(PATH_TO_DATA / str(file_name_start)).with_suffix(".tiff")
#     i = 1
#     while filepath.exists():
#         next_file_name = f"{file_name}_{i}"
#         filepath = Path(PATH_TO_DATA / str(next_file_name)).with_suffix(".tiff")
#         i += 1
#     return filepath


@timing_wrapper
def mix(
    mill: Union[Mill, MockMill],
    pump: Union[SyringePump, MockPump],
    well: Well,
    well_id: str,
    volume: float,
    mix_count: int = 3,
    mix_height: float = None,
):
    """
    Mix the solution in the well by pipetting it up and down

    Args:
        mill (object): The mill object
        pump (object): The pump object
        wellplate (object): The wellplate object
        well_id (str): The well to be mixed
        volume (float): The volume to be mixed
        mix_count (int): The number of times to mix
        mix_height (float): The height to mix at
    """
    if mix_height is None:
        mix_height = well.depth + well.height
    else:
        mix_height = well.depth + mix_height

    logger.info("Mixing well %s %dx...", well_id, mix_count)

    # Withdraw air for blow out volume
    pump.withdraw_air(40)

    for i in range(mix_count):
        logger.info("Mixing well %s %d of %d...", well_id, i + 1, mix_count)
        # Move to the bottom of the target well
        mill.safe_move(
            x_coord=well.coordinates.x,
            y_coord=well.coordinates.y,
            z_coord=well.depth,
            instrument=Instruments.PIPETTE,
        )

        # Withdraw the solutions from the well
        pump.withdraw(
            volume_to_withdraw=volume,
            solution=well,
            rate=pump.max_pump_rate,
            weigh=False,
        )

        mill.safe_move(
            x_coord=well.coordinates.x,
            y_coord=well.coordinates.y,
            z_coord=mix_height,
            instrument=Instruments.PIPETTE,
        )

        # Deposit the solution back into the well
        pump.infuse(
            volume_to_infuse=volume,
            being_infused=None,
            infused_into=well,
            rate=pump.max_pump_rate,
            blowout_ul=0,
            weigh=False,
        )

    pump.infuse_air(40)
    mill.move_to_safe_position()
    return 0


if __name__ == "__main__":
    pass
