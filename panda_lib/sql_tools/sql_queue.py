"""
SQL Queue Functions

This module contains functions for interacting with the queue table in the database.
The queue table is used to store experiments that are waiting to be processed.

Note the queue is a view and not a table, so it cannot be updated directly.
Instead the well_hx table is updated with the experiment_id and status.
If the status is 'queued' then the experiment is in the queue.
Otherwise the experiment is not in the queue.

"""

# region Queue Functions


# TODO in the future experiments in the experiments table that are not matched to a well
# in the well_hx table should be added to the queue in some manner but this is not implemented yet.

# from panda_lib.sql_tools.sql_utilities import execute_sql_command, execute_sql_command_no_return
import random

from sqlalchemy import and_, select

from shared_utilities.db_setup import SessionLocal


class Queue:
    def __init__(
        self,
        experiment_id: int,
        project_id: int,
        project_campaign_id: int,
        priority: int,
        process_type: str,
        filename: str,
        well_type: str,
        well_id: int,
        status: str,
        status_date: str,
    ):
        self.experiment_id = experiment_id
        self.project_id = project_id
        self.project_campaign_id = project_campaign_id
        self.priority = priority
        self.process_type = process_type
        self.filename = filename
        self.well_type = well_type
        self.well_id = well_id
        self.status = status
        self.status_date = status_date


def select_queue() -> list:
    """
    Selects all the entries from the queue table.

    Returns:
        list: The entries from the queue table.
    """
    from .panda_models import (
        Experiments,
        WellModel,
        Wellplates,
    )

    with SessionLocal() as session:
        stmt = (
            select(
                Experiments.experiment_id,
                Experiments.project_id,
                Experiments.project_campaign_id,
                Experiments.priority,
                Experiments.process_type,
                Experiments.filename,
                Wellplates.id,
                Experiments.well_type,
                WellModel.well_id,
                WellModel.status,
                WellModel.status_date,
            )
            .join(
                Wellplates,
                Experiments.well_type == Wellplates.type_id,
            )
            .join(
                WellModel,
                and_(
                    WellModel.experiment_id == Experiments.experiment_id,
                    WellModel.plate_id == Wellplates.id,
                ),
            )
            .where(
                and_(
                    Wellplates.current == 1, WellModel.status.in_(["queued", "waiting"])
                )
            )
            .order_by(Experiments.priority, Experiments.experiment_id)
        )
        return session.execute(stmt).fetchall()


def get_next_experiment_from_queue(
    random_pick: bool = False, specific_experiment_id: int = None
) -> tuple[int, int, str, int, int]:
    """
    Reads the next experiment from the queue table, the experiment with the
    highest priority (lowest value).

    If random_pick, a random experiment with highest priority (lowest value) is selected.
    Else, the lowest experiment id with the highest priority (lowest value) is selected.

    Specific_experiment_id is used to select a specific experiment from the queue.
    This overrides random_pick.

    Args:
        random_pick (bool): Whether to pick a random experiment from the queue.
        specific_experiment_id (int): The experiment ID to select.

    Returns:
        tuple: The experiment ID, process type, filename, project ID, and well ID.
    """

    if specific_experiment_id:
        result_all = select_queue()
        result = [x for x in result_all if x.experiment_id == specific_experiment_id][0]
        if len(result) == 0:
            return None
        result = Queue(
            result.experiment_id,
            result.project_id,
            result.project_campaign_id,
            result.priority,
            result.process_type,
            result.filename,
            result.well_type,
            result.well_id,
            result.status,
            result.status_date,
        )
        if result is None:
            return None

        return (
            result.experiment_id,
            result.process_type,
            result.filename,
            result.project_id,
            result.well_id,
        )

    result = select_queue()
    if random_pick:
        result = select_queue()

        if len(result) == 0:
            return None

        random_index = random.randint(0, len(result) - 1)
        result = result[random_index]

    else:
        result = Queue(**result[0])

    if result is None:
        return None

    return (
        result.experiment_id,
        result.process_type,
        result.filename,
        result.project_id,
        result.well_id,
    )


# def clear_queue() -> None:
#     """Go through and change the status of any queued experiment to pending"""
#     # execute_sql_command_no_return(
#     #     """
#     #     UPDATE well_hx SET status = 'pending'
#     #     WHERE status = 'queued'
#     #     """
#     # )

#     with SessionLocal() as session:
#         session.query(Queue).filter(Queue.status == "queued").update(
#             {Queue.status: "pending"}
#         )
#         session.commit()


def count_queue_length() -> int:
    """Count the number of experiments in the queue"""

    return len(select_queue())


# endregion
