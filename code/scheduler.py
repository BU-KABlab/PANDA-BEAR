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
import random
from datetime import datetime
from pathlib import Path
from typing import Tuple

import experiment_class
import pandas as pd
from config.config import (EPANDA_LOG, PATH_TO_COMPLETED_EXPERIMENTS,
                           PATH_TO_DATA, PATH_TO_ERRORED_EXPERIMENTS,
                           PATH_TO_EXPERIMENT_INBOX, PATH_TO_EXPERIMENT_QUEUE)
from config.config import QUEUE as PATH_TO_QUEUE
from config.config import WELL_STATUS
from experiment_class import ExperimentBase, ExperimentResult, ExperimentStatus
from wellplate import Well

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&&&&%(message)s&")
system_handler = logging.FileHandler(EPANDA_LOG)
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
        file_to_open = WELL_STATUS
        if not Path.exists(file_to_open):
            logger.error("%s not found", file_to_open)
            raise FileNotFoundError(f"{file_to_open.stem} not found")

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
        logger.debug("Choosing alternative well")
        file_to_open = WELL_STATUS
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

    def change_well_status(self, well: str, experiment: ExperimentBase) -> None:
        """
        Changes the status of a well in well_status.json.
        :param well: The well to change.
        :param status: The new status of the well.
        """
        logger.debug("Changing well %s status to %s", well, experiment.status.value)
        file_to_open = WELL_STATUS
        if not Path.exists(file_to_open):
            logger.error("well_status.json not found")
            raise FileNotFoundError("well_status.json")

        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            for wells in data["wells"]:
                if wells["well_id"] == well:
                    wells["status"] = experiment.status
                    wells["status_date"] = experiment.status_date.strftime("%Y-%m-%dT%H:%M:%S")
                    wells["experiment_id"] = experiment.id
                    wells["project_id"] = experiment.project_id
                    break
        with open(file_to_open, "w", encoding="ascii") as file:
            json.dump(data, file, indent=4)

        logger.info("Well %s status changed to %s", well, experiment.status.value)

    def change_well_status_v2(self, well: Well, experiment: ExperimentBase) -> None:
        """
        Changes the status of a well in well_status.json.
        :param well: The well to change.
        :param status: The new status of the well.
        """
        logger.debug("Changing %s status to %s", well, well.status)

        well.status = experiment.status.value
        well.status_date = experiment.status_date

        file_to_open = WELL_STATUS
        if not Path.exists(file_to_open):
            logger.error("well_status.json not found")
            raise FileNotFoundError("well_status.json")

        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            for wells in data["wells"]:
                if wells["well_id"] == well.well_id:
                    wells["status"] = well.status
                    wells["status_date"] = well.status_date.strftime("%Y-%m-%dT%H:%M:%S")
                    wells["experiment_id"] = well.experiment_id
                    wells["project_id"] = well.project_id
                    wells['contents'] = well.contents
                    break
        with open(file_to_open, "w", encoding="ascii") as file:
            json.dump(data, file, indent=4)

        logger.info("%s status changed to %s", well, well.status)

    def ingest_inbox_experiments(self, filename: str) -> Tuple[int, bool]:
        """
        Reads a JSON file and returns the experiment instructions/recipie as a dictionary.
        :param filename: The name of the JSON file to read.
        :return: number of experiments queued, if any left behind.
        """
        experiments_read = 0
        complete = True
        inbox_dir = PATH_TO_EXPERIMENT_INBOX
        file_to_open = (inbox_dir / filename).with_suffix(".json")
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
                    logger.info(
                        "No wells available for experiment originally for well %s" ,desired_well
                    )
                    complete = False
                    continue
                logger.info(
                    "Experiment originally for well %s is now for well %s", desired_well, target_well
                )
                experiment["target_well"] = target_well
            else:
                target_well = desired_well

            filename = f"{experiment['id']}.json"

            # populate an experiment instance
            instructions = experiment_class.RootModel[ExperimentBase].model_validate_json(json.dumps(experiment)).root

            # Save the experiment as a separate file in the experiment_queue subfolder
            queue_dir = PATH_TO_EXPERIMENT_QUEUE
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
            queue_file_path = PATH_TO_QUEUE
            with open(queue_file_path, "a", encoding="UTF-8") as queue_file:
                line = f"{instructions.id},{instructions.priority},{instructions.filename},{instructions.protocol_type}"
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

        file_path = PATH_TO_EXPERIMENT_INBOX
        count = 0
        complete = True
        for file in file_path.iterdir():
            # If there are files but 0 added then begin by inserting a baseline test
            # or every tenth experiment
            # if (count == 0) or (count % 9 == 0): # We are currently having the science team insert the baseline tests
            #     self.insert_control_tests()   # so we are not doing this here.

            if file.is_file():
                logger.info("Reading file %s for experiments", file.name)
                count, complete = self.ingest_inbox_experiments(file.name)

                # Move the file to archive if it has been completely read
                if complete:
                    logger.debug("Moving file %s to archive", file.name)
                    archive_path = file_path / "archive"
                    archive_path.mkdir(parents=True, exist_ok=True)
                    file.replace(archive_path / file.name)
                    logger.info("File %s moved to archive.", file.name)
                else:
                    logger.info("File %s not moved to archive. Not all experiments queued.", file.name)

        return count, complete

    def read_next_experiment_from_queue(self, random_pick: bool = True) -> Tuple[ExperimentBase, Path]:
        """
        Reads the next experiment from the queue.
        :return: The next experiment.
        """
        queue_file_path = PATH_TO_QUEUE
        ## Starting with the queue.csv file to get the experiment id and filename
        ## The we want to get the experiment with the highest priority (lowest number)
        if not Path.exists(queue_file_path):
            logger.error("queue file not found")
            raise FileNotFoundError("experiment queue file")

        # Read the queue file
        # with open(queue_file_path, "r", encoding="ascii") as queue_file:
        #     queue = queue_file.readlines()

        queue = pd.read_csv(queue_file_path, header=0, names=["id", "priority", "filename","protocol_type"], dtype={"id": int, "priority": int, "filename": str, "protocol_type":int}, skipinitialspace=True)
        if queue.empty:
            logger.info("No experiments in queue")
            return None, None

        highest_priority = queue["priority"].min()
        # Get all experiments with the highest priority so that we can randomly select one of them
        # Exclude layered protocols (protocol_type = 2)
        experiments = queue[(queue["priority"] == highest_priority) & (queue["protocol_type"] != 2)]["filename"]
        experiments_list = experiments.tolist()
        if not Path.exists(PATH_TO_EXPERIMENT_QUEUE):
            logger.error("experiment_queue folder not found")
            raise FileNotFoundError("experiment queue folder")

        if random_pick:
            # Pick a random experiment from the list of experiments with the highest priority
            random_experiment = random.choice(experiments_list)
            experiment_file_path = Path(PATH_TO_EXPERIMENT_QUEUE / random_experiment).with_suffix(".json")
            if not Path.exists(experiment_file_path):
                logger.error("experiment file not found")
                raise FileNotFoundError("experiment file")
        else:
            # Sort the queue by experiment id and then by priority, excluding type 2 protocols
            queue = queue.sort_values(by=["id", "priority"], ascending=[True, True])
            queue = queue[queue["protocol_type"] != 2]
            # Get the first experiment in the queue
            experiment_file_path = Path(PATH_TO_EXPERIMENT_QUEUE / queue["filename"].iloc[0]).with_suffix(".json")
            if not Path.exists(experiment_file_path):
                logger.error("experiment file not found")
                raise FileNotFoundError("experiment file")

        # Read the experiment file
        with open(experiment_file_path, "r", encoding="ascii") as experiment_file:
            # experiment = json.load(experiment_file)
            # experiment = (
            #     experiment_class.RootModel[ExperimentBase]
            #     .model_validate_json(json.dumps(experiment))
            #     .root
            # )
            experiment = experiment_class.parse_experiment(experiment_file.read())
        # Remove the selected experiment from the queue
        self.remove_from_queue(experiment)
        logger.info("Experiment %s read from queue", experiment.id)

        return experiment, experiment_file_path

    def remove_from_queue(self, experiment: ExperimentBase) -> None:
        """
        Updates the queue file to remove the experiment that was just run.
        :param experiment: The experiment that was just run.
        """
        file_path = PATH_TO_QUEUE
        if not Path.exists(file_path):
            logger.error("queue file not found")
            raise FileNotFoundError("experiment queue file")

        # Read the queue file
        queue = pd.read_csv(file_path, header=0, names=["id", "priority", "filename", "protocol_type"], dtype={"id": int, "priority": int, "filename": str, "protocol_type":int}, skipinitialspace=True)

        # Remove the experiment from the queue file
        queue = queue[queue["id"] != experiment.id]
        queue.to_csv(file_path, index=False)

    def update_experiment_queue_priority(self, experiment_id: int, priority: int):
        """Update the priority of experiments in the queue"""
        queue_file_path = PATH_TO_QUEUE
        if not Path.exists(queue_file_path):
            logger.error("queue file not found")
            raise FileNotFoundError("experiment queue file")

        # Read the queue file
        queue = pd.read_csv(queue_file_path, header=0, names=["id", "priority", "filename","protocol_type"], dtype={"id": int, "priority": int, "filename": str, "protocol_type":int}, skipinitialspace=True)

        # Find the experiment in the queue
        queue.loc[queue["id"] == experiment_id, "priority"] = priority

        # Rewrite the queue csv file
        queue.to_csv(queue_file_path, index=False)

    def update_experiment_file(self, experiment: ExperimentBase) -> None:
        """
        Updates the status of the experiment in the experiment instructions file.
        Args:
            experiment (ExperimentBase): The experiment to update

        Returns:
            None
        """
        file_path = (PATH_TO_EXPERIMENT_QUEUE / experiment.filename).with_suffix(".json")
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

        logger.info("Experiment %s status changed to %s", experiment.id, experiment.status.value)

    def update_experiment_location(self, experiment: ExperimentBase) -> None:
        """
        Updates the location of the experiment instructions file based on status.
        Args:
            experiment (ExperimentBase): The experiment to update.
        
        Returns:
            None
        """
        file_name_with_suffix = Path(experiment.filename).with_suffix(".json")
        file_path = Path(
            PATH_TO_EXPERIMENT_QUEUE / file_name_with_suffix.name
        )
        if not Path.exists(file_path):
            logger.error("experiment file not found")
            raise FileNotFoundError("experiment file")

        if experiment.status == ExperimentStatus.COMPLETE:
            # Move the file to the completed folder
            completed_path = PATH_TO_COMPLETED_EXPERIMENTS
            file_path.replace(completed_path / file_name_with_suffix)

        elif experiment.status == ExperimentStatus.ERROR:
            # Move the file to the errored folder
            errored_path = PATH_TO_ERRORED_EXPERIMENTS
            file_path.replace(errored_path / file_name_with_suffix)

        else:
            # If the experiment is neither complete nor errored, then we need to keep it in the queue
            # and add it back to the queue file
            experiment = self.add_to_queue_file(experiment)
            logger.info(
                "Experiment %s is not complete or errored, keeping in queue",
                experiment.id,
            )

        logger.info("Experiment %s location updated to %s", experiment.id, experiment.status.value)

    def add_nonfile_experiment(self, experiment: ExperimentBase, override_well_available = False) -> str:
        """
        Adds an experiment which is not a file to the experiment queue directly.
        
        Args:
            experiment (ExperimentBase): The experiment to add.

        Returns:
            str: A message indicating whether the experiment was successfully added to the queue.
        """
        if not override_well_available:
            ## First check the existing status, if not new or queued, then do not add to queue
            if experiment.status not in [ExperimentStatus.NEW, ExperimentStatus.QUEUED]:
                message = f"Experiment {experiment.id} is not new or queued, not adding to queue"
                logger.info(message)
                return message

            ## Check if the well is available
            if self.check_well_status(experiment.well_id) != "new":
                # Find the next available well
                target_well = self.choose_alternative_well(experiment.well_id)
                if target_well is None:
                    logger.info(
                        "No wells available for experiment originally for well %s.",
                        experiment.well_id
                    )
                    return "No wells available"
                logger.info(
                    "Experiment originally for well %s is now for well %s.",
                    experiment.well_id,
                    target_well
                )
                experiment.well_id = target_well

        # Save the experiment as a separate file in the experiment_queue subfolder
        experiment.status = ExperimentStatus.QUEUED
        experiment = self.add_to_queue_folder(experiment)

        ## Add the experiment to the queue
        experiment = self.add_to_queue_file(experiment)

        ## Change the status of the well
        self.change_well_status(experiment.well_id, experiment)

        logger.info("Experiment %s added to queue", experiment.id)
        return "success"

    def add_to_queue_folder(self, experiment: ExperimentBase) -> ExperimentBase:
        """Add the given experiment to the experiment_queue folder"""
        queue_dir = PATH_TO_EXPERIMENT_QUEUE
        file_to_save = (queue_dir / experiment.filename).with_suffix(".json")
        with open(file_to_save, "w", encoding="UTF-8") as file:
            serialized_data = experiment_class.serialize_experiment(experiment)
            file.write(serialized_data)
        return experiment

    def add_to_queue_file(self, experiment: ExperimentBase) -> ExperimentBase:
        """Add the given experiment to the queue.csv"""
        queue_file_path = PATH_TO_QUEUE
        if not Path.exists(queue_file_path):
            logger.error("queue file not found")
            raise FileNotFoundError("experiment queue file")

        # Read the queue file
        # Add the experiment to the queue
        new_row = {"id": experiment.id, "priority": experiment.priority, "filename": experiment.filename, "protocol_type": experiment.protocol_type}
        df = pd.DataFrame(new_row, index=[0])

        # Write the updated queue to the csv file
        df.to_csv(queue_file_path,mode='a', index=False, header=False)
        experiment.status = ExperimentStatus.QUEUED
        return experiment

    def add_nonfile_experiments(self, experiments: list[ExperimentBase]) -> str:
        """
        Adds a list of experiments which are not files to the experiment queue directly.
        :param experiments: The experiments to add.
        """
        for experiment in experiments:
            response = self.add_nonfile_experiment(experiment, override_well_available=experiment.override_well_selection)
            if response != "success":
                print(response)
                logger.warning(response)
                return 0
        return 1

    def save_results(self, experiment: ExperimentBase, results: ExperimentResult) -> None:
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
            Path(PATH_TO_DATA) / f"{experiment.id}.json", "w", encoding="UTF-8"
        ) as results_file:
            results_file.write(results_json)

    def count_available_wells(self) -> int:
        """Return the number of wells available for experiments

        Returns:
            int: the number of experiments we can queue from the inbox
        """
        file_to_open = WELL_STATUS
        if not Path.exists(file_to_open):
            logger.error("well_status.json not found")
            raise FileNotFoundError("well_status.json")

        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            count = 0
            for wells in data["wells"]:
                if wells["status"] == "new":
                    count += 1
            return count

    def generate_layered_protocol_experiment_list(self) -> list[ExperimentBase]:
        """Generate a list of experiments for a layered protocol
        
        This method will run through the queue and generate a list of experiments that can be run together given the current well availability.
        It will avoid running experiments that require the same well.

        Layered protocols are identified as protocol_type = 2 in the queue.csv file and the experiment object.

        Along with returning the list, all of theses experiments will be removed from the queue.csv file and the experiment_queue folder as they will be run all together.

        Returns:
            list: a list of experiments
        """
        # Read the queue file
        queue_file_path = PATH_TO_QUEUE
        if not Path.exists(queue_file_path):
            logger.error("queue file not found")
            raise FileNotFoundError(f"experiment queue file {queue_file_path.stem}")

        queue_df = pd.read_csv(queue_file_path, header=0, names=["id", "priority", "filename","protocol_type"], dtype={"id": int, "priority": int, "filename": str, "protocol_type":int}, skipinitialspace=True)

        # Get the list of experiments that are in the queue and are layered protocols
        layered_queue = queue_df[(queue_df["protocol_type"] == 2)]["id"].tolist()

        # Filter the the layered_queue to only include experiments for wells that are available
        # First get the list of available wells
        available_wells = []
        file_to_open = WELL_STATUS
        if not Path.exists(file_to_open):
            logger.error("well_status.json not found")
            raise FileNotFoundError(f"{file_to_open.stem} not found")

        with open(file_to_open, "r", encoding="ascii") as file:
            data = json.load(file)
            for wells in data["wells"]:
                if wells["status"] == "new":
                    available_wells.append(wells["well_id"])

        # Now filter the layered_queue to only include experiments for wells that are available
        # This involves openening each experiment file and checking the target well since the filenames are just the experiment id
        filtered_layered_queue = []
        for experiment_id in layered_queue:
            experiment_file_path = PATH_TO_EXPERIMENT_QUEUE / f"{experiment_id}.json"
            if not Path.exists(experiment_file_path):
                logger.error("experiment file not found")
                raise FileNotFoundError(f"experiment file {experiment_file_path.stem}")

            with open(experiment_file_path, "r", encoding="ascii") as experiment_file:
                experiment = json.load(experiment_file)
                experiment = (
                    experiment_class.RootModel[ExperimentBase]
                    .model_validate_json(json.dumps(experiment))
                    .root
                )
                if experiment.well_id in available_wells:
                    filtered_layered_queue.append(experiment_id)

        # Now we have a list of experiments that are in the queue and are layered protocols and are for available wells
        # We need to generate a list of experiments that can be run together
        # We will do this by looping through the list of experiments and checking if the target well is already in the list
        # If it is, then we will skip that experiment
        # If it is not, then we will add it to the list

        # We don't need to check the queue again because we will be skipping the experiments that are already in the list
        # We will just loop through the filtered_layered_queue and add the experiments to the list
        experiment_list = []
        for experiment_id in filtered_layered_queue:
            experiment_file_path = PATH_TO_EXPERIMENT_QUEUE / f"{experiment_id}.json"
            if not Path.exists(experiment_file_path):
                logger.error("experiment file %s not found", experiment_file_path.stem)
                raise FileNotFoundError(f"experiment file {experiment_file_path.stem}")

            with open(experiment_file_path, "r", encoding="ascii") as experiment_file:
                experiment = json.load(experiment_file)
                experiment = (
                    experiment_class.RootModel[ExperimentBase]
                    .model_validate_json(json.dumps(experiment))
                    .root
                )
                if experiment.well_id not in experiment_list:
                    experiment_list.append(experiment)

        # Now we have a list of experiments that can be run together
        # We need to remove these experiments from the queue.csv file and the experiment_queue folder
        # We will do this by looping through the list of experiments and removing them from the queue
        for experiment_id in filtered_layered_queue:
            experiment_file_path = PATH_TO_EXPERIMENT_QUEUE / f"{experiment_id}.json"
            if not Path.exists(experiment_file_path):
                logger.error("experiment file not found")
                raise FileNotFoundError(f"experiment file {experiment_file_path.stem}")

            # Remove the experiment from the queue file
            queue_df = pd.DataFrame(queue_df[queue_df["id"] != experiment_id])
            queue_df.to_csv(queue_file_path, index=False)

            # Remove the experiment from the experiment_queue folder
            experiment_file_path.unlink()

        return experiment_list

    def get_queue(self) -> pd.DataFrame:
        """Return the queue as a DataFrame"""
        queue_file_path = PATH_TO_QUEUE
        if not Path.exists(queue_file_path):
            logger.error("queue file not found")
            raise FileNotFoundError("experiment queue file")

        # Read the queue file
        queue = pd.read_csv(queue_file_path, header=0, names=["id", "priority", "filename","protocol_type"], dtype={"id": int, "priority": int, "filename": str, "protocol_type":int}, skipinitialspace=True)
        return queue

####################################################################################################
def test_well_status_update():
    """
    Tests the change_well_status function.
    """
    test_scheduler = Scheduler()
    current_status = test_scheduler.check_well_status("A1")
    test_scheduler.change_well_status("A1", "running")
    assert test_scheduler.check_well_status("A1") == "running"
    test_scheduler.change_well_status("A1", "complete")
    assert test_scheduler.check_well_status("A1") == "complete"
    test_scheduler.change_well_status("A1", "new")
    assert test_scheduler.check_well_status("A1") == "new"
    test_scheduler.change_well_status("A1", current_status)


if __name__ == "__main__":
    test_well_status_update()
    #scheduler.read_next_experiment_from_queue()
