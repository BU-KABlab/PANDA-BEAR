"""
A "driver" class for controlling a new era A-1000 syringe pump using the nesp-lib library
"""

# pylint: disable=line-too-long, too-many-arguments, too-many-lines, too-many-instance-attributes, too-many-locals, import-outside-toplevel
import time
from typing import Optional, Union

from nesp_lib_py import nesp_lib
from nesp_lib_py.nesp_lib.mock import Pump as MockNespLibPump

import panda_lib.wellplate as wp
from panda_lib.config.config_tools import read_config
from panda_lib.experiment_class import ExperimentResult
from panda_lib.pipette import Pipette
from panda_lib.vials import StockVial, Vial2, WasteVial

from panda_lib.log_tools import (
    setup_default_logger,
    default_logger as pump_control_logger,
)

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
        self.max_pump_rate = config.getfloat(
            "PUMP", "max_pumping_rate", fallback=0.640
        )  # ml/min
        self.syringe_capacity = config.getfloat(
            "PUMP", "syringe_capacity", fallback=1.0
        )  # mL
        self.pump = self.set_up_pump()
        self.pipette = Pipette()

    def set_up_pump(self):
        """
        Set up the syringe pump using hardcoded settings.
        Returns:
            Pump: Initialized pump object.
        """
        try:
            pump_control_logger.info("Setting up pump...")
            pump_port = nesp_lib.Port(
                config.get("PUMP", "port", fallback="COM5"),
                config.getint("PUMP", "baudrate", fallback=19200),
            )
            syringe_pump = nesp_lib.Pump(pump_port)
            syringe_pump.syringe_diameter = config.getfloat(
                "PUMP", "syringe_inside_diameter", fallback=4.600
            )  # millimeters
            syringe_pump.pumping_rate = self.max_pump_rate
            syringe_pump.volume_infused_clear()
            syringe_pump.volume_withdrawn_clear()
            log_msg = f"Pump found at address {syringe_pump.address}"
            pump_control_logger.info(log_msg)
            time.sleep(2)
        except Exception as e:
            pump_control_logger.error("Error setting up pump: %s", e)
            pump_control_logger.exception(e)
            raise e
        return syringe_pump

    def withdraw(
        self,
        volume_to_withdraw: float,
        solution: Optional[Union[wp.Well, StockVial, WasteVial]] = None,
        rate: float = None,
        weigh: bool = False,
        results: ExperimentResult = None,
    ):
        """
        Withdraw the given volume at the given rate and depth from the specified position.
        Update the volume of the pipette and the solution if given.
        Args:
            volume (float): Volume to be withdrawn in microliters.
            solution (Vial object or str): The vial or wellplate ID to withdraw from
            rate (float): Pumping rate in milliliters per minute.

        Returns:
            The updated solution object if given one
        """
        # Perform the withdrawl
        # TODO Consider tracking the volume of air in the pipette as blowout and dripstop?
        volume_to_withdraw = float(volume_to_withdraw)
        if volume_to_withdraw > 0:
            volume_ml = (
                volume_to_withdraw / 1000
            )  # convert the volume argument from ul to ml

            if solution is not None and isinstance(solution, Vial2):
                density = solution.density
            else:
                density = None
                rate = (
                    self.max_pump_rate
                )  # if no solution, assume air and use the max pump rate

            _, pumprecord = self.run_pump(
                nesp_lib.PumpingDirection.WITHDRAW, volume_ml, rate, density, weigh
            )

            if solution is not None and isinstance(solution, Vial2):
                pumprecord["solution"] = solution.name
            if results is not None:
                results.pumping_record.append(pumprecord)

            volume_withdrawn_ml = round(self.pump.volume_withdrawn, PRECISION)
            volume_withdrawn_ul = round(volume_withdrawn_ml * 1000, PRECISION)

            # Update the pipette volume
            if isinstance(solution, (Vial2, wp.Well)):
                # If the solution is a vial or well, update the volume and contents
                if isinstance(solution.contents, dict):
                    # If the solution has multiple contents, calculate the ratio
                    # of the solution being withdrawn
                    content_ratio = {
                        key: value / sum(solution.contents.values())
                        for key, value in solution.contents.items()
                    }
                    # Update the pipette contents according to the ratio
                    for key, ratio in content_ratio.items():
                        self.pipette.update_contents(
                            key, float(ratio * volume_withdrawn_ul)
                        )
                else:
                    # If the solution has a single content, update the pipette contents
                    self.pipette.update_contents(solution.contents, volume_withdrawn_ul)

                # Update the solution volume and contents
                solution.update_volume(-volume_withdrawn_ul)
                solution.update_contents(
                    solution.contents, -volume_withdrawn_ul, save=True
                )

                # Updating the contents also updates the volume so we are done here

                # log the action and return
                pump_control_logger.info(
                    "Pump has withdrawn: %0.6f ml at %fmL/min  Pipette vol: %0.3f ul",
                    self.pump.volume_withdrawn,
                    self.pump.pumping_rate,
                    self.pipette.volume,
                )
                # Clear the pump's memory so that future operations are fresh
                self.pump.volume_infused_clear()
                self.pump.volume_withdrawn_clear()

                return None

            elif solution is None:
                # If the solution is not a vial, or a well, we don't track it
                # as contents of the pipette but we do track the volume.
                # This is likely the case for air. Only the volume is updated.
                self.pipette.volume = round(
                    self.pipette.volume + volume_withdrawn_ul, PRECISION
                )

                pump_control_logger.info(
                    "Pump has withdrawn: %0.6f ml at %fmL/min  Pipette vol: %0.3f ul",
                    self.pump.volume_withdrawn,
                    self.pump.pumping_rate,
                    self.pipette.volume,
                )

                # Clear the pump's memory so that future operations are fresh
                self.pump.volume_infused_clear()
                self.pump.volume_withdrawn_clear()

                return None

        else:
            # If the volume is 0, return None
            return None

    def withdraw_air(self, volume: float):
        """Withdraw the given ul of air with the pipette"""
        volume = float(volume)
        if volume > 0:
            volume_ml = volume / 1000
            _, _ = self.run_pump(
                nesp_lib.PumpingDirection.WITHDRAW, volume_ml, self.max_pump_rate
            )
            self.update_pipette_volume(self.pump.volume_withdrawn)
            pump_control_logger.info(
                "Pump has withdrawn: %0.6f ml of air at %fmL/min  Pipette vol: %0.3f ul",
                self.pump.volume_withdrawn,
                self.pump.pumping_rate,
                self.pipette.volume,
            )
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()
            return 0  # return 0 if successful
        else:
            return 1  # return 1 if volume is 0

    def infuse(
        self,
        volume_to_infuse: float,
        being_infused: Optional[Union[wp.Well, StockVial, WasteVial]] = None,
        infused_into: Optional[Union[wp.Well, StockVial, WasteVial]] = None,
        rate: float = None,
        blowout_ul: float = float(0.0),
        weigh: bool = False,
        results: ExperimentResult = None,
    ) -> int:
        """
        Infuse the given volume at the given rate and depth from the specified position.
        Args:
            volume_to_infuse (float): Volume to be infused in microliters.
            being_infused (Vial object): The solution being infused to get the density
            infused_into (str or Vial): The destination of the solution (well or vial)
            rate (float): Pumping rate in milliliters per minute.
            blowout_ul (float): The volume to blowout in microliters
            weigh (bool): If true, will weigh the solution before and after infusing and log the difference
            results (ExperimentResult): The experiment results object to store pumping records

        Returns:
            int: The difference in weight if weighing, otherwise 0
        """
        # Convert volume to microliters
        volume_ul = round(float(volume_to_infuse), PRECISION)
        # Convert blowout volume to milliliters
        blowout_ml = round(float(blowout_ul) / 1000, PRECISION)

        if volume_ul > 0:
            # Convert volume to milliliters
            volume_ml = round(volume_ul / 1000, PRECISION)

            if being_infused is not None:
                # Get density and viscosity from the solution being infused
                density = being_infused.density
                viscosity = being_infused.viscosity_cp
            else:
                density = None
                viscosity = None
                # If no solution is given, assume air and use the max pump rate
            if not rate:
                rate = self.max_pump_rate

            # Run the pump to infuse the solution
            _, pumprecord = self.run_pump(
                nesp_lib.PumpingDirection.INFUSE,
                volume_ml,
                rate,
                density,
                blowout_ml,
                weigh,
                viscosity,
            )

            # Update the volume of the pipette with the blowout volume
            self.pipette.volume -= blowout_ul

            # Fetch the total infused volume in milliliters and microliters from the pump
            volume_infused_ml_total = round(self.pump.volume_infused, PRECISION)
            volume_infused_ul_total = round(volume_infused_ml_total * 1000, PRECISION)
            # Calculate the infused volume without the blowout volume
            volume_infused_ml = round(volume_infused_ml_total - blowout_ml, PRECISION)
            volume_infused_ul = round(volume_infused_ul_total - blowout_ul, PRECISION)

            # Clear the pump's infused and withdrawn volumes
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()

            # Log the infusion details
            pump_control_logger.info(
                "Pump has infused: %0.4f ul (%0.4f ul of solution) at %fmL/min Pipette volume: %0.4f ul",
                volume_infused_ul_total,
                volume_infused_ul,
                self.pump.pumping_rate,
                self.pipette.volume,
            )

            if being_infused is not None and isinstance(being_infused, Vial2):
                # Add the solution name to the pump record if it's a Vial2 object
                pumprecord["solution"] = being_infused.name

            if results is not None:
                # Append the pump record to the experiment results
                results.pumping_record.append(pumprecord)

            if infused_into is not None:
                # Update the volume and contents of the destination vial or well
                infused_into.update_volume(volume_infused_ul)
                infused_into.update_contents(
                    self.pipette.contents, volume_infused_ul, save=True
                )

                # Calculate the ratio of each content in the pipette
                content_ratio = {
                    key: value / sum(self.pipette.contents.values())
                    for key, value in self.pipette.contents.items()
                }

                # Update the contents of the pipette based on the content ratio
                for key, ratio in content_ratio.items():
                    self.pipette.update_contents(key, -volume_infused_ul * ratio)

            else:
                # Update the volume of the pipette without the infused volume
                # We don't need to include the blowout because it was accounted for earlier
                self.pipette.volume -= volume_infused_ul

            return 0  # TODO return infused into like withdraw does
        else:  # If the volume is 0
            return None

    def infuse_air(self, volume: float):
        """Infuse the given ul of air with the pipette"""
        volume_ul = float(volume)
        if volume_ul > 0:
            volume_ml = volume_ul / 1000
            _, _ = self.run_pump(
                nesp_lib.PumpingDirection.INFUSE, volume_ml, self.max_pump_rate
            )
            self.pipette.volume -= volume_ul
            pump_control_logger.info(
                "Pump has infused: %0.6f ml of air at %fmL/min Pipette volume: %0.3f ul",
                self.pump.volume_infused,
                self.pump.pumping_rate,
                self.pipette.volume,
            )
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()
        return 0

    def run_pump(
        self,
        pump_direction: nesp_lib.PumpingDirection,
        volume_ml: float,
        rate=None,
        density=None,
        blowout_ml=float(0.0),
        weigh: bool = False,
        viscosity: float = None,
    ) -> tuple[float, dict]:
        """Combine all the common commands to run the pump into one function"""
        pumping_record = {}
        volume_ml = float(volume_ml)
        blowout_ml = float(blowout_ml)
        density = float(density) if density is not None else None
        if volume_ml <= 0:
            return 0, pumping_record
        # Set the pump parameters for the run
        if self.pump.pumping_direction != pump_direction:
            self.pump.pumping_direction = pump_direction
        self.pump.pumping_volume = float(
            volume_ml + blowout_ml
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
            "%s %f ml at %f mL/min...", action, volume_ml, self.pump.pumping_rate
        )
        time.sleep(0.5)
        self.pump.run()
        while self.pump.running:
            pass
        pump_control_logger.debug("Done %s", action)

        pumping_record = {
            "action": action,
            "solution": "",
            "volume": volume_ml,
            "density": density,
            "pumping_rate": self.pump.pumping_rate,
            "viscosity": viscosity,
        }

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

        return 0, pumping_record


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
        pump_control_logger.info(log_msg)
        time.sleep(2)
        return syringe_pump

if __name__ == "__main__":
    # test_mixing()
    # _mock_pump_testing_routine()
    # pump.withdraw(160, rate=0.64)
    # pump.infuse(167.43, rate=0.64, blowout_ul=0)

    pipette = Pipette()
    pipette.update_contents("water", 100)
