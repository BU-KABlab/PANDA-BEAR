from enum import Enum

from .experiment_parameters import ExperimentParameterRecord
from .experiment_types import EchemExperimentBase, ExperimentBase
from .results import ExperimentResult, ExperimentResultsRecord
from .sql_functions import (
    insert_experiment,
    insert_experiment_parameters,
    insert_experiments,
    insert_experiments_parameters,
    select_complete_experiment_information,
    select_experiment_information,
    select_experiment_parameters,
    select_experiment_status,
    select_next_experiment_id,
    select_specific_parameter,
    update_experiment,
    update_experiment_status,
    update_experiments,
    update_experiments_statuses,
)


class ExperimentStatus(str, Enum):
    """Define the possible statuses of an experiment"""

    NEW = "new"
    QUEUED = "queued"
    RUNNING = "running"
    OCPCHECK = "ocpcheck"
    DEPOSITING = "depositing"
    EDEPOSITING = "e_depositing"
    RINSING = "rinsing"
    ERINSING = "rinsing electrode"
    BASELINE = "baselining"
    CHARACTERIZING = "characterizing"
    CA = "cyclic-amperometry"
    CV = "cyclic-voltametry"
    FINAL_RINSE = "final_rinse"
    COMPLETE = "complete"
    ERROR = "error"
    MIXING = "mixing"
    IMAGING = "imaging"
    CLEARING = "clearing"
    FLUSHING = "flushing"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PENDING = "pending"  # pending experiments either are waiting for a well to be assigned or lack the correct well type
    SAVING = "saving"
    ANALYZING = "analyzing"
    MOVING = "moving"
    PIPETTING = "pipetting"


__all__ = [
    "ExperimentStatus",
    "EchemExperimentBase",
    "ExperimentResult",
    "ExperimentResultsRecord",
    "ExperimentBase",
    "ExperimentParameterRecord",
    "insert_experiment",
    "insert_experiment_parameters",
    "insert_experiments",
    "insert_experiments_parameters",
    "select_complete_experiment_information",
    "select_experiment_information",
    "select_experiment_parameters",
    "select_experiment_status",
    "select_next_experiment_id",
    "select_specific_parameter",
    "update_experiment",
    "update_experiment_status",
    "update_experiments",
    "update_experiments_statuses",
]
