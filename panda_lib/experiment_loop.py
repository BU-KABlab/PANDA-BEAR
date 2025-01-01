"""
The controller is responsible for the following:
    - Running the scheduler and retriving the next experiment to run
    - checking the state of the system (vials, wells, etc.)
    - Running the experiment (passing the experiment, system state, and instruments)
    - Recieve data from the experiment, and store it in the database
    - Update system state (vials, wells, etc.)
    - Running the analyzer

Additionally controller should be able to:
    - Reset the well statuses
    - Update the vial statuses
"""

# pylint: disable=line-too-long, broad-exception-caught
import importlib
import logging
import multiprocessing
import sys
import time
from pathlib import Path
from typing import Optional, Sequence, Tuple

import PySpin
from slack_sdk import errors as slack_errors
from sqlalchemy.orm import sessionmaker

from panda_lib import scheduler

# from panda_experiment_analyzers import pedot as pedot_analyzer
from panda_lib.gamry_potentiostat import gamry_control

# from .movement import Mill, MockMill
from panda_lib.grlb_mill_wrapper import MockPandaMill as MockMill
from panda_lib.grlb_mill_wrapper import PandaMill as Mill
from panda_lib.pawduino import ArduinoLink, MockArduinoLink
from panda_lib.sql_tools import db_setup, panda_models, sql_queue

from . import actions
from .config.config_tools import read_config, read_testing_config
from .errors import (
    CAFailure,
    CVFailure,
    DepositionFailure,
    ExperimentError,
    ExperimentNotFoundError,
    InstrumentConnectionError,
    InsufficientVolumeError,
    MismatchWellplateTypeError,
    OCPFailure,
    ProtocolNotFoundError,
    ShutDownCommand,
    WellImportError,
)
from .experiment_class import (
    EchemExperimentBase,
    ExperimentBase,
    ExperimentResult,
    ExperimentResultsRecord,
    ExperimentStatus,
    select_complete_experiment_information,
    select_experiment_status,
    select_specific_result,
)
from .instrument_toolkit import Hardware, Labware, Toolkit
from .log_tools import apply_log_filter, setup_default_logger, timing_wrapper
from .slack_tools.SlackBot import SlackBot
from .sql_tools import sql_protocol_utilities, sql_system_state, sql_wellplate
from .sql_tools.db_setup import SessionLocal
from .syringepump import MockPump, SyringePump
from .utilities import SystemState
from .vials import StockVial, Vial, WasteVial, read_vials
from .wellplate import Well, Wellplate

config = read_config()
# set up slack globally so that it can be used in the main function and others
logger = setup_default_logger(log_name="panda")
TESTING = read_testing_config()


def run_slack_bot(testing_mode: bool = TESTING):
    """
    Run the slack bot
    Args:
    ----
        testing_mode (bool, optional): Whether to run the slack bot in testing mode. Defaults to TESTING.
    """
    slack_monitor = SlackBot(test=testing_mode)
    slack_monitor.run()


def experiment_loop_worker(
    use_mock_instruments: bool = TESTING,
    one_off: bool = False,
    al_campaign_length: int = None,
    random_experiment_selection: bool = False,
    specific_experiment_id: int = None,
    status_queue: multiprocessing.Queue = multiprocessing.Queue(),
    process_id: int = None,
    command_queue: multiprocessing.Queue = multiprocessing.Queue(),
):
    """
    Main function

    Args:
    ----
        use_mock_instruments (bool, optional): Whether to use mock instruments. Defaults to False.
        one_off (bool, optional): Whether to run one experiment and then exit. Defaults to False.
    """

    controller_slack = SlackBot(test=use_mock_instruments)
    # slack_thread = threading.Thread(target=run_slack_bot, args=(use_mock_instruments,))
    # if config.getboolean("OPTIONS", "testing") or not config.getboolean(
    #     "OPTIONS", "use_obs"
    # ):
    #     obs = MockOBSController()
    # else:
    #     obs = OBSController()
    ## Reset the logger to log to the PANDA_SDL.log file and format
    apply_log_filter(logger=logger)
    controller_slack.send_message("alert", "PANDA_SDL is starting up")
    toolkit = None
    current_experiment = None

    # Everything runs in a try block so that we can close out of the serial connections if something goes wrong
    try:
        # obs.place_text_on_screen("PANDA_SDL is starting up")
        # obs.start_recording()
        current_experiment = None
        # Connect to equipment
        toolkit, all_found = connect_to_instruments(use_mock_instruments)
        if not all_found:
            raise InstrumentConnectionError("Not all instruments connected")

        controller_slack.send_message("alert", "PANDA_SDL has connected to equipment")
        # obs.place_text_on_screen("PANDA_SDL has connected to equipment")
        status_queue.put((process_id, "connected to equipment"))

        ## Establish state of system - we do this each time because each experiment changes the system state
        stock_vials, waste_vials, toolkit.wellplate = _establish_system_state()

        ## Check that the pipette is empty, if not dispose of full volume into waste
        if toolkit.pump.pipette.volume > 0:
            # obs.place_text_on_screen("Pipette is not empty, purging into waste")
            status_queue.put((process_id, "Purging pipette into waste"))
            actions.purge_pipette(
                mill=toolkit.mill,
                pump=toolkit.pump,
            )

        # experiemnt loop
        while True:
            ## Begin slack monitoring
            # slack_thread.start()

            ## Reset the logger to log to the PANDA_SDL.log file and format
            # obs.place_text_on_screen("")
            apply_log_filter(logger=logger)
            sql_system_state.set_system_status(SystemState.BUSY)
            ## Establish state of system - we do this each time because each experiment changes the system state
            stock_vials, _, toolkit.wellplate = _establish_system_state()

            while current_experiment is None:
                ## Ask the scheduler for the next experiment
                current_experiment, _ = scheduler.read_next_experiment_from_queue(
                    random_pick=random_experiment_selection,
                    experiment_id=specific_experiment_id,
                )
                specific_experiment_id = None  # reset the specific experiment id so that we don't keep running the same experiment
                if current_experiment is not None:
                    controller_slack.send_message(
                        "alert",
                        f"New experiment {current_experiment.experiment_id} found",
                    )

                    break  # break out of the while new experiment is None loop

                logger.info(
                    "No new experiments to run...waiting a minute for new experiments"
                )
                controller_slack.send_message(
                    "alert",
                    "No new experiments to run...waiting a minute for new experiments",
                )
                status_queue.put(
                    (
                        process_id,
                        "idle",
                    )
                )

                sql_system_state.set_system_status(
                    SystemState.PAUSE, "Waiting for new experiments"
                )
                status = _monitor_system_status(
                    controller_slack, status_queue, process_id
                )
                if status == SystemState.STOP:
                    break  # break out of the main while True loop

            ## Validate the experiment object
            # Does the experiment object exist and is it an instance of ExperimentBase
            if not isinstance(current_experiment, ExperimentBase):
                logger.error("The experiment object is invalid")
                controller_slack.send_message(
                    "alert",
                    "An invalid experiment object was passed to the controller",
                )
                break  # break out of the main while True loop

            # Does the experiment object's well_type and well_id exist as new or queued in the wellplate
            well: Well = toolkit.wellplate.wells[current_experiment.well_id]
            if (
                well.plate_id != toolkit.wellplate.plate_id
                or current_experiment.well_type_number != toolkit.wellplate.type_number
            ):
                logger.error(
                    "The experiment object's well type and wellplate id do not match the current wellplate"
                )
                controller_slack.send_message(
                    "alert",
                    "The experiment object's well type and well id do not exist in the wellplate",
                )
                break  # break out of the main while True loop

            logger.info(
                "Experiment %d selected and validated", current_experiment.experiment_id
            )
            sql_system_state.set_system_status(SystemState.BUSY)
            ## Initialize a results object
            current_experiment.results = ExperimentResult(
                experiment_id=current_experiment.experiment_id,
                well_id=current_experiment.well_id,
            )
            ## Check that there is enough volume in the stock vials to run the experiment
            sufficient_stock, _ = _check_stock_vials(
                current_experiment.solutions, stock_vials
            )
            if not sufficient_stock:
                error_message = f"Experiment {current_experiment.experiment_id} cannot be run because there is not enough volume in the stock vials"
                controller_slack.send_message(
                    "alert",
                    error_message,
                )
                logger.warning(error_message)

                current_experiment.priority = 999
                scheduler.update_experiment_info(
                    current_experiment, "priority"
                )  # update the experiment file with the new status and priority
                scheduler.update_experiment_queue_priority(
                    current_experiment.experiment_id, current_experiment.priority
                )
                controller_slack.send_message(
                    "alert",
                    f"Experiment {current_experiment.experiment_id} has been moved to the back of the queue. Checking for other experiments",
                )
                # continue  # continue to the next experiment
                break  # break out of the main while True loop
            # Announce the experiment
            pre_experiment_status_msg = (
                f"Running experiment {current_experiment.experiment_id}"
            )
            logger.info(pre_experiment_status_msg)
            status_queue.put((process_id, pre_experiment_status_msg))
            controller_slack.send_message("alert", pre_experiment_status_msg)

            ## Update the experiment status to running
            current_experiment.plate_id = toolkit.wellplate.plate_id
            current_experiment.well = toolkit.wellplate.wells[
                current_experiment.well_id
            ]
            current_experiment.well.plate_id = toolkit.wellplate.plate_id
            current_experiment.well.experiment_id = current_experiment.experiment_id
            current_experiment.well.project_id = current_experiment.project_id
            current_experiment.set_status_and_save(ExperimentStatus.RUNNING)

            ## Run the experiment
            apply_log_filter(
                logger,
                current_experiment.experiment_id,
                current_experiment.well_id,
                str(current_experiment.project_id)
                + "."
                + str(current_experiment.project_campaign_id),
                test=use_mock_instruments,
            )

            logger.info("Beginning experiment %d", current_experiment.experiment_id)

            # Get the protocol entry using either the name or id
            protocol_entry: sql_protocol_utilities.ProtocolEntry = (
                sql_protocol_utilities.select_protocol(current_experiment.protocol_id)
            )

            # Convert the file path to a module name
            module_name = Path(
                (config.get("GENERAL", "protocols_dir") + "." + protocol_entry.filepath)
                .replace("/", ".")
                .rstrip(".py")
            )

            # Import the module
            protocol_module = importlib.import_module(module_name.name)

            # Get the main function from the module
            try:
                protocol_function = getattr(protocol_module, "run")
            except AttributeError:
                try:
                    protocol_function = getattr(protocol_module, "main")
                except AttributeError:
                    raise ProtocolNotFoundError(
                        f"Protocol {protocol_entry.name} does not have a 'run' or 'main' function"
                    )

            try:
                protocol_function(
                    experiment=current_experiment,
                    toolkit=toolkit,
                )
            except Exception as error:
                logger.error(error)
                current_experiment.set_status_and_save(ExperimentStatus.ERROR)
                raise error

            # Analysis function call if experiment includes one
            # if not TESTING and current_experiment.analyzer is not None:
            #     current_experiment.analyzer(current_experiment)
            current_experiment.set_status_and_save(ExperimentStatus.SAVING)
            scheduler.save_results(current_experiment)
            current_experiment.set_status_and_save(ExperimentStatus.COMPLETE)
            # Post to the alerts channel
            controller_slack.send_message(
                "alert",
                f"Experiment {current_experiment.experiment_id} has completed",
            )
            # Share any results images with the slack data channel
            share_to_slack(current_experiment)

            ## Reset the logger to log to the PANDA_SDL.log file and format after the experiment is complete
            apply_log_filter(logger=logger)

            ## With returned experiment and results, update the experiment status and post the final status
            post_experiment_status_msg = f"Experiment {current_experiment.experiment_id} ended with status {current_experiment.status.value}"
            logger.info(post_experiment_status_msg)
            status_queue.put((process_id, post_experiment_status_msg))
            # slack.send_slack_message("alert", post_experiment_status_msg)

            ## If the status is complete mark for analysis
            if current_experiment.status == ExperimentStatus.COMPLETE:
                with db_setup.SessionLocal() as connection:
                    connection.query(panda_models.Experiments).filter(
                        panda_models.Experiments.experiment_id
                        == current_experiment.experiment_id
                    ).update({"needs_analysis": True})
                    connection.commit()

            ## Clean up
            current_experiment = None  # reset new_experiment to None so that we can check the queue again
            ## Update the system state with new vial and wellplate information

            if toolkit.pump.pipette.volume > 0 and toolkit.pump.pipette.volume_ml < 1:
                # assume unreal volume, not actually solution, set to 0
                toolkit.pump.pipette.reset_contents()
            if one_off:
                break  # break out of the while True loop

            if SystemState.SHUTDOWN in sql_system_state.select_system_status(2):
                raise ShutDownCommand

            # check for paused status and hold until status changes to resume
            status = _monitor_system_status(controller_slack, status_queue, process_id)
            if status == SystemState.STOP:
                break  # break out of the while True loop and the try block to go to finally
    except (
        OCPFailure,
        DepositionFailure,
        CVFailure,
        CAFailure,
    ) as error:
        if current_experiment is not None:
            current_experiment.set_status_and_save(ExperimentStatus.ERROR)
        sql_system_state.set_system_status(SystemState.ERROR)
        # scheduler.change_well_status(
        #     toolkit.wellplate.wells[new_experiment.well_id], new_experiment
        # )
        logger.error(error)
        controller_slack.echem_error_procedure()

        raise error  # raise error to go to finally. We do not want the program to continue if there is an electochemistry error as it usually indicates a hardware or solutions issue

    except ProtocolNotFoundError as error:
        if current_experiment is not None:
            current_experiment.set_status_and_save(ExperimentStatus.ERROR)
        sql_system_state.set_system_status(SystemState.ERROR)
        logger.error(error)
        controller_slack.send_message(
            "alert", f"PANDA_SDL encountered an error: {error}"
        )
        raise error

    except ShutDownCommand:
        if current_experiment is not None:
            current_experiment.set_status_and_save(ExperimentStatus.ERROR)
        sql_system_state.set_system_status(SystemState.OFF)
        logger.info("User commanded shutting down of PANDA_SDL")

    except KeyboardInterrupt as exc:
        if current_experiment is not None:
            current_experiment.set_status_and_save(ExperimentStatus.ERROR)
        sql_system_state.set_system_status(SystemState.ERROR)
        logger.info("Keyboard interrupt detected")
        controller_slack.send_message("alert", "PANDA_SDL was interrupted by the user")
        raise KeyboardInterrupt from exc  # raise error to go to finally. This was triggered by the user to indicate they want to stop the program

    except Exception as error:
        if current_experiment is not None:
            current_experiment.set_status_and_save(ExperimentStatus.ERROR)
        sql_system_state.set_system_status(SystemState.ERROR)
        logger.error(error)
        logger.exception(error)
        controller_slack.send_message(
            "alert", f"PANDA_SDL encountered an error: {error}"
        )
        raise error  # raise error to go to finally. If we don't know what caused an error we don't want to continue

    finally:
        if current_experiment is not None:
            scheduler.save_results(current_experiment)
            share_to_slack(current_experiment)

        toolkit.mill.rest_electrode()
        if toolkit is not None:
            disconnect_from_instruments(toolkit)
        # obs.place_text_on_screen("")
        # obs.stop_recording()
        sql_system_state.set_system_status(SystemState.IDLE)

        controller_slack.send_message("alert", "PANDA_SDL is shutting down...goodbye")
        status_queue.put((process_id, "idle"))


def sila_experiment_loop_worker(
    specific_experiment_id: Optional[int] = None,
    specific_well_id: Optional[str] = None,
    process_id: Optional[int] = None,
    status_queue: multiprocessing.Queue = None,
    command_queue: multiprocessing.Queue = None,
) -> None:
    """
    Main worker function to execute SILA experiments.
    """

    toolkit, _ = connect_to_instruments()
    hardware = Hardware(
        pump=toolkit.pump,
        mill=toolkit.mill,
        flir_camera=toolkit.flir_camera,
        arduino=toolkit.arduino,
        global_logger=toolkit.global_logger,
    )
    labware = Labware(
        wellplate=Wellplate(),
        global_logger=toolkit.global_logger,
    )

    def set_worker_state(state: SystemState):
        """Set the worker state"""
        sql_system_state.set_system_status(state)
        status_queue.put((process_id, f"{specific_experiment_id}: {state.value}"))

    set_worker_state(SystemState.RUNNING)
    exp_logger = (
        hardware.global_logger
        if hardware.global_logger is not None
        else setup_default_logger(log_name="panda")
    )
    ## Reset the logger to log to the PANDA_SDL.log file and format
    apply_log_filter(exp_logger)

    try:
        exp_obj = None

        ## Check that the pipette is empty, if not dispose of full volume into waste
        if hardware.pump.pipette.volume > 0:
            exp_logger.info("Pipette not empty, purging into waste")
            set_worker_state(SystemState.PIPETTE_PURGE)
            actions.purge_pipette(hardware.mill, hardware.pump)
        # This also validates the experiment parameters since its a pydantic object
        exp_obj: EchemExperimentBase = _initialize_experiment(
            specific_experiment_id, hardware, labware, exp_logger, specific_well_id
        )

        ## Check that there is enough volume in the stock vials to run the experiment
        _validate_the_stock_solutions(exp_obj, labware)
        # Announce the experiment
        exp_logger.info("Running experiment %d", exp_obj.experiment_id)
        exp_obj.set_status_and_save(ExperimentStatus.RUNNING)

        ## Run the experiment
        apply_log_filter(
            exp_logger,
            exp_obj.experiment_id,
            exp_obj.well_id,
            str(exp_obj.project_id) + "." + str(exp_obj.project_campaign_id),
        )

        exp_logger.info("Beginning experiment %d", exp_obj.experiment_id)
        protocol_function = _fetch_protocol_function(exp_obj.protocol_id)

        try:
            protocol_function(
                experiment=exp_obj,
                hardware=hardware,
                labware=labware,
            )
        except (
            OCPFailure,
            DepositionFailure,
            CVFailure,
            CAFailure,
            ExperimentError,
        ) as error:
            if exp_obj:
                exp_obj.set_status_and_save(ExperimentStatus.ERROR)
            exp_logger.exception(error)
            raise error
        except Exception as error:
            exp_logger.exception(error)
            exp_obj.set_status_and_save(ExperimentStatus.ERROR)
            raise error

        finally:
            if exp_obj is not None:
                status = select_experiment_status(exp_obj.experiment_id)
                scheduler.save_results(exp_obj)
                if status == ExperimentStatus.COMPLETE:
                    with db_setup.SessionLocal() as connection:
                        connection.query(panda_models.Experiments).filter(
                            panda_models.Experiments.experiment_id
                            == exp_obj.experiment_id
                        ).update({"needs_analysis": True})
                        connection.commit()

    except (ProtocolNotFoundError, KeyboardInterrupt, Exception) as error:
        set_worker_state(SystemState.ERROR)
        if exp_obj is not None:
            exp_obj.set_status_and_save(ExperimentStatus.ERROR)
        exp_logger.exception(error)
        raise error

    finally:
        # Lets handle the experiment first
        if exp_obj is not None:
            post_experiment_status_msg = f"Experiment {exp_obj.experiment_id} ended with status {exp_obj.status.value}"
            logger.info(post_experiment_status_msg)
            scheduler.save_results(exp_obj)
            share_to_slack(exp_obj)

        ## Clean up the instruments
        if hardware.pump.pipette.volume > 0 and hardware.pump.pipette.volume_ml < 1:
            # assume unreal volume, not actually solution, set to 0
            actions.purge_pipette(
                mill=hardware.mill,
                pump=hardware.pump,
            )

        hardware.mill.rest_electrode()
        # We are not disconnecting from instruments with this function, that will
        # be handled by a higher level function
        apply_log_filter(exp_logger)
        set_worker_state(SystemState.IDLE)


def _attach_well_to_experiment(exp_obj: ExperimentBase, trgt_well: Well):
    trgt_well.experiment_id = exp_obj.experiment_id
    trgt_well.project_id = exp_obj.project_id
    exp_obj.well = trgt_well
    exp_obj.plate_id = trgt_well.plate_id


def _initialize_experiment(
    exp_id: int,
    hardware: Hardware,
    labware: Labware,
    exp_logger: logging.Logger,
    well_id: Optional[str] = None,
) -> EchemExperimentBase:
    """Initialize and validate the experiment."""
    exp_obj = select_complete_experiment_information(exp_id)

    # TODO: this is silly but we need to reference the queue to get the well_id because the experiment object isn't updated with the correct target well_id
    _, _, _, _, well_id = sql_queue.get_next_experiment_from_queue(
        specific_experiment_id=exp_id
    )
    # TODO: Replace with checking for available well, unless given one.
    exp_obj.well_id = well_id

    if not exp_obj:
        raise ExperimentNotFoundError(f"Experiment {exp_id} not found in the database.")

    well = labware.wellplate.wells[exp_obj.well_id]
    if (
        well.plate_id != labware.wellplate.id
        or exp_obj.well_type_number != labware.wellplate.type_id
    ):
        raise MismatchWellplateTypeError("Mismatched wellplate type or ID.")

    exp_logger.info("Experiment %d selected and validated", exp_obj.experiment_id)
    exp_obj.results = ExperimentResult(
        experiment_id=exp_obj.experiment_id,
        well_id=exp_obj.well_id,
    )

    _attach_well_to_experiment(exp_obj, well)

    return exp_obj


def _validate_the_stock_solutions(exp: EchemExperimentBase, labware: Labware):
    sufficient_stock, check_table = _check_stock_vials(
        exp.solutions, labware.stock_vials
    )
    if not sufficient_stock:
        issues = []
        if check_table["insufficient"]:
            issues.append(f"insufficient volume of: {check_table['insufficient']}")
        if check_table["missing"]:
            issues.append(f"missing vials: {check_table['missing']}")
        if issues == []:
            issues.append("unknown reason")
        error_message = f"Experiment {exp.experiment_id} cannot be run because {', and '.join(issues)}"
        raise InsufficientVolumeError(error_message)


def _fetch_protocol_function(protocol_id: int):
    protocol_entry: sql_protocol_utilities.ProtocolEntry = (
        sql_protocol_utilities.select_protocol(protocol_id)
    )

    # Convert the file path to a module name
    module_name = Path(
        (config.get("GENERAL", "protocols_dir") + "." + protocol_entry.filepath)
        .replace("/", ".")
        .rstrip(".py")
    )

    # Import the module
    protocol_module = importlib.import_module(module_name.name)

    # Get the main function from the module
    try:
        protocol_function = getattr(protocol_module, "run")
    except AttributeError:
        try:
            protocol_function = getattr(protocol_module, "main")
        except AttributeError:
            raise ProtocolNotFoundError(
                f"Protocol {protocol_entry.name} does not have a 'run' or 'main' function"
            )
    return protocol_function


@timing_wrapper
def _establish_system_state(
    session_maker: sessionmaker = SessionLocal,
) -> tuple[Sequence[StockVial], Sequence[WasteVial], Wellplate]:
    """
    Establish state of system
    Returns:
        stock_vials (list[Vial]): list of stock vials
        waste_vials (list[Vial]): list of waste vials
        wellplate (wellplate_module.Wells): wellplate object
    """
    slack = SlackBot()
    stock_vials, waste_vials = read_vials(session=session_maker)
    # stock_vials = get_current_vials("stock")
    # waste_vials = get_current_vials("waste")
    stock_vials_only = [vial for vial in stock_vials if isinstance(vial, StockVial)]
    waste_vials_only = [vial for vial in waste_vials if isinstance(vial, WasteVial)]
    wellplate = Wellplate()
    logger.info("System state reestablished")

    ## read through the stock vials and log their name, contents, and volume
    # for vial in stock_vials_only:
    #     logger.debug(
    #         "Stock vial %s contains %s with volume %d",
    #         vial.name,
    #         vial.contents,
    #         vial.volume,
    #     )

    ## if any stock vials are empty, send a slack message prompting the user to refill them and confirm if program should continue
    empty_stock_vials = [vial for vial in stock_vials_only if vial.volume < 1000]
    if len(empty_stock_vials) > 0:
        slack.send_message(
            "alert",
            "The following stock vials are low or empty: "
            + ", ".join([vial.name for vial in empty_stock_vials]),
        )
        slack.send_message(
            "alert",
            "Please refill the stock vials and restart the program from the main menu",
        )
        # options = input(
        #     "Confirm that the program should continue by pressing enter or q to exit: "
        # )
        # if options.lower() == "q":
        slack.send_message("alert", "PANDA_SDL is shutting down")
        raise ShutDownCommand
        # slack.send_message("alert", "The program is continuing")

    ## read through the waste vials and log their name, contents, and volume
    # for vial in waste_vials_only:
    #     logger.debug(
    #         "Waste vial %s contains %s with volume %d",
    #         vial.name,
    #         vial.contents,
    #         vial.volume,
    #     )

    ## if any waste vials are full, send a slack message prompting the user to empty them and confirm if program should continue
    full_waste_vials = [vial for vial in waste_vials_only if vial.volume > 19000]
    if len(full_waste_vials) == len(waste_vials_only):
        slack.send_message(
            "alert",
            "The following waste vials are full: "
            + ", ".join([vial.name for vial in full_waste_vials]),
        )
        slack.send_message(
            "alert",
            "Please empty the waste vials and confirm in the terminal that the program should continue",
        )
        options = input(
            "Confirm that the program should continue by pressing enter or q to exit: "
        )
        if options.lower() == "q":
            slack.send_message("alert", "PANDA_SDL is shutting down")
            raise ShutDownCommand

        slack.send_message("alert", "The program is continuing")

    ## read the wellplate json and log the status of each well in a grid
    number_of_clear_wells = 0
    number_of_wells = 0

    # Query the number of clear wells in well_status
    number_of_clear_wells = sql_wellplate.get_number_of_clear_wells()
    number_of_wells = sql_wellplate.get_number_of_wells()
    ## check that wellplate has the appropriate number of wells
    if number_of_wells != len(wellplate.wells):
        logger.error(
            "Wellplates status file does not have the correct number of wells. File may be corrupted"
        )
        raise WellImportError
    logger.info("There are %d clear wells", number_of_clear_wells)
    if number_of_clear_wells == 0:
        slack.send_message("alert", "There are no clear wells on the wellplate")
        slack.send_message(
            "alert",
            "Please replace the wellplate and restart the program from the main menu",
        )
        raise ShutDownCommand

    return stock_vials_only, waste_vials_only, wellplate


@timing_wrapper
def _check_stock_vials(
    exp_solns: dict, stock_vials: Sequence[Vial]
) -> Tuple[bool, dict]:
    """
    Check that there is enough volume in the stock vials to run the experiment

    Args:
        exp_solns (dict): Dictionary of solutions required for the experiment
        stock_vials (list[Vial]): The stock vials

    Returns:
        bool: True if there is enough volume in the stock vials to run the experiment
    """
    ## Check that the experiment has solutions and those soltuions are in the stock vials

    check_table = {
        "sufficient": [],
        "insufficient": [],
        "missing": [],
    }

    passes = True

    if len(exp_solns) == 0:
        logger.warning("The experiment has no solutions.")
        passes = True
        return passes, check_table
    contents_keys_list = []
    for vial in stock_vials:
        for key in vial.contents.keys():
            contents_keys_list.append(str(key).lower())

    for solution in exp_solns:
        solution_lwr = str(solution).lower()
        logger.debug("Checking for solution %s in stock vials", solution_lwr)

        if solution_lwr not in contents_keys_list:
            logger.error(
                "The experiment requires solution %s but it is not in the stock vials",
                solution,
            )
            passes = False
            check_table["missing"].append(solution)

    ## Check that there is enough volume in the stock vials to run the experiment
    ## Note there may be multiple of the same stock vial so we need to sum the volumes
    for solution in exp_solns:
        solution_lwr = str(solution).lower()
        vol = exp_solns[solution]["volume"]
        try:
            rep = exp_solns[solution]["repeated"]
        except KeyError:
            rep = 1
        volume_required = vol * rep
        volume_available = sum(
            [
                vial.volume
                for vial in stock_vials
                if solution_lwr
                in [
                    str(key).lower()
                    for vial in stock_vials
                    for key in vial.contents.keys()
                ]
            ]
        )  # we sum the volumes of all stock vials with the same name
        if volume_available < volume_required:
            logger.error(
                "There is not enough volume of solution %s to run the experiment",
                solution,
            )
            passes = False
            check_table["insufficient"].append(solution)
        else:
            check_table["sufficient"].append(solution)

    return passes, check_table


@timing_wrapper
def _monitor_system_status(
    slack: SlackBot, status_queue: multiprocessing.Queue, process_id: int
) -> SystemState:
    """
    Loop to check the system status and update the system status
    """
    first_pause = True
    while True:
        slack.check_slack_messages("alert")
        # Check the system status
        system_status = sql_system_state.select_system_status(1)
        if SystemState.SHUTDOWN in system_status:
            raise ShutDownCommand

        if SystemState.STOP in system_status:
            return SystemState.STOP

        if SystemState.RESUME in system_status:
            slack.send_message("alert", "PANDA_SDL is resuming")
            sql_system_state.set_system_status(SystemState.BUSY)
            break
        if len(sql_queue.select_queue()) > 0:
            slack.send_message("alert", "PANDA_SDL is resuming")
            sql_system_state.set_system_status(SystemState.BUSY)
            break
        if SystemState.PAUSE in system_status:
            # elif SystemState.PAUSE in system_status or SystemState.WAITING in system_status:
            # if SystemState.IDLE in system_status:
            #     break
            if first_pause:
                slack.send_message("alert", "PANDA_SDL is paused")
                status_queue.put((process_id, "idle"))
                first_pause = False
            for remaining in range(60, 0, -1):
                sys.stdout.write("\r")
                sys.stdout.write(
                    f"Waiting for new experiments: {remaining} seconds remaining"
                )
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write("\r")
            sys.stdout.write("Waiting for new experiments: 0 seconds remaining")
            sys.stdout.flush()
            sys.stdout.write("\n")
            continue


@timing_wrapper
def connect_to_instruments(
    use_mock_instruments: bool = TESTING,
) -> tuple[Toolkit, bool]:
    """Connect to the instruments"""
    instruments = Toolkit(
        mill=None,
        scale=None,
        pump=None,
        wellplate=None,
        global_logger=logger,
        experiment_logger=logger,
        arduino=None,
        flir_camera=None,
    )

    if use_mock_instruments:
        logger.info("Using mock instruments")
        instruments.mill = MockMill()
        instruments.mill.connect_to_mill()
        # instruments.scale = MockScale()
        instruments.pump = MockPump()
        # pstat = echem_mock.GamryPotentiostat.connect()
        instruments.arduino = MockArduinoLink()
        return instruments, True

    incomplete = False
    logger.info("Connecting to instruments:")
    try:
        logger.debug("Connecting to mill")
        instruments.mill = Mill()
        instruments.mill.connect_to_mill()
        instruments.mill.homing_sequence()
    except Exception as error:
        logger.error("No mill connected, %s", error)
        instruments.mill = None
        # raise error
        incomplete = True

    # try:
    #     logger.debug("Connecting to scale")
    #     scale = Scale(address="COM6")
    #     info_dict = scale.get_info()
    #     model = info_dict["model"]
    #     serial = info_dict["serial"]
    #     software = info_dict["software"]
    #     if not model:
    #         logger.error("No scale connected")
    #         # raise Exception("No scale connected")
    #     logger.debug("Connected to scale:\n%s\n%s\n%s\n", model, serial, software)
    # except Exception as error:
    #     logger.error("No scale connected, %s", error)
    #     instruments.scale = None
    #     # raise error
    #     incomplete = True

    try:
        logger.debug("Connecting to pump")
        instruments.pump = SyringePump()
        logger.debug("Connected to pump at %s", instruments.pump.pump.address)

    except Exception as error:
        logger.error("No pump connected, %s", error)
        instruments.pump = None
        # raise error
        incomplete = True

    # Check for FLIR Camera
    try:
        logger.debug("Connecting to FLIR Camera")
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        if cam_list.GetSize() == 0:
            logger.error("No FLIR Camera connected")
            instruments.flir_camera = None
        else:
            instruments.flir_camera = cam_list.GetByIndex(0)
            # instruments.flir_camera.Init()
            cam_list.Clear()
            system.ReleaseInstance()

            logger.debug("Connected to FLIR Camera")
    except Exception as error:
        logger.error("No FLIR Camera connected, %s", error)
        instruments.flir_camera = None
        incomplete = True

    # Connect to PSTAT

    # Connect to Arduino
    try:
        logger.debug("Connecting to Arduino")
        with ArduinoLink() as arduino:
            if not arduino.configured:
                logger.error("No Arduino connected")
                incomplete = True
                instruments.arduino = None
            logger.debug("Connected to Arduino")
            instruments.arduino = ArduinoLink()
    except Exception as error:
        logger.error("Error connecting to Arduino, %s", error)
        incomplete = True

    if incomplete:
        print("Not all instruments connected")
        return instruments, False

    logger.info("Connected to instruments")
    return instruments, True


@timing_wrapper
def test_instrument_connections(
    use_mock_instruments: bool = TESTING,
) -> tuple[Toolkit, bool]:
    """Connect to the instruments"""
    instruments = Toolkit(
        mill=None,
        scale=None,
        pump=None,
        wellplate=None,
        arduino=None,
        global_logger=logger,
        experiment_logger=logger,
    )

    if use_mock_instruments:
        logger.info("Using mock instruments")
        instruments.mill = MockMill()
        instruments.mill.connect_to_mill()
        # instruments.scale = MockScale()
        instruments.pump = MockPump()
        instruments.arduino = MockArduinoLink()
        # pstat = echem_mock.GamryPotentiostat.connect()
        return instruments

    incomplete = False
    logger.info("Connecting to instruments:")
    try:
        logger.debug("Connecting to mill")
        instruments.mill = Mill()
        instruments.mill.connect_to_mill()
    except Exception as error:
        logger.error("No mill connected, %s", error)
        instruments.mill = None
        # raise error
        incomplete = True

    # try:
    #     logger.debug("Connecting to scale")
    #     scale = Scale(address="COM6")
    #     info_dict = scale.get_info()
    #     model = info_dict["model"]
    #     serial = info_dict["serial"]
    #     software = info_dict["software"]
    #     if not model:
    #         logger.error("No scale connected")
    #         # raise Exception("No scale connected")
    #     logger.debug("Connected to scale:\n%s\n%s\n%s\n", model, serial, software)
    # except Exception as error:
    #     logger.error("No scale connected, %s", error)
    #     instruments.scale = None
    #     # raise error
    #     incomplete = True

    try:
        logger.debug("Connecting to pump")
        instruments.pump = SyringePump()
        logger.debug("Connected to pump at %s", instruments.pump.pump.address)

    except Exception as error:
        logger.error("No pump connected, %s", error)
        instruments.pump = None
        # raise error
        incomplete = True

    # Check for FLIR Camera
    try:
        logger.debug("Connecting to FLIR Camera")
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        if cam_list.GetSize() == 0:
            logger.error("No FLIR Camera connected")
            instruments.flir_camera = None
            incomplete = True
        else:
            instruments.flir_camera = cam_list.GetByIndex(0)
            # instruments.flir_camera.Init()
            cam_list.Clear()
            system.ReleaseInstance()

            logger.debug("Connected to FLIR Camera")

    except Exception as error:
        logger.error("No FLIR Camera connected, %s", error)
        instruments.flir_camera = None
        incomplete = True

    # Connect to PSTAT
    try:
        logger.debug("Connecting to Potentiostat")
        connected = gamry_control.pstatconnect()
        if not connected:
            logger.error("No Potentiostat connected")
            incomplete = True
        else:
            logger.debug("Connected to Potentiostat")
            gamry_control.pstatdisconnect()
    except Exception as error:
        logger.error("Error connecting to Potentiostat, %s", error)
        incomplete = True

    # Connect to Arduino
    try:
        logger.debug("Connecting to Arduino")
        with ArduinoLink() as arduino:
            if not arduino.configured:
                logger.error("No Arduino connected")
                incomplete = True
                instruments.arduino = None
            logger.debug("Connected to Arduino")
            instruments.arduino = arduino
    except Exception as error:
        logger.error("Error connecting to Arduino, %s", error)
        incomplete = True

    if incomplete:
        print("Not all instruments connected")
        return instruments, False

    logger.info("Connected to all instruments")
    return instruments, True


@timing_wrapper
def disconnect_from_instruments(instruments: Toolkit):
    """Disconnect from the instruments"""
    logger.info("Disconnecting from instruments:")
    if instruments.mill:
        instruments.mill.disconnect()
    # if instruments.flir_camera: instruments.flir_camera.DeInit()

    logger.info("Disconnected from instruments")


@timing_wrapper
def share_to_slack(experiment: ExperimentBase):
    """Share the results of the experiment to the slack data channel"""
    slack = SlackBot(test=TESTING)

    if experiment.results is None:
        logger.error("The experiment has no results")
        return
    if experiment.results.images is None:
        logger.error("The experiment has no image files")
        return
    try:
        exp_id = experiment.experiment_id

        if TESTING:
            msg = f"Experiment {exp_id} has completed with status {experiment.status}. Testing mode, no images to share"
            slack.send_message("data", msg)
            return
        # images_with_dz = [
        #     image
        #     for image in experiment.results.image
        #     if image[0].name.endswith("dz.tiff")
        # ]
        # if len(images_with_dz) == 0:
        #     logger.error(
        #         "The experiment %d has no dz.tiff image files", exp_id
        #     )
        #     msg = f"Experiment {exp_id} has completed with status {exp_id} but has no datazoned image files to share"
        #     slack.send_slack_message("data", msg)
        #     return

        # for image in experiment.results.image:
        #     image: Path = image[0]
        #     images_with_dz = []
        #     if image.name.endswith("dz.tiff"):
        #         images_with_dz.append(image)
        # msg = f"Experiment {exp_id} has completed with status {experiment.status}. Photos taken:"
        #     slack.upload_images("data", images_with_dz, msg)

        results = select_specific_result(exp_id, "image")

        if results is None:
            logger.error("The experiment %d has no image files", exp_id)
            msg = f"Experiment {exp_id} has completed with status {experiment.status} but has no image files to share"
            slack.send_message("data", msg)
            return

        for result in results:
            result: ExperimentResultsRecord
            if "dz" not in result.result_value:
                results.remove(result)

        if len(results) == 0:
            logger.error("The experiment %d has no dz.tiff image files", exp_id)
            msg = f"Experiment {exp_id} has completed with status {experiment.status} but has no datazoned image files to share"
            slack.send_message("data", msg)
            return

        msg = f"Experiment {exp_id} has completed with status {experiment.status}. Photos taken:"
        image_paths = [result.result_value for result in results]
        slack.upload_images("data", image_paths, f"{msg}")
    except (
        slack_errors.SlackApiError,
        slack_errors.SlackClientError,
        slack_errors.SlackRequestError,
        slack_errors.SlackTokenRotationError,
        slack_errors.BotUserAccessError,
        slack_errors.SlackClientConfigurationError,
        slack_errors.SlackObjectFormationError,
        slack_errors.SlackRequestError,
    ) as error:
        logger.warning(
            "A Slack specific error occured while sharing images from experiment %d with slack: %s",
            experiment.experiment_id,
            error,
        )
        # continue with the rest of the program

    except Exception as error:
        logger.warning(
            "An unanticipated error occured while sharing images from experiment %d with slack: %s",
            experiment.experiment_id,
            error,
        )
        # continue with the rest of the program


if __name__ == "__main__":
    print("TEST MODE: ", TESTING)
    input("Press enter to continue or ctrl+c to exit")
    experiment_loop_worker(use_mock_instruments=TESTING, one_off=False)
