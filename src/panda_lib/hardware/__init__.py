from panda_shared.config.config_tools import read_testing_config

if read_testing_config():
    from .arduino_interface import MockArduinoLink as ArduinoLink
    from .gantry_interface import MockPandaMill as PandaMill
    from .sync_scale import MockSyncScale as Scale
else:
    from .arduino_interface import ArduinoLink
    from .gantry_interface import PandaMill
    from .sync_scale import SyncScale as Scale


__all__ = [
    "ArduinoLink",
    "MockArduinoLink",
    "MockPandaMill",
    "PandaMill",
    "Scale",
    "SyncScale",
]
