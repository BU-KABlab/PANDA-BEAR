"""
A "driver" class for controlling a new era A-1000 syringe pump using the nesp-lib library
"""
# pylint: disable=line-too-long, too-many-arguments, too-many-lines

import logging
import time
from typing import Optional, Union


import nesp_lib
from sartorius_local.driver import Scale
from sartorius_local.mock import Scale as MockScale
from slack_functions2 import SlackBot
from vials import Vial, Vessel
from mill_control import Mill, MockMill
from wellplate import Wells as Wellplate

pump_control_logger = logging.getLogger("e_panda")
scale_logger = logging.getLogger("e_panda")

class Pump:
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

    def __init__(self, mill: Union[Mill, MockMill], scale: Union[Scale, MockScale]):
        """
        Initialize the pump and set the capacity.
        """
        self.pump = self.set_up_pump()
        self.max_pump_rate = 0.640 # ml/min
        self.syringe_capacity = 1.0  # mL
        self.pipette_capacity_ml = 0.2  # mL
        self.pipette_capacity_ul = 200  # uL
        self.pipette_volume_ul = 0.0  # uL
        self.pipette_volume_ml = 0.0  # mL
        self.mill = mill
        self.scale = scale

    def set_up_pump(self):
        """
        Set up the syringe pump using hardcoded settings.
        Returns:
            Pump: Initialized pump object.
        """
        pump_port = nesp_lib.Port("COM5", 19200)
        pump = nesp_lib.Pump(pump_port)
        pump.syringe_diameter = 4.600  # millimeters #4.643 #4.685
        pump.volume_infused_clear()
        pump.volume_withdrawn_clear()
        log_msg = f"Pump found at address {pump.address}"
        pump_control_logger.info(log_msg)
        time.sleep(2)
        return pump

    def withdraw(
        self, volume: float, solution: Optional[Vessel] = None, rate: float = None, weigh: bool = False
    ):
        """
        Withdraw the given volume at the given rate and depth from the specified position.
        Args:
            volume (float): Volume to be withdrawn in microliters.
            solution (Vial object or str): The vial or wellplate ID to withdraw from
            rate (float): Pumping rate in milliliters per minute.

        Returns:
            The updated solution object if given one
        """
        # Perform the withdrawl
        volume_ul = volume
        if volume > 0:
            volume_ml = volume / 1000.00  # convert the volume argument from ul to ml

            if solution is not None and isinstance(solution, Vial):
                density = solution.density
            else:
                density = None

            self.run_pump(nesp_lib.PumpingDirection.WITHDRAW, volume_ml, rate, density, weigh)
            self.update_pipette_volume(self.pump.volume_withdrawn)
            pump_control_logger.info(
                "Pump has withdrawn: %0.6f ml at %fmL/min  Pipette vol: %0.3f ul",
                self.pump.volume_withdrawn,
                self.pump.pumping_rate,
                self.pipette_volume_ul,
            )
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()
            if solution is not None:
                solution.update_volume(-volume_ul)
                return None
        else:
            return None

    def infuse(
        self, volume_to_infuse: float, being_infused: Optional[Vessel] = None, infused_into: Optional[Vessel] = None, rate: float = 0.5, blowout_ul: float = 0.0, weigh: bool = False
    ) ->  int:
        """
        Infuse the given volume at the given rate and depth from the specified position.
        Args:
            volume (float): Volume to be infused in microliters.
            solution (Vial object): The solution being infused to get the density
            destination (str or Vial): The destination of the solution (well or vial)
            rate (float): Pumping rate in milliliters per minute.
            blowout_ul (float): The volume to blowout in microliters
            weigh (bool): If true, will weigh the solution before and after infusing and log the difference

        Returns:
            int: The difference in weight if weighing, otherwise 0
        """
        # convert the volume argument from ul to ml
        volume_ul = volume_to_infuse
        blowout_ml = blowout_ul / 1000.0
        if volume_ul > 0:
            volume_ml = volume_ul / 1000.000
            if being_infused is not None:
                density = being_infused.density
            else:
                density = None

            self.run_pump(nesp_lib.PumpingDirection.INFUSE, volume_ml, rate, density, blowout_ml, weigh)
            self.update_pipette_volume(self.pump.volume_infused) # doesn't need to include blowout because the pump will count that as infused
            pump_control_logger.info(
                "Pump has infused: %0.6f ml (%0.6f of solution) at %fmL/min Pipette volume: %0.3f ul",
                self.pump.volume_infused,
                self.pump.volume_infused - blowout_ml,
                self.pump.pumping_rate,
                self.pipette_volume_ul,
            )
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()
            if infused_into is not None:
                #TODO change update_volume to check the pumping direction to determine if it should add or subtract
                #TODO correct the volume change based on the difference in weight
                infused_into.update_volume(volume_ul)
                return 0
            else:
                return 0
        else:
            return 0

    # def purge(
    #     self,
    #     purge_vial: Vial,
    #     solution_being_purged: Vial = None,
    #     purge_volume=20.00,
    #     pumping_rate=0.5,
    # ) -> Vial:
    #     """
    #     Perform purging from the pipette.
    #     Args:
    #         purge_vial (Vial object): The vial to purge into
    #         solution (Vial object): The solution being purged
    #         pump (object): The pump object to use
    #         purge_volume (float): The volume to purge in ml (default 20)
    #         pumping_rate (float): The pumping rate in ml/min (default 0.5)

    #     Returns:
    #         The updated purge_vial object
    #     """

    #     pump_control_logger.debug("Purging %f ul...", purge_volume)
    #     purge_vial = self.infuse(volume_to_infuse=purge_volume,
    #                              rate=pumping_rate,
    #                              being_infused= solution_being_purged,
    #                              infused_into=purge_vial
    #                              )
    #     log_msg = f"Purged {purge_volume} ul"
    #     pump_control_logger.debug(log_msg)
    #     #purge_vial.update_volume(purge_volume)
    #     return purge_vial

    def run_pump(self, direction, volume_ml, rate = None, density=None, blowout_ml = 0.0, weigh: bool = False) -> float:
        """Combine all the common commands to run the pump into one function"""
        if volume_ml <= 0:
            return 0
        # Set the pump parameters for the run
        self.pump.pumping_direction = direction
        self.pump.pumping_volume = volume_ml+blowout_ml #ml
        if rate is None:
            self.pump.pumping_rate = self.max_pump_rate
        else:
            self.pump.pumping_rate = rate
        action = (
            "Withdrawing"
            if direction == nesp_lib.PumpingDirection.WITHDRAW
            else "Infusing"
        )
        pre_weight = 0.00
        post_weight = 0.00
        ## Get scale value prior to pump action
        if density is not None and density != 0 and weigh:
            pre_weight = float(self.scale.read_scale())
            scale_logger.debug("Expected difference in scale reading: %f", volume_ml * density)
            scale_logger.debug("Scale reading before %s: %f", action, pre_weight)

        pump_control_logger.info("%s %f ml at %f mL/min...", action, volume_ml, self.pump.pumping_rate)
        time.sleep(0.5)
        self.pump.run()
        while self.pump.running:
            pass
        pump_control_logger.debug("Done %s", action)

        time.sleep(3) # let the scale settle

        ## Get scale value after pump action
        if density is not None and density != 0 and weigh:
            #post_weight = self.scale.value()
            post_weight = float(self.scale.read_scale())
            scale_logger.debug("Scale reading after %s: %f", action, post_weight)
            scale_logger.debug("Scale reading difference: %f", post_weight - pre_weight)
            scale_logger.info("Data,%s,%f,%f,%f,%f, %f",
                            action, volume_ml, density, pre_weight, post_weight, self.pump.pumping_rate
                            )

        action_type = (
            "infused" if direction == nesp_lib.PumpingDirection.INFUSE else "withdrawn"
        )
        action_volume = (
            self.pump.volume_infused
            if direction == nesp_lib.PumpingDirection.INFUSE
            else self.pump.volume_withdrawn
        )
        log_msg = f"Pump has {action_type}: {action_volume} ml"
        pump_control_logger.debug(log_msg)
        if density is not None and density != 0 and weigh:
            expected_difference = volume_ml * density
            difference = post_weight - pre_weight
            scale_logger.debug("Expected difference: %f", expected_difference)
            scale_logger.debug("Actual difference: %f", difference)
            percent_error = abs((difference - expected_difference)/expected_difference)
            if percent_error > .50:
                scale_logger.warning("Percent error is above 50%")
                SlackBot().send_slack_message('alert',f'WARNING: Percent Error was {percent_error*100}% for most recent experiment')
            return difference

        return 0

    def mix(
        self,
        mix_location: Optional[dict] = None,
        mix_repetitions=3,
        mix_volume=200.0,
        mix_rate=0.62,
    ):
        """Mix the solution in the pipette by withdrawing and infusing the solution
        Args:
            mix_location (dict): Dictionary containing x, y, and z coordinates of the position.
            mix_repetitions (int): Number of times to mix the solution.
            mix_volume (float): Volume to be infused in microliters.
            mix_rate (float): Pumping rate in milliliters per minute.

        Returns:
            None
        """
        pump_control_logger.info("Mixing %d times", mix_repetitions)

        if mix_location is None:
            for i in range(mix_repetitions):
                pump_control_logger.debug("Mixing %d of %d times", i, mix_repetitions)
                self.withdraw(volume=mix_volume, rate=mix_rate)
                current_coords = self.mill.current_coordinates()
                current_coords = {
                    "x": current_coords[0],
                    "y": current_coords[1],
                    "z": current_coords[2],
                }
                self.mill.set_feed_rate(500)
                self.mill.move_center_to_position(
                    current_coords["x"], current_coords["y"], current_coords["z"] + 5
                )
                self.infuse(volume_to_infuse=mix_volume, rate=mix_rate)
                self.mill.move_center_to_position(
                    current_coords["x"], current_coords["y"], current_coords["z"]
                )
                self.mill.set_feed_rate(2000)
        else:
            # move to mix location
            self.mill.move_pipette_to_position(mix_location["x"], mix_location["y"], 0)
            self.mill.move_pipette_to_position(
                mix_location["x"], mix_location["y"], mix_location["depth"]
            )
            for i in range(mix_repetitions):
                pump_control_logger.debug("Mixing %d of %d times", i, mix_repetitions)
                self.withdraw(volume=mix_volume, rate=mix_rate)
                self.mill.set_feed_rate(500)
                self.mill.move_pipette_to_position(
                    mix_location["x"], mix_location["y"], mix_location["depth"] + 1.5
                )
                self.infuse(volume_to_infuse=mix_volume, rate=mix_rate)
                self.mill.move_pipette_to_position(
                    mix_location["x"], mix_location["y"], mix_location["depth"]
                )
                self.mill.set_feed_rate(2000)
            # move back to original position
            self.mill.move_pipette_to_position(mix_location["x"], mix_location["y"], 0)
            return None

    def update_pipette_volume(self, volume_ml: float):
        """Change the volume of the pipette in ml"""
        volume_ml = round(volume_ml, 4)
        if self.pump.pumping_direction == nesp_lib.PumpingDirection.INFUSE:
            self.pipette_volume_ul -= volume_ml * 1000
            self.pipette_volume_ml -= volume_ml
        else:
            self.pipette_volume_ul += volume_ml * 1000
            self.pipette_volume_ml += volume_ml

    def set_pipette_capacity(self, capacity_ul):
        """Set the capacity of the pipette in ul"""
        self.pipette_capacity_ul = capacity_ul
        self.pipette_capacity_ml = capacity_ul / 1000.000

class MockPump(Pump):
    """Mock pump class for testing"""
    def __init__(self, mill, scale):
        super().__init__(mill, scale)
        self.max_pump_rate = 0.654 # ml/min
        self.syringe_capacity = 1.0  # mL
        self.pipette_capacity_ml = 0.2  # mL
        self.pipette_capacity_ul = 200  # uL
        self.pipette_volume_ul = 0.0  # uL
        self.pipette_volume_ml = 0.0  # mL
        self.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        self.pumping_rate = self.max_pump_rate

    def set_up_pump(self):
        pump = object()
        return pump

    def withdraw(
        self, volume: float, solution: Optional[Vessel] = None, rate: float = 0.5, weigh: bool = False
    ) -> Optional[float]:
        # Simulate withdraw behavior without sending commands to the pump
        # Update pipette volume, log, and handle exceptions as needed

        # Perform the withdrawl
        volume_ul = volume
        if volume > 0:
            volume_ml = volume / 1000.00  # convert the volume argument from ul to ml

            if solution is not None and isinstance(solution, Vial):
                density = solution.density
            else:
                density = None
            self.pumping_rate = rate
            self.run_pump(nesp_lib.PumpingDirection.WITHDRAW, volume_ml, self.pumping_rate, density, weigh)
            self.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
            self.update_pipette_volume(volume_ml)
            pump_control_logger.info(
                "Pump has withdrawn: %0.6f ml at %fmL/min  Pipette vol: %0.3f ul",
                volume_ml,
                self.pumping_rate,
                self.pipette_volume_ul,
            )

            if solution is not None:
                #TODO change update_volume to check the pumping direction to determine if it should add or subtract
                solution.update_volume(-volume_ul)
                return None
        else:
            return None

    def infuse(
        self, volume_to_infuse: float, being_infused: Optional[Vessel] = None, infused_into: Optional[Vessel] = None, rate: float = 0.5, blowout_ul = 0.0, weigh: bool = False
    ) -> Optional[Vessel]:
        """
        Simulate infuse behavior without sending commands to the pump
        Update pipette volume, log, and handle exceptions as needed        
        
        Args:
            volume (float): Volume to be infused in microliters.
            solution (Vial object): The solution being infused to get the density
            destination (str or Vial): The destination of the solution (well or vial)
            rate (float): Pumping rate in milliliters per minute.

        Returns:
            The updated destination object if given one
        """
        # convert the volume argument from ul to ml
        volume_ul = volume_to_infuse
        blowout_ml = blowout_ul / 1000.0
        if volume_ul > 0:
            volume_ml = volume_ul / 1000.000
            if being_infused is not None:
                density = being_infused.density
            else:
                density = None
            self.pumping_rate = rate
            self.run_pump(nesp_lib.PumpingDirection.INFUSE, volume_ml, self.pumping_rate, density, blowout_ml, weigh)
            self.pumping_direction = nesp_lib.PumpingDirection.INFUSE
            self.update_pipette_volume(volume_ml + blowout_ml)
            pump_control_logger.info(
                "Pump has infused: %0.6f ml (%0.6f of solution) at %fmL/min Pipette volume: %0.3f ul",
                volume_ml,
                self.pumping_rate,
                volume_ml - blowout_ml,
                self.pipette_volume_ul,
            )
            #self.pump.volume_infused_clear()
            #self.pump.volume_withdrawn_clear()
            if infused_into is not None:
                infused_into.update_volume(volume_ul)
                return None
            else:
                return None
        else:
            return None

    def run_pump(self, direction, volume_ml, rate = None, density=None, blowout_ml = 0.0, weigh = False)-> float:
        """Combine all the common commands to run the pump into one function"""
        if volume_ml <= 0:
            return 0
        # Set the pump parameters for the run
        action = (
            "Withdrawing"
            if direction == nesp_lib.PumpingDirection.WITHDRAW
            else "Infusing"
        )
        pre_weight = 0.00
        post_weight = 0.00
        ## Get scale value prior to pump action
        if density is not None and density != 0 and weigh:
            pre_weight = float(self.scale.read_scale())
            scale_logger.debug("Expected difference in scale reading: %f", volume_ml * density)
            scale_logger.debug("Scale reading before %s: %f", action, pre_weight)

        pump_control_logger.debug("%s %f ml at %f mL/min...", action, volume_ml, rate)
        time.sleep(0.05)
        pump_control_logger.debug("Done %s", action)
        time.sleep(0.05)

        ## Get scale value after pump action
        if density is not None and density != 0 and weigh:
            post_weight = float(self.scale.read_scale())
            scale_logger.debug("Scale reading after %s: %f", action, post_weight)
            scale_logger.debug("Scale reading difference: %f", post_weight - pre_weight)
            scale_logger.info("Data,%s,%f,%f,%f,%f, %f",
                            action, volume_ml, density, pre_weight, post_weight, self.pumping_rate
                            )

        action_type = (
            "infused" if direction == nesp_lib.PumpingDirection.INFUSE else "withdrawn"
        )
        action_volume = (
            volume_ml
            if direction == nesp_lib.PumpingDirection.INFUSE
            else volume_ml
        )
        log_msg = f"Pump has {action_type}: {action_volume} ml"
        pump_control_logger.debug(log_msg)
        if density is not None and density != 0 and weigh:
            return post_weight - pre_weight
        else:
            return 0

    def update_pipette_volume(self, volume_ml):
        """Change the pipette volume by the given amount
        Args:
            volume_ml (float): The amount to change the pipette volume by

        Returns:
            None
        """
        volume_ml = round(volume_ml, 4)
        if self.pumping_direction == nesp_lib.PumpingDirection.INFUSE:
            self.pipette_volume_ul -= volume_ml * 1000
            self.pipette_volume_ml -= volume_ml
        else:
            self.pipette_volume_ul += volume_ml * 1000
            self.pipette_volume_ml += volume_ml

    def set_pipette_capacity(self, capacity_ul):
        self.pipette_capacity_ul = capacity_ul
        self.pipette_capacity_ml = capacity_ul / 1000.000


class OverDraftException(Exception):
    """Raised when a vessel is over drawn"""

    def __init__(self, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self):
        return f"OverDraftException: {self.volume} - {self.added_volume} < 0"


def test_mixing():
    """Test the mixing function"""
    wellplate = Wellplate(
        a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13
    )
    a1 = wellplate.get_coordinates("A1")
    with Mill() as mill:
        mill.homing_sequence()
        pump = Pump(mill=mill, scale=Scale())
        mill.move_pipette_to_position(a1["x"], a1["y"], 0)
        mill.move_pipette_to_position(a1["x"], a1["y"], a1["depth"])
        pump.mix()


def mock_pump_testing_routine():
    """Test the pump"""
    with MockMill() as mill:
        mock_pump = MockPump(mill=mill, scale = MockScale())
        mock_pump.withdraw(100)
        assert mock_pump.pipette_volume_ul == 100
        mock_pump.infuse(100)
        assert mock_pump.pipette_volume_ul == 0
        mock_pump.mix()


if __name__ == "__main__":
    # test_mixing()
    #mock_pump_testing_routine()
    pump = Pump(mill=MockMill(), scale=MockScale())
    pump.infuse(160, rate=0.64, blowout_ul=50)
