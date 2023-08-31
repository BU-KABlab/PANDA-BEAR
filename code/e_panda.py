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

Returns:
    ExperimentResult: The results of the experiment.
    Wellplate: The updated wellplate object.
    Vials: The updated vials object.
"""
# pylint: disable=line-too-long

import logging
import math
from datetime import datetime
import sys
import gamrycontrol as echem
from experiment_class import Experiment, ExperimentResult, ExperimentStatus
import mill_control
from pump_control import Pump as pump_class
import vials as vial_class
import wellplate as wellplate_class

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
file_handler = logging.FileHandler("code/logs/ePANDA_module.log")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
file_handler.setFormatter(formatter)
system_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(system_handler)


def pipette(
    volume: float,  # volume in ul
    solutions: list,
    solution_name: str,
    target_well: str,
    pumping_rate: float,
    waste_vials: list,
    waste_solution_name: str,
    wellplate: object,
    pump: pump_class,
    mill: object,
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

    if volume > 0.00:
        repetitions = math.ceil(
            volume / (200 - 2 * purge_volume)
        )  # divide by pipette capacity (200 ul)
        repetition_vol = volume / repetitions
        for j in range(repetitions):
            logger.info("Repetition %d of %d", j + 1, repetitions)
            # solution = solution_selector(solution_name, repetition_vol)
            solution = solution_selector(solutions, solution_name, repetition_vol)
            # purge_vial = waste_selector(waste_solution_name, repetition_vol)
            purge_vial = waste_selector(
                waste_vials, waste_solution_name, repetition_vol
            )
            ## First half: pick up solution
            logger.info("Withdrawing %s...", solution.name)
            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], 0
            )  # start at safe height
            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], solution.bottom
            )  # go to solution depth (depth replaced with height)

            solution.update_volume(-(repetition_vol + 2 * purge_volume))
            pump.withdraw(repetition_vol + (2 * purge_volume), pumping_rate, pump)
            
            logger.debug("%s new volume: %f", solution.name, solution.volume)
            mill.move_pipette_to_position(
                solution.coordinates["x"], solution.coordinates["y"], 0
            )  # return to safe height

            ## Intermediate: Purge
            logger.info("Purging...")
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"],
                purge_vial.coordinates["y"],
                purge_vial.height,
            )  # purge_vial.depth replaced with height
            purge(purge_vial, pump, purge_volume)
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )

            ## Second Half: Deposit to well
            logger.info("Infusing %s into well %s...", solution.name, target_well)
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
            pump.infuse(repetition_vol, pumping_rate, pump)
            logger.info(
                "Well %s volume: %f", target_well, wellplate.volume(target_well)
            )
            mill.move_pipette_to_position(
                wellplate.get_coordinates(target_well)["x"],
                wellplate.get_coordinates(target_well)["y"],
                0,
            )  # return to safe height

            ## Intermediate: Purge
            logger.info("Purging...")
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"],
                purge_vial.coordinates["y"],
                purge_vial.height,
            )  # purge_vial.depth replaced with height

            purge(purge_vial, pump, purge_volume)
            mill.move_pipette_to_position(
                purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
            )

            logger.debug(
                "Remaining volume in pipette: %f ", pump.volume_withdrawn
            )  # should always be zero, pause if not


def clear_well(
    volume: float,
    target_well: str,
    wellplate: object,
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
    clear_well_buffer = 20  # an extra 20 ul to ensure the well is cleared
    repititions = math.ceil(
        volume / 200
    )  # divide by 200 ul (pipette capacity) for the number of repetitions. No purge needed here.
    repetition_vol = volume / repititions

    logger.info(
        "Clearing well %s with %dx repetitions of %f",
        target_well,
        repititions,
        repetition_vol,
    )
    for j in range(repititions):
        # TODO revisit bundling vial selection within purge, infuse, and withdraw along with updating volumes
        purge_vial = waste_selector(waste_vials, solution_name, repetition_vol + clear_well_buffer)

        logger.info("Repitition %d of %d", j + 1, repititions)
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
        wellplate.update_volume(target_well, -repetition_vol) # no buffer to avoid an overdraft error
        pump.withdraw(repetition_vol + clear_well_buffer, pumping_rate, pump)
        logger.debug("Well %s volume: %f", target_well, wellplate.volume(target_well))

        mill.move_pipette_to_position(
            wellplate.get_coordinates(target_well)["x"],
            wellplate.get_coordinates(target_well)["y"],
            0,
        )  # return to safe height

        logger.info("Moving to purge vial...")
        mill.move_pipette_to_position(
            purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
        )
        mill.move_pipette_to_position(
            purge_vial.coordinates["x"],
            purge_vial.coordinates["y"],
            purge_vial.height,
        )  # purge_vial.depth replaced with height
        logger.info("Purging...")
        purge(purge_vial, pump, repetition_vol + clear_well_buffer)  # repitition volume + 20 ul purge
        mill.move_pipette_to_position(
            purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
        )
        # pump.withdraw(20, pumping_rate, pump)
        # pump.infuse(20, pumping_rate, pump)

        logger.info("Remaining volume in well: %d", wellplate.volume(target_well))


def rinse(
    wellplate: object,
    instructions: Experiment,
    pump: pump_class,
    waste_vials: list,
    mill: object,
    stock_vials: list,
):
    """
    Rinse the well with given ul of specified rinse solution in the experiment instructions
    Args:
        wellplate (Wells object): The wellplate object
        instructions (Experiment object): The experiment instructions
        pump (object): The pump object
        waste_vials (list): The list of waste vials
        mill (object): The mill object
        stock_vials (list): The list of stock vials

    Returns:
        None
    """

    logger.info("Rinsing well %s %dx...", instructions.target_well, instructions.rinse_count)
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
    Flush the pipette tip with given ul of flush solution
    Args:
        pump (object): The pump object
        waste_vials (list): The list of waste vial objects
        stock_vials (list): The list of stock vial objects
        flush_solution_name (str): The name of the flush solution
        mill (object): The mill object
        pumping_rate (float): The pumping rate in ml/min (default 0.5)
        flush_volume (float): The volume to flush in ml (default 120)

    Returns:
        None
    """

    # flush_solution = solution_selector(flush_solution_name, flush_volume)
    # purge_vial = waste_selector("waste", flush_volume)
    flush_solution = solution_selector(stock_vials, flush_solution_name, flush_volume)
    purge_vial = waste_selector(waste_vials, "waste", flush_volume)

    logger.info("Flushing with %s...", flush_solution.name)
    mill.move_pipette_to_position(
        flush_solution.coordinates["x"], flush_solution.coordinates["y"], 0
    )
    pump.withdraw(20, pumping_rate, pump)
    mill.move_pipette_to_position(
        flush_solution.coordinates["x"],
        flush_solution.coordinates["y"],
        flush_solution.bottom,
    )  # depth replaced with height
    logger.debug("Withdrawing %s...", flush_solution.name)
    pump.withdraw(flush_volume, pumping_rate, pump)
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
    purge(purge_vial, pump, flush_volume + 20)
    mill.move_pipette_to_position(
        purge_vial.coordinates["x"], purge_vial.coordinates["y"], 0
    )  # move back to safe height (top)


def purge(purge_vial: vial_class, pump: pump_class, purge_volume=20.00, pumping_rate=0.5) -> None:
    """
    Perform purging from the pipette.
    Args:
        purge_vial (Vial object): The vial to purge into
        pump (object): The pump object to use
        purge_volume (float): The volume to purge in ml (default 20)
        pumping_rate (float): The pumping rate in ml/min (default 0.5)

    Returns:
        None
    """
    purge_vial.update_volume(purge_volume)
    pump.infuse(purge_volume, pumping_rate, pump)
    log_msg = f"Purged {purge_volume} ml"
    logger.debug(log_msg)


def solution_selector(solutions: list, solution_name: str, volume: float) -> vial_class:
    """
    Select the first solution from the list of solutions that:
        1. matches the name
        2. has enough volume

    Args:
        solutions (list): The list of solutions
        solution_name (str): The name of the desired solution
        volume (float): The volume to be added to the solution

    Returns:
        vial_class: The solution vial object
    """
    for solution in solutions:
        if solution.name.lower() == solution_name.lower() and solution.volume > (
            volume + 1000
        ):
            return solution
    raise NoAvailableSolution(solution_name)


def waste_selector(solutions: list, solution_name: str, volume: float) -> vial_class:
    """
    Select the waste vial from the list of waste vials that:
        1. matches the name
        2. has enough volume

    Args:
        solutions (list): The list of waste vials
        solution_name (str): The name of the desired waste vial
        volume (float): The volume to be added to the waste vial

    Returns:
        vial_class: The waste vial object
    """
    solution_name = solution_name.lower()
    for waste_solution in solutions:
        if (
            waste_solution.name.lower() == solution_name
            and (waste_solution.volume + volume) < waste_solution.capacity
        ):
            return waste_solution
    raise NoAvailableSolution(solution_name)


class NoAvailableSolution(Exception):
    """Raised when no available solution is found"""

    def __init__(self, solution_name):
        self.solution_name = solution_name
        self.message = f"No available solution of {solution_name} found"
        super().__init__(self.message)


def deposition(dep_instructions: Experiment,dep_results: ExperimentResult, mill, wellplate):
    """Deposition of the solutions onto the substrate"""
    ## echem setup
    logger.info("\n\nSetting up eChem experiments...")

    ## echem OCP
    logger.info("Beginning eChem OCP of well: %s", dep_instructions.target_well)
    # TODO replace update_experiment_recipt with populating experiment result data class
    # dep_instructions = update_experiment_recipt(
    #    dep_instructions, "status", "ocp", dep_instructions["filename"]
    # )
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
    dep_results.ocp_dep_pass = echem.check_vsig_range(dep_results.ocp_dep_file.with_suffix(".txt"))

    ## echem CA - deposition
    if dep_instructions["OCP_pass"]:
        logger.info("Beginning eChem deposition of well: %s", dep_instructions.target_well)
        dep_results.deposition_data_file = echem.setfilename(dep_instructions.id, "CA")
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
        mill.move_electrode_to_position(
            wellplate.get_coordinates(dep_instructions.target_well)["x"],
            wellplate.get_coordinates(dep_instructions.target_well)["y"],
            0,
        )  # move to safe height above target well

        mill.rinse_electrode()
        return dep_instructions, dep_results
    raise OCPFailure("CA")


class OCPFailure(Exception):
    """Raised when OCP fails"""

    def __init__(self, stage):
        self.stage = stage
        self.message = f"OCP failed before {stage}"
        super().__init__(self.message)


def characterization(char_instructions: Experiment,
                     char_results: ExperimentResult,
                     mill: mill_control,
                     wellplate: wellplate_class
                     ):
    """Characterization of the solutions on the substrate"""
    logger.info("Characterizing well: %s", char_instructions.target_well)
    ## echem OCP
    logger.info("Beginning eChem OCP of well: %s", char_instructions.target_well)

    # char_instructions = update_experiment_recipt(
    #     char_instructions, "status", "ocp-char", char_instructions["filename"]
    # )
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
    char_results.ocp_char_pass = (
        echem.check_vsig_range(char_results.ocp_char_file.with_suffix(".txt"))
    )
    ## echem CV - characterization
    if char_instructions.ocp_char_pass:
        if char_instructions["baseline"] == 1:
            test_type = "CV_baseline"
        else:
            test_type = "CV"
        char_results.characterization_data_file = echem.setfilename(char_instructions.id, test_type)
        echem.cyclic(
            echem.potentiostat_cv_parameters.CVvi,
            echem.potentiostat_cv_parameters.CVap1,
            echem.potentiostat_cv_parameters.CVap2,
            echem.potentiostat_cv_parameters.CVvf,
            CVsr1=char_instructions["scan-rate"],
            CVsr2=char_instructions["scan-rate"],
            CVsr3=char_instructions["scan-rate"],
            CVsamplerate=(
            echem.potentiostat_cv_parameters.CVstep / char_instructions["scan-rate"]
            ),
            CVcycle=echem.potentiostat_cv_parameters.CVcycle,
        )
        echem.activecheck()
        ## echem plot the data
        # analyzer.plotdata("CV", complete_file_name)
        mill.move_electrode_to_position(
            wellplate.get_coordinates(char_instructions.target_well)["x"],
            wellplate.get_coordinates(char_instructions.target_well)["y"],
            0,
        )  # move to safe height above target well
        mill.rinse_electrode()
        return char_instructions
    else:
        raise OCPFailure("CV")


def run_experiment(instructions: Experiment,
                   results: ExperimentResult,
                   mill: mill_control,
                   pump: pump_class,
                   stock_vials: list,
                   waste_vials: list,
                   wellplate: wellplate_class
                   ) -> ExperimentResult:
    """
    Run the experiment
    """
    try:
        logger.info("Beginning experiment %d", instructions.id)

        ## Deposit all experiment solutions into well
        # TODO reconfigure the Experiment to have this list included
        experiment_solutions = ["acrylate", "peg", "dmf", "ferrocene", "custom"]

        for solution_name in experiment_solutions:
            if getattr(instructions,solution_name) > 0:  # if there is a solution to deposit
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    getattr(instructions,solution_name),
                    solution_name,
                    instructions.target_well,
                )
                pipette(
                    volume=getattr(instructions, solution_name),  # volume in ul
                    solutions=stock_vials, # list of vial objects passed to ePANDA
                    solution_name=solution_name, # from the list above
                    target_well=instructions.target_well,
                    pumping_rate=instructions.pumping_rate,
                    waste_vials=waste_vials, # list of vial objects passed to ePANDA
                    waste_solution_name="waste", # this is hardcoded as waste...no reason to not be so far
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

        logger.info("Pipetted solutions: %f", datetime.now())

        if instructions["ca"] == 1:
            instructions.status = ExperimentStatus.DEPOSITING
            instructions, results = deposition(
                instructions,results, mill, wellplate
            )

            logger.info("Deposition completed: %f", datetime.now())

            ## Withdraw all well volume into waste
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

            logger.info("Cleared dep_sol: %f", datetime.now())

            ## Rinse the well 3x
            rinse(
                wellplate,
                instructions,
                pump,
                waste_vials,
                mill,
                stock_vials
            )

            logger.info("Rinsed well: %f", datetime.now())
            logger.info("Well rinsed")

        ## Echem CV - characterization
        if instructions["cv"] == 1:
            logger.info("Beginning eChem characterization of well: %s", instructions.target_well)
            ## Deposit characterization solution into well

            logger.info("Infuse %s into well %s...",
                        instructions.char_sol_name,
                        instructions.target_well)
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

            logger.info("Deposited char_sol: %f", datetime.now())

            instructions, results = characterization(
                instructions,results, mill, wellplate
            )

            logger.info("Characterization complete: %f", datetime.now())

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

            logger.info("Well cleared: %f", datetime.now())

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

            logger.info("Pipette Flushed: %f", datetime.now())

        instructions.status = ExperimentStatus.FINAL_RINSE
        rinse(
            wellplate,
            instructions,
            pump,
            waste_vials,
            mill,
            stock_vials
        )
        logger.info("Final Rinse: %f", datetime.now())

        instructions.status = ExperimentStatus.COMPLETE
        logger.info("End: %f", datetime.now())


        mill.move_to_safe_position()
        logger.info("EXPERIMENT %s COMPLETED\n\n", instructions.id)

    except OCPFailure as ocp_failure:
        logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.datetime.now().strftime(
            "%Y-%m-%d_%H_%M_%S"
        )
        logger.info("Failed instructions updated for experiment %s", instructions.id)
        return 1

    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date= datetime.datetime.now().strftime(
            "%Y-%m-%d_%H_%M_%S"
        )
        logger.info("Saved interrupted instructions for experiment %s", instructions.id)
        return 2


    except Exception as general_exception:
        exception_type, experiment_object, exception_traceback = sys.exc_info()
        filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        logger.error("Exception: %s", general_exception)
        logger.error("Exception type: %s", exception_type)
        logger.error("File name: %s", filename)
        logger.error("Line number: %d", line_number)
        instructions["status"] = "error"
        instructions["status_date"] = datetime.datetime.now().strftime(
            "%Y-%m-%d_%H_%M_%S"
        )
        return 1

    finally:
        instructions["status_date"] = datetime.datetime.now().strftime(
            "%Y-%m-%d_%H_%M_%S"
        )
        logger.info("Saved completed instructions for experiment %s", instructions.id)
        # change_well_status(current_well, instructions["status"])
    return 0


if __name__ == "__main__":
    import pathlib
    from experiment_class import make_test_value
    pump_driver = pump_class()
    mill_driver = mill_control.Mill()
    echem.initialize()
    path_to_state = pathlib.Path.cwd() / "code/state"
    stock_vials_list = vial_class.read_vials(path_to_state / "vial_status.json")
    waste_vials_list = vial_class.read_vials(path_to_state / "waste_status.json")
    wells_object = wellplate_class.Wellplate(-218, -74, 0, 0)
    test_instructions = make_test_value()
    test_results = ExperimentResult()
    run_experiment(
        instructions=test_instructions,
        results=test_results,
        mill=mill_driver,
        pump=pump_driver,
        stock_vials=stock_vials_list,
        waste_vials=waste_vials_list,
        wellplate=wells_object,
    )
