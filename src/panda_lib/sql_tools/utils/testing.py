"""
SQL Tools Testing Utilities

This module contains utilities for managing test data in the database.
"""

from sqlalchemy import delete, select

from panda_shared.config.config_tools import get_unit_id
from panda_shared.db_setup import SessionLocal

from ..models import Experiments


def remove_test_experiments() -> int:
    """
    Remove all test experiments from the database.

    Returns:
        The number of experiments removed
    """
    unit_id = get_unit_id()

    with SessionLocal() as session:
        # Get experiment IDs that are marked as testing
        stmt = select(Experiments.experiment_id).where(
            Experiments.panda_unit_id == unit_id,
            Experiments.project_id == 999,
            # Experiments.is_test == True,  # noqa: E712
        )
        test_experiment_ids = session.scalars(stmt).all()

        # If no test experiments, return early
        if not test_experiment_ids:
            return 0

        # Delete test experiments
        delete_stmt = delete(Experiments).where(
            Experiments.experiment_id.in_(test_experiment_ids)
        )
        session.execute(delete_stmt)

        # Delete related data in other tables
        # (In a real implementation, you'd delete from all related tables or use cascade)

        session.commit()

        return len(test_experiment_ids)


# def mark_as_test_experiment(experiment_id: int) -> bool:
#     """
#     Mark an experiment as a test experiment.

#     Args:
#         experiment_id: The ID of the experiment to mark

#     Returns:
#         True if successful, False otherwise
#     """
#     with SessionLocal() as session:
#         experiment = session.get(Experiments, experiment_id)
#         if not experiment:
#             return False

#         experiment.is_test = True
#         session.commit()

#         return True
