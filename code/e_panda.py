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
from typing import Optional, Sequence, Tuple, Union

# Third party or custom imports
from pathlib import Path
import gamry_control_WIP as echem
from camera_call_camera import capture_new_image
from config.config import (AIR_GAP, DRIP_STOP, PATH_TO_LOGS, PURGE_VOLUME,
                           TESTING, PATH_TO_DATA)
import instrument_toolkit
#from gamry_control_WIP_mock import GamryPotentiostat as echem
#from gamry_control_WIP_mock import potentiostat_cv_parameters, potentiostat_ocp_parameters, potentiostat_ca_parameters
from experiment_class import (EchemExperimentBase, ExperimentResult,
                              ExperimentStatus)
from gamry_control_WIP import (potentiostat_ca_parameters,
                               potentiostat_cv_parameters,
                               potentiostat_ocp_parameters)
from log_tools import CustomLoggingFilter
from mill_control import Instruments, Mill, MockMill
from pump_control import MockPump, Pump
from vials import StockVial, Vessel, WasteVial
from wellplate import Well, Wells, Wells2

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger("e_panda")
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter(
    "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(message)s"
)
system_handler = logging.FileHandler(PATH_TO_LOGS / "ePANDA.log")
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
        logger.info(
            "Forward pipetting %f ul from %s to %s",
            volume,
            from_vessel.name,
            to_vessel.name,
        )
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

        repetitions = math.ceil(volume / (pump.pipette_capacity_ul - DRIP_STOP))
        repetition_vol = volume / repetitions

        for j in range(repetitions):
            logger.info("Repetition %d of %d", j + 1, repetitions)
            # First half: pick up solution
            logger.debug("Withdrawing %f of air gap...", AIR_GAP)

            # withdraw a little to engange screw receive nothing
            pump.withdraw(
                volume=AIR_GAP, solution=None, rate=pumping_rate
            )  # withdraw air gap to engage screw
            if isinstance(from_vessel, Well):
                logger.info("Moving to %s at %s...", from_vessel.name, from_vessel.coordinates)
            else:
                logger.info("Moving to %s at %s...", from_vessel.name, from_vessel.position)
            # if from vessel is a well, go to well depth
            if isinstance(from_vessel,Well):
                from_vessel: Well = from_vessel
                mill.safe_move(
                    from_vessel.coordinates["x"],
                    from_vessel.coordinates["y"],
                    from_vessel.depth,
                    Instruments.PIPETTE,
                )
            else:  # go to safe height above vial
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
                weigh=False,
            )  # pipette now has air gap + repitition vol

            mill.move_to_safe_position()

            # Withdraw an air gap to prevent dripping, receive nothing
            pump.withdraw(
                volume=DRIP_STOP, solution=None, rate=pumping_rate, weigh=False
            )
            logger.debug(
                "From Vessel %s volume: %f depth: %f",
                from_vessel.name,
                from_vessel.volume,
                from_vessel.depth,
            )
            # Second Half: Deposit to to_vessel
            logger.info("Moving to: %s...", to_vessel.name)
            # determine if the destination is a well or a waste vial
            if isinstance(to_vessel, Well):  # go to solution depth
                to_vessel: Well = to_vessel
                mill.safe_move(
                    to_vessel.coordinates["x"],
                    to_vessel.coordinates["y"],
                    to_vessel.height,  # FIXME: to_vessel.height,
                    Instruments.PIPETTE,
                )
            else:  # go to safe height above waste vial
                to_vessel: WasteVial = to_vessel
                mill.safe_move(
                    to_vessel.coordinates["x"],
                    to_vessel.coordinates["y"],
                    to_vessel.height,
                    Instruments.PIPETTE,
                )

            # Infuse into the to_vessel and receive the updated vessel object
            weigh = bool(isinstance(to_vessel, Well))

            pump.infuse(
                volume_to_infuse=repetition_vol,
                being_infused=from_vessel,
                infused_into=to_vessel,
                rate=pumping_rate,
                blowout_ul=AIR_GAP + DRIP_STOP,
                weigh=weigh,
            )

            # Update the contentes of the to_vessel
            # FEATURE change from repitition volume to corrected volume
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
        logger.info(
            "Reverse pipetting %f ul from %s to %s",
            volume,
            from_vessel.name,
            to_vessel.name,
        )
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
                volume=AIR_GAP, solution=None, rate=pumping_rate
            )  # withdraw air gap to engage screw

            logger.info("Moving to %s...", from_vessel.name)
            mill.safe_move(
                from_vessel.coordinates["x"],
                from_vessel.coordinates["y"],
                from_vessel.z_bottom,  # from_vessel.depth,
                Instruments.PIPETTE,
            )  # go to solution depth (depth replaced with height)

            # Withdraw the solution from the source and receive the updated vessel object
            pump.withdraw(
                volume=repetition_vol + purge_volume,
                solution=from_vessel,
                rate=pumping_rate,
                weigh=False,
            )  # pipette now has air gap + repitition vol + purge volume

            mill.move_to_safe_position()

            # Withdraw an air gap to prevent dripping, receive nothing
            pump.withdraw(
                volume=DRIP_STOP, solution=None, rate=pumping_rate, weigh=False
            )  # pipette now has air gap + repitition vol + purge volume + drip stop

            # Second Half: Deposit to to_vessel
            logger.info("Moving to: %s...", to_vessel.name)
            # determine if the destination is a well or a waste vial
            if isinstance(to_vessel, Well):  # go to solution depth
                logger.debug("%s is a Well", to_vessel.name)
                mill.safe_move(
                    to_vessel.coordinates["x"],
                    to_vessel.coordinates["y"],
                    0,
                    Instruments.PIPETTE,
                )
                logger.info("Moved to well %s", to_vessel.name)
            else:  # go to safe height above vial
                logger.debug("%s is a Vial", to_vessel.name)
                mill.safe_move(
                    to_vessel.coordinates["x"],
                    to_vessel.coordinates["y"],
                    from_vessel.z_bottom,  # to_vessel.depth + 5 ,
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
                blowout_ul=DRIP_STOP,
                weigh=True,
            )  # pipette now has purge volume
            logger.info(
                "Infused %s into %s. Moving to safe position",
                from_vessel.name,
                to_vessel.name,
            )
            mill.move_to_safe_position()
            logger.info("Moved to safe position")
            # Update the contentes of the to_vessel
            logger.debug("Updating contents of %s", to_vessel.name)
            to_vessel.update_contents(from_vessel, repetition_vol)

            logger.info(
                "Vessel %s volume: %f",
                to_vessel.name,
                to_vessel.volume,
            )
            logger.info("Withdrawing the drip stop...")
            pump.withdraw(
                volume=DRIP_STOP, solution=None, rate=pumping_rate, weigh=False
            )  # pipette now has purge volume + air gap + drip stop
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
                blowout_ul=DRIP_STOP + AIR_GAP,
                weigh=False,  # Vials are not on the scale
            )  # Pipette should be empty after this
            logger.info(
                "Purged the purge volume, updating contents of %s - %s",
                purge_vessel.position,
                purge_vessel.name,
            )
            purge_vessel.update_contents(from_vessel, purge_volume)

            mill.move_to_safe_position()


def rinse_v2(
    wellplate: Wells2,
    instructions: EchemExperimentBase,
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
        "Rinsing well %s %dx...", instructions.well_id, instructions.rinse_count
    )
    for rep in range(instructions.rinse_count):  # 0, 1, 2...
        rinse_solution_name = "rinse" + str(rep)
        # purge_vial = waste_selector(rinse_solution_name, rinse_vol)
        # rinse_solution = solution_selector(stock_vials, rinse_solution_name, rinse_vol)
        logger.info("Rinse %d of %d", rep + 1, instructions.rinse_count)

        # Withdraw the rinse volume from the rinse solution into the well
        rinse_solution = solution_selector(
            stock_vials, rinse_solution_name, instructions.rinse_vol
        )
        forward_pipette_v2(
            instructions.rinse_vol,
            from_vessel=rinse_solution,
            to_vessel=wellplate[instructions.well_id],
            pump=pump,
            mill=mill,
            pumping_rate=None,
        )
        # Remove the rinse volume from the well to a waste vial
        rinse_waste = waste_selector(
            waste_vials, rinse_solution_name, instructions.rinse_vol
        )
        forward_pipette_v2(
            instructions.rinse_vol,
            from_vessel=wellplate[instructions.well_id],
            to_vessel=rinse_waste,
            pump=pump,
            mill=mill,
            pumping_rate=None,
        )

        logger.info("Rinse %d of %d complete", rep + 1, instructions.rinse_count)
        logger.debug(
            "Remaining volume in well: %f",
            wellplate.get_volume(instructions.well_id),
        )
    return 0


def flush_v2(
    waste_vials: Sequence[WasteVial],
    stock_vials: Sequence[StockVial],
    flush_solution_name: str,
    mill: Union[Mill, MockMill],
    pump: Union[Pump, MockPump],
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

        logger.info(
            "Flushed pipette tip with %f ul of %s...", flush_volume, flush_solution_name
        )
    else:
        logger.info("No flushing required. Flush volume is 0. Continuing...")
    return 0


def solution_selector(
    solutions: Sequence[StockVial], solution_name: str, volume: float
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
    for solution in solutions:
        # if the solution names match and the requested volume is less than the available volume (volume - 15% of capacity)
        if (
            solution.name.lower() == solution_name.lower()
            and solution.volume - 0.20 * solution.capacity > (volume)
        ):
            logger.debug(
                "Selected stock vial: %s in position %s",
                solution.name,
                solution.position,
            )
            return solution
    raise NoAvailableSolution(solution_name)


def waste_selector(
    solutions: Sequence[WasteVial], solution_name: str, volume: float
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
    pstat = echem
    pstat.pstatconnect()
    # echem OCP
    logger.info("Beginning eChem OCP of well: %s", dep_instructions.well_id)
    dep_instructions.status = ExperimentStatus.OCPCHECK
    mill.safe_move(
        wellplate.get_coordinates(dep_instructions.well_id)["x"],
        wellplate.get_coordinates(dep_instructions.well_id)["y"],
        wellplate.echem_height,
        Instruments.ELECTRODE,
    )  # move to well depth
    base_filename = pstat.setfilename(dep_instructions.id, "OCP", dep_instructions.project_id, dep_instructions.project_campaign_id, dep_instructions.well_id)
    dep_results.ocp_dep_file = base_filename
    pstat.OCP(
        potentiostat_ocp_parameters.OCPvi,
        potentiostat_ocp_parameters.OCPti,
        potentiostat_ocp_parameters.OCPrate,
    )  # OCP
    pstat.activecheck()
    dep_results.ocp_dep_pass = pstat.check_vf_range(
        dep_results.ocp_dep_file.with_suffix(".txt")
    )

    # echem CA - deposition
    if dep_results.ocp_dep_pass:
        dep_instructions.status = ExperimentStatus.DEPOSITING
        logger.info(
            "Beginning eChem deposition of well: %s", dep_instructions.well_id
        )
        dep_results.deposition_data_file = pstat.setfilename(dep_instructions.id, "CA", dep_instructions.project_id, dep_instructions.project_campaign_id, dep_instructions.well_id)

        # FEATURE have chrono return the max and min values for the deposition
        # and save them to the results
        # don't have any parameters hardcoded, switch these all to instructions
        pstat.chrono(
            potentiostat_ca_parameters.CAvi,
            potentiostat_ca_parameters.CAti,
            CAv1=dep_instructions.CAv1,
            CAt1=dep_instructions.CAt1,
            CAv2=potentiostat_ca_parameters.CAv2,
            CAt2=potentiostat_ca_parameters.CAt2,
            CAsamplerate=dep_instructions.ca_sample_period,
        )  # CA

        pstat.activecheck()
        mill.move_to_safe_position()  # move to safe height above target well

        mill.rinse_electrode()
        pstat.pstatdisconnect()

    else:
        pstat.pstatdisconnect()
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
    logger.info("Characterizing well: %s", char_instructions.well_id)
    # echem OCP
    logger.info("Beginning eChem OCP of well: %s", char_instructions.well_id)
    pstat = echem
    pstat.pstatconnect()
    char_instructions.status = ExperimentStatus.OCPCHECK
    mill.safe_move(
        wellplate.get_coordinates(char_instructions.well_id)["x"],
        wellplate.get_coordinates(char_instructions.well_id)["y"],
        wellplate.echem_height,
        Instruments.ELECTRODE,
    )  # move to well depth
    char_results.ocp_char_file = pstat.setfilename(char_instructions.id, "OCP_char", char_instructions.project_id, char_instructions.project_campaign_id, char_instructions.well_id)
    pstat.OCP(
        OCPvi= potentiostat_ocp_parameters.OCPvi,
        OCPti=potentiostat_ocp_parameters.OCPti,
        OCPrate=potentiostat_ocp_parameters.OCPrate,
    )  # OCP
    pstat.activecheck()
    char_results.ocp_char_pass = pstat.check_vf_range(
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
            "Beginning eChem %s of well: %s", test_type, char_instructions.well_id
        )

        char_results.characterization_data_file = pstat.setfilename(
            char_instructions.id, test_type,
            char_instructions.project_id, char_instructions.project_campaign_id, char_instructions.well_id
        )

        # FEATURE have cyclic return the max and min values for the characterization
        # and save them to the results
        pstat.cyclic(
            potentiostat_cv_parameters.CVvi,
            potentiostat_cv_parameters.CVap1,
            potentiostat_cv_parameters.CVap2,
            potentiostat_cv_parameters.CVvf,
            CVsr1=char_instructions.cv_scan_rate,
            CVsr2=char_instructions.cv_scan_rate,
            CVsr3=char_instructions.cv_scan_rate,
            CVsamplerate=(
                potentiostat_cv_parameters.CVstep / char_instructions.cv_scan_rate
            ),
            CVcycle=potentiostat_cv_parameters.CVcycle,
        )
        pstat.activecheck()
        mill.move_to_safe_position()  # move to safe height above target well
        #mill.rinse_electrode()
        pstat.pstatdisconnect()
        return char_instructions, char_results

    pstat.pstatdisconnect()
    mill.move_to_safe_position()  # move to safe height above target well
    raise OCPFailure("CV")


def apply_log_filter(
    experiment_id: int = None,
    target_well: Optional[str] = None,
    campaign_id: Optional[str] = None,
    test: bool = TESTING,
):
    """Add custom value to log format"""
    experiment_formatter = logging.Formatter(
        "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(custom1)s&%(custom2)s&%(custom3)s&%(message)s&%(custom4)s"
    )
    system_handler.setFormatter(experiment_formatter)
    custom_filter = CustomLoggingFilter(campaign_id, experiment_id, target_well, test)
    logger.addFilter(custom_filter)

def volume_correction(volume, density = None, viscosity = None):
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
        density = 1.0
    if viscosity is None:
        viscosity = 1.0
    corrected_volume = volume * (1.0 + (1.0 - density) * (1.0 - viscosity))
    return corrected_volume

def image_well(
    wellplate: Wells2,
    instructions: EchemExperimentBase,
    toolkit: instrument_toolkit.Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Image the well with the camera

    Args:
        wellplate (Wells object): The wellplate object
        target_well (str): The alphanumeric name of the well you would like to image
        toolkit (Toolkit): The toolkit object
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials

    Returns:
        None (void function) since the objects are passed by reference
    """
    try:
        # position lens above the well
        logger.info("Moving camera above well %s", instructions.well_id)
        toolkit.mill.safe_move(
            wellplate.get_coordinates(instructions.well_id)["x"],
            wellplate.get_coordinates(instructions.well_id)["y"],
            wellplate.image_height,
            Instruments.LENS,
        )
        logger.info("Imaging well %s", instructions.well_id)
        # capture image
        logger.debug("Capturing image of well %s", instructions.well_id)
        FILE_NAME = "_".join([
            str(instructions.project_id),
            str(instructions.project_campaign_id),
            str(instructions.id),
            str(instructions.well_id),
            "image"
        ])
        file_path = Path(PATH_TO_DATA / str(FILE_NAME)).with_suffix(".png")

        for i, _ in enumerate(range(100)):
            if not file_path.exists():
                break
            file_name = f"{FILE_NAME}_{i}"
            file_path = Path(PATH_TO_DATA / str(file_name)).with_suffix(".png")

        capture_new_image(
            save=True,
            num_images=1,
            file_name=file_path
        )
        logger.debug("Image of well %s captured", instructions.well_id)
        # upload image to OBS
        #logger.info("Uploading image of well %s to OBS", instructions.well_id)

    except Exception as e:
        logger.exception("Failed to image well %s", instructions.well_id)
        raise e
    finally:
        # move camera to safe position
        if wellplate.image_height < 0:
            logger.info("Moving camera to safe position")
            toolkit.mill.move_to_safe_position()

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

if __name__ == "__main__":
    mill = Mill()
    mill.home()
    try:
        characterization(
            char_instructions=EchemExperimentBase(
                id=0,
                project_id=0,
                project_campaign_id=0,
                well_id="D2",
                status=ExperimentStatus.NEW,
                baseline=0,
                ca=0,
                cv_scan_rate=0.050,
                CVstep=0.02,
                CVap2=-0.2,
                CVap1=0.58,
                CVsr1=0.050,
                CVsr2=0.050,
            ),
            char_results=ExperimentResult(),
            mill=mill,
            wellplate=Wells2(),
        )
    except OCPFailure as e:
        print(e.message)

    from Analyzer import plotdata
    #OCP
    plotdata(
        "OCP",
        ExperimentResult().ocp_char_file.with_suffix(".txt"),
        True,
    )
