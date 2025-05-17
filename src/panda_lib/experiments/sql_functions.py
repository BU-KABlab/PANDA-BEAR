import json
from datetime import datetime
from typing import List, Union, get_type_hints

from sqlalchemy import select

from panda_lib.sql_tools import (
    ExperimentParameters,
    Experiments,
    WellModel,
    Wellplates,
)
from panda_shared.config.config_tools import read_config

# from panda_lib.sql_tools.sql_utilities import (execute_sql_command,
#                                                 execute_sql_command_no_return)
from panda_shared.db_setup import SessionLocal
from panda_shared.log_tools import setup_default_logger

from .experiment_parameters import ExperimentParameterRecord
from .experiment_status import ExperimentStatus
from .experiment_types import EchemExperimentBase, ExperimentBase

global_logger = setup_default_logger(log_name="panda")
experiment_logger = setup_default_logger(log_name="experiment_logger")
config = read_config()


def select_next_experiment_id() -> int:
    """Determines the next experiment id by checking the experiment table"""

    with SessionLocal() as session:
        result = (
            session.query(Experiments.experiment_id)
            .order_by(Experiments.experiment_id.desc())
            .first()
        )
    if result in [None, []]:
        return 1
    return result[0] + 1


def select_experiment_information(experiment_id: int) -> ExperimentBase:
    """
    Selects the experiment information from the experiments table.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        ExperimentBase: The experiment information.
    """

    with SessionLocal() as session:
        result = (
            session.query(Experiments)
            .filter(Experiments.experiment_id == experiment_id)
            .first()
        )

    if result is None:
        return None
    else:
        # With the project_id known to determine the experiment type
        # object type

        experiment = EchemExperimentBase()
        experiment.experiment_id = experiment_id
        experiment.project_id = result.project_id
        experiment.project_campaign_id = result.project_campaign_id
        experiment.wellplate_type_id = result.well_type
        experiment.protocol_name = result.protocol_id
        experiment.priority = result.priority
        experiment.filename = result.filename
        return experiment


def select_experiment_parameters(experiment_id) -> list:
    """
    Selects the experiment parameters from the experiment_parameters table.
    If an experiment_object is provided, the parameters are added to the object.

    Args:
        experiment_to_select (Union[int, EchemExperimentBase]): The experiment ID or object.

    Returns:
        EchemExperimentBase: The experiment parameters.
    """
    with SessionLocal() as session:
        result = (
            session.query(ExperimentParameters)
            .filter(ExperimentParameters.experiment_id == experiment_id)
            .all()
        )
    values = []
    for row in result:
        values.append(row)

    return values


def select_specific_parameter(experiment_id: int, parameter_name: str):
    """
    Select a specific parameter from the experiment_parameters table.

    Args:
        experiment_id (int): The experiment ID.
        parameter_name (str): The parameter name.

    Returns:
        any: The parameter value.
    """

    with SessionLocal() as session:
        result = (
            session.query(ExperimentParameters.parameter_value)
            .filter(ExperimentParameters.experiment_id == experiment_id)
            .filter(ExperimentParameters.parameter_name == parameter_name)
            .all()
        )

    if not result:
        return None
    return result[0][0]


def select_experiment_status(experiment_id: int) -> str:
    """
    Select the status of an experiment from the well_hx table.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        str: The status of the experiment.
    """

    with SessionLocal() as session:
        stmt = select(WellModel.status).where(WellModel.experiment_id == experiment_id)
        result = session.execute(stmt).fetchall()

    if result == []:
        return ValueError("No experiment found with that ID")
    return result[0][0]


def select_complete_experiment_information(experiment_id: int) -> ExperimentBase:
    """
    Selects the experiment information and parameters from the experiments and experiment_parameters tables.

    Args:
        experiment_id (int): The experiment ID.

    Returns:
        ExperimentBase: The experiment information and parameters.
    """

    experiment = select_experiment_information(experiment_id)
    if experiment is None:
        return None

    params = select_experiment_parameters(experiment_id)
    experiment.map_parameter_list_to_experiment(params)
    if experiment is None:
        return None

    return experiment


def insert_experiment(experiment: ExperimentBase) -> None:
    """
    Insert an experiment into the experiments table.

    Args:
        experiment (ExperimentBase): The experiment to insert.
    """
    insert_experiments([experiment])


def insert_experiments(experiments: List[ExperimentBase]) -> None:
    """
    Insert a list of experiments into the experiments table.

    Args:
        experiments (List[ExperimentBase]): The experiments to insert.
    """
    parameters = []
    for experiment in experiments:
        parameters.append(
            (
                experiment.experiment_id,
                experiment.project_id,
                experiment.project_campaign_id,
                experiment.wellplate_type_id,
                experiment.protocol_name,
                experiment.priority,
                experiment.filename,
                datetime.now().isoformat(timespec="seconds"),
            )
        )

    with SessionLocal() as session:
        for parameter in parameters:
            session.add(
                Experiments(
                    experiment_id=parameter[0],
                    project_id=parameter[1],
                    project_campaign_id=parameter[2],
                    well_type=parameter[3],
                    protocol_id=parameter[4],
                    priority=parameter[5],
                    filename=parameter[6],
                    created=datetime.strptime(parameter[7], "%Y-%m-%dT%H:%M:%S"),
                )
            )
        session.commit()


def insert_experiment_parameters(experiment: ExperimentBase) -> None:
    """
    Insert the experiment parameters into the experiment_parameters table.

    Args:
        experiment (ExperimentBase): The experiment to insert.
    """
    insert_experiments_parameters([experiment])


def insert_experiments_parameters(experiments: List[ExperimentBase]) -> None:
    """
    Insert the experiment parameters into the experiment_parameters table.

    Args:
        experiments (List[ExperimentBase]): The experiments to insert.
    """
    parameters_to_insert = []  # this will be a list of tuples of the parameters to insert
    for experiment in experiments:
        experiment_parameters: list[ExperimentParameterRecord] = (
            experiment.generate_parameter_list()
        )
        for parameter in experiment_parameters:
            parameters_to_insert.append(
                (
                    experiment.experiment_id,
                    parameter.parameter_name,
                    (
                        json.dumps(parameter.parameter_value, default=str)
                        if isinstance(parameter.parameter_value, dict)
                        else parameter.parameter_value
                    ),
                    datetime.now().isoformat(timespec="seconds"),
                )
            )

    with SessionLocal() as session:
        for parameter in parameters_to_insert:
            session.add(
                ExperimentParameters(
                    experiment_id=parameter[0],
                    parameter_name=parameter[1],
                    parameter_value=parameter[2],
                    created=datetime.strptime(parameter[3], "%Y-%m-%dT%H:%M:%S"),
                )
            )
        session.commit()


def update_experiment(experiment: ExperimentBase) -> None:
    """
    Update an experiment in the experiments table.

    Args:
        experiment (ExperimentBase): The experiment to update.
    """
    update_experiments([experiment])


def update_experiments(experiments: List[ExperimentBase]) -> None:
    """
    Update a list of experiments in the experiments table.

    Args:
        experiments (List[ExperimentBase]): The experiments to update.
    """
    parameters = []
    for experiment in experiments:
        parameters.append(
            (
                experiment.project_id,
                experiment.project_campaign_id,
                experiment.wellplate_type_id,
                experiment.protocol_name,
                experiment.priority,
                experiment.filename,
                experiment.experiment_id,
            )
        )

    with SessionLocal() as session:
        for parameter in parameters:
            session.query(Experiments).filter(
                Experiments.experiment_id == parameter[6]
            ).update(
                {
                    Experiments.project_id: parameter[0],
                    Experiments.project_campaign_id: parameter[1],
                    Experiments.well_type: parameter[2],
                    Experiments.protocol_id: parameter[3],
                    Experiments.priority: parameter[4],
                    Experiments.filename: parameter[5],
                }
            )
        session.commit()


def update_experiment_status(
    experiment: Union[ExperimentBase, int],
    status: ExperimentStatus = None,
    status_date: datetime = None,
) -> None:
    """
    Update the status of an experiment in the experiments table.

    When provided with an int, the experiment_id is the int, and the status and
    status_date are the other two arguments.
    If no status is provided, the function will not make assumptions and will do nothing.

    When provided with an ExperimentBase object, the object's attributes will be
    used to update the status.
    If an object is provided along with a status and status date, the object's
    attributes will be updated with the status and status date.

    Args:
        experiment_id (int): The experiment ID.
        status (ExperimentStatus): The status to update to.
    """
    # Handel the case where the experiment is passed as an object or an int
    # If it is an int, then the experiment_id is the int, and the status and the
    # status_date are the other two arguments
    # If it is an object, then use the experimentbase object for the data
    if isinstance(experiment, int):
        experiment_id = experiment
        if status is None:
            return
        if status_date is None:
            status_date = datetime.now().isoformat(timespec="seconds")

        experiment_info = select_experiment_information(experiment_id)
        project_id = experiment_info.project_id
        well_id = experiment_info.well_id

    else:
        experiment_id = experiment.experiment_id
        if status is not None:
            experiment.set_status(status)
        else:
            status = experiment.status
        if status_date is not None:
            experiment.status_date = status_date
        else:
            status_date = experiment.status_date
        project_id = experiment.project_id
        well_id = experiment.well_id

    with SessionLocal() as session:
        subquery = (
            session.query(Wellplates.id)
            .filter(Wellplates.current == 1)
            .scalar_subquery()
        )
        session.query(WellModel).filter(WellModel.well_id == well_id).filter(
            WellModel.plate_id == subquery
        ).update(
            {
                WellModel.status: status.value,
                WellModel.status_date: status_date,
                WellModel.experiment_id: experiment_id,
                WellModel.project_id: project_id,
            }
        )
        session.commit()


def update_experiments_statuses(
    experiments: List[ExperimentBase],
    exp_status: ExperimentStatus,
    status_date: datetime = None,
) -> None:
    """
    Set the status of a list of experiments in the well_hx table.

    Args:
        experiments (List[ExperimentBase]): The experiments to set the status for.
        status (ExperimentStatus): The status to set for the experiments.
        status_date (datetime): The status date to set for the experiments.
    """
    if status_date is None:
        status_date = datetime.now().isoformat(timespec="seconds")

    for experiment in experiments:
        experiment.set_status(exp_status)

    parameters = [
        (
            exp_status.value,
            status_date,
            experiment.experiment_id,
            experiment.project_id,
            experiment.well_id,
        )
        for experiment in experiments
    ]
    # execute_sql_command_no_return(
    #     """
    #     UPDATE well_hx
    #     SET status = ?,
    #     status_date = ?,
    #     experiment_id = ?,
    #     project_id = ?
    #     WHERE well_id = ?
    #     AND plate_id = (SELECT id FROM wellplates WHERE current = 1)
    #     """,
    #     parameters,
    # )

    with SessionLocal() as session:
        for parameter in parameters:
            session.query(WellModel).filter(WellModel.well_id == parameter[4]).filter(
                WellModel.plate_id
                == session.query(Wellplates.id).filter(Wellplates.current == 1)
            ).update(
                {
                    WellModel.status: parameter[0],
                    WellModel.status_date: parameter[1],
                    WellModel.experiment_id: parameter[2],
                    WellModel.project_id: parameter[3],
                }
            )
        session.commit()


def get_all_type_hints(cls):
    """Get all type hints for a class"""
    hints = {}
    for base in reversed(cls.__mro__):
        hints.update(get_type_hints(base))
    return hints
