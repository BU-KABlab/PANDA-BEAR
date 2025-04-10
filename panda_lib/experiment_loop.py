"""
The controller is responsible for the following:
    - Running the scheduler and retrieving the next experiment to run
    - checking the state of the system (vials, wells, etc.)
    - Running the experiment (passing the experiment, system state, and instruments)
    - Receive data from the experiment, and store it in the database
    - Update system state (vials, wells, etc.)
    - Running the analyzer

Additionally controller should be able to:
    - Update the vial statuses
"""

import importlib
import logging
import multiprocessing
import sys
import time
from pathlib import Path
from typing import Optional, Sequence, Tuple

from sqlalchemy import update
from sqlalchemy.orm import sessionmaker

from panda_lib import scheduler
from panda_lib.actions import purge_pipette
from panda_lib.errors import (
    CAFailure,
    CVFailure,
    DepositionFailure,
    ExperimentError,
    ExperimentNotFoundError,
    InstrumentConnectionError,
    InsufficientVolumeError,
    MismatchWellplateTypeError,
    OCPError,
    ProtocolNotFoundError,
    ShutDownCommand,
    WellImportError,
)
from panda_lib.experiments import (
    EchemExperimentBase,
    ExperimentBase,
    ExperimentResult,
    ExperimentStatus,
    select_complete_experiment_information,
    select_experiment_status,
)
from panda_lib.labware.vials import StockVial, Vial, WasteVial, read_vials
from panda_lib.labware.wellplates import Well, Wellplate
from panda_lib.slack_tools.slackbot_module import SlackBot, share_to_slack
from panda_lib.sql_tools import (
    panda_models,
    sql_protocol_utilities,
    sql_queue,
    sql_system_state,
    sql_wellplate,
)
from panda_lib.toolkit import (
    Hardware,
    Labware,
    connect_to_instruments,
    disconnect_from_instruments,
)
from panda_lib.utilities import SystemState
from shared_utilities.config.config_tools import read_config, read_testing_config
from shared_utilities.db_setup import SessionLocal
from shared_utilities.log_tools import (
    apply_log_filter,
    setup_default_logger,
    timing_wrapper,
)

config = read_config()
logger = setup_default_logger(log_name="panda")
TESTING = read_testing_config()


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

        stock_vials, waste_vials, toolkit.wellplate = _establish_system_state()

        ## Check that the pipette is empty, if not dispose of full volume into waste
        if toolkit.pump.pipette.volume > 0:
            # obs.place_text_on_screen("Pipette is not empty, purging into waste")
            status_queue.put((process_id, "Purging pipette into waste"))
            purge_pipette(toolkit)

        while True:
            ## Begin slack monitoring
            # slack_thread.start()

            ## Reset the logger to log to the PANDA_SDL.log file and format
            # obs.place_text_on_screen("")
            apply_log_filter(logger=logger)
            sql_system_state.set_system_status(SystemState.BUSY)
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

            # Validate the experiment object
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
                well.plate_id != toolkit.wellplate.id
                or current_experiment.plate_type_number != toolkit.wellplate.type_id
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
            # Initialize a results object
            current_experiment.results = ExperimentResult(
                experiment_id=current_experiment.experiment_id,
                well_id=current_experiment.well_id,
            )
            # Check that there is enough volume in the stock vials to run the experiment
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
            current_experiment.plate_id = toolkit.wellplate.id
            current_experiment.well = toolkit.wellplate.wells[
                current_experiment.well_id
            ]
            current_experiment.well.plate_id = toolkit.wellplate.id
            current_experiment.well.well_data.experiment_id = (
                current_experiment.experiment_id
            )
            current_experiment.well.well_data.project_id = current_experiment.project_id
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

            current_experiment.set_status_and_save(ExperimentStatus.SAVING)
            current_experiment.results.save_results()
            current_experiment.set_status_and_save(ExperimentStatus.COMPLETE)
            # Post to the alerts channel
            controller_slack.send_message(
                "alert",
                f"Experiment {current_experiment.experiment_id} has completed",
            )
            # Share any results images with the slack data channel
            share_to_slack(current_experiment)

            # Reset the logger to log to the PANDA_SDL.log file and format after the experiment is complete
            apply_log_filter(logger=logger)

            # With returned experiment and results, update the experiment status and post the final status
            post_experiment_status_msg = f"Experiment {current_experiment.experiment_id} ended with status {current_experiment.status.value}"
            logger.info(post_experiment_status_msg)
            status_queue.put((process_id, post_experiment_status_msg))
            # slack.send_slack_message("alert", post_experiment_status_msg)

            ## If the status is complete mark for analysis
            if current_experiment.status == ExperimentStatus.COMPLETE:
                with SessionLocal() as connection:
                    stmt = (
                        update(panda_models.Experiments)
                        .where(panda_models.Experiments.experiment_id)
                        .values(needs_analysis=True)
                    )
                    connection.execute(stmt)
                    connection.commit()

            ## Clean up
            current_experiment = None  # reset new_experiment to None so that we can check the queue again
            ## Update the system state with new vial and wellplate information

            if toolkit.pump.pipette.volume > 0 and toolkit.pump.pipette.volume_ml < 1:
                # assume unreal volume, not actually solution, set to 0
                toolkit.pump.pipette.reset_contents()
            if one_off:
                break  # break out of the while True loop

            # Check for incoming commands
            if not command_queue.empty():
                cmd = command_queue.get_nowait()
                if cmd == SystemState.STOP:
                    logger.info("Received STOP command. Exiting loop.")
                    break
                elif cmd == SystemState.PAUSE:
                    logger.info("Received PAUSE command. Waiting for RESUME.")
                    while True:
                        status_queue.put((process_id, "pause"))
                        if not command_queue.empty():
                            resume_cmd = command_queue.get_nowait()
                            if resume_cmd == SystemState.RESUME:
                                logger.info("Received RESUME command. Resuming loop.")
                                break
                            elif resume_cmd == SystemState.STOP:
                                logger.info(
                                    "Received STOP command during PAUSE. Exiting."
                                )
                                return
                        time.sleep(0.5)  # small wait to avoid busy loop

    except (
        OCPError,
        DepositionFailure,
        CVFailure,
        CAFailure,
    ) as error:
        if current_experiment is not None:
            current_experiment.set_status_and_save(ExperimentStatus.ERROR)
        sql_system_state.set_system_status(SystemState.ERROR)

        logger.error(error)
        controller_slack.echem_error_procedure()

        raise error  # raise error to go to finally. We do not want the program to continue if there is an electrochemistry error as it usually indicates a hardware or solutions issue

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
            current_experiment.results.save_results()
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
    specific_experiment_ids: Optional[list[int]] = None,
    specific_well_id: Optional[str] = None,
    process_id: Optional[int] = None,
    status_queue: multiprocessing.Queue = None,
    command_queue: multiprocessing.Queue = None,
) -> None:
    """
    Main worker function to execute SILA experiments.
    """

    toolkit, _ = connect_to_instruments(config.getboolean("OPTIONS", "testing"))
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
    toolkit.wellplate = labware.wellplate

    experiment_ids = (
        [specific_experiment_id] if specific_experiment_id else specific_experiment_ids
    )

    def set_worker_state(state: SystemState):
        """Set the worker state"""
        sql_system_state.set_system_status(state)
        status_queue.put((process_id, f"{specific_experiment_id}: {state.value}"))

    for specific_experiment_id in experiment_ids:
        # Check for incoming commands
        if not command_queue.empty():
            cmd = command_queue.get_nowait()
            if cmd == SystemState.STOP:
                logger.info("Received STOP command. Exiting loop.")
                break
            elif cmd == SystemState.PAUSE:
                logger.info("Received PAUSE command. Waiting for RESUME.")
                while True:
                    status_queue.put((process_id, "pause"))
                    if not command_queue.empty():
                        resume_cmd = command_queue.get_nowait()
                        if resume_cmd == SystemState.RESUME:
                            logger.info("Received RESUME command. Resuming loop.")
                            break
                        elif resume_cmd == SystemState.STOP:
                            logger.info("Received STOP command during PAUSE. Exiting.")
                            return
                    time.sleep(0.5)  # small wait to avoid busy loop

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
                purge_pipette(toolkit)
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
                    # hardware=hardware,
                    # labware=labware,
                    toolkit=toolkit,
                )

            except (
                OCPError,
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
                    exp_obj.results.save_results()
                    if status == ExperimentStatus.COMPLETE:
                        with SessionLocal() as connection:
                            stmt = (
                                update(panda_models.Experiments)
                                .where(panda_models.Experiments.experiment_id)
                                .values(needs_analysis=True)
                            )
                            connection.execute(stmt)
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
                exp_obj.results.save_results()
                share_to_slack(exp_obj)

            ## Clean up the instruments
            if hardware.pump.pipette.volume > 0 and hardware.pump.pipette.volume_ml < 1:
                # assume unreal volume, not actually solution, set to 0
                purge_pipette(toolkit)

            hardware.mill.rest_electrode()
            # We are not disconnecting from instruments with this function, that will
            # be handled by a higher level function
            apply_log_filter(exp_logger)
            set_worker_state(SystemState.IDLE)


def _attach_well_to_experiment(exp_obj: ExperimentBase, trgt_well: Well):
    trgt_well.well_data.experiment_id = exp_obj.experiment_id
    trgt_well.well_data.project_id = exp_obj.project_id
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
    # TODO: make a function that just gets the well_id from the queue and returns it
    _, _, _, well_id = sql_queue.get_next_experiment_from_queue(
        specific_experiment_id=exp_id
    )
    # TODO: Replace with checking for available well, unless given one.
    exp_obj.well_id = well_id

    if not exp_obj:
        raise ExperimentNotFoundError(f"Experiment {exp_id} not found in the database.")

    well = labware.wellplate.wells[exp_obj.well_id]
    if (
        well.plate_id != labware.wellplate.id
        or exp_obj.plate_type_number != labware.wellplate.type_id
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
    # First check experiment specific solutions in solutions dictionary
    check_table_a, check_table_b, check_table_c = {}, {}, {}

    sufficient_stock_1, check_table_a = _check_stock_vials(
        exp.solutions, labware.stock_vials
    )
    # Next check for any additional solutions in the experiment under rinse_sol_name and flush_sol_name
    if exp.rinse_sol_name:
        rinse_sol = {
            exp.rinse_sol_name: {"volume": exp.rinse_vol, "repeated": 1}
        }  # This is a false repeated value but allows us to reuse the check_stock_vials function
        sufficient_stock_2, check_table_b = _check_stock_vials(
            rinse_sol, labware.stock_vials
        )
    if exp.flush_sol_name:
        flush_sol = {exp.flush_sol_name: {"volume": exp.flush_sol_vol, "repeated": 1}}
        sufficient_stock_3, check_table_c = _check_stock_vials(
            flush_sol, labware.stock_vials
        )

    # Consolidate the check tables
    check_table = {**check_table_a}
    [check_table[key].extend(value) for key, value in check_table_b.items()]
    [check_table[key].extend(value) for key, value in check_table_c.items()]

    sufficient_stock = all([sufficient_stock_1, sufficient_stock_2, sufficient_stock_3])

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


def _fetch_protocol_function(protocol_id: int) -> callable:
    """
    Fetch the protocol function from the protocol module.

    Args:
    ----
        protocol_id (int): The protocol id.

    Returns:
    --------
        callable: The protocol function.
    """

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

    Args:
    --------
        session_maker (Optional): The session maker object. Defaults to SessionLocal.

    Returns:
    --------
        stock_vials (list[Vial]): list of stock vials
        waste_vials (list[Vial]): list of waste vials
        wellplate (wellplate_module.Wells): wellplate object
    """
    slack = SlackBot()
    stock_vials, waste_vials = read_vials(session=session_maker)
    stock_vials_only = [vial for vial in stock_vials if isinstance(vial, StockVial)]
    waste_vials_only = [vial for vial in waste_vials if isinstance(vial, WasteVial)]
    wellplate = Wellplate()
    logger.info("System state reestablished")

    # if any stock vials are empty, send a slack message prompting the user to refill them and confirm if program should continue
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

        slack.send_message("alert", "PANDA_SDL is shutting down")
        raise ShutDownCommand

    # if any waste vials are full, send a slack message prompting the user to empty them and confirm if program should continue
    full_waste_vials = [vial for vial in waste_vials_only if vial.volume > 19000]
    if len(full_waste_vials) == len(waste_vials_only) and len(waste_vials_only)>0:
        slack.send_message(
            "alert",
            "The following waste vials are full: "
            + ", ".join([vial.name for vial in full_waste_vials]),
        )
        slack.send_message(
            "alert",
            "Please empty the waste vials and confirm in the terminal that the program should continue",
        )
        # options = input(
        #     "Confirm that the program should continue by pressing enter or q to exit: "
        # )
        # if options.lower() == "q":
        #     slack.send_message("alert", "PANDA_SDL is shutting down")
        #     raise ShutDownCommand

        # slack.send_message("alert", "The program is continuing")
        raise ShutDownCommand


    # read the wellplate json and log the status of each well in a grid
    number_of_clear_wells = 0
    number_of_wells = 0

    # Query the number of clear wells in well_status
    number_of_clear_wells = sql_wellplate.get_number_of_clear_wells()
    number_of_wells = sql_wellplate.get_number_of_wells()
    # check that wellplate has the appropriate number of wells
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
    -----
        exp_solns (dict): Dictionary of solutions required for the experiment
            formatted as:  {solution_name: {"volume": volume, "repeated": number_of_repeats}}
        stock_vials (list[Vial]): The stock vials

    Returns:
    -----
        bool: True if there is enough volume in the stock vials to run the experiment
        dict: Dictionary of solutions that are sufficient, insufficient, and missing
    """
    ## Check that the experiment has solutions and those solutions are in the stock vials

    check_table = {
        "sufficient": [],
        "insufficient": [],
        "missing": [],
    }
    passes = True

    # Lower all solutions in exp_solns
    exp_solns = {key.lower(): value for key, value in exp_solns.items()}
    # Lower all stock_vial names
    for vial in stock_vials:
        vial.vial_data.name.lower()
        vial.vial_data.contents = {
            key.lower(): value for key, value in vial.contents.items()
        }

    if len(exp_solns) == 0:
        logger.warning("The experiment has no solutions.")
        passes = True
        return passes, check_table
    contents_keys_list = []
    for vial in stock_vials:
        for key in vial.contents.keys():
            contents_keys_list.append(key)

    names_list = [vial.vial_data.name.lower() for vial in stock_vials]
    # Check that the experiment solution names are found in the stock vials
    for solution in exp_solns:
        if solution not in names_list:
            logger.error(
                "The experiment requires solution %s but it is not in the stock vials",
                solution,
            )
            passes = False
            check_table["missing"].append(solution)

    # for solution in exp_solns:
    #     logger.debug("Checking for solution %s in stock vials", solution)

    # if solution not in contents_keys_list:
    #     logger.error(
    #         "The experiment requires solution %s but it is not in the stock vials",
    #         solution,
    #     )
    #     passes = False
    #     check_table["missing"].append(solution)

    ## Check that there is enough volume in the stock vials to run the experiment
    ## Note there may be multiple of the same stock vial so we need to sum the volumes
    for solution in exp_solns:
        solution_lwr = solution
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
                in [key for vial in stock_vials for key in vial.contents.keys()]
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

    Args:
    -----
        slack (SlackBot): The slack bot object
        status_queue (multiprocessing.Queue): The status queue
        process_id (int): The process id

    Returns:
    --------
        SystemState: The system status

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


if __name__ == "__main__":
    print("TEST MODE: ", TESTING)
    input("Press enter to continue or ctrl+c to exit")
    experiment_loop_worker(use_mock_instruments=TESTING, one_off=False)
