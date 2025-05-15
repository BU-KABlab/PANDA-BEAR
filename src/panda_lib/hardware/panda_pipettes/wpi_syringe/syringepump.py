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
        aspirate(volume, rate): Withdraw the given volume at the given rate.
        dispense(volume, rate): Infuse the given volume at the given rate.
        purge(purge_vial, pump, purge_volume, pumping_rate): Perform purging from the pipette.
        mix(repetitions, volume, rate): Mix the solution in the pipette by withdrawing and infusing the solution.
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

        # Add unit conversion constants for clarity
        self.UL_TO_ML = 0.001  # Conversion factor from µL to mL
        self.ML_TO_UL = 1000.0  # Conversion factor from mL to µL

        self.pump: nesp_lib.Pump = self.set_up_pump()
        self.pipette_tracker = PipetteDBHandler()

    def set_up_pump(self) -> nesp_lib.Pump:
        """
        Set up the syringe pump by attempting to connect to available serial ports.
        The connection order prioritizes:
        1. The port specified in the configuration.
        2. Ports identified with "Silicon Labs" manufacturer.
        3. Any other available serial ports.

        Returns:
            nesp_lib.Pump: Initialized pump object.

        Raises:
            nesp_lib.AddressException: If no pump is found or connection fails on all tried ports.
        """
        all_available_ports = get_ports()
        if not all_available_ports:
            pump_control_logger.error("No serial ports found.")
            raise nesp_lib.AddressException("No serial ports found.")

        ports_to_try_ordered = []
        attempted_ports_set = set()

        # 1. Add configured port
        configured_port = config.get("PUMP", "port", fallback=None)
        if configured_port and configured_port in all_available_ports:
            if configured_port not in attempted_ports_set:
                ports_to_try_ordered.append(configured_port)
                attempted_ports_set.add(configured_port)

        # 2. Add Silicon Labs ports
        ports_manufacturers = get_port_manufacturers()
        for port, manufacturer in ports_manufacturers.items():
            if "silicon labs" in manufacturer.lower() and port in all_available_ports:
                if port not in attempted_ports_set:
                    ports_to_try_ordered.append(port)
                    attempted_ports_set.add(port)

        # 3. Add remaining available ports
        for port in all_available_ports:
            if port not in attempted_ports_set:
                ports_to_try_ordered.append(port)
                attempted_ports_set.add(
                    port
                )  # Add to set to be complete, though list is built

        if not ports_to_try_ordered:
            pump_control_logger.error(
                "No suitable ports to try after ordering and filtering. "
                "Check port availability and configuration."
            )
            raise nesp_lib.AddressException(
                "No suitable ports identified for connection attempt."
            )

        last_exception = None
        for port_to_attempt in ports_to_try_ordered:
            pump_control_logger.info(
                f"Attempting to connect to pump on port: {port_to_attempt}"
            )
            try:
                pump = nesp_lib.Pump(port_to_attempt)
                pump_control_logger.info(
                    f"Successfully connected to pump on {port_to_attempt}"
                )
                self.connected = True
                # Perform any initial pump configuration if needed here
                # e.g., pump.set_diameter(...), pump.set_rate_units(...)
                # For now, assuming nesp_lib handles or pump is pre-configured.
                return pump
            except Exception as e:  # pylint: disable=broad-except
                pump_control_logger.warning(
                    f"Failed to connect on port {port_to_attempt}: {e}"
                )
                last_exception = e
                # self.connected remains False or is handled by __init__ default

        # If loop completes, all attempts failed
        pump_control_logger.error(
            "All connection attempts failed. No pump could be initialized."
        )
        if last_exception:
            raise nesp_lib.AddressException(
                f"Failed to connect to pump on any port. Last error: {last_exception}"
            ) from last_exception
        else:
            # This case should ideally not be reached if ports_to_try_ordered was not empty.
            raise nesp_lib.AddressException(
                "Failed to connect to pump on any port, and no specific "
                "exception was caught during attempts (unexpected state)."
            )

    def __enter__(self):
        """Enter the context manager"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager"""
        self.close()

    def close(self):
        """Disconnect the pump and update connection status."""
        if hasattr(self, "pump") and self.pump:
            if self.connected:
                pump_control_logger.info(
                    f"Closing connection to pump on port {self.pump.port}..."
                )
                try:
                    self.pump.close()
                    self.connected = False
                    pump_control_logger.info("Pump connection closed successfully.")
                except Exception as e:  # pylint: disable=broad-except
                    # Catch a more specific error if nesp_lib provides one for close failures
                    pump_control_logger.error(
                        f"Error closing pump connection on port {self.pump.port}: {e}"
                    )
            else:
                pump_control_logger.info(
                    "Pump object exists but was not marked as connected. No action taken to close."
                )
        else:
            pump_control_logger.info("No pump instance or connection to close.")

    def aspirate(
        self,
        volume_to_aspirate: float,
        solution: Optional[Union[Vial, wp.Well]] = None,
        rate: Optional[float] = None,
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

        # If no solution is provided, assume air withdrawal
        if solution is None:
            # Use max pump rate for air
            try:
                _ = self.run_pump(
                    nesp_lib.PumpingDirection.WITHDRAW, volume_ml, self.max_pump_rate
                )
                self.update_pipette_volume(self.pump.volume_withdrawn)
                pump_control_logger.debug(
                    "Pump has aspirated: %0.6f ml of air at %fmL/min  Pipette vol: %0.3f ul",
                    self.pump.volume_withdrawn,
                    self.pump.pumping_rate,
                    self.pipette_tracker.volume,
                )
                self.pump.volume_infused_clear()
                self.pump.volume_withdrawn_clear()
            except Exception as e:
                pump_control_logger.error(f"Error during air aspiration: {e}")
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
                    "Pump has aspirated: %0.6f ml at %fmL/min from %s. Pipette vol: %0.3f ul",
                    volume_withdrawn_ml,
                    self.pump.pumping_rate,
                    solution,
                    self.pipette_tracker.volume,
                )

            else:
                # If the solution is not a vial or well, only update the volume
                self.pipette_tracker.volume = round(
                    self.pipette_tracker.volume + volume_withdrawn_ul, PRECISION
                )

                pump_control_logger.debug(
                    "Pump has aspirated: %0.6f ml at %fmL/min  Pipette vol: %0.3f ul",
                    self.pump.volume_withdrawn,
                    self.pump.pumping_rate,
                    self.pipette_tracker.volume,
                )

            # Clear the pump's memory
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()

            return solution
        except Exception as e:
            pump_control_logger.error(f"Error during aspiration: {e}")
            return None

    def dispense(
        self,
        volume_to_dispense: float,
        being_infused: Optional[Union[Vial, wp.Well]] = None,
        infused_into: Optional[Union[Vial, wp.Well]] = None,
        rate: Optional[float] = None,
        blowout_ul: float = 0.0,
    ) -> None:
        """
        Infuse the given volume at the given rate from the specified position.
        If only volume is specified, air is dispensed.

        Args:
            volume_to_dispense (float): Volume to be dispensed in microliters.
            being_infused (Union[Vial, wp.Well], optional): The solution being dispensed to get the density
            infused_into (Union[Vial, wp.Well], optional): The destination of the solution (well or vial)
            rate (float, optional): Pumping rate in milliliters per minute. None defaults to the max pump rate.
            blowout_ul (float): The volume to blowout in microliters

        Returns:
            None
        """
        # Convert volume to microliters
        volume_ml = round(float(volume_to_dispense / 1000), PRECISION)
        # Convert blowout volume to milliliters
        blowout_ml = round(float(blowout_ul) / 1000, PRECISION)

        if volume_ml <= 0:
            return None

        # If no solution/destination is provided, assume air infusion
        if being_infused is None and infused_into is None:
            if volume_ml > 0:
                _ = self.run_pump(
                    nesp_lib.PumpingDirection.INFUSE, volume_ml, self.max_pump_rate
                )
                self.pipette_tracker.volume -= round(
                    self.pump.volume_infused * 1000, PRECISION
                )
                pump_control_logger.debug(
                    "Pump has dispensed: %0.6f ml of air at %fmL/min Pipette volume: %0.3f ul",
                    self.pump.volume_infused,
                    self.pump.pumping_rate,
                    self.pipette_tracker.volume,
                )
                self.pump.volume_infused_clear()
                self.pump.volume_withdrawn_clear()
            return None

        # Regular solution infusion
        density = (
            being_infused.density
            if being_infused and hasattr(being_infused, "density")
            else None
        )
        if not rate:
            rate = self.max_pump_rate

        # Handle air infusion case (when only volume is provided)
        is_air_infusion = being_infused is None and infused_into is None

        if is_air_infusion:
            # Air infusion case (previously infuse_air)
            density = None
        elif being_infused is not None and hasattr(being_infused, "density"):
            # Get density from the solution being dispensed
            density = being_infused.density
        else:
            density = None

        # Run the pump to dispense the solution
        _ = self.run_pump(
            nesp_lib.PumpingDirection.INFUSE,
            volume_ml,
            rate,
            density,
            blowout_ml if not is_air_infusion else 0,
        )

        # Update the volume of the pipette with the blowout volume
        self.pipette_tracker.volume -= blowout_ul

        # Fetch the total dispensed volume in milliliters and microliters from the pump
        volume_infused_ml_total = round(self.pump.volume_infused, PRECISION)
        volume_infused_ul_total = round(volume_infused_ml_total * 1000, PRECISION)
        volume_infused_ul = round(volume_infused_ul_total - blowout_ul, PRECISION)

        # Clear the pump's dispensed and aspirated volumes
        self.pump.volume_infused_clear()
        self.pump.volume_withdrawn_clear()

        # Log the infusion details
        pump_control_logger.debug(
            "Pump has dispensed: %0.4f ul (%0.4f ul of solution) at %fmL/min Pipette volume: %0.4f ul",
            volume_infused_ul_total,
            volume_infused_ul,
            self.pump.pumping_rate,
            self.pipette_tracker.volume,
        )

        if infused_into is not None:
            # Update the volume and contents of the destination vial or well
            infused_into.add_contents(self.pipette_tracker.contents, volume_infused_ul)

            # Calculate the ratio of each content in the pipette
            if sum(self.pipette_tracker.contents.values() or [0]) > 0:
                content_ratio = {
                    key: value / sum(self.pipette_tracker.contents.values())
                    for key, value in self.pipette_tracker.contents.items()
                }
            else:
                content_ratio = {key: 1 for key in self.pipette_tracker.contents.keys()}

            # Update the contents of the pipette based on the content ratio
            for key, ratio in content_ratio.items():
                self.pipette_tracker.update_contents(key, -volume_infused_ul * ratio)
        else:
            # Update the volume of the pipette without the dispensed volume
            self.pipette_tracker.volume -= volume_infused_ul

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
            "Withdrawing"
            if pump_direction == nesp_lib.PumpingDirection.WITHDRAW
            else "Infusing"
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
    """Mock pump class for testing"""

    def set_up_pump(self):
        """
        Set up the syringe pump using hardcoded settings.
        Returns:
            Pump: Initialized pump object.
        """
        pump_control_logger.info("Setting up pump...")
        syringe_pump = MockNespLibPump()
        syringe_pump.syringe_diameter = 4.600  # millimeters #4.643 #4.685
        syringe_pump.volume_infused_clear()
        syringe_pump.volume_withdrawn_clear()
        log_msg = f"Pump found at address {syringe_pump.address}"
        self.connected = True
        pump_control_logger.info(log_msg)
        time.sleep(2)
        return syringe_pump

    def close(self):
        self.connected = False


if __name__ == "__main__":
    # test_mixing()
    # _mock_pump_testing_routine()
    # pump.aspirate(160, rate=0.64)
    # pump.dispense(167.43, rate=0.64, blowout_ul=0)

    pipette = PipetteDBHandler()
    pipette.update_contents("water", 100)
