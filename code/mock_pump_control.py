
import logging
import time

# Create a mock class for nesp_lib to simulate the behavior of the actual library
class MockPump:
    def __init__(self):
        self.volume_withdrawn = 0.0
        self.volume_infused = 0.0
        self.syringe_diameter = 4.699
        self.running = False

    def volume_infused_clear(self):
        self.volume_infused = 0.0

    def volume_withdrawn_clear(self):
        self.volume_withdrawn = 0.0

    def run(self):
        self.running = True
        time.sleep(1)
        self.running = False

class Pump:
    def __init__(self):
        """
        Initialize the mock pump and set the capacity.
        """
        self.pump = MockPump()
        self.capacity = 1.0  # mL
        self.pipette_capacity = 0.2  # mL

    def withdraw(self, volume: float, rate: float):
        """
        Mocked withdrawal operation.

        Args:
            volume (float): Volume to be withdrawn in milliliters but given as microliters.
            rate (float): Pumping rate in milliliters per minute.
        """
        volume_ml = volume / 1000  # Convert ul to ml

        if self.pump.volume_withdrawn + volume_ml > self.pipette_capacity:
            raise OverFillException(volume_ml, self.pump.volume_withdrawn, self.pipette_capacity)

        self.run_pump(MockPumpingDirection.WITHDRAW, volume_ml, rate)
        return 0

    def infuse(self, volume: float, rate: float):
        """
        Mocked infusion operation.

        Args:
            volume (float): Volume to be infused in milliliters but given as microliters.
            rate (float): Pumping rate in milliliters per minute.
        """
        volume_ml = volume / 1000  # Convert ul to ml

        if volume_ml > 0.0:
            if self.pump.volume_withdrawn - volume_ml < 0:
                raise OverDraftException(volume_ml, self.pump.volume_withdrawn, self.capacity)

            self.run_pump(MockPumpingDirection.INFUSE, volume_ml, rate)

        return 0

    def run_pump(self, direction, volume_ml, rate):
        """Combine all the common commands to run the mock pump into one function"""
        self.pump.running = True
        action = "Withdrawing" if direction == MockPumpingDirection.WITHDRAW else "Infusing"
        log_msg = f"{action} {volume_ml} ml at {rate} ml/min"
        logger.debug(log_msg)
        time.sleep(1)
        self.pump.running = False
        action_type = "infused" if direction == MockPumpingDirection.INFUSE else "withdrawn"
        log_msg = f"Mock Pump has {action_type}: {volume_ml} ml"
        logger.debug(log_msg)

class OverFillException(Exception):
    """Raised when a vessel is overfilled"""

    def __init__(self, volume, added_volume, capacity) -> None:
        super().__init__()
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self):
        return f"OverFillException: {self.volume} + {self.added_volume} > {self.capacity}"

class OverDraftException(Exception):
    """Raised when a vessel is overdrawn"""

    def __init__(self, volume, added_volume, capacity) -> None:
        super().__init__()
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self):
        return f"OverDraftException: {self.volume} - {self.added_volume} < 0"

class MockPumpingDirection:
    WITHDRAW = "Withdraw"
    INFUSE = "Infuse"

# Mocking the logger and other non-mocked dependencies
class MockLogger:
    def __init__(self):
        pass

    def setLevel(self, level):
        pass

    def info(self, message, *args):
        pass

    def debug(self, message, *args):
        pass

    def addHandler(self, handler):
        pass

class MockFormatter:
    def __init__(self, format_string):
        pass

class MockFileHandler:
    def __init__(self, filename):
        pass

logger = MockLogger()
logger.setLevel(logging.DEBUG)
formatter = MockFormatter("%(asctime)s:%(name)s:%(message)s")
system_handler = MockFileHandler("ePANDA.log")