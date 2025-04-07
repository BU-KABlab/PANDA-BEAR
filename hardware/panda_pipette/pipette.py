"""Module for the pipette class"""

import json
import logging
import time

from hardware.panda_pipette.sql_pipette import (
    SessionLocal,
    activate_pipette,
    deincrement_use_count,
    select_pipette_status,
    sessionmaker,
    update_pipette_status,
)

from .errors import InvalidPipetteID

vessel_logger = logging.getLogger("vessel_logger")


class Pipette:
    """Class for storing pipette information"""

    def __init__(
        self, pipette_id: int = None, db_session_maker: sessionmaker = SessionLocal
    ):
        """Initialize the pipette"""
        self.capacity_ul: float = 0.0
        self.capacity_ml: float = 0.0
        self._volume_ul: float = 0.0
        self._volume_ml: float = 0.0
        self.contents = {}
        self.id = pipette_id
        self.uses = 0
        self.panda_unit_id = 99
        self.session_maker: sessionmaker = db_session_maker

        if self.id is not None and (self.id <= 0 or not isinstance(self.id, int)):
            raise InvalidPipetteID("Pipette ID must be a positive integer")

        self.read_state_file()
        self.log_contents()

    def set_capacity(self, capacity_ul: float) -> None:
        """Set the capacity of the pipette in ul"""
        if capacity_ul < 0:
            raise ValueError("Capacity must be non-negative.")
        self.capacity_ul = round(float(capacity_ul), 6)
        self.capacity_ml = round(float(capacity_ul) / 1000, 6)
        self.record_pipette_state()

    def update_contents(self, solution: str, volume_change: float) -> None:
        """Update the contents of the pipette"""
        self.contents[solution] = round(
            float(self.contents.get(solution, 0)) + volume_change, 6
        )
        self._volume_ul += volume_change
        self.record_pipette_state()
        time.sleep(0.01)

    @property
    def volume(self) -> float:
        """Get the volume of the pipette in ul"""
        return self._volume_ul

    @volume.setter
    def volume(self, volume: float) -> None:
        """Set the volume of the pipette in ul"""
        if volume < 0:
            raise ValueError("Volume must be non-negative.")
        self._volume_ul = round(float(volume), 6)
        self.log_contents()
        self.record_pipette_state()
        time.sleep(0.01)

    @property
    def volume_ml(self) -> float:
        """Get the volume of the pipette in ml"""
        return self.volume / 1000

    @volume_ml.setter
    def volume_ml(self, volume: float) -> None:
        """Set the volume of the pipette in ml"""
        if volume < 0:
            raise ValueError("Volume must be non-negative.")
        self.volume = round(float(volume) * 1000, 6)
        # self.log_contents()
        # self.record_pipette_state()

    def liquid_volume(self) -> float:
        """Get the volume of liquid in the pipette in ul

        Sum the volume of the pipette contents

        Returns:
            float: The volume of liquid in the pipette in ul
        """
        return round(sum(self.contents.values()), 6)

    def reset_contents(self) -> None:
        """Reset the contents of the pipette"""
        self.contents = {}
        self._volume_ul = 0.0
        self._volume_ml = 0.0
        self.log_contents()
        self.record_pipette_state()
        # Resetting the contents triggers the use counter to still increment
        # We need to deduct the use counter by 1
        deincrement_use_count(self.id, self.session_maker)

    def log_contents(self) -> None:
        """Log the contents of the pipette"""
        vessel_logger.debug(
            "%s&%s&%s",
            "pipette",
            self._volume_ul,
            self.contents,
        )
        # print(f"Pipette has {self._volume_ul} ul of liquid")

    def record_pipette_state(self) -> None:
        """Update the state file for the pipette"""
        update_pipette_status(
            self.capacity_ul,
            self.capacity_ml,
            self.volume,
            self.volume_ml,
            json.dumps(self.contents),
            self.id,
            self.session_maker,
        )

    def read_state_file(self) -> None:
        """
        Select the current state of the pipette from the db
        """

        if self.id is None:
            pipette_status = select_pipette_status(session_maker=self.session_maker)
            if pipette_status is not None:
                self.id = pipette_status.id
                self.capacity_ul = round(float(pipette_status.capacity_ul), 6)
                self.capacity_ml = round(float(pipette_status.capacity_ml), 6)
                self._volume_ul = round(float(pipette_status.volume_ul), 6)
                self._volume_ml = round(float(pipette_status.volume_ml), 6)
                self.contents = (
                    pipette_status.contents
                    if pipette_status.contents is not None
                    else {}
                )
            else:
                raise InvalidPipetteID("No pipette found in the database")

        else:
            pipette_status = select_pipette_status(self.id, self.session_maker)
            if pipette_status is not None:
                self.capacity_ul = round(float(pipette_status.capacity_ul), 6)
                self.capacity_ml = round(float(pipette_status.capacity_ml), 6)
                self._volume_ul = round(float(pipette_status.volume_ul), 6)
                self._volume_ml = round(float(pipette_status.volume_ml), 6)
                self.contents = pipette_status.contents

                if pipette_status.active == 0:
                    print(f"Pipette with id {self.id} is inactive.")
                    activate = input("Do you want to activate it? (y/n): ")
                    if activate.lower() == "y":
                        self.activate()
                    else:
                        print("Pipette will remain inactive.")

            else:
                raise InvalidPipetteID(f"""
                                 Pipette with id {self.id} does not exist.
                                 
                                 Please create a pipette with the given id before using it.
                                 """)

    def activate(self):
        """Activate the pipette"""
        activate_pipette(self.id, self.session_maker)

    def __str__(self):
        return f"Pipette has {self._volume_ul} ul of liquid"
