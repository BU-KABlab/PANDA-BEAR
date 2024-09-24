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
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import Queue


def select_queue() -> list:
    """
    Selects all the entries from the queue table.

    Returns:
        list: The entries from the queue table.
    """
    # result = execute_sql_command(
    #     """
    #     SELECT
    #         experiment_id,
    #         process_type,
    #         priority,
    #         well_id,
    #         filename
    #     FROM queue
    #     ORDER BY experiment_id ASC
    #     """
    # )
    # return result

    with SessionLocal() as session:
        return session.query(Queue).order_by(Queue.priority, Queue.experiment_id).all()


def get_next_experiment_from_queue(random_pick: bool = False, specific_experiment_id:int = None) -> tuple[int, int, str]:
    """
    Reads the next experiment from the queue table, the experiment with the
    highest priority (lowest value).

    If random_pick, a random experiment with highest priority (lowest value) is selected.
    Else, the lowest experiment id with the highest priority (lowest value) is selected.

    Args:
        random_pick (bool): Whether to pick a random experiment from the queue.

    Returns:
        tuple: The experiment ID, the process type, and the filename.
    """
    
    if specific_experiment_id:
        with SessionLocal() as session:
            result = (
                session.query(Queue)
                .filter(Queue.experiment_id == specific_experiment_id)
                .first()
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

    with SessionLocal() as session:
        if random_pick:
            result = (
                session.query(Queue)
                .filter(Queue.status == "queued")
                .order_by(Queue.priority)
                .first()
            )
        else:
            result = (
                session.query(Queue)
                .filter(Queue.status == "queued")
                .order_by(Queue.priority, Queue.experiment_id)
                .first()
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


def clear_queue() -> None:
    """Go through and change the status of any queued experiment to pending"""
    # execute_sql_command_no_return(
    #     """
    #     UPDATE well_hx SET status = 'pending'
    #     WHERE status = 'queued'
    #     """
    # )

    with SessionLocal() as session:
        session.query(Queue).filter(Queue.status == "queued").update(
            {Queue.status: "pending"}
        )
        session.commit()


def count_queue_length() -> int:
    """Count the number of experiments in the queue"""

    with SessionLocal() as session:
        return session.query(Queue).filter(Queue.status == "queued").count()


# endregion
