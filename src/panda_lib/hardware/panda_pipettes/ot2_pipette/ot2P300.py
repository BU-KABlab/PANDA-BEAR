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

    def __init__(self, arduino: Optional[ArduinoLink] = None):
        """Initialize the OT2P300 Pipette interface."""
        # Set up Arduino connection
        self.arduino = ArduinoLink() if arduino is None else arduino

        # Configuration constants
        self.max_p300_rate = config.getfloat(
            "P300", "max_pipetting_rate", fallback=50.0
        )  # µL/s for Arduino pipette

        # Add unit conversion constants for clarity
        self.UL_TO_ML = 0.001  # Conversion factor from µL to mL
        self.ML_TO_UL = 1000.0  # Conversion factor from mL to µL

        # Create pipette driver for hardware control
        self.pipette_driver = Pipette.from_config(
            stepper=self.arduino,
            config_file="P300.json",
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
        # Validate inputs
        try:
            volume_to_aspirate = float(volume_to_aspirate)
            if rate is not None:
                rate = float(rate)
            else:
                rate = self.max_p300_rate
        except (ValueError, TypeError) as e:
            p300_control_logger.error(f"Invalid aspirate parameters: {e}")
            return None

        if volume_to_aspirate <= 0:
            p300_control_logger.warning(
                f"Cannot aspirate {volume_to_aspirate} µL - volume must be positive"
            )
            return None

        # Check if solution is a valid container type
        if solution is not None and not isinstance(solution, (Vial, wp.Well)):
            p300_control_logger.error(
                f"Invalid solution container type: {type(solution)}"
            )
            return None

        # Log the operation
        p300_control_logger.info(
            f"Aspirating {volume_to_aspirate} µL at {rate} µL/s"
            + (f" from {solution}" if solution else " of air")
        )

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

        # If we have a solution, update the pipette contents and the solution volume
        if solution is not None and isinstance(solution, (Vial, wp.Well)):
            removed_contents = solution.remove_contents(volume_to_aspirate)
            for soln, vol in removed_contents.items():
                self.pipette_tracker.update_contents(soln, vol)

            p300_control_logger.debug(
                f"Aspirated: {volume_to_aspirate} µL at {rate} µL/s from {solution}. Pipette vol: {self.pipette_tracker.volume} µL"
            )
        else:
            # If no solution is provided, just update the pipette volume
            self.pipette_tracker.volume += volume_to_aspirate
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
        # Validate inputs
        try:
            volume_to_dispense = float(volume_to_dispense)
            blowout_ul = float(blowout_ul)
            if rate is not None:
                rate = float(rate)
            else:
                rate = self.max_p300_rate
        except (ValueError, TypeError) as e:
            p300_control_logger.error(f"Invalid dispense parameters: {e}")
            return None

        if volume_to_dispense <= 0:
            p300_control_logger.warning(
                f"Cannot dispense {volume_to_dispense} µL - volume must be positive"
            )
            return None

        # Check if we have enough volume
        if self.pipette_tracker.volume < volume_to_dispense:
            p300_control_logger.warning(
                f"Cannot dispense {volume_to_dispense} µL - pipette only contains {self.pipette_tracker.volume} µL"
            )
            return None

        # Calculate the total volume dispensed (including blowout)
        total_volume_dispensed = volume_to_dispense

        # Log the dispensing operation with details
        p300_control_logger.info(
            f"Dispensing {volume_to_dispense} µL"
            + f" at {rate} µL/s"
            + (f" from {being_infused}" if being_infused else "")
            + (f" into {infused_into}" if infused_into else "")
        )

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
            # return to zero position after blowout
            self.pipette_driver.prime()

        # If we have a destination, update its contents based on what was in the pipette
        if infused_into is not None and isinstance(infused_into, (Vial, wp.Well)):
            # First update the destination vessel
            if sum(self.pipette_tracker.contents.values() or [0]) > 0:
                # Calculate the ratio of each content in the pipette
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
            else:
                # If no contents defined but we have volume, still track the empty transfer
                # and update the destination vial
                infused_into.add_contents({}, volume_to_dispense)
                # Remove the volume (including blowout) from the pipette
                self.pipette_tracker.volume -= total_volume_dispensed
        else:
            # If no destination vessel, just update the pipette volume
            self.pipette_tracker.volume -= total_volume_dispensed

        p300_control_logger.debug(
            f"Dispensed: {volume_to_dispense} µL"
            f" at {rate} µL/s. Pipette vol: {self.pipette_tracker.volume} µL"
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
        # Validate input parameters
        try:
            repetitions = int(repetitions)
            volume = float(volume)
            if rate is not None:
                rate = float(rate)
            else:
                rate = self.max_p300_rate
        except (ValueError, TypeError) as e:
            p300_control_logger.error(f"Invalid mix parameters: {e}")
            return False

        if volume <= 0 or repetitions <= 0:
            p300_control_logger.warning(
                f"Cannot mix with invalid parameters: volume={volume} µL, repetitions={repetitions}"
            )
            return False

        # Check if volume exceeds capacity
        if volume > self.pipette_tracker.capacity_ul:
            p300_control_logger.warning(
                f"Mix volume {volume} µL exceeds pipette capacity {self.pipette_tracker.capacity_ul} µL"
            )
            return False

        # Use the pipette driver's mix command
        p300_control_logger.info(
            f"Mixing {repetitions} times with {volume} µL at {rate} µL/s"
        )
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
        p300_control_logger.debug("Pipette contents reset")
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
        p300_control_logger.info("Performing blowout operation")
        success = self.pipette_driver.blowout()

        if success:
            # Log the original volume before resetting
            original_volume = self.pipette_tracker.volume
            original_contents = dict(self.pipette_tracker.contents)

            # Reset volume and contents after blowout
            # Note: Different from syringepump implementation which uses reset_contents()
            # We preserve the content keys but set volumes to 0
            for key in original_contents:
                original_contents[key] = 0.0
            self.pipette_tracker.volume = 0.0
            self.pipette_tracker.contents = original_contents

            p300_control_logger.debug(
                f"Performed blowout of {original_volume} µL with contents: {original_contents}"
            )

            # Return to zero position after blowout
            prime_success = self.pipette_driver.prime()
            if not prime_success:
                p300_control_logger.warning("Failed to prime pipette after blowout")
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

    def has_tip(self) -> bool:
        """
        Check if the pipette has a tip attached

        Returns:
            bool: True if a tip is attached, False otherwise
        """
        return self.pipette_driver.has_tip

    def set_tip_status(self, has_tip: bool) -> None:
        """
        Set the tip status of the pipette

        Args:
            has_tip (bool): Whether the pipette has a tip
        """
        self.pipette_driver.has_tip = bool(has_tip)
        p300_control_logger.debug(
            f"Pipette tip status set to: {'attached' if has_tip else 'detached'}"
        )

    def _ul_to_ml(self, volume_ul: float) -> float:
        """Convert microliters to milliliters

        Args:
            volume_ul (float): Volume in microliters

        Returns:
            float: Volume in milliliters, rounded to PRECISION decimal places
        """
        return round(float(volume_ul) * self.UL_TO_ML, PRECISION)

    def _ml_to_ul(self, volume_ml: float) -> float:
        """Convert milliliters to microliters

        Args:
            volume_ml (float): Volume in milliliters

        Returns:
            float: Volume in microliters, rounded to PRECISION decimal places
        """
        return round(float(volume_ml) * self.ML_TO_UL, PRECISION)


class MockOT2P300(OT2P300):
    """Mock version of OT2P300 for testing"""

    def __init__(self, arduino: Optional[ArduinoLink] = None):
        """Initialize the mock OT2P300 interface"""
        # Use the mock Arduino interface
        self.arduino = MockArduinoLink() if arduino is None else arduino

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
