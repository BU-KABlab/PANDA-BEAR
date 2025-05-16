from shared_utilities.config.config_tools import read_testing_config

if read_testing_config():
    from sartorius.mock import Scale

    from .arduino_interface import MockArduinoLink as ArduinoLink
    from .gantry_interface import MockPandaMill as PandaMill
else:
    from sartorius import Scale

    from .arduino_interface import ArduinoLink
    from .gantry_interface import PandaMill

__all__ = [
    "ArduinoLink",
    "MockArduinoLink",
    "MockPandaMill",
    "PandaMill",
    "Scale",
]
