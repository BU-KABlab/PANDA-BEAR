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
import logging
import math
from datetime import datetime
import sys
from typing import Tuple
import pytz as tz

# Third party or custom imports
import gamry_control_WIP as echem
from experiment_class import (
    Experiment,
    ExperimentResult,
    ExperimentStatus,
)
from log_tools import CustomLoggingFilter
from mill_control import Mill, Instruments
from pump_control import Pump
from scale import Sartorius as Scale
from vials import Vial
from wellplate import Wells

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

AIR_GAP = 40  # ul


def pipette(
    volume: float,  # volume in ul
    solutions: list[Vial],
    solution_name: str,
    target_well: str,
    pumping_rate: float,
    waste_vials: list[Vial],
    waste_solution_name: str,
    wellplate: Wells,
    pump: Pump,
    mill: Mill,
    purge_volume: float = 20.00,
) -> Tuple[list[Vial], list[Vial], Wells]:
    """
    Perform the full pipetting sequence:
    1. Determine the number of repetitions
    2. Withdraw the solution from the source
        a. Withdraw an air gap to engage the screw
        b. Move to the source
        c. Withdraw the solution
        d. Move back to safe height
    3. Purge the solution into the waste vial
        a. Move to the waste vial
        b. Purge the solution
        c. Purge the air gap
        d. Move back to safe height
    4. Deposit the solution into the target well
        a. Move to the target well
        b. Deposit the solution
        c. Move back to safe height
    5. Purge the solution into the waste vial
        a. Move to the waste vial
        b. Purge the solution
        c. Purge the air gap
        d. Move back to safe height
    6. Repeat 2-5 until all repetitions are complete
    7. Purge the air gap
    8. Move back to safe height

    Args:
        volume (float): Volume to be pipetted into desired well
        solution (Vial object): the vial source or solution to be pipetted
        target_well (str): The alphanumeric name of the well you would like to pipette into
        purge_volume (float): Desired about to purge before and after pipetting

    Returns:
        solutions (list): The updated list of solution vials
        waste_vials (list): The updated list of waste vials
        wellplate (Wells object): The updated wellplate object
    """
    air_gap = purge_volume * 2  # ul
    if volume > 0.00:
        # Calculate the number of repetitions
        # based on pipette capacity and known purge volumes
        repetitions = math.ceil(
            volume / (pump.pipette_capacity_ul - 2 * purge_volume)
        )  # divide by pipette capacity
        repetition_vol = volume / repetitions

        for j in range(repetitions):
            logger.info("Repetition %d of %d", j + 1, repetitions)
            repetition_and_purge_vol = repetition_vol + (2 * purge_volume)
            # solution = solution_selector(solution_name, repetition_vol)
            solution = solution_selector(
                solutions, solution_name, repetition_and_purge_vol
            )
            # purge_vial = waste_selector(waste_solution_name, repetition_vol)
            purge_vial = waste_selector(
                waste_vials, waste_solution_name, repetition_and_purge_vol
            )
            # First half: pick up solution
            logger.debug("Withdrawing %f of air gap...", air_gap)
            pump.withdraw(
                volume=air_gap, rate=pumping_rate
            )  # withdraw air gap to engage screw

            logger.info("Moving to %s...", solution.name)
            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], 0
            )  # start at safe height
            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], solution.bottom
            )  # go to solution depth (depth replaced with height)

            solution = pump.withdraw(
                volume=repetition_and_purge_vol, solution=solution, rate=pumping_rate
            )  # pipette now has air gap + repitition + 2 purge vol

            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], 0
            )  # return to safe height

            # Intermediate: Purge
            logger.info("Moving to purge vial: %s...", purge_vial.name)
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"],
                purge_vial.coordinates["y"],
                purge_vial.height,
            )  # purge_vial.depth replaced with height

            purge_vial = pump.purge(
                purge_vial=purge_vial, purge_volume=purge_volume
            )  # remaining vol in pipette is now air gap + repition vol + 1 purge
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )

            # Second Half: Deposit to well
            logger.info("Moving to target well: %s...", target_well)
            mill.move_pipette_to_position(
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                0,
            )  # start at safe height
            mill.move_pipette_to_position(
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                wellplate.depth(target_well),
            )  # go to solution depth

            wellplate.update_volume(target_well, repetition_vol)
            logger.info(
                "Infusing %s into well %s...",
                solution.name,
                target_well,
            )
            solution = pump.infuse(
                volume=repetition_vol, solution=solution, rate=pumping_rate
            )  # remaining vol in pipette is now air gap + 1 purge vol
            logger.info(
                "Well %s volume: %f",
                target_well,
                wellplate.volume(target_well),
            )

            mill.move_pipette_to_position(
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                0,
            )  # return to safe height

            # End Purge
            logger.debug("Moving to purge vial: %s...", purge_vial.name)
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"],
                purge_vial.coordinates["y"],
                purge_vial.height,
            )  # purge_vial.depth replaced with height

            purge_vial = pump.purge(
                purge_vial=purge_vial, purge_volume=purge_volume
            )  # remaining vol in pipette is now air gap
            # Pump out the air gap
            pump.infuse(volume=air_gap, rate=0.5)  # purge the pipette tip
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )

            logger.debug(
                "Remaining volume in pipette: %f ",
                pump.pump.volume_withdrawn,
            )  # should always be zero, pause if not

    return solutions, waste_vials, wellplate


def clear_well(
    volume: float,
    target_well: str,
    wellplate: Wells,
    pumping_rate: float,
    pump: Pump,
    waste_vials: list[Vial],
    mill: Mill,
    solution_name="waste",
) -> Tuple[list[Vial], Wells]:
    """
    Clear the well of the specified volume with the specified solution.
    Involves withdrawing the solution from the well and purging it into the waste vial

    Args:
        volume (float): Volume to be cleared in microliters
        target_well (str): The alphanumeric name of the well you would like to clear
        wellplate (Wells object): The wellplate object
        pumping_rate (float): The pumping rate in ml/min
        pump (object): The pump object
        waste_vials (list): The list of waste vials
        mill (object): The mill object

    Returns:
        waste_vials (list): The updated list of waste vials
        wellplate (Wells object): The updated wellplate object
    """
    if volume > 0.00:
        repetition = math.ceil(
            volume / 200
        )  # divide by 200 ul which is the pipette capacity to determin the number of repetitions
        repetition_vol = volume / repetition
        logger.info(
            "Clearing well %s with %dx repetitions of %f",
            target_well,
            repetition,
            repetition_vol,
        )
        for j in range(repetition):
            purge_vial = waste_selector(waste_vials, solution_name, repetition_vol)

            logger.info("Repitition %d of %d", j + 1, repetition)
            logger.debug("Withdrawing %f of air gap...", AIR_GAP)
            # withdraw a little to engange screw
            pump.withdraw(volume=AIR_GAP, rate=pumping_rate)
            logger.debug("Moving to %s...", target_well)
            mill.safe_move(
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                wellplate.depth(target_well),
                Instruments.PIPETTE,
            )  # go to bottom of well

            wellplate.update_volume(target_well, -repetition_vol)
            logger.debug("Withdrawing %f from %s...", repetition_vol, target_well)
            pump.withdraw(
                volume=repetition_vol,
                solution=None,
                rate=pumping_rate,
            )  # withdraw the volume from the well

            logger.debug("Well %s volume: %f", target_well, wellplate.volume(target_well))
            mill.move_pipette_to_position(
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                0,
            )  # return to safe height

            logger.info("Moving to purge vial %s...", purge_vial.name)
            mill.safe_move(
                purge_vial.coordinates["x"],
                purge_vial.coordinates["y"],
                purge_vial.height,
                Instruments.PIPETTE,
            )

            purge_vial = pump.purge(
                purge_vial=purge_vial, purge_volume=repetition_vol
            )  # repitition volume
            logger.info("Purging the air gap...")
            pump.infuse(volume=AIR_GAP, rate=0.5)  # extra purge to clear pipette

            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )
            logger.info("Remaining volume in well: %f", wellplate.volume(target_well))
    else:
        logger.info("No clearing required. Clear volume is 0. Continuing...")
    return waste_vials, wellplate


def rinse(
    wellplate: Wells,
    instructions: Experiment,
    pump: Pump,
    mill: Mill,
    stock_vials: list[Vial],
    waste_vials: list[Vial],
) -> Tuple[list[Vial], list[Vial], Wells]:
    """
    Rinse the well with rinse_vol ul of ACN.
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
        stock_vials (list): The updated list of stock vials
        waste_vials (list): The updated list of waste vials
        wellplate (Wells object): The updated wellplate object
    """

    logger.info(
        "Rinsing well %s %dx...", instructions.target_well, instructions.rinse_count
    )
    for rep in range(instructions.rinse_count):  # 0, 1, 2...
        rinse_solution_name = "rinse" + str(rep)
        # purge_vial = waste_selector(rinse_solution_name, rinse_vol)
        # rinse_solution = solution_selector(stock_vials, rinse_solution_name, rinse_vol)
        logger.info("Rinse %d of %d", rep + 1, instructions.rinse_count)
        stock_vials, waste_vials, wellplate = pipette(
            instructions.rinse_vol,
            stock_vials,
            rinse_solution_name,
            instructions.target_well,
            instructions.pumping_rate,
            waste_vials,
            rinse_solution_name,
            wellplate,
            pump,
            mill,
        )
        waste_vials, wellplate = clear_well(
            instructions.rinse_vol,
            instructions.target_well,
            wellplate,
            instructions.pumping_rate,
            pump,
            waste_vials,
            mill,
            solution_name=rinse_solution_name,
        )
        logger.info("Rinse %d of %d complete", rep + 1, instructions.rinse_count)
        logger.debug(
            "Remaining volume in well: %f", wellplate.volume(instructions.target_well)
        )
    return stock_vials, waste_vials, wellplate


def flush_pipette_tip(
    pump: Pump,
    waste_vials: list[Vial],
    stock_vials: list[Vial],
    flush_solution_name: str,
    mill: Mill,
    pumping_rate=0.5,
    flush_volume=120,
) -> Tuple[list[Vial], list[Vial]]:
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
        purge_vial = waste_selector(waste_vials, "waste", flush_volume)

        logger.info("Moving to flush solution %s...", flush_solution.name)
        mill.move_pipette_to_position(
            flush_solution.coordinates["x"], flush_solution.coordinates["y"], 0
        )
        logger.debug("Withdrawing %f of air gap...", AIR_GAP)
        pump.withdraw(volume=AIR_GAP, rate=pumping_rate)

        mill.move_pipette_to_position(
            flush_solution.coordinates["x"],
            flush_solution.coordinates["y"],
            flush_solution.bottom,
        )  # depth replaced with height

        logger.debug("Withdrawing %s...", flush_solution.name)
        flush_solution = pump.withdraw(
            volume=flush_volume, solution=flush_solution, rate=pumping_rate
        )
        mill.move_pipette_to_position(
            flush_solution.coordinates["x"], flush_solution.coordinates["y"], 0
        )

        logger.debug("Moving to purge...")
        mill.move_pipette_to_position(
            purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
        )
        mill.move_pipette_to_position(
            purge_vial.coordinates["x"], purge_vial.coordinates["y"], purge_vial.height
        )  # purge_vial.depth replaced with height
        logger.debug("Purging...")
        purge_vial = pump.purge(purge_vial, flush_solution, flush_volume)
        logger.debug("Purging the air gap...")
        pump.infuse(volume=AIR_GAP, rate=0.5)  # purge the pipette tip
        mill.move_pipette_to_position(
            purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
        )  # move back to safe height (top)
    else:
        logger.info("No flushing required. Flush volume is 0. Continuing...")
    return stock_vials, waste_vials


def solution_selector(solutions: list[Vial], solution_name: str, volume: float) -> Vial:
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
        if solution.name.lower() == solution_name.lower() and solution.volume > (
            volume + 1000
        ):
            logger.debug(
                "Selected stock vial: %s in position %s",
                solution.name,
                solution.position,
            )
            return solution
    raise NoAvailableSolution(solution_name)


def waste_selector(solutions: list[Vial], solution_name: str, volume: float) -> Vial:
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
    dep_instructions: Experiment,
    dep_results: ExperimentResult,
    mill: Mill,
    wellplate: Wells,
) -> Tuple[Experiment, ExperimentResult]:
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
    logger.info("\n\nSetting up eChem experiments...")
    echem.pstatconnect()
    # echem OCP
    logger.info("Beginning eChem OCP of well: %s", dep_instructions.target_well)
    dep_instructions.status = ExperimentStatus.OCPCHECK
    mill.move_electrode_to_position(
        wellplate.get_coordinates(dep_instructions.target_well)["x"],
        wellplate.get_coordinates(dep_instructions.target_well)["y"],
        0,
    )  # move to safe height above target well
    mill.move_electrode_to_position(
        wellplate.get_coordinates(dep_instructions.target_well)["x"],
        wellplate.get_coordinates(dep_instructions.target_well)["y"],
        wellplate.echem_height,
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
        echem.disconnectpstat()

    else:
        echem.disconnectpstat()
        raise OCPFailure("CA")

    return dep_instructions, dep_results


def characterization(
    char_instructions: Experiment,
    char_results: ExperimentResult,
    mill: Mill,
    wellplate: Wells,
) -> Tuple[Experiment, ExperimentResult]:
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
    mill.move_electrode_to_position(
        wellplate.get_coordinates(char_instructions.target_well)["x"],
        wellplate.get_coordinates(char_instructions.target_well)["y"],
        0,
    )  # move to safe height above target well
    mill.move_electrode_to_position(
        wellplate.get_coordinates(char_instructions.target_well)["x"],
        wellplate.get_coordinates(char_instructions.target_well)["y"],
        wellplate.echem_height,
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
        echem.disconnectpstat()
        return char_instructions, char_results
    else:
        echem.disconnectpstat()
        raise OCPFailure("CV")


def apply_log_filter(experiment_id: int, target_well: str = None):
    """Add custom value to log format"""
    experiment_formatter = logging.Formatter(
        "%(asctime)s:%(name)s:%(levelname)s:%(custom1)s:%(custom2)s:%(message)s"
    )
    system_handler.setFormatter(experiment_formatter)
    custom_filter = CustomLoggingFilter(experiment_id, target_well)
    logger.addFilter(custom_filter)


def run_experiment(
    instructions: Experiment,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    scale: Scale,
    stock_vials: list[Vial],
    waste_vials: list[Vial],
    wellplate: Wells,
) -> Tuple[Experiment, ExperimentResult, list[Vial], list[Vial], Wells]:
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
            g. Flush pipette tip
    2. Mix solutions in well
    3. Flush pipette tip
    4. Deposit film onto substrate
    5. Withdraw all well volume into waste
    6. Rinse the well 3x
    7. Characterize the film on the substrate
    8. Rinse the well 3x

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
    apply_log_filter(instructions.id, instructions.target_well)

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        exclude_list = ["rinse0", "rinse1", "rinse2"]
        experiment_solutions = [
            vial.name for vial in stock_vials if vial.name not in exclude_list
        ]
        # experiment_solutions = ["acrylate", "peg", "dmf", "ferrocene", "custom"]

        # Deposit all experiment solutions into well
        for solution_name in experiment_solutions:
            if (
                getattr(instructions, solution_name) > 0
                and solution_name[0:4] != "rinse"
            ):  # if there is a solution to deposit
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    getattr(instructions, solution_name),
                    solution_name,
                    instructions.target_well,
                )
                stock_vials, waste_vials, wellplate = pipette(
                    # volume in ul
                    volume=getattr(instructions, solution_name),
                    solutions=stock_vials,  # list of vial objects passed to ePANDA
                    solution_name=solution_name,  # from the list above
                    target_well=instructions.target_well,
                    pumping_rate=instructions.pumping_rate,
                    waste_vials=waste_vials,  # list of vial objects passed to ePANDA
                    # this is hardcoded as waste...no reason to not be so far
                    waste_solution_name="waste",
                    wellplate=wellplate,
                    pump=pump,
                    mill=mill,
                )

                stock_vials, waste_vials = flush_pipette_tip(
                    pump,
                    waste_vials,
                    stock_vials,
                    instructions.flush_sol_name,
                    mill,
                    instructions.pumping_rate,
                    instructions.flush_vol,
                )
        logger.info("Pipetted solutions into well: %s", instructions.target_well)

        # Mix solutions in well
        if instructions.mix == 1:
            logger.info("Mixing well: %s", instructions.target_well)
            instructions.status = ExperimentStatus.MIXING
            pump.mix(
                mix_location=wellplate.get_coordinates(
                    instructions.target_well
                ),  # fetch x, y, z, depth, and echem height coordinates of well
                mix_repetitions=3,
                mix_volume=instructions.mix_vol,
                mix_rate=instructions.mix_rate,
            )
            logger.info("Mixed well: %s", instructions.target_well)

        stock_vials, waste_vials = flush_pipette_tip(
            pump,
            waste_vials,
            stock_vials,
            instructions.flush_sol_name,
            mill,
            instructions.pumping_rate,
            instructions.flush_vol,
        )

        if instructions.ca == 1:
            instructions.status = ExperimentStatus.DEPOSITING
            instructions, results = deposition(instructions, results, mill, wellplate)

            logger.info("Deposition completed for well: %s", instructions.target_well)

            # Withdraw all well volume into waste
            waste_vials, wellplate = clear_well(
                volume=wellplate.volume(instructions.target_well),
                target_well=instructions.target_well,
                wellplate=wellplate,
                pumping_rate=instructions.pumping_rate,
                pump=pump,
                waste_vials=waste_vials,
                mill=mill,
                solution_name="waste",
            )

            logger.info("Cleared dep_sol from well: %s", instructions.target_well)

            # Rinse the well 3x
            stock_vials, waste_vials, wellplate = rinse(
                wellplate=wellplate,
                instructions=instructions,
                pump=pump,
                mill=mill,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
            )

            logger.info("Rinsed well: %s", instructions.target_well)

        # Echem CV - characterization
        if instructions.cv == 1:
            logger.info(
                "Beginning eChem characterization of well: %s", instructions.target_well
            )
            # Deposit characterization solution into well

            logger.info(
                "Infuse %s into well %s...",
                instructions.char_sol_name,
                instructions.target_well,
            )
            stock_vials, waste_vials, wellplate = pipette(
                volume=instructions.char_vol,
                solutions=stock_vials,
                solution_name=instructions.char_sol_name,
                target_well=instructions.target_well,
                pumping_rate=instructions.pumping_rate,
                waste_vials=waste_vials,
                waste_solution_name="waste",
                wellplate=wellplate,
                pump=pump,
                mill=mill,
            )

            logger.info("Deposited char_sol in well: %s", instructions.target_well)

            instructions, results = characterization(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete", instructions.target_well)

            waste_vials, wellplate = clear_well(
                instructions.char_vol,
                instructions.target_well,
                wellplate,
                instructions.pumping_rate,
                pump,
                waste_vials,
                mill,
                "waste",
            )

            logger.info("Well %s cleared", instructions.target_well)

            # Flushing procedure
            stock_vials, waste_vials = flush_pipette_tip(
                pump,
                waste_vials,
                stock_vials,
                instructions.flush_sol_name,
                mill,
                instructions.pumping_rate,
                instructions.flush_vol,
            )

            logger.info("Pipette Flushed")

        instructions.status = ExperimentStatus.FINAL_RINSE
        stock_vials, waste_vials, wellplate = rinse(
            wellplate=wellplate,
            instructions=instructions,
            pump=pump,
            mill=mill,
            waste_vials=waste_vials,
            stock_vials=stock_vials,
        )
        logger.info("Final Rinse")

        instructions.status = ExperimentStatus.COMPLETE
        logger.info("End of Experiment: %s", instructions.id)

        mill.move_to_safe_position()
        logger.info("EXPERIMENT %s COMPLETED\n\n", instructions.id)

    except OCPFailure as ocp_failure:
        logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Failed instructions updated for experiment %s", instructions.id)
        return instructions, results, stock_vials, waste_vials, wellplate

    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Saved interrupted instructions for experiment %s", instructions.id)
        return instructions, results, stock_vials, waste_vials, wellplate

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
        return instructions, results, stock_vials, waste_vials, wellplate

    finally:
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info(
            "Returning completed instructions for experiment %s", instructions.id
        )

    return instructions, results, stock_vials, waste_vials, wellplate


def mixing_test_protocol(
    instructions: Experiment,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    stock_vials: list[Vial],
    waste_vials: list[Vial],
    wellplate: Wells,
) -> Tuple[Experiment, ExperimentResult, list[Vial], list[Vial], Wells]:
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
            g. Flush pipette tip
    2. Mix solutions in well
    3. Flush pipette tip
    7. Characterize the film on the substrate
    8. Return results, stock_vials, waste_vials, wellplate

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
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
        wellplate (Wells object): The wellplate object
    """
    # Add custom value to log format
    custom_filter = CustomLoggingFilter(instructions.id, instructions.target_well)
    logger.addFilter(custom_filter)

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        experiment_solutions = ["peg", "acrylate", "dmf", "custom", "ferrocene"]
        apply_log_filter(instructions.id, instructions.target_well)
        # Deposit all experiment solutions into well
        for solution_name in experiment_solutions:
            if (
                getattr(instructions, solution_name) > 0
                and solution_name[0:4] != "rinse"
            ):  # if there is a solution to deposit
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    getattr(instructions, solution_name),
                    solution_name,
                    instructions.target_well,
                )
                experiment_solutions, waste_vials, wellplate = pipette(
                    volume=getattr(instructions, solution_name),
                    solutions=stock_vials,  # list of vial objects passed to ePANDA
                    solution_name=solution_name,  # from the list above
                    target_well=instructions.target_well,
                    pumping_rate=instructions.pumping_rate,
                    waste_vials=waste_vials,  # list of vial objects passed to ePANDA
                    waste_solution_name="waste",
                    wellplate=wellplate,
                    pump=pump,
                    mill=mill,
                )

                stock_vials, waste_vials = flush_pipette_tip(
                    pump,
                    waste_vials,
                    stock_vials,
                    instructions.flush_sol_name,
                    mill,
                    instructions.pumping_rate,
                    instructions.flush_vol,
                )
        logger.info("Pipetted solutions into well: %s", instructions.target_well)

        # Mix solutions in well
        if instructions.mix == 1:
            logger.info("Mixing well: %s", instructions.target_well)
            instructions.status = ExperimentStatus.MIXING
            pump.mix(
                mix_location=wellplate.get_coordinates(instructions.target_well),
                mix_repetitions=instructions.mix_count,
                mix_volume=instructions.mix_vol,
                mix_rate=instructions.mix_rate,
            )
            logger.info("Mixed well: %s", instructions.target_well)

            stock_vials, waste_vials = flush_pipette_tip(
                pump,
                waste_vials,
                stock_vials,
                instructions.flush_sol_name,
                mill,
                instructions.pumping_rate,
                instructions.flush_vol,
            )

        # Echem CV - characterization
        if instructions.cv == 1:
            logger.info(
                "Beginning eChem characterization of well: %s", instructions.target_well
            )
            # Deposit characterization solution into well

            instructions, results = characterization(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete", instructions.target_well)
            # Flushing procedure

        instructions.status = ExperimentStatus.COMPLETE
        logger.info("End of Experiment: %s", instructions.id)

        mill.move_to_safe_position()
        logger.info("EXPERIMENT %s COMPLETED\n\n", instructions.id)

    except OCPFailure as ocp_failure:
        logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Failed instructions updated for experiment %s", instructions.id)
        return instructions, results, stock_vials, waste_vials, wellplate

    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Saved interrupted instructions for experiment %s", instructions.id)
        return instructions, results, stock_vials, waste_vials, wellplate

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
        return instructions, results, stock_vials, waste_vials, wellplate

    finally:
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info(
            "Returning completed instructions for experiment %s", instructions.id
        )

    return instructions, results, stock_vials, waste_vials, wellplate


def peg2p_protocol(
    instructions: Experiment,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    stock_vials: list[Vial],
    waste_vials: list[Vial],
    wellplate: Wells,
) -> Tuple[Experiment, ExperimentResult, list[Vial], list[Vial], Wells]:
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
            g. Flush pipette tip
    2. Flush pipette tip
    3. Electrodeposit film with CA
    4. Rinse the well
    5. Deposit characterization solution into well
    6. Characterize the film on the substrate
    7. Return results, stock_vials, waste_vials, wellplate
    8. Update the system state
    9. Update location of experiment instructions and save results

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
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials
        wellplate (Wells object): The wellplate object
    """
    # Add custom value to log format
    custom_filter = CustomLoggingFilter(instructions.id, instructions.target_well)
    logger.addFilter(custom_filter)

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        experiment_solutions = ["dmf", "peg"]
        apply_log_filter(instructions.id, instructions.target_well)
        # Deposit all experiment solutions into well
        for solution_name in experiment_solutions:
            if (
                getattr(instructions, solution_name) > 0
                and solution_name[0:4] != "rinse"
            ):  # if there is a solution to deposit
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    getattr(instructions, solution_name),
                    solution_name,
                    instructions.target_well,
                )
                experiment_solutions, waste_vials, wellplate = pipette(
                    volume=getattr(instructions, solution_name),
                    solutions=stock_vials,  # list of vial objects passed to ePANDA
                    solution_name=solution_name,  # from the list above
                    target_well=instructions.target_well,
                    pumping_rate=instructions.pumping_rate,
                    waste_vials=waste_vials,  # list of vial objects passed to ePANDA
                    waste_solution_name="waste",
                    wellplate=wellplate,
                    pump=pump,
                    mill=mill,
                )

                stock_vials, waste_vials = flush_pipette_tip(
                    pump,
                    waste_vials,
                    stock_vials,
                    instructions.flush_sol_name,
                    mill,
                    instructions.pumping_rate,
                    instructions.flush_vol,
                )
        logger.info("Pipetted solutions into well: %s", instructions.target_well)

        # Echem CA - deposition
        if instructions.ca == 1:
            instructions.status = ExperimentStatus.DEPOSITING
            instructions, results = deposition(instructions, results, mill, wellplate)
            logger.info("deposition completed for well: %s", instructions.target_well)

            waste_vials, wellplate = clear_well(
                volume=wellplate.volume(instructions.target_well),
                target_well=instructions.target_well,
                wellplate=wellplate,
                pumping_rate=instructions.pumping_rate,
                pump=pump,
                waste_vials=waste_vials,
                mill=mill,
                solution_name="waste",
            )

            logger.info("Cleared dep_sol from well: %s", instructions.target_well)

            # Rinse the well 3x
            stock_vials, waste_vials, wellplate = rinse(
                wellplate=wellplate,
                instructions=instructions,
                pump=pump,
                mill=mill,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
            )

            logger.info("Rinsed well: %s", instructions.target_well)
        # Echem CV - characterization
        if instructions.cv == 1:
            logger.info(
                "Beginning eChem characterization of well: %s", instructions.target_well
            )
            # Deposit characterization solution into well

            logger.info(
                "Infuse %s into well %s...",
                instructions.char_sol_name,
                instructions.target_well,
            )
            stock_vials, waste_vials, wellplate = pipette(
                volume=instructions.char_vol,
                solutions=stock_vials,
                solution_name=instructions.char_sol_name,
                target_well=instructions.target_well,
                pumping_rate=instructions.pumping_rate,
                waste_vials=waste_vials,
                waste_solution_name="waste",
                wellplate=wellplate,
                pump=pump,
                mill=mill,
            )

            logger.info("Deposited char_sol in well: %s", instructions.target_well)

            instructions, results = characterization(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete", instructions.target_well)

            waste_vials, wellplate = clear_well(
                instructions.char_vol,
                instructions.target_well,
                wellplate,
                instructions.pumping_rate,
                pump,
                waste_vials,
                mill,
                "waste",
            )

            logger.info("Well %s cleared", instructions.target_well)

            # Flushing procedure
            stock_vials, waste_vials = flush_pipette_tip(
                pump,
                waste_vials,
                stock_vials,
                instructions.flush_sol_name,
                mill,
                instructions.pumping_rate,
                instructions.flush_vol,
            )

            logger.info("Pipette Flushed")
            instructions.status = ExperimentStatus.COMPLETE
        logger.info("End of Experiment: %s", instructions.id)

        mill.move_to_safe_position()
        logger.info("EXPERIMENT %s COMPLETED\n\n", instructions.id)

    except OCPFailure as ocp_failure:
        logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Failed instructions updated for experiment %s", instructions.id)
        return instructions, results, stock_vials, waste_vials, wellplate

    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info("Saved interrupted instructions for experiment %s", instructions.id)
        return instructions, results, stock_vials, waste_vials, wellplate

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
        return instructions, results, stock_vials, waste_vials, wellplate

    finally:
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        logger.info(
            "Returning completed instructions for experiment %s", instructions.id
        )

    return instructions, results, stock_vials, waste_vials, wellplate


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
