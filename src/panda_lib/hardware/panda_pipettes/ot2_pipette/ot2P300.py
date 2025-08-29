"""
A class for controlling an OT2 P300 pipette via an Arduino while tracking vessel contents.

This module provides an interface for controlling ot2p300 pipettes for
liquid handling operations. It manages connection, configuration, and operation of OT2 P300 pipettes
while tracking volumes and contents.
"""

# pylint: disable=line-too-long, too-many-arguments, too-many-lines, too-many-instance-attributes, too-many-locals, import-outside-toplevel
from typing import Any, Dict, Optional, Union
import time
from panda_lib.hardware.arduino_interface import ArduinoLink, MockArduinoLink
from panda_lib.labware import Vial
from panda_lib.labware import wellplates as wp
from panda_shared.config.config_tools import read_config
from panda_shared.log_tools import (
    default_logger as p300_control_logger,
)
from panda_shared.log_tools import (
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

    Methods:
        prime(): Prime the pipette by aspirating a configured volume of air.
        aspirate(volume, rate): Aspirate the given volume at the given rate.
        drip_stop(): Aspirate a small volume of air to prevent dripping.
        dispense(volume, rate): Dispense the given volume at the given rate.
        blowout(reprime): Blow out any remaining volume and optionally reprime.#TODO remove this. Blowout is not necessary. Dispensing will go to the blowout position.
        mix(repetitions, volume, rate): Mix the solution by aspirating and dispensing.
    """

    def __init__(self, arduino: Optional[ArduinoLink] = None, prime_position: Optional[float] = None):
        """Initialize the OT2P300 Pipette interface."""
        # Set up Arduino connection
        self.arduino = ArduinoLink() if arduino is None else arduino
        # Configuration constants
        self.prime_position = prime_position if prime_position is not None else config.getfloat("P300", "prime_position", fallback=36.0)
      
        self.max_p300_rate = config.getfloat(
            "P300", "max_pipetting_rate", fallback=3000
        )  # µL/s for Arduino pipette

        # Liquid handling specific constants
        self.prime_volume_ul = config.getfloat(
            "P300", "prime_volume_ul", fallback=0.0
        )  # µL
        self.drip_stop_volume_ul = config.getfloat(
            "P300", "drip_stop_volume_ul", fallback=5.0
        )  # µL

        # Tracking flags
        self.is_primed = False
        self.has_drip_stop = False
        self._drip_stop_volume = 0.0  # Track actual drip stop volume

        # Add unit conversion constants for clarity
        self.UL_TO_ML = 0.001  # Conversion factor from µL to mL
        self.ML_TO_UL = 1000.0  # Conversion factor from mL to µL

        # Set up database tracker for volumes and contents
        self.pipette_tracker = PipetteDBHandler()
        self.pipette_tracker.set_capacity(
            config.getfloat("P300", "pipette_capacity", fallback=200.0)
        )  # µL

        # If there is volume in the pipette, warn the user
        if self.pipette_tracker.volume > 0:
            vessel_logger.warning(
                f"Warning: Pipette volume is {self.pipette_tracker.volume} µL. This may affect operations."
            )
        # Create pipette driver for hardware control
        self.pipette_driver = Pipette.from_config(
            stepper=self.arduino,
            config_file="P300.json",
        )

        # Confirm that the driver is initialized
        if not self.pipette_driver or not self.pipette_driver.stepper:
            p300_control_logger.error("Failed to initialize pipette driver")
            raise RuntimeError("Pipette driver initialization failed")

        p300_control_logger.info("OT2P300 initialized")
    
    @classmethod
    def from_config(cls, stepper=None, config: Optional[dict] = None) -> "OT2P300":
        return cls(arduino=stepper)
    
    def __enter__(self):
        """Enter the context manager"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager"""
        self.close()

    def close(self):
        """Clean up resources - not much needed since Arduino cleanup happens at process exit"""
        p300_control_logger.info("OT2P300 closed")

    def prime(self, volume_ul: Optional[float] = None) -> bool:
        """
        Prime the pipette by aspirating a small volume of air.
        The primed air is used later for blowout operations.

        Args:
            volume_ul, but will be ignored. The OT2P300 has a configuered prime position. Maintained
            argument to match the interface of other pipettes.

        Returns:
            bool: True if priming was successful, False otherwise
        """

        if self.pipette_driver.is_primed:
            p300_control_logger.warning(
                "Pipette is already primed. No need to prime again."
            )
            return True
        try:
            self.pipette_driver.prime()
            self.is_primed = True
            p300_control_logger.info("Pipette primed successfully")
            # NOTE we do not track the volume of air aspirated here

        except Exception as e:
            p300_control_logger.error(f"Error during priming: {e}")
            return False

        return True

    def drip_stop(self, volume_ul: Optional[float] = None) -> bool:
        """
        Perform a drip stop operation by aspirating a small amount of air.
        This prevents dripping when moving between positions.

        Args:
            volume_ul (float, optional): Air volume to aspirate in microliters.
                                        If None, uses the configured drip_stop_volume_ul.

        Returns:
            bool: True if drip stop was successful, False otherwise
        """
        # Use configured value if none specified
        drip_volume = volume_ul if volume_ul is not None else self.drip_stop_volume_ul

        try:
            drip_volume = float(drip_volume)
            if drip_volume <= 0:
                p300_control_logger.warning(
                    f"Cannot perform drip stop with {drip_volume} µL - volume must be positive"
                )
                return False

            # Log the operation
            p300_control_logger.info(
                f"Performing drip stop with {drip_volume} µL of air"
            )

            # Check if volume would exceed capacity
            if (
                self.pipette_tracker.volume + drip_volume
                > self.pipette_tracker.capacity_ul
            ):
                p300_control_logger.warning(
                    f"Cannot perform drip stop with {drip_volume} µL - would exceed pipette capacity"
                )
                return False

            # Use the pipette driver to aspirate air
            #TODO fix the drip_stop function, because right now it uses aspirate as a function which starts at the prime position
            # as is, the drip_stop function will push out the volume it already aspirated, then aspirate the drip_stop volume.
            success = self.pipette_driver.aspirate( #TODO change this to an actual drip_stop function, not aspirate.
                vol=drip_volume, s=self.max_p300_rate
            )

            if not success:
                p300_control_logger.error(
                    f"Failed to perform drip stop with {drip_volume} µL"
                )
                return False

            # Store the actual drip stop volume and update tracking
            self._drip_stop_volume = drip_volume
            self.pipette_tracker.volume += drip_volume
            self.has_drip_stop = True

            p300_control_logger.debug(
                f"Drip stop performed with {drip_volume} µL of air"
            )
            return True

        except Exception as e:
            p300_control_logger.error(f"Error during drip stop: {e}")
            return False

    def aspirate(
        self,
        volume_to_aspirate: float,
        solution: Optional[Union[Vial, wp.Well]] = None,
        rate: Optional[float] = None,
        drip_stop: bool = False,
    ) -> Optional[Union[Vial, wp.Well]]:
        """
        Aspirate the given volume at the given rate from the specified vessel.
        Update the volume of the pipette and the solution if given.

        Args:
            volume_to_aspirate (float): Volume to be aspirated in microliters.
            solution (Union[Vial, wp.Well], optional): The vial or well to aspirate from. If None, air is aspirated.
            rate (float, optional): Pumping rate in µL/second. None defaults to the max p300 rate.
            drip_stop (bool): Whether to perform a drip stop after aspiration

        Returns:
            The updated solution object if given one, otherwise None
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
            f"Aspirating {volume_to_aspirate} µL at {rate} steps/s"
            + (f" from {solution}" if solution else " of air")
        )

        # Check if volume would exceed capacity
        if (
            self.pipette_tracker.volume + volume_to_aspirate
            > self.pipette_tracker.capacity_ul
        ):
            p300_control_logger.warning(
                f"Cannot aspirate {volume_to_aspirate} µL - would exceed pipette capacity of {self.pipette_tracker.capacity_ul} µL"
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

            if removed_contents and sum(removed_contents.values()) > 0:
                for soln, vol in removed_contents.items():
                    self.pipette_tracker.update_contents(soln, vol)
            else:
                # No contents returned (e.g., overdraft), still update pipette volume as air or unknown liquid
                self.pipette_tracker.volume += volume_to_aspirate
                p300_control_logger.warning(
                    f"Overdraft detected from {solution.name}. "
                    f"Contents were empty but {volume_to_aspirate} µL was aspirated anyway. "
                    "Pipette volume adjusted to reflect physical state."
                )

            p300_control_logger.debug(
                f"Aspirated: {volume_to_aspirate} µL at {rate} steps/s from {solution}. Pipette vol: {self.pipette_tracker.volume} µL"
            )
        else:
            # If no solution is provided, just update the pipette volume
            self.pipette_tracker.volume += volume_to_aspirate
            p300_control_logger.debug(
                f"Aspirated: {volume_to_aspirate} µL of air at {rate} steps/s. Pipette vol: {self.pipette_tracker.volume} µL"
            )

        # If a drip stop is requested, perform it
        if (
            drip_stop and solution is not None
        ):  # Only do drip stop when aspirating from solution
            drip_stop_success = self.drip_stop()
            if not drip_stop_success:
                p300_control_logger.warning(
                    "Failed to perform drip stop after aspiration"
                )

        return solution

    def dispense(
        self,
        volume_to_dispense: float,
        being_infused: Optional[Union[Vial, wp.Well]] = None,
        infused_into: Optional[Union[Vial, wp.Well]] = None,
        rate: Optional[float] = None,
    ) -> None:
        """
        Dispense the given volume at the given rate.
        If a drip stop was performed, it will also dispense the drip stop volume
        but not add it to the destination vessel.

        Args:
            volume_to_dispense (float): Volume to be dispensed in microliters.
            being_infused (Union[Vial, wp.Well], optional): The solution being dispensed to get the density
            infused_into (Union[Vial, wp.Well], optional): The destination of the solution (well or vial)
            rate (float, optional): Pumping rate in µL/second. None defaults to the max p300 rate.
        """
        # Validate inputs
        try:
            volume_to_dispense = float(volume_to_dispense)
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

        # Calculate total dispense volume including drip stop if present
        total_volume_to_dispense = volume_to_dispense
        drip_stop_volume = 0.0


        # Log the operation
        p300_control_logger.info(
            f"Dispensing {volume_to_dispense} µL at {rate} steps/s"
            + (f" from {being_infused}" if being_infused else "")
            + (f" into {infused_into}" if infused_into else "")
            + (
                f" (including {drip_stop_volume} µL drip stop)"
                if drip_stop_volume > 0
                else ""
            )
        )

        # Use the pipette driver to dispense the total volume
        success = self.pipette_driver.dispense(total_volume_to_dispense, rate)
        if not success:
            p300_control_logger.error(
                f"Failed to dispense {total_volume_to_dispense} µL"
            )
            return None

        # If we have a destination, update its contents based on what was in the pipette
        if infused_into is not None and isinstance(infused_into, (Vial, wp.Well)):
            # Calculate the sample volume (excluding drip stop)
            sample_volume_ul = volume_to_dispense  # The actual sample without drip stop

            # First update the destination vessel with just the sample volume
            if sum(self.pipette_tracker.contents.values() or [0]) > 0:
                # Calculate the ratio of each content in the pipette
                content_ratio = {
                    key: value / sum(self.pipette_tracker.contents.values())
                    for key, value in self.pipette_tracker.contents.items()
                }

                # Add the proportional contents to the destination (excluding drip stop)
                infused_into.add_contents(
                    {
                        key: ratio * sample_volume_ul
                        for key, ratio in content_ratio.items()
                    },
                    sample_volume_ul,
                )

                # Remove all dispensed contents from the pipette (including drip stop)
                for key, ratio in content_ratio.items():
                    self.pipette_tracker.update_contents(
                        key, -total_volume_to_dispense * ratio
                    )
            else:
                # If no contents defined but we have volume, still track the empty transfer
                # and update the destination vial with just the sample volume
                infused_into.add_contents({}, sample_volume_ul)
                # Remove the total volume from the pipette
                self.pipette_tracker.volume -= total_volume_to_dispense
        else:
            # If no destination vessel, just update the pipette volume with the total dispensed
            self.pipette_tracker.volume -= total_volume_to_dispense

        # Reset drip stop flag
        self.has_drip_stop = False
        self._drip_stop_volume = 0.0

        p300_control_logger.debug(
            f"Dispensed: {volume_to_dispense} µL"
            f" at {rate} steps/s. Pipette vol: {self.pipette_tracker.volume} µL"
        )

        return None
    
    def blowout_no_tracker(self, rate: float | None = None) -> None:
        """
        Move plunger to BLOWOUT_POSITION to clear the tip after mixing.
        NOTE: Call only when the tip is out of liquid (gantry lifted).

        Args:
            rate: Optional firmware velocity (steps/s). If None, uses firmware default.
        """
        # Log intent (avoid unit mismatch in the message)
        if rate is None:
            p300_control_logger.info("Blowout at firmware default velocity")
        else:
            p300_control_logger.info(f"Blowout at firmware velocity={rate}")

        # Send dispense with volume=0 so firmware performs blowout
        if rate is None:
            success = self.pipette_driver.dispense(0.0)                    # -> CMD_PIPETTE_DISPENSE,0
        else:
            success = self.pipette_driver.dispense(0.0, float(rate))       # -> CMD_PIPETTE_DISPENSE,0,<rate>

        if not success:
            p300_control_logger.error("Blowout failed")
            return

        # On success, plunger is at blowout -> no liquid in tip
        self.pipette_tracker.volume = 0
        p300_control_logger.debug("Blowout complete; tracker volume reset to 0 µL")

        return None
    #TODO remove this blowout function, but verify that nothing references it.
    ''' 
    def blowout(self, reprime: bool = True) -> bool:
        """
        Perform a blowout operation to expel any remaining liquid.
        Optionally reprime the pipette afterward.

        Args:
            reprime (bool): Whether to prime the pipette after blowout

        Returns:
            bool: True if successful
        """
        if not self.is_primed:
            p300_control_logger.warning(
                "Cannot perform blowout - pipette is not primed"
            )
            return False

        p300_control_logger.info("Performing blowout operation")
        success = self.pipette_driver.blowout()

        if success:
            # Log the original volume before resetting
            original_volume = self.pipette_tracker.volume
            original_contents = dict(self.pipette_tracker.contents)

            # Reset volume and contents after blowout
            for key in original_contents:
                original_contents[key] = 0.0
            self.pipette_tracker.volume = 0.0
            self.pipette_tracker.contents = original_contents

            # Reset flags
            self.is_primed = False
            self.has_drip_stop = False
            self._drip_stop_volume = 0.0

            p300_control_logger.debug(
                f"Performed blowout of {original_volume} µL with contents: {original_contents}"
            )

            # Return to zero position after blowout
            if self.pipette_driver.prime():
                # Reprime if requested
                if reprime:
                    prime_success = self.prime()
                    if not prime_success:
                        p300_control_logger.warning("Failed to reprime after blowout")
                        return False
            else:
                p300_control_logger.warning(
                    "Failed to reset pipette position after blowout"
                )
                return False
        else:
            p300_control_logger.error("Failed to perform blowout")
            return False

        return success
    '''
    def mix(
        self, repetitions: int, volume: float, rate: Optional[float] = None
    ) -> bool:
        """
        Mix the solution by repeated aspirating and dispensing.

        Args:
            repetitions (int): Number of mixing cycles
            volume (float): Volume to mix in µL
            rate (float): Mixing rate in steps/sec

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
            f"Mixing {repetitions} times with {volume} µL at {rate} steps/s"
        )
        success = self.pipette_driver.mix(volume, repetitions, rate)

        if not success:
            p300_control_logger.error(
                f"Failed to mix {volume} µL for {repetitions} repetitions"
            )
            return False

        # Volume shouldn't change after mixing
        p300_control_logger.debug(
            f"Mixed {repetitions} times with {volume} µL at {rate} steps/s. Pipette vol: {self.pipette_tracker.volume} µL"
        )

        return True

    def reset_contents(self) -> bool:
        """
        Reset the pipette contents tracking (but not physical position)

        Returns:
            bool: True if successful
        """
        self.pipette_tracker.reset_contents()
        self.has_drip_stop = False
        self._drip_stop_volume = 0.0
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

        # Reset flags
        self.is_primed = False
        self.has_drip_stop = False
        self._drip_stop_volume = 0.0

        p300_control_logger.debug("Pipette reset successfully")

        # Re-prime the pipette with air
        self.prime()

        return True

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
            # "is_primed": self.is_primed, # TODO add to schema
            # "has_drip_stop": self.has_drip_stop,# TODO add to schema
            # "drip_stop_volume": self._drip_stop_volume,# TODO add to schema
        }

        return status

    
    @property
    def has_tip(self) -> bool:
        """Return True if a tip is attached."""
        return bool(getattr(self.pipette_driver, "has_tip", False))
    
    @has_tip.setter
    def has_tip(self, value: bool) -> None:
        self.pipette_driver.has_tip = bool(value)
        p300_control_logger.debug(
            f"Pipette tip status set to: {'attached' if self.pipette_driver.has_tip else 'detached'}"
        )

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

    def replace_tip(self) -> bool:
        """
        Replace the pipette tip using the configured driver method.
        Disposes of the current tip (if present) and picks up a new one.
        
        Returns:
            bool: True if tip replacement was successful, False otherwise.
        """
        # Log the intent
        p300_control_logger.info("Initiating pipette tip replacement.")

        # Drop current tip, if supported
        if hasattr(self.pipette_driver, "drop_tip"):
            drop_success = self.pipette_driver.drop_tip()
            if not drop_success:
                p300_control_logger.warning("Failed to drop current pipette tip.")
                return False
            time.sleep(1.0)
            p300_control_logger.debug("Old tip dropped successfully.")
        else:
            p300_control_logger.warning("drop_tip() not implemented in pipette driver.")

        # Pick up a new tip
        if hasattr(self.pipette_driver, "pick_up_tip"):
            pick_success = self.pipette_driver.pick_up_tip()
            if not pick_success:
                p300_control_logger.error("Failed to pick up a new pipette tip.")
                return False
            time.sleep(2.0)
            p300_control_logger.debug("New pipette tip picked up successfully.")
        else:
            p300_control_logger.error("pick_up_tip() not implemented in pipette driver.")
            return False

        # Reset internal state if needed
        self.pipette_tracker.reset_contents()
        p300_control_logger.info("Pipette tip successfully replaced and volume reset.")

        return True



class MockOT2P300(OT2P300):
    """
    Mock version of OT2P300 for testing.

    Simulates the behavior of a real OT2P300 pipette without requiring hardware connection.
    Maintains accurate volume tracking, state management, and simulated timing.
    """

    def __init__(self, arduino: Optional[ArduinoLink] = None, prime_position: Optional[float] = None):

        """Initialize the mock OT2P300 interface"""
        # Use the mock Arduino interface
        self.arduino = MockArduinoLink() if arduino is None else arduino

        # Configuration constants
        self.prime_position = prime_position if prime_position is not None else config.getfloat("P300", "prime_position", fallback=36)

        self.max_p300_rate = config.getfloat(
            "P300", "max_pipetting_rate", fallback=2500.0
        )  # µL/s for Arduino pipette

        # Liquid handling specific constants
        self.prime_volume_ul = config.getfloat(
            "P300", "prime_volume_ul", fallback=0.0
        )  # µL
        self.drip_stop_volume_ul = config.getfloat(
            "P300", "drip_stop_volume_ul", fallback=5.0
        )  # µL

        # Tracking flags - same as real implementation
        self.is_primed = False
        self.has_drip_stop = False
        self._drip_stop_volume = 0.0

        # Add unit conversion constants for clarity
        self.UL_TO_ML = 0.001  # Conversion factor from µL to mL
        self.ML_TO_UL = 1000.0  # Conversion factor from mL to µL

        # Use the mock pipette driver
        self.pipette_driver = MockPipette.from_config(
            stepper=self.arduino,
            config_file="P300.json",
        )
        self.pipette_driver.has_tip = True  # Default to having a tip

        # Set up database tracker
        self.pipette_tracker = PipetteDBHandler()
        self.pipette_tracker.set_capacity(
            config.getfloat("P300", "pipette_capacity", fallback=300.0)
        )  # µL

        p300_control_logger.info("Mock OT2P300 initialized")

        # Prime automatically if the pipette is empty
        if self.pipette_tracker.volume == 0:
            self.prime()
