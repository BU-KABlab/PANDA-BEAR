"""
The scheduler module will be responsible for:
    - Injesting new experiments
    - Designating experiments to wells
    - Scheduling experiments by priority
    - Inserting control tests
    - Returning the next experiment to run
"""
# pylint: disable = line-too-long
import json
import logging
import os
import pathlib
import random
from datetime import datetime
from experiment_class import Experiment, ExperimentStatus #, make_baseline_value
from configs.pin import CURRENT_PIN

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
system_handler = logging.FileHandler("logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)


class Scheduler:
    """
    Class for scheduling experiments and control tests
    """

    def __init__(self):
        """
        Initialize the scheduler
        """
        self.experiment_queue = []
        self.control_tests = []

    def check_well_status(self, well_to_check: str) -> str:
        """
        Checks the status of a well in the well config file: well_status.json.
        :param well: The well to check.
        :return: The status of the well. Or None if the well is not found.
        """
        file_to_open = pathlib.Path.cwd() / "code" / "system state" / "well_status.json"
        if not pathlib.Path.exists(file_to_open):
            logger.error("well_status.json not found")
            raise FileNotFoundError("well_status.json")

        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            for well in data["Wells"]:
                if well["well_id"] == well_to_check:
                    return well["status"]
                else:
                    continue
            return None

    def choose_alternative_well(self, baseline: bool = False) -> str:
        """
        Chooses an alternative well if the target well is not available.
        :param well: The well to check.
        :param baseline: Whether or not the experiment is a baseline test.
        :return: The alternative well. Or None if no wells are available.
        """
        file_to_open = pathlib.Path.cwd() / "code" / "system state" / "well_status.json"
        if not pathlib.Path.exists(file_to_open):
            logger.error("well_status.json not found")
            raise FileNotFoundError("well_status.json")

        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            for well in data["Wells"]:
                if well["status"] == "new":
                    if baseline:
                        # Baseline tests can only be run in rows 1 or 12
                        if well["well_id"][1] == 1 or well["well_id"][1] == 12:
                            return well["well_id"]
                    return well["well_id"]
            return None

    def change_well_status(self, well: str, status: str) -> None:
        """
        Changes the status of a well in well_status.json.
        :param well: The well to change.
        :param status: The new status of the well.
        """
        file_to_open = pathlib.Path.cwd() / "code" / "system state" / "well_status.json"
        if not pathlib.Path.exists(file_to_open):
            logger.error("well_status.json not found")
            raise FileNotFoundError("well_status.json")

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

    def read_new_experiments(self, filename: str) -> int and bool:
        """
        Reads a JSON file and returns the experiment instructions/recipie as a dictionary.
        :param filename: The name of the JSON file to read.
        :return: number of experiments queued, if any left behind.
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
                if self.check_well_status(desired_well) != "new":
                    # Find the next available well
                    target_well = self.choose_alternative_well(desired_well)
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

                # populate an experiment instance
                # TODO make the planner json output conform to schema so it can just be read in
                instructions = Experiment(
                    id=experiment["id"],
                    pin=CURRENT_PIN,
                    target_well=target_well,
                    dmf=experiment["dmf"],
                    peg=experiment["peg"],
                    acrylate=experiment["acrylate"],
                    ferrocene=experiment["ferrocene"],
                    custom=experiment["custom"],
                    ocp=experiment["ocp"],
                    ca=experiment["ca"],
                    cv=experiment["cv"],
                    baseline=experiment["baseline"],
                    dep_duration=experiment["dep_duration"],
                    dep_pot=experiment["dep_pot"],
                    char_sol_name=experiment["char_sol_name"],
                    char_vol=experiment["char_vol"],
                    flush_sol_name=experiment["flush_sol_name"],
                    flush_vol=experiment["flush_vol"],
                    pumping_rate=experiment["pumping_rate"],
                    rinse_count=experiment["rinse_count"],
                    rinse_vol=experiment["rinse_vol"],
                    status=ExperimentStatus.QUEUED,
                    filename=filename,
                )

                # Save the experiment as a separate file in the experiment_que subfolder
                subfolder_path = cwd / "experiment_queue"
                subfolder_path.mkdir(parents=True, exist_ok=True)
                file_to_save = subfolder_path / filename
                with open(file_to_save, "w", encoding="UTF-8") as outfile:
                    json.dump(instructions, outfile, indent=4)

                # Change the status of the well
                self.change_well_status(target_well, "queued")

                # Add the experiment to the list of experiments read
                experiments_read += 1

        # Save the updated file
        with open(file_to_open, "w", encoding="UTF-8") as file:
            json.dump(data, file, indent=4)

        return experiments_read, complete

    def check_inbox(self) -> int and bool:
        """
        Checks the experiments inbox folder for new experiments.
        :return: the count of new experiments.
        """

        cwd = pathlib.Path(__file__).parents[0]
        file_path = cwd / "experiments_inbox"
        count = 0
        for file in file_path.iterdir():
            # If there are files but 0 added then begin by inserting a baseline test
            # or every tenth experiment
            # if (count == 0) or (count % 9 == 0): # We are currently having the science team insert the baseline tests
            #     self.insert_control_tests()   # so we are not doing this here.

            if file.is_file():
                [count, complete] = self.read_new_experiments(file.name)

                # Move the file to archive if it has been completely read
                if complete:
                    archive_path = file_path / "archive"
                    archive_path.mkdir(parents=True, exist_ok=True)
                    file.replace(archive_path / file.name)
                    print(f"File {file.name} moved to archive.")
                else:
                    print(
                        f"File {file.name} not moved to archive. Not all experiments queued."
                    )

        return count, complete

    # def insert_control_tests(self):
    #     """
    #     Creates a baseline test experiment and saves it to the queue.
    #     Args:
    #         None
    #     Returns:
    #         None
    #     """

    #     ## Insert the baseline tests to the queue directory
    #     target_well = self.choose_alternative_well(baseline=True)
    #     filename = f"{datetime.datetime.now().strftime('%Y-%m-%d')}_baseline_{target_well}.json"
    #     baseline = make_baseline_value()
    #     baseline.target_well = target_well
    #     baseline.filename = filename
    #     ## save the experiment as a separate file in the experiment_queue subfolder
    #     subfolder_path = pathlib.Path.cwd() / "code" / "experiment_queue"
    #     subfolder_path.mkdir(parents=True, exist_ok=True)
    #     file_to_save = subfolder_path / filename
    #     with open(file_to_save, "w", encoding="UTF-8") as outfile:
    #         json.dump(baseline, outfile, indent=4)
    #     ## change the status of the well
    #     self.change_well_status(target_well, "queued")

    def read_next_experiment_from_queue(self) -> tuple(Experiment, pathlib.Path):
        """
        Reads the next experiment from the queue.
        :return: The next experiment.
        """
        file_path = pathlib.Path.cwd() / "code" / "experiment_queue"
        if not pathlib.Path.exists(file_path):
            logger.error("experiment_queue folder not found")
            raise FileNotFoundError("experiment_queue folder")

        ## check if folder is not empty
        if os.listdir(file_path):
            ## if there is a baseline test in the queue run that first

            ## if there are any experiments are in queue pick one at random
            file_list = os.listdir(file_path)
            random_file = random.choice(file_list)
            with open(file_path / random_file, "r", encoding="ascii") as file:
                data = json.load(file)
                if data["baseline"] == 0 and data["status"] == "queued":
                    return data, (file_path / random_file)

        else:
            return None, None