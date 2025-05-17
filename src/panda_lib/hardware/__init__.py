from shared_utilities.config.config_tools import read_testing_config

if read_testing_config():
    from .sync_scale import MockSyncScale as Scale

    from .arduino_interface import MockArduinoLink as ArduinoLink
    from .gantry_interface import MockPandaMill as PandaMill
else:
    from .sync_scale import SyncScale as Scale

    from .arduino_interface import ArduinoLink
    from .gantry_interface import PandaMill


__all__ = [
    "ArduinoLink",
    "MockArduinoLink",
    "MockPandaMill",
    "PandaMill",
    "Scale",
    "SyncScale",
]
