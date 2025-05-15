"""
A driver class for controlling a New Era A-1000 syringe pump using the nesp-lib library.

This module provides a comprehensive interface for controlling syringe pumps for precise
liquid handling operations in automated laboratory settings. It manages connection,
configuration, and operation of New Era pumps while tracking pipette volumes and contents.

Key features:
- Automatic port detection and connection to syringe pumps
- Volume tracking with precision control
- Content tracking between vessels during liquid transfers
- Bidirectional operation (aspirate/dispense)
- Error handling for common pump operation issues
- Context manager support for clean resource management
- Advanced liquid handling features (priming, drip stop, blowout)
"""

# pylint: disable=line-too-long, too-many-arguments, too-many-lines, too-many-instance-attributes, too-many-locals, import-outside-toplevel
import time
from typing import Optional, Union

import nesp_lib
from nesp_lib.mock import Pump as MockNespLibPump

from panda_lib.labware import Vial
from panda_lib.labware import wellplates as wp
from shared_utilities import get_port_manufacturers, get_ports
from shared_utilities.config.config_tools import read_config
from shared_utilities.log_tools import (
    default_logger as pump_control_logger,
)
from shared_utilities.log_tools import (
    setup_default_logger,
)

from ..pipette import PipetteDBHandler

vessel_logger = setup_default_logger(log_name="vessel")

config = read_config()

PRECISION = config.getint("OPTIONS", "precision")


class SyringePump:
    """
    Class for controlling a new era A-1000 syringe pump using the nesp-lib library

    Attributes:
        pump (Pump): Initialized pump object.
        capacity (float): Maximum volume of the syringe in milliliters.
        pipette_capacity_ml (float): Maximum volume of the pipette in milliliters.
        pipette_capacity_ul (float): Maximum volume of the pipette in microliters.
        pipette_volume_ul (float): Current volume of the pipette in microliters.
        pipette_volume_ml (float): Current volume of the pipette in milliliters.

    Methods:
        prime(): Prime the pump by aspirating a configured volume of air.
        aspirate(volume, rate): Withdraw the given volume at the given rate.
        drip_stop(): Aspirate a small volume of air to prevent dripping.
        dispense(volume, rate): Infuse the given volume at the given rate.
        blowout(reprime): Blow out any remaining volume and optionally reprime.
        update_pipette_volume(volume_ul): Set the volume of the pipette in ul.
        set_pipette_capacity(capacity_ul): Set the capacity of the pipette in ul.

    Exceptions:
        OverFillException: Raised when a syringe is over filled.
        OverDraftException: Raised when a syringe is over drawn.
    """

    def __init__(self):
        """
        Initialize the pump and set the capacity.
        """
        self.connected = False
        # Configuration constants
        self.max_pump_rate = config.getfloat(
            "PUMP", "max_pumping_rate", fallback=0.640
        )  # ml/min
        self.syringe_capacity = config.getfloat(
            "PUMP", "syringe_capacity", fallback=1.0
        )  # mL

        # Liquid handling specific constants
        self.prime_volume_ul = config.getfloat(
            "PUMP", "prime_volume_ul", fallback=20.0
        )  # µL
        self.drip_stop_volume_ul = config.getfloat(
            "PUMP", "drip_stop_volume_ul", fallback=10.0
        )  # µL

        # Tracking flags
        self.is_primed = False
        self.has_drip_stop = False
        self._drip_stop_volume = 0.0  # Track actual drip stop volume

        # Add unit conversion constants for clarity
        self.UL_TO_ML = 0.001  # Conversion factor from µL to mL
        self.ML_TO_UL = 1000.0  # Conversion factor from mL to µL

        self.pump: nesp_lib.Pump = self.set_up_pump()
        self.pipette_tracker = PipetteDBHandler()
        if self.pipette_tracker.volume == 0:
            self.prime()

    def set_up_pump(self) -> nesp_lib.Pump:
        """
        Set up the syringe pump using hardcoded settings.
        Returns:
            Pump: Initialized pump object.
        """
        ports = get_ports()
        if not ports:
            pump_control_logger.error("No ports found")
            raise Exception("No ports found")

        # Try the configured port first if it exists
        initial_port = config.get("PUMP", "port", fallback=None)
        if initial_port in ports:
            # Move the initial port to the front of the list
            ports.remove(initial_port)
            ports.insert(0, initial_port)

        # Check if a port has silicon labs in the name, if so try that first
        ports_manurfacturers = get_port_manufacturers()
        for port, manufacturer in ports_manurfacturers.items():
            if "silicon" in manufacturer.lower():
                ports.remove(port)
                ports.insert(0, port)
                break

        last_exception = None
        for port in ports:
            try:
                pump_control_logger.debug(f"Setting up pump on port {port}...")
                pump_port = nesp_lib.Port(
                    name=port,
                    baud_rate=config.getint("PUMP", "baudrate", fallback=19200),
                    timeout=5,
                )

                syringe_pump = nesp_lib.Pump(pump_port)
                syringe_pump.syringe_diameter = config.getfloat(
                    "PUMP", "syringe_inside_diameter", fallback=4.600
                )  # millimeters
                syringe_pump.pumping_rate = self.max_pump_rate
                syringe_pump.volume_infused_clear()
                syringe_pump.volume_withdrawn_clear()
                log_msg = f"Pump found at address {syringe_pump.address}"
                config.set("PUMP", "port", port)
                pump_control_logger.info(log_msg)
                self.connected = True
                time.sleep(2)
                return syringe_pump

            except Exception as e:
                last_exception = e
                pump_control_logger.error(f"Error setting up pump on port {port}: {e}")
                pump_control_logger.exception(e)
                continue

        # If we've tried all ports and none worked
        pump_control_logger.error("All ports exhausted, no pump found")
        if last_exception:
            raise Exception(f"All ports exhausted, last error: {last_exception}")
        else:
            raise Exception("All ports exhausted, no pump found")

    def __enter__(self):
        """Enter the context manager"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager"""
        self.close()

    def close(self):
        """Disconnect the pump"""
        if self.pump:
            if self.pump.close():
                pump_control_logger.info("Pump port closed")
                pump_control_logger.info("Pump disconnected")
        else:
            pump_control_logger.warning("Pump not connected")

    def prime(self, volume_ul: Optional[float] = None) -> bool:
        """
        Prime the syringe pump by aspirating a small volume of air.
        The primed air is used later for blowout operations.

        Args:
            volume_ul (float, optional): Air volume to prime in microliters.
                                        If None, uses the configured prime_volume_ul.

        Returns:
            bool: True if priming was successful, False otherwise
        """
        # Use configured value if none specified
        prime_volume = volume_ul if volume_ul is not None else self.prime_volume_ul

        try:
            prime_volume = float(prime_volume)
            if prime_volume <= 0:
                pump_control_logger.warning(
                    f"Cannot prime with {prime_volume} µL - volume must be positive"
                )
                return False

            # Convert to milliliters
            prime_volume_ml = self._ul_to_ml(prime_volume)

            # Log the operation
            pump_control_logger.info(f"Priming pump with {prime_volume} µL of air")

            # Run the pump to aspirate air
            _ = self.run_pump(
                nesp_lib.PumpingDirection.WITHDRAW, prime_volume_ml, self.max_pump_rate
            )

            # Update the flag but don't track in pipette volume
            self.is_primed = True

            # Clear the pump's memory
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()

            pump_control_logger.debug(f"Pump primed with {prime_volume} µL of air")
            return True

        except Exception as e:
            pump_control_logger.error(f"Error during priming: {e}")
            pump_control_logger.exception(e)
            return False

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
                pump_control_logger.warning(
                    f"Cannot perform drip stop with {drip_volume} µL - volume must be positive"
                )
                return False

            # Convert to milliliters
            drip_volume_ml = self._ul_to_ml(drip_volume)

            # Log the operation
            pump_control_logger.info(
                f"Performing drip stop with {drip_volume} µL of air"
            )

            # Run the pump to aspirate air
            _ = self.run_pump(
                nesp_lib.PumpingDirection.WITHDRAW, drip_volume_ml, self.max_pump_rate
            )

            # Store the actual withdrawn volume
            actual_drip_volume_ul = self._ml_to_ul(self.pump.volume_withdrawn)
            self._drip_stop_volume = actual_drip_volume_ul

            # Update the pipette volume and flag
            self.pipette_tracker.volume += actual_drip_volume_ul
            self.has_drip_stop = True

            # Clear the pump's memory
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()

            pump_control_logger.debug(
                f"Drip stop performed with {actual_drip_volume_ul} µL of air"
            )
            return True

        except Exception as e:
            pump_control_logger.error(f"Error during drip stop: {e}")
            pump_control_logger.exception(e)
            return False

    def blowout(self, reprime: bool = True) -> bool:
        """
        Blow out any remaining volume in the pipette.
        Optionally reprime the pipette afterward.

        Args:
            reprime (bool): Whether to prime the pipette after blowout

        Returns:
            bool: True if blowout was successful, False otherwise
        """
        if not self.is_primed:
            pump_control_logger.warning("Cannot perform blowout - pump is not primed")
            return False

        try:
            # Log the operation
            pump_control_logger.info("Performing blowout operation")

            # Get the current pipette volume
            original_volume = self.pipette_tracker.volume
            original_contents = dict(self.pipette_tracker.contents)

            # Calculate blowout volume in milliliters (use prime volume)
            blowout_volume_ml = self._ul_to_ml(self.prime_volume_ul)

            # Run the pump to dispense the prime volume
            _ = self.run_pump(
                nesp_lib.PumpingDirection.INFUSE, blowout_volume_ml, self.max_pump_rate
            )

            # Reset the pipette - clear contents but maintain tracking
            for key in original_contents:
                original_contents[key] = 0.0
            self.pipette_tracker.volume = 0.0
            self.pipette_tracker.contents = original_contents

            # Reset flags
            self.is_primed = False
            self.has_drip_stop = False
            self._drip_stop_volume = 0.0

            # Clear the pump's memory
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()

            pump_control_logger.debug(
                f"Performed blowout of {original_volume} µL with contents: {original_contents}"
            )

            # Reprime if requested
            if reprime:
                prime_success = self.prime()
                if not prime_success:
                    pump_control_logger.warning("Failed to reprime after blowout")
                    return False

            return True

        except Exception as e:
            pump_control_logger.error(f"Error during blowout: {e}")
            pump_control_logger.exception(e)
            return False

    def aspirate(
        self,
        volume_to_aspirate: float,
        solution: Optional[Union[Vial, wp.Well]] = None,
        rate: Optional[float] = None,
        drip_stop: bool = False,
    ) -> Optional[Union[Vial, wp.Well]]:
        """
        Withdraw the given volume at the given rate from the specified vessel.
        Update the volume of the pipette and the solution if given.
        If only volume is specified, air is aspirated.

        Args:
            volume_to_aspirate (float): Volume to be aspirated in microliters.
            solution (Union[Vial, wp.Well], optional): The vial or well to aspirate from. If None, air is aspirated.
            rate (float, optional): Pumping rate in milliliters per minute. None defaults to the max pump rate.

        Returns:
            The updated solution object if given one, otherwise None

        Raises:
            ValueError: If volume is negative or invalid
        """
        # Validate inputs
        try:
            volume_to_aspirate = float(volume_to_aspirate)
            if rate is not None:
                rate = float(rate)
            else:
                rate = self.max_pump_rate
        except (ValueError, TypeError) as e:
            pump_control_logger.error(f"Invalid aspirate parameters: {e}")
            return None

        if volume_to_aspirate <= 0:
            pump_control_logger.warning(
                f"Cannot aspirate {volume_to_aspirate} µL - volume must be positive"
            )
            return None

        # Check if solution is a valid container type when provided
        if solution is not None and not isinstance(solution, (Vial, wp.Well)):
            pump_control_logger.error(
                f"Invalid solution container type: {type(solution)}"
            )
            return None

        # Convert volume to milliliters using the helper method
        volume_ml = self._ul_to_ml(volume_to_aspirate)

        # Log the operation
        pump_control_logger.info(
            f"Aspirating {volume_to_aspirate} µL ({volume_ml} mL) at {rate} mL/min"
            + (f" from {solution}" if solution else " of air")
        )

        # Check if volume would exceed capacity
        pipette_capacity_ul = self._ml_to_ul(self.syringe_capacity)
        if self.pipette_tracker.volume + volume_to_aspirate > pipette_capacity_ul:
            pump_control_logger.warning(
                f"Cannot aspirate {volume_to_aspirate} µL - would exceed pipette capacity of {pipette_capacity_ul} µL"
            )
            return None

        # If no solution is provided, assume air withdrawal
        if solution is None:
            # Use max pump rate for air
            try:
                _ = self.run_pump(
                    nesp_lib.PumpingDirection.WITHDRAW, volume_ml, self.max_pump_rate
                )
                self.pipette_tracker.volume += self._ml_to_ul(
                    self.pump.volume_withdrawn
                )
                pump_control_logger.debug(
                    f"Pump has aspirated: {self.pump.volume_withdrawn:.6f} ml of air at {self.pump.pumping_rate}mL/min. Pipette vol: {self.pipette_tracker.volume:.3f} ul",
                )
                self.pump.volume_infused_clear()
                self.pump.volume_withdrawn_clear()
            except Exception as e:
                pump_control_logger.error(f"Error during air aspiration: {e}")
                pump_control_logger.exception(e)
                return None
            return None

        # If solution is provided, proceed with regular solution withdrawal
        try:
            if isinstance(solution, Vial):
                density = solution.density
            else:
                density = None
                rate = self.max_pump_rate if rate is None else rate

            _ = self.run_pump(
                nesp_lib.PumpingDirection.WITHDRAW, volume_ml, rate, density
            )

            volume_withdrawn_ml = round(self.pump.volume_withdrawn, PRECISION)
            volume_withdrawn_ul = self._ml_to_ul(volume_withdrawn_ml)

            # Update the pipette and solution based on what was aspirated
            if isinstance(solution, (Vial, wp.Well)):
                # Update the solution volume and contents
                removed_contents = solution.remove_contents(volume_withdrawn_ul)
                for soln, vol in removed_contents.items():
                    self.pipette_tracker.update_contents(soln, vol)

                pump_control_logger.debug(
                    f"Pump has aspirated: {volume_withdrawn_ml:.6f} ml at {self.pump.pumping_rate}mL/min from {solution}. Pipette vol: {self.pipette_tracker.volume:.3f} ul",
                )
            else:
                # If the solution is not a vial or well, only update the volume
                self.pipette_tracker.volume = round(
                    self.pipette_tracker.volume + volume_withdrawn_ul, PRECISION
                )

                pump_control_logger.debug(
                    f"Pump has aspirated: {self.pump.volume_withdrawn:.6f} ml at {self.pump.pumping_rate}mL/min. Pipette vol: {self.pipette_tracker.volume:.3f} ul",
                )

            # Clear the pump's memory
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()

            # If a drip stop is requested, perform it
            if drip_stop:
                drip_stop_success = self.drip_stop()
                if not drip_stop_success:
                    pump_control_logger.warning(
                        "Failed to perform drip stop after aspiration"
                    )

            return solution
        except Exception as e:
            pump_control_logger.error(f"Error during aspiration: {e}")
            pump_control_logger.exception(e)
            return None

    def dispense(
        self,
        volume_to_dispense: float,
        being_infused: Optional[Union[Vial, wp.Well]] = None,
        infused_into: Optional[Union[Vial, wp.Well]] = None,
        rate: Optional[float] = None,
    ) -> None:
        """
        Infuse the given volume at the given rate from the specified position.
        If a drip stop was performed, it will also dispense the drip stop volume
        but not add it to the destination vessel.

        Args:
            volume_to_dispense (float): Volume to be dispensed in microliters.
            being_infused (Union[Vial, wp.Well], optional): The solution being dispensed to get the density
            infused_into (Union[Vial, wp.Well], optional): The destination of the solution (well or vial)
            rate (float, optional): Pumping rate in milliliters per minute. None defaults to the max pump rate.

        Returns:
            None
        """
        # Validate inputs
        try:
            volume_to_dispense = float(volume_to_dispense)
            if rate is not None:
                rate = float(rate)
            else:
                rate = self.max_pump_rate
        except (ValueError, TypeError) as e:
            pump_control_logger.error(f"Invalid dispense parameters: {e}")
            return None

        if volume_to_dispense <= 0:
            pump_control_logger.warning(
                f"Cannot dispense {volume_to_dispense} µL - volume must be positive"
            )
            return None

        # Check if we have enough volume
        if self.pipette_tracker.volume < volume_to_dispense:
            pump_control_logger.warning(
                f"Cannot dispense {volume_to_dispense} µL - pipette only contains {self.pipette_tracker.volume} µL"
            )
            return None

        # Calculate total dispense volume including drip stop if present
        total_volume_to_dispense = volume_to_dispense
        drip_stop_volume = 0.0

        if self.has_drip_stop:
            drip_stop_volume = self._drip_stop_volume
            total_volume_to_dispense += drip_stop_volume
            pump_control_logger.debug(
                f"Including drip stop volume of {drip_stop_volume} µL in dispense operation"
            )

        # Convert volume to milliliters
        total_volume_ml = self._ul_to_ml(total_volume_to_dispense)

        # Log the operation
        pump_control_logger.info(
            f"Dispensing {volume_to_dispense} µL ({self._ul_to_ml(volume_to_dispense)} mL) at {rate} mL/min"
            + (f" from {being_infused}" if being_infused else "")
            + (f" into {infused_into}" if infused_into else "")
            + (
                f" (including {drip_stop_volume} µL drip stop)"
                if drip_stop_volume > 0
                else ""
            )
        )

        # If no solution/destination is provided, assume air infusion
        if being_infused is None and infused_into is None:
            try:
                _ = self.run_pump(
                    nesp_lib.PumpingDirection.INFUSE,
                    total_volume_ml,
                    self.max_pump_rate,
                )
                self.pipette_tracker.volume -= total_volume_to_dispense
                pump_control_logger.debug(
                    f"Pump has dispensed: {total_volume_ml:.6f} ml of air at {self.pump.pumping_rate}mL/min. Pipette vol: {self.pipette_tracker.volume:.3f} ul"
                )
                self.pump.volume_infused_clear()
                self.pump.volume_withdrawn_clear()
            except Exception as e:
                pump_control_logger.error(f"Error during air dispense: {e}")
                pump_control_logger.exception(e)

            # Reset drip stop flag
            self.has_drip_stop = False
            self._drip_stop_volume = 0.0

            return None

        # Regular solution infusion
        try:
            # Get density from the solution being dispensed if available
            density = (
                being_infused.density
                if being_infused and hasattr(being_infused, "density")
                else None
            )

            # Run the pump to dispense the total volume (including drip stop)
            _ = self.run_pump(
                nesp_lib.PumpingDirection.INFUSE, total_volume_ml, rate, density
            )

            # Fetch the total dispensed volume from the pump
            volume_infused_ml = round(self.pump.volume_infused, PRECISION)
            volume_infused_ul = self._ml_to_ul(volume_infused_ml)

            # Clear the pump's memory
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()

            # Log the infusion details
            pump_control_logger.debug(
                f"Pump has dispensed: {volume_infused_ul:.4f} ul at {self.pump.pumping_rate}mL/min. Pipette vol: {self.pipette_tracker.volume - volume_infused_ul:.4f} ul"
            )

            # Only update the destination with the actual sample volume (exclude drip stop)
            if infused_into is not None:
                # Calculate the sample volume (excluding drip stop)
                sample_volume_ul = min(
                    volume_to_dispense, volume_infused_ul - drip_stop_volume
                )

                # Update the volume and contents of the destination vial or well
                if sum(self.pipette_tracker.contents.values() or [0]) > 0:
                    # Calculate the ratio of each content in the pipette
                    content_ratio = {
                        key: value / sum(self.pipette_tracker.contents.values())
                        for key, value in self.pipette_tracker.contents.items()
                    }

                    # Add the proportional contents to the destination
                    infused_into.add_contents(
                        {
                            key: ratio * sample_volume_ul
                            for key, ratio in content_ratio.items()
                        },
                        sample_volume_ul,
                    )

                    # Remove the dispensed contents from the pipette
                    for key, ratio in content_ratio.items():
                        self.pipette_tracker.update_contents(
                            key, -volume_infused_ul * ratio
                        )
                else:
                    # If no contents defined but we have volume, still update the destination
                    infused_into.add_contents({}, sample_volume_ul)
                    # Update the pipette volume
                    self.pipette_tracker.volume -= volume_infused_ul
            else:
                # If no destination vessel, just update the pipette volume
                self.pipette_tracker.volume -= volume_infused_ul

            # Reset drip stop flag
            self.has_drip_stop = False
            self._drip_stop_volume = 0.0

            return None
        except Exception as e:
            pump_control_logger.error(f"Error during dispense: {e}")
            pump_control_logger.exception(e)
            return None

    def run_pump(
        self,
        pump_direction: nesp_lib.PumpingDirection,
        volume_ml: float,
        rate=None,
        density=None,
        blowout_ml=float(0.0),
    ) -> float:
        """Combine all the common commands to run the pump into one function"""
        volume_ml = float(volume_ml)
        blowout_ml = float(blowout_ml)
        density = float(density) if density is not None else None
        if volume_ml <= 0:
            return 0
        # Set the pump parameters for the run
        if self.pump.pumping_direction != pump_direction:
            self.pump.pumping_direction = pump_direction
        self.pump.pumping_volume = round(
            float(volume_ml + blowout_ml), PRECISION
        )  # conver to float for nesp-lib
        if rate is None:
            self.pump.pumping_rate = float(
                self.max_pump_rate
            )  # conver to float for nesp-lib
        else:
            self.pump.pumping_rate = float(rate)
        action = (
            "Aspirating"
            if pump_direction == nesp_lib.PumpingDirection.WITHDRAW
            else "Dispensing"
        )

        pump_control_logger.info(
            "%s %f ml (%f of solution) at %f mL/min...",
            action,
            self.pump.pumping_volume,
            volume_ml,
            self.pump.pumping_rate,
        )
        time.sleep(0.5)
        self.pump.run()
        while self.pump.running:
            pass

        action_type = (
            "dispensed"
            if pump_direction == nesp_lib.PumpingDirection.INFUSE
            else "aspirated"
        )
        action_volume = (
            self.pump.volume_infused
            if pump_direction == nesp_lib.PumpingDirection.INFUSE
            else self.pump.volume_withdrawn
        )
        log_msg = f"Pump has {action_type}: {action_volume} ml"
        pump_control_logger.debug(log_msg)

        return 0

    def update_pipette_volume(self, volume_ml: float):
        """Change the volume of the pipette in ml"""
        volume_ml = float(volume_ml)
        if self.pump.pumping_direction == nesp_lib.PumpingDirection.INFUSE:
            self.pipette_tracker.volume = round(
                self.pipette_tracker.volume - (volume_ml * 1000), PRECISION
            )
        else:
            self.pipette_tracker.volume = round(
                self.pipette_tracker.volume + (volume_ml * 1000), PRECISION
            )

    def _ul_to_ml(self, volume_ul: float) -> float:
        """
        Convert volume from microliters to milliliters.

        Args:
            volume_ul (float): Volume in microliters

        Returns:
            float: Volume in milliliters with appropriate precision
        """
        try:
            volume_ul = float(volume_ul)
            return round(volume_ul * self.UL_TO_ML, PRECISION)
        except (ValueError, TypeError) as e:
            pump_control_logger.error(f"Error converting volume to mL: {e}")
            return 0.0

    def _ml_to_ul(self, volume_ml: float) -> float:
        """
        Convert volume from milliliters to microliters.

        Args:
            volume_ml (float): Volume in milliliters

        Returns:
            float: Volume in microliters with appropriate precision
        """
        try:
            volume_ml = float(volume_ml)
            return round(volume_ml * self.ML_TO_UL, PRECISION)
        except (ValueError, TypeError) as e:
            pump_control_logger.error(f"Error converting volume to µL: {e}")
            return 0.0


class MockPump(SyringePump):
    """
    Mock implementation of the SyringePump class for testing.

    Simulates the behavior of a real syringe pump without requiring hardware connection.
    Maintains accurate volume tracking, state management, and simulated timing.
    """

    def __init__(self):
        """Initialize the mock pump with same parameters as real pump but use mock hardware"""
        self.connected = False
        # Configuration constants
        self.max_pump_rate = config.getfloat(
            "PUMP", "max_pumping_rate", fallback=0.640
        )  # ml/min
        self.syringe_capacity = config.getfloat(
            "PUMP", "syringe_capacity", fallback=1.0
        )  # mL

        # Liquid handling specific constants
        self.prime_volume_ul = config.getfloat(
            "PUMP", "prime_volume_ul", fallback=20.0
        )  # µL
        self.drip_stop_volume_ul = config.getfloat(
            "PUMP", "drip_stop_volume_ul", fallback=10.0
        )  # µL

        # Tracking flags - same as real pump
        self.is_primed = False
        self.has_drip_stop = False
        self._drip_stop_volume = 0.0

        # Add unit conversion constants for clarity
        self.UL_TO_ML = 0.001  # Conversion factor from µL to mL
        self.ML_TO_UL = 1000.0  # Conversion factor from mL to µL

        # Initialize the mock pump hardware
        self.pump = self.set_up_pump()

        # Initialize the pipette tracker
        self.pipette_tracker = PipetteDBHandler()

        # Prime by default to match real pump behavior
        if self.pipette_tracker.volume == 0:
            self.prime()

    def set_up_pump(self):
        """
        Set up a mock syringe pump.
        Returns:
            Pump: Initialized mock pump object.
        """
        pump_control_logger.info("Setting up mock pump...")

        # Create the mock pump with the same properties as a real one
        syringe_pump = MockNespLibPump()
        syringe_pump.syringe_diameter = config.getfloat(
            "PUMP", "syringe_inside_diameter", fallback=4.600
        )  # millimeters
        syringe_pump.pumping_rate = self.max_pump_rate
        syringe_pump.volume_infused_clear()
        syringe_pump.volume_withdrawn_clear()

        # Set the address to indicate it's a mock
        syringe_pump.address = "MOCK-PUMP-01"
        log_msg = f"Mock pump created with address {syringe_pump.address}"
        self.connected = True
        pump_control_logger.info(log_msg)

        # Simulate connection delay
        time.sleep(0.1)  # Reduced delay for tests

        return syringe_pump

    def run_pump(
        self,
        pump_direction: nesp_lib.PumpingDirection,
        volume_ml: float,
        rate=None,
        density=None,
        blowout_ml=float(0.0),
    ) -> float:
        """
        Mock implementation of run_pump with simulated timing.

        Args:
            pump_direction: Direction to pump (withdraw/infuse)
            volume_ml: Volume to pump in milliliters
            rate: Pumping rate in mL/min
            density: Density of the liquid (not used in mock)
            blowout_ml: Additional volume for blowout

        Returns:
            float: Always returns 0 for success
        """
        # Convert inputs to correct types like the real implementation
        volume_ml = float(volume_ml)
        blowout_ml = float(blowout_ml)

        # Skip if volume is invalid
        if volume_ml <= 0:
            return 0

        # Configure the mock pump
        if self.pump.pumping_direction != pump_direction:
            self.pump.pumping_direction = pump_direction

        self.pump.pumping_volume = round(float(volume_ml + blowout_ml), PRECISION)

        # Set pumping rate
        if rate is None:
            self.pump.pumping_rate = float(self.max_pump_rate)
        else:
            self.pump.pumping_rate = float(rate)

        # Log the operation
        action = (
            "Aspirating"
            if pump_direction == nesp_lib.PumpingDirection.WITHDRAW
            else "Dispensing"
        )
        pump_control_logger.info(
            f"{action} {self.pump.pumping_volume} ml ({volume_ml} of solution) at {self.pump.pumping_rate} mL/min..."
        )

        # Calculate how long the operation would take and simulate that delay
        operation_time_sec = (volume_ml / self.pump.pumping_rate) * 60
        # Use a shorter delay for testing
        simulated_delay = min(operation_time_sec * 0.1, 0.5)  # Max 0.5s delay for tests
        time.sleep(simulated_delay)

        # Set the appropriate volume that was pumped
        if pump_direction == nesp_lib.PumpingDirection.WITHDRAW:
            self.pump.volume_withdrawn = volume_ml
            action_volume = self.pump.volume_withdrawn
            action_type = "aspirated"
        else:  # INFUSE
            self.pump.volume_infused = volume_ml
            action_volume = self.pump.volume_infused
            action_type = "dispensed"

        # Log the completion
        log_msg = f"Mock pump has {action_type}: {action_volume} ml"
        pump_control_logger.debug(log_msg)

        return 0

    def close(self):
        """Clean up the mock pump resources"""
        if self.connected:
            pump_control_logger.info("Mock pump disconnected")
            self.connected = False

    # All other methods are inherited from SyringePump and work with the mock pump
