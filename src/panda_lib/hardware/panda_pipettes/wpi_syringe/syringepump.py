"""
A "driver" class for controlling a new era A-1000 syringe pump using the nesp-lib library
"""

# pylint: disable=line-too-long, too-many-arguments, too-many-lines, too-many-instance-attributes, too-many-locals, import-outside-toplevel
import time
from typing import Optional

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
        withdraw(volume, rate): Withdraw the given volume at the given rate.
        infuse(volume, rate): Infuse the given volume at the given rate.
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
        self.max_pump_rate = config.getfloat(
            "PUMP", "max_pumping_rate", fallback=0.640
        )  # ml/min
        self.syringe_capacity = config.getfloat(
            "PUMP", "syringe_capacity", fallback=1.0
        )  # mL
        self.pump: nesp_lib.Pump = self.set_up_pump()

        self.pipette = PipetteDBHandler()

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

    def aspirate(
        self,
        volume_to_withdraw: float,
        solution: Optional[object] = None,
        rate: float = None,
    ) -> Optional[object]:
        """
        Withdraw the given volume at the given rate from the specified vessel.
        Update the volume of the pipette and the solution if given.
        If only volume is specified, air is withdrawn.

        Args:
            volume_to_withdraw (float): Volume to be withdrawn in microliters.
            solution (Vessel object, optional): The vial or well to withdraw from. If None, air is withdrawn.
            rate (float, optional): Pumping rate in milliliters per minute. None defaults to the max pump rate.

        Returns:
            The updated solution object if given one
        """
        volume_ml = round(float(volume_to_withdraw / 1000), PRECISION)
        if volume_ml <= 0:
            return None

        # If no solution is provided, assume air withdrawal
        if solution is None:
            # Use max pump rate for air
            _ = self.run_pump(
                nesp_lib.PumpingDirection.WITHDRAW, volume_ml, self.max_pump_rate
            )
            self.update_pipette_volume(self.pump.volume_withdrawn)
            pump_control_logger.debug(
                "Pump has withdrawn: %0.6f ml of air at %fmL/min  Pipette vol: %0.3f ul",
                self.pump.volume_withdrawn,
                self.pump.pumping_rate,
                self.pipette.volume,
            )
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()
            return None

        # If solution is provided, proceed with regular solution withdrawal
        if isinstance(solution, Vial):
            density = solution.density
        else:
            density = None
            rate = self.max_pump_rate if rate is None else rate

        _ = self.run_pump(nesp_lib.PumpingDirection.WITHDRAW, volume_ml, rate, density)

        volume_withdrawn_ml = round(self.pump.volume_withdrawn, PRECISION)
        volume_withdrawn_ul = round(volume_withdrawn_ml * 1000, PRECISION)

        # Update the pipette volume
        if isinstance(solution, (Vial, wp.Well)):
            # Update the solution volume and contents
            removed_contents = solution.remove_contents(volume_withdrawn_ul)
            for soln, vol in removed_contents.items():
                self.pipette.update_contents(soln, vol)

            pump_control_logger.debug(
                "Pump has withdrawn: %0.6f ml at %fmL/min  Pipette vol: %0.3f ul",
                self.pump.volume_withdrawn,
                self.pump.pumping_rate,
                self.pipette.volume,
            )
        else:
            # If the solution is not a vial or well, only update the volume
            self.pipette.volume = round(
                self.pipette.volume + volume_withdrawn_ul, PRECISION
            )

            pump_control_logger.debug(
                "Pump has withdrawn: %0.6f ml at %fmL/min  Pipette vol: %0.3f ul",
                self.pump.volume_withdrawn,
                self.pump.pumping_rate,
                self.pipette.volume,
            )

        # Clear the pump's memory
        self.pump.volume_infused_clear()
        self.pump.volume_withdrawn_clear()

        return None

    def dispense(
        self,
        volume_to_infuse: float,
        being_infused: Optional[object] = None,
        infused_into: Optional[object] = None,
        rate: float = None,
        blowout_ul: float = float(0.0),
    ) -> None:
        """
        Infuse the given volume at the given rate from the specified position.
        If only volume is specified, air is infused.

        Args:
            volume_to_infuse (float): Volume to be infused in microliters.
            being_infused (Vial object, optional): The solution being infused to get the density
            infused_into (str or Vial, optional): The destination of the solution (well or vial)
            rate (float, optional): Pumping rate in milliliters per minute. None defaults to the max pump rate.
            blowout_ul (float): The volume to blowout in microliters

        Returns:
            None
        """
        # Convert volume to microliters
        volume_ml = round(float(volume_to_infuse / 1000), PRECISION)
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
                self.pipette.volume -= round(self.pump.volume_infused * 1000, PRECISION)
                pump_control_logger.debug(
                    "Pump has infused: %0.6f ml of air at %fmL/min Pipette volume: %0.3f ul",
                    self.pump.volume_infused,
                    self.pump.pumping_rate,
                    self.pipette.volume,
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

        # Run the pump to infuse the solution
        _ = self.run_pump(
            nesp_lib.PumpingDirection.INFUSE,
            volume_ml,
            rate,
            density,
            blowout_ml,
        )

        # Update the volume of the pipette with the blowout volume
        self.pipette.volume -= blowout_ul

        # Fetch the total infused volume in milliliters and microliters from the pump
        volume_infused_ml_total = round(self.pump.volume_infused, PRECISION)
        volume_infused_ul_total = round(volume_infused_ml_total * 1000, PRECISION)
        volume_infused_ul = round(volume_infused_ul_total - blowout_ul, PRECISION)

        # Clear the pump's infused and withdrawn volumes
        self.pump.volume_infused_clear()
        self.pump.volume_withdrawn_clear()

        # Log the infusion details
        pump_control_logger.debug(
            "Pump has infused: %0.4f ul (%0.4f ul of solution) at %fmL/min Pipette volume: %0.4f ul",
            volume_infused_ul_total,
            volume_infused_ul,
            self.pump.pumping_rate,
            self.pipette.volume,
        )

        if infused_into is not None:
            # Update the volume and contents of the destination vial or well
            infused_into.add_contents(self.pipette.contents, volume_infused_ul)

            # Calculate the ratio of each content in the pipette
            if sum(self.pipette.contents.values() or [0]) > 0:
                content_ratio = {
                    key: value / sum(self.pipette.contents.values())
                    for key, value in self.pipette.contents.items()
                }
            else:
                content_ratio = {key: 1 for key in self.pipette.contents.keys()}

            # Update the contents of the pipette based on the content ratio
            for key, ratio in content_ratio.items():
                self.pipette.update_contents(key, -volume_infused_ul * ratio)
        else:
            # Update the volume of the pipette without the infused volume
            self.pipette.volume -= volume_infused_ul

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
            "infused"
            if pump_direction == nesp_lib.PumpingDirection.INFUSE
            else "withdrawn"
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
            self.pipette.volume = round(
                self.pipette.volume - (volume_ml * 1000), PRECISION
            )
        else:
            self.pipette.volume = round(
                self.pipette.volume + (volume_ml * 1000), PRECISION
            )


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
    # pump.withdraw(160, rate=0.64)
    # pump.infuse(167.43, rate=0.64, blowout_ul=0)

    pipette = PipetteDBHandler()
    pipette.update_contents("water", 100)
