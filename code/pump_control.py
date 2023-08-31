'''
A "driver" class for controlling a new era A-1000 syringe pump using the nesp-lib library
'''
import logging
import time
import nesp_lib

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
file_handler = logging.FileHandler("pump_control.log")
system_handler = logging.FileHandler("ePANDA.log")
file_handler.setFormatter(formatter)
system_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(system_handler)

class Pump():
    '''
    Class for controlling a new era A-1000 syringe pump using the nesp-lib library
    
    Attributes:
        pump (Pump): Initialized pump object.
        capacity (float): Maximum volume of the syringe in milliliters.
    
    Methods:
        withdraw(volume, rate): Withdraw the given volume at the given rate.
        infuse(volume, rate): Infuse the given volume at the given rate.
    
    Exceptions:
        OverFillException: Raised when a syringe is over filled.
        OverDraftException: Raised when a syringe is over drawn.
    '''

    def __init__(self):
        """
        Initialize the pump and set the capacity.
        """
        self.pump = self.set_up_pump()
        self.capacity = 1.0 #mL

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

    def withdraw(self, volume: float, rate: float):
        """
        Withdraw the given volume at the given rate and depth from the specified position.
        Args:
            volume (float): Volume to be withdrawn in milliliters but given as microliters.
            position (dict): Dictionary containing x, y, and z coordinates of the position.
            depth (float): Depth to plunge from the specified position in millimeters.
            rate (float): Pumping rate in milliliters per minute.
        """
        # Perform the withdrawl

        ## convert the volume argument from ul to ml
        volume = volume / 1000

        if (
            self.pump.volume_withdrawn + volume > 0.2
        ):  # 0.2 is the maximum volume for the pipette tip
            raise OverFillException(volume, self.pump.volume_withdrawn, self.capacity)

        self.pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        self.pump.pumping_volume = (
            volume  # Sets the pumping volume of the pump in units of milliliters.
        )
        self.pump.pumping_rate = rate  # in units of milliliters per minute.
        self.pump.run()
        logger.debug("Withdrawing...")
        time.sleep(0.5)
        while self.pump.running:
            pass
        logger.debug("Done withdrawing")
        time.sleep(2)
        log_msg = f"Pump has withdrawn: {self.pump.volume_withdrawn} ml"
        logger.debug(log_msg)

        return 0

    def infuse(self, volume: float, rate: float):
        """
        Infuse the given volume at the given rate and depth from the specified position.
        Args:
            volume (float): Volume to be infused in milliliters but given as microliters.
            position (dict): Dictionary containing x, y, and z coordinates of the position.
            depth (float): Depth to lower from the specified position in millimeters.
            rate (float): Pumping rate in milliliters per minute.
        """
        # then lower to the pipetting depth
        # mill.move_pipette_to_position(position["x"], position["y"], depth)
        # Perform infusion

        ## convert the volume argument from ul to ml
        volume = volume / 1000

        if volume > 0.0:

            if self.pump.volume_withdrawn - volume < 0:
                raise OverDraftException(volume, self.pump.volume_withdrawn, self.capacity)

            self.pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
            self.pump.pumping_volume = (
                volume  # Sets the pumping volume of the pump in units of mLs.
            )
            self.pump.pumping_rate = rate  # rate of the pump in units of mL/min.
            self.pump.run()
            logger.debug("Infusing...")
            time.sleep(0.5)
            while self.pump.running:
                pass
            time.sleep(2)
            log_msg = f"Pump has infused: {self.pump.volume_infused} ml"
            logger.debug(log_msg)
        else:
            pass
        return 0


class OverFillException(Exception):
    """Raised when a vessel is over filled"""

    def __init__(self, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self) -> str:
        return f"OverFillException: {self.volume} + {self.added_volume} > {self.capacity}"


class OverDraftException(Exception):
    """Raised when a vessel is over drawn"""

    def __init__(self, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self) -> str:
        return f"OverDraftException: {self.volume} - {self.added_volume} < 0"
