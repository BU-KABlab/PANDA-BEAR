"""This module is used to control the pipette. It is used to get the status of the pipette and to set the status of the pipette."""

from shared_utilities.config.config_tools import read_config_value

from .sql_pipette import Pipette as PipetteModel
from .sql_pipette import (
    activate_pipette,
    deincrement_use_count,
    insert_new_pipette,
    select_current_pipette_id,
    select_current_pipette_uses,
    select_pipette_status,
    update_pipette_status,
)
from .state import PipetteState

pipette_type = read_config_value("PIPETTE", "PIPETTE_TYPE")
if pipette_type == "WPI":
    from .wpi_syringe.pipette import Pipette

elif pipette_type == "OT2":
    from .ot2_pipette.pipette import Pipette

else:
    raise ValueError(f"Invalid pipette type: {pipette_type}")


__all__ = [
    "Pipette",
    "PipetteModel",
    "PipetteState",
    "activate_pipette",
    "deincrement_use_count",
    "insert_new_pipette",
    "select_current_pipette_id",
    "select_current_pipette_uses",
    "select_pipette_status",
    "update_pipette_status",
]
