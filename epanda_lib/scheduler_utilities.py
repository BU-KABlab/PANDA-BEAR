"""Utilities for the scheduler"""

import logging
import random
import sqlite3
from pathlib import Path
from typing import Tuple

import pandas as pd

from .experiment_class import ExperimentBase, parse_experiment
from .config.config import PATH_TO_EXPERIMENT_QUEUE

DB_LOCATION = "data/epanda_db.db"
TABLE_NAME = "queue"

logger = logging.getLogger("scheduler")


def get_queue_length():
    """
    Get the length of the queue.

    Args:
        None

    Returns:
        int: The length of the queue.
    """
    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    # Get the length of the queue
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    queue_length = cursor.fetchone()[0]

    conn.close()

    return queue_length


# def determine_next_experiment_id():
#     """
#     Determine the next experiment id.
#     """
#     conn = sqlite3.connect(db_location)
#     cursor = conn.cursor()

#     # Get the id of the last experiment
#     cursor.execute("SELECT id FROM experiments ORDER BY id DESC LIMIT 1")
#     last_experiment_id = cursor.fetchone()

#     conn.close()

#     if last_experiment_id:
#         return last_experiment_id[0] + 1
#     else:
#         return 1


def get_queue_list() -> pd.DataFrame:
    """
    Get a dataframe of experiments in the queue.

    Args:
        None

    Returns:
        pd.DataFrame: The experiments in the queue.
    """
    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    # Get the experiments in the queue
    cursor.execute(f"SELECT * FROM {TABLE_NAME}")
    queue = cursor.fetchall()
    queue_df = pd.DataFrame(queue, columns=["id", "experiment_id", "priority"])

    conn.close()

    return queue_df


def add_to_queue(experiment_id: int, priority: int):
    """
    Add an experiment to the queue.

    Args:
        experiment_id (int): The id of the experiment.
        priority (int): The priority of the experiment.

    Returns:
        None
    """
    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    # Add the experiment to the queue
    cursor.execute(
        f"INSERT INTO {TABLE_NAME} (experiment_id, priority) VALUES (?, ?)",
        (experiment_id, priority),
    )
    conn.commit()

    conn.close()


def remove_from_queue(experiment_id: int):
    """
    Remove an experiment from the queue.

    Args:
        experiment_id (int): The id of the experiment.

    Returns:
        None
    """
    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    # Remove the experiment from the queue
    cursor.execute(
        f"DELETE FROM {TABLE_NAME} WHERE experiment_id = ?", (experiment_id,)
    )
    conn.commit()

    conn.close()


def get_next_experiment() -> int:
    """
    Get the next experiment in the queue.

    Args:
        None

    Returns:
        int: The id of the next experiment.
    """
    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    # Get the next experiment in the queue
    cursor.execute(
        f"SELECT experiment_id FROM {TABLE_NAME} ORDER BY priority DESC, id ASC LIMIT 1"
    )
    next_experiment = cursor.fetchone()

    conn.close()

    if next_experiment:
        return next_experiment[0]
    else:
        return None


def update_queue_priority(experiment_id: int, priority: int):
    """
    Update the priority of an experiment in the queue.

    Args:
        experiment_id (int): The id of the experiment.
        priority (int): The priority of the experiment.

    Returns:
        None
    """
    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    # Update the priority of the experiment in the queue
    cursor.execute(
        f"UPDATE {TABLE_NAME} SET priority = ? WHERE experiment_id = ?",
        (priority, experiment_id),
    )
    conn.commit()

    conn.close()


def clear_queue():
    """
    Clear the queue.

    Args:
        None

    Returns:
        None
    """
    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    # Clear the queue
    cursor.execute(f"DELETE FROM {TABLE_NAME}")
    conn.commit()

    conn.close()

def read_next_experiment_from_queue(
    random_pick: bool = True
) -> Tuple[ExperimentBase, Path]:
    """
    Reads the next experiment from the queue.
    :return: The next experiment.
    """
    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    # Get the experiment with the highest priority (lowest number)
    cursor.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY priority ASC LIMIT 1")
    next_experiment = cursor.fetchone()

    conn.close()

    if not next_experiment:
        logger.info("No experiments in queue")
        return None, None

    experiment_id, priority = next_experiment[1], next_experiment[2]

    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    # Get all experiments with the highest priority
    cursor.execute(
        f"SELECT experiment_id FROM {TABLE_NAME} WHERE priority = ?", (priority,)
    )
    experiments = cursor.fetchall()
    experiments_list = [experiment[0] for experiment in experiments]

    conn.close()

    if not Path.exists(PATH_TO_EXPERIMENT_QUEUE):
        logger.error("experiment_queue folder not found")
        raise FileNotFoundError("experiment queue folder")

    if random_pick:
        # Pick a random experiment from the list of experiments with the highest priority
        random_experiment = random.choice(experiments_list)
        experiment_file_path = Path(
            PATH_TO_EXPERIMENT_QUEUE / random_experiment
        ).with_suffix(".json")
        if not Path.exists(experiment_file_path):
            logger.error("experiment file not found")
            raise FileNotFoundError("experiment file")
    else:
        # Sort the queue by experiment id and then by priority, excluding type 2 protocols
        conn = sqlite3.connect(DB_LOCATION)
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT experiment_id FROM {TABLE_NAME} ORDER BY id ASC, priority ASC LIMIT 1"
        )
        first_experiment = cursor.fetchone()

        conn.close()

        if not first_experiment:
            logger.error("experiment file not found")
            raise FileNotFoundError("experiment file")

        experiment_file_path = Path(
            PATH_TO_EXPERIMENT_QUEUE / first_experiment[0]
        ).with_suffix(".json")
        if not Path.exists(experiment_file_path):
            logger.error("experiment file not found")
            raise FileNotFoundError("experiment file")

    # Read the experiment file
    with open(experiment_file_path, "r", encoding="ascii") as experiment_file:
        experiment: ExperimentBase = parse_experiment(experiment_file.read())

    # Remove the selected experiment from the queue
    conn = sqlite3.connect(DB_LOCATION)
    cursor = conn.cursor()

    cursor.execute(
        f"DELETE FROM {TABLE_NAME} WHERE experiment_id = ?", (experiment_id,)
    )
    conn.commit()

    conn.close()

    logger.info("Experiment %s read from queue", experiment.id)

    return experiment, experiment_file_path
