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
# pylint: disable=line-too-long
import json
import logging

# import standard libraries

# import third-party libraries
from typing import Sequence

import e_panda
import wellplate as wellplate_module
from config.config import (
    RANDOM_FLAG,
    STOCK_STATUS,
    TESTING,
    WASTE_STATUS,
    WELL_STATUS,
)
from experiment_class import ExperimentBase, ExperimentResult, ExperimentStatus
from mill_control import Mill, MockMill
from pump_control import MockPump, Pump
from sartorius_local import Scale
from sartorius_local.mock import Scale as MockScale
from scheduler import Scheduler
from instrument_toolkit import Toolkit

# import obs_controls as obs
from slack_functions2 import SlackBot
from vials import StockVial, Vial2, WasteVial, read_vials, update_vial_state_file
from wellplate import save_current_wellplate
from obs_controls import OBSController
# set up logging to log to both the pump_control.log file and the ePANDA.log file
from log_tools import e_panda_logger as logger

# set up slack globally so that it can be used in the main function and others
slack = SlackBot()
obs = OBSController()

def main(use_mock_instruments: bool = TESTING, one_off: bool = False):
    """
    Main function

    Args:
    ----
        use_mock_instruments (bool, optional): Whether to use mock instruments. Defaults to False.
        one_off (bool, optional): Whether to run one experiment and then exit. Defaults to False.
    """
    #import exp_b_pipette_contamination_assessment_protocol as exp_b
    #import protocols

    ## Reset the logger to log to the ePANDA.log file and format
    e_panda.apply_log_filter()
    # print(printpanda())
    print("Starting ePANDA...")
    slack.test = use_mock_instruments
    slack.send_slack_message("alert", "ePANDA is starting up")
    toolkit = None
    # Everything runs in a try block so that we can close out of the serial connections if something goes wrong
    try:
        obs.place_text_on_screen("ePANDA is starting up")
        obs.start_recording()
        new_experiment = None
        # Connect to equipment
        toolkit = connect_to_instruments(use_mock_instruments)
        logger.info("Connected to instruments")
        slack.send_slack_message("alert", "ePANDA has connected to equipment")
        obs.place_text_on_screen("ePANDA has connected to equipment")
        ## Initialize scheduler
        scheduler = Scheduler()

        ## Establish state of system - we do this each time because each experiment changes the system state
        stock_vials, waste_vials, wellplate = establish_system_state()

        # Flush the pipette tip with water before we start
        obs.place_text_on_screen("Initial flushing of pipette tip")
        e_panda.flush_v2(
            stock_vials=stock_vials,
            waste_vials=waste_vials,
            flush_solution_name="rinse",
            flush_volume=140,
            pump=toolkit.pump,
            mill=toolkit.mill,
        )
        ## Update the system state with new vial and wellplate information
        update_vial_state_file(stock_vials, STOCK_STATUS)
        update_vial_state_file(waste_vials, WASTE_STATUS)

        ## Begin experiemnt loop
        while True:
            ## Reset the logger to log to the ePANDA.log file and format
            obs.place_text_on_screen("")
            e_panda.apply_log_filter()

            ## Establish state of system - we do this each time because each experiment changes the system state
            stock_vials, waste_vials, wellplate = establish_system_state()
            toolkit.wellplate = wellplate
            ## Check the qeueue for any protocol type 2 experiments
            #queue = scheduler.get_queue()
            # check if any of the experiments in the queue pandas dataframe are type 2
            ## Ask the scheduler for the next experiment
            new_experiment, _ = scheduler.read_next_experiment_from_queue(
                random_pick=RANDOM_FLAG
            )
            # if new_experiment is None:
            #     slack.send_slack_message(
            #         "alert",
            #         "No new experiments to run...monitoring inbox for new experiments",
            #     )
            if new_experiment is None:
                # e_panda.flush_pipette_tip(pump=toolkit.pump,
                #                           mill=toolkit.mill,
                #                           stock_vials=stock_vials,
                #                           waste_vials=waste_vials,
                #                           flush_solution_name='water',
                #                           flush_volume=120,
                #                           )
                break  # break out of the while True loop

            # while new_experiment is None:
            #     scheduler.check_inbox()
            #     new_experiment, _ = scheduler.read_next_experiment_from_queue()
            #     if new_experiment is not None:
            #         slack.send_slack_message(
            #             "alert", f"New experiment {new_experiment.id} found"
            #         )
            #         break # break out of the while new experiment is None loop
            #     logger.info(
            #         "No new experiments to run...waiting 5 minutes for new experiments"
            #     )
            #     time.sleep(600)
            #     # Replace with slack alert and wait for response from user

            ## confirm that the new experiment is a valid experiment object
            if not isinstance(new_experiment, ExperimentBase):
                logger.error("The experiment object is not valid")
                slack.send_slack_message(
                    "alert",
                    "An invalid experiment object was passed to the controller",
                )
                break  # break out of the while True loop

            ## Check that there is enough volume in the stock vials to run the experiment
            if not check_stock_vials(new_experiment, stock_vials):
                error_message = f"Experiment {new_experiment.id} cannot be run because there is not enough volume in the stock vials"
                slack.send_slack_message(
                    "alert",
                    error_message,
                )
                logger.error(error_message)
                new_experiment.set_status(ExperimentStatus.ERROR)
                new_experiment.priority = 999
                scheduler.update_experiment_file(new_experiment)
                scheduler.update_experiment_queue_priority(
                    new_experiment.id, new_experiment.priority
                )
                break  # break out of the while True loop

            ## Initialize a results object
            new_experiment.results = ExperimentResult(
                id=new_experiment.id,
                well_id=new_experiment.well_id,
            )
            # Announce the experiment
            pre_experiment_status_msg = f"Running experiment {new_experiment.id}"
            logger.info(pre_experiment_status_msg)
            slack.send_slack_message("alert", pre_experiment_status_msg)

            ## Update the experiment status to running
            new_experiment.set_status(ExperimentStatus.RUNNING)
            scheduler.change_well_status_v2(
                wellplate.wells[new_experiment.well_id], new_experiment
            )

            ## Run the experiment
            e_panda.apply_log_filter(
                new_experiment.id,
                new_experiment.well_id,
                str(new_experiment.project_id)
                + "."
                + str(new_experiment.project_campaign_id),
                test=use_mock_instruments,
            )

            ## Now that we know we are about to run the experiment
            ## Add the plate id to the experiment
            new_experiment.plate_id = wellplate.plate_id

            logger.info("Beginning experiment %d", new_experiment.id)
            import exp_a_2_ferrocyanide_assessment_protocol as exp_a
            exp_a.cv_repeatability(
                instructions=new_experiment,
                toolkit=toolkit,
                stock_vials=stock_vials,
                waste_vials=waste_vials,
            )
            #import exp_edot_bleaching_protocol as edot
            # import exp_d2_mixing_assessment_protocol as exp_d2
            # exp_d2.mixing_assessment(
            #     instructions=new_experiment,
            #     toolkit=toolkit,
            #     stock_vials=stock_vials,
            #     waste_vials=waste_vials,
            # )
            ## Update the experiment status to complete
            new_experiment.set_status(ExperimentStatus.COMPLETE)

            ## Reset the logger to log to the ePANDA.log file and format
            e_panda.apply_log_filter()

            ## With returned experiment and results, update the experiment status and post the final status
            post_experiment_status_msg = f"Experiment {new_experiment.id} ended with status {new_experiment.status.value}"
            logger.info(post_experiment_status_msg)
            # slack.send_slack_message("alert", post_experiment_status_msg)

            ## Update the system state with new vial and wellplate information
            scheduler.change_well_status_v2(
                wellplate.wells[new_experiment.well_id], new_experiment
            )

            ## Update location of experiment instructions and save results
            scheduler.update_experiment_file(new_experiment)
            scheduler.update_experiment_location(new_experiment)
            scheduler.save_results(new_experiment, new_experiment.results)

            scheduler.remove_from_queue(new_experiment)
            new_experiment = None # reset new_experiment to None so that we can check the queue again
            
            ## Update the system state with new vial and wellplate information
            update_vial_state_file(stock_vials, STOCK_STATUS)
            update_vial_state_file(waste_vials, WASTE_STATUS)
            if one_off:
                break  # break out of the while True loop
    except Exception as error:
        if new_experiment is not None:
            new_experiment.set_status(ExperimentStatus.ERROR)
            scheduler.change_well_status_v2(
                    wellplate.wells[new_experiment.well_id], new_experiment
                )

        logger.error(error)
        slack.send_slack_message("alert", f"ePANDA encountered an error: {error}")
        raise error

    except KeyboardInterrupt as exc:
        if new_experiment is not None:
            new_experiment.set_status(ExperimentStatus.ERROR)
            scheduler.change_well_status_v2(
                    wellplate.wells[new_experiment.well_id], new_experiment
                )
        logger.info("Keyboard interrupt detected")
        slack.send_slack_message("alert", "ePANDA was interrupted by the user")
        raise KeyboardInterrupt from exc

    finally:
        if new_experiment is not None:
            ## Update location of experiment instructions and save results
            scheduler.update_experiment_file(new_experiment)
            scheduler.update_experiment_location(new_experiment)
            scheduler.save_results(new_experiment, new_experiment.results)

        # Save the current wellplate
        save_current_wellplate() #load a "new" wellplate to save and update wells
        # close out of serial connections
        toolkit.mill.rest_electrode()
        if toolkit is not None:
            disconnect_from_instruments(toolkit)
        obs.place_text_on_screen("")
        obs.stop_recording()
        slack.send_slack_message("alert", "ePANDA is shutting down...goodbye")
        print("ePANDA is shutting down...goodbye")


def establish_system_state() -> (
    tuple[Sequence[StockVial], Sequence[WasteVial], wellplate_module.Wellplate]
):
    """
    Establish state of system
    Returns:
        stock_vials (list[Vial]): list of stock vials
        waste_vials (list[Vial]): list of waste vials
        wellplate (wellplate_module.Wells): wellplate object
    """
    stock_vials = read_vials(STOCK_STATUS)
    waste_vials = read_vials(WASTE_STATUS)
    stock_vials_only = [vial for vial in stock_vials if isinstance(vial, StockVial)]
    waste_vials_only = [vial for vial in waste_vials if isinstance(vial, WasteVial)]
    wellplate = wellplate_module.Wellplate()
    logger.info("System state established")

    ## read through the stock vials and log their name, contents, and volume
    for vial in stock_vials_only:
        logger.debug(
            "Stock vial %s contains %s with volume %d",
            vial.name,
            vial.contents,
            vial.volume,
        )

    ## if any stock vials are empty, send a slack message prompting the user to refill them and confirm if program should continue
    empty_stock_vials = [vial for vial in stock_vials_only if vial.volume < 1000]
    if len(empty_stock_vials) > 0:
        slack.send_slack_message(
            "alert",
            "The following stock vials are low or empty: "
            + ", ".join([vial.name for vial in empty_stock_vials]),
        )
        slack.send_slack_message(
            "alert",
            "Please refill the stock vials and confirm in the terminal that the program should continue",
        )
        input(
            "Confirm that the program should continue by pressing enter or ctrl+c to exit"
        )
        slack.send_slack_message("alert", "The program is continuing")

    ## read through the waste vials and log their name, contents, and volume
    for vial in waste_vials_only:
        logger.debug(
            "Waste vial %s contains %s with volume %d",
            vial.name,
            vial.contents,
            vial.volume,
        )

    ## if any waste vials are full, send a slack message prompting the user to empty them and confirm if program should continue
    full_waste_vials = [vial for vial in waste_vials_only if vial.volume > 19000]
    if len(full_waste_vials) == len(waste_vials_only):
        slack.send_slack_message(
            "alert",
            "The following waste vials are full: "
            + ", ".join([vial.name for vial in full_waste_vials]),
        )
        slack.send_slack_message(
            "alert",
            "Please empty the waste vials and confirm in the terminal that the program should continue",
        )
        input(
            "Confirm that the program should continue by pressing enter or ctrl+c to exit"
        )
        slack.send_slack_message("alert", "The program is continuing")

    ## read the wellplate json and log the status of each well in a grid
    number_of_clear_wells = 0
    number_of_wells = 0
    with open(WELL_STATUS, "r", encoding="UTF-8") as file:
        wellplate_status = json.load(file)
    for well in wellplate_status["wells"]:
        number_of_wells += 1
        if well["status"] in ["clear", "new", "queued"]:
            number_of_clear_wells += 1

    ## check that wellplate has the appropriate number of wells
    if number_of_wells != len(wellplate.wells):
        logger.error(
            "Wellplate status file does not have the correct number of wells. File may be corrupted"
        )
        raise ValueError
    logger.info("There are %d clear wells", number_of_clear_wells)
    if number_of_clear_wells == 0:
        # slack.send_slack_message("alert", "There are no clear wells on the wellplate")
        # slack.send_slack_message(
        #     "alert",
        #     "Please replace the wellplate and confirm in the terminal that the program should continue",
        # )
        # input(
        #     "Confirm that the program should continue by pressing enter or ctrl+c to exit"
        # )
        # load_new_wellplate()
        # slack.send_slack_message("alert", "Wellplate has been reset. Continuing...")
        pass

    return stock_vials_only, waste_vials_only, wellplate


def check_stock_vials(experiment: ExperimentBase, stock_vials: Sequence[Vial2]) -> bool:
    """
    Check that there is enough volume in the stock vials to run the experiment

    Args:
        experiment (Experiment): The experiment to be run
        stock_vials (list[Vial]): The stock vials

    Returns:
        bool: True if there is enough volume in the stock vials to run the experiment
    """
    ## Check that the experiment has solutions and those soltuions are in the stock vials
    if len(experiment.solutions) == 0:
        logger.error("The experiment has no solutions")
        return False
    for solution in experiment.solutions:
        if str(solution).lower() not in [
            str(vial.name).lower() for vial in stock_vials
        ]:
            logger.error(
                "The experiment requires solution %s but it is not in the stock vials",
                solution,
            )
            return False

    ## Check that there is enough volume in the stock vials to run the experiment
    ## Note there may be multiple of the same stock vial so we need to sum the volumes
    for solution in experiment.solutions:
        volume_required = experiment.solutions[solution]
        volume_available = sum(
            [vial.volume for vial in stock_vials if vial.name == solution]
        )
        if volume_available < volume_required:
            logger.error(
                "There is not enough volume of solution %s to run the experiment",
                solution,
            )
            return False
    return True


def connect_to_instruments(use_mock_instruments: bool = TESTING) -> Toolkit:
    """Connect to the instruments"""
    if use_mock_instruments:
        logger.info("Using mock instruments")
        mill = MockMill()
        mill.connect_to_mill()
        scale = MockScale()
        pump = MockPump(mill=mill, scale=scale)
        # pstat = echem_mock.GamryPotentiostat.connect()
        instruments = Toolkit(
            mill=mill,
            scale=scale,
            pump=pump,
            wellplate=None,
            global_logger=logger,
            experiment_logger=logger,
        )
        return instruments

    logger.info("Connecting to instruments:")
    mill = Mill()
    mill.connect_to_mill()
    mill.homing_sequence()
    scale = Scale(address="COM6")
    pump = Pump(mill=mill, scale=scale)
    # pstat_connected = echem.pstatconnect()
    instruments = Toolkit(
        mill=mill,
        scale=scale,
        pump=pump,
        wellplate=None,
        global_logger=logger,
        experiment_logger=logger,
    )
    return instruments


def disconnect_from_instruments(instruments: Toolkit):
    """Disconnect from the instruments"""
    logger.info("Disconnecting from instruments:")
    instruments.mill.disconnect()

    logger.info("Disconnected from instruments")

if __name__ == "__main__":
    #wellplate_module.load_new_wellplate(False,new_plate_id=107,new_wellplate_type_number=3)
    print("TEST MODE: ", TESTING)
    input("Press enter to continue or ctrl+c to exit")
    main(use_mock_instruments=TESTING, one_off=False)
