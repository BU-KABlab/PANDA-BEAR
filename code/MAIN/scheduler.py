'''
The scheduler module will be responsible for:
    - Injesting new experiments
    - Designating experiments to wells
    - Scheduling experiments by priority
    - Inserting control tests
    - Returning the next experiment to run
'''
import logging
import time
import experiment_class
import json
import pathlib
from datetime import datetime

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
file_handler = logging.FileHandler("scheduler.log")
system_handler = logging.FileHandler("ePANDA.log")
file_handler.setFormatter(formatter)
system_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(system_handler)

class Scheduler:
    ''' 
    Class for scheduling experiments and control tests
    '''
    def __init__(self):
        '''
        Initialize the scheduler
        '''
        pass

    
def check_well_status(well_to_check: str):
    """
    Checks the status of a well in well_status.json.
    :param well: The well to check.
    :return: The status of the well.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_open = cwd / "well_status.json"
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for well in data["Wells"]:
            if well["well_id"] == well_to_check:
                return well["status"]
            else:
                continue
        return "none"


def choose_alternative_well(well: str):
    """
    Chooses an alternative well if the target well is not available.
    :param well: The well to check.
    :return: The alternative well.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_open = cwd / "well_status.json"
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for well in data["Wells"]:
            if well["status"] == "new":
                return well["well_id"]
        return "none"


def change_well_status(well: str, status: str):
    """
    Changes the status of a well in well_status.json.
    :param well: The well to change.
    :param status: The new status of the well.
    """
    cwd = pathlib.Path(__file__).parents[0]
    file_to_open = cwd / "well_status.json"
    with open(file_to_open, "r", encoding="ascii") as file:
        data = json.load(file)
        for wells in data["Wells"]:
            if wells["well_id"] == well:
                wells["status"] = status
                wells["status_date"] = datetime.datetime.now().strftime(
                    "%Y-%m-%d_%H_%M_%S"
                )
                break
    with open(file_to_open, "w", encoding="ascii") as file:
        json.dump(data, file, indent=4)


    def read_new_experiments(filename: str):
        """
        Reads a JSON file and returns the experiment instructions/recipie as a dictionary.
        :param filename: The name of the JSON file to read.
        :return: The instructions/recipie from the JSON file as a dictionary.
        """
        experiments_read = 0
        complete = True
        cwd = pathlib.Path(__file__).parents[0]
        file_path = cwd / "experiments_inbox"
        file_to_open = file_path / filename
        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            for experiment in data["Experiments"]:
                existing_status = experiment["status"]
                if existing_status != "new":
                    continue
                # Get the experiment id and create a filename
                desired_well = experiment["target_well"]

                # Check if the well is available
                if check_well_status(desired_well) != "new":
                    # Find the next available well
                    target_well = choose_alternative_well(desired_well)
                    if target_well == "none":
                        print(
                            f"No wells available for experiment originally for well {desired_well}."
                        )
                        complete = False
                        continue
                    print(
                        f"Experiment originally for well {desired_well} is now for well {target_well}."
                    )
                    experiment["target_well"] = target_well
                else:
                    target_well = desired_well

                filename = f"{datetime.datetime.now().strftime('%Y-%m-%d')}_experiment-{experiment['id']}_{target_well}.json"

                # add additional information to the experiment
                experiment["filename"] = filename
                experiment["status"] = "queued"
                experiment["status_date"] = "YYYY-MM-DD:HH:MM:SS"
                experiment["time_stamps"] = []
                experiment["OCP_file"] = None
                experiment["OCP_pass"] = None
                experiment["OCP_char_file"] = None
                experiment["OCP_char_pass"] = None
                experiment["deposition_data_file"] = None
                experiment["deposition_plot_file"] = None
                experiment["deposition_max_value"] = None
                experiment["deposition_min_value"] = None
                experiment["characterization_data_file"] = None
                experiment["characterization_plot_file"] = None
                experiment["characterization_max_value"] = None
                experiment["characterization_min_value"] = None

                # Save the experiment as a separate file in the experiment_que subfolder
                subfolder_path = cwd / "experiment_queue"
                subfolder_path.mkdir(parents=True, exist_ok=True)
                file_to_save = subfolder_path / filename
                with open(file_to_save, "w", encoding="UTF-8") as outfile:
                    json.dump(experiment, outfile, indent=4)

                # Change the status of the well
                change_well_status(target_well, "queued")
                experiment["filename"] = filename
                experiment["status"] = "queued"
                experiment["status_date"] = datetime.datetime.now().strftime(
                    "%Y-%m-%d_%H_%M_%S"
                )

                # Add the experiment to the list of experiments read
                experiments_read += 1

        # Save the updated file
        with open(file_to_open, "w", encoding="UTF-8") as file:
            json.dump(data, file, indent=4)

        return experiments_read, complete


    def check_inbox():
        """
        Checks the experiments inbox folder for new experiments.
        :return: the filename(s) of new experiments.
        """

        cwd = pathlib.Path(__file__).parents[0]
        file_path = cwd / "experiments_inbox"
        count = 0
        for file in file_path.iterdir():
            if file.is_file():
                [count, complete] = read_new_experiments(file.name)

                # Move to archive the file if it has been read
                if complete:
                    archive_path = file_path / "archive"
                    archive_path.mkdir(parents=True, exist_ok=True)
                    file.replace(archive_path / file.name)
                    print(f"File {file.name} moved to archive.")
                else:
                    print(
                        f"File {file.name} not moved to archive. Not all experiments read."
                    )

        return count


    def read_next_experiment_from_queue():
        """
        Reads the next experiment from the queue.
        :return: The next experiment.
        """
        cwd = pathlib.Path(__file__).parents[0]
        file_path = cwd / "experiment_queue"

        ## if folder is not empty pick the first file in the queue
        if os.listdir(file_path):
            file_to_open = file_path / os.listdir(file_path)[0]
            with open(file_to_open, "r", encoding="ascii") as file:
                data = json.load(file)
            return data, file_to_open
        else:
            return None, None

