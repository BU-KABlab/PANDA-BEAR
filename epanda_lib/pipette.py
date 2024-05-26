from decimal import Decimal, getcontext
import json

from epanda_lib.vessel import logger as vessel_logger
from epanda_lib.sql_tools.sql_pipette import (
    insert_pipette_status,
    select_pipette_status,
)

getcontext().prec = 6


class Pipette:
    """Class for storing pipette information"""

    def __init__(self, capacity_ul: Decimal = Decimal(0.0)):
        """Initialize the pipette"""
        if capacity_ul is not None and capacity_ul > 0:
            self.capacity_ul: Decimal = capacity_ul
            self.capacity_ml: Decimal = capacity_ul / Decimal(
                1000
            )  # convert capacity to ml, Decimal division by int is OK
            self._volume_ul: Decimal = Decimal(0.0)
            self._volume_ml: Decimal = Decimal(0.0)
            self.contents = {}
        # self.state_file = PATH_TO_SYSTEM_STATE / "pipette_state.csv"
        else:
            self.read_state_file()
        self.log_contents()

    def set_capacity(self, capacity_ul: Decimal) -> None:
        """Set the capacity of the pipette in ul"""
        if capacity_ul < 0:
            raise ValueError("Capacity must be non-negative.")
        self.capacity_ul = Decimal(capacity_ul)
        self.capacity_ml = capacity_ul / Decimal(1000)
        self.update_state_file()

    def update_contents(self, solution: str, volume_change: Decimal) -> None:
        """Update the contents of the pipette"""
        self.contents[solution] = self.contents.get(solution, 0) + volume_change
        self.log_contents()

    @property
    def volume(self) -> Decimal:
        """Get the volume of the pipette in ul"""
        return self._volume_ul

    @volume.setter
    def volume(self, volume: Decimal) -> None:
        """Set the volume of the pipette in ul"""
        if volume < 0:
            raise ValueError("Volume must be non-negative.")
        self._volume_ul = volume
        self._volume_ml = volume / Decimal(1000)
        self.log_contents()

    @property
    def volume_ml(self) -> Decimal:
        """Get the volume of the pipette in ml"""
        return self._volume_ml

    @volume_ml.setter
    def volume_ml(self, volume: Decimal) -> None:
        """Set the volume of the pipette in ml"""
        if volume < 0:
            raise ValueError("Volume must be non-negative.")
        self._volume_ml = volume
        self._volume_ul = volume * Decimal(1000)

        self.log_contents()

    def liquid_volume(self) -> Decimal:
        """Get the volume of liquid in the pipette in ul

        Sum the volume of the pipette contents

        Returns:
            float: The volume of liquid in the pipette in ul
        """
        return sum(self.contents.values())

    def reset_contents(self) -> None:
        """Reset the contents of the pipette"""
        self.contents = {}
        self._volume_ul = Decimal(0)
        self._volume_ml = Decimal(0)
        self.log_contents()

    def log_contents(self) -> None:
        """Log the contents of the pipette"""
        vessel_logger.info(
            "%s&%s&%s",
            "pipette",
            self._volume_ul,
            self.contents,
        )
        self.update_state_file()

    # def update_state_file(self) -> None:
    #     """Update the state file for the pipette"""
    #     file_name = self.state_file
    #     with open(file_name, "w", encoding="utf-8") as file:
    #         file.write(f"capacity_ul,{self.capacity_ul}\n")
    #         file.write(f"capacity_ml,{self.capacity_ml}\n")
    #         file.write(f"volume_ul,{self._volume_ul}\n")
    #         file.write(f"volume_ml,{self.volume_ml}\n")
    #         file.write("contents\n")
    #         for solution, volume in self.contents.items():
    #             file.write(f"{solution},{volume}\n")

    def update_state_file(self) -> None:
        """Update the state file for the pipette"""
        insert_pipette_status(
            self.capacity_ul,
            self.capacity_ml,
            self._volume_ul,
            self._volume_ml,
            json.dumps(self.contents, default=decimal_default),
        )

    # def read_state_file(self) -> None:
    #     """Read the state file for the pipette.
    #     If the file does not exist, it will be created, and the pipette will be reset to empty.
    #     If the file exists but is empty, the pipette will be reset to empty.
    #     """
    #     file_name = self.state_file
    #     if file_name.exists():
    #         with open(file_name, "r", encoding="utf-8") as file:
    #             lines = file.readlines()
    #             if len(lines) > 0:
    #                 for line in lines:
    #                     if "capacity_ul" in line:
    #                         self.capacity_ul = Decimal(line.split(",")[1])
    #                         self.capacity_ml = self.capacity_ul / 1000.0
    #                     elif "volume_ul" in line:
    #                         self._volume_ul = Decimal(line.split(",")[1])
    #                     elif "volume_ml" in line:
    #                         self._volume_ml = Decimal(line.split(",")[1])
    #                     elif "contents" in line:
    #                         self.contents = {}
    #                     else:
    #                         solution, volume = line.split(",")
    #                         self.contents[solution] = Decimal(volume)

    #     else:
    #         self.reset_contents()

    def read_state_file(self) -> None:
        """
        Select the current state of the pipette from the db
        """
        pipette_status = get_pieptte_status()
        if pipette_status is not None:
            self.capacity_ul = pipette_status.capacity_ul
            self.capacity_ml = self.capacity_ml
            self._volume_ul = pipette_status.volume
            self._volume_ml = pipette_status.volume_ml
            self.contents = pipette_status.contents
        else:
            self.reset_contents()

    def __str__(self):
        return f"Pipette has {self._volume_ul} ul of liquid"


def get_pieptte_status() -> Pipette:
    """Get the status of the pipette"""
    result = select_pipette_status()
    if result is None:
        return None
    pipette_status = PipetteStatus(Decimal(0), Decimal(0), Decimal(0), Decimal(0), {})
    pipette_status.capacity_ul = Decimal(result[0])
    pipette_status.capacity_ml = Decimal(result[1])
    pipette_status.volume = Decimal(result[2])
    pipette_status.volume_ml = Decimal(result[3])
    pipette_status.contents = json.loads(result[4]) if result[4] is not None else {}
    return pipette_status


class PipetteStatus:
    def __init__(
        self,
        capacity_ul: Decimal,
        capacity_ml: Decimal,
        volume: Decimal,
        volume_ml: Decimal,
        contents: dict,
    ):
        self.capacity_ul = capacity_ul
        self.capacity_ml = capacity_ml
        self.volume = volume
        self.volume_ml = volume_ml
        self.contents = contents


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError
