<!-- title: PANDA SDL End User Manual -->

# [Construction](constructions.md) | [Installation](installation.md) | End User Manual | [Dev User Manual](developer_manual.md) | [Contents](user_manual.md) <!-- omit from toc -->

## Table of Contents <!-- omit from toc -->
- [Overview](#overview)
- [Operating the PANDA SDL](#operating-the-panda-sdl)
- [SlackBot (If Using)](#slackbot-if-using)
- [Protocols](#protocols)
- [Generators](#generators)
- [Analyzers](#analyzers)

## Overview

As an end user, you will hopefully not need to dive into the project code as deeply as someone developing new capabilities or fixing an issue. So you will be primarily working in 4 different directories (folders):

1. **Project Directory**

    This is where the `main.py` files lives and is run when you want to operate the system.

2. **Protocols** 
   
    This directory may live anywhere (so long as you've updated the `config.ini` accordingly and set the location of the `config.ini` in the .env file). Protocols are scripts where you write out how an experiment will be run. Think of protocols as recipes or orders of operation. Many experiments might follow the same protocol (steps) but the experiments might differ in variables like volume or voltage, you will define these with a generator.

3. **Generators**

    Like the Protocols directory, this may be placed anywhere but must be documented. Generators are Python scripts where you describe the variables of an experiment type. They are especially useful for setting up replicates or permutations of an experiment. While Protocols are the steps taken, Generators define the values of things like volumes, concentrations, solutions used, voltages etc... The Generator script then logs the experiment into the system's database and applies the appropriate identifiers.

    Generators are also used by Analyzers to generate experiments for you based on Machine Learning algorithms.

4. **Analyzers**

    As before, may be anywhere, so long as its documented. Analyzers are experiment or campaign specific Python scripts. They are how you plan to analyze certain experiments and determine if and how the system should generate experiments for you using a Generator.

## Operating the PANDA SDL

From the top project directory level run `main.py`. This will begin initializing the system and will show prompts in the command line. The menu will offer the following:

| Menu Option | Sub Option | Function Name                   | Description                                                                                                                     |
| ----------- | ---------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 0           |            | run_experiment                  | Will prompt you for the experiment ID to run and then run that experiment.                                                      |
| 1           |            | run_queue                       | Will show you the current queue and then run all experiments in the queue.                                                      |
| 1           | 1          | stop_panda_sdl                  | Instructs the experiment_worker to stop at the next opportunity.                                                                |
| 1           | 2          | pause_panda_sdl                 | Instructs the experiment_worker to pause at the next opportunity.                                                               |
| 1           | 3          | resume_panda_sdl                | Instructs the experiment_worker to resume from where it paused.                                                                 |
| 2           |            | change_wellplate                | Will prompt you for information about the new wellplate and its location.                                                       |
| 2           | 1          | change_wellplate_location       | Change where the wellplate is located on the deck.                                                                              |
| 2           | 2          | remove_wellplate_from_database  | **Warning: Irreversible!** Deletes a wellplate from the database. Does not delete associated experiments and results.           |
| 2           | 3          | print_wellplate_info            | Prints a description of the current wellplate                                                                                   |
| 2           | 5          | remove_training_data            | Removes training data from an experiment for the associated ML model.                                                           |
| 2           | 6          | clean_up_testing_experiments    | Experiments with project ID 999 will be deleted, even if results exist.                                                         |
| 2           | 7          | update_well_status              | Change the status of a given well                                                                                               |
| 3           |            | reset_vials_stock               | Current stock vials will have their volume set to the vial capacity, and contamination set to 0.                                |
| 3           | 1          | reset_vials_waste               | Current waste vials will have their volume set to zero, contents will be cleared, and contamination set to 0.                   |
| 3           | 2          | input_new_vial_values_stock     | Begins a commandline prompt for changing a stock vial                                                                           |
| 3           | 3          | input_new_vial_values_waste     | Begins a commandline prompt for changing a waste vial                                                                           |
| 3           | 4          | import_vial_data                | Import a .csv file with vial data. Vials listed in the .csv will be marked as active and all current vials will be deactivated. |
| 3           | 5          | generate_vial_data_template     | Save a template vial.csv                                                                                                        |
| 4           |            | print_queue_info                | Does what it says on the tin                                                                                                    |
| 4           | 1          | run_experiment_generator        | Run a specified experiment generator, will print a list of available generators and their IDs.                                  |
| 4           | 2          | remove_experiment_from_database | Remove the specified experiment(s) from the DB if there are no associated results.                                              |
| 5           |            | change_pipette_tip              | Logs that the pipette tip has been changed (incrementing the ID and resetting uses), asks what size.                            |
| 6           |            | mill_calibration                | Begin the mill calibration program.                                                                                             |
| 7           |            | test_image                      | Takes an image with the FLIR camera and shows you.                                                                              |
| 8           |            | instrument_check                | Checks that communication can be established with each instrument.                                                              |
| 10          |            | start_analysis_loop             | Starts the analysis worker. Looks for experiments flagged for analysis and runs their associated analysis scripts.              |
| 10          | 1          | stop_analysis_loop              | Stops the analysis worker.                                                                                                      |
| 10          | 2          | list_analysis_script_ids        | Lists analysis scripts and their IDs.                                                                                           |
| t           |            | toggle_testing_mode             | In testing mode, virtual instruments will be used along with the test_db.db. Useful for validating protocols.                   |
| r           |            | refresh                         | Refresh the main menu.                                                                                                          |
| w           |            | show_warranty                   | Print the warranty                                                                                                              |
| c           |            | show_conditions                 | Print the conditions of the license                                                                                             |
| env         |            | print_config                    | Print the `config.ini` listed in .env                                                                                           |
| q           |            | exit_program                    | Ends the main menu script, halts workers, disconnects from any instruments, and stops monitoring Slack.                         |

## SlackBot (If Using)

Coming soon...

## Protocols

To write a protocol navigate to your protocols directory and create a new `.py ` file with a short unique name such as `abc_experiment name_01.py`.

The script will have at least one function, named "run" which accepts an experiment object and a toolkit object. You are free to add other functions and classes so long as run exists.

Example:
```python
# For writing a protocol, use the available actions and types from the panda_lib library.
from panda_lib import (
    EchemExperimentBase,
    ExperimentStatus,
    Toolkit,
    chrono_amp,
    clear_well,
    flush_pipette,
    image_well,
    rinse_well,
    transfer,
)

# You can have a developer create custom actions for your system or project and save them as actions_name modules in panda_lib
from panda_lib.actions_pgma import cyclic_volt_pgma_fc

# A helper class for solutions is convenient
from dataclasses import dataclass
@dataclass
class Solution:
    name: str
    volume: int
    concentration: float
    repeated: int


def run(experiment, toolkit):
    """Run the experiment."""

    # Use the system logger to note when the experiment starts, can be used for any other events you want to log
    toolkit.global_logger.info("Running experiment: " + experiment.experiment_name)
    
    # Use the helper function to make referencing later on easier
    solution = Solution(
        "solution_name",
        exp.solutions["solution_name"]["volume"],
        exp.solutions["solution_name"]["concentration"],
        exp.solutions["solution_name"]["repetitions"],
    ) 

    # Define the well we are working with for this experiment
    well: Well = toolkit.wellplate.get_well(exp.well_id)

    # Move the camera above the well and take a picture, and label the picture.
    image_well(toolkit, exp, "New Well")

    # Transfer solution from its stock vial into the well
    transfer(solution.volume, solution.name, well, toolkit)
    
    image_well(toolkit, exp, "Well with Solution")

    # Remove all contents from the well into a waste vial
    clear_well(toolkit, well)

    # Flushing the pipette after transferring a sample is good to reduce contamination
    flush_pipette(
        flush_with="solventA rinse",
        toolkit=toolkit,
    )

    # Rinsing can be done with the default rinse prescribed by the experiment 
    rinse_well(
        instructions=exp,
        toolkit=toolkit,
    )

    # or you can define an alternative solution, volume, and repetition
    rinse_well(
        instructions=exp,
        toolkit=toolkit,
        alt_sol_name="solventB rinse",
        alt_vol=120,
        alt_count=4,
    )

    image_well(toolkit, exp, "Rinsed Well")


    toolkit.global_logger.info("Experiment complete")
```

## Generators

Writing generators is relatively simple, however you need to know exactly what the protocol will be expecting, so writing the protocol first is recommended.

Like protocols, generators must have at least one function, this time named "main". 

Example:

```python
"""
Author: Your name
Date: YYYY-MM-DD
Description: 3 series of experiments for polymer-deposition-voltage-screening with 10mm wells, comparing the voltage of the CA.
"""
# Import the experiment type and the scheduler
from panda_lib import EchemExperimentBase, scheduler

PROJECT_ID = 123
EXPERIMENT_NAME = "polymer-deposition-voltage-screening"
CAMPAIGN_ID = 1
PLATE_TYPE = 7  # 10 mm diameter wells on gold
PROTOCOL_NAME = abc_experiment name_01.py # The name of the protocol file you wrote

voltages = [1.0, 1.5, 2.0]
replicates = 3


def main():
    """Runs the experiment generator."""
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments = []

    for voltage in voltages:
        for i in range(replicates):
            experiments.append(
                # Define the experiment variables
                EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_id=PROTOCOL_NAME,
                    well_id="A1", # The desired well if available, will be reassigned automatically if not.
                    plate_type_number=PLATE_TYPE,
                    experiment_name=EXPERIMENT_NAME,
                    project_id=PROJECT_ID,
                    project_campaign_id=CAMPAIGN_ID + i,
                    solutions={
                        "polymer_solution": {
                            "volume": 320,
                            "concentration": 1.0,
                            "repeated": 1,
                        },
                        "solventA rinse": {
                            "volume": 160,
                            "concentration": 1.0,
                            "repeated": 5,
                        },
                        "solventB rinse": {
                            "volume": 160,
                            "concentration": 1.0,
                            "repeated": 9,
                        },
                    },
                    flush_sol_name="solventB rinse",
                    rinse_sol_name="solventB rinse",
                    pumping_rate=0.5,
                    filename=str(experiment_id)+EXPERIMENT_NAME,
                    # Echem specific - define all potentiostat parameters here
                    ocp=1, # Perform 1=yes 0=no
                    baseline=0,
                    cv=1,
                    ca=1,
                    ca_sample_period=0.1,
                    ca_prestep_voltage=0.0,
                    ca_prestep_time_delay=0.0,
                    ca_step_1_voltage=voltage,
                    ca_step_1_time=1200,
                    ca_step_2_voltage=0.0,
                    ca_step_2_time=0.0,
                    ca_sample_rate=0.5,
                    cv_step_size=0.002,
                    cv_first_anodic_peak=1.6,
                    cv_second_anodic_peak=0.0,
                    cv_scan_rate_cycle_1=0.025,
                    cv_scan_rate_cycle_2=0.025,
                    cv_scan_rate_cycle_3=0.025,
                    cv_cycle_count=3,
                    cv_initial_voltage=0.0,
                    cv_final_voltage=0.0,
                    cv_sample_period=0.1,
                    deposition_voltage=voltage,
                )
            )
            experiment_id += 1

    scheduler.add_nonfile_experiments(experiments) # REQUIRED

```

## Analyzers

Coming soon...