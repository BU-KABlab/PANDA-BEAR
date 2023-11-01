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
from math import exp
import pathlib
from pathlib import Path
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
PATH_TO_EXPERIMENT_INBOX = "code/experiments_inbox"
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
        file_to_open = Path.cwd() / PATH_TO_STATUS / "well_status.json"
        if not Path.exists(file_to_open):
            logger.error("%s not found", file_to_open)
            raise FileNotFoundError("%s not found", file_to_open)

        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            for well in data["wells"]:
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
        file_to_open = Path.cwd() / PATH_TO_STATUS / "well_status.json"
        if not Path.exists(file_to_open):
            logger.error("well_status.json not found")
            raise FileNotFoundError("well_status.json")

        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            for well in data["wells"]:
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
        file_to_open = Path.cwd() / PATH_TO_STATUS/ "well_status.json"
        if not Path.exists(file_to_open):
            logger.error("well_status.json not found")
            raise FileNotFoundError("well_status.json")

        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            for wells in data["wells"]:
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
        inbox_dir = Path.cwd() / PATH_TO_EXPERIMENT_INBOX
        file_to_open = inbox_dir / filename
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

                filename = f"{experiment['id']}_{target_well}.json"

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

                # Save the experiment as a separate file in the experiment_queue subfolder
                queue_dir = Path.cwd() / PATH_TO_EXPERIMENT_QUEUE
                queue_dir.mkdir(parents=True, exist_ok=True)
                file_to_save = queue_dir / filename

                serialized_data = experiment_class.serialize_experiment(instructions)
                with open(file_to_save, "w", encoding="UTF-8") as file:
                    file.write(serialized_data)
                logger.debug("Experiment %s saved to %s", instructions.id, file_to_save)
                # with open(file_to_save, "w", encoding="UTF-8") as outfile:
                #     text_version = json.dumps(instructions)
                #     json.dump(text_version, outfile, indent=4)

                # Add the experiment to the queue
                queue_file_path = Path.cwd() / PATH_TO_QUEUE
                with open(queue_file_path, "a", encoding="UTF-8") as queue_file:
                    line = f"{instructions.id},{instructions.priority},{instructions.filename}"
                    queue_file.write(line)
                    queue_file.write("\n")

                logger.debug("Experiment %s added to queue", instructions.id)
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

        file_path = Path.cwd() / PATH_TO_EXPERIMENT_INBOX
        count = 0
        complete = True
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

    def read_next_experiment_from_queue(self) -> Tuple[Experiment, Path]:
        """
        Reads the next experiment from the queue.
        :return: The next experiment.
        """
        queue_file_path = Path.cwd() / PATH_TO_QUEUE
        ## Starting with the queue.csv file to get the experiment id and filename
        ## The we want to get the experiment with the highest priority (lowest number)
        if not Path.exists(queue_file_path):
            logger.error("queue file not found")
            raise FileNotFoundError("experiment queue file")

        # Read the queue file
        with open(queue_file_path, "r", encoding="ascii") as queue_file:
            queue = queue_file.readlines()

        # Find the highest priority in the queue
        highest_priority = 100
        for line in queue[1:]:
            priority = int(line.split(",")[1])
            if priority < highest_priority:
                highest_priority = priority

        # Get all experiments with the highest priority so that we can randomly select one of them
        experiments = []
        for line in queue[1:]:
            priority = int(line.split(",")[1])
            if priority == highest_priority:
                experiments.append(line.split(",")[2].strip()) # adds the filename to the list of experiments

        if not experiments:
            logger.info("No experiments in queue")
            return None, None

        queue_dir_path = Path.cwd() / PATH_TO_EXPERIMENT_QUEUE
        if not Path.exists(queue_dir_path):
            logger.error("experiment_queue folder not found")
            raise FileNotFoundError("experiment queue folder")

        # Pick a random experiment from the list of experiments with the highest priority
        random_experiment = random.choice(experiments)
        experiment_file_path = Path(queue_dir_path / random_experiment).with_suffix(".json")
        if not Path.exists(experiment_file_path):
            logger.error("experiment file not found")
            raise FileNotFoundError("experiment file")

        # Read the experiment file
        with open(experiment_file_path, "r", encoding="ascii") as experiment_file:
            experiment = json.load(experiment_file)
            experiment = (
                experiment_class.RootModel[Experiment]
                .model_validate_json(json.dumps(experiment))
                .root
            )

        # Remove the selected experiment from the queue
        self.remove_from_queue(experiment)
        logger.info("Experiment %s read from queue", experiment.id)

        return experiment, experiment_file_path

    def remove_from_queue(self, experiment: Experiment) -> None:
        """
        Updates the queue file to remove the experiment that was just run.
        :param experiment: The experiment that was just run.
        """
        file_path = Path.cwd() / PATH_TO_QUEUE
        if not Path.exists(file_path):
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

    def update_experiment_queue_priority(self, experiment_id: int, priority: int):
        """Update the priority of experiments in the queue"""
        queue_file_path = Path.cwd() / PATH_TO_QUEUE
        if not Path.exists(queue_file_path):
            logger.error("queue file not found")
            raise FileNotFoundError("experiment queue file")

        # Read the queue file
        with open(queue_file_path, "r", encoding="ascii") as queue_file:
            queue = queue_file.readlines()

        # Find the experiment in the queue
        for line in queue[1:]:
            if line.split(",")[0] == str(experiment_id):
                # Update the priority
                line.split(",")[1] = str(priority)

        # Rewrite the queue csv file
        with open(queue_file_path, "w", encoding="ascii") as file:
            for line in queue:
                file.write(line)
                file.write("\n")


    def update_experiment_status(self, experiment: Experiment) -> None:
        """
        Updates the status of the experiment in the experiment instructions file.
        :param experiment: The experiment that was just run.
        """
        file_path = (Path.cwd() / PATH_TO_EXPERIMENT_QUEUE / experiment.filename).with_suffix(".json")
        if not Path.exists(file_path):
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

        logger.info("Experiment %s status changed to %s", experiment.id, experiment.status)

    def update_experiment_location(self, experiment: Experiment) -> None:
        """
        Updates the location of the experiment instructions file.
        :param experiment: The experiment that was just run.
        """
        file_name_with_suffix = Path(experiment.filename).with_suffix(".json")
        file_path = Path(
            Path.cwd() / PATH_TO_EXPERIMENT_QUEUE / file_name_with_suffix.name
        )
        if not Path.exists(file_path):
            logger.error("experiment file not found")
            raise FileNotFoundError("experiment file")

        if experiment.status == ExperimentStatus.COMPLETE:
            # Move the file to the completed folder
            completed_path = Path.cwd() / PATH_TO_COMPLETED_EXPERIMENTS
            file_path.replace(completed_path / file_name_with_suffix)

        elif experiment.status == ExperimentStatus.ERROR:
            # Move the file to the errored folder
            errored_path = Path.cwd() / PATH_TO_ERRORED_EXPERIMENTS
            file_path.replace(errored_path / file_name_with_suffix)

        else:
            # If the experiment is neither complete nor errored, then we need to keep it in the queue
            logger.info(
                "Experiment %s is not complete or errored, keeping in queue",
                experiment.id,
            )

        logger.info("Experiment %s location updated to %s", experiment.id, experiment.status)

    def add_nonfile_experiment(self, experiment: Experiment) -> None:
        """
        Adds an experiment which is not a file to the experiment queue.
        :param experiment: The experiment to add.
        """
        # Save the new experiment to a file in the inbox folder
        file_path = pathlib.Path.cwd() / PATH_TO_EXPERIMENT_INBOX / experiment.filename
        experiment_json = experiment_class.serialize_experiment(experiment)
        with open(file_path.with_suffix(".json"), "w", encoding="UTF-8") as file:
            file.write(experiment_json)

        # read the experiment to the queue
        self.read_new_experiments(experiment.filename)

    def save_results(self, experiment: Experiment, results: ExperimentResult) -> None:
        """Save the results of the experiment as a json file in the data folder
        Args:
            experiment (Experiment): The experiment that was just run
            results (ExperimentResult): The results of the experiment

        Returns:
            None
        """
        # Save the results
        filename_with_suffix = Path(experiment.filename).with_suffix(".json")
        filename = filename_with_suffix.name
        logger.info("Saving experiment %d results to database as %s", experiment.id, str(filename))
        results_json = experiment_class.serialize_results(results)
        with open(
            Path.cwd() / "data" / f"{experiment.id}.json", "w", encoding="UTF-8"
        ) as results_file:
            results_file.write(results_json)


####################################################################################################
def test_well_status_update():
    """
    Tests the change_well_status function.
    """
    scheduler = Scheduler()
    current_status = scheduler.check_well_status("A1")
    scheduler.change_well_status("A1", "running")
    assert scheduler.check_well_status("A1") == "running"
    scheduler.change_well_status("A1", "complete")
    assert scheduler.check_well_status("A1") == "complete"
    scheduler.change_well_status("A1", "new")
    assert scheduler.check_well_status("A1") == "new"
    scheduler.change_well_status("A1", current_status)


if __name__ == "__main__":
    test_well_status_update()
