"""The standard experiment protocol for eChem experiments."""
# pylint: disable=too-many-lines
# Standard imports
from datetime import datetime
import json
import logging
import sys
from typing import Sequence, Tuple, Union

# Non-standard imports
import pytz as tz
from experiment_class import (
    ExperimentBase,
    ExperimentResult,
    ExperimentStatus,
    PEG2P_Test_Instructions,
    LayeredExperiments,
)
from mill_control import Mill, MockMill
from pump_control import Pump, MockPump
from vials import StockVial, WasteVial
from wellplate import Wells, Wells2
from e_panda import (
    deposition,
    characterization,
    apply_log_filter,
    solution_selector,
    waste_selector,
    forward_pipette_v2,
    reverse_pipette_v2,
    flush_v2,
    rinse_v2,
    volume_correction,
    OCPFailure,
    NoAvailableSolution,
)


def standard_experiment_protocol(
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    wellplate: Wells,
    logger: logging.Logger,
) -> Tuple[
    ExperimentBase, ExperimentResult, Sequence[StockVial], Sequence[WasteVial], Wells
]:
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
    apply_log_filter(
        instructions.id,
        instructions.target_well,
        str(instructions.project_id) + "." + str(instructions.project_campaign_id),
    )

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
                forward_pipette_v2(
                    volume=getattr(instructions, solution_name),
                    from_vessel=solution_selector(
                        stock_vials, solution_name, getattr(instructions, solution_name)
                    ),
                    to_vessel=wellplate.wells[instructions.target_well],
                    pump=pump,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                )

                flush_v2(
                    pump=pump,
                    waste_vials=waste_vials,
                    stock_vials=stock_vials,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                    flush_volume=instructions.flush_vol,
                    flush_solution_name=instructions.flush_sol_name,
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

        flush_v2(
            pump=pump,
            waste_vials=waste_vials,
            stock_vials=stock_vials,
            mill=mill,
            pumping_rate=instructions.pumping_rate,
            flush_volume=instructions.flush_vol,
            flush_solution_name=instructions.flush_sol_name,
        )

        if instructions.ca == 1:
            instructions.status = ExperimentStatus.DEPOSITING
            instructions, results = deposition(instructions, results, mill, wellplate)

            logger.info("Deposition completed for well: %s", instructions.target_well)

            # Withdraw all well volume into waste
            forward_pipette_v2(
                volume=wellplate.read_volume(instructions.target_well),
                from_vessel=wellplate.wells[instructions.target_well],
                to_vessel=waste_selector(
                    waste_vials,
                    "waste",
                    wellplate.read_volume(instructions.target_well),
                ),
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Cleared dep_sol from well: %s", instructions.target_well)

            # Rinse the well 3x
            rinse_v2(
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
            forward_pipette_v2(
                volume=instructions.char_vol,
                from_vessel=solution_selector(
                    stock_vials, instructions.char_sol_name, instructions.char_vol
                ),
                to_vessel=wellplate.wells[instructions.target_well],
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Deposited char_sol in well: %s", instructions.target_well)

            instructions, results = characterization(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete", instructions.target_well)

            forward_pipette_v2(
                volume=instructions.char_vol,
                from_vessel=wellplate.wells[instructions.target_well],
                to_vessel=waste_selector(waste_vials, "waste", instructions.char_vol),
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Well %s cleared", instructions.target_well)

            # Flushing procedure
            flush_v2(
                pump=pump,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
                flush_volume=instructions.flush_vol,
                flush_solution_name=instructions.flush_sol_name,
            )

            logger.info("Pipette Flushed")

        instructions.status = ExperimentStatus.FINAL_RINSE
        rinse_v2(
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
        logger.info("EXPERIMENT %s COMPLETED", instructions.id)

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
    instructions: PEG2P_Test_Instructions,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    wellplate: Wells,
    logger: logging.Logger,
) -> Tuple[
    PEG2P_Test_Instructions,
    ExperimentResult,
    Sequence[StockVial],
    Sequence[WasteVial],
    Wells,
]:
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
    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        experiment_solutions = ["dmf", "peg"]
        apply_log_filter(
            instructions.id,
            instructions.target_well,
            str(instructions.project_id) + "." + str(instructions.project_campaign_id),
        )

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
                forward_pipette_v2(
                    volume=getattr(instructions, solution_name),
                    from_vessel=solution_selector(
                        stock_vials, solution_name, getattr(instructions, solution_name)
                    ),
                    to_vessel=wellplate.wells[instructions.target_well],
                    pump=pump,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                )

                flush_v2(
                    pump=pump,
                    waste_vials=waste_vials,
                    stock_vials=stock_vials,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                    flush_volume=instructions.flush_vol,
                    flush_solution_name=instructions.flush_sol_name,
                )
        logger.info("Pipetted solutions into well: %s", instructions.target_well)

        # Echem CA - deposition
        if instructions.ca == 1:
            instructions.status = ExperimentStatus.DEPOSITING
            instructions, results = deposition(instructions, results, mill, wellplate)
            logger.info("deposition completed for well: %s", instructions.target_well)

            forward_pipette_v2(
                volume=wellplate.read_volume(instructions.target_well),
                from_vessel=wellplate.wells[instructions.target_well],
                to_vessel=waste_selector(
                    waste_vials,
                    "waste",
                    wellplate.read_volume(instructions.target_well),
                ),
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Cleared dep_sol from well: %s", instructions.target_well)

            # Rinse the well 3x
            rinse_v2(
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
            forward_pipette_v2(
                volume=instructions.char_vol,
                from_vessel=solution_selector(
                    stock_vials, instructions.char_sol_name, instructions.char_vol
                ),
                to_vessel=wellplate.wells[instructions.target_well],
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Deposited char_sol in well: %s", instructions.target_well)

            instructions, results = characterization(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete", instructions.target_well)

            forward_pipette_v2(
                volume=instructions.char_vol,
                from_vessel=wellplate.wells[instructions.target_well],
                to_vessel=waste_selector(waste_vials, "waste", instructions.char_vol),
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Well %s cleared", instructions.target_well)

            # Flushing procedure
            flush_v2(
                pump=pump,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
                flush_volume=instructions.flush_vol,
                flush_solution_name=instructions.flush_sol_name,
            )

            logger.info("Pipette Flushed")
            instructions.status = ExperimentStatus.COMPLETE
        logger.info("End of Experiment: %s", instructions.id)

        mill.move_to_safe_position()
        logger.info("EXPERIMENT %s COMPLETED", instructions.id)

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
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    wellplate: Wells,
    logger: logging.Logger,
) -> Tuple[
    ExperimentBase, ExperimentResult, Sequence[StockVial], Sequence[WasteVial], Wells
]:
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
    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        experiment_solutions = ["peg", "acrylate", "dmf", "custom", "ferrocene"]
        apply_log_filter(
            instructions.id,
            instructions.target_well,
            str(instructions.project_id) + "." + str(instructions.project_campaign_id),
        )
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
                forward_pipette_v2(
                    volume=getattr(instructions, solution_name),
                    from_vessel=solution_selector(
                        stock_vials, solution_name, getattr(instructions, solution_name)
                    ),
                    to_vessel=wellplate.wells[instructions.target_well],
                    pump=pump,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                )

                flush_v2(
                    pump=pump,
                    waste_vials=waste_vials,
                    stock_vials=stock_vials,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                    flush_volume=instructions.flush_vol,
                    flush_solution_name=instructions.flush_sol_name,
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

            flush_v2(
                pump=pump,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
                flush_volume=instructions.flush_vol,
                flush_solution_name=instructions.flush_sol_name,
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
        logger.info("EXPERIMENT %s COMPLETED", instructions.id)

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


def pipette_accuracy_protocol_v2(
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    stock_vials: Sequence[StockVial],
    wellplate: Wells2,
    logger: logging.Logger,
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
                solution_volume > 0 and solution_name in available_solutions
            ):  # if there is a solution to deposit
                matched += 1
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    solution_volume,
                    solution_name,
                    instructions.target_well,
                )

                stock_vial = solution_selector(
                    stock_vials, solution_name, solution_volume
                )
                forward_pipette_v2(
                    volume=solution_volume,
                    from_vessel=stock_vial,
                    to_vessel=wellplate.wells[instructions.target_well],
                    pump=pump,
                    mill=mill,
                    pumping_rate=None,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.target_well,
        )

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
    logger: logging.Logger,
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
    apply_log_filter(
        instructions.id,
        instructions.target_well,
        str(instructions.project_id) + "." + str(instructions.project_campaign_id),
    )

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        exclude_list = ["rinse0", "rinse1", "rinse2"]
        available_solutions = [
            vial.name for vial in stock_vials if vial.name not in exclude_list
        ]

        # although we already checked before running the experiment we want to check again
        # that all requested solutions are found
        experiment_solution_count = len(instructions.solutions)
        matched = 0

        ## Deposit all experiment solutions into well
        for solution_name in instructions.solutions:
            solution_name = str(solution_name).lower()
            solution_volume = instructions.solutions[solution_name]
            if (
                solution_volume > 0 and solution_name in available_solutions
            ):  # if there is a solution to deposit
                matched += 1
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    solution_volume,
                    solution_name,
                    instructions.target_well,
                )

                stock_vial = solution_selector(
                    stock_vials, solution_name, solution_volume
                )

                if instructions.id % 2 == 0:
                    logger.info("Forward pipetting")
                    forward_pipette_v2(
                        volume=solution_volume,
                        from_vessel=stock_vial,
                        to_vessel=wellplate.wells[instructions.target_well],
                        pump=pump,
                        mill=mill,
                    )
                else:
                    logger.info("Reverse pipetting")
                    purge_vial = waste_selector(waste_vials, "waste", solution_volume)
                    reverse_pipette_v2(
                        volume=solution_volume,
                        from_vessel=stock_vial,
                        to_vessel=wellplate.wells[instructions.target_well],
                        purge_vessel=purge_vial,
                        pump=pump,
                        mill=mill,
                    )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.target_well,
        )

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
    logger: logging.Logger,
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
    apply_log_filter(
        instructions.id,
        instructions.target_well,
        str(instructions.project_id) + "." + str(instructions.project_campaign_id),
    )

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        exclude_list = ["rinse0", "rinse1", "rinse2"]
        available_solutions = [
            vial.name for vial in stock_vials if vial.name not in exclude_list
        ]

        # although we already checked before running the experiment we want to check again 
        # that all requested solutions are found
        experiment_solution_count = len(instructions.solutions)
        matched = 0

        ## Deposit all experiment solutions into well
        for solution_name in instructions.solutions:
            solution_name = str(solution_name).lower()
            solution_volume = instructions.solutions[solution_name]
            if (
                solution_volume > 0 and solution_name in available_solutions
            ):  # if there is a solution to deposit
                matched += 1
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    solution_volume,
                    solution_name,
                    instructions.target_well,
                )

                stock_vial = solution_selector(
                    stock_vials, solution_name, solution_volume
                )
                forward_pipette_v2(
                    volume=solution_volume,
                    from_vessel=stock_vial,
                    to_vessel=wellplate.wells[instructions.target_well],
                    pump=pump,
                    mill=mill,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.target_well,
        )

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
        exception_type = type(general_exception).__name__
        exception_traceback = sys.exc_info()[2]
        filename = (
            exception_traceback.tb_frame.f_code.co_filename
            if exception_traceback
            else ""
        )
        line_number = exception_traceback.tb_lineno if exception_traceback else 0
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


def viscocity_experiments_protocol(
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Union[Mill, MockMill],
    pump: Union[Pump, MockPump],
    stock_vials: Sequence[StockVial],
    wellplate: Wells2,
    logger: logging.Logger,
):
    """
    Protocol for testing the pumping rates for various viscosities of solutions
    1. Deposit solutions into well
        for each solution:
            a. Withdraw air gap
            b. Withdraw solution
            c. Read the scale
            d. Deposit into well
            e. Blow out
            f. Read the scale

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
    apply_log_filter(
        instructions.id,
        instructions.target_well,
        str(instructions.project_id) + "." + str(instructions.project_campaign_id),
    )

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        exclude_list = ["rinse0", "rinse1", "rinse2"]
        available_solutions = [
            vial.name for vial in stock_vials if vial.name not in exclude_list
        ]

        # although we already checked before running the experiment we want to check again
        # that all requested solutions are found
        experiment_solution_count = len(instructions.solutions)
        matched = 0

        ## Deposit all experiment solutions into well
        for solution_name in instructions.solutions:
            solution_name = str(solution_name).lower()
            solution_volume = instructions.solutions[solution_name]
            if (
                solution_volume > 0 and solution_name in available_solutions
            ):  # if there is a solution to deposit
                matched += 1
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    solution_volume,
                    solution_name,
                    instructions.target_well,
                )

                stock_vial = solution_selector(
                    stock_vials, solution_name, solution_volume
                )
                forward_pipette_v2(
                    volume=solution_volume,
                    from_vessel=stock_vial,
                    to_vessel=wellplate.wells[instructions.target_well],
                    pump=pump,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.target_well,
        )

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
        exception_type = type(general_exception).__name__
        exception_traceback = sys.exc_info()[2]
        if exception_traceback is not None:
            frame = exception_traceback.tb_frame
            filename = frame.f_code.co_filename
            line_number = exception_traceback.tb_lineno
        else:
            filename = "Unknown"
            line_number = -1
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


def layered_solution_protocol(
    instructions: list[LayeredExperiments],
    mill: Union[Mill, MockMill],
    pump: Union[Pump, MockPump],
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    wellplate: Wells2,
    logger: logging.Logger,
):
    """
    For a layered protocol we want to deposit each solution into every well that requires 
    it in one "pass" followed by a flush of the pipette tip.
    Then repeat until each solution has been desposited into each well that requires it.
    We then will work well by well to mix and characterize the solutions in each well.
    """
    instructions = [
        instruction
        for instruction in instructions
        if isinstance(instruction, LayeredExperiments)
    ]
    # Generate a list of all solutions that will be used in the experiment
    experiment_solutions = []
    for instruction in instructions:
        for solution in instruction.solutions:
            if solution not in experiment_solutions:
                experiment_solutions.append(solution)

    # Deposit all experiment solutions into well
    for solution_name in experiment_solutions:
        if (
            getattr(instructions, solution_name) > 0 and solution_name[0:4] != "rinse"
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
                        vial
                        for vial in stock_vials
                        if vial.name
                        == solution_name
                        & vial.volume - getattr(instructions, solution_name)
                        > 3000
                    )

                    forward_pipette_v2(
                        volume=getattr(instructions, solution_name),
                        to_vessel=wellplate.wells[instruction.target_well],
                        from_vessel=stock_vial,
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

            waste_vial = next(vial for vial in waste_vials if vial.name == "waste")
            forward_pipette_v2(
                volume=wellplate.get_volume(instruction.target_well),
                to_vessel=waste_vial,
                from_vessel=wellplate.wells[instruction.target_well],
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
                vial
                for vial in stock_vials
                if vial.name == instruction.char_sol_name
                and ((vial.volume - instruction.char_vol) > 3000)
            )

            forward_pipette_v2(
                volume=instruction.char_vol,
                to_vessel=wellplate.wells[instruction.target_well],
                from_vessel=char_vial,
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

            waste_vial = next(vial for vial in waste_vials if vial.name == "waste")

            forward_pipette_v2(
                volume=instruction.char_vol,
                to_vessel=waste_vial,
                from_vessel=wellplate.wells[instruction.target_well],
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
                mill=mill,
            )

            logger.info("Pipette Flushed")
            instruction.status = ExperimentStatus.COMPLETE

    logger.info("End of Experiment: %s", instruction.id)

def correction_factor_tests_protocol(
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Union[Mill, MockMill],
    pump: Union[Pump, MockPump],
    stock_vials: Sequence[StockVial],
    wellplate: Wells2,
    logger: logging.Logger,
):
    """
    Protocol for testing the use of a correction factor when pipetting.
    The correction factor is applied prior to calling forward_pipette_v2 so that the volume
    used to calculate repetitions and selecting the correct vial is the corrected volume.

    Order of operations:
    1. Deposit solutions into well
        for each solution:
            a.  Withdraw air gap
            b.  Withdraw solution
            c.  Read the scale
            d.  Deposit into well
            e.  Blow out
            f.  Read the scale

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
    apply_log_filter(
        instructions.id,
        instructions.target_well,
        str(instructions.project_id) + "." + str(instructions.project_campaign_id),
    )

    try:
        logger.info("Beginning experiment %d", instructions.id)
        results.id = instructions.id
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        exclude_list = ["rinse0", "rinse1", "rinse2"]
        available_solutions = [
            vial.name for vial in stock_vials if vial.name not in exclude_list
        ]

        # although we already checked before running the experiment we want to check again
        # that all requested solutions are found
        experiment_solution_count = len(instructions.solutions)
        matched = 0

        ## Deposit all experiment solutions into well
        for solution_name in instructions.solutions:
            solution_name = str(solution_name).lower()
            solution_volume = instructions.solutions[solution_name]
            if (
                solution_volume > 0
                and solution_name in available_solutions
            ):  # is there is an available solution to deposit
                matched += 1
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    solution_volume,
                    solution_name,
                    instructions.target_well,
                )
                corrected_volume = volume_correction(solution_volume)
                stock_vial = solution_selector(
                    stock_vials, solution_name, corrected_volume
                )
                forward_pipette_v2(
                    volume=corrected_volume,
                    from_vessel=stock_vial,
                    to_vessel=wellplate.wells[instructions.target_well],
                    pump=pump,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.target_well,
        )

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
        exception_type = type(general_exception).__name__
        exception_traceback = sys.exc_info()[2]
        if exception_traceback is not None:
            frame = exception_traceback.tb_frame
            filename = frame.f_code.co_filename
            line_number = exception_traceback.tb_lineno
        else:
            filename = "Unknown"
            line_number = -1
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