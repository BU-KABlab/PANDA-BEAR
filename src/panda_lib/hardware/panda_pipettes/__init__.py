"""This module is used to control the pipette. It is used to get the status of the pipette and to set the status of the pipette."""

from panda_shared.config.config_tools import read_config_value, read_testing_config

from .pipette import PipetteDBHandler
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

pipette_type = str(read_config_value("PIPETTE", "pipette_type")).upper()
if pipette_type == "WPI":
    if read_testing_config():
        from .wpi_syringe_pump.syringepump import MockPump as Pipette
    else:
        from .wpi_syringe_pump.syringepump import SyringePump as Pipette

elif pipette_type == "OT2P300":
    if read_testing_config():
        from .ot2_pipette.ot2P300 import MockOT2P300 as Pipette
    else:
        from .ot2_pipette.ot2P300 import OT2P300 as Pipette

else:
    raise ValueError(f"Invalid pipette type: {pipette_type}")


__all__ = [
    "Pipette",
    "MockPipette",
    "PipetteDBHandler",
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
