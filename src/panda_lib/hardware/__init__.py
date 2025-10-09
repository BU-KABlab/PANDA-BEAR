from panda_shared.config.config_tools import read_testing_config

if read_testing_config():
    from .arduino_interface import MockArduinoLink as ArduinoLink
    from .gantry_interface import MockPandaMill as PandaMill
else:
    from .arduino_interface import ArduinoLink
    from .gantry_interface import PandaMill


__all__ = [
    "ArduinoLink",
    "MockArduinoLink",
    "MockPandaMill",
    "PandaMill",
]
