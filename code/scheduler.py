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
from typing import Tuple
import experiment_class
from experiment_class import (
    Experiment,
    ExperimentStatus,
    ExperimentResult,
)  # , make_baseline_value
from config.pin import CURRENT_PIN

# define constants or globals
PATH_TO_CONFIG = "code/config/mill_config.json"
PATH_TO_STATUS = "code/system state"
PATH_TO_QUEUE = "code/system state/queue.csv"
PATH_TO_EXPERIMENT_QUEUE = "code/experiment_queue"
PATH_TO_COMPLETED_EXPERIMENTS = "code/experiments_completed"
PATH_TO_ERRORED_EXPERIMENTS = "code/experiments_error"

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
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

    def change_well_status(self, well: str, status: str, status_date: str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), experiment_id: int = None) -> None:
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
                    wells["status_date"] = status_date
                    wells["experiment_id"] = experiment_id
                    break
        with open(file_to_open, "w", encoding="ascii") as file:
            json.dump(data, file, indent=4)

        logger.info("Well %s status changed to %s", well, status)

    def read_new_experiments(self, filename: str) -> Tuple[int, bool]:
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

                filename = f"{datetime.now().strftime('%Y-%m-%d')}_experiment-{experiment['id']}_{target_well}.json"

                # populate an experiment instance
                # TODO make the planner json output conform to schema so it can just be read in
                instructions = Experiment(
                    id=experiment["id"],
                    priority=experiment["priority"],
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

                # Add the experiment to the queue
                queue_file_path = "code" / "system state" / "queue.csv"
                with open(queue_file_path, "a", encoding="UTF-8") as queue_file:
                    line = f"{instructions.id},{instructions.priority},{instructions.filename}"
                    queue_file.write(line)

                # Change the status of the well
                self.change_well_status(target_well, "queued")

                # Add the experiment to the list of experiments read
                experiments_read += 1

        # Save the updated file
        with open(file_to_open, "w", encoding="UTF-8") as file:
            json.dump(data, file, indent=4)

        return experiments_read, complete

    def check_inbox(self) -> Tuple[int, bool]:
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

    def read_next_experiment_from_queue(self) -> Tuple[Experiment, pathlib.Path]:
        """
        Reads the next experiment from the queue.
        :return: The next experiment.
        """
        file_path = pathlib.Path.cwd() / "code" / "system state" / "queue.csv"
        if not pathlib.Path.exists(file_path):
            logger.error("queue file not found")
            raise FileNotFoundError("experiment queue file")

        file_path = pathlib.Path.cwd() / "code" / "experiment_queue"
        if not pathlib.Path.exists(file_path):
            logger.error("experiment_queue folder not found")
            raise FileNotFoundError("experiment queue folder")

        # check if folder is not empty
        if os.listdir(file_path):
            # if there is a baseline test in the queue run that first

            # if there are any experiments are in queue pick one at random
            file_list = os.listdir(file_path)
            count = 0
            while count < len(file_list):
                random_file = random.choice(file_list)
                count += 1
                with open(file_path / random_file, "r", encoding="ascii") as file:
                    data = json.load(file)
                    if data["baseline"] == 0 and data["status"] in ["queued","new"]:
                        data = (
                            experiment_class.RootModel[Experiment]
                            .model_validate_json(json.dumps(data))
                            .root
                        )
                        return data, (file_path / random_file)

        else:
            return None, None

    def update_queue(self, experiment: Experiment) -> None:
        """
        Updates the queue file to remove the experiment that was just run.
        :param experiment: The experiment that was just run.
        """
        file_path = pathlib.Path.cwd() / "code" / "system state" / "queue.csv"
        if not pathlib.Path.exists(file_path):
            logger.error("queue file not found")
            raise FileNotFoundError("experiment queue file")

        # Read the queue file
        with open(file_path, "r", encoding="ascii") as file:
            data = file.readlines()

        # Remove the experiment from the queue file
        with open(file_path, "w", encoding="ascii") as file:
            for line in data:
                if line.split(",")[0] != experiment.id:
                    file.write(line)

    def update_experiment_status(self, experiment: Experiment) -> None:
        """
        Updates the status of the experiment in the experiment instructions file.
        :param experiment: The experiment that was just run.
        """
        file_path = (pathlib.Path.cwd() / PATH_TO_EXPERIMENT_QUEUE / experiment.filename).with_suffix(".json")
        if not pathlib.Path.exists(file_path):
            logger.error("experiment file not found")
            raise FileNotFoundError("experiment file")

        # Update the status of the experiment
        with open(file_path, "r", encoding="UTF-8") as file:
            data = json.load(file)
            data = json.dumps(data)
            parsed_data = experiment_class.parse_experiment(data)
            parsed_data.status = str(experiment.status.value)
            parsed_data.status_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # Save the updated file
        serialized_data = experiment_class.serialize_experiment(parsed_data)
        with open(file_path, "w", encoding="UTF-8") as file:
            file.write(serialized_data)

    def update_experiment_location(self, experiment: Experiment) -> None:
        """
        Updates the location of the experiment instructions file.
        :param experiment: The experiment that was just run.
        """
        file_name_with_suffix = experiment.filename + ".json"
        file_path = pathlib.Path(
            pathlib.Path.cwd() / PATH_TO_EXPERIMENT_QUEUE / file_name_with_suffix
        )
        if not pathlib.Path.exists(file_path):
            logger.error("experiment file not found")
            raise FileNotFoundError("experiment file")

        if experiment.status == ExperimentStatus.COMPLETE:
            # Move the file to the completed folder
            completed_path = pathlib.Path.cwd() / PATH_TO_COMPLETED_EXPERIMENTS
            file_path.replace(completed_path / file_name_with_suffix)

        elif experiment.status == ExperimentStatus.ERROR:
            # Move the file to the errored folder
            errored_path = pathlib.Path.cwd() / PATH_TO_ERRORED_EXPERIMENTS
            file_path.replace(errored_path / file_name_with_suffix)

        else:
            # If the experiment is neither complete nor errored, then we need to keep it in the queue
            logger.info(
                "Experiment %s is not complete or errored, keeping in queue",
                experiment.id,
            )
    def add_experiment(self, experiment: Experiment) -> None:
        """
        Adds an experiment to the experiment queue.
        :param experiment: The experiment to add.
        """
        file_path = pathlib.Path.cwd() / PATH_TO_EXPERIMENT_QUEUE / experiment.filename
        # Save the updated file
        experiment_json = experiment_class.serialize_experiment(experiment)
        with open(file_path.with_suffix(".json"), "w", encoding="UTF-8") as file:
            file.write(experiment_json)

    def save_results(self, experiment: Experiment, results: ExperimentResult) -> None:
        """Save the results of the experiment as a json file in the data folder
        Args:
            experiment (Experiment): The experiment that was just run
            results (ExperimentResult): The results of the experiment

        Returns:
            None
        """
        # Save the results
        logger.info("Saving experiment %d results to database as %s", experiment.id, str(experiment.filename) + ".json")
        results_json = experiment_class.serialize_results(results)
        with open(
            pathlib.Path.cwd() / "data" / f"{experiment.id}.json", "w", encoding="UTF-8"
        ) as results_file:
            results_file.write(results_json)


####################################################################################################
def test_well_status_update():
    """
    Tests the change_well_status function.
    """
    scheduler = Scheduler()
    scheduler.change_well_status("A1", "running")
    assert scheduler.check_well_status("A1") == "running"
    scheduler.change_well_status("A1", "complete")
    assert scheduler.check_well_status("A1") == "complete"
    scheduler.change_well_status("A1", "new")
    assert scheduler.check_well_status("A1") == "new"


if __name__ == "__main__":
    test_well_status_update()
