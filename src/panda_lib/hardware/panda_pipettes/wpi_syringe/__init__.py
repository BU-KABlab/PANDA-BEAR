"""This module is used to control the pipette. It is used to get the status of the pipette and to set the status of the pipette."""

from .syringepump import MockPump, SyringePump

__all__ = ["MockPump", "SyringePump"]
