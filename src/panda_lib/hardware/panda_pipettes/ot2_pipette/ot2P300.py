"""
A class for controlling an OT2 P300 pipette via an Arduino while tracking vessel contents
"""

# pylint: disable=line-too-long, too-many-arguments, too-many-lines, too-many-instance-attributes, too-many-locals, import-outside-toplevel
from typing import Any, Dict, Optional, Union

from panda_lib.hardware.arduino_interface import ArduinoLink, MockArduinoLink
from panda_lib.labware import Vial
from panda_lib.labware import wellplates as wp
from shared_utilities.config.config_tools import read_config
from shared_utilities.log_tools import (
    default_logger as p300_control_logger,
)
from shared_utilities.log_tools import (
    setup_default_logger,
)

from ..pipette import PipetteDBHandler
from .pipette_driver import MockPipette, Pipette

vessel_logger = setup_default_logger(log_name="vessel")

config = read_config()
PRECISION = config.getint("OPTIONS", "precision")


class OT2P300:
    """
    OT2P300 class for controlling a pipette that integrates:
    1. ArduinoLink for hardware communication via pipette_driver
    2. PipetteDBHandler for volume/content tracking in the database
    3. Vessel integration for content tracking between vessels

    Attributes:
        arduino (ArduinoLink): Low-level Arduino communication interface
        pipette_driver (Pipette): Pipette driver for hardware control
        pipette_tracker (PipetteDBHandler): Database handler for tracking pipette state
        max_p300_rate (float): Maximum pipetting rate in µL/s
    """

    def __init__(self):
        """Initialize the OT2P300 Pipette interface."""
        # Set up Arduino connection
        self.arduino = ArduinoLink()

        # Configuration constants
        self.max_p300_rate = config.getfloat(
            "P300", "max_pipetting_rate", fallback=50.0
        )  # µL/s for Arduino pipette

        # Create pipette driver for hardware control
        self.pipette_driver = Pipette.from_config(
            stepper=self.arduino,
            config_file="P300_config.json",
        )

        # Confirm that the driver is initialized
        if not self.pipette_driver or not self.pipette_driver.stepper:
            p300_control_logger.error("Failed to initialize pipette driver")
            raise RuntimeError("Pipette driver initialization failed")

        # Set up database tracker for volumes and contents
        self.pipette_tracker = PipetteDBHandler()
        self.pipette_tracker.set_capacity(
            config.getfloat("P300", "pipette_capacity", fallback=300.0)
        )  # µL

        p300_control_logger.info("OT2P300 initialized")

    def __enter__(self):
        """Enter the context manager"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager"""
        self.close()

    def close(self):
        """Clean up resources - not much needed since Arduino cleanup happens at process exit"""
        p300_control_logger.info("OT2P300 closed")

    def aspirate(
        self,
        volume_to_aspirate: float,
        solution: Optional[Union[Vial, wp.Well]] = None,
        rate: Optional[float] = None,
    ) -> Optional[Union[Vial, wp.Well]]:
        """
        Aspirate the given volume at the given rate from the specified vessel.
        Update the volume of the pipette and the solution if given.

        Args:
            volume_to_aspirate (float): Volume to be aspirated in microliters.
            solution (Vessel object): The vial or well to aspirate from
            rate (float): Pumping rate in µL/second. None defaults to the max p300 rate.

        Returns:
            The updated solution object if given one
        """
        if not rate:
            rate = self.max_p300_rate
        if volume_to_aspirate <= 0:
            return None

        # Check if volume would exceed capacity
        if (
            self.pipette_tracker.volume + volume_to_aspirate
            > self.pipette_tracker.capacity_ul
        ):
            p300_control_logger.warning(
                f"Cannot aspirate {volume_to_aspirate} µL - would exceed pipette capacity"
            )
            return None

        # Use the pipette driver to aspirate
        success = self.pipette_driver.aspirate(vol=volume_to_aspirate, s=rate)

        if not success:
            p300_control_logger.error(f"Failed to aspirate {volume_to_aspirate} µL")
            return None

        # Update the database tracker with the volume change
        self.pipette_tracker.volume += volume_to_aspirate

        # If we have a solution, update the pipette contents and the solution volume
        if solution is not None and isinstance(solution, (Vial, wp.Well)):
            removed_contents = solution.remove_contents(volume_to_aspirate)
            for soln, vol in removed_contents.items():
                self.pipette_tracker.update_contents(soln, vol)

            p300_control_logger.debug(
                f"Aspirated: {volume_to_aspirate} µL at {rate} µL/s. Pipette vol: {self.pipette_tracker.volume} µL"
            )

        return solution

    def dispense(
        self,
        volume_to_dispense: float,
        being_infused: Optional[Union[Vial, wp.Well]] = None,
        infused_into: Optional[Union[Vial, wp.Well]] = None,
        rate: Optional[float] = None,
        blowout_ul: float = 0.0,
    ) -> None:
        """
        Dispense the given volume at the given rate.

        Args:
            volume_to_dispense (float): Volume to be dispensed in microliters.
            being_infused (Vial object): The solution being dispensed to get the density
            infused_into (str or Vial): The destination of the solution (well or vial)
            rate (float): Pumping rate in µL/second. None defaults to the max p300 rate.
            blowout_ul (float): The volume to blowout in microliters
        """
        if not rate:
            rate = self.max_p300_rate
        if volume_to_dispense <= 0:
            return None

        # Check if we have enough volume
        if self.pipette_tracker.volume < volume_to_dispense:
            p300_control_logger.warning(
                f"Cannot dispense {volume_to_dispense} µL - pipette only contains {self.pipette_tracker.volume} µL"
            )
            return None

        # Use the pipette driver to dispense
        success = self.pipette_driver.dispense(volume_to_dispense, rate)

        if not success:
            p300_control_logger.error(f"Failed to dispense {volume_to_dispense} µL")
            return None

        # If blowout is requested, perform it
        if blowout_ul > 0:
            blowout_success = self.pipette_driver.blowout()
            if not blowout_success:
                p300_control_logger.error("Failed to perform blowout")

        # Update the volume in the database tracker
        original_volume = self.pipette_tracker.volume
        self.pipette_tracker.volume = original_volume - volume_to_dispense

        # If we have a destination, update its contents based on what was in the pipette
        if infused_into is not None and isinstance(infused_into, (Vial, wp.Well)):
            # Calculate the ratio of each content in the pipette
            if sum(self.pipette_tracker.contents.values() or [0]) > 0:
                content_ratio = {
                    key: value / sum(self.pipette_tracker.contents.values())
                    for key, value in self.pipette_tracker.contents.items()
                }

                # Add the proportional contents to the destination
                infused_into.add_contents(
                    {
                        key: ratio * volume_to_dispense
                        for key, ratio in content_ratio.items()
                    },
                    volume_to_dispense,
                )

                # Remove the dispensed contents from the pipette
                for key, ratio in content_ratio.items():
                    self.pipette_tracker.update_contents(
                        key, -volume_to_dispense * ratio
                    )

        p300_control_logger.debug(
            f"Dispensed: {volume_to_dispense} µL at {rate} µL/s. Pipette vol: {self.pipette_tracker.volume} µL"
        )

        return None

    def mix(
        self, repetitions: int, volume: float, rate: Optional[float] = None
    ) -> bool:
        """
        Mix the solution by repeated aspirating and dispensing.

        Args:
            repetitions (int): Number of mixing cycles
            volume (float): Volume to mix in µL
            rate (float): Mixing rate in µL/second

        Returns:
            bool: True if mixing was successful
        """
        if volume <= 0 or repetitions <= 0:
            return False

        # Use the pipette driver's mix command
        if not rate:
            rate = self.max_p300_rate

        success = self.pipette_driver.mix(volume, repetitions, rate)

        if not success:
            p300_control_logger.error(
                f"Failed to mix {volume} µL for {repetitions} repetitions"
            )
            return False

        # Volume shouldn't change after mixing
        p300_control_logger.debug(
            f"Mixed {repetitions} times with {volume} µL at {rate} µL/s. Pipette vol: {self.pipette_tracker.volume} µL"
        )

        return True

    def reset_contents(self) -> bool:
        """
        Reset the pipette contents tracking (but not physical position)

        Returns:
            bool: True if successful
        """
        self.pipette_tracker.reset_contents()
        return True

    def reset_pipette(self) -> bool:
        """
        Reset the pipette by homing and priming it

        Returns:
            bool: True if reset was successful
        """
        # First home the pipette
        home_success = self.pipette_driver.home()
        if not home_success:
            p300_control_logger.error("Failed to home pipette")
            return False

        # Then prime it
        prime_success = self.pipette_driver.prime()
        if not prime_success:
            p300_control_logger.error("Failed to prime pipette")
            return False

        # Reset the database volume tracker
        self.pipette_tracker.volume = 0.0
        self.pipette_tracker.reset_contents()

        p300_control_logger.debug("Pipette reset successfully")
        return True

    def blowout(self) -> bool:
        """
        Perform a blowout operation to expel any remaining liquid

        Returns:
            bool: True if successful
        """
        success = self.pipette_driver.blowout()

        if success:
            # Reset volume after blowout
            original_volume = self.pipette_tracker.volume
            self.pipette_tracker.volume = 0.0
            # Reset contents
            self.pipette_tracker.reset_contents()
            p300_control_logger.debug(f"Performed blowout of {original_volume} µL")
        else:
            p300_control_logger.error("Failed to perform blowout")

        return success

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the pipette.

        Returns:
            Dict[str, Any]: Dictionary with status information
        """
        # Get hardware status from the driver
        driver_status = self.pipette_driver.get_status()

        # Combine with database tracker status
        status = {
            "success": driver_status.get("success", False),
            "homed": driver_status.get("homed", False),
            "position": driver_status.get("position", 0.0),
            "hardware_max_volume": driver_status.get("max_volume", 0.0),
            "current_volume": self.pipette_tracker.volume,
            "db_max_volume": self.pipette_tracker.capacity_ul,
            "has_tip": self.pipette_driver.has_tip,
            "contents": self.pipette_tracker.contents,
        }

        return status


class MockOT2P300(OT2P300):
    """Mock version of OT2P300 for testing"""

    def __init__(self):
        """Initialize the mock OT2P300 interface"""
        # Use the mock Arduino interface
        self.arduino = MockArduinoLink()

        # Configuration constants
        self.max_p300_rate = config.getfloat(
            "P300", "max_pipetting_rate", fallback=50.0
        )  # µL/s for Arduino pipette

        # Use the mock pipette driver
        self.pipette_driver = MockPipette.from_config(
            stepper=self.arduino,
            config_file="P300.json",
        )
        self.pipette_driver.has_tip = True  # Default to having a tip

        # Set up database tracker
        self.pipette_tracker = PipetteDBHandler()
        self.pipette_tracker.set_capacity(300.0)  # µL

        p300_control_logger.info("Mock OT2P300 initialized")
