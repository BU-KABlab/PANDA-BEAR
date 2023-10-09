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
# pylint: disable=line-too-long

# Standard library imports
import logging
import math
from datetime import datetime
import sys
import time
from typing import List, Tuple
import pytz as tz

# Third party or custom imports
import gamry_control_WIP as echem
from experiment_class import Experiment, ExperimentResult, ExperimentStatus, make_test_value
from mill_control import Mill as mill_control
from pump_control import Pump as pump_class
from scale import Sartorius as scale_class
import vials as vial_class
import wellplate as wellplate_module
from wellplate import Wells

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(custom1)s:%(custom2)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

class CustomLoggingFilter(logging.Filter):
    """ This is a filter which injects custom values into the log record.
    From: https://stackoverflow.com/questions/56776576/how-to-add-custom-values-to-python-logging
    The values will be the experiment id and the well id
    """
    def __init__(self, custom1, custom2):
        super().__init__()
        self.custom1 = custom1
        self.custom2 = custom2

    def filter(self, record):
        record.custom1 = self.custom1
        record.custom2 = self.custom2
        return True

def pipette(
    volume: float,  # volume in ul
    solutions: list,
    solution_name: str,
    target_well: str,
    pumping_rate: float,
    waste_vials: list,
    waste_solution_name: str,
    wellplate: Wells,
    pump: pump_class,
    mill: mill_control,
    purge_volume=20.00,
):
    """
    Perform the full pipetting sequence
    Args:
        volume (float): Volume to be pipetted into desired well
        solution (Vial object): the vial source or solution to be pipetted
        target_well (str): The alphanumeric name of the well you would like to pipette into
        purge_volume (float): Desired about to purge before and after pipetting
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
            logger.info("Repetition %d of %d",
                        j + 1,  repetitions)
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
            logger.debug("Withdrawing %f of air gap...",
                         air_gap)
            pump.withdraw(
                air_gap, solution, pumping_rate
            )  # withdraw air gap to engage screw

            logger.info("Moving to %s...", solution.name)
            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], 0
            )  # start at safe height
            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], solution.bottom
            )  # go to solution depth (depth replaced with height)

            # Estimate the weight to be withdrawn
            # based on the density of the solution
            # and the volume to be withdrawn
            # estimated_weight = solution.density * repetition_and_purge_vol
            # weight_before = scale.value()
            # logger.debug(":%s:Scale: Weight before: %f",target_well, weight_before)
            solution.update_volume(-(repetition_and_purge_vol))
            # logger.info(":%s:Scale: Withdrawing %s...", target_well, solution.name)
            pump.withdraw(
                volume=repetition_and_purge_vol, solution=solution, rate=pumping_rate
            )  # pipette now has air gap + repitition + 2 purge vol
            # logger.debug(":%s: %s new volume: %f", target_well, solution.name, solution.volume)
            # weight_after = scale.value()
            # logger.debug(":%s:Scale: Weight after: %f", target_well, weight_after)
            # logger.debug(":%s:Scale: Weight difference: %f", target_well, weight_before - weight_after)
            # logger.debug(":%s:Scale: Weight deviation: %f", target_well, weight_before - weight_after - estimated_weight)

            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], 0
            )  # return to safe height

            # Intermediate: Purge
            logger.info(
                "%s: Moving to purge vial: %s...", target_well, purge_vial.name
            )
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"],
                purge_vial.coordinates["y"],
                purge_vial.height,
            )  # purge_vial.depth replaced with height

            pump.purge(
                purge_vial, solution, purge_volume
            )  # remaining vol in pipette is now air gap + repition vol + 1 purge
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )

            # Second Half: Deposit to well
            logger.info("Moving to target well: %s...",
                        target_well)
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
                "%s: Infusing %s into well %s...",
                target_well,
                solution.name,
                target_well,
            )
            pump.infuse(
                volume=repetition_vol, solution=solution, rate=pumping_rate
            )  # remaining vol in pipette is now air gap + 1 purge vol
            logger.info(
                "%s: Well %s volume: %f",
                target_well,
                target_well,
                wellplate.volume(target_well),
            )

            mill.move_pipette_to_position(
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                0,
            )  # return to safe height

            # End Purge
            logger.debug(
                "%s: Moving to purge vial: %s...", target_well, purge_vial.name
            )
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"],
                purge_vial.coordinates["y"],
                purge_vial.height,
            )  # purge_vial.depth replaced with height

            pump.purge(
                purge_vial, solution, purge_volume
            )  # remaining vol in pipette is now air gap
            # Pump out the air gap
            pump.infuse(volume=air_gap, rate=0.5)  # purge the pipette tip
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )

            logger.debug(
                "%s: Remaining volume in pipette: %f ",
                target_well,
                pump.pump.volume_withdrawn,
            )  # should always be zero, pause if not

            if round(pump.pipette_volume_ul, 2) != 0.00:
                while pump.pipette_volume_ul > 0.00:
                    logger.warning(
                        "%s: Pipette not empty. Volume: %f. Attempting to purge",
                        target_well,
                        pump.pipette_volume_ul,
                    )
                    pump.infuse(volume=pump.pipette_volume_ul,
                                rate=pumping_rate)
                    time.sleep(1)

                logger.debug("Pipette empty. Continuing...")


def clear_well(
    volume: float,
    target_well: str,
    wellplate: Wells,
    pumping_rate: float,
    pump: pump_class,
    waste_vials: list,
    mill: object,
    solution_name="waste",
):
    """
    Clear the well of the specified volume with the specified solution

    Args:
        volume (float): Volume to be cleared in microliters
        target_well (str): The alphanumeric name of the well you would like to clear
        wellplate (Wells object): The wellplate object
        pumping_rate (float): The pumping rate in ml/min
        pump (object): The pump object
        waste_vials (list): The list of waste vials
        mill (object): The mill object

    Returns:
        None
    """
    repetition = math.ceil(
        volume / 200
    )  # divide by 200 ul which is the pipette capacity to determin the number of repetitions
    repetition_vol = volume / repetition
    air_gap = 20  # ul
    logger.info(
        "Clearing well %s with %dx repetitions of %f",
        target_well,
        repetition,
        repetition_vol,
    )
    for j in range(repetition):
        purge_vial = waste_selector(waste_vials, solution_name, repetition_vol)

        logger.info("Repitition %d of %d", j + 1, repetition)
        logger.debug("Withdrawing %f of air gap...", air_gap)
        # withdraw a little to engange screw
        pump.withdraw(air_gap, pumping_rate)
        logger.debug("Moving to %s...", target_well)
        mill.move_pipette_to_position(
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            0,
        )  # start at safe height
        mill.move_pipette_to_position(
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            wellplate.depth(target_well),
        )  # go to bottom of well

        wellplate.update_volume(target_well, -repetition_vol)
        logger.debug("Withdrawing %f from %s...",
                     repetition_vol, target_well)
        pump.withdraw(
            volume=repetition_vol,
            solution=wellplate.density(target_well),
            rate=pumping_rate,
        )  # withdraw the volume from the well

        logger.debug("Well %s volume: %f", target_well,
                     wellplate.volume(target_well))
        mill.move_pipette_to_position(
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            0,
        )  # return to safe height

        logger.info("Moving to purge vial %s...", purge_vial.name)
        mill.move_pipette_to_position(
            purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
        )
        mill.move_pipette_to_position(
            purge_vial.coordinates["x"],
            purge_vial.coordinates["y"],
            purge_vial.height,
        )  # purge_vial.depth replaced with height

        pump.purge(
            purge_vial, wellplate.density(target_well), repetition_vol
        )  # repitition volume
        logger.info("Purging the air gap...")
        pump.infuse(volume=air_gap, rate=0.5)  # extra purge to clear pipette

        mill.move_pipette_to_position(
            purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
        )
        logger.info("Remaining volume in well: %f",
                    wellplate.volume(target_well))
        if round(pump.pipette_volume_ul, 2) != 0.00:
            while pump.pipette_volume_ul != 0:
                logger.warning(
                    "Pipette not empty. Volume: %f. Attempting to purge",
                    pump.pipette_volume_ul,
                )
                pump.infuse(pump.pipette_volume_ul, pumping_rate)
                time.sleep(1)

            logger.debug("Pipette empty. Continuing...")



def rinse(
    wellplate: Wells,
    instructions: Experiment,
    pump: pump_class,
    scale: scale_class,
    mill: object,
    stock_vials: list,
    waste_vials: list,
):
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
        None
    """

    logger.info(
        "Rinsing well %s %dx...", instructions.target_well, instructions.rinse_count
    )
    for rep in range(instructions.rinse_count):  # 0, 1, 2...
        rinse_solution_name = "rinse" + str(rep)
        # purge_vial = waste_selector(rinse_solution_name, rinse_vol)
        # rinse_solution = solution_selector(stock_vials, rinse_solution_name, rinse_vol)
        logger.info("Rinse %d of %d", rep + 1, instructions.rinse_count)
        pipette(
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
            scale,
        )
        clear_well(
            instructions.rinse_vol,
            instructions.target_well,
            wellplate,
            instructions.pumping_rate,
            pump,
            waste_vials,
            mill,
            solution_name=rinse_solution_name,
        )


def flush_pipette_tip(
    pump: pump_class,
    waste_vials: list,
    stock_vials: list,
    flush_solution_name: str,
    mill: object,
    pumping_rate=0.5,
    flush_volume=120,
):
    """
    Flush the pipette tip with flush_volume ul of DMF to remove any residue
    Args:
        pump (object): The pump object
        waste_vials (list): The list of waste vials
        stock_vials (list): The list of stock vials
        flush_solution_name (str): The name of the flush solution
        mill (object): The mill object
        pumping_rate (float): The pumping rate in ml/min
        flush_volume (float): The volume to flush with in microliters

    Returns:
        None
    """

    # flush_solution = solution_selector(flush_solution_name, flush_volume)
    # purge_vial = waste_selector("waste", flush_volume)
    flush_solution = solution_selector(
        stock_vials, flush_solution_name, flush_volume)
    purge_vial = waste_selector(waste_vials, "waste", flush_volume)
    air_gap = 40  # ul

    logger.info("Moving to flush solution %s...", flush_solution.name)
    mill.move_pipette_to_position(
        flush_solution.coordinates["x"], flush_solution.coordinates["y"], 0
    )
    logger.debug("Withdrawing %f of air gap...", air_gap)
    pump.withdraw(air_gap, pumping_rate)

    mill.move_pipette_to_position(
        flush_solution.coordinates["x"],
        flush_solution.coordinates["y"],
        flush_solution.bottom,
    )  # depth replaced with height

    logger.debug("Withdrawing %s...", flush_solution.name)
    pump.withdraw(volume=flush_volume,
                  solution=flush_solution, rate=pumping_rate)
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
    pump.purge(purge_vial, flush_solution, flush_volume)
    logger.debug("Purging the air gap...")
    pump.infuse(volume=air_gap, rate=0.5)  # purge the pipette tip
    mill.move_pipette_to_position(
        purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
    )  # move back to safe height (top)


def solution_selector(solutions: list, solution_name: str, volume: float) -> vial_class:
    """
    Select the solution from which to writhdraw from from the list of solution objects
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


def waste_selector(solutions: list, solution_name: str, volume: float) -> vial_class:
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


class NoAvailableSolution(Exception):
    """Raised when no available solution is found"""

    def __init__(self, solution_name):
        self.solution_name = solution_name
        self.message = f"No available solution of {solution_name} found"
        super().__init__(self.message)


def deposition(
    dep_instructions: Experiment,
    dep_results: ExperimentResult,
    mill: mill_control,
    wellplate: Wells,
):
    """Deposition of the solutions onto the substrate"""
    # echem setup
    logger.info("\n\nSetting up eChem experiments...")

    # echem OCP
    logger.info("Beginning eChem OCP of well: %s",
                dep_instructions.target_well)
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
    dep_results.ocp_dep_file = echem.setfilename(dep_instructions.id, "OCP")
    echem.OCP(
        echem.potentiostat_ocp_parameters.OCPvi,
        echem.potentiostat_ocp_parameters.OCPti,
        echem.potentiostat_ocp_parameters.OCPrate,
    )  # OCP
    echem.activecheck()
    dep_results.ocp_dep_pass = echem.check_vsig_range(
        dep_results.ocp_dep_file.with_suffix(".txt")
    )

    # echem CA - deposition
    if dep_instructions["OCP_pass"]:
        dep_instructions.status = ExperimentStatus.DEPOSITING
        logger.info(
            "Beginning eChem deposition of well: %s", dep_instructions.target_well
        )
        dep_results.deposition_data_file = echem.setfilename(
            dep_instructions.id, "CA")

        # TODO have chrono return the max and min values for the deposition
        # and save them to the results
        echem.chrono(
            echem.potentiostat_ca_parameters.CAvi,
            echem.potentiostat_ca_parameters.CAti,
            CAv1=dep_instructions["dep-pot"],
            CAt1=dep_instructions["dep-duration"],
            CAv2=echem.potentiostat_ca_parameters.CAv2,
            CAt2=echem.potentiostat_ca_parameters.CAt2,
            CAsamplerate=dep_instructions["sample-period"],
        )  # CA

        echem.activecheck()
        mill.move_to_safe_position()  # move to safe height above target well

        mill.rinse_electrode()
        return dep_instructions, dep_results
    raise OCPFailure("CA")


class OCPFailure(Exception):
    """Raised when OCP fails"""

    def __init__(self, stage):
        self.stage = stage
        self.message = f"OCP failed before {stage}"
        super().__init__(self.message)


def characterization(
    char_instructions: Experiment,
    char_results: ExperimentResult,
    mill: mill_control,
    wellplate: Wells,
):
    """Characterization of the solutions on the substrate"""
    logger.info("Characterizing well: %s", char_instructions.target_well)
    # echem OCP
    logger.info("Beginning eChem OCP of well: %s",
                char_instructions.target_well)

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
    char_results.ocp_char_file = echem.setfilename(
        char_instructions.id, "OCP_char")
    echem.OCP(
        echem.potentiostat_ocp_parameters.OCPvi,
        echem.potentiostat_ocp_parameters.OCPti,
        echem.potentiostat_ocp_parameters.OCPrate,
    )  # OCP
    echem.activecheck()
    char_results.ocp_char_pass = echem.check_vsig_range(
        char_results.ocp_char_file.with_suffix(".txt")
    )
    # echem CV - characterization
    if char_instructions.ocp_char_pass:
        if char_instructions["baseline"] == 1:
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
            CVsr1=char_instructions["scan-rate"],
            CVsr2=char_instructions["scan-rate"],
            CVsr3=char_instructions["scan-rate"],
            CVsamplerate=(
                echem.potentiostat_cv_parameters.CVstep /
                char_instructions["scan-rate"]
            ),
            CVcycle=echem.potentiostat_cv_parameters.CVcycle,
        )
        echem.activecheck()
        mill.move_to_safe_position()  # move to safe height above target well
        mill.rinse_electrode()
        return char_instructions
    else:
        raise OCPFailure("CV")


def run_experiment(
    instructions: Experiment,
    results: ExperimentResult,
    mill: mill_control,
    pump: pump_class,
    scale: scale_class,
    stock_vials: list,
    waste_vials: list,
    wellplate: Wells,
) -> Tuple[Experiment, ExperimentResult, List, List, Wells]:
    """
    Run the experiment
    """
    # Add custom value to log format
    custom_filter = CustomLoggingFilter(instructions.id, instructions.target_well)
    logger.addFilter(custom_filter)

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        exclude_list = ["rinse0", "rinse1", "rinse2"]
        experiment_solutions = [
            vial.name for vial in stock_vials if vial.name not in exclude_list]
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
                pipette(
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

                flush_pipette_tip(
                    pump,
                    waste_vials,
                    stock_vials,
                    instructions.flush_sol_name,
                    mill,
                    instructions.pumping_rate,
                    instructions.flush_vol,
                )
        logger.info("Pipetted solutions into well: %s",
                    instructions.target_well)

        # Mix solutions in well
        if instructions.mix == 1:
            logger.info("Mixing well: %s", instructions.target_well)
            instructions.status = ExperimentStatus.MIXING
            pump.mix(
                mix_location=wellplate.get_coordinates(
                    instructions.target_well),
                mix_repetitions=3,
                mix_volume=instructions.mix_vol,
                mix_rate=instructions.mix_rate,
            )
            logger.info("Mixed well: %s", instructions.target_well)

        flush_pipette_tip(
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
            instructions, results = deposition(
                instructions, results, mill, wellplate)

            logger.info("Deposition completed for well: %s",
                        instructions.target_well)

            # Withdraw all well volume into waste
            clear_well(
                volume=wellplate.volume(instructions.target_well),
                target_well=instructions.target_well,
                wellplate=wellplate,
                pumping_rate=instructions.pumping_rate,
                pump=pump,
                waste_vials=waste_vials,
                mill=mill,
                solution_name="waste",
            )

            logger.info("Cleared dep_sol from well: %s",
                        instructions.target_well)

            # Rinse the well 3x
            rinse(
                wellplate=wellplate,
                instructions=instructions,
                pump=pump,
                scale=scale,
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
            pipette(
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

            logger.info("Deposited char_sol in well: %s",
                        instructions.target_well)

            instructions, results = characterization(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete",
                        instructions.target_well)

            clear_well(
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
            flush_pipette_tip(
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
        rinse(
            wellplate=wellplate,
            instructions=instructions,
            pump=pump,
            scale=scale,
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
        instructions.status_date = datetime.now(tz.timezone('US/Eastern'))
        logger.info("Failed instructions updated for experiment %s",
                    instructions.id)
        return instructions, results, stock_vials, waste_vials, wellplate

    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone('US/Eastern'))
        logger.info(
            "Saved interrupted instructions for experiment %s", instructions.id)
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
        instructions.status_date = datetime.now(tz.timezone('US/Eastern'))
        return instructions, results, stock_vials, waste_vials, wellplate

    finally:
        instructions.status_date = datetime.now(tz.timezone('US/Eastern'))
        logger.info(
            "Returning completed instructions for experiment %s", instructions.id)

    return instructions, results, stock_vials, waste_vials, wellplate


if __name__ == "__main__":
    import pathlib

    mill_driver = mill_control.Mill()
    Sartorius = scale_class()
    pump_driver = pump_class(mill=mill_driver, scale=Sartorius)
    echem.pstatconnect()
    path_to_state = pathlib.Path.cwd() / "code/state"
    stock_vials_list = vial_class.read_vials(
        path_to_state / "vial_status.json")
    waste_vials_list = vial_class.read_vials(
        path_to_state / "waste_status.json")
    wells_object = wellplate_module.Wellplate(-218, -74, 0, 0)
    test_instructions = make_test_value()
    test_results = ExperimentResult()
    run_experiment(
        instructions=test_instructions,
        results=test_results,
        mill=mill_driver,
        pump=pump_driver,
        scale=Sartorius,
        stock_vials=stock_vials_list,
        waste_vials=waste_vials_list,
        wellplate=wells_object,
    )
    print(test_results)

    # close connections
    echem.pstatdisconnect()
    mill_driver.disconnect()
