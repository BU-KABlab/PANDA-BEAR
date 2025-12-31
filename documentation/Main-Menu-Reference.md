# Main Menu Reference

Complete reference for all PANDA-BEAR command-line interface menu options and functions.

**Navigation**: [Home](00-Home.md) | [Getting Started](01%20Getting-Started.md) | Main Menu Reference | [API Reference](API-Reference.md)

## Table of Contents

- [Main Menu Overview](#main-menu-overview)
- [Menu Options](#menu-options)
- [Common Workflows](#common-workflows)
- [Keyboard Shortcuts](#keyboard-shortcuts)

## Main Menu Overview

To access the main menu, run `python main.py` from the project root directory. The menu will present you with various options for controlling the PANDA system.

## Menu Options

| Option  | Sub-Option | Function Name                     | Description                                                                                                                      |
| ------- | ---------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **0**   |            | `run_experiment`                  | Prompts for an experiment ID and runs that specific experiment.                                                                  |
| **1**   |            | `run_queue`                       | Displays the current queue and runs all experiments in the queue.                                                                |
| **1**   | **1**      | `stop_panda_sdl`                  | Instructs the experiment worker to stop at the next opportunity.                                                                 |
| **1**   | **2**      | `pause_panda_sdl`                 | Instructs the experiment worker to pause at the next opportunity.                                                                |
| **1**   | **3**      | `resume_panda_sdl`                | Instructs the experiment worker to resume from where it paused.                                                                  |
| **2**   |            | `change_wellplate`                | Prompts for information about the new wellplate and its location.                                                                |
| **2**   | **1**      | `change_wellplate_location`       | Changes where the wellplate is located on the deck.                                                                              |
| **2**   | **2**      | `remove_wellplate_from_database`  | **Warning: Irreversible!** Deletes a wellplate from the database. Does not delete associated experiments and results.            |
| **2**   | **3**      | `print_wellplate_info`            | Prints a description of the current wellplate.                                                                                   |
| **2**   | **5**      | `remove_training_data`            | Removes training data from an experiment for the associated ML model.                                                            |
| **2**   | **6**      | `clean_up_testing_experiments`    | Deletes experiments with project ID 999, even if results exist.                                                                  |
| **2**   | **7**      | `update_well_status`              | Changes the status of a given well.                                                                                              |
| **3**   |            | `reset_vials_stock`               | Sets stock vial volumes to capacity and contamination to 0.                                                                      |
| **3**   | **1**      | `reset_vials_waste`               | Sets waste vial volumes to zero, clears contents, and sets contamination to 0.                                                   |
| **3**   | **2**      | `input_new_vial_values_stock`     | Begins a command line prompt for changing a stock vial.                                                                          |
| **3**   | **3**      | `input_new_vial_values_waste`     | Begins a command line prompt for changing a waste vial.                                                                          |
| **3**   | **4**      | `import_vial_data`                | Imports a .csv file with vial data. Vials listed in the .csv will be marked as active and all current vials will be deactivated. |
| **3**   | **5**      | `generate_vial_data_template`     | Saves a template vial.csv file.                                                                                                  |
| **4**   |            | `print_queue_info`                | Displays information about the current experiment queue.                                                                         |
| **4**   | **1**      | `run_experiment_generator`        | Runs a specified experiment generator, displaying available generators and their IDs.                                            |
| **4**   | **2**      | `remove_experiment_from_database` | Removes specified experiment(s) from the database if there are no associated results.                                            |
| **5**   |            | `change_pipette_tip`              | Logs that the pipette tip has been changed (incrementing the ID and resetting uses), asks what size.                             |
| **6**   |            | `mill_calibration`                | Begins the mill calibration program.                                                                                             |
| **7**   |            | `test_image`                      | Takes an image with the FLIR camera and displays it.                                                                             |
| **8**   |            | `instrument_check`                | Checks that communication can be established with each instrument.                                                               |
| **10**  |            | `start_analysis_loop`             | Starts the analysis worker, which looks for experiments flagged for analysis and runs their associated analysis scripts.         |
| **10**  | **1**      | `stop_analysis_loop`              | Stops the analysis worker.                                                                                                       |
| **10**  | **2**      | `list_analysis_script_ids`        | Lists analysis scripts and their IDs.                                                                                            |
| **t**   |            | `toggle_testing_mode`             | Toggles testing mode, which uses virtual instruments and test_db.db. Useful for validating protocols.                            |
| **r**   |            | `refresh`                         | Refreshes the main menu display.                                                                                                 |
| **w**   |            | `show_warranty`                   | Displays the warranty information.                                                                                               |
| **c**   |            | `show_conditions`                 | Displays the conditions of the license.                                                                                          |
| **env** |            | `print_config`                    | Displays the `config.ini` settings listed in .env file.                                                                          |
| **q**   |            | `exit_program`                    | Exits the main menu script, halts workers, disconnects from any instruments, and stops monitoring Slack.                         |

## Common Workflows

Here are some common workflows using the main menu:

### Running Experiments

1. Generate experiments:
   - Press `4`, then `1`
   - Select your generator ID
   - The system will create and queue experiments

2. Run experiments:
   - Press `1` to run all queued experiments
   - Or press `0` to run a specific experiment by ID

### Managing Wellplates

1. Change wellplate:
   - Press `2`
   - Follow the prompts to provide information about the new wellplate

2. View wellplate info:
   - Press `2`, then `3`
   - The system will display the current wellplate information

### Managing Vials

1. Reset stock vials:
   - Press `3`
   - All stock vials will have their volume reset to capacity

2. Import vial data:
   - Press `3`, then `4`
   - Provide the path to your vial data CSV file

### Running Analysis

1. Start analysis:
   - Press `10`
   - The system will begin analyzing completed experiments

2. Stop analysis:
   - Press `10`, then `1`
   - The analysis worker will be stopped

## Testing and Validation

The testing mode is particularly useful for new users or when developing new protocols:

1. Toggle testing mode:
   - Press `t`
   - The system will switch to using virtual instruments

2. Test camera:
   - Press `7`
   - The system will take a test image with the camera

3. Check instruments:
   - Press `8`
   - The system will check connectivity with all instruments

## Best Practices

1. Always start with instrument checks (`8`) before running experiments.

2. Use testing mode (`t`) when developing or testing new protocols.

3. Regularly check queue information (`4`) to monitor experiment status.

4. When finished, always exit properly (`q`) to ensure all resources are properly released.

5. Use the analysis loop (`10`) for automated analysis of completed experiments.

6. Keep track of vial volumes to avoid running out of solutions during experiments.

## Troubleshooting

If you encounter issues:

1. Check the logs in the `logs_test/` directory for error messages.

2. Verify that all instruments are properly connected and powered on.

3. Restart the PANDA-BEAR system if you encounter unexpected behavior.

4. Ensure your configuration files (.env and config.ini) are correctly set up.

5. Check that vials have sufficient volumes for your planned experiments.

6. Verify that the wellplate is properly installed and configured in the system.

## Next Steps

After familiarizing yourself with the main menu, you may want to:

- Review [Getting Started](01%20Getting-Started.md) for basic system usage
- Learn to [write protocols](03%20Writing-Protocols.md) for custom experiments
- Create [generators](02%20Creating-Generators.md) for batch experiments
- Consult the [API Reference](API-Reference.md) for programmatic usage
