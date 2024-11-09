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
import json
import re
import time
from pathlib import Path

# third-party libraries
# from pydantic.dataclasses import dataclass

import serial

# local libraries
from .logger import set_up_mill_logger
from .exceptions import (
    CommandExecutionError,
    LocationNotFound,
    MillConfigError,
    MillConfigNotFound,
    MillConnectionError,
    StatusReturnError,
    CNCMillException,
)
from .status_codes import AlarmStatus, ErrorCodes
from .instruments import Instruments

current_directory = Path(__file__).parent

# Set up the logger
logger = set_up_mill_logger(current_directory / "logs")


class Mill:
    """
    Set up the mill connection and pass commands, including special commands
    """

    def __init__(self):
        self.mill_config_file = "_configuration.json"
        self.active_connection = False
        self.mill_config = self.read_mill_config()
        self.ser_mill: serial.Serial = self.connect_to_mill()

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

            if not ser_mill.is_open:
                logger.info("Opening serial connection to mill...")
                ser_mill.open()
                time.sleep(2)
                if ser_mill.is_open:
                    logger.info("Serial connection to mill opened successfully")
                    self.active_connection = True
                else:
                    logger.error("Serial connection to mill failed to open")
                    raise MillConnectionError("Error opening serial connection to mill")

            logger.info("Mill connected: %s", ser_mill.is_open)
            print("Mill connected: ", ser_mill.is_open)
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
        time.sleep(15)  # Wait for the connection to close
        logger.info("Mill connected: %s", self.ser_mill.is_open)
        print("Mill connected: ", self.ser_mill.is_open)

    def read_json_config(self, config_file):
        """Read the config file"""
        try:
            config_file_path = current_directory / config_file
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

    def read_mill_config(self):
        """Read the mill config file"""
        return self.read_json_config(self.mill_config_file)

    def execute_command(self, command):
        """Encodes and sends commands to the mill and returns the response"""
        try:
            logger.debug("Command sent: %s", command)

            command_bytes = str(command).encode()
            self.ser_mill.write(command_bytes + b"\n")
            time.sleep(2)
            mill_response = self.ser_mill.readline().decode().rstrip()

            if command not in ["$H", "$X", "(ctrl-x)", "$C", "$#", "$G", "F2000", "?"]:
                logger.debug("Initially %s", mill_response)
                self.wait_for_completion(mill_response)
                mill_response = self.current_status()
                logger.debug("Returned %s", mill_response)
            else:
                logger.debug("Returned %s", mill_response)

            if mill_response.lower() in ["error", "alarm"]:
                # Parse the response for errors or alarms and match to the corresponding error or alarm codes
                # translate the error in the form of error:## to error## and alarm:## to alarm##
                error_code = re.search(r"error:?\d+", mill_response, re.IGNORECASE)
                alarm_code = re.search(r"alarm:?\d+", mill_response, re.IGNORECASE)

                if error_code:
                    error_code = error_code.group().lower().replace("error", "error")
                    if error_code in ErrorCodes.__members__:
                        logger.error("%s: %s", error_code, ErrorCodes[error_code].value)
                        if error_code == "error22":
                            # This is a GRBL error that occurs when the feed rate isn't set before moving with G01 command
                            logger.error(
                                "%s: %s", error_code, ErrorCodes[error_code].value
                            )
                            # Try setting the feed rate and executing the command again
                            self.set_feed_rate(2000)
                            mill_response = self.execute_command(command)
                        else:
                            raise StatusReturnError(f"Error in status: {mill_response}")
                    else:
                        logger.error("Unknown Error in Status: %s", mill_response)
                        raise StatusReturnError(
                            f"Unknown Error in Status: {mill_response}"
                        )

                if alarm_code:
                    alarm_code = alarm_code.group().lower().replace("alarm", "alarm")
                    if alarm_code in AlarmStatus.__members__:
                        logger.error(
                            "%s: %s", alarm_code, AlarmStatus[alarm_code].value
                        )
                        raise StatusReturnError(f"Alarm in status: {mill_response}")
                    else:
                        logger.error("Alarm in status: %s", mill_response)
                        raise StatusReturnError(
                            f"Unkown Alarm in status: {mill_response}"
                        )
                else:
                    logger.error("current_status: Error in status: %s", mill_response)
                    raise StatusReturnError(f"Error in status: {mill_response}")

        except CNCMillException as exep:
            logger.error("Error executing command %s: %s", command, str(exep))
            raise CommandExecutionError(
                f"Error executing command {command}: {str(exep)}"
            ) from exep

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
        self.execute_command("$X")

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
        offsets = self.mill_config["instrument_offsets"]["center"]
        working_volume = self.mill_config["working_volume"]

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
            offsets = self.mill_config["instrument_offsets"]["pipette"]
            current_coordinates = [
                x_coord - offsets["x"],
                y_coord - offsets["y"],
                z_coord - offsets["z"],
            ]
        elif instrument == Instruments.ELECTRODE:
            offsets = self.mill_config["instrument_offsets"]["electrode"]
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
        coords = self.mill_config["electrode_bath"]
        self.safe_move(coords["x"], coords["y"], 0, instrument=Instruments.ELECTRODE)
        for _ in range(rinses):
            self.move_to_position(
                coords["x"], coords["y"], coords["z"], instrument=Instruments.ELECTRODE
            )
            self.move_to_position(
                coords["x"], coords["y"], 0, instrument=Instruments.ELECTRODE
            )
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
        coords = self.mill_config["electrode_bath"]
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

        return self.execute_command("G01 Z0")

    def move_to_position(
        self,
        x_coord: float,
        y_coord: float,
        z_coord: float = 0.00,
        instrument: Instruments = Instruments.CENTER,
    ) -> int:
        """
        Move the mill to the specified coordinates.
        Args:
            x_coord (float): X coordinate.
            y_coord (float): Y coordinate.
            z_coord (float): Z coordinate.
            instrument (Instruments): Instrument to move.
        Returns:
            str: Response from the mill after executing the command.
        """
        # Fetch offsets for the specified instrument
        try:
            offsets = self.mill_config["instrument_offsets"][instrument.value]
        except KeyError as e:
            logger.error("Instrument not found in config file")
            raise MillConfigError("Instrument not found in config file") from e
        # updated target coordinates with offsets so the center of the mill moves to the right spot
        x_coord = x_coord + offsets["x"]
        y_coord = y_coord + offsets["y"]
        z_coord = z_coord + offsets["z"]

        # Double check that the target coordinates are within the working volume
        working_volume = self.mill_config["working_volume"]
        if x_coord > 0 or x_coord < working_volume["x"]:
            logger.error("x coordinate out of range")
            raise ValueError("x coordinate out of range")
        if y_coord > 0 or y_coord < working_volume["y"]:
            logger.error("y coordinate out of range")
            raise ValueError("y coordinate out of range")
        if z_coord > 0 or z_coord < working_volume["z"]:
            logger.error("z coordinate out of range")
            raise ValueError("z coordinate out of range")

        mill_move = "G01 X{} Y{} Z{}"  # Format of the move command
        command_coordinates = [x_coord, y_coord, z_coord]

        command = mill_move.format(*command_coordinates)
        self.execute_command(command)
        return 0

    def update_offset(self, offset_type, offset_x, offset_y, offset_z):
        """
        Update the offset in the config file
        """
        current_offset = self.mill_config[offset_type]
        offset = {
            "x": current_offset["x"] + offset_x,
            "y": current_offset["y"] + offset_y,
            "z": current_offset["z"] + offset_z,
        }

        self.mill_config["instrument_offsets"][offset_type] = offset

        try:
            with open(self.mill_config_file, "w", encoding="UTF-8") as file:
                json.dump(self.mill_config, file, indent=4)
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
            if current_z < self.mill_config["safe_height_floor"]:
                logger.debug("Testing - Would be moving to Z = 0")
                logger.debug(
                    "Reason:\n\tcurrent_z is below self.mill_config['safe_height_floor'] %s",
                    current_z < self.mill_config["safe_height_floor"],
                )
                # self.execute_command("G01 Z0")
            else:
                logger.debug("Testing - Would not be moving to Z = 0")
                logger.debug(
                    "Reason:\n\tcurrent_z is at or above self.mill_config['safe_height_floor'] %s",
                    current_z >= self.mill_config["safe_height_floor"],
                )
        else:
            logger.debug("Testing - Would not be moving to Z = 0")
            if current_z == 0:
                logger.debug("Reason:\n\tcurrent_z is zero")
            elif current_z == z_coord:
                logger.debug(
                    "Reason:\n\tcurrent_z is equal to the target Z coordinate %s",
                    current_z == z_coord,
                )
            elif fixed_z:
                logger.debug("Reason:\n\tfixed_z is set to True")
            else:
                logger.debug(
                    "Reason:\n\tMultiple Conditions not met: current_z = %s, z_coord = %s, fixed_z = %s",
                    current_z,
                    z_coord,
                    fixed_z,
                )

        if current_z != 0:
            if current_x != x_coord and current_y != y_coord:
                self.execute_command(f"G01 X{x_coord}")
            else:
                logger.warning(
                    "Current Z coordinate is not zero, but current X and Y coordinates are equal to the target coordinates so moving to Z = 0 is not necessary"
                )
        else:
            # If the current Z coordinate is zero, move to the target coordinates
            logger.warning(
                "Current Z coordinate is zero, moving to the target coordinates without moving to Z = 0"
            )
        # Fetch offsets for the specified instrument
        offsets = self.mill_config["instrument_offsets"][instrument.value]
        # updated target coordinates with offsets so the center of the mill moves to the right spot
        x_coord = x_coord + offsets["x"]
        y_coord = y_coord + offsets["y"]
        z_coord = z_coord + offsets["z"]

        # Double check that the target coordinates are within the working volume
        working_volume = self.mill_config["working_volume"]
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
