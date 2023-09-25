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
system_handler = logging.FileHandler("ePANDA.log")
system_handler.setFormatter(formatter)
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
        self.syringe_capacity = 1.0 #mL
        self.pipette_capacity_ml = 0.2 #mL
        self.pipette_capacity_ul = 200 #uL
        self.pipette_volume_ul = 0.0 #uL
        self.pipette_volume_ml = 0.0 #mL

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

    def withdraw(self, volume: float, rate: float = 0.5):
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

    def infuse(self, volume: float, rate: float = 0.5):
        """
        Infuse the given volume at the given rate and depth from the specified position.
        Args:
            volume (float): Volume to be infused in milliliters but given as microliters.
            rate (float): Pumping rate in milliliters per minute.
        """
        ## convert the volume argument from ul to ml
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

    def run_pump(self, direction, volume_ml, rate):
        """Combine all the common commands to run the pump into one function"""

        self.pump.pumping_direction = direction
        self.pump.pumping_volume = volume_ml
        self.pump.pumping_rate = rate
        self.pump.run()
        action = "Withdrawing" if direction == nesp_lib.PumpingDirection.WITHDRAW else "Infusing"
        logger.debug("%s %f ml...", action, volume_ml)
        time.sleep(0.5)
        while self.pump.running:
            pass
        logger.debug("Done %s", action)
        time.sleep(2)
        action_type = "infused" if direction == nesp_lib.PumpingDirection.INFUSE else "withdrawn"
        log_msg = f"Pump has {action_type}: {self.pump.volume_infused} ml"
        logger.debug(log_msg)

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
    