"""The standard experiment protocol for eChem experiments."""
# pylint: disable=too-many-lines
# Standard imports
import json
from json import tool
import logging
import sys
from datetime import datetime
from typing import Callable, Sequence, Tuple, Union

# Non-standard imports
import pytz as tz
from mill_control import Mill, MockMill
from pump_control import MockPump, Pump
from vials import StockVial, WasteVial
from wellplate import Wellplate as WellplateV2

from e_panda import (
    NoAvailableSolution,
    OCPFailure,
    apply_log_filter,
    cyclic_volt,
    chrono_amp,
    flush_v2,
    forward_pipette_v2,
    reverse_pipette_v2,
    rinse_v2,
    solution_selector,
    waste_selector,
)
from experiment_class import (
    ExperimentBase,
    ExperimentResult,
    ExperimentStatus,
    LayeredExperiments,
    PEG2P_Test_Instructions,
)
from controller import Toolkit

def run_protocol(
        instructions: ExperimentBase,
        toolkit: Toolkit,
        stock_vials: Sequence[StockVial],
        waste_vials: Sequence[WasteVial],
        protocol_func: Callable
):
    """Wraps the protocol functions with the common beginning and ending sections.

    Args:
        instructions (ExperimentBase): _description_
        toolkit (Toolkit): _description_
        stock_vials (Sequence[StockVial]): _description_
        waste_vials (Sequence[WasteVial]): _description_
        protocol_func (function): _description_
    """
    try:
        # Common beginning section
        apply_log_filter(
            instructions.id,
            instructions.well_id,
            str(instructions.project_id) + "." + str(instructions.project_campaign_id),
        )
        # Lookup the appropriate protocol
        protocol_func = find_protocol_function(instructions.protocol_name)
        # Your specific protocol function
        toolkit.global_logger.info("Beginning experiment %d", instructions.id)
        protocol_func(instructions, toolkit, stock_vials, waste_vials)

        # Common ending section
        instructions.status = ExperimentStatus.COMPLETE

    # Handle exceptions and errors
    except NoAvailableSolution as solution_error:
        toolkit.global_logger.error(solution_error)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        toolkit.global_logger.info(
            "Failed instructions updated for experiment %s", instructions.id
        )
    except OCPFailure as ocp_failure:
        toolkit.global_logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        toolkit.global_logger.info(
            "Failed instructions updated for experiment %s", instructions.id
        )

    except KeyboardInterrupt:
        toolkit.global_logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        toolkit.global_logger.info(
            "Saved interrupted instructions for experiment %s", instructions.id
        )

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
        toolkit.global_logger.error("Exception: %s", general_exception)
        toolkit.global_logger.error("Exception type: %s", exception_type)
        toolkit.global_logger.error("File name: %s", filename)
        toolkit.global_logger.error("Line number: %d", line_number)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))

    finally:
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        toolkit.global_logger.info("End of Experiment: %s", instructions.id)

def find_protocol_function(protocol_name: str) -> Callable:
    """Finds the protocol function based on the protocol name.

    Args:
        protocol_name (str): The name of the protocol.

    Returns:
        Callable: The protocol function.
    """
    import os
    import importlib.util

    protocols_directory = "protocols"

    # Iterate through files in the directory
    for file_name in os.listdir(protocols_directory):
        if file_name.endswith(".py") and file_name != "__init__.py":
            module_name = file_name[:-3]  # Remove the ".py" extension
            module_path = os.path.join(protocols_directory, file_name)

            # Create a module object
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find functions in the module and add them to output
            for func_name in dir(module):
                func = getattr(module, func_name)
                if callable(func) and func_name.endswith("_protocol"):
                    if func_name == protocol_name:
                        return func
            
    raise ValueError(f"Protocol {protocol_name} not found")

def standard_experiment_protocol(
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Mill,
    pump: Pump,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    wellplate: WellplateV2,
    logger: logging.Logger,
) -> Tuple[
    ExperimentBase,
    ExperimentResult,
    Sequence[StockVial],
    Sequence[WasteVial],
    WellplateV2,
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
        instructions.well_id,
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
                    instructions.well_id,
                )
                forward_pipette_v2(
                    volume=getattr(instructions, solution_name),
                    from_vessel=solution_selector(
                        stock_vials, solution_name, getattr(instructions, solution_name)
                    ),
                    to_vessel=wellplate.wells[instructions.well_id],
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
        logger.info("Pipetted solutions into well: %s", instructions.well_id)

        # Mix solutions in well
        if instructions.mix == 1:
            logger.info("Mixing well: %s", instructions.well_id)
            instructions.status = ExperimentStatus.MIXING
            pump.mix(
                mix_location=wellplate.get_coordinates(
                    instructions.well_id
                ),  # fetch x, y, z, depth, and echem height coordinates of well
                mix_repetitions=3,
                mix_volume=instructions.mix_vol,
                mix_rate=instructions.mix_rate,
            )
            logger.info("Mixed well: %s", instructions.well_id)

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
            instructions, results = chrono_amp(instructions, results, mill, wellplate)

            logger.info("Deposition completed for well: %s", instructions.well_id)

            # Withdraw all well volume into waste
            forward_pipette_v2(
                volume=wellplate.read_volume(instructions.well_id),
                from_vessel=wellplate.wells[instructions.well_id],
                to_vessel=waste_selector(
                    waste_vials,
                    "waste",
                    wellplate.read_volume(instructions.well_id),
                ),
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Cleared dep_sol from well: %s", instructions.well_id)

            # Rinse the well 3x
            rinse_v2(
                wellplate=wellplate,
                instructions=instructions,
                pump=pump,
                mill=mill,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
            )

            logger.info("Rinsed well: %s", instructions.well_id)

        # Echem CV - characterization
        if instructions.cv == 1:
            logger.info(
                "Beginning eChem characterization of well: %s", instructions.well_id
            )
            # Deposit characterization solution into well

            logger.info(
                "Infuse %s into well %s...",
                instructions.char_sol_name,
                instructions.well_id,
            )
            forward_pipette_v2(
                volume=instructions.char_vol,
                from_vessel=solution_selector(
                    stock_vials, instructions.char_sol_name, instructions.char_vol
                ),
                to_vessel=wellplate.wells[instructions.well_id],
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Deposited char_sol in well: %s", instructions.well_id)

            instructions, results = cyclic_volt(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete", instructions.well_id)

            forward_pipette_v2(
                volume=instructions.char_vol,
                from_vessel=wellplate.wells[instructions.well_id],
                to_vessel=waste_selector(waste_vials, "waste", instructions.char_vol),
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Well %s cleared", instructions.well_id)

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
    wellplate: WellplateV2,
    logger: logging.Logger,
) -> Tuple[
    PEG2P_Test_Instructions,
    ExperimentResult,
    Sequence[StockVial],
    Sequence[WasteVial],
    WellplateV2,
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
            instructions.well_id,
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
                    instructions.well_id,
                )
                forward_pipette_v2(
                    volume=getattr(instructions, solution_name),
                    from_vessel=solution_selector(
                        stock_vials, solution_name, getattr(instructions, solution_name)
                    ),
                    to_vessel=wellplate.wells[instructions.well_id],
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
        logger.info("Pipetted solutions into well: %s", instructions.well_id)

        # Echem CA - deposition
        if instructions.ca == 1:
            instructions.status = ExperimentStatus.DEPOSITING
            instructions, results = chrono_amp(instructions, results, mill, wellplate)
            logger.info("deposition completed for well: %s", instructions.well_id)

            forward_pipette_v2(
                volume=wellplate.read_volume(instructions.well_id),
                from_vessel=wellplate.wells[instructions.well_id],
                to_vessel=waste_selector(
                    waste_vials,
                    "waste",
                    wellplate.read_volume(instructions.well_id),
                ),
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Cleared dep_sol from well: %s", instructions.well_id)

            # Rinse the well 3x
            rinse_v2(
                wellplate=wellplate,
                instructions=instructions,
                pump=pump,
                mill=mill,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
            )

            logger.info("Rinsed well: %s", instructions.well_id)
        # Echem CV - characterization
        if instructions.cv == 1:
            logger.info(
                "Beginning eChem characterization of well: %s", instructions.well_id
            )
            # Deposit characterization solution into well

            logger.info(
                "Infuse %s into well %s...",
                instructions.char_sol_name,
                instructions.well_id,
            )
            forward_pipette_v2(
                volume=instructions.char_vol,
                from_vessel=solution_selector(
                    stock_vials, instructions.char_sol_name, instructions.char_vol
                ),
                to_vessel=wellplate.wells[instructions.well_id],
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Deposited char_sol in well: %s", instructions.well_id)

            instructions, results = cyclic_volt(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete", instructions.well_id)

            forward_pipette_v2(
                volume=instructions.char_vol,
                from_vessel=wellplate.wells[instructions.well_id],
                to_vessel=waste_selector(waste_vials, "waste", instructions.char_vol),
                pump=pump,
                mill=mill,
                pumping_rate=instructions.pumping_rate,
            )

            logger.info("Well %s cleared", instructions.well_id)

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
    wellplate: WellplateV2,
    logger: logging.Logger,
) -> Tuple[
    ExperimentBase,
    ExperimentResult,
    Sequence[StockVial],
    Sequence[WasteVial],
    WellplateV2,
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
            instructions.well_id,
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
                    instructions.well_id,
                )
                forward_pipette_v2(
                    volume=getattr(instructions, solution_name),
                    from_vessel=solution_selector(
                        stock_vials, solution_name, getattr(instructions, solution_name)
                    ),
                    to_vessel=wellplate.wells[instructions.well_id],
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
        logger.info("Pipetted solutions into well: %s", instructions.well_id)

        # Mix solutions in well
        if instructions.mix == 1:
            logger.info("Mixing well: %s", instructions.well_id)
            instructions.status = ExperimentStatus.MIXING
            pump.mix(
                mix_location=wellplate.get_coordinates(instructions.well_id),
                mix_repetitions=instructions.mix_count,
                mix_volume=instructions.mix_vol,
                mix_rate=instructions.mix_rate,
            )
            logger.info("Mixed well: %s", instructions.well_id)

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
                "Beginning eChem characterization of well: %s", instructions.well_id
            )
            # Deposit characterization solution into well

            instructions, results = cyclic_volt(
                instructions, results, mill, wellplate
            )

            logger.info("Characterization of %s complete", instructions.well_id)
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
    wellplate: WellplateV2,
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
                    instructions.well_id,
                )

                stock_vial = solution_selector(
                    stock_vials, solution_name, solution_volume
                )
                forward_pipette_v2(
                    volume=solution_volume,
                    from_vessel=stock_vial,
                    to_vessel=wellplate.wells[instructions.well_id],
                    pump=pump,
                    mill=mill,
                    pumping_rate=None,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.well_id,
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
    wellplate: WellplateV2,
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
        instructions.well_id,
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
                    instructions.well_id,
                )

                stock_vial = solution_selector(
                    stock_vials, solution_name, solution_volume
                )

                if instructions.id % 2 == 0:
                    logger.info("Forward pipetting")
                    forward_pipette_v2(
                        volume=solution_volume,
                        from_vessel=stock_vial,
                        to_vessel=wellplate.wells[instructions.well_id],
                        pump=pump,
                        mill=mill,
                    )
                else:
                    logger.info("Reverse pipetting")
                    purge_vial = waste_selector(waste_vials, "waste", solution_volume)
                    reverse_pipette_v2(
                        volume=solution_volume,
                        from_vessel=stock_vial,
                        to_vessel=wellplate.wells[instructions.well_id],
                        purge_vessel=purge_vial,
                        pump=pump,
                        mill=mill,
                    )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.well_id,
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
    waste_vials: Sequence[WasteVial],
    wellplate: WellplateV2,
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
        instructions.well_id,
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
                    instructions.well_id,
                )

                stock_vial = solution_selector(
                    stock_vials, solution_name, solution_volume
                )
                forward_pipette_v2(
                    volume=solution_volume,
                    from_vessel=stock_vial,
                    to_vessel=wellplate.wells[instructions.well_id],
                    pump=pump,
                    mill=mill,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.well_id,
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


def viscosity_experiments_protocol(
    instructions: ExperimentBase,
    results: ExperimentResult,
    mill: Union[Mill, MockMill],
    pump: Union[Pump, MockPump],
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    wellplate: WellplateV2,
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
        instructions.well_id,
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
                    instructions.well_id,
                )

                stock_vial = solution_selector(
                    stock_vials, solution_name, solution_volume
                )
                forward_pipette_v2(
                    volume=solution_volume,
                    from_vessel=stock_vial,
                    to_vessel=wellplate.wells[instructions.well_id],
                    pump=pump,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.well_id,
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


calibration_testing_protocol = viscosity_experiments_protocol


def ferrocyanide_repeatability(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Protocol for testing the repeatability of the ferrocyanide solution cyclovoltammetry
    1. Deposit solutions into well
        for each solution:
            a. Withdraw air gap
            b. Withdraw solution
            c. Read the scale
            d. Deposit into well
            e. Blow out
            f. Read the scale
            g. Perform CV
            h. Clear the well

    Args:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        toolkit (Toolkit object): The toolkit object which contains the pump, mill, and wellplate
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials

    Returns:
        None - all arguments are passed by reference or are unchanged

    """
    available_solutions = [
        vial.name
        for vial in stock_vials
        if vial.name not in ["rinse0", "rinse1", "rinse2"]
    ]

    # although we already checked before running the experiment we want to check again
    # that all requested solutions are found
    matched = 0

    ## Deposit all experiment solutions into well
    for solution_name in instructions.solutions:
        solution_name = str(solution_name).lower()
        if (
            instructions.solutions[solution_name] > 0
            and solution_name in available_solutions
        ):  # if there is a solution to deposit
            matched += 1
            toolkit.global_logger.info(
                "Pipetting %s ul of %s into %s...",
                instructions.solutions[solution_name],
                solution_name,
                instructions.well_id,
            )

            forward_pipette_v2(
                volume=instructions.solutions[solution_name],
                from_vessel=solution_selector(
                    stock_vials,
                    solution_name,
                    instructions.solutions[solution_name],
                ),
                to_vessel=toolkit.wellplate.wells[instructions.well_id],
                pump=toolkit.pump,
                mill=toolkit.mill,
                pumping_rate=instructions.pumping_rate,
            )

    if matched != len(instructions.solutions):
        raise NoAvailableSolution("One or more solutions are not available")

    toolkit.global_logger.info(
        "Pipetted %s into well: %s",
        json.dumps(instructions.solutions),
        instructions.well_id,
    )
    # Initial fluid handeling is done now we can perform the CV
    cyclic_volt(instructions, instructions.results, toolkit.mill, toolkit.wellplate)
    # Clear the well
    forward_pipette_v2(
        volume=toolkit.wellplate.wells[instructions.well_id].volume,
        from_vessel=toolkit.wellplate.wells[instructions.well_id],
        to_vessel=waste_selector(
            waste_vials,
            "waste",
            toolkit.wellplate.wells[instructions.well_id].volume,
        ),
        pump=toolkit.pump,
        mill=toolkit.mill,
    )
    instructions.status = ExperimentStatus.COMPLETE


def contamination_assessment(
    instructions: ExperimentBase,
    toolkit: Toolkit,
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
):
    """
    Protocol for testing the conamination coming from the pipette tip
    1. Deposit solutions into well
        for each solution:
            a. Pipette 120ul of solution into waste
            b. Flush the pipette tip x3 with electrolyte rinse
            c. Pipette 120ul of solution into well
            d. Perform CV
            e. Rinse the electrode with electrode rinse

    Args:
        instructions (Experiment object): The experiment instructions
        results (ExperimentResult object): The experiment results
        toolkit (Toolkit object): The toolkit object which contains the pump, mill, and wellplate
        stock_vials (list): The list of stock vials
        waste_vials (list): The list of waste vials

    Returns:
        None - all arguments are passed by reference or are unchanged

    """
    apply_log_filter(
        instructions.id,
        instructions.well_id,
        str(instructions.project_id) + "." + str(instructions.project_campaign_id),
    )

    try:
        toolkit.global_logger.info("Beginning experiment %d", instructions.id)
        # Fetch list of solution names from stock_vials
        # list of vial names to exclude
        available_solutions = [
            vial.name
            for vial in stock_vials
            if vial.name not in ["rinse0", "rinse1", "rinse2"]
        ]

        # although we already checked before running the experiment we want to check again
        # that all requested solutions are found
        matched = 0

        ## Deposit all experiment solutions into well
        for solution_name in instructions.solutions:
            solution_name = str(solution_name).lower()
            if (
                instructions.solutions[solution_name] > 0
                and solution_name in available_solutions
            ):  # if there is a solution to deposit
                matched += 1
                toolkit.global_logger.info(
                    "Pipetting %s ul of %s into %s...",
                    instructions.solutions[solution_name],
                    solution_name,
                    instructions.well_id,
                )

                # Pipette 120ul of solution into waste
                forward_pipette_v2(
                    volume=instructions.solutions[solution_name],
                    from_vessel=solution_selector(
                        stock_vials,
                        solution_name,
                        instructions.solutions[solution_name],
                    ),
                    to_vessel=solution_selector(
                        stock_vials, "waste", instructions.solutions[solution_name]
                    ),
                    pump=toolkit.pump,
                    mill=toolkit.mill,
                    pumping_rate=instructions.pumping_rate,
                )

                # Flush the pipette tip x3 with electrolyte rinse
                for _ in range(3):
                    forward_pipette_v2(
                        volume=instructions.solutions[solution_name],
                        from_vessel=solution_selector(
                            stock_vials, "rinse0", instructions.solutions[solution_name]
                        ),
                        to_vessel=solution_selector(
                            stock_vials, "waste", instructions.solutions[solution_name]
                        ),
                        pump=toolkit.pump,
                        mill=toolkit.mill,
                        pumping_rate=instructions.pumping_rate,
                    )

                # Pipette 120ul of solution into well
                forward_pipette_v2(
                    volume=instructions.solutions[solution_name],
                    from_vessel=solution_selector(
                        stock_vials,
                        solution_name,
                        instructions.solutions[solution_name],
                    ),
                    to_vessel=toolkit.wellplate.wells[instructions.well_id],
                    pump=toolkit.pump,
                    mill=toolkit.mill,
                    pumping_rate=instructions.pumping_rate,
                )

        if matched != len(instructions.solutions):
            raise NoAvailableSolution("One or more solutions are not available")

        toolkit.global_logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.well_id,
        )

        # Perform CV
        cyclic_volt(instructions,instructions.results, toolkit.mill, toolkit.wellplate)

        # Rinse the electrode with electrode rinse
        toolkit.mill.rinse_electrode()

        # End of experiment
        instructions.status = ExperimentStatus.COMPLETE

    except OCPFailure as ocp_failure:
        toolkit.global_logger.error(ocp_failure)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        toolkit.global_logger.info(
            "Failed instructions updated for experiment %s", instructions.id
        )

    except KeyboardInterrupt:
        toolkit.global_logger.warning("Keyboard Interrupt")
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        toolkit.global_logger.info(
            "Saved interrupted instructions for experiment %s", instructions.id
        )

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
        toolkit.global_logger.error("Exception: %s", general_exception)
        toolkit.global_logger.error("Exception type: %s", exception_type)
        toolkit.global_logger.error("File name: %s", filename)
        toolkit.global_logger.error("Line number: %d", line_number)
        instructions.status = ExperimentStatus.ERROR
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))

    finally:
        instructions.status_date = datetime.now(tz.timezone("US/Eastern"))
        toolkit.global_logger.info("End of Experiment: %s", instructions.id)


def layered_solution_protocol(
    instructions: list[LayeredExperiments],
    mill: Union[Mill, MockMill],
    pump: Union[Pump, MockPump],
    stock_vials: Sequence[StockVial],
    waste_vials: Sequence[WasteVial],
    wellplate: WellplateV2,
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
                        instruction.well_id,
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
                        to_vessel=wellplate.wells[instruction.well_id],
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
            logger.info("Mixing well: %s", instruction.well_id)
            instruction.status = ExperimentStatus.MIXING
            pump.mix(
                mix_location=wellplate.get_coordinates(instruction.well_id),
                mix_repetitions=instruction.mix_count,
                mix_volume=instruction.mix_volume,
                mix_rate=instruction.pumping_rate,
            )
            logger.info("Mixed well: %s", instruction.well_id)

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
            instruction, results = chrono_amp(instruction, results, mill, wellplate)
            instruction.results = results
            logger.info("deposition completed for well: %s", instruction.well_id)

            waste_vial = next(vial for vial in waste_vials if vial.name == "waste")
            forward_pipette_v2(
                volume=wellplate.get_volume(instruction.well_id),
                to_vessel=waste_vial,
                from_vessel=wellplate.wells[instruction.well_id],
                pumping_rate=None,
                pump=pump,
                mill=mill,
            )

            logger.info("Cleared dep_sol from well: %s", instruction.well_id)

            # Rinse the well 3x
            rinse_v2(
                wellplate=wellplate,
                instructions=instruction,
                pump=pump,
                mill=mill,
                waste_vials=waste_vials,
                stock_vials=stock_vials,
            )

            logger.info("Rinsed well: %s", instruction.well_id)

        # Echem CV - characterization
        if instruction.cv == 1:
            logger.info(
                "Beginning eChem characterization of well: %s", instruction.well_id
            )
            # Deposit characterization solution into well
            instruction.status = ExperimentStatus.CHARACTERIZING
            logger.info(
                "Infuse %s into well %s...",
                instruction.char_sol_name,
                instruction.well_id,
            )
            char_vial = next(
                vial
                for vial in stock_vials
                if vial.name == instruction.char_sol_name
                and ((vial.volume - instruction.char_vol) > 3000)
            )

            forward_pipette_v2(
                volume=instruction.char_vol,
                to_vessel=wellplate.wells[instruction.well_id],
                from_vessel=char_vial,
                pumping_rate=None,
                pump=pump,
                mill=mill,
            )

            logger.info("Deposited char_sol in well: %s", instruction.well_id)

            instruction, results = cyclic_volt(
                instruction, results, mill, wellplate
            )
            instruction.results = results
            logger.info("Characterization of %s complete", instruction.well_id)

            waste_vial = next(vial for vial in waste_vials if vial.name == "waste")

            forward_pipette_v2(
                volume=instruction.char_vol,
                to_vessel=waste_vial,
                from_vessel=wellplate.wells[instruction.well_id],
                pumping_rate=None,
                pump=pump,
                mill=mill,
            )

            logger.info("Well %s cleared", instruction.well_id)

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
    wellplate: WellplateV2,
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
        instructions.well_id,
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
            ):  # is there is an available solution to deposit
                matched += 1
                logger.info(
                    "Pipetting %s ul of %s into %s...",
                    solution_volume,
                    solution_name,
                    instructions.well_id,
                )
                corrected_volume = solution_volume  # volume_correction(solution_volume)
                stock_vial = solution_selector(
                    stock_vials, solution_name, corrected_volume
                )
                forward_pipette_v2(
                    volume=corrected_volume,
                    from_vessel=stock_vial,
                    to_vessel=wellplate.wells[instructions.well_id],
                    pump=pump,
                    mill=mill,
                    pumping_rate=instructions.pumping_rate,
                )

        if matched != experiment_solution_count:
            raise NoAvailableSolution("One or more solutions are not available")

        logger.info(
            "Pipetted %s into well: %s",
            json.dumps(instructions.solutions),
            instructions.well_id,
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


protocol_dict = {
    "standard": standard_experiment_protocol,
    "mixing_test": mixing_test_protocol,
    "pipette_accuracy": pipette_accuracy_protocol_v2,
    "forward_vs_reverse": forward_vs_reverse_pipetting,
    "vial_depth_tracking": vial_depth_tracking_protocol,
    "viscosity_experiments": viscosity_experiments_protocol,
    "calibration_testing": calibration_testing_protocol,
    "layered": layered_solution_protocol,
    "correction_factor_tests": correction_factor_tests_protocol,
}
