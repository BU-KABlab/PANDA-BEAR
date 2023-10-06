'''
A "driver" class for controlling a new era A-1000 syringe pump using the nesp-lib library
'''
import logging
import time
import nesp_lib
from scale import Sartorius as Scale
from vials import Vial
from mill_control import Mill, Instruments
from wellplate import Wells as Wellplate

# set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)


class Pump():
    '''
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
    '''

    def __init__(self, mill: Mill, scale: Scale):
        """
        Initialize the pump and set the capacity.
        """
        self.pump = self.set_up_pump()
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
        pump.syringe_diameter = 4.699  # millimeters
        pump.volume_infused_clear()
        pump.volume_withdrawn_clear()
        log_msg = f"Pump found at address {pump.address}"
        logger.info(log_msg)
        time.sleep(2)
        return pump

    def withdraw(self, volume: float, solution: Vial = None, rate: float = 0.5) -> int:
        """
        Withdraw the given volume at the given rate and depth from the specified position.
        Args:
            volume (float): Volume to be withdrawn in milliliters but given as microliters.
            position (dict): Dictionary containing x, y, and z coordinates of the position.
            depth (float): Depth to plunge from the specified position in millimeters.
            rate (float): Pumping rate in milliliters per minute.
        """
        # Perform the withdrawl

        # convert the volume argument from ul to ml
        volume = volume / 1000

        self.run_pump(nesp_lib.PumpingDirection.WITHDRAW, volume, rate)
        self.update_pipette_volume(self.pump.volume_withdrawn)
        logging.debug(
            "Pump has withdrawn: %f ml    Pipette vol: %f",
            self.pump.volume_withdrawn,
            self.pipette_volume_ul,
        )
        self.pump.volume_infused_clear()
        self.pump.volume_withdrawn_clear()
        return 0

    def infuse(self, volume: float,  solution: Vial = None, rate: float = 0.5) -> int:
        """
        Infuse the given volume at the given rate and depth from the specified position.
        Args:
            volume (float): Volume to be infused in milliliters but given as microliters.
            rate (float): Pumping rate in milliliters per minute.
        """
        # convert the volume argument from ul to ml
        volume = volume / 1000

        if volume > 0.0:
            self.run_pump(nesp_lib.PumpingDirection.INFUSE, volume, rate)
            self.update_pipette_volume(self.pump.volume_infused)
            logging.debug(
                "Pump has infused: %f ml  Pipette volume: %f",
                self.pump.volume_infused,
                self.pipette_volume_ul,
            )
            self.pump.volume_infused_clear()
            self.pump.volume_withdrawn_clear()
        else:
            pass
        return 0

    def purge(
        self, purge_vial: Vial, solution: Vial = None, purge_volume=20.00, pumping_rate=0.5
    ) -> None:
        """
        Perform purging from the pipette.
        Args:
            purge_vial (Vial object): The vial to purge into
            pump (object): The pump object to use
            purge_volume (float): The volume to purge in ml (default 20)
            pumping_rate (float): The pumping rate in ml/min (default 0.5)

        Returns:
            None
        """
        purge_vial.update_volume(purge_volume)
        logger.debug("Purging %f ul...", purge_volume)
        self.infuse(volume=purge_volume, rate=pumping_rate, solution=solution)
        log_msg = f"Purged {purge_volume} ul"
        logger.debug(log_msg)

    def run_pump(self, direction, volume_ml, rate):
        """Combine all the common commands to run the pump into one function"""

        self.pump.pumping_direction = direction
        self.pump.pumping_volume = volume_ml
        self.pump.pumping_rate = rate
        action = "Withdrawing" if direction == nesp_lib.PumpingDirection.WITHDRAW else "Infusing"
        logger.debug("%s %f ml...", action, volume_ml)
        time.sleep(0.5)
        self.pump.run()
        while self.pump.running:
            pass
        logger.debug("Done %s", action)
        time.sleep(2)
        action_type = "infused" if direction == nesp_lib.PumpingDirection.INFUSE else "withdrawn"
        log_msg = f"Pump has {action_type}: {self.pump.volume_infused} ml"
        logger.debug(log_msg)

    def mix(self, mix_location: dict = None, mix_repetitions=3, mix_volume=200.0, rate=0.62):
        """Mix the solution in the pipette by withdrawing and infusing the solution
        Args:
            mix_location (dict): Dictionary containing x, y, and z coordinates of the position.
            repetitions (int): Number of times to mix the solution.
            volume (float): Volume to be infused in milliliters but given as microliters.
            rate (float): Pumping rate in milliliters per minute.

        Returns:
            None
        """
        logger.info("Mixing %d times", mix_repetitions)

        if mix_location is not None:
            for i in range(mix_repetitions):
                logger.debug("Mixing %d of %d times", i, mix_repetitions)
                self.withdraw(mix_volume, rate)
                current_coords = self.mill.current_coordinates(
                    Instruments.PIPETTE)

                self.mill.move_pipette_to_position(current_coords["x"],
                                                   current_coords["y"],
                                                   current_coords["z"] + 1.5)
                self.infuse(mix_volume, rate)
                self.mill.move_pipette_to_position(current_coords["x"],
                                                   current_coords["y"],
                                                   current_coords["z"])
        else:
            # move to mix location
            self.mill.move_pipette_to_position(
                mix_location['x'], mix_location['y'], 0)
            self.mill.move_pipette_to_position(
                mix_location['x'], mix_location['y'], mix_location['depth'])
            for i in range(mix_repetitions):
                logger.debug("Mixing %d of %d times", i, mix_repetitions)
                self.withdraw(mix_volume, rate)
                self.mill.move_pipette_to_position(
                    mix_location['x'], mix_location['y'], mix_location['depth'] + 1.5)
                self.infuse(mix_volume, rate)
                self.mill.move_pipette_to_position(
                    mix_location['x'], mix_location['y'], mix_location['depth'])
            # move back to original position
            self.mill.move_pipette_to_position(
                mix_location['x'], mix_location['y'], 0)

    def update_pipette_volume(self, volume_ul):
        """Set the volume of the pipette in ul"""
        if self.pump.pumping_direction == nesp_lib.PumpingDirection.INFUSE:
            self.pipette_volume_ul -= volume_ul
            self.pipette_volume_ml -= volume_ul / 1000
        else:
            self.pipette_volume_ul += volume_ul
            self.pipette_volume_ml += volume_ul / 1000

    def set_pipette_capacity(self, capacity_ul):
        """Set the capacity of the pipette in ul"""
        self.pipette_capacity_ml = capacity_ul
        self.pipette_capacity_ul = capacity_ul / 1000


class OverFillException(Exception):
    """Raised when a vessel is over filled"""

    def __init__(self, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self):
        return f"OverFillException: {self.volume} + {self.added_volume} > {self.capacity}"


class OverDraftException(Exception):
    """Raised when a vessel is over drawn"""

    def __init__(self, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self):
        return f"OverDraftException: {self.volume} - {self.added_volume} < 0"
