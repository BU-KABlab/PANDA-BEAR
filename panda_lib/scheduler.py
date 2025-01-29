"""
The scheduler module will be responsible for:
    - ingesting new experiments
    - Designating experiments to wells
    - Scheduling experiments by priority
    - Inserting control tests
    - Returning the next experiment to run
"""

# pylint: disable = line-too-long
import sqlite3
from pathlib import Path
from typing import Tuple, Union

from shared_utilities.log_tools import setup_default_logger, timing_wrapper

from .experiments import (
    ExperimentBase,
    ExperimentStatus,
    insert_experiment,
    insert_experiment_parameters,
    insert_experiments_parameters,
    select_experiment_information,
    select_experiment_parameters,
    select_next_experiment_id,
    update_experiment_status,
)
from .experiments.results import insert_experiment_result
from .labware.wellplates import Well
from .sql_tools.db_setup import SessionLocal
from .sql_tools.panda_models import ExperimentParameters, Experiments, Projects
from .sql_tools.sql_queue import (
    get_next_experiment_from_queue,
)
from .sql_tools.sql_wellplate import (
    check_if_plate_type_exists,
    get_well_by_id,
    select_current_wellplate_info,
    select_next_available_well,
    select_well_status,
    select_wellplate_info,
    update_well,
)

logger = setup_default_logger(log_name="scheduler")


@timing_wrapper
def check_well_status(well_to_check: str, plate_id: int = None) -> str:
    """Checks the status of the well in the well_status view in the SQLite database"""
    try:
        well_status = select_well_status(well_to_check, plate_id)
        return well_status
    except sqlite3.Error as e:
        logger.error("Error occurred while checking well status: %s", e)
        raise e


@timing_wrapper
def choose_next_new_well(plate_id: int = None) -> str:
    """Choose the next available well for an experiment"""
    try:
        next_well = select_next_available_well(plate_id)
        return next_well
    except sqlite3.Error as e:
        logger.error("Error occurred while choosing next well: %s", e)
        raise e


@timing_wrapper
def change_well_status(well: Union[Well, str], experiment: ExperimentBase) -> None:
    """Change the status of the well in the well_status view in the SQLite database"""
    logger.debug(
        "Changing %s status to %s",
        well,
        well.status if isinstance(well, Well) else experiment.status.value,
    )
    # If the well is a string, get a well object
    if isinstance(well, str):
        well_id = well
        well: Well = get_well_by_id(well_id=well_id)
        if well is None:
            logger.error("Well %s not found", well_id)
            raise ValueError(f"Well {well_id} not found")

    # Update the well status
    well.status = experiment.status.value
    well.status_date = experiment.status_date

    # Verify that the well has a plate id
    if well.plate_id is None:
        logger.error("Well %s does not have a plate id", well)
        raise ValueError(f"Well {well} does not have a plate id")

    try:
        update_well(well)
    except sqlite3.Error as e:
        logger.error("Error occurred while changing well status: %s", e)
        raise e


@timing_wrapper
def read_next_experiment_from_queue(
    random_pick: bool = True,
    experiment_id: int = None,
) -> Tuple[ExperimentBase, Path]:
    """
    Reads the next experiment from the queue table, the experiment with the highest priority (lowest number).
    If random_pick is True, then a random experiment with the highest priority is selected.
    Otherwise, the lowest experiment id in the queue with the highest priority is selected.

    If experiment_id is provided, then the experiment with that id is selected.

    Args:
        random_pick (bool): Whether to randomly select an experiment from the queue.
        experiment_id (int): The experiment id to select from the queue.

    Returns:
        Tuple[ExperimentBase]: The next experiment.
    """
    # Get the next experiment from the queue
    try:
        queue_info = get_next_experiment_from_queue(random_pick, experiment_id)
    except sqlite3.Error as e:
        logger.error("Error occurred while reading next experiment from queue: %s", e)
        raise e

    if queue_info is None:
        logger.info("No experiments in queue")
        return None, None

    else:
        experiment_id, _, filename, _, well_id = queue_info
    # Get the experiment information from the experiment table
    experiment = select_experiment_information(experiment_id)
    experiment.map_parameter_list_to_experiment(
        select_experiment_parameters(experiment_id)
    )

    # Finally get the well id and plate id for the experiment based on the well_status view
    experiment.well_id = well_id

    return experiment, filename


@timing_wrapper
def update_experiment_queue_priority(experiment_id: int, priority: int):
    """Update the priority of experiments in the queue"""
    try:
        # execute_sql_command(
        #     "UPDATE experiments SET priority = ? WHERE experiment_id = ?",
        #     (priority, experiment_id),
        # )
        with SessionLocal() as session:
            session.query(Experiments).filter_by(experiment_id=experiment_id).update(
                {"priority": priority}
            )
            session.commit()

    except sqlite3.Error as e:
        logger.error("Error occurred while updating experiment queue priority: %s", e)
        raise e


@timing_wrapper
def update_experiment_info(experiment: ExperimentBase, column: str) -> None:
    """Update the experiment information in the experiments table"""
    try:
        # execute_sql_command(
        #     f"UPDATE experiments SET {column} = ? WHERE experiment_id = ?",
        #     (getattr(experiment, column), experiment.experiment_id),
        # )

        with SessionLocal() as session:
            session.query(Experiments).filter_by(
                experiment_id=experiment.experiment_id
            ).update({column: getattr(experiment, column)})
            session.commit()
    except sqlite3.Error as e:
        logger.error("Error occurred while updating experiment information: %s", e)
        raise e


@timing_wrapper
def update_experiment_parameters(experiment: ExperimentBase, parameter: str) -> None:
    """Update the experiment parameters in the experiment_parameters table"""
    try:
        with SessionLocal() as session:
            session.query(ExperimentParameters).filter_by(
                experiment_id=experiment.experiment_id
            ).update({parameter: getattr(experiment, parameter)})
            session.commit()
    except sqlite3.Error as e:
        logger.error("Error occurred while updating experiment parameters: %s", e)
        raise e


@timing_wrapper
def add_nonfile_experiment(
    experiment: ExperimentBase, override_well_available=False
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
            message = f"Experiment {experiment.experiment_id} is not new or queued, not adding to queue"
            logger.info(message)
            return message

        ## Check if the well is available
        if check_well_status(experiment.well_id) != "new":
            # Find the next available well
            target_well = choose_next_new_well()
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
            # update_experiment_parameters(experiment, "well_id")
    # Data clean the solutions to all be lowercase
    experiment.solutions = {k.lower(): v for k, v in experiment.solutions.items()}
    # Save the experiment as a separate file in the experiment_queue subfolder
    experiment.set_status_and_save(ExperimentStatus.QUEUED)

    ## Add the experiment to experiments table
    try:
        insert_experiment(experiment)
    except sqlite3.Error as e:
        logger.error(
            "Error occurred while adding the experiment to experiments table: %s", e
        )
        experiment.status = ExperimentStatus.ERROR
        raise e  # raise the error to be caught by the calling function

    ## Add the experiment parameters to the experiment_parameters table
    try:
        insert_experiment_parameters(experiment)
    except sqlite3.Error as e:
        logger.error(
            "Error occurred while adding the experiment parameters to experiment_parameters table: %s",
            e,
        )
        experiment.status = ExperimentStatus.ERROR
        raise e

    ## Add the experiment to the queue
    experiment = add_to_queue(experiment)

    ## Change the status of the well
    change_well_status(experiment.well_id, experiment)

    logger.info("Experiment %s added to queue", experiment.experiment_id)
    return "success"


@timing_wrapper
def add_to_queue(experiment: ExperimentBase) -> ExperimentBase:
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
        logger.error("Error occurred while adding the experiment to queue table: %s", e)
        experiment.status = ExperimentStatus.ERROR
        raise e  # raise the error to be caught by the calling function
    return experiment


@timing_wrapper
def add_nonfile_experiments(experiments: list[ExperimentBase]) -> int:
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
                message = f"Experiment {experiment.experiment_id} is not new or queued, not adding to queue"
                logger.info(message)
                print(message)
                experiments.remove(experiment)

            ## Check if the experiment is for a specific plate, if not choose the current plate
            if experiment.plate_id is None:
                experiment.plate_id, _, _ = select_current_wellplate_info()
            ## Check if the well is available
            if check_well_status(experiment.well_id, experiment.plate_id) != "new":
                # Check that the plate ID exists
                if not check_if_plate_type_exists(experiment.plate_type_number):
                    logger.error(
                        "Plate type %s does not exist, cannot add experiment to queue",
                        experiment.plate_id,
                    )
                    print(
                        f"Plate type {experiment.plate_id} does not exist, cannot add experiment to queue"
                    )
                    experiments.remove(experiment)
                    continue

                # Check if the target plate id has the target well type number
                plate_info = select_wellplate_info(experiment.plate_id)
                if plate_info is None:
                    logger.error(
                        "Plate %s does not exist, cannot add experiment to queue",
                        experiment.plate_id,
                    )
                    print(
                        f"Plate {experiment.plate_id} does not exist, cannot add experiment to queue"
                    )
                    experiments.remove(experiment)
                    continue

                if (
                    plate_info.type_id != experiment.plate_type_number
                    or plate_info.id != experiment.plate_id
                ):
                    logger.error(
                        "Plate %s does not have the correct well type number, cannot add experiment to queue",
                        experiment.plate_id,
                    )
                    print(
                        f"Plate {experiment.plate_id} does not have the correct well type number, cannot add experiment to queue"
                    )
                    experiments.remove(experiment)
                    continue

                # Find the next available well
                target_well = choose_next_new_well(experiment.plate_id)
                if target_well is None:
                    logger.info(
                        "No wells available for experiment originally for well %s.",
                        experiment.well_id,
                    )
                    print(
                        f"No wells available for experiment originally for well {experiment.well_id}."
                    )
                    experiments.remove(experiment)
                    continue
                    # TODO Add a pending label to the experiment to be added to the queue when the right well is available
                logger.info(
                    "Experiment originally for well %s is now for well %s.",
                    experiment.well_id,
                    target_well,
                )
                experiment.well_id = target_well

        # Check if the project_id is in the projects table, if not add it
        if not check_project_id(experiment.project_id):
            add_project_id(experiment.project_id)

        # Data clean the solutions to all be lowercase
        experiment.solutions = {k.lower(): v for k, v in experiment.solutions.items()}

        # Individually insert the experiment and update the status
        # We do this so that the wellchecker is checking as the wells are allocated
        # The parameters are quite lengthy, so we will save those for a bulk entry
        try:
            insert_experiment(experiment)
            update_experiment_status(experiment, ExperimentStatus.QUEUED)
        except sqlite3.Error as e:
            logger.error(
                "Error occurred while adding the experiment to experiments table: %s",
                e,
            )
            logger.error(
                "The statements have been rolled back and nothing has been added to the tables."
            )
            print(
                "The statements have been rolled back and nothing has been added to the tables."
            )
            raise e

    ## Add the experiment to experiments table
    try:
        # Bulk insert the experiments that had wells available
        # sql_utilities.insert_experiments(experiments)
        # Bulk set the status of the experiments that had wells available
        # sql_utilities.update_experiments_statuses(
        #     experiments, ExperimentStatus.QUEUED
        # )

        ## Bulk add the experiment parameters to the experiment_parameters table
        insert_experiments_parameters(experiments)

    except sqlite3.Error as e:
        logger.error(
            "Error occurred while adding the experiment parameters to experiment_parameters table: %s",
            e,
        )
        logger.error(
            "The statements have been rolled back and nothing has been added to the tables."
        )
        print(
            "The statements have been rolled back and nothing has been added to the tables."
        )
        raise e

    logger.info("Experiments loaded and added to queue")
    return 1


@timing_wrapper
def check_project_id(project_id: int) -> bool:
    """Check if the project_id is in the projects table"""
    try:
        with SessionLocal() as session:
            project = session.query(Projects).filter_by(id=project_id).first()
            if project is None:
                return False
            return True
    except sqlite3.Error as e:
        logger.error("Error occurred while checking project id: %s", e)
        raise e


@timing_wrapper
def add_project_id(project_id: int) -> None:
    """Add the project_id to the projects table"""
    try:
        with SessionLocal() as session:
            session.add(Projects(id=project_id))
            session.commit()
    except sqlite3.Error as e:
        logger.error("Error occurred while adding project id: %s", e)
        raise e


@timing_wrapper
def save_results(experiment: ExperimentBase) -> None:
    """
    Save the results of the experiment to the experiment_results table in the SQL database.

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

    Returns:
        None
    """
    # Turn the results into a list of values
    results_lists = experiment.results.one_to_many()

    for result in results_lists:
        # Save the results to the database
        insert_experiment_result(result)


@timing_wrapper
def determine_next_experiment_id() -> int:
    """Load well history to get last experiment id and increment by 1"""
    return select_next_experiment_id()


####################################################################################################
def test_well_statusupdate():
    """
    Tests the change_well_status function.
    """
    current_status = check_well_status("A1")
    change_well_status("A1", "running")
    assert check_well_status("A1") == "running"
    change_well_status("A1", "complete")
    assert check_well_status("A1") == "complete"
    change_well_status("A1", "new")
    assert check_well_status("A1") == "new"
    change_well_status("A1", current_status)


if __name__ == "__main__":
    test_well_statusupdate()
    # scheduler.read_next_experiment_from_queue()
