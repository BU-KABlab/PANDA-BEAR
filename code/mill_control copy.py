"""
This module contains the MillControl class, which is used to control the a GRBL CNC machine.
The MillControl class is used by the EPanda class to move the pipette and electrode to the
specified coordinates. 

The MillControl class contains methods to move the pipette and
electrode to a safe position, rinse the electrode, and update the offsets in the mill config
file. 

The MillControl class contains methods to connect to the mill, execute commands,
stop the mill, reset the mill, home the mill, get the current status of the mill, get the
gcode mode of the mill, get the gcode parameters of the mill, and get the gcode parser state
of the mill.
"""

# pylint: disable=line-too-long

# standard libraries
import dataclasses
import json
import logging
import re
import time
from datetime import datetime
from enum import Enum
from pathlib import Path

# third-party libraries
# from pydantic.dataclasses import dataclass
import serial
from config.config import (
    MILL_CONFIG,
    PATH_TO_DATA,
    PATH_TO_LOGS,
    STOCK_STATUS,
    WASTE_STATUS,
)

# Configure the logger
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # Change to INFO to reduce verbosity
# formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
# system_handler = logging.FileHandler("code/logs/ePANDA.log")
# system_handler.setFormatter(formatter)
# logger.addHandler(system_handler)
logger = logging.getLogger("e_panda")
if not logger.hasHandlers():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(message)s"
    )
    system_handler = logging.FileHandler(PATH_TO_LOGS / "mill_control.log")
    system_handler.setFormatter(formatter)
    logger.addHandler(system_handler)


@dataclasses.dataclass
class Instruments(Enum):
    """Class for naming of the mill instruments"""

    CENTER = "center"
    PIPETTE = "pipette"
    ELECTRODE = "electrode"
    LENS = "lens"  # Fixed the typo here


# @dataclass
# class MillConfiguration():
#     """Class for the mill configuration"""

#     instrument_offsets: dict
#     working_volume: dict
#     electrode_bath: dict
#     safe_height_floor: float

# @dataclass
# class coordinates():
#     """Class for the coordinates of the mill"""

#     x: float
#     y: float
#     z: float

# @dataclass
# class electrode_offsets(coordinates):
#     """Class for the electrode coordinates"""

# @dataclass
# class pipette_offsets(coordinates):
#     """Class for the pipette coordinates"""

# @dataclass
# class lens_offsets(coordinates):
#     """Class for the lens coordinates"""

# @dataclass
# class center_offsets(coordinates):
#     """Class for the center coordinates"""

# @dataclass
# class working_volume(coordinates):
#     """Class for the working volume of the mill"""

# @dataclass
# class electrode_bath(coordinates):
#     """Class for the electrode bath coordinates"""


class Mill:
    """
    Set up the mill connection and pass commands, including special commands
    """

    def __init__(self, config_file="mill_config.json"):
        self.config_file = config_file
        self.config = self.read_json_config()
        self.ser_mill = self.connect_to_mill()

    def homing_sequence(self):
        """Home the mill, set the feed rate, and clear the buffers"""
        self.home()
        self.set_feed_rate(2000)  # Set feed rate to 2000
        self.clear_buffers()

    def connect_to_mill(self) -> serial.Serial:
        """Connect to the mill"""
        try:
            ser_mill = serial.Serial(
                # Hardcoded serial port (consider making this configurable)
                port="COM4",
                baudrate=115200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=10,
            )
            time.sleep(2)

            if not ser_mill.isOpen():
                logger.info("Opening serial connection to mill...")
                ser_mill.open()
                time.sleep(2)

            logger.info("Mill connected: %s", ser_mill.isOpen())
            print("Mill connected: ", ser_mill.isOpen())
            return ser_mill
        except Exception as exep:
            logger.error("Error connecting to the mill: %s", str(exep))
            raise MillConnectionError("Error connecting to the mill") from exep

    def __enter__(self):
        """Enter the context manager"""
        self.homing_sequence()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager"""
        logger.info("Exiting the mill context manager")
        logger.debug("Disconnecting from the mill")
        self.disconnect()

    def disconnect(self):
        """Close the serial connection to the mill"""
        logger.info("Disconnecting from the mill")
        self.ser_mill.close()
        time.sleep(15)
        logger.info("Mill connected: %s", self.ser_mill.isOpen())
        print("Mill connected: ", self.ser_mill.isOpen())

    def read_json_config(self):
        """Read the config file"""
        try:
            config_file_path = MILL_CONFIG
            with open(config_file_path, "r", encoding="UTF-8") as file:
                configuration = json.load(file)
            logger.debug("Mill config loaded: %s", configuration)
            return configuration
        except FileNotFoundError as err:
            logger.error("Config file not found")
            raise MillConfigNotFound("Config file not found") from err
        except Exception as err:
            logger.error("Error reading config file: %s", str(err))
            raise MillConfigError("Error reading config file") from err

    def execute_command(self, command):
        """Encodes and sends commands to the mill and returns the response"""
        try:
            logger.debug("Command sent: %s", command)

            command_bytes = str(command).encode()
            self.ser_mill.write(command_bytes + b"\n")
            time.sleep(2)
            mill_response = self.ser_mill.readline().decode().rstrip()

            if command == "F2000":
                logger.debug("Returned %s", mill_response)

            elif command == "?":
                logger.debug("eturned %s", mill_response)

            elif command not in ["$H", "$X", "(ctrl-x)", "$C", "$#", "$G"]:
                logger.debug("Initially %s", mill_response)
                self.wait_for_completion(mill_response)
                mill_response = self.current_status()
                logger.debug("Returned %s", mill_response)
            else:
                logger.debug("Returned %s", mill_response)

            if mill_response.lower() in ["error", "alarm"]:
                if "error:22" in mill_response.lower():
                    # This is a GRBL error that occurs when the feed rate isn't set before moving with G01 command
                    logger.error("Error in status: %s", mill_response)
                    # Try setting the feed rate and executing the command again
                    self.set_feed_rate(2000)
                    mill_response = self.execute_command(command)
                else:
                    logger.error("current_status: Error in status: %s", mill_response)
                    raise StatusReturnError(f"Error in status: {mill_response}")

        except Exception as exep:
            logger.error("Error executing command %s: %s", command, str(exep))
            raise CommandExecutionError(
                f"Error executing command {command}: {str(exep)}"
            ) from exep

        return mill_response

    def stop(self):
        """Stop the mill"""
        self.execute_command("$X")

    def reset(self):
        """Reset the mill"""
        self.execute_command("(ctrl-x)")

    def home(self, timeout=90):
        """Home the mill with a timeout"""
        self.execute_command("$H")
        time.sleep(15)
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                logger.warning("Homing timed out")
                break

            status = self.current_status()
            if "Idle" in status:
                logger.info("Homing completed")
                break

            time.sleep(2)  # Adjust the sleep interval as needed

    def wait_for_completion(self, incoming_status, timeout=90):
        """Wait for the mill to complete the previous command"""
        status = incoming_status
        start_time = time.time()
        while "Idle" not in status:
            if time.time() - start_time > timeout:
                logger.warning("wait_for_completion: Command execution timed out")
                break
            status = self.current_status()
            time.sleep(1)

    def current_status(self) -> str:
        """Get the current status of the mill"""
        command = "?"
        command_bytes = command.encode()
        status = ""
        while status == "":
            self.ser_mill.write(command_bytes + b"\n")
            # time.sleep(2)
            status = self.ser_mill.readline().decode().rstrip()
        # Check for errors
        if "error" in status.lower() or "alarm" in status.lower():
            logger.error("current_status: Error in status: %s", status)
            raise StatusReturnError(f"Error in status: {status}")
        # Check for busy
        while status == "ok":
            status = self.ser_mill.readline().decode().rstrip()
        return status

    def set_feed_rate(self, rate):
        """Set the feed rate"""
        self.execute_command(f"F{rate}")

    def clear_buffers(self):
        """Clear input and output buffers"""
        self.ser_mill.flushInput()  # Clear input buffer
        self.ser_mill.flushOutput()  # Clear output buffer

    def gcode_mode(self):
        """Ask the mill for its gcode mode"""
        self.execute_command("$C")

    def gcode_parameters(self):
        """Ask the mill for its gcode parameters"""
        return self.execute_command("$#")

    def gcode_parser_state(self):
        """Ask the mill for its gcode parser state"""
        return self.execute_command("$G")

    def move_center_to_position(self, x_coord, y_coord, z_coord) -> int:
        """
        Move the mill to the specified coordinates.
        Args:
            x_coord (float): X coordinate.
            y_coord (float): Y coordinate.
            z_coord (float): Z coordinate.
        Returns:
            str: Response from the mill after executing the command.
        """
        offsets = self.config["instrument_offsets"]["center"]
        working_volume = self.config["working_volume"]

        mill_move = "G01 X{} Y{} Z{}"  # Move to specified coordinates

        command_coordinates = [
            x_coord + offsets["x"],
            y_coord + offsets["y"],
            z_coord + offsets["z"],
        ]

        # check that command coordinates are within working volume
        if command_coordinates[0] > 0 or command_coordinates[0] < working_volume["x"]:
            logger.error("x coordinate out of range")
            raise ValueError("x coordinate out of range")
        if command_coordinates[1] > 0 or command_coordinates[1] < working_volume["y"]:
            logger.error("y coordinate out of range")
            raise ValueError("y coordinate out of range")
        if command_coordinates[2] > 0 or command_coordinates[2] < working_volume["z"]:
            logger.error("z coordinate out of range")
            raise ValueError("z coordinate out of range")

        command = mill_move.format(*command_coordinates)
        self.execute_command(command)
        return 0

    def current_coordinates(self, instrument=Instruments.CENTER) -> list:
        """
        Get the current coordinates of the mill.
        Args:
            None
        Returns:
            list: [x,y,z]
        """

        status = self.current_status()
        # Regular expression to extract MPos coordinates
        pattern = re.compile(r"MPos:([\d.-]+),([\d.-]+),([\d.-]+)")

        match = pattern.search(status)  # Decoding the bytes to string
        max_attempts = 3
        for _ in range(max_attempts):
            try:
                if match:
                    x_coord = float(match.group(1)) + 3
                    y_coord = float(match.group(2)) + 3
                    z_coord = float(match.group(3)) + 3
                    log_message = (
                        f"MPos coordinates: X = {x_coord}, Y = {y_coord}, Z = {z_coord}"
                    )
                    logger.info(log_message)
                    break
                else:
                    logger.warning(
                        "MPos coordinates not found in the line. Trying again..."
                    )
                    raise LocationNotFound
            except LocationNotFound as e:
                logger.error(
                    "Error occurred while getting MPos coordinates: %s", str(e)
                )
                if _ == max_attempts - 1:
                    raise

        if instrument in [Instruments.CENTER, Instruments.LENS]:
            current_coordinates = [x_coord, y_coord, z_coord]
        elif instrument == Instruments.PIPETTE:
            offsets = self.config["instrument_offsets"]["pipette"]
            current_coordinates = [
                x_coord - offsets["x"],
                y_coord - offsets["y"],
                z_coord - offsets["z"],
            ]
        elif instrument == Instruments.ELECTRODE:
            offsets = self.config["instrument_offsets"]["electrode"]
            current_coordinates = [
                x_coord - offsets["x"],
                y_coord - offsets["y"],
                z_coord - offsets["z"],
            ]

        else:
            raise ValueError("Invalid instrument")

        logger.debug("current_coordinates: %s", current_coordinates)
        return current_coordinates

    def rinse_electrode(self, rinses: int = 3):
        """
        Rinse the electrode by moving it to the rinse position and back to the
        center position.
        Args:
            None
        Returns:
            None
        """
        coords = self.config["electrode_bath"]
        self.safe_move(coords["x"], coords["y"], 0, instrument=Instruments.ELECTRODE)
        for _ in range(rinses):
            self.move_electrode_to_position(coords["x"], coords["y"], coords["z"])
            self.move_electrode_to_position(coords["x"], coords["y"], 0)
        return 0

    def rest_electrode(self):
        """
        Rinse the electrode by moving it to the rinse position and back to the
        center position.
        Args:
            None
        Returns:
            None
        """
        coords = self.config["electrode_bath"]
        self.move_to_safe_position()
        self.safe_move(
            coords["x"], coords["y"], coords["z"], instrument=Instruments.ELECTRODE
        )
        return 0

    def move_to_safe_position(self) -> str:
        """Move the mill to its current x,y location and z = 0"""
        # [initial_x, initial_y, initial_z] = self.current_coordinates()
        # mill_response = self.move_center_to_position(
        #     initial_x, initial_y, 0
        # )

        mill_response = self.execute_command("G01 Z0")
        return mill_response

    def move_pipette_to_position(
        self,
        x_coord: float = 0,
        y_coord: float = 0,
        z_coord=0.00,
    ) -> int:
        """
        Move the pipette to the specified coordinates.
        Args:
            x (float): X coordinate.
            y (float): Y coordinate.
            z (float): Z coordinate.
        Returns:
            str: Response from the mill after executing the command.
        """
        # offsets = {"x": -88, "y": 0, "z": 0}
        offsets = self.config["instrument_offsets"]["pipette"]
        # mill_move = "G01 X{} Y{} Z{}"  # move to specified coordinates
        # command = mill_move.format(
        #     x_coord + offsets["x"], y_coord +
        #     offsets["y"], z_coord + offsets["z"]
        # )
        # self.execute_command(str(command))
        command_coordinates = [
            x_coord + offsets["x"],
            y_coord + offsets["y"],
            z_coord + offsets["z"],
        ]
        self.move_center_to_position(*command_coordinates)
        return 0

    def move_electrode_to_position(
        self, x_coord: float, y_coord: float, z_coord: float = 0.00
    ) -> int:
        """
        Move the electrode to the specified coordinates.
        Args:
            coordinates (dict): Dictionary containing x, y, and z coordinates.
        Returns:
            str: Response from the mill after executing the command.
        """
        # offsets = {"x": 36, "y": 30, "z": 0}
        offsets = self.config["instrument_offsets"]["electrode"]
        # move to specified coordinates
        # mill_move = "G01 X{} Y{} Z{}"
        # command = mill_move.format(
        #     (x_coord + offsets["x"]), (y_coord +
        #                                offsets["y"]), (z_coord + offsets["z"])
        # )
        # self.execute_command(str(command))

        command_coordinates = [
            x_coord + offsets["x"],
            y_coord + offsets["y"],
            z_coord + offsets["z"],
        ]
        self.move_center_to_position(*command_coordinates)
        return 0

    def update_offset(self, offset_type, offset_x, offset_y, offset_z):
        """
        Update the offset in the config file
        """
        current_offset = self.config[offset_type]
        offset = {
            "x": current_offset["x"] + offset_x,
            "y": current_offset["y"] + offset_y,
            "z": current_offset["z"] + offset_z,
        }

        self.config["instrument_offsets"][offset_type] = offset
        config_file_path = MILL_CONFIG
        if not config_file_path.exists():
            logger.error("Config file not found")
            raise MillConfigNotFound

        try:
            with open(config_file_path, "w", encoding="UTF-8") as file:
                json.dump(self.config, file, indent=4)
            logger_message = f"Updated {offset_type} to {offset}"
            logger.info(logger_message)
            return 0
        except MillConfigNotFound as update_offset_exception:
            logger.error(update_offset_exception)
            return 3

    ## Special versions of the movement commands that avoid diagonal movements
    def safe_move(
        self,
        x_coord,
        y_coord,
        z_coord,
        instrument: Instruments = Instruments.CENTER,
        fixed_z=False,
    ) -> int:
        """
        Move the mill to the specified coordinates using only horizontal and vertical movements.
        Args:
            x_coord (float): X coordinate.
            y_coord (float): Y coordinate.
            z_coord (float): Z coordinate.
        Returns:
            str: Response from the mill after executing the commands.
        """
        # Get the current coordinates
        current_x, current_y, current_z = self.current_coordinates()
        logger.debug("Current coordinates: %s, %s, %s", current_x, current_y, current_z)
        logger.debug("Target coordinates: %s, %s, %s", x_coord, y_coord, z_coord)

        if current_z != 0 and current_z != z_coord and (not fixed_z or fixed_z):
            # This condition is true if:
            #  - the current Z coordinate is not zero
            #  - it is not equal to the target Z coordinate
            #  - the fixed_z flag is not set (i.e. fixed_z = False) or it is set (i.e. fixed_z = True)
            # Additionally, current_z should be below the safe height.
            if current_z < self.config["safe_height_floor"]:
                logger.debug("Testing - Would be moving to Z = 0")
                logger.debug(
                    "Reason:\n\tcurrent_z is below self.config['safe_height_floor'] %s",
                    current_z < self.config['safe_height_floor']
                )
                # self.execute_command("G01 Z0")
            else:
                logger.debug("Testing - Would not be moving to Z = 0")
                logger.debug(
                    "Reason:\n\tcurrent_z is at or above self.config['safe_height_floor'] %s",
                    current_z >= self.config['safe_height_floor']
                )  
        else:
            logger.debug("Testing - Would not be moving to Z = 0")
            if current_z == 0:
                logger.debug("Reason:\n\tcurrent_z is zero")
            elif current_z == z_coord:
                logger.debug("Reason:\n\tcurrent_z is equal to the target Z coordinate %s", current_z == z_coord)
            elif fixed_z:
                logger.debug("Reason:\n\tfixed_z is set to True")
            else:
                logger.debug("Reason:\n\tMultiple Conditions not met: current_z = %s, z_coord = %s, fixed_z = %s", current_z, z_coord, fixed_z) 


        if current_z != 0:
            self.execute_command("G01 Z0")

        # Fetch offsets for the specified instrument
        offsets = self.config["instrument_offsets"][instrument.value]
        # updated target coordinates with offsets so the center of the mill moves to the right spot
        x_coord = x_coord + offsets["x"]
        y_coord = y_coord + offsets["y"]
        z_coord = z_coord + offsets["z"]

        # Double check that the target coordinates are within the working volume
        working_volume = self.config["working_volume"]
        if x_coord > 0 or x_coord < working_volume["x"]:
            logger.error("x coordinate out of range")
            raise ValueError("x coordinate out of range")
        if y_coord > 0 or y_coord < working_volume["y"]:
            logger.error("y coordinate out of range")
            raise ValueError("y coordinate out of range")
        if z_coord > 0 or z_coord < working_volume["z"]:
            logger.error("z coordinate out of range")
            raise ValueError("z coordinate out of range")

        # Calculate the differences between the current and target coordinates
        dx = x_coord - current_x
        dy = y_coord - current_y
        # Initialize a list to store the movement commands
        commands = []

        # Generate horizontal movements
        if dx != 0:
            commands.append(f"G01 X{x_coord}")

        if dy != 0:
            commands.append(f"G01 Y{y_coord}")

        # Generate vertical movements
        commands.append(f"G01 Z{z_coord}")

        # Execute the commands one by one
        for command in commands:
            self.execute_command(command)

        return 0


class StatusReturnError(Exception):
    """Raised when the mill returns an error in the status"""


class MillConfigNotFound(Exception):
    """Raised when the mill config file is not found"""


class MillConfigError(Exception):
    """Raised when there is an error reading the mill config file"""


class MillConnectionError(Exception):
    """Raised when there is an error connecting to the mill"""


class CommandExecutionError(Exception):
    """Raised when there is an error executing a command"""


class LocationNotFound(Exception):
    """Raised when the mill cannot find its location"""


class MockMill:
    """A class that simulates a mill for testing purposes.

    Attributes:
    config_file (str): The path to the configuration file.
    config (dict): The configuration dictionary.
    ser_mill (None): The serial connection to the mill.
    current_x (float): The current x-coordinate.
    current_y (float): The current y-coordinate.
    current_z (float): The current z-coordinate.

    Methods:
    homing_sequence(): Simulate homing, setting feed rate, and clearing buffers.
    disconnect(): Simulate disconnecting from the mill.
    execute_command(command): Simulate executing a command.
    stop(): Simulate stopping the mill.
    reset(): Simulate resetting the mill.
    home(timeout): Simulate homing the mill.
    wait_for_completion(incoming_status, timeout): Simulate waiting for completion.
    current_status(): Simulate getting the current status.
    set_feed_rate(rate): Simulate setting the feed rate.
    clear_buffers(): Simulate clearing buffers.
    gcode_mode(): Simulate getting the G-code mode.
    gcode_parameters(): Simulate getting G-code parameters.
    gcode_parser_state(): Simulate getting G-code parser state.
    rinse_electrode(): Simulate rinsing the electrode.
    move_to_safe_position(): Simulate moving to a safe position.
    move_center_to_position(x_coord, y_coord, z_coord): Simulate moving to a specified position.
    current_coordinates(instrument): Return the tracked current coordinates.
    move_pipette_to_position(x_coord, y_coord, z_coord): Simulate moving the pipette to a specified position.
    move_electrode_to_position(x_coord, y_coord, z_coord): Simulate moving the electrode to a specified position.
    update_offset(offset_type, offset_x, offset_y, offset_z): Simulate updating offsets in the config.
    safe_move(x_coord, y_coord, z_coord, instrument): Simulate a safe move with horizontal and vertical movements.
    """

    def __init__(self, config_file="mill_config.json"):
        self.config_file = config_file
        self.config = {}  # Initialize an empty config for testing
        self.ser_mill = None  # No serial connection in mock
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        self.logger = logger

    def homing_sequence(self):
        """Simulate homing, setting feed rate, and clearing buffers"""
        self.home()
        self.set_feed_rate(2000)  # Set feed rate to 2000
        self.clear_buffers()

    def __enter__(self):
        """Enter the context manager"""
        self.homing_sequence()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager"""
        self.home()
        self.disconnect()

    def disconnect(self):
        """Simulate disconnecting from the mill"""
        self.logger.info("Disconnecting from the mill")

    def execute_command(self, command):
        """Simulate executing a command"""
        self.logger.info("Executing command: %s", command)

    def stop(self):
        """Simulate stopping the mill"""
        self.logger.info("Stopping the mill")

    def reset(self):
        """Simulate resetting the mill"""
        self.logger.info("Resetting the mill")

    def home(self, timeout=90):
        """Simulate homing the mill"""
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        self.logger.debug("timeout for homing is %s", str(timeout))
        self.logger.info("Homing the mill")

    def wait_for_completion(self, incoming_status, timeout=90):
        """Simulate waiting for completion"""
        self.logger.info("Waiting for completion with status: %s", incoming_status)
        self.logger.debug("timeout for waiting is %s", str(timeout))

    def current_status(self) -> str:
        """Simulate getting the current status"""
        self.logger.info("Getting current status")
        return "Idle"  # Mock status for testing

    def set_feed_rate(self, rate):
        """Simulate setting the feed rate"""
        self.logger.info("Setting feed rate to %s", rate)

    def clear_buffers(self):
        """Simulate clearing buffers"""
        self.logger.info("Clearing buffers")

    def gcode_mode(self):
        """Simulate getting the G-code mode"""
        self.logger.info("Getting G-code mode")

    def gcode_parameters(self):
        """Simulate getting G-code parameters"""
        self.logger.info("Getting G-code parameters")

    def gcode_parser_state(self):
        """Simulate getting G-code parser state"""
        self.logger.info("Getting G-code parser state")

    def rinse_electrode(self, rinses: int = 3):
        """Simulate rinsing the electrode"""
        self.logger.info("Rinsing the electrode")
        for _ in range(rinses):
            time.sleep(1)

    def rest_electrode(self):
        """
        Rinse the electrode by moving it to the rinse position and back to the
        center position.
        Args:
            None
        Returns:
            None
        """

    def move_to_safe_position(self):
        """Simulate moving to a safe position"""
        self.logger.info("Moving to a safe position")

    def move_center_to_position(self, x_coord, y_coord, z_coord) -> int:
        """Simulate moving to a specified position"""
        self.current_x = x_coord
        self.current_y = y_coord
        self.current_z = z_coord
        self.logger.info("Moving to position: (%s, %s, %s)", x_coord, y_coord, z_coord)
        return 0

    def current_coordinates(self, instrument=Instruments.CENTER) -> list:
        """Return the tracked current coordinates"""
        self.logger.info("Getting current coordinates of %s", instrument.value)
        return [self.current_x, self.current_y, self.current_z]

    def move_pipette_to_position(
        self,
        x_coord: float = 0,
        y_coord: float = 0,
        z_coord=0.00,
    ):
        """Simulate moving the pipette to a specified position"""
        self.current_x = x_coord
        self.current_y = y_coord
        self.current_z = z_coord
        self.logger.info(
            "Moving pipette to position: (%s, %s, %s)", x_coord, y_coord, z_coord
        )

    def move_electrode_to_position(
        self, x_coord: float, y_coord: float, z_coord: float = 0.00
    ):
        """Simulate moving the electrode to a specified position"""
        self.current_x = x_coord
        self.current_y = y_coord
        self.current_z = z_coord
        self.logger.info(
            "Moving electrode to position: (%s, %s, %s)", x_coord, y_coord, z_coord
        )

    def update_offset(self, offset_type, offset_x, offset_y, offset_z):
        """Simulate updating offsets in the config"""
        self.logger.info(
            "Updating offset: %s (%s, %s, %s)",
            offset_type,
            offset_x,
            offset_y,
            offset_z,
        )

    def safe_move(
        self, x_coord, y_coord, z_coord, instrument: Instruments = Instruments.CENTER
    ) -> int:
        """Simulate a safe move with horizontal and vertical movements"""
        self.current_x = x_coord
        self.current_y = y_coord
        self.current_z = z_coord
        self.logger.info(
            "Safe move %s to position: (%s, %s, %s)",
            instrument.value,
            x_coord,
            y_coord,
            z_coord,
        )
        return 0


def wellplate_scan(mill_arg: Mill = None, capture_images=False):
    """Scan the wellplate"""
    # Perform image scan of each well of the wellplate
    from camera_call_camera import capture_new_image
    from wellplate import Well, Wellplate

    wellplate = Wellplate()
    if mill_arg is None:
        mill = Mill()
    else:
        mill = mill_arg
    with mill:
        for well in wellplate.wells.values():
            well: Well = well
            print("Currently imaging: {well.name}", end="\r")
            well_coordinates = well.coordinates
            mill.safe_move(
                well_coordinates["x"],
                well_coordinates["y"],
                wellplate.image_height,
                instrument=Instruments.LENS,
                fixed_z=True,
            )
            if capture_images:
                # create a folder in data folder with the wellplate id
                folder = Path(f"{PATH_TO_DATA}/{wellplate.plate_id}")
                folder.mkdir(parents=True, exist_ok=True)

                # capture each image with file name as the date and the well name
                file_name = f"{datetime.now().strftime('%Y-%m-%d')}-{well.name}.png"
                capture_new_image(file_name=folder / file_name)
        if mill_arg is None:
            mill.rest_electrode()


def move_pipette_to_each_corner(mill: Mill, a1, a12, h12, h1, z_top):
    mill.safe_move(a1["x"], a1["y"], z_top, instrument=Instruments.PIPETTE)
    mill.safe_move(a12["x"], a12["y"], z_top, instrument=Instruments.PIPETTE)
    mill.safe_move(h12["x"], h12["y"], z_top, instrument=Instruments.PIPETTE)
    mill.safe_move(h1["x"], h1["y"], z_top, instrument=Instruments.PIPETTE)


def move_electrode_to_each_corner(mill: Mill, a1, a12, h12, h1, z_top, echem_height):
    mill.safe_move(a1["x"], a1["y"], z_top, instrument=Instruments.ELECTRODE)
    mill.safe_move(a12["x"], a12["y"], z_top, instrument=Instruments.ELECTRODE)
    mill.safe_move(h12["x"], h12["y"], z_top, instrument=Instruments.ELECTRODE)
    mill.safe_move(h1["x"], h1["y"], z_top, instrument=Instruments.ELECTRODE)

    repsonse = input("Move the electrode to the echem height? y/n: ")
    if repsonse.lower() == "y":
        mill.safe_move(a1["x"], a1["y"], echem_height, instrument=Instruments.ELECTRODE)
        mill.safe_move(
            a12["x"], a12["y"], echem_height, instrument=Instruments.ELECTRODE
        )
        mill.safe_move(
            h12["x"], h12["y"], echem_height, instrument=Instruments.ELECTRODE
        )
        mill.safe_move(h1["x"], h1["y"], echem_height, instrument=Instruments.ELECTRODE)


def move_lens_to_each_corner(mill: Mill, image_height, a1, a12, h12, h1):
    mill.safe_move(a1["x"], a1["y"], image_height, instrument=Instruments.LENS)
    mill.safe_move(a12["x"], a12["y"], image_height, instrument=Instruments.LENS)
    mill.safe_move(h12["x"], h12["y"], image_height, instrument=Instruments.LENS)
    mill.safe_move(h1["x"], h1["y"], image_height, instrument=Instruments.LENS)


def move_to_vials(mill: Mill, stock_vials, waste_vials):
    from vials import StockVial, WasteVial

    if len(stock_vials) != 0:
        for _, stock_vial in enumerate(stock_vials):
            stock_vial: StockVial
            if stock_vial.position == "e1":
                continue
            mill.safe_move(
                stock_vial.coordinates["x"],
                stock_vial.coordinates["y"],
                stock_vial.height,
                instrument=Instruments.PIPETTE,
            )
        mill.move_to_safe_position()

    if len(waste_vials) != 0:
        for _, waste_vial in enumerate(waste_vials):
            waste_vial: WasteVial
            mill.safe_move(
                waste_vial.coordinates["x"],
                waste_vial.coordinates["y"],
                waste_vial.height,
                instrument=Instruments.PIPETTE,
            )
        mill.move_to_safe_position()


def movement_test():
    """Test the mill movement with a wellplate"""
    import wellplate as Wells
    from vials import StockVial, WasteVial, read_vials

    wellplate = Wells.Wellplate()

    # Configure the logger for testing
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel(logging.DEBUG)  # Change to INFO to reduce verbosity
    formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
    testing_handler = logging.FileHandler(PATH_TO_LOGS / "mill_control_testing.log")
    testing_handler.setFormatter(formatter)
    test_logger.addHandler(testing_handler)

    try:
        with Mill() as mill:
            a1 = wellplate.get_coordinates("A1")
            a2 = wellplate.get_coordinates("A2")
            a3 = wellplate.get_coordinates("A3")
            a4 = wellplate.get_coordinates("A4")
            a5 = wellplate.get_coordinates("A5")
            a6 = wellplate.get_coordinates("A6")
            a7 = wellplate.get_coordinates("A7")
            a8 = wellplate.get_coordinates("A8")
            a9 = wellplate.get_coordinates("A9")
            a10 = wellplate.get_coordinates("A10")
            a11 = wellplate.get_coordinates("A11")
            a12 = wellplate.get_coordinates("A12")
            b1 = wellplate.get_coordinates("B1")
            b2 = wellplate.get_coordinates("B2")
            b3 = wellplate.get_coordinates("B3")
            b4 = wellplate.get_coordinates("B4")
            b5 = wellplate.get_coordinates("B5")
            b6 = wellplate.get_coordinates("B6")
            b7 = wellplate.get_coordinates("B7")
            b8 = wellplate.get_coordinates("B8")
            b9 = wellplate.get_coordinates("B9")
            b10 = wellplate.get_coordinates("B10")
            b11 = wellplate.get_coordinates("B11")
            b12 = wellplate.get_coordinates("B12")
            c1 = wellplate.get_coordinates("C1")
            c2 = wellplate.get_coordinates("C2")
            c3 = wellplate.get_coordinates("C3")
            c4 = wellplate.get_coordinates("C4")
            c5 = wellplate.get_coordinates("C5")
            c6 = wellplate.get_coordinates("C6")
            c7 = wellplate.get_coordinates("C7")
            c8 = wellplate.get_coordinates("C8")
            c9 = wellplate.get_coordinates("C9")
            c10 = wellplate.get_coordinates("C10")
            c11 = wellplate.get_coordinates("C11")
            c12 = wellplate.get_coordinates("C12")
            d1 = wellplate.get_coordinates("D1")
            d2 = wellplate.get_coordinates("D2")
            d3 = wellplate.get_coordinates("D3")
            d4 = wellplate.get_coordinates("D4")
            d5 = wellplate.get_coordinates("D5")
            d6 = wellplate.get_coordinates("D6")
            d7 = wellplate.get_coordinates("D7")
            d8 = wellplate.get_coordinates("D8")
            d9 = wellplate.get_coordinates("D9")
            d10 = wellplate.get_coordinates("D10")
            d11 = wellplate.get_coordinates("D11")
            d12 = wellplate.get_coordinates("D12")
            e1 = wellplate.get_coordinates("E1")
            e2 = wellplate.get_coordinates("E2")
            e3 = wellplate.get_coordinates("E3")
            e4 = wellplate.get_coordinates("E4")
            e5 = wellplate.get_coordinates("E5")
            e6 = wellplate.get_coordinates("E6")
            e7 = wellplate.get_coordinates("E7")
            e8 = wellplate.get_coordinates("E8")
            e9 = wellplate.get_coordinates("E9")
            e10 = wellplate.get_coordinates("E10")
            e11 = wellplate.get_coordinates("E11")
            e12 = wellplate.get_coordinates("E12")
            f1 = wellplate.get_coordinates("F1")
            f2 = wellplate.get_coordinates("F2")
            f3 = wellplate.get_coordinates("F3")
            f4 = wellplate.get_coordinates("F4")
            f5 = wellplate.get_coordinates("F5")
            f6 = wellplate.get_coordinates("F6")
            f7 = wellplate.get_coordinates("F7")
            f8 = wellplate.get_coordinates("F8")
            f9 = wellplate.get_coordinates("F9")
            f10 = wellplate.get_coordinates("F10")
            f11 = wellplate.get_coordinates("F11")
            f12 = wellplate.get_coordinates("F12")
            g1 = wellplate.get_coordinates("G1")
            g2 = wellplate.get_coordinates("G2")
            g3 = wellplate.get_coordinates("G3")
            g4 = wellplate.get_coordinates("G4")
            g5 = wellplate.get_coordinates("G5")
            g6 = wellplate.get_coordinates("G6")
            g7 = wellplate.get_coordinates("G7")
            g8 = wellplate.get_coordinates("G8")
            g9 = wellplate.get_coordinates("G9")
            g10 = wellplate.get_coordinates("G10")
            g11 = wellplate.get_coordinates("G11")
            g12 = wellplate.get_coordinates("G12")
            
            
            ## Load the vials

            stock_vials: StockVial = read_vials(STOCK_STATUS)
            waste_vials: WasteVial = read_vials(WASTE_STATUS)
            input(
                "Begin the movement test to each corner of the wellplate. Press enter to continue..."
            )

            mill.move_to_safe_position()
            mill.rest_electrode()

    except (
        MillConnectionError,
        MillConfigNotFound,
        MillConfigError,
        CommandExecutionError,
        StatusReturnError,
        LocationNotFound,
    ) as error:
        logger.error("Error occurred: %s", error)
        # Handle the error gracefully, e.g., print a message or perform cleanup

    finally:
        logger.info("Exiting program.")


if __name__ == "__main__":
    movement_test()
