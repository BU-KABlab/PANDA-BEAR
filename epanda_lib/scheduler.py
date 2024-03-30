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
import sqlite3
from pathlib import Path
from typing import Tuple, Union

import pandas as pd
from numpy import choose

from epanda_lib import sql_utilities
from epanda_lib.scheduler_utilities import remove_from_queue

from . import experiment_class
from .config.config import (
    EPANDA_LOG,
    PATH_TO_COMPLETED_EXPERIMENTS,
    PATH_TO_ERRORED_EXPERIMENTS,
    PATH_TO_EXPERIMENT_INBOX,
    PATH_TO_EXPERIMENT_QUEUE,
)
from .config.config import QUEUE as PATH_TO_QUEUE
from .config.config import WELL_STATUS
from .experiment_class import ExperimentBase, ExperimentResult, ExperimentStatus
from .sql_utilities import execute_sql_command, execute_sql_command_no_return
from .wellplate import Well

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter(
    "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&&&&%(message)s&"
)
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

    # def check_well_status(self, well_to_check: str) -> str:
    #     """
    #     Checks the status of a well in the well config file: well_status.json.
    #     :param well: The well to check.
    #     :return: The status of the well. Or None if the well is not found.
    #     """
    #     file_to_open = WELL_STATUS
    #     if not Path.exists(file_to_open):
    #         logger.error("%s not found", file_to_open)
    #         raise FileNotFoundError(f"{file_to_open.stem} not found")

    #     with open(file_to_open, "r", encoding="ascii") as file:
    #         data = json.load(file)
    #         for well in data["wells"]:
    #             if well["well_id"] == well_to_check:
    #                 return well["status"]
    #             else:
    #                 continue
    #         return None

    def check_well_status(self, well_to_check: str) -> str:
        """Checks the status of the well in the well_status view in the SQLite database"""
        try:
            well_status = sql_utilities.get_well_status(well_to_check)
            return well_status
        except sqlite3.Error as e:
            logger.error("Error occured while checking well status: %s", e)
            raise e

    # def choose_next_new_well(self, baseline: bool = False) -> str:
    #     """
    #     Chooses the next available well for an experiment.

    #     Args:
    #         baseline (bool): Whether the experiment is a baseline test.

    #     Returns:
    #         str: The well id of the next available well.

    #     """
    #     logger.debug("Choosing alternative well")
    #     file_to_open = WELL_STATUS
    #     if not Path.exists(file_to_open):
    #         logger.error("well_status.json not found")
    #         raise FileNotFoundError("well_status.json")

    #     with open(file_to_open, "r", encoding="ascii") as file:
    #         data = json.load(file)
    #         for well in data["wells"]:
    #             if well["status"] == "new":
    #                 if baseline:
    #                     # Baseline tests can only be run in rows 1 or 12
    #                     if well["well_id"][1] == 1 or well["well_id"][1] == 12:
    #                         return well["well_id"]
    #                 return well["well_id"]
    #         return None

    def choose_next_new_well(self) -> str:
        """Choose the next available well for an experiment"""
        try:
            next_well = sql_utilities.select_next_available_well()
            return next_well
        except sqlite3.Error as e:
            logger.error("Error occured while choosing next well: %s", e)
            raise e

    # def change_well_status(self, well: str, experiment: ExperimentBase) -> None:
    #     """
    #     Changes the status of a well in well_status.json.
    #     :param well: The well to change.
    #     :param status: The new status of the well.
    #     """
    #     logger.debug("Changing well %s status to %s", well, experiment.status.value)
    #     file_to_open = WELL_STATUS
    #     if not Path.exists(file_to_open):
    #         logger.error("well_status.json not found")
    #         raise FileNotFoundError("well_status.json")

    #     with open(file_to_open, "r", encoding="ascii") as file:
    #         data = json.load(file)
    #         for wells in data["wells"]:
    #             if wells["well_id"] == well:
    #                 wells["status"] = experiment.status
    #                 wells["status_date"] = experiment.status_date.isoformat(
    #                     timespec="seconds"
    #                 )
    #                 wells["experiment_id"] = experiment.id
    #                 wells["project_id"] = experiment.project_id
    #                 break
    #     with open(file_to_open, "w", encoding="ascii") as file:
    #         json.dump(data, file, indent=4)

    #     logger.info("Well %s status changed to %s", well, experiment.status.value)

    # def change_well_status_v2(self, well: Well, experiment: ExperimentBase) -> None:
    #     """
    #     Changes the status of a well in well_status.json.
    #     :param well: The well to change.
    #     :param status: The new status of the well.
    #     """
    #     logger.debug("Changing %s status to %s", well, well.status)

    #     well.status = experiment.status.value
    #     well.status_date = experiment.status_date

    #     file_to_open = WELL_STATUS
    #     if not Path.exists(file_to_open):
    #         logger.error("well_status.json not found")
    #         raise FileNotFoundError("well_status.json")

    #     with open(file_to_open, "r", encoding="ascii") as file:
    #         data = json.load(file)
    #         for wells in data["wells"]:
    #             if wells["well_id"] == well.well_id:
    #                 wells["status"] = well.status
    #                 wells["status_date"] = well.status_date.isoformat(timespec="seconds"
    #                 )
    #                 wells["experiment_id"] = well.experiment_id
    #                 wells["project_id"] = well.project_id
    #                 wells["contents"] = well.contents
    #                 break
    #     with open(file_to_open, "w", encoding="ascii") as file:
    #         json.dump(data, file, indent=4)

    #     logger.info("%s status changed to %s", well, well.status)

    def change_well_status(
        self, well: Union[Well, str], experiment: ExperimentBase
    ) -> None:
        """Change the status of the well in the well_status view in the SQLite database"""
        logger.debug(
            "Changing %s status to %s",
            well,
            well.status if isinstance(well, Well) else experiment.status.value,
        )
        if isinstance(well, str):
            well_id = well
            well = sql_utilities.WellSQLHandler(well_id).get_well()

        well.status = experiment.status.value
        well.status_date = experiment.status_date

        try:
            well.save_to_db()
        except sqlite3.Error as e:
            logger.error("Error occured while changing well status: %s", e)
            raise e

    # def ingest_inbox_experiments(self, filename: str) -> Tuple[int, bool]:
    #     """
    #     Reads a JSON file and returns the experiment instructions/recipie as a dictionary.
    #     :param filename: The name of the JSON file to read.
    #     :return: number of experiments queued, if any left behind.
    #     """
    #     experiments_read = 0
    #     complete = True
    #     inbox_dir = PATH_TO_EXPERIMENT_INBOX
    #     file_to_open = (inbox_dir / filename).with_suffix(".json")
    #     with open(file_to_open, "r", encoding="ascii") as file:
    #         data = json.load(file)
    #     for experiment in data["Experiments"]:
    #         existing_status = experiment["status"]
    #         if existing_status != "new":
    #             continue
    #         # Get the experiment id and create a filename
    #         desired_well = experiment["target_well"]

    #         # Check if the well is available
    #         if self.check_well_status(desired_well) != "new":
    #             # Find the next available well
    #             target_well = self.choose_next_new_well()
    #             if target_well is None:
    #                 logger.info(
    #                     "No wells available for experiment originally for well %s",
    #                     desired_well,
    #                 )
    #                 complete = False
    #                 continue
    #             logger.info(
    #                 "Experiment originally for well %s is now for well %s",
    #                 desired_well,
    #                 target_well,
    #             )
    #             experiment["target_well"] = target_well
    #         else:
    #             target_well = desired_well

    #         filename = f"{experiment['id']}.json"

    #         # populate an experiment instance
    #         instructions = (
    #             experiment_class.RootModel[ExperimentBase]
    #             .model_validate_json(json.dumps(experiment))
    #             .root
    #         )

    #         # Save the experiment as a separate file in the experiment_queue subfolder
    #         queue_dir = PATH_TO_EXPERIMENT_QUEUE
    #         queue_dir.mkdir(parents=True, exist_ok=True)
    #         file_to_save = queue_dir / filename

    #         serialized_data = experiment_class.serialize_experiment(instructions)
    #         with open(file_to_save, "w", encoding="UTF-8") as file:
    #             file.write(serialized_data)
    #         logger.debug("Experiment %s saved to %s", instructions.id, file_to_save)
    #         # with open(file_to_save, "w", encoding="UTF-8") as outfile:
    #         #     text_version = json.dumps(instructions)
    #         #     json.dump(text_version, outfile, indent=4)

    #         # Add the experiment to the queue
    #         queue_file_path = PATH_TO_QUEUE
    #         with open(queue_file_path, "a", encoding="UTF-8") as queue_file:
    #             line = (
    #                 f"{instructions.id},{instructions.priority},{instructions.filename}"
    #             )
    #             queue_file.write(line)
    #             queue_file.write("\n")

    #         logger.debug("Experiment %s added to queue", instructions.id)
    #         # Change the status of the well
    #         self.change_well_status(target_well, "queued")

    #         # Add the experiment to the list of experiments read
    #         experiments_read += 1

    #     # Save the updated file
    #     with open(file_to_open, "w", encoding="UTF-8") as file:
    #         json.dump(data, file, indent=4)

    #     return experiments_read, complete

    # def check_inbox(self) -> Tuple[int, bool]:
    #     """
    #     Checks the experiments inbox folder for new experiments.
    #     :return: the count of new experiments.
    #     """

    #     file_path = PATH_TO_EXPERIMENT_INBOX
    #     count = 0
    #     complete = True
    #     for file in file_path.iterdir():
    #         # If there are files but 0 added then begin by inserting a baseline test
    #         # or every tenth experiment
    #         # if (count == 0) or (count % 9 == 0): # We are currently having the science team insert the baseline tests
    #         #     self.insert_control_tests()   # so we are not doing this here.

    #         if file.is_file():
    #             logger.info("Reading file %s for experiments", file.name)
    #             count, complete = self.ingest_inbox_experiments(file.name)

    #             # Move the file to archive if it has been completely read
    #             if complete:
    #                 logger.debug("Moving file %s to archive", file.name)
    #                 archive_path = file_path / "archive"
    #                 archive_path.mkdir(parents=True, exist_ok=True)
    #                 file.replace(archive_path / file.name)
    #                 logger.info("File %s moved to archive.", file.name)
    #             else:
    #                 logger.info(
    #                     "File %s not moved to archive. Not all experiments queued.",
    #                     file.name,
    #                 )

    #     return count, complete

    # def read_next_experiment_from_queue(
    #     self, random_pick: bool = True
    # ) -> Tuple[ExperimentBase, Path]:
    #     """
    #     Reads the next experiment from the queue.
    #     :return: The next experiment.
    #     """
    #     queue_file_path = PATH_TO_QUEUE
    #     ## Starting with the queue.csv file to get the experiment id and filename
    #     ## The we want to get the experiment with the highest priority (lowest number)
    #     if not Path.exists(queue_file_path):
    #         logger.error("queue file not found")
    #         raise FileNotFoundError("experiment queue file")

    #     # Read the queue file
    #     # with open(queue_file_path, "r", encoding="ascii") as queue_file:
    #     #     queue = queue_file.readlines()

    #     queue = pd.read_csv(
    #         queue_file_path,
    #         header=0,
    #         names=["id", "priority", "filename"],
    #         dtype={"id": int, "priority": int, "filename": str},
    #         skipinitialspace=True,
    #     )
    #     if queue.empty:
    #         logger.info("No experiments in queue")
    #         return None, None

    #     highest_priority = queue["priority"].min()
    #     # Get all experiments with the highest priority so that we can randomly select one of them
    #     experiments = queue[(queue["priority"] == highest_priority)]["filename"]
    #     experiments_list = experiments.tolist()
    #     if not Path.exists(PATH_TO_EXPERIMENT_QUEUE):
    #         logger.error("experiment_queue folder not found")
    #         raise FileNotFoundError("experiment queue folder")

    #     if random_pick:
    #         # Pick a random experiment from the list of experiments with the highest priority
    #         random_experiment = random.choice(experiments_list)
    #         experiment_file_path = Path(
    #             PATH_TO_EXPERIMENT_QUEUE / random_experiment
    #         ).with_suffix(".json")
    #         if not Path.exists(experiment_file_path):
    #             logger.error("experiment file not found")
    #             raise FileNotFoundError("experiment file")
    #     else:
    #         # Sort the queue by experiment id and then by priority, excluding type 2 protocols
    #         queue = queue.sort_values(by=["id", "priority"], ascending=[True, True])
    #         # Get the first experiment in the queue
    #         experiment_file_path = Path(
    #             PATH_TO_EXPERIMENT_QUEUE / queue["filename"].iloc[0]
    #         ).with_suffix(".json")
    #         if not Path.exists(experiment_file_path):
    #             logger.error("experiment file not found")
    #             raise FileNotFoundError("experiment file")

    #     # Read the experiment file
    #     with open(experiment_file_path, "r", encoding="ascii") as experiment_file:
    #         # experiment = json.load(experiment_file)
    #         # experiment = (
    #         #     experiment_class.RootModel[ExperimentBase]
    #         #     .model_validate_json(json.dumps(experiment))
    #         #     .root
    #         # )
    #         experiment: ExperimentBase = experiment_class.parse_experiment(
    #             experiment_file.read()
    #         )
    #     # Remove the selected experiment from the queue
    #     # self.remove_from_queue(experiment)
    #     logger.info("Experiment %s read from queue", experiment.id)

    #     return experiment, experiment_file_path

    def read_next_experiment_from_queue(
        self, random_pick: bool = True
    ) -> Tuple[ExperimentBase, Path]:
        """
        Reads the next experiment from the queue table, the experiment with the highest priority (lowest number).
        If random_pick is True, then a random experiment with the highest priority is selected.
        Otherwise, the lowest experiment id in the queue with the highest priority is selected.

        Args:
            random_pick (bool): Whether to randomly select an experiment from the queue.

        Returns:
            Tuple[ExperimentBase]: The next experiment.
        """
        # Get the next experiment from the queue
        try:
            experiment_info = sql_utilities.get_next_experiment_from_queue(random_pick)
        except sqlite3.Error as e:
            logger.error(
                "Error occured while reading next experiment from queue: %s", e
            )
            raise e

        if experiment_info is None:
            logger.info("No experiments in queue")
            return None, None

        experiment_id = experiment_info[0]
        experiment_process_type = experiment_info[1]
        experiment_filename = experiment_info[2]

        # TODO Get the experiment parameters from the database

        # TODO Map the experiment process type to the correct experiment class

        # TODO Return the experiment

    # def remove_from_queue(self, experiment: ExperimentBase) -> None:
    #     """
    #     Updates the queue file to remove the experiment that was just run.
    #     :param experiment: The experiment that was just run.
    #     """
    #     file_path = PATH_TO_QUEUE
    #     if not Path.exists(file_path):
    #         logger.error("queue file not found")
    #         raise FileNotFoundError("experiment queue file")

    #     # Read the queue file
    #     queue = pd.read_csv(
    #         file_path,
    #         header=0,
    #         names=["id", "priority", "filename"],
    #         dtype={"id": int, "priority": int, "filename": str},
    #         skipinitialspace=True,
    #     )

    #     # Remove the experiment from the queue file
    #     queue = queue[queue["id"] != experiment.id]
    #     queue.to_csv(file_path, index=False)
    #     # TODO replace with sql table

    def remove_from_queue(self, experiment: ExperimentBase | int) -> None:
        """Remove the experiment from the queue table"""

        if isinstance(experiment, int):
            experiment_id = experiment
        else:
            experiment_id = experiment.id
        try:
            remove_from_queue(experiment_id)
        except sqlite3.Error as e:
            logger.error("Error occured while removing experiment from queue: %s", e)
            raise e

    # def update_experiment_queue_priority(self, experiment_id: int, priority: int):
    #     """Update the priority of experiments in the queue"""
    #     queue_file_path = PATH_TO_QUEUE
    #     if not Path.exists(queue_file_path):
    #         logger.error("queue file not found")
    #         raise FileNotFoundError("experiment queue file")

    #     # Read the queue file
    #     queue = pd.read_csv(
    #         queue_file_path,
    #         header=0,
    #         names=["id", "priority", "filename"],
    #         dtype={"id": int, "priority": int, "filename": str},
    #         skipinitialspace=True,
    #     )

    #     # Find the experiment in the queue
    #     queue.loc[queue["id"] == experiment_id, "priority"] = priority

    #     # Rewrite the queue csv file
    #     queue.to_csv(queue_file_path, index=False)
    #     # TODO replace with sql table

    def update_experiment_queue_priority(self, experiment_id: int, priority: int):
        """Update the priority of experiments in the queue"""
        try:
            execute_sql_command(
                "UPDATE queue SET priority = ? WHERE id = ?", (priority, experiment_id)
            )
        except sqlite3.Error as e:
            logger.error(
                "Error occured while updating experiment queue priority: %s", e
            )
            raise e

    # def update_experiment_file(self, experiment: ExperimentBase) -> None:
    #     """
    #     Updates the status of the experiment in the experiment instructions file.
    #     Args:
    #         experiment (ExperimentBase): The experiment to update

    #     Returns:
    #         None
    #     """
    #     file_path = (PATH_TO_EXPERIMENT_QUEUE / experiment.filename).with_suffix(
    #         ".json"
    #     )
    #     if not Path.exists(file_path):
    #         logger.error("experiment file not found")
    #         raise FileNotFoundError("experiment file")

    #     # # Update the status of the experiment
    #     # with open(file_path, "r", encoding="UTF-8") as file:
    #     #     data = json.load(file)
    #     #     data = json.dumps(data)
    #     #     parsed_data = experiment_class.parse_experiment(data)
    #     #     parsed_data.status = str(experiment.status.value)
    #     #     parsed_data.status_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    #     # Save the updated file
    #     serialized_data = experiment_class.serialize_experiment(experiment)
    #     with open(file_path, "w", encoding="UTF-8") as file:
    #         file.write(serialized_data)

    #     logger.info(
    #         "Experiment %s status changed to %s", experiment.id, experiment.status.value
    #     )

    def update_experiment_info(self, experiment: ExperimentBase, column: str) -> None:
        """Update the experiment information in the experiments table"""
        try:
            execute_sql_command(
                "UPDATE experiments SET ? = ? WHERE id = ?",
                (column, experiment[column], experiment.id),
            )
        except sqlite3.Error as e:
            logger.error("Error occured while updating experiment information: %s", e)
            raise e

    def update_experiment_parameters(
        self, experiment: ExperimentBase, parameter: str
    ) -> None:
        """Update the experiment parameters in the experiment_parameters table"""
        try:
            execute_sql_command(
                "UPDATE experiment_parameters SET ? = ? WHERE experiment_id = ?",
                (parameter, experiment[parameter], experiment.id),
            )
        except sqlite3.Error as e:
            logger.error("Error occured while updating experiment parameters: %s", e)
            raise e

    def update_experiment_location(self, experiment: ExperimentBase) -> None:
        """
        Updates the location of the experiment instructions file based on status.
        Args:
            experiment (ExperimentBase): The experiment to update.

        Returns:
            None
        """
        # file_name_with_suffix = Path(experiment.filename).with_suffix(".json")
        # file_path = Path(PATH_TO_EXPERIMENT_QUEUE / file_name_with_suffix.name)
        # if not Path.exists(file_path):
        #     logger.error("experiment file not found")
        #     raise FileNotFoundError("experiment file")

        # if experiment.status == ExperimentStatus.COMPLETE:
        #     # Move the file to the completed folder
        #     completed_path = PATH_TO_COMPLETED_EXPERIMENTS
        #     file_path.replace(completed_path / file_name_with_suffix)

        # elif experiment.status == ExperimentStatus.ERROR:
        #     # Move the file to the errored folder
        #     errored_path = PATH_TO_ERRORED_EXPERIMENTS
        #     file_path.replace(errored_path / file_name_with_suffix)

        # else:
        #     # If the experiment is neither complete nor errored, then we need to keep it in the queue
        #     # and add it back to the queue file
        #     experiment = self.add_to_queue(experiment)
        #     logger.info(
        #         "Experiment %s is not complete or errored, keeping in queue",
        #         experiment.id,
        #     )

        # logger.info(
        #     "Experiment %s location updated to %s",
        #     experiment.id,
        #     experiment.status.value,
        # )
        logger.warning("No files to move when using database")

    def add_nonfile_experiment(
        self, experiment: ExperimentBase, override_well_available=False
    ) -> str:
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
                target_well = self.choose_next_new_well()
                if target_well is None:
                    logger.info(
                        "No wells available for experiment originally for well %s.",
                        experiment.well_id,
                    )
                    return "No wells available"
                logger.info(
                    "Experiment originally for well %s is now for well %s.",
                    experiment.well_id,
                    target_well,
                )
                experiment.well_id = target_well

        # Save the experiment as a separate file in the experiment_queue subfolder
        experiment.set_status_and_save(ExperimentStatus.QUEUED)
        experiment = self.add_to_queue_folder(experiment)

        ## Add the experiment to experiments table
        try:
            sql_utilities.insert_experiment(experiment)
        except sqlite3.Error as e:
            logger.error(
                "Error occured while adding the experiment to experiments table: %s", e
            )
            experiment.status = ExperimentStatus.ERROR
            raise e  # raise the error to be caught by the calling function

        ## Add the experiment parameters to the experiment_parameters table
        try:
            sql_utilities.insert_experiment_parameters(experiment)
        except sqlite3.Error as e:
            logger.error(
                "Error occured while adding the experiment parameters to experiment_parameters table: %s",
                e,
            )
            experiment.status = ExperimentStatus.ERROR
            raise e

        ## Add the experiment to the queue
        experiment = self.add_to_queue(experiment)

        ## Change the status of the well
        self.change_well_status(experiment.well_id, experiment)

        logger.info("Experiment %s added to queue", experiment.id)
        return "success"

    def add_to_queue_folder(self, experiment: ExperimentBase) -> ExperimentBase:
        """Add the given experiment to the experiment_queue folder"""
        # queue_dir = PATH_TO_EXPERIMENT_QUEUE
        # file_to_save = (queue_dir / experiment.filename).with_suffix(".json")
        # with open(file_to_save, "w", encoding="UTF-8") as file:
        #     serialized_data = experiment_class.serialize_experiment(experiment)
        #     file.write(serialized_data)
        logger.warning("No files to save when using database")
        return experiment

    # def add_to_queue(self, experiment: ExperimentBase) -> ExperimentBase:
    #     """Add the given experiment to the queue.csv"""
    #     queue_file_path = PATH_TO_QUEUE
    #     if not Path.exists(queue_file_path):
    #         logger.error("queue file not found")
    #         raise FileNotFoundError("experiment queue file")

    #     # Read the queue file
    #     # Add the experiment to the queue
    #     new_row = {
    #         "id": experiment.id,
    #         "priority": experiment.priority,
    #         "filename": experiment.filename,
    #     }
    #     df = pd.DataFrame(new_row, index=[0])

    #     # Write the updated queue to the csv file
    #     df.to_csv(queue_file_path, mode="a", index=False, header=False)
    #     experiment.status = ExperimentStatus.QUEUED
    #     return experiment

    def add_to_queue(self, experiment: ExperimentBase) -> ExperimentBase:
        """Add the given experiment to the queue table"""
        # Add the experiment to the queue
        try:
            # output = execute_sql_command(
            #     "INSERT INTO queue (experiment_id, process_type, priority, filename) VALUES (?, ?, ?, ?)",
            #     (experiment.id, experiment.process_type, experiment.priority, str(experiment.filename)),
            # )
            # print("Adding experiment to queue result:",output)
            logger.warning("No queue to add to when using database, will be in a view")
            experiment.status = ExperimentStatus.QUEUED

        except sqlite3.Error as e:
            logger.error(
                "Error occured while adding the experiment to queue table: %s", e
            )
            experiment.status = ExperimentStatus.ERROR
            raise e  # raise the error to be caught by the calling function
        return experiment

    # def add_nonfile_experiments(self, experiments: list[ExperimentBase]) -> str:
    #     """
    #     Adds a list of experiments which are not files to the experiment queue directly.
    #     :param experiments: The experiments to add.
    #     """
    #     for experiment in experiments:
    #         response = self.add_nonfile_experiment(
    #             experiment, override_well_available=experiment.override_well_selection
    #         )
    #         if response != "success":
    #             print(response)
    #             logger.warning(response)
    #             return 0
    #     return 1

    def add_nonfile_experiments(self, experiments: list[ExperimentBase]) -> int:
        """
        Adds an experiment which is not a file to the experiment queue directly.

        Args:
            experiment (ExperimentBase): The experiment to add.

        Returns:
            str: A message indicating whether the experiment was successfully added to the queue.
        """
        for experiment in experiments:
            if not experiment.override_well_selection:
                ## First check the existing status, if not new or queued, then do not add to queue
                if experiment.status not in [
                    ExperimentStatus.NEW,
                    ExperimentStatus.QUEUED,
                ]:
                    message = f"Experiment {experiment.id} is not new or queued, not adding to queue"
                    logger.info(message)
                    print(message)
                    experiments.remove(experiment)

                ## Check if the well is available
                if self.check_well_status(experiment.well_id) != "new":
                    # Find the next available well
                    target_well = self.choose_next_new_well()
                    if target_well is None:
                        logger.info(
                            "No wells available for experiment originally for well %s.",
                            experiment.well_id,
                        )
                        print(
                            "No wells available for experiment originally for well %s.",
                            experiment.well_id,
                        )
                        experiments.remove(experiment)
                        # TODO Add these experiments to a list to be added to the queue later when wells are available
                    logger.info(
                        "Experiment originally for well %s is now for well %s.",
                        experiment.well_id,
                        target_well,
                    )
                    experiment.well_id = target_well

        ## Add the experiment to experiments table
        try:
            # Bulk insert the experiments that had wells available
            sql_utilities.insert_experiments(experiments)
            # Bulk set the status of the experiments that had wells available
            sql_utilities.set_experiments_statuses(experiments, ExperimentStatus.QUEUED)

            ## Bulk add the experiment parameters to the experiment_parameters table
            sql_utilities.insert_experiments_parameters(experiments)

        except sqlite3.Error as e:
            logger.error(
                "Error occured while adding the experiment parameters to experiment_parameters table: %s",
                e,
            )
            logger.error(
                "The statements have been rolled back and nothing has been added to the tables."
            )
            print(
                "The statements have been rolled back and nothing has been added to the tables."
            )
            raise e

        ## Add the experiment to the queue
        # for experiment in experiments:
        #     experiment = self.add_to_queue(experiment)

        ## Change the status of the well
        # self.change_well_status(experiment.well_id, experiment)

        logger.info("Experiments loaded and added to queue")
        return 1

    # def save_results(
    #     self, experiment: ExperimentBase, results: ExperimentResult
    # ) -> None:
    #     """Save the results of the experiment as a json file in the data folder
    #     Args:
    #         experiment (Experiment): The experiment that was just run
    #         results (ExperimentResult): The results of the experiment

    #     Returns:
    #         None
    #     """
    #     # Save the results
    #     filename_with_suffix = Path(experiment.filename).with_suffix(".json")
    #     filename = filename_with_suffix.name
    #     logger.info(
    #         "Saving experiment %d results to database as %s",
    #         experiment.id,
    #         str(filename),
    #     )
    #     results_json = experiment_class.serialize_results(results)
    #     with open(
    #         Path(PATH_TO_DATA) / f"{experiment.id}.json", "w", encoding="UTF-8"
    #     ) as results_file:
    #         results_file.write(results_json)

    def save_results(self, experiment: ExperimentBase) -> None:
        """Save the results of the experiment to the experiment_results table in the SQLite database.

            The results are saved in a one to many relationship with the experiment id as the foreign key.
            Each result value is saved as a separate row in the table.
            This function accepts an Experiment object and turns it into a dictionary to be saved in the database.

            The results table has columns:
                - id (primary key) - autoincrement
                - experiment_id (foreign key)
                - result_type
                - result_value
                - created (timestamp)
                - modified (timestamp)
        Args:
            experiment (ExperimentBase): The experiment that was just run
            results (ExperimentResult): The results of the experiment

            Returns:
                None
        """
        # Turn the results into a list of values
        results_lists = experiment.results.one_to_many()

        for result in results_lists:
            # Save the results to the database
            sql_utilities.insert_experiment_results(result)

    # def count_available_wells(self) -> int:
    #     """Return the number of wells available for experiments

    #     Returns:
    #         int: the number of experiments we can queue from the inbox
    #     """
    #     file_to_open = WELL_STATUS
    #     if not Path.exists(file_to_open):
    #         logger.error("well_status.json not found")
    #         raise FileNotFoundError("well_status.json")

    #     with open(file_to_open, "r", encoding="ascii") as file:
    #         data = json.load(file)
    #         count = 0
    #         for wells in data["wells"]:
    #             if wells["status"] == "new":
    #                 count += 1
    #         return count

    def count_available_wells(self) -> int:
        """Return the number of wells available for experiments"""
        try:
            available_wells = sql_utilities.count_wells_with_new_status()
            return available_wells
        except sqlite3.Error as e:
            logger.error("Error occured while counting available wells: %s", e)
            raise e

    # def get_queue(self) -> pd.DataFrame:
    #     """Return the queue as a DataFrame"""
    #     queue_file_path = PATH_TO_QUEUE
    #     if not Path.exists(queue_file_path):
    #         logger.error("queue file not found")
    #         raise FileNotFoundError("experiment queue file")

    #     # Read the queue file
    #     queue = pd.read_csv(
    #         queue_file_path,
    #         header=0,
    #         names=["id", "priority", "filename"],
    #         dtype={"id": int, "priority": int, "filename": str},
    #         skipinitialspace=True,
    #     )
    #     return queue

    def get_queue(self) -> pd.DataFrame:
        """Return the queue as a DataFrame"""
        try:
            queue = sql_utilities.select_queue()
            queue = pd.DataFrame(
                queue, columns=["id", "priority", "process_type", "filename"]
            )
            return queue
        except sqlite3.Error as e:
            logger.error("Error occured while getting queue: %s", e)
            raise e


def get_queue_length() -> int:
    """Get queue length"""
    queue_file = pd.read_csv(
        PATH_TO_QUEUE,
        skipinitialspace=True,
        header=None,
        names=["id", "priority", "filename"],
    )
    # the columsn to id,priority,filename
    return len(queue_file) - 1


def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    # well_hx = pd.read_csv(WELL_HX, skipinitialspace=True, sep="&")
    # well_hx = well_hx.dropna(subset=["experiment id"])
    # well_hx = well_hx.drop_duplicates(subset=["experiment id"])
    # well_hx = well_hx[well_hx["experiment id"] != "None"]
    # well_hx["experiment id"] = well_hx["experiment id"].astype(int)
    # last_experiment_id = well_hx["experiment id"].max()
    # return int(last_experiment_id + 1)
    return sql_utilities.determine_next_experiment_id()


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
    # scheduler.read_next_experiment_from_queue()
