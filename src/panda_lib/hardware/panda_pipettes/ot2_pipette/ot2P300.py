"""
A "driver" class for controlling an Arduino-based pipette driver via serial communication
"""

# pylint: disable=line-too-long, too-many-arguments, too-many-lines, too-many-instance-attributes, too-many-locals, import-outside-toplevel
import time
import serial
import serial.tools.list_ports
from typing import Optional, Dict, Any, List, Union

from panda_lib.labware import Vial
from panda_lib.labware import wellplates as wp
from shared_utilities import get_port_manufacturers, get_ports
from shared_utilities.config.config_tools import read_config
from shared_utilities.log_tools import (
    default_logger as p300_control_logger,
)
from shared_utilities.log_tools import (
    setup_default_logger,
    timing_wrapper,
)

from .pipette import Pipette
from panda_lib.hardware.arduino_interface import ArduinoLink as ArduinoInterface

vessel_logger = setup_default_logger(log_name="vessel")

config = read_config()
PRECISION = config.getint("OPTIONS", "precision")

# Arduino-specific constants
ARDUINO_BAUDRATE = 115200
ARDUINO_TIMEOUT = 5
MAX_CONNECTION_ATTEMPTS = 3
COMMAND_TIMEOUT = 60  # seconds
SERIAL_DELAY = 0.1  # seconds between commands


class OT2P300:
    """
    Class for controlling an Arduino-based pipette using the ArduinoInterface

    Attributes:
        arduino (ArduinoInterface): Arduino communication interface
        connected (bool): Whether the connection is established
        pipette (Pipette): Pipette object to track contents and volume
        pipette_capacity_ul (float): Maximum volume of the pipette in microliters

    Methods:
        aspirate(volume, rate): Aspirate the given volume at the given rate.
        dispense(volume, rate): Dispense the given volume at the given rate.
        mix(repetitions, volume, rate): Mix the solution in the pipette.
        update_pipette_volume(volume_ul): Set the volume of the pipette in ul.
        set_pipette_capacity(capacity_ul): Set the capacity of the pipette in ul.

    Exceptions:
        OverFillException: Raised when a pipette tip is over filled.
        OverDraftException: Raised when a pipette tip is over drawn.
    """

    def __init__(self):
        """
        Initialize the Arduino-based pipette driver.
        """
        self.connected = False
        self.arduino = ArduinoInterface()
        
        # Configuration constants
        self.max_p300_rate = config.getfloat(
            "P300", "max_pipetting_rate", fallback=50.0
        )  # µL/s for Arduino pipette
        
        # Create pipette object to track contents
        self.pipette = Pipette()
        self.pipette_capacity_ul = config.getfloat(
            "P300", "pipette_capacity", fallback=300.0
        )  # µL
        
        # Try to connect to the Arduino
        self._connect_to_arduino()

    def _connect_to_arduino(self):
        """
        Connect to the Arduino pipette driver.
        """
        # Try the configured port first if it exists
        port = config.get("P300", "arduino_port", fallback=None)
        
        if port:
            try:
                self.arduino.connect(port)
                self.connected = True
                config.set("P300", "arduino_port", port)
                return
            except Exception as e:
                p300_control_logger.error(f"Failed to connect to configured port {port}: {e}")
        
        # Try to auto-detect Arduino
        ports = get_ports()
        for port in ports:
            try:
                self.arduino.connect(port)
                self.connected = True
                config.set("P300", "arduino_port", port)
                p300_control_logger.info(f"Connected to Arduino on port {port}")
                return
            except Exception as e:
                p300_control_logger.debug(f"Failed to connect on port {port}: {e}")
                continue
                
        p300_control_logger.error("Failed to connect to Arduino pipette driver")
        raise ConnectionError("Could not connect to Arduino pipette driver")

    def __enter__(self):
        """Enter the context manager"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager"""
        self.close()

    def close(self):
        """Disconnect from the Arduino"""
        if self.arduino:
            self.arduino.disconnect()
            self.connected = False
            p300_control_logger.info("Disconnected from Arduino pipette driver")

    @timing_wrapper
    def aspirate(
        self,
        volume_to_aspirate: float,
        solution: Optional[object] = None,
        rate: float = None,
    ) -> Optional[object]:
        """
        Aspirate the given volume at the given rate from the specified vessel.
        Update the volume of the pipette and the solution if given.
        
        Args:
            volume_to_aspirate (float): Volume to be aspirated in microliters.
            solution (Vessel object): The vial or well to aspirate from
            rate (float): Pumping rate in µL/second. None defaults to the max p300 rate.

        Returns:
            The updated solution object if given one
        """
        if volume_to_aspirate <= 0:
            return None

        # Check if volume would exceed capacity
        if self.pipette.volume + volume_to_aspirate > self.pipette_capacity_ul:
            p300_control_logger.warning(
                f"Cannot aspirate {volume_to_aspirate} µL - would exceed pipette capacity"
            )
            return None

        # Use the Arduino to aspirate
        if not rate:
            rate = self.max_p300_rate
            
        success = self.arduino.aspirate(volume_to_aspirate, rate)
        
        if not success:
            p300_control_logger.error(f"Failed to aspirate {volume_to_aspirate} µL")
            return None
            
        # Update the volume from Arduino's reported value
        self.pipette.volume = self.arduino.volume
        
        # If we have a solution, update the pipette contents and the solution volume
        if solution is not None and isinstance(solution, (Vial, wp.Well)):
            removed_contents = solution.remove_contents(volume_to_aspirate)
            for soln, vol in removed_contents.items():
                self.pipette.update_contents(soln, vol)
                
            p300_control_logger.debug(
                f"Aspirated: {volume_to_aspirate} µL at {rate} µL/s. Pipette vol: {self.pipette.volume} µL"
            )

        return None

    @timing_wrapper
    def aspirate_air(self, volume: float) -> None:
        """
        Aspirate the given µL of air with the pipette
        
        Args:
            volume (float): Volume of air to aspirate in µL
        """
        if volume <= 0:
            return None
            
        # Use the Arduino to aspirate air
        success = self.arduino.aspirate(volume, self.max_p300_rate)
        
        if not success:
            p300_control_logger.error(f"Failed to aspirate {volume} µL of air")
            return None
            
        # Update the volume from Arduino's reported value
        self.pipette.volume = self.arduino.volume
        
        p300_control_logger.debug(
            f"Aspirated: {volume} µL of air at {self.max_p300_rate} µL/s. Pipette vol: {self.pipette.volume} µL"
        )
        
        return None

    def dispense(
        self,
        volume_to_dispense: float,
        being_dispensed: Optional[object] = None,
        dispensed_into: Optional[object] = None,
        rate: float = None,
        blowout_ul: float = float(0.0),
    ) -> None:
        """
        Dispense the given volume at the given rate.
        
        Args:
            volume_to_dispense (float): Volume to be dispensed in microliters.
            being_dispensed (Vial object): The solution being dispensed to get the density
            dispensed_into (str or Vial): The destination of the solution (well or vial)
            rate (float): Pumping rate in µL/second. None defaults to the max p300 rate.
            blowout_ul (float): The volume to blowout in microliters
        """
        if volume_to_dispense <= 0:
            return None

        # Check if we have enough volume
        if self.pipette.volume < volume_to_dispense:
            p300_control_logger.warning(
                f"Cannot dispense {volume_to_dispense} µL - pipette only contains {self.pipette.volume} µL"
            )
            return None

        # Use the Arduino to dispense
        if not rate:
            rate = self.max_p300_rate
            
        success = self.arduino.dispense(volume_to_dispense, rate)
        
        if not success:
            p300_control_logger.error(f"Failed to dispense {volume_to_dispense} µL")
            return None
            
        # If blowout is requested, perform it
        if blowout_ul > 0:
            blowout_success = self.arduino.blowout()
            if not blowout_success:
                p300_control_logger.error("Failed to perform blowout")
        
        # Update the volume from Arduino's reported value
        original_volume = self.pipette.volume
        self.pipette.volume = self.arduino.volume
        
        # If we have a destination, update its contents based on what was in the pipette
        if dispensed_into is not None and isinstance(dispensed_into, (Vial, wp.Well)):
            # Calculate the ratio of each content in the pipette
            if sum(self.pipette.contents.values() or [0]) > 0:
                content_ratio = {
                    key: value / sum(self.pipette.contents.values())
                    for key, value in self.pipette.contents.items()
                }
                
                # Add the proportional contents to the destination
                dispensed_into.add_contents(
                    {key: ratio * volume_to_dispense for key, ratio in content_ratio.items()},
                    volume_to_dispense
                )
                
                # Remove the dispensed contents from the pipette
                for key, ratio in content_ratio.items():
                    self.pipette.update_contents(key, -volume_to_dispense * ratio)
        
        p300_control_logger.debug(
            f"Dispensed: {volume_to_dispense} µL at {rate} µL/s. Pipette vol: {self.pipette.volume} µL"
        )
        
        return None

    @timing_wrapper
    def dispense_air(self, volume: float) -> int:
        """
        Dispense the given µL of air with the pipette
        
        Args:
            volume (float): Volume of air to dispense in µL
        """
        if volume <= 0:
            return 0
            
        # Use the Arduino to dispense air
        success = self.arduino.dispense(volume, self.max_p300_rate)
        
        if not success:
            p300_control_logger.error(f"Failed to dispense {volume} µL of air")
            return 1
            
        # Update the volume from Arduino's reported value
        self.pipette.volume = self.arduino.volume
        
        p300_control_logger.debug(
            f"Dispensed: {volume} µL of air at {self.max_p300_rate} µL/s. Pipette vol: {self.pipette.volume} µL"
        )
        
        return 0

    @timing_wrapper
    def mix(self, repetitions: int, volume: float, rate: float = None) -> bool:
        """
        Mix the solution by repeated aspirating and dispensing.
        
        Args:
            repetitions (int): Number of mixing cycles
            volume (float): Volume to mix in µL
            rate (float): Mixing rate in µL/second
            
        Returns:
            bool: True if mixing was successful
        """
        if volume <= 0 or repetitions <= 0:
            return False
            
        # Use Arduino's built-in mixing command
        if not rate:
            rate = self.max_p300_rate
            
        success = self.arduino.mix(repetitions, volume, rate)
        
        if not success:
            p300_control_logger.error(f"Failed to mix {volume} µL for {repetitions} repetitions")
            return False
            
        # Update the volume from Arduino's reported value
        self.pipette.volume = self.arduino.volume
        
        p300_control_logger.debug(
            f"Mixed {repetitions} times with {volume} µL at {rate} µL/s. Pipette vol: {self.pipette.volume} µL"
        )
        
        return True

    @timing_wrapper
    def update_pipette_volume(self, volume_ul: float):
        """
        Update the pipette volume
        
        Args:
            volume_ul (float): New volume in µL
        """
        # Set the volume directly on the Arduino
        success = self.arduino.set_volume(volume_ul)
        
        if success:
            self.pipette.volume = volume_ul
            p300_control_logger.debug(f"Updated pipette volume to {volume_ul} µL")
        else:
            p300_control_logger.error(f"Failed to set pipette volume to {volume_ul} µL")

    def set_pipette_capacity(self, capacity_ul: float):
        """
        Set the maximum capacity of the pipette
        
        Args:
            capacity_ul (float): Maximum capacity in µL
        """
        self.pipette_capacity_ul = capacity_ul
        p300_control_logger.debug(f"Set pipette capacity to {capacity_ul} µL")
        
    def home_pipette(self) -> bool:
        """
        Home the pipette
        
        Returns:
            bool: True if homing was successful
        """
        success = self.arduino.home()
        
        if success:
            # Update volume from Arduino
            self.pipette.volume = self.arduino.volume
            p300_control_logger.debug("Pipette homed successfully")
        else:
            p300_control_logger.error("Failed to home pipette")
            
        return success
        
    def attach_tip(self) -> bool:
        """
        Attach a new tip
        
        Returns:
            bool: True if tip attachment was successful
        """
        success = self.arduino.attach_tip()
        
        if success:
            # Update volume from Arduino
            self.pipette.volume = self.arduino.volume
            p300_control_logger.debug("Tip attached successfully")
        else:
            p300_control_logger.error("Failed to attach tip")
            
        return success
        
    def detach_tip(self) -> bool:
        """
        Detach the current tip
        
        Returns:
            bool: True if tip detachment was successful
        """
        success = self.arduino.detach_tip()
        
        if success:
            # Update volume from Arduino
            self.pipette.volume = self.arduino.volume
            p300_control_logger.debug("Tip detached successfully")
        else:
            p300_control_logger.error("Failed to detach tip")
            
        return success
        
    def reset_pipette(self) -> bool:
        """
        Reset the pipette (home and empty)
        
        Returns:
            bool: True if reset was successful
        """
        success = self.arduino.reset()
        
        if success:
            # Update volume from Arduino
            self.pipette.volume = self.arduino.volume
            # Clear contents
            self.pipette.contents = {}
            p300_control_logger.debug("Pipette reset successfully")
        else:
            p300_control_logger.error("Failed to reset pipette")
            
        return success


class MockArduinoInterface(ArduinoInterface):
    """Mock Arduino driver for testing"""
    
    def __init__(self, port=None, baudrate=ARDUINO_BAUDRATE, timeout=ARDUINO_TIMEOUT):
        """Initialize the mock Arduino connection."""
        super().__init__(port, baudrate, timeout)
        self.position = 0.0
        self.volume = 0.0
        self.connected = False
        self.max_volume = 300.0
        self.min_volume = 20.0
        self.zero_position = 0.0
        self.max_position = 60.0
        
    def connect(self, port=None):
        """Mock connection to Arduino"""
        self.connected = True
        p300_control_logger.info("Connected to mock Arduino pipette driver")
        return True
        
    def disconnect(self):
        """Mock disconnect from Arduino"""
        self.connected = False
        p300_control_logger.info("Disconnected from mock Arduino pipette driver")
        
    def send_command(self, cmd: str, timeout=COMMAND_TIMEOUT) -> str:
        """Mock sending a command to Arduino"""
        p300_control_logger.debug(f"Mock sending command: {cmd}")
        
        # Process the command based on first character
        if cmd.startswith("H"):
            # Home command
            self.position = 0.0
            self.volume = 0.0
            return "Homing pipette...\nHoming complete - position set to 0\nOK"
            
        elif cmd.startswith("P"):
            # Status command
            return f"=== Pipette Status ===\nPosition: {self.position} mm\nVolume: {self.volume} µL\nTip attached: Yes\nMotor enabled: Yes\nLimit switch: Not triggered\nOK"
            
        elif cmd.startswith("M"):
            # Move command
            try:
                parts = cmd[1:].split(',')
                target_position = float(parts[0])
                self.position = target_position
                # Calculate volume based on position
                ratio = (self.position - self.zero_position) / (self.max_position - self.zero_position)
                self.volume = self.min_volume + ratio * (self.max_volume - self.min_volume)
                return f"Moving to position: {target_position} mm\nMove complete. Position: {self.position} mm, Volume: {self.volume} µL\nOK"
            except Exception:
                return "ERROR: Invalid move command"
                
        elif cmd.startswith("V"):
            # Set volume command
            try:
                volume = float(cmd[1:])
                self.volume = volume
                # Calculate position based on volume
                ratio = (self.volume - self.min_volume) / (self.max_volume - self.min_volume)
                self.position = self.zero_position + ratio * (self.max_position - self.zero_position)
                return f"Setting volume to {volume} µL\nPosition: {self.position} mm\nOK"
            except Exception:
                return "ERROR: Invalid volume command"
                
        elif cmd.startswith("A"):
            # Aspirate command
            try:
                parts = cmd[1:].split(',')
                volume = float(parts[0])
                if self.volume + volume > self.max_volume:
                    return f"ERROR: Cannot aspirate {volume} µL - would exceed capacity"
                self.volume += volume
                # Calculate position based on volume
                ratio = (self.volume - self.min_volume) / (self.max_volume - self.min_volume)
                self.position = self.zero_position + ratio * (self.max_position - self.zero_position)
                return f"Aspirating {volume} µL\nPosition: {self.position} mm, Volume: {self.volume} µL\nOK"
            except Exception:
                return "ERROR: Invalid aspirate command"
                
        elif cmd.startswith("E"):
            # Dispense command
            try:
                parts = cmd[1:].split(',')
                volume = float(parts[0])
                if self.volume - volume < 0:
                    return f"ERROR: Cannot dispense {volume} µL - insufficient volume"
                self.volume -= volume
                # Calculate position based on volume
                ratio = (self.volume - self.min_volume) / (self.max_volume - self.min_volume)
                self.position = self.zero_position + ratio * (self.max_position - self.zero_position)
                return f"Dispensing {volume} µL\nPosition: {self.position} mm, Volume: {self.volume} µL\nOK"
            except Exception:
                return "ERROR: Invalid dispense command"
                
        elif cmd.startswith("B"):
            # Blowout command
            self.volume = 0
            self.position = self.max_position
            return "Performing blowout...\nPosition: {self.position} mm, Volume: 0 µL\nOK"
            
        elif cmd.startswith("X"):
            # Mix command
            return "Mixing...\nMixing complete\nOK"
            
        elif cmd.startswith("T+"):
            # Attach tip
            self.position = 0.0
            self.volume = 0.0
            return "Attaching new tip...\nTip attached successfully\nOK"
            
        elif cmd.startswith("T-"):
            # Detach tip
            self.position = self.max_position
            self.volume = 0.0
            return "Detaching tip...\nTip detached\nOK"
            
        elif cmd.startswith("R"):
            # Reset
            self.position = 0.0
            self.volume = 0.0
            return "Resetting pipette...\nOK"
            
        elif cmd.startswith("?"):
            # Help
            return "Pipette Driver v1.1\n=== Pipette Driver Commands ===\nOK"
            
        else:
            return "ERROR: Unknown command"


class MockOT2P300(OT2P300):
    """Mock P300 class for testing"""

    def _connect_to_arduino(self):
        """Connect to a mock Arduino driver"""
        self.arduino = MockArduinoInterface()
        self.arduino.connect()
        self.connected = True
        p300_control_logger.info("Connected to mock Arduino pipette driver")
        
    def close(self):
        """Disconnect from the mock Arduino"""
        if self.arduino:
            self.arduino.disconnect()
            self.connected = False
            p300_control_logger.info("Disconnected from mock Arduino pipette driver")


if __name__ == "__main__":
    # Initialize logger
    setup_default_logger(log_name="arduino_pipette_test")
    
    # Test with mock pipette
    with MockOT2P300() as p300:
        # Test basic operations
        p300.home_pipette()
        p300.aspirate(100)
        p300.dispense(50)
        p300.mix(3, 20)
        
    # Test with real OT2P300 (uncomment to use)
    # with OT2P300() as p300:
    #     p300.home_pipette()
    #     p300.aspirate(100)
    #     p300.dispense(50)
    #     p300.mix(3, 20)