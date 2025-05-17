"""
The scheduler module will be responsible for:
    - ingesting new experiments
    - Designating experiments to wells
    - Scheduling experiments by priority
    - Inserting control tests
    - Returning the next experiment to run
"""

import json
import sqlite3
from pathlib import Path
from typing import Tuple, Union

import sqlalchemy.exc
from sqlalchemy import select, update

from panda_lib.experiments.sql_functions import update_experiment_status
from panda_shared.db_setup import SessionLocal
from panda_shared.log_tools import setup_default_logger, timing_wrapper

from .experiments import (
    EchemExperimentGenerator,
    ExperimentBase,
    ExperimentGenerator,
    ExperimentStatus,
    insert_experiments,
    insert_experiments_parameters,
    select_experiment_information,
    select_experiment_parameters,
    select_next_experiment_id,
)
from .labware.wellplates import Well
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
    """Change the status of the well in the well_hx table"""
    logger.debug(
        "Changing %s status to %s",
        well,
        well.status if isinstance(well, Well) else experiment.status.value,
    )
    # If the well is a string, get a well object
    if isinstance(well, str):
        well_id = well
        result = get_well_by_id(well_id=well_id)
        well: Well = Well(
            id=result.well_id,
            plate_id=result.plate_id,
        )
        if well is None:
            logger.error("Well %s not found", well_id)
            raise ValueError(f"Well {well_id} not found")

    # Update the well status
    well.update_status(experiment.status.value)

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
    Reads the next experiment from the queue, the experiment with the highest priority (lowest number).
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
        experiment_id, filename, _, well_id = queue_info
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
        with SessionLocal() as session:
            stmt = (
                update(Experiments)
                .where(Experiments.experiment_id == experiment_id)
                .values({"priority": priority})
            )
            session.execute(stmt)
            session.commit()

    except sqlite3.Error as e:
        logger.error("Error occurred while updating experiment queue priority: %s", e)
        raise e


@timing_wrapper
def update_experiment_info(experiment: ExperimentBase, column: str) -> None:
    """Update the experiment information in the experiments table"""
    try:
        with SessionLocal() as session:
            stmt = (
                update(Experiments)
                .where(Experiments.experiment_id == experiment.experiment_id)
                .values({column: getattr(experiment, column)})
            )
            session.execute(stmt)
            session.commit()
    except sqlite3.Error as e:
        logger.error("Error occurred while updating experiment information: %s", e)
        raise e


@timing_wrapper
def update_experiment_parameters(experiment: ExperimentBase, parameter: str) -> None:
    """
    Update the experiment parameters in the experiment_parameters table.

    Perform an update on the experiment_parameters table for the given experiment_id and parameter name.
    The parameter value is updated to the value of the parameter attribute in the experiment object.

    NOTE: The ExperimentParameters table is a many to one relationship with the Experiments table. There are
    just 6 columns, and we only work with 3 of them: experiment_id, parameter_name, and parameter_value.

    Args:
        experiment (ExperimentBase): The experiment to update.
        parameter (str): The parameter to update.

    Raises:
        sqlite3.Error: If an error occurs while updating the experiment parameters in the experiment_parameters table.


    """
    try:
        with SessionLocal() as session:
            value = getattr(experiment, parameter)
            value = json.dumps(value, default=str) if isinstance(value, dict) else value

            # session.query(ExperimentParameters).filter_by(
            #     experiment_id=experiment.experiment_id, parameter_name=parameter
            # ).update({"parameter_value": value})
            stmt = (
                update(ExperimentParameters)
                .where(
                    ExperimentParameters.experiment_id == experiment.experiment_id,
                    ExperimentParameters.parameter_name == parameter,
                )
                .values({"parameter_value": value})
            )
            session.execute(stmt)
            session.commit()
    except sqlite3.Error as e:
        logger.error("Error occurred while updating experiment parameters: %s", e)
        raise e


@timing_wrapper
def schedule_experiment(
    experiment: ExperimentBase, override_well_available=False
) -> int:
    """
    Deprecated function kept temporarily. It delegates to schedule_experiments.
    """
    return schedule_experiments([experiment], override=override_well_available)


def validate_experiment_plate(experiment: ExperimentBase) -> bool:
    """
    Checks if plate_id exists and matches the plate_type_number.
    Returns True if valid, otherwise False.
    """
    # Check if the experiment is for a specific plate, if not choose the current plate
    if experiment.plate_id is None:
        experiment.plate_id, _, _ = select_current_wellplate_info()
    # Check if the plate ID exists
    if not check_if_plate_type_exists(experiment.wellplate_type_id):
        logger.error(
            "Plate type %s does not exist, cannot add experiment to queue",
            experiment.plate_id,
        )
        print(
            f"Plate type {experiment.plate_id} does not exist, cannot add experiment to queue"
        )
        return False

    # Check if the target plate id has the target well type number
    plate_info = select_wellplate_info(experiment.plate_id)
    if plate_info is None:
        logger.error(
            "Plate %s does not exist, cannot add experiment %s AKA %s to queue",
            experiment.plate_id,
            experiment.experiment_id,
            experiment.experiment_name,
        )
        print(
            f"Plate {experiment.plate_id} does not exist, cannot add experiment {experiment.experiment_id} AKA {experiment.experiment_name} to queue"
        )
        return False

    if (
        plate_info.type_id != experiment.wellplate_type_id
        or plate_info.id != experiment.plate_id
    ):
        logger.error(
            "Plate %s does not have the correct well type number %s, cannot add experiment to queue",
            experiment.plate_id,
            experiment.wellplate_type_id,
        )
        print(
            f"Plate {experiment.plate_id} does not have the correct well type number {experiment.wellplate_type_id}, cannot add experiment to queue"
        )
        return False

    return True


def assign_well_if_unavailable(experiment: ExperimentBase) -> bool:
    """
    If the well is not 'new', attempts to assign another well
    Returns True if a well was assigned, otherwise False.
    """
    if check_well_status(experiment.well_id, experiment.plate_id) != "new":
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
            return False
        logger.info(
            "Experiment originally for well %s is now for well %s.",
            experiment.well_id,
            target_well,
        )
        experiment.well_id = target_well
    return True


@timing_wrapper
def schedule_experiments(
    experiments: list[
        Union[ExperimentBase, ExperimentGenerator, EchemExperimentGenerator]
    ],
    override: bool = False,
) -> int:
    """
    Schedules a list of experiments by assigning each to a wellplate well. Each experiment is assigned to an available well,
    validated for plate type, and checked for project ID. If the well is unavailable, the function will request user input
    unless the override flag is set.

    Args:
        experiments (list[Union[ExperimentBase, ExperimentGenerator, EchemExperimentGenerator]]):
            A list of experiments to be added to the queue. Can be base experiment types or generator types.
        override (bool, optional): If True, overrides the well selection process. Defaults to False.
    Returns:
        int: The number of experiments successfully added to the queue.
    Raises:
        sqlite3.Error: If an error occurs while inserting experiments or their parameters into the database.
    """
    if len(experiments) == 0:
        logger.info("No experiments to add to queue")
        return 0

    # Convert any generator types to their respective base types
    converted_experiments = []
    for experiment in experiments:
        if not isinstance(experiment, (ExperimentBase, ExperimentGenerator)):
            logger.error(
                "Experiment %s is not a valid experiment type, skipping",
                str(experiment),
            )
            print(f"Experiment {str(experiment)} is not a valid experiment type")
            continue
        if experiment.experiment_id is None:
            experiment.experiment_id = select_next_experiment_id()
        if isinstance(experiment, EchemExperimentGenerator):
            converted_experiments.append(experiment.to_echem_experiment_base())
        elif isinstance(experiment, ExperimentGenerator):
            converted_experiments.append(experiment.to_experiment_base())
        else:
            converted_experiments.append(experiment)

    experiments = converted_experiments

    for experiment in experiments:
        try:
            override = experiment.override_well_selection
        except AttributeError:
            pass

        if not override:
            ## First check the existing status, if not new or queued, then do not add to queue
            if experiment.status not in [
                ExperimentStatus.NEW,
                ExperimentStatus.QUEUED,
            ]:
                message = f"Experiment {experiment.experiment_id} is not new or queued, not adding to queue"
                logger.info(message)
                print(message)
                experiments.remove(experiment)

            if not validate_experiment_plate(experiment):
                experiments.remove(experiment)
                continue

            if not assign_well_if_unavailable(experiment):
                experiments.remove(experiment)
                continue

        # Check if the project_id is in the projects table, if not add it
        if not check_project_id(experiment.project_id):
            add_project_id(experiment.project_id)

        # Data clean the solutions to all be lowercase
        experiment.solutions = {
            k.lower().strip(): v for k, v in experiment.solutions.items()
        }

        # Individually insert the experiment and update the status
        # We do this so that the wellchecker is checking as the wells are allocated
        # The parameters are quite lengthy, so we will save those for a bulk entry
        try:
            insert_experiments([experiment])
            update_experiment_status(experiment, ExperimentStatus.QUEUED)
        except (sqlite3.IntegrityError, sqlalchemy.exc.IntegrityError) as e:
            if "UNIQUE" in str(e):
                logger.info(
                    "Experiment %s already exists in the experiments table, skipping",
                    experiment.experiment_id,
                )
                print(
                    f"Experiment {experiment.experiment_id} already exists in the experiments table, skipping"
                )
                experiments.remove(experiment)
                continue

        except (sqlite3.Error, sqlalchemy.exc.SQLAlchemyError) as e:
            logger.error(
                "Error occurred while adding the experiment to experiments table: %s. The statements have been rolled back and nothing has been added to the tables.",
                e,
            )
            print(
                "The statements have been rolled back and nothing has been added to the tables."
            )
            experiments.remove(experiment)
            continue

    # Add the experiment to experiments table
    try:
        # Bulk add the experiment parameters to the experiment_parameters table
        insert_experiments_parameters(experiments)

    except sqlite3.Error as e:
        logger.error(
            "Error occurred while adding the experiment parameters to experiment_parameters table: %s. The statements have been rolled back and nothing has been added to the tables.",
            e,
        )
        print(
            "The statements have been rolled back and nothing has been added to the tables."
        )
        raise e

    logger.info("Experiments loaded and added to queue")
    return len(experiments)


@timing_wrapper
def check_project_id(project_id: int) -> bool:
    """Check if the project_id is in the projects table"""
    try:
        with SessionLocal() as session:
            project = session.scalars(select(Projects).filter_by(id=project_id)).first()
            if project is None:
                return False
            return True
    except sqlite3.Error as e:
        logger.error("Error occurred while checking project id: %s", e)
        raise e


@timing_wrapper
def add_project_id(project_id: int) -> None:
    """Add the project_id to the projects table when an experiment is submitted with an unrecongized project_id"""
    try:
        with SessionLocal() as session:
            session.add(Projects(id=project_id))
            session.commit()
    except sqlite3.Error as e:
        logger.error("Error occurred while adding project id: %s", e)
        raise e


@timing_wrapper
def determine_next_experiment_id() -> int:
    """FIX ME: This is used in many places but should be changed to directly call the sql function"""
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
