import os

from . import errors, timer

if os.name == "nt":
    from . import gamry_control
else:
    from . import gamry_control_mock
    from . import gamry_control_mock as gamry_control

__all__ = ["timer", "errors", "gamry_control", "gamry_control_mock"]
