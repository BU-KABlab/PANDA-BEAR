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
# pylint: disable=line-too-long, too-many-arguments, too-many-lines

# Standard library imports
import json
import logging
import math
from datetime import datetime
import sys
from typing import Optional, Tuple, Union, Sequence
import pytz as tz

# Third party or custom imports
import gamry_control_WIP as echem
#import gamry_control_WIP_mock as echem

from experiment_class import (
    ExperimentResult,
    ExperimentStatus,
    ExperimentBase,
    PEG2P_Test_Instructions,
    LayeredExperiments,
    EchemExperimentBase
)
from log_tools import CustomLoggingFilter
from mill_control import Mill, Instruments, MockMill
from pump_control import MockPump, Pump
from vials import Vessel, Vial, Vial2, StockVial, WasteVial
from wellplate import Wells, Well, Wells2
from config.config import (
    PATH_TO_NETWORK_LOGS,
    AIR_GAP,
    DRIP_STOP,
    PURGE_VOLUME,
)
# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger("e_panda")
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(message)s")
system_handler = logging.FileHandler(PATH_TO_NETWORK_LOGS / "ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

def forward_pipette_v2(
        volume: float,
        from_vessel: Vessel,
        to_vessel: Vessel,
        pump: Union[Pump, MockPump],
        mill: Union[Mill, MockMill],
        pumping_rate: Optional[float] = None,
    ):
    """
    Pipette a volume from one vessel to another. This depreciates the clear_well function.

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
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials

    Returns:
        None (void function) since the objects are passed by reference
        
    """
    if volume > 0.00:
        logger.info("Forward pipetting %f ul from %s to %s", volume, from_vessel.name, to_vessel.name)
        # Check to ensure that the from_vessel and to_vessel are an allowed combination
        if isinstance(from_vessel, Well) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a well to a vial")
        elif isinstance(from_vessel, WasteVial) and isinstance(to_vessel, Well):
            raise ValueError("Cannot pipette from a waste vial to a well")
        elif isinstance(from_vessel, StockVial) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a stock vial to a stock vial")

        # Calculate the number of repetitions
        # based on pipette capacity and drip stop
        if pumping_rate is None:
            pumping_rate = pump.max_pump_rate

        repetitions = math.ceil(
            volume / (pump.pipette_capacity_ul - DRIP_STOP)
        )
        repetition_vol = volume / repetitions

        for j in range(repetitions):
            logger.info("Repetition %d of %d", j + 1, repetitions)
            # First half: pick up solution
            logger.debug("Withdrawing %f of air gap...", AIR_GAP)

            # withdraw a little to engange screw receive nothing
            pump.withdraw(
                volume=AIR_GAP,
                solution= None,
                rate=pumping_rate
            )  # withdraw air gap to engage screw

            logger.info("Moving to %s...", from_vessel.name)
            mill.safe_move(
                from_vessel.coordinates["x"],
                from_vessel.coordinates["y"],
                from_vessel.depth,
                Instruments.PIPETTE,
            )  # go to solution depth
            # Withdraw the solution from the source and receive the updated vessel object
            pump.withdraw(
                volume=repetition_vol,
                solution=from_vessel,
                rate=pumping_rate,
                weigh= False
            )  # pipette now has air gap + repitition vol

            mill.move_to_safe_position()

            # Withdraw an air gap to prevent dripping, receive nothing
            pump.withdraw(
                volume=DRIP_STOP,
                solution= None,
                rate=pumping_rate,
                weigh= False
            )
            logger.debug("From Vessel %s volume: %f depth: %f", from_vessel.name, from_vessel.volume, from_vessel.depth)
            # Second Half: Deposit to to_vessel
            logger.info("Moving to: %s...", to_vessel.name)
            # determine if the destination is a well or a waste vial
            if isinstance(to_vessel, Well): # go to solution depth
                mill.safe_move(
                    to_vessel.coordinates["x"],
                    to_vessel.coordinates["y"],
                    0,
                    Instruments.PIPETTE,
                )
            else: # go to safe height above waste vial
                mill.safe_move(
                    to_vessel.coordinates["x"],
                    to_vessel.coordinates["y"],
                    to_vessel.depth + 5 , # depth but slightly higher to avoid contamination
                    Instruments.PIPETTE,
                )

            # Infuse into the to_vessel and receive the updated vessel object
            pump.infuse(
                volume_to_infuse=repetition_vol,
                being_infused=from_vessel,
                infused_into=to_vessel,
                rate=pumping_rate,
                blowout_ul= AIR_GAP + DRIP_STOP,
                weigh= True
            )

            # Update the contentes of the to_vessel
            # TODO change from repitition volume to corrected volume
            to_vessel.update_contents(from_vessel, repetition_vol)

            logger.info(
                "Vessel %s volume: %f depth: %f",
                to_vessel.name,
                to_vessel.volume,
                to_vessel.depth,
            )

            mill.move_to_safe_position()

def reverse_pipette_v2(
        volume: float,
        from_vessel: Vessel,
        to_vessel: Vessel,
        purge_vessel: WasteVial,
        pump: Union[Pump, MockPump],
        mill: Union[Mill, MockMill],
        pumping_rate: Optional[float] = None,
    ):
    """
    Reverse Pipette a volume from one vessel to another. This depreciates the clear_well function.

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
        c. Withdraw the solution volume + purge volume
        d. Move back to safe height
        e. Withdraw an air gap to prevent dripping
    3. Deposit the solution into the destination vessel
        a. Move to the destination
        b. Deposit the solution and blow out
        c. Move to the purge vessel
        d. Purge the purge volume
        If depositing stock solution into a well, the recorded weight change will be saved to the target well 
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
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials

    Returns:
        None (void function) since the objects are passed by reference
        
    """
    purge_volume = PURGE_VOLUME
    if volume > 0.00:
        logger.info("Reverse pipetting %f ul from %s to %s", volume, from_vessel.name, to_vessel.name)
        # Check to ensure that the from_vessel and to_vessel are an allowed combination
        if isinstance(from_vessel, Well) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a well to a vial")
        elif isinstance(from_vessel, WasteVial) and isinstance(to_vessel, Well):
            raise ValueError("Cannot pipette from a waste vial to a well")
        elif isinstance(from_vessel, StockVial) and isinstance(to_vessel, StockVial):
            raise ValueError("Cannot pipette from a stock vial to a stock vial")

        # Calculate the number of repetitions
        # based on pipette capacity and drip stop
        if pumping_rate is None:
            pumping_rate = pump.max_pump_rate

        repetitions = math.ceil(
            volume / (pump.pipette_capacity_ul - DRIP_STOP - purge_volume)
        )
        repetition_vol = volume / repetitions

        for j in range(repetitions):
            logger.info("Repetition %d of %d", j + 1, repetitions)
            # First half: pick up solution
            logger.debug("Withdrawing %f of air gap...", AIR_GAP)

            # withdraw a little to engange screw receive nothing
            pump.withdraw(
                volume=AIR_GAP,
                solution= None,
                rate=pumping_rate
            )  # withdraw air gap to engage screw

            logger.info("Moving to %s...", from_vessel.name)
            mill.safe_move(
                from_vessel.coordinates["x"],
                from_vessel.coordinates["y"],
                from_vessel.z_bottom, #from_vessel.depth,
                Instruments.PIPETTE,
            )  # go to solution depth (depth replaced with height)

            # Withdraw the solution from the source and receive the updated vessel object
            pump.withdraw(
                volume=repetition_vol + purge_volume,
                solution=from_vessel,
                rate=pumping_rate,
                weigh= False
            )  # pipette now has air gap + repitition vol + purge volume

            mill.move_to_safe_position()

            # Withdraw an air gap to prevent dripping, receive nothing
            pump.withdraw(
                volume=DRIP_STOP,
                solution= None,
                rate=pumping_rate,
                weigh= False
            ) # pipette now has air gap + repitition vol + purge volume + drip stop

            # Second Half: Deposit to to_vessel
            logger.info("Moving to: %s...", to_vessel.name)
            # determine if the destination is a well or a waste vial
            if isinstance(to_vessel, Well): # go to solution depth
                logger.debug("%s is a Well", to_vessel.name)
                mill.safe_move(
                    to_vessel.coordinates["x"],
                    to_vessel.coordinates["y"],
                    0,
                    Instruments.PIPETTE,
                )
                logger.info("Moved to well %s", to_vessel.name)
            else: # go to safe height above vial
                logger.debug("%s is a Vial", to_vessel.name)
                mill.safe_move(
                    to_vessel.coordinates["x"],
                    to_vessel.coordinates["y"],
                    from_vessel.z_bottom, #to_vessel.depth + 5 ,
                    Instruments.PIPETTE,
                )
                logger.info("Moved to vial %s", to_vessel.name)

            # Infuse into the to_vessel and receive the updated vessel object
            logger.info("Infusing %s into %s", from_vessel.name, to_vessel.name)
            pump.infuse(
                volume_to_infuse=repetition_vol,
                being_infused=from_vessel,
                infused_into=to_vessel,
                rate=pumping_rate,
                blowout_ul= DRIP_STOP,
                weigh= True
            ) # pipette now has purge volume
            logger.info("Infused %s into %s. Moving to safe position", from_vessel.name, to_vessel.name)
            mill.move_to_safe_position()
            logger.info("Moved to safe position")
            # Update the contentes of the to_vessel
            # TODO change from repitition volume to corrected volume
            logger.debug("Updating contents of %s", to_vessel.name)
            to_vessel.update_contents(from_vessel, repetition_vol)

            logger.info(
                "Vessel %s volume: %f",
                to_vessel.name,
                to_vessel.volume,
            )
            logger.info("Withdrawing the drip stop...")
            pump.withdraw(
                volume=DRIP_STOP,
                solution= None,
                rate=pumping_rate,
                weigh= False
            ) # pipette now has purge volume + air gap + drip stop
            logger.info("Moving to purge vial %s...", purge_vessel.name)
            mill.safe_move(
                purge_vessel.coordinates["x"],
                purge_vessel.coordinates["y"],
                purge_vessel.height,
                Instruments.PIPETTE,
            )
            logger.info("Purging the purge volume")
            pump.infuse(
                volume_to_infuse=purge_volume,
                being_infused=from_vessel,
                infused_into=purge_vessel,
                rate=pumping_rate,
                blowout_ul= DRIP_STOP + AIR_GAP,
                weigh= False # Vials are not on the scale
            ) # Pipette should be empty after this
            logger.info("Purged the purge volume, updating contents of %s - %s", purge_vessel.position, purge_vessel.name)
            purge_vessel.update_contents(from_vessel, purge_volume)

            mill.move_to_safe_position()

def rinse_v2(
    wellplate: Wells2,
    instructions: ExperimentBase,
    pump: Pump,
    mill: Mill,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Rinse the well with rinse_vol ul.
    Involves pipetteing and then clearing the well with no purging steps

    Args:
        wellplate (Wells object): The wellplate object
        target_well (str): The alphanumeric name of the well you would like to rinse
        pumping_rate (float): The pumping rate in ml/min
        pump (object): The pump object
        waste_vials (list): The list of waste vials
        mill (object): The mill object
        rinse_repititions (int): The number of times to rinse
        rinse_vol (float): The volume to rinse with in microliters
    Returns:
        None (void function) since the objects are passed by reference
    """

    logger.info(
        "Rinsing well %s %dx...", instructions.target_well, instructions.rinse_count
    )
    for rep in range(instructions.rinse_count):  # 0, 1, 2...
        rinse_solution_name = "rinse" + str(rep)
        # purge_vial = waste_selector(rinse_solution_name, rinse_vol)
        # rinse_solution = solution_selector(stock_vials, rinse_solution_name, rinse_vol)
        logger.info("Rinse %d of %d", rep + 1, instructions.rinse_count)

        # Withdraw the rinse volume from the rinse solution into the well
        rinse_solution = solution_selector(stock_vials, rinse_solution_name, instructions.rinse_vol)
        forward_pipette_v2(
            instructions.rinse_vol,
            from_vessel=rinse_solution,
            to_vessel=wellplate[instructions.target_well],
            pump=pump,
            mill=mill,
            pumping_rate=None,
        )
        # Remove the rinse volume from the well to a waste vial
        rinse_waste = waste_selector(waste_vials, rinse_solution_name, instructions.rinse_vol)
        forward_pipette_v2(
            instructions.rinse_vol,
            from_vessel=wellplate[instructions.target_well],
            to_vessel=rinse_waste,
            pump=pump,
            mill=mill,
            pumping_rate=None,
        )

        logger.info("Rinse %d of %d complete", rep + 1, instructions.rinse_count)
        logger.debug(
            "Remaining volume in well: %f", wellplate.get_volume(instructions.target_well)
        )
    return 0

def flush_v2(
    waste_vials: Sequence[WasteVial],
    stock_vials: Sequence[StockVial],
    flush_solution_name: str,
    mill: Mill,
    pump: Pump,
    pumping_rate=0.5,
    flush_volume=120,
    ):
    """
    Flush the pipette tip with the designated flush_volume ul of DMF to remove any residue
    Args:
        pump (object): The pump object
        waste_vials (list): The list of waste vials
        stock_vials (list): The list of stock vials
        flush_solution_name (str): The name of the flush solution
        mill (object): The mill object
        pumping_rate (float): The pumping rate in ml/min
        flush_volume (float): The volume to flush with in microliters

    Returns:
        stock_vials (list): The updated list of stock vials
        waste_vials (list): The updated list of waste vials
    """

    if flush_volume > 0.000:
        logger.info(
            "Flushing pipette tip with %f ul of %s...",
            flush_volume,
            flush_solution_name,
        )
        flush_solution = solution_selector(
            stock_vials, flush_solution_name, flush_volume
        )
        waste_vial = waste_selector(waste_vials, "waste", flush_volume)

        forward_pipette_v2(
            flush_volume,
            from_vessel=flush_solution,
            to_vessel=waste_vial,
            pump=pump,
            mill=mill,
            pumping_rate=pumping_rate,
        )

        logger.info("Flushed pipette tip with %f ul of %s...", flush_volume, flush_solution_name)
    else:
        logger.info("No flushing required. Flush volume is 0. Continuing...")
    return 0

def solution_selector(solutions: Sequence[StockVial], solution_name: str, volume: float) -> StockVial:
    """
    Select the solution from which to withdraw from, from the list of solution objects
    Args:
        solutions (list): The list of solution objects
        solution_name (str): The name of the solution to select
        volume (float): The volume to be pipetted
    Returns:
        solution (object): The solution object
    """
    for solution in solutions:
        # if the solution names match and the requested volume is less than the available volume (volume - 15% of capacity)
        if (
            solution.name.lower() == solution_name.lower() 
            and solution.volume - 0.20*solution.capacity > (volume)
        ):
            logger.debug(
                "Selected stock vial: %s in position %s",
                solution.name,
                solution.position,
            )
            return solution
    raise NoAvailableSolution(solution_name)


def waste_selector(solutions: Sequence[WasteVial], solution_name: str, volume: float) -> WasteVial:
    """
    Select the solution in which to deposit into from the list of solution objects
    Args:
        solutions (list): The list of solution objects
        solution_name (str): The name of the solution to select
        volume (float): The volume to be pipetted
    Returns:
        solution (object): The solution object
    """
    solution_name = solution_name.lower()
    for waste_solution in solutions:
        if (
            waste_solution.name.lower() == solution_name
            and (waste_solution.volume + volume) < waste_solution.capacity
        ):
            logger.debug(
                "Selected waste vial: %s in position %s",
                waste_solution.name,
                waste_solution.position,
            )
            return waste_solution
    raise NoAvailableSolution(solution_name)


def deposition(
    dep_instructions: EchemExperimentBase,
    dep_results: ExperimentResult,
    mill: Mill,
    wellplate: Wells,
) -> Tuple[EchemExperimentBase, ExperimentResult]:
    """
    Deposition of the solutions onto the substrate. This includes the OCP and CA steps.

    No pipetting is performed in this step.

    Args:
        dep_instructions (Experiment): The experiment instructions
        dep_results (ExperimentResult): The experiment results
        mill (object): The mill object
        wellplate (Wells object): The wellplate object
    Returns:
        dep_instructions (Experiment): The updated experiment instructions
        dep_results (ExperimentResult): The updated experiment results
    """
    # echem setup
    logger.info("Setting up eChem experiments...")
    echem.pstatconnect()
    # echem OCP
    logger.info("Beginning eChem OCP of well: %s", dep_instructions.target_well)
    dep_instructions.status = ExperimentStatus.OCPCHECK
    mill.safe_move(
        wellplate.get_coordinates(dep_instructions.target_well)["x"],
        wellplate.get_coordinates(dep_instructions.target_well)["y"],
        wellplate.echem_height,
        Instruments.ELECTRODE
    )  # move to well depth
    base_filename = echem.setfilename(dep_instructions.id, "OCP")
    dep_results.ocp_dep_file = base_filename
    echem.OCP(
        echem.potentiostat_ocp_parameters.OCPvi,
        echem.potentiostat_ocp_parameters.OCPti,
        echem.potentiostat_ocp_parameters.OCPrate,
    )  # OCP
    echem.activecheck()
    dep_results.ocp_dep_pass = echem.check_vf_range(
        dep_results.ocp_dep_file.with_suffix(".txt")
    )

    # echem CA - deposition
    if dep_results.ocp_dep_pass:
        dep_instructions.status = ExperimentStatus.DEPOSITING
        logger.info(
            "Beginning eChem deposition of well: %s", dep_instructions.target_well
        )
        dep_results.deposition_data_file = echem.setfilename(dep_instructions.id, "CA")

        # TODO have chrono return the max and min values for the deposition
        # and save them to the results
        # don't have any parameters hardcoded, switch these all to instructions
        echem.chrono(
            echem.potentiostat_ca_parameters.CAvi,
            echem.potentiostat_ca_parameters.CAti,
            CAv1=dep_instructions.dep_pot,
            CAt1=dep_instructions.dep_duration,
            CAv2=echem.potentiostat_ca_parameters.CAv2,
            CAt2=echem.potentiostat_ca_parameters.CAt2,
            CAsamplerate=dep_instructions.ca_sample_period,
        )  # CA

        echem.activecheck()
        mill.move_to_safe_position()  # move to safe height above target well

        mill.rinse_electrode()
        echem.pstatdisconnect()

    else:
        echem.pstatdisconnect()
        raise OCPFailure("CA")

    return dep_instructions, dep_results


def characterization(
    char_instructions: EchemExperimentBase,
    char_results: ExperimentResult,
    mill: Mill,
    wellplate: Wells,
) -> Tuple[EchemExperimentBase, ExperimentResult]:
    """
    Characterization of the solutions on the substrate

    No pipetting is performed in this step.

    Args:
        char_instructions (Experiment): The experiment instructions
        char_results (ExperimentResult): The experiment results
        mill (object): The mill object
        wellplate (Wells object): The wellplate object
    Returns:
        char_instructions (Experiment): The updated experiment instructions
        char_results (ExperimentResult): The updated experiment results
    """
    logger.info("Characterizing well: %s", char_instructions.target_well)
    # echem OCP
    logger.info("Beginning eChem OCP of well: %s", char_instructions.target_well)
    echem.pstatconnect()
    char_instructions.status = ExperimentStatus.OCPCHECK
    mill.safe_move(
        wellplate.get_coordinates(char_instructions.target_well)["x"],
        wellplate.get_coordinates(char_instructions.target_well)["y"],
        wellplate.echem_height,
        Instruments.ELECTRODE,
    )  # move to well depth
    char_results.ocp_char_file = echem.setfilename(char_instructions.id, "OCP_char")
    echem.OCP(
        echem.potentiostat_ocp_parameters.OCPvi,
        echem.potentiostat_ocp_parameters.OCPti,
        echem.potentiostat_ocp_parameters.OCPrate,
    )  # OCP
    echem.activecheck()
    char_results.ocp_char_pass = echem.check_vf_range(
        char_results.ocp_char_file.with_suffix(".txt")
    )
    # echem CV - characterization
    if char_results.ocp_char_pass:
        if char_instructions.baseline == 1:
            test_type = "CV_baseline"
            char_instructions.status = ExperimentStatus.BASELINE
        else:
            test_type = "CV"
            char_instructions.status = ExperimentStatus.CHARACTERIZING

        logger.info(
            "Beginning eChem %s of well: %s", test_type, char_instructions.target_well
        )

        char_results.characterization_data_file = echem.setfilename(
            char_instructions.id, test_type
        )

        # TODO have cyclic return the max and min values for the characterization
        # and save them to the results
        echem.cyclic(
            echem.potentiostat_cv_parameters.CVvi,
            echem.potentiostat_cv_parameters.CVap1,
            echem.potentiostat_cv_parameters.CVap2,
            echem.potentiostat_cv_parameters.CVvf,
            CVsr1=char_instructions.cv_scan_rate,
            CVsr2=char_instructions.cv_scan_rate,
            CVsr3=char_instructions.cv_scan_rate,
            CVsamplerate=(
                echem.potentiostat_cv_parameters.CVstep / char_instructions.cv_scan_rate
            ),
            CVcycle=echem.potentiostat_cv_parameters.CVcycle,
        )
        echem.activecheck()
        mill.move_to_safe_position()  # move to safe height above target well
        mill.rinse_electrode()
        echem.pstatdisconnect()
        return char_instructions, char_results
    else:
        echem.pstatdisconnect()
        raise OCPFailure("CV")

def apply_log_filter(experiment_id: int, target_well: Optional[str] = None, campaign_id: Optional[str] = None):
    """Add custom value to log format"""
    experiment_formatter = logging.Formatter(
        "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(custom1)s&%(custom2)s&%(custom3)s&%(message)s"
    )
    system_handler.setFormatter(experiment_formatter)
    custom_filter = CustomLoggingFilter(campaign_id, experiment_id, target_well)
    logger.addFilter(custom_filter)

# def standard_experiment_protocol(
#     instructions: ExperimentBase,
#     results: ExperimentResult,
#     mill: Mill,
#     pump: Pump,
#     stock_vials: Sequence[Vial],
#     waste_vials: Sequence[Vial],
#     wellplate: Wells,
# ) -> Tuple[ExperimentBase, ExperimentResult, Sequence[Vial], Sequence[Vial], Wells]:
#     """
#     Run the standard experiment:
#     1. Deposit solutions into well
#         for each solution:
#             a. Withdraw air gap
#             b. Withdraw solution
#             c. Purge
#             d. Deposit into well
#             e. Purge
#             f. Blow out
#             g. Flush pipette tip
#     2. Mix solutions in well
#     3. Flush pipette tip
#     4. Deposit film onto substrate
#     5. Withdraw all well volume into waste
#     6. Rinse the well 3x
#     7. Characterize the film on the substrate
#     8. Rinse the well 3x

#     Args:
#         instructions (Experiment object): The experiment instructions
#         results (ExperimentResult object): The experiment results
#         mill (object): The mill object
#         pump (object): The pump object
#         scale (object): The scale object
#         stock_vials (list): The list of stock vials
#         waste_vials (list): The list of waste vials
#         wellplate (Wells object): The wellplate object

#     Returns:
#         instructions (Experiment object): The updated experiment instructions
#         results (ExperimentResult object): The updated experiment results
#         stock_vials (list): The updated list of stock vials
#         waste_vials (list): The updated list of waste vials
#         wellplate (Wells object): The updated wellplate object

#     """
#     apply_log_filter(instructions.id, instructions.target_well, str(instructions.project_id) +"."+str(instructions.project_campaign_id))

#     try:
#         logger.info("Beginning experiment %d", instructions.id)
#         results.id = instructions.id
#         # Fetch list of solution names from stock_vials
#         # list of vial names to exclude
#         exclude_list = ["rinse0", "rinse1", "rinse2"]
#         experiment_solutions = [
#             vial.name for vial in stock_vials if vial.name not in exclude_list
#         ]
#         # experiment_solutions = ["acrylate", "peg", "dmf", "ferrocene", "custom"]

#         # Deposit all experiment solutions into well
#         for solution_name in experiment_solutions:
#             if (
#                 getattr(instructions, solution_name) > 0
#                 and solution_name[0:4] != "rinse"
#             ):  # if there is a solution to deposit
#                 logger.info(
#                     "Pipetting %s ul of %s into %s...",
#                     getattr(instructions, solution_name),
#                     solution_name,
#                     instructions.target_well,
#                 )
#                 stock_vials, waste_vials, wellplate = pipette(
#                     # volume in ul
#                     volume=getattr(instructions, solution_name),
#                     solutions=stock_vials,  # list of vial objects passed to ePANDA
#                     solution_name=solution_name,  # from the list above
#                     target_well=instructions.target_well,
#                     pumping_rate=instructions.pumping_rate,
#                     waste_vials=waste_vials,  # list of vial objects passed to ePANDA
#                     # this is hardcoded as waste...no reason to not be so far
#                     waste_solution_name="waste",
#                     wellplate=wellplate,
#                     pump=pump,
#                     mill=mill,
#                 )

#                 flush_pipette_tip(
#                     pump,
#                     waste_vials,
#                     stock_vials,
#                     instructions.flush_sol_name,
#                     mill,
#                     instructions.pumping_rate,
#                     instructions.flush_vol,
#                 )
#         logger.info("Pipetted solutions into well: %s", instructions.target_well)

#         # Mix solutions in well
#         if instructions.mix == 1:
#             logger.info("Mixing well: %s", instructions.target_well)
#             instructions.status = ExperimentStatus.MIXING
#             pump.mix(
#                 mix_location=wellplate.get_coordinates(
#                     instructions.target_well
#                 ),  # fetch x, y, z, depth, and echem height coordinates of well
#                 mix_repetitions=3,
#                 mix_volume=instructions.mix_vol,
#                 mix_rate=instructions.mix_rate,
#             )
#             logger.info("Mixed well: %s", instructions.target_well)

#         flush_pipette_tip(
#             pump,
#             waste_vials,
#             stock_vials,
#             instructions.flush_sol_name,
#             mill,
#             instructions.pumping_rate,
#             instructions.flush_vol,
#         )

#         if instructions.ca == 1:
#             instructions.status = ExperimentStatus.DEPOSITING
#             instructions, results = deposition(instructions, results, mill, wellplate)

#             logger.info("Deposition completed for well: %s", instructions.target_well)

#             # Withdraw all well volume into waste
#             waste_vials, wellplate = clear_well(
#                 volume=wellplate.read_volume(instructions.target_well),
#                 target_well=instructions.target_well,
#                 wellplate=wellplate,
#                 pumping_rate=instructions.pumping_rate,
#                 pump=pump,
#                 waste_vials=waste_vials,
#                 mill=mill,
#                 solution_name="waste",
#             )

#             logger.info("Cleared dep_sol from well: %s", instructions.target_well)

#             # Rinse the well 3x
#             stock_vials, waste_vials, wellplate = rinse(
#                 wellplate=wellplate,
#                 instructions=instructions,
#                 pump=pump,
#                 mill=mill,
#                 waste_vials=waste_vials,
#                 stock_vials=stock_vials,
#             )

#             logger.info("Rinsed well: %s", instructions.target_well)

#         # Echem CV - characterization
#         if instructions.cv == 1:
#             logger.info(
#                 "Beginning eChem characterization of well: %s", instructions.target_well
#             )
#             # Deposit characterization solution into well

#             logger.info(
#                 "Infuse %s into well %s...",
#                 instructions.char_sol_name,
#                 instructions.target_well,
#             )
#             stock_vials, waste_vials, wellplate = pipette(
#                 volume=instructions.char_vol,
#                 solutions=stock_vials,
#                 solution_name=instructions.char_sol_name,
#                 target_well=instructions.target_well,
#                 pumping_rate=instructions.pumping_rate,
#                 waste_vials=waste_vials,
#                 waste_solution_name="waste",
#                 wellplate=wellplate,
#                 pump=pump,
#                 mill=mill,
#             )

#             logger.info("Deposited char_sol in well: %s", instructions.target_well)

#             instructions, results = characterization(
#                 instructions, results, mill, wellplate
#             )

#             logger.info("Characterization of %s complete", instructions.target_well)

#             waste_vials, wellplate = clear_well(
#                 instructions.char_vol,
#                 instructions.target_well,
#                 wellplate,
#                 instructions.pumping_rate,
#                 pump,
#                 waste_vials,
#                 mill,
#                 "waste",
#             )

#             logger.info("Well %s cleared", instructions.target_well)

#             # Flushing procedure
#             flush_pipette_tip(
#                 pump,
#                 waste_vials,
#                 stock_vials,
#                 instructions.flush_sol_name,
#                 mill,
#                 instructions.pumping_rate,
#                 instructions.flush_vol,
#             )

#             logger.info("Pipette Flushed")

#         instructions.status = ExperimentStatus.FINAL_RINSE
#         stock_vials, waste_vials, wellplate = rinse(
#             wellplate=wellplate,
#             instructions=instructions,
#             pump=pump,
#             mill=mill,
#             waste_vials=waste_vials,
#             stock_vials=stock_vials,
#         )
#         logger.info("Final Rinse")

#         instructions.status = ExperimentStatus.COMPLETE
#         logger.info("End of Experiment: %s", instructions.id)

#         mill.move_to_safe_position()
#         logger.info("EXPERIMENT %s COMPLETED", instructions.id)

#     except OCPFailure as ocp_failure:
#         logger.error(ocp_failure)
#         instructions.status = ExperimentStatus.ERROR
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         logger.info("Failed instructions updated for experiment %s", instructions.id)
#         return instructions, results, stock_vials, waste_vials, wellplate

#     except KeyboardInterrupt:
#         logger.warning("Keyboard Interrupt")
#         instructions.status = ExperimentStatus.ERROR
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         logger.info("Saved interrupted instructions for experiment %s", instructions.id)
#         return instructions, results, stock_vials, waste_vials, wellplate

#     except Exception as general_exception:
#         exception_type, _, exception_traceback = sys.exc_info()
#         filename = exception_traceback.tb_frame.f_code.co_filename
#         line_number = exception_traceback.tb_lineno
#         logger.error("Exception: %s", general_exception)
#         logger.error("Exception type: %s", exception_type)
#         logger.error("File name: %s", filename)
#         logger.error("Line number: %d", line_number)
#         instructions.status = ExperimentStatus.ERROR
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         return instructions, results, stock_vials, waste_vials, wellplate

#     finally:
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         logger.info(
#             "Returning completed instructions for experiment %s", instructions.id
#         )

#     return instructions, results, stock_vials, waste_vials, wellplate

def pipette_accuracy_protocol_v2(
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    stock_vials: Sequence[StockVial],
    wellplate: Wells2,
):
    """
    Run the standard experiment:
    1. Deposit solutions into well
        for each solution:
            a. Withdraw air gap
            b. Withdraw solution
            c. Purge
            d. Deposit into well
            e. Purge
            f. Blow out
            
    Args:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        mill (object): The mill object
        pump (object): The pump object
        scale (object): The scale object
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
        wellplate (Wells object): The wellplate object

    Returns:
        instructions (Experiment object): The updated experiment instructions
        results (ExperimentResult object): The updated experiment results
        stock_vials (list): The updated list of stock vials
        waste_vials (list): The updated list of waste vials
        wellplate (Wells object): The updated wellplate object

    """
    apply_log_filter(instructions.id, instructions.target_well, str(instructions.project_id) +"."+str(instructions.project_campaign_id))

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        exclude_list = ["rinse0", "rinse1", "rinse2"]
        available_solutions = [
            vial.name for vial in stock_vials if vial.name not in exclude_list
        ]

        # although we already checked before running the experiment we want to check again that all requested solutions are found
        experiment_solution_count = len(instructions.solutions)
        matched = 0

        ## Deposit all experiment solutions into well
        for solution_name in instructions.solutions:
            solution_name = str(solution_name).lower()
            solution_volume = instructions.solutions[solution_name]
            if (
                solution_volume > 0
                and solution_name in available_solutions
            ):  # if there is a solution to deposit
                matched += 1
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    solution_volume,
                    solution_name,
                    instructions.target_well,
                )

                stock_vial = solution_selector(stock_vials, solution_name, solution_volume)
                forward_pipette_v2(
                    volume = solution_volume,
                    from_vessel= stock_vial,
                    to_vessel= wellplate.wells[instructions.target_well],
                    pump=pump,
                    mill=mill,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info("Pipetted %s into well: %s", json.dumps(instructions.solutions), instructions.target_well)

        instructions.status = ExperimentStatus.COMPLETE
        logger.info("End of Experiment: %s", instructions.id)

        mill.move_to_safe_position()
        logger.info("EXPERIMENT %s COMPLETED", instructions.id)

    except OCPFailure as ocp_failure:
        logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Failed instructions updated for experiment %s", instructions.id)


    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Saved interrupted instructions for experiment %s", instructions.id)


    except Exception as general_exception:
        exception_type, _, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        logger.error("Exception: %s", general_exception)
        logger.error("Exception type: %s", exception_type)
        logger.error("File name: %s", filename)
        logger.error("Line number: %d", line_number)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))

    finally:
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info(
            "Returning completed instructions for experiment %s", instructions.id
        )

def forward_vs_reverse_pipetting(
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    wellplate: Wells2,
):
    """
    Protocol for testing whether forward or reverse pipetting is more accurate
    If the expeirment ID is even choose forward pipetting otherwise choose reverse pipetting
    1. Deposit solutions into well
        for each solution:
            a. Withdraw air gap
            b. Withdraw solution
            c. Purge
            d. Deposit into well
            e. Purge
            f. Blow out
            
    Args:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        mill (object): The mill object
        pump (object): The pump object
        scale (object): The scale object
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
        wellplate (Wells object): The wellplate object

    Returns:
        instructions (Experiment object): The updated experiment instructions
        results (ExperimentResult object): The updated experiment results
        stock_vials (list): The updated list of stock vials
        waste_vials (list): The updated list of waste vials
        wellplate (Wells object): The updated wellplate object

    """
    apply_log_filter(instructions.id, instructions.target_well, str(instructions.project_id) +"."+str(instructions.project_campaign_id))

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        exclude_list = ["rinse0", "rinse1", "rinse2"]
        available_solutions = [
            vial.name for vial in stock_vials if vial.name not in exclude_list
        ]

        # although we already checked before running the experiment we want to check again that all requested solutions are found
        experiment_solution_count = len(instructions.solutions)
        matched = 0

        ## Deposit all experiment solutions into well
        for solution_name in instructions.solutions:
            solution_name = str(solution_name).lower()
            solution_volume = instructions.solutions[solution_name]
            if (
                solution_volume > 0
                and solution_name in available_solutions
            ):  # if there is a solution to deposit
                matched += 1
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    solution_volume,
                    solution_name,
                    instructions.target_well,
                )

                stock_vial = solution_selector(stock_vials, solution_name, solution_volume)

                if instructions.id % 2 == 0:
                    logger.info("Forward pipetting")
                    forward_pipette_v2(
                        volume = solution_volume,
                        from_vessel= stock_vial,
                        to_vessel= wellplate.wells[instructions.target_well],
                        pump=pump,
                        mill=mill,
                    )
                else:
                    logger.info("Reverse pipetting")
                    purge_vial = waste_selector(waste_vials, "waste", solution_volume)
                    reverse_pipette_v2(
                    volume = solution_volume,
                    from_vessel= stock_vial,
                    to_vessel= wellplate.wells[instructions.target_well],
                    purge_vessel=purge_vial,
                    pump=pump,
                    mill=mill,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info("Pipetted %s into well: %s", json.dumps(instructions.solutions), instructions.target_well)

        instructions.status = ExperimentStatus.COMPLETE
        logger.info("End of Experiment: %s", instructions.id)

        mill.move_to_safe_position()
        logger.info("EXPERIMENT %s COMPLETED", instructions.id)

    except OCPFailure as ocp_failure:
        logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Failed instructions updated for experiment %s", instructions.id)


    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Saved interrupted instructions for experiment %s", instructions.id)


    except Exception as general_exception:
        exception_type, _, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        logger.error("Exception: %s", general_exception)
        logger.error("Exception type: %s", exception_type)
        logger.error("File name: %s", filename)
        logger.error("Line number: %d", line_number)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))


    finally:
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info(
            "Returning completed instructions for experiment %s", instructions.id
        )

def vial_depth_tracking_protocol(
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Union[Mill, MockMill],
    pump: Union[Pump, MockPump],
    stock_vials: Sequence[StockVial],
    wellplate: Wells2,
):
    """
    Protocol for testing whether the vial depth calculations are accurate for the stock vials
    1. Deposit solutions into well
        for each solution:
            a. Withdraw air gap
            b. Withdraw solution
            c. Purge
            d. Deposit into well
            e. Purge
            f. Blow out
            
    Args:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        mill (object): The mill object
        pump (object): The pump object
        scale (object): The scale object
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
        wellplate (Wells object): The wellplate object

    Returns:
        instructions (Experiment object): The updated experiment instructions
        results (ExperimentResult object): The updated experiment results
        stock_vials (list): The updated list of stock vials
        waste_vials (list): The updated list of waste vials
        wellplate (Wells object): The updated wellplate object

    """
    apply_log_filter(instructions.id, instructions.target_well, str(instructions.project_id) +"."+str(instructions.project_campaign_id))

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        exclude_list = ["rinse0", "rinse1", "rinse2"]
        available_solutions = [
            vial.name for vial in stock_vials if vial.name not in exclude_list
        ]

        # although we already checked before running the experiment we want to check again that all requested solutions are found
        experiment_solution_count = len(instructions.solutions)
        matched = 0

        ## Deposit all experiment solutions into well
        for solution_name in instructions.solutions:
            solution_name = str(solution_name).lower()
            solution_volume = instructions.solutions[solution_name]
            if (
                solution_volume > 0
                and solution_name in available_solutions
            ):  # if there is a solution to deposit
                matched += 1
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    solution_volume,
                    solution_name,
                    instructions.target_well,
                )

                stock_vial = solution_selector(stock_vials, solution_name, solution_volume)
                forward_pipette_v2(
                    volume = solution_volume,
                    from_vessel= stock_vial,
                    to_vessel= wellplate.wells[instructions.target_well],
                    pump=pump,
                    mill=mill,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info("Pipetted %s into well: %s", json.dumps(instructions.solutions), instructions.target_well)

        instructions.status = ExperimentStatus.COMPLETE
        logger.info("End of Experiment: %s", instructions.id)

        mill.move_to_safe_position()
        logger.info("EXPERIMENT %s COMPLETED", instructions.id)

    except OCPFailure as ocp_failure:
        logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Failed instructions updated for experiment %s", instructions.id)


    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Saved interrupted instructions for experiment %s", instructions.id)


    except Exception as general_exception:
        exception_type, _, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        logger.error("Exception: %s", general_exception)
        logger.error("Exception type: %s", exception_type)
        logger.error("File name: %s", filename)
        logger.error("Line number: %d", line_number)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))


    finally:
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info(
            "Returning completed instructions for experiment %s", instructions.id
        )

# def mixing_test_protocol(
#     instructions: ExperimentBase,
#     results: ExperimentResult,
#     mill: Mill,
#     pump: Pump,
#     stock_vials: Sequence[Vial],
#     waste_vials: Sequence[Vial],
#     wellplate: Wells,
# ) -> Tuple[ExperimentBase, ExperimentResult, Sequence[Vial], Sequence[Vial], Wells]:
#     """
#     Run the standard experiment:
#     1. Deposit solutions into well
#         for each solution:
#             a. Withdraw air gap
#             b. Withdraw solution
#             c. Purge
#             d. Deposit into well
#             e. Purge
#             f. Blow out
#             g. Flush pipette tip
#     2. Mix solutions in well
#     3. Flush pipette tip
#     7. Characterize the film on the substrate
#     8. Return results, stock_vials, waste_vials, wellplate

#     Args:
#         instructions (Experiment object): The experiment instructions
#         results (ExperimentResult object): The experiment results
#         mill (object): The mill object
#         pump (object): The pump object
#         scale (object): The scale object
#         stock_vials (list): The list of stock vials
#         waste_vials (list): The list of waste vials
#         wellplate (Wells object): The wellplate object

#     Returns:
#         instructions (Experiment object): The experiment instructions
#         results (ExperimentResult object): The experiment results
#         stock_vials (list): The list of stock vials
#         waste_vials (list): The list of waste vials
#         wellplate (Wells object): The wellplate object
#     """
#     # Add custom value to log format
#     custom_filter = CustomLoggingFilter(instructions.project_campaign_id, instructions.id, instructions.target_well)
#     logger.addFilter(custom_filter)

#     try:
#         logger.info("Beginning experiment %d", instructions.id)
#         results.id = instructions.id
#         experiment_solutions = ["peg", "acrylate", "dmf", "custom", "ferrocene"]
#         apply_log_filter(instructions.id, instructions.target_well, str(instructions.project_id) +"."+str(instructions.project_campaign_id))
#         # Deposit all experiment solutions into well
#         for solution_name in experiment_solutions:
#             if (
#                 getattr(instructions, solution_name) > 0
#                 and solution_name[0:4] != "rinse"
#             ):  # if there is a solution to deposit
#                 logger.info(
#                     "Pipetting %s ul of %s into %s...",
#                     getattr(instructions, solution_name),
#                     solution_name,
#                     instructions.target_well,
#                 )
#                 experiment_solutions, waste_vials, wellplate = pipette(
#                     volume=getattr(instructions, solution_name),
#                     solutions=stock_vials,  # list of vial objects passed to ePANDA
#                     solution_name=solution_name,  # from the list above
#                     target_well=instructions.target_well,
#                     pumping_rate=instructions.pumping_rate,
#                     waste_vials=waste_vials,  # list of vial objects passed to ePANDA
#                     waste_solution_name="waste",
#                     wellplate=wellplate,
#                     pump=pump,
#                     mill=mill,
#                 )

#                 flush_pipette_tip(
#                     pump,
#                     waste_vials,
#                     stock_vials,
#                     instructions.flush_sol_name,
#                     mill,
#                     instructions.pumping_rate,
#                     instructions.flush_vol,
#                 )
#         logger.info("Pipetted solutions into well: %s", instructions.target_well)

#         # Mix solutions in well
#         if instructions.mix == 1:
#             logger.info("Mixing well: %s", instructions.target_well)
#             instructions.status = ExperimentStatus.MIXING
#             pump.mix(
#                 mix_location=wellplate.get_coordinates(instructions.target_well),
#                 mix_repetitions=instructions.mix_count,
#                 mix_volume=instructions.mix_vol,
#                 mix_rate=instructions.mix_rate,
#             )
#             logger.info("Mixed well: %s", instructions.target_well)

#             flush_pipette_tip(
#                 pump,
#                 waste_vials,
#                 stock_vials,
#                 instructions.flush_sol_name,
#                 mill,
#                 instructions.pumping_rate,
#                 instructions.flush_vol,
#             )

#         # Echem CV - characterization
#         if instructions.cv == 1:
#             logger.info(
#                 "Beginning eChem characterization of well: %s", instructions.target_well
#             )
#             # Deposit characterization solution into well

#             instructions, results = characterization(
#                 instructions, results, mill, wellplate
#             )

#             logger.info("Characterization of %s complete", instructions.target_well)
#             # Flushing procedure

#         instructions.status = ExperimentStatus.COMPLETE
#         logger.info("End of Experiment: %s", instructions.id)

#         mill.move_to_safe_position()
#         logger.info("EXPERIMENT %s COMPLETED", instructions.id)

#     except OCPFailure as ocp_failure:
#         logger.error(ocp_failure)
#         instructions.status = ExperimentStatus.ERROR
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         logger.info("Failed instructions updated for experiment %s", instructions.id)
#         return instructions, results, stock_vials, waste_vials, wellplate

#     except KeyboardInterrupt:
#         logger.warning("Keyboard Interrupt")
#         instructions.status = ExperimentStatus.ERROR
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         logger.info("Saved interrupted instructions for experiment %s", instructions.id)
#         return instructions, results, stock_vials, waste_vials, wellplate

#     except Exception as general_exception:
#         exception_type, _, exception_traceback = sys.exc_info()
#         filename = exception_traceback.tb_frame.f_code.co_filename
#         line_number = exception_traceback.tb_lineno
#         logger.error("Exception: %s", general_exception)
#         logger.error("Exception type: %s", exception_type)
#         logger.error("File name: %s", filename)
#         logger.error("Line number: %d", line_number)
#         instructions.status = ExperimentStatus.ERROR
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         return instructions, results, stock_vials, waste_vials, wellplate

#     finally:
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         logger.info(
#             "Returning completed instructions for experiment %s", instructions.id
#         )

#     return instructions, results, stock_vials, waste_vials, wellplate

# def peg2p_protocol(
#     instructions: PEG2P_Test_Instructions,
#     results: ExperimentResult,
#     mill: Mill,
#     pump: Pump,
#     stock_vials: Sequence[Vial],
#     waste_vials: Sequence[Vial],
#     wellplate: Wells,
# ) -> Tuple[PEG2P_Test_Instructions, ExperimentResult, Sequence[Vial], Sequence[Vial], Wells]:
#     """
#     Run the standard experiment:
#     1. Deposit solutions into well
#         for each solution:
#             a. Withdraw air gap
#             b. Withdraw solution
#             c. Purge
#             d. Deposit into well
#             e. Purge
#             f. Blow out
#             g. Flush pipette tip
#     2. Flush pipette tip
#     3. Electrodeposit film with CA
#     4. Rinse the well
#     5. Deposit characterization solution into well
#     6. Characterize the film on the substrate
#     7. Return results, stock_vials, waste_vials, wellplate
#     8. Update the system state
#     9. Update location of experiment instructions and save results

#     Args:
#         instructions (Experiment object): The experiment instructions
#         results (ExperimentResult object): The experiment results
#         mill (object): The mill object
#         pump (object): The pump object
#         scale (object): The scale object
#         stock_vials (list): The list of stock vials
#         waste_vials (list): The list of waste vials
#         wellplate (Wells object): The wellplate object

#     Returns:
#         instructions (Experiment object): The experiment instructions
#         results (ExperimentResult object): The experiment results
#         stock_vials (list): The list of stock vials
#         waste_vials (list): The list of waste vials
#         wellplate (Wells object): The wellplate object
#     """
#     # Add custom value to log format
#     custom_filter = CustomLoggingFilter(instructions.project_campaign_id, instructions.id, instructions.target_well)
#     logger.addFilter(custom_filter)

#     try:
#         logger.info("Beginning experiment %d", instructions.id)
#         results.id = instructions.id
#         experiment_solutions = ["dmf", "peg"]
#         apply_log_filter(instructions.id, instructions.target_well, str(instructions.project_id) +"."+str(instructions.project_campaign_id))

#         # Deposit all experiment solutions into well
#         for solution_name in experiment_solutions:
#             if (
#                 getattr(instructions, solution_name) > 0
#                 and solution_name[0:4] != "rinse"
#             ):  # if there is a solution to deposit
#                 logger.info(
#                     "Pipetting %s ul of %s into %s...",
#                     getattr(instructions, solution_name),
#                     solution_name,
#                     instructions.target_well,
#                 )
#                 experiment_solutions, waste_vials, wellplate = pipette(
#                     volume=getattr(instructions, solution_name),
#                     solutions=stock_vials,  # list of vial objects passed to ePANDA
#                     solution_name=solution_name,  # from the list above
#                     target_well=instructions.target_well,
#                     pumping_rate=instructions.pumping_rate,
#                     waste_vials=waste_vials,  # list of vial objects passed to ePANDA
#                     waste_solution_name="waste",
#                     wellplate=wellplate,
#                     pump=pump,
#                     mill=mill,
#                 )

#                 flush_pipette_tip(
#                     pump,
#                     waste_vials,
#                     stock_vials,
#                     instructions.flush_sol_name,
#                     mill,
#                     instructions.pumping_rate,
#                     instructions.flush_vol,
#                 )
#         logger.info("Pipetted solutions into well: %s", instructions.target_well)

#         # Echem CA - deposition
#         if instructions.ca == 1:
#             instructions.status = ExperimentStatus.DEPOSITING
#             instructions, results = deposition(instructions, results, mill, wellplate)
#             logger.info("deposition completed for well: %s", instructions.target_well)

#             waste_vials, wellplate = clear_well(
#                 volume=wellplate.read_volume(instructions.target_well),
#                 target_well=instructions.target_well,
#                 wellplate=wellplate,
#                 pumping_rate=instructions.pumping_rate,
#                 pump=pump,
#                 waste_vials=waste_vials,
#                 mill=mill,
#                 solution_name="waste",
#             )

#             logger.info("Cleared dep_sol from well: %s", instructions.target_well)

#             # Rinse the well 3x
#             stock_vials, waste_vials, wellplate = rinse(
#                 wellplate=wellplate,
#                 instructions=instructions,
#                 pump=pump,
#                 mill=mill,
#                 waste_vials=waste_vials,
#                 stock_vials=stock_vials,
#             )

#             logger.info("Rinsed well: %s", instructions.target_well)
#         # Echem CV - characterization
#         if instructions.cv == 1:
#             logger.info(
#                 "Beginning eChem characterization of well: %s", instructions.target_well
#             )
#             # Deposit characterization solution into well

#             logger.info(
#                 "Infuse %s into well %s...",
#                 instructions.char_sol_name,
#                 instructions.target_well,
#             )
#             stock_vials, waste_vials, wellplate = pipette(
#                 volume=instructions.char_vol,
#                 solutions=stock_vials,
#                 solution_name=instructions.char_sol_name,
#                 target_well=instructions.target_well,
#                 pumping_rate=instructions.pumping_rate,
#                 waste_vials=waste_vials,
#                 waste_solution_name="waste",
#                 wellplate=wellplate,
#                 pump=pump,
#                 mill=mill,
#             )

#             logger.info("Deposited char_sol in well: %s", instructions.target_well)

#             instructions, results = characterization(
#                 instructions, results, mill, wellplate
#             )

#             logger.info("Characterization of %s complete", instructions.target_well)

#             waste_vials, wellplate = clear_well(
#                 instructions.char_vol,
#                 instructions.target_well,
#                 wellplate,
#                 instructions.pumping_rate,
#                 pump,
#                 waste_vials,
#                 mill,
#                 "waste",
#             )

#             logger.info("Well %s cleared", instructions.target_well)

#             # Flushing procedure
#             flush_pipette_tip(
#                 pump,
#                 waste_vials,
#                 stock_vials,
#                 instructions.flush_sol_name,
#                 mill,
#                 instructions.pumping_rate,
#                 instructions.flush_vol,
#             )

#             logger.info("Pipette Flushed")
#             instructions.status = ExperimentStatus.COMPLETE
#         logger.info("End of Experiment: %s", instructions.id)

#         mill.move_to_safe_position()
#         logger.info("EXPERIMENT %s COMPLETED", instructions.id)

#     except OCPFailure as ocp_failure:
#         logger.error(ocp_failure)
#         instructions.status = ExperimentStatus.ERROR
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         logger.info("Failed instructions updated for experiment %s", instructions.id)
#         return instructions, results, stock_vials, waste_vials, wellplate

#     except KeyboardInterrupt:
#         logger.warning("Keyboard Interrupt")
#         instructions.status = ExperimentStatus.ERROR
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         logger.info("Saved interrupted instructions for experiment %s", instructions.id)
#         return instructions, results, stock_vials, waste_vials, wellplate

#     except Exception as general_exception:
#         exception_type, _, exception_traceback = sys.exc_info()
#         filename = exception_traceback.tb_frame.f_code.co_filename
#         line_number = exception_traceback.tb_lineno
#         logger.error("Exception: %s", general_exception)
#         logger.error("Exception type: %s", exception_type)
#         logger.error("File name: %s", filename)
#         logger.error("Line number: %d", line_number)
#         instructions.status = ExperimentStatus.ERROR
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         return instructions, results, stock_vials, waste_vials, wellplate

#     finally:
#         instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
#         logger.info(
#             "Returning completed instructions for experiment %s", instructions.id
#         )

#     return instructions, results, stock_vials, waste_vials, wellplate

def layered_solution_protocol(
    instructions: Sequence[LayeredExperiments],
    mill: Mill,
    pump: Pump,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    wellplate: Wells2,
):
    """
    For a layered protocol we want to deposit each solution into every well that requires it in one "pass" followed by a flush of the pipette tip. 
    Then repeat until each solution has been desposited into each well that requires it.
    We then will work well by well to mix and characterize the solutions in each well.
    """
    instructions = [instruction for instruction in instructions if isinstance(instruction, LayeredExperiments)]
    # Generate a list of all solutions that will be used in the experiment
    experiment_solutions = []
    for instruction in instructions:
        for solution in instruction.solutions:
            if solution not in experiment_solutions:
                experiment_solutions.append(solution)

    # Deposit all experiment solutions into well
    for solution_name in experiment_solutions:
        if (
            getattr(instructions, solution_name) > 0
            and solution_name[0:4] != "rinse"
        ):  # if there is a solution to deposit

            # for every well that requires this solution
            for instruction in instructions:
                if solution_name in instruction.solutions:
                    logger.info(
                        "Pipetting %s ul of %s into %s...",
                        getattr(instructions, solution_name),
                        solution_name,
                        instruction.target_well,
                    )
                    # Select the correct vial for the solution and designate a waste vial
                    stock_vial = next(
                        vial for vial in stock_vials if vial.name == solution_name & vial.volume - getattr(instructions, solution_name) > 3000
                    )

                    forward_pipette_v2(
                        volume = getattr(instructions, solution_name),
                        to_vessel= wellplate.wells[instruction.target_well],
                        from_vessel= stock_vial,
                        pumping_rate=None,
                        pump=pump,
                        mill=mill,
                    )

            flush_v2(
                pump=pump,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
                mill=mill,
                pumping_rate=instructions[0].pumping_rate,
                flush_volume=instructions[0].flush_vol,
                flush_solution_name=instructions[0].flush_sol_name,
            )

    # Mix and characterize each well
    for instruction in instructions:
        # Mix solutions in well
        if instruction.mix == 1:
            logger.info("Mixing well: %s", instruction.target_well)
            instruction.status = ExperimentStatus.MIXING
            pump.mix(
                mix_location=wellplate.get_coordinates(instruction.target_well),
                mix_repetitions=instruction.mix_count,
                mix_volume=instruction.mix_volume,
                mix_rate=instruction.pumping_rate,
            )
            logger.info("Mixed well: %s", instruction.target_well)

            flush_v2(
                pump=pump,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
                flush_solution_name=instructions[0].flush_sol_name,
                mill=mill,
                pumping_rate=instructions[0].pumping_rate,
                flush_volume=instructions[0].flush_vol,
            )
        # Echem CA - deposition
        if instruction.ca == 1:
            instruction.status = ExperimentStatus.DEPOSITING
            instruction, results = deposition(instruction, results, mill, wellplate)
            instruction.results = results
            logger.info("deposition completed for well: %s", instruction.target_well)

            waste_vial = next(
                vial for vial in waste_vials if vial.name == "waste"
            )
            forward_pipette_v2(
                volume=wellplate.get_volume(instruction.target_well),
                to_vessel= waste_vial,
                from_vessel= wellplate.wells[instruction.target_well],
                pumping_rate=None,
                pump=pump,
                mill=mill,
            )

            logger.info("Cleared dep_sol from well: %s", instruction.target_well)

            # Rinse the well 3x
            rinse_v2(
                wellplate=wellplate,
                instructions=instruction,
                pump=pump,
                mill=mill,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
            )

            logger.info("Rinsed well: %s", instruction.target_well)


        # Echem CV - characterization
        if instruction.cv == 1:
            logger.info(
                "Beginning eChem characterization of well: %s", instruction.target_well
            )
            # Deposit characterization solution into well
            instruction.status = ExperimentStatus.CHARACTERIZING
            logger.info(
                "Infuse %s into well %s...",
                instruction.char_sol_name,
                instruction.target_well,
            )
            char_vial = next(
                vial for vial in stock_vials if vial.name == instruction.char_sol_name & ((vial.volume - instruction.char_vol) > 3000)
            )

            forward_pipette_v2(
                volume=instruction.char_vol,
                to_vessel= wellplate.wells[instruction.target_well],
                from_vessel= char_vial,
                pumping_rate=None,
                pump=pump,
                mill=mill,
            )

            logger.info("Deposited char_sol in well: %s", instruction.target_well)

            instruction, results = characterization(
                instruction, results, mill, wellplate
            )
            instruction.results = results
            logger.info("Characterization of %s complete", instruction.target_well)

            waste_vial = next(
                vial for vial in waste_vials if vial.name == "waste"
            )

            forward_pipette_v2(
                volume=instruction.char_vol,
                to_vessel= waste_vial,
                from_vessel= wellplate.wells[instruction.target_well],
                pumping_rate=None,
                pump=pump,
                mill=mill,
            )

            logger.info("Well %s cleared", instruction.target_well)

            # Flushing procedure
            flush_v2(
                pump=pump,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
                flush_solution_name=instructions[0].flush_sol_name,
                mill=mill
            )

            logger.info("Pipette Flushed")
            instruction.status = ExperimentStatus.COMPLETE

    logger.info("End of Experiment: %s", instructions.id)

class OCPFailure(Exception):
    """Raised when OCP fails"""

    def __init__(self, stage):
        self.stage = stage
        self.message = f"OCP failed before {stage}"
        super().__init__(self.message)


class NoAvailableSolution(Exception):
    """Raised when no available solution is found"""

    def __init__(self, solution_name):
        self.solution_name = solution_name
        self.message = f"No available solution of {solution_name} found"
        super().__init__(self.message)
