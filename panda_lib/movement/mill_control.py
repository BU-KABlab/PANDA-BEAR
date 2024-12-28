"""
This module contains the MillControl class, which is used to control the a GRBL CNC machine.
The MillControl class is used by the actions module to move the pipette and electrode to the
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
import configparser
import logging
import re
import sys
import time
from typing import Union
from unittest.mock import MagicMock

# third-party libraries
# from pydantic.dataclasses import dataclass
import serial

from panda_lib.config.config_tools import read_config
from panda_lib.log_tools import setup_default_logger, timing_wrapper
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import MillConfig
from panda_lib.utilities import Coordinates, Instruments

# add the mill_control logger
mill_control_logger = setup_default_logger(
    log_name="mill_control", console_level=logging.WARNING
)

# Mill movement logger - just for the movement commands
mill_movement_logger = setup_default_logger(
    log_name="mill_movement", console_level=logging.WARNING
)

config = read_config()
MILL_COM_PORT = config.get("MILL", "port")
MILL_BAUD_RATE = config.getint("MILL", "baudrate")
MILL_TIMEOUT = config.getint("MILL", "timeout")

MILL_MOVE = (
    "G01 X{} Y{} Z{}"  # Move to specified coordinates at the specified feed rate
)
MILL_MOVE_Z = "G01 Z{}"  # Move to specified Z coordinate at the specified feed rate
RAPID_MILL_MOVE = (
    "G00 X{} Y{} Z{}"  # Move to specified coordinates at the maximum feed rate
)

# Compile regex patterns once
wpos_pattern = re.compile(r"WPos:([\d.-]+),([\d.-]+),([\d.-]+)")
mpos_pattern = re.compile(r"MPos:([\d.-]+),([\d.-]+),([\d.-]+)")


class Mill:
    """
    Set up the mill connection and pass commands, including special commands
    """

    def __init__(self):
        self.active_connection = False
        self.config = self.fetch_saved_config()
        self.ser_mill: serial.Serial = None
        self.homed = False

    @timing_wrapper
    def homing_sequence(self):
        """Home the mill, set the feed rate, and clear the buffers"""
        self.home()
        self.set_feed_rate(2000)
        self.clear_buffers()

    @timing_wrapper
    def connect_to_mill(self) -> serial.Serial:
        """Connect to the mill"""
        try:
            ser_mill = serial.Serial(
                port=config.get("MILL", "port"),
                baudrate=config.getint("MILL", "baudrate", fallback=115200),
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=config.getint("MILL", "timeout", fallback=10),
            )
            time.sleep(2)

            if not ser_mill.is_open:
                ser_mill.open()
                time.sleep(2)
            if ser_mill.is_open:
                self.active_connection = True
            else:
                mill_control_logger.error("Serial connection to mill failed to open")
                raise MillConnectionError("Error opening serial connection to mill")

            mill_control_logger.info("Mill connected: %s", ser_mill.is_open)
            self.ser_mill = ser_mill
        except configparser.Error as err:
            mill_control_logger.error("Error reading config file: %s", str(err))
            raise MillConfigError("Error reading config file") from err

        except serial.SerialException as exep:
            mill_control_logger.error("Error connecting to the mill: %s", str(exep))
            raise MillConnectionError("Error connecting to the mill") from exep

        except MillConnectionError as exep:
            mill_control_logger.error("Error connecting to the mill: %s", str(exep))
            raise MillConnectionError("Error connecting to the mill") from exep

        # Check if the mill is currently in alarm state
        # If it is, reset the mill
        status = self.ser_mill.readlines()
        mill_control_logger.debug("Status: %s", status)
        if not status:
            mill_control_logger.warning("Initial status reading from the mill is blank")
            mill_control_logger.warning("Querying the mill for status")

            status = self.current_status()
            mill_control_logger.debug("Status: %s", status)
            if not status:
                mill_control_logger.error("Failed to get status from the mill")
                raise MillConnectionError("Failed to get status from the mill")
        else:
            status = status[-1].decode().rstrip()
        if "alarm" in status.lower():
            mill_control_logger.warning("Mill is in alarm state")
            reset_alarm = input("Reset the mill? (y/n): ")
            if reset_alarm[0].lower() == "y":
                self.reset()
            else:
                mill_control_logger.error(
                    "Mill is in alarm state, user chose not to reset the mill"
                )
                raise MillConnectionError("Mill is in alarm state")
        if "error" in status.lower():
            mill_control_logger.error("Error in status: %s", status)
            raise MillConnectionError(f"Error in status: {status}")

        # We only check that the mill is indeed lock upon connection because we will home before any movement
        if "unlock" not in status.lower():
            mill_control_logger.error("Mill is not locked")
            proceed = input("Proceed? (y/n): ")
            if proceed[0].lower() == "n":
                raise MillConnectionError("Mill is not locked")
            else:
                mill_control_logger.warning("Proceeding despite mill not being locked")
                mill_control_logger.warning("Current status: %s", status)
                mill_control_logger.warning("Homing is reccomended before any movement")
                home_now = input("Home now? (y/n): ")
                if home_now.lower() == "y":
                    self.homing_sequence()
                else:
                    mill_control_logger.warning("User chose not to home the mill")

        self.clear_buffers()
        return self.ser_mill

    def __enter__(self):
        """Enter the context manager"""
        self.connect_to_mill()
        self.homing_sequence()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager"""
        self.disconnect()
        mill_control_logger.info("Exiting the mill context manager")

    @timing_wrapper
    def disconnect(self):
        """Close the serial connection to the mill"""
        mill_control_logger.info("Disconnecting from the mill")

        if self.homed:
            mill_control_logger.debug("Mill was homed, resting electrode")
            self.rest_electrode()

        self.ser_mill.close()
        time.sleep(2)
        mill_control_logger.info("Mill connected: %s", self.ser_mill.is_open)
        if self.ser_mill.is_open:
            mill_control_logger.error(
                "Failed to close the serial connection to the mill"
            )
            raise MillConnectionError("Error closing serial connection to mill")
        else:
            mill_control_logger.info("Serial connection to mill closed successfully")
            self.active_connection = False
            self.ser_mill = None
        return

    @timing_wrapper
    def fetch_saved_config(self) -> dict:
        """Read the config file"""

        with SessionLocal() as session:
            mill_config = (
                session.query(MillConfig).order_by(MillConfig.id.desc()).first()
            )
            if mill_config:
                return mill_config.config
            else:
                mill_control_logger.error(
                    "Config not found in db...attempting to fetch from mill"
                )

                try:
                    self.connect_to_mill()
                    current_config = self.grbl_settings()
                    self.disconnect()
                    self.save_config(current_config)
                    return current_config
                except Exception as e:
                    raise MillConfigNotFound("Config file not found") from e

    @timing_wrapper
    def save_config(self, mill_config: Union[None, dict] = None):
        """Save the config to the db"""
        if mill_config is None:
            mill_config = self.config
        with SessionLocal() as session:
            mill_config_record = MillConfig(config=mill_config)
            session.add(mill_config_record)
            session.commit()

        mill_control_logger.info("Config saved to db")

    def execute_command(self, command: str):
        """Encodes and sends commands to the mill and returns the response"""
        try:
            mill_control_logger.debug("Command sent: %s", command)
            mill_movement_logger.debug("%s", command)
            command_bytes = str(command).encode()
            self.ser_mill.write(command_bytes + b"\n")
            time.sleep(2)
            mill_response = self.ser_mill.readline().decode().rstrip()

            if command == "$$":
                full_mill_response = []
                full_mill_response.append(mill_response)
                while full_mill_response[-1] != "ok":
                    full_mill_response.append(
                        self.ser_mill.readline().decode().rstrip()
                    )
                full_mill_response = full_mill_response[:-1]
                mill_control_logger.debug("Returned %s", full_mill_response)

                # parse the settings into a dictionary
                settings_dict = {}
                for setting in full_mill_response:
                    setting: str
                    key, value = setting.split("=")
                    settings_dict[key] = value

                return settings_dict

            elif not command.startswith("$"):
                # logger.debug("Initially %s", mill_response)
                mill_response = self.__wait_for_completion(mill_response)
                mill_control_logger.debug("Returned %s", mill_response)
            else:
                mill_control_logger.debug("Returned %s", mill_response)

            if re.search(r"\b(error|alarm)\b", mill_response.lower()):
                if re.search(r"\berror:22\b", mill_response.lower()):
                    # This is a GRBL error that occurs when the feed rate isn't set before moving with G01 command
                    mill_control_logger.error("Error in status: %s", mill_response)
                    # Try setting the feed rate and executing the command again
                    self.set_feed_rate(2000)
                    mill_response = self.execute_command(command)
                else:
                    mill_control_logger.error(
                        "current_status: Error in status: %s", mill_response
                    )
                    raise StatusReturnError(f"Error in status: {mill_response}")

        except Exception as exep:
            mill_control_logger.error(
                "Error executing command %s: %s", command, str(exep)
            )
            raise CommandExecutionError(
                f"Error executing command {command}: {str(exep)}"
            ) from exep

        return mill_response

    @timing_wrapper
    def stop(self):
        """Stop the mill"""
        self.execute_command("!")

    @timing_wrapper
    def reset(self):
        """Reset or unlock the mill"""
        self.execute_command("$X")

    @timing_wrapper
    def soft_reset(self):
        """Soft reset the mill"""
        self.execute_command("0x18")

    @timing_wrapper
    def home(self, timeout=90):
        """Home the mill with a timeout"""
        self.execute_command("$H")
        time.sleep(15)
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                mill_control_logger.warning("Homing timed out")
                break

            status = self.current_status()
            if "Idle" in status:
                mill_control_logger.info("Homing completed")
                self.homed = True
                break

            time.sleep(2)  # Check every 2 seconds

    def __wait_for_completion(self, incoming_status, timeout=90):
        """Wait for the mill to complete the previous command"""
        status = incoming_status
        start_time = time.time()
        while "Idle" not in status:
            if time.time() - start_time > timeout:
                mill_control_logger.warning("Command execution timed out")
                return status
            status = self.current_status()
            time.sleep(0.25)
        return status

    @timing_wrapper
    def current_status(self) -> str:
        """Get the current status of the mill"""
        command = "?"
        command_bytes = command.encode()
        status = ""
        attempt_limit = 25
        while status == "" and attempt_limit > 0:
            self.ser_mill.write(command_bytes + b"\n")
            time.sleep(0.25)
            status = self.ser_mill.readline().decode().rstrip()
            attempt_limit -= 1
        # Check for busy
        while status == "ok":
            status = self.ser_mill.readline().decode().rstrip()
        return status

    @timing_wrapper
    def set_feed_rate(self, rate):
        """Set the feed rate"""
        self.execute_command(f"F{rate}")

    @timing_wrapper
    def clear_buffers(self):
        """Clear input and output buffers"""
        self.ser_mill.flushInput()
        self.ser_mill.flushOutput()

    @timing_wrapper
    def gcode_mode(self):
        """Ask the mill for its gcode mode"""
        return self.execute_command("$C")

    @timing_wrapper
    def gcode_parameters(self):
        """Ask the mill for its gcode parameters"""
        return self.execute_command("$#")

    @timing_wrapper
    def gcode_parser_state(self):
        """Ask the mill for its gcode parser state"""
        return self.execute_command("$G")

    @timing_wrapper
    def grbl_settings(self) -> dict:
        """Ask the mill for its grbl settings"""
        return self.execute_command("$$")

    @timing_wrapper
    def set_grbl_setting(self, setting: str, value: str):
        """Set a grbl setting"""
        command = f"${setting}={value}"
        return self.execute_command(command)

    @timing_wrapper
    def current_coordinates(
        self, instrument: Instruments = Instruments.CENTER
    ) -> Coordinates:
        """
        Get the current coordinates of the mill.
        Args:
            None
        Returns:
            list: [x,y,z]
        """

        status = self.current_status()

        # Get the current mode of the mill
        # 0=WCS position, 1=Machine position, 2= plan/buffer and WCS position, 3=plan/buffer and Machine position.
        status_mode = self.config["$10"]

        if status_mode not in [0, 1, 2, 3]:
            mill_control_logger.error("Invalid status mode")
            raise ValueError("Invalid status mode")

        max_attempts = 3
        homing_pull_off = self.config["$27"]

        if status_mode in [0, 2]:
            match = wpos_pattern.search(status)
            for _ in range(max_attempts):
                if match:
                    x_coord = round(float(match.group(1)), 3)
                    y_coord = round(float(match.group(2)), 3)
                    z_coord = round(float(match.group(3)), 3)
                    mill_control_logger.info(
                        "WPos coordinates: X = %s, Y = %s, Z = %s",
                        x_coord,
                        y_coord,
                        z_coord,
                    )
                    break
                else:
                    mill_control_logger.warning(
                        "WPos coordinates not found in the line. Trying again..."
                    )
                    if _ == max_attempts - 1:
                        mill_control_logger.error(
                            "Error occurred while getting WPos coordinates"
                        )
                        raise LocationNotFound
        elif status_mode in [1, 3]:
            match = mpos_pattern.search(status)
            for _ in range(max_attempts):
                if match:
                    x_coord = float(match.group(1)) + homing_pull_off
                    y_coord = float(match.group(2)) + homing_pull_off
                    z_coord = float(match.group(3)) + homing_pull_off
                    mill_control_logger.debug(
                        "MPos coordinates: X = %s, Y = %s, Z = %s",
                        x_coord - homing_pull_off,
                        y_coord - homing_pull_off,
                        z_coord - homing_pull_off,
                    )
                    mill_control_logger.debug(
                        "WPos coordinates: X = %s, Y = %s, Z = %s",
                        x_coord,
                        y_coord,
                        z_coord,
                    )
                    break
                else:
                    mill_control_logger.warning(
                        "MPos coordinates not found in the line. Trying again..."
                    )
                    if _ == max_attempts - 1:
                        mill_control_logger.error(
                            "Error occurred while getting MPos coordinates"
                        )
                        raise LocationNotFound
        else:
            mill_control_logger.critical("Failed to obtain coordinates from the mill")
            self.stop()
            self.disconnect()
            sys.exit()

        # So far we have obtain the mill's coordinates
        # Now we need to adjust them based on the instrument to communicate where the current instrument is
        try:
            if instrument in [Instruments.CENTER, Instruments.LENS]:
                current_coordinates = [x_coord, y_coord, z_coord]

            else:
                offsets = self.config["instrument_offsets"][instrument.value]
                current_coordinates = [
                    x_coord - offsets["x"],
                    y_coord - offsets["y"],
                    z_coord - offsets["z"],
                ]

        except Exception as exception:
            raise ValueError("Invalid instrument") from exception
        return Coordinates(*current_coordinates)

    @timing_wrapper
    def rinse_electrode(self, rinses: int = 3):
        """
        Rinse the electrode by moving it to the rinse position and back to the
        center position.
        Args:
            None
        Returns:
            None
        """
        command_block = []
        coords = self.config["electrode_bath"]
        self.safe_move(coords["x"], coords["y"], 0, instrument=Instruments.ELECTRODE)

        for _ in range(rinses):
            command_block.append(f"G01 Z{coords['z']}")
            command_block.append("G01 Z0")

        command_block = "\n".join(command_block)
        self.execute_command(command_block)

        return 0

    @timing_wrapper
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

    @timing_wrapper
    def move_to_safe_position(self) -> str:
        """Move the mill to its current x,y location and z = 0"""
        return self.execute_command("G01 Z0")

    @timing_wrapper
    def move(self, x_coord, y_coord, z_coord) -> int:
        """
        WARNING: Will move diagonally
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

        command_coordinates = [
            x_coord + offsets["x"],
            y_coord + offsets["y"],
            z_coord + offsets["z"],
        ]

        # check that command coordinates are within working volume
        if command_coordinates[0] > 1 or command_coordinates[0] < working_volume["x"]:
            mill_control_logger.error("x coordinate out of range")
            raise ValueError("x coordinate out of range")
        if command_coordinates[1] > 1 or command_coordinates[1] < working_volume["y"]:
            mill_control_logger.error("y coordinate out of range")
            raise ValueError("y coordinate out of range")
        if command_coordinates[2] > 1 or command_coordinates[2] < working_volume["z"]:
            mill_control_logger.error("z coordinate out of range")
            raise ValueError("z coordinate out of range")

        command = MILL_MOVE.format(*command_coordinates)
        self.execute_command(command)
        return 0

    @timing_wrapper
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

        # with SessionLocal() as session:
        #     mill_config = session.query(MillConfig).order_by(MillConfig.id.desc()).first()
        #     mill_config.config = self.config
        #     session.commit()

        self.save_config()

    ## Special versions of the movement commands that avoid diagonal movements
    @timing_wrapper
    def safe_move(
        self,
        x_coord,
        y_coord,
        z_coord,
        instrument: Instruments,
        second_z_cord: float = None,
        second_z_cord_feed: float = None,
    ) -> Coordinates:
        """
        Move the mill to the specified coordinates using only horizontal (xy) and vertical movements.

        Args:
            x_coord (float): X coordinate.
            y_coord (float): Y coordinate.
            z_coord (float): Z coordinate.
            instrument (Instruments): The instrument to move to the specified coordinates.
            second_z_cord (float): The second z coordinate to move to.
            second_z_cord_feed (float): The feed rate to use when moving to the second z coordinate.

        Returns:
            Coordinates: Current center coordinates.
        """
        commands = []
        goto = Coordinates(x=x_coord, y=y_coord, z=z_coord)
        offsets = Coordinates(**self.config["instrument_offsets"][instrument.value])
        current_coordinates = self.current_coordinates()

        if self._is_already_at_target(goto, current_coordinates, offsets):
            mill_control_logger.debug(
                "%s is already at the target coordinates of [%s, %s, %s]",
                instrument,
                x_coord,
                y_coord,
                z_coord,
            )
            return current_coordinates

        target_coordinates = self._calculate_target_coordinates(
            goto, current_coordinates, offsets
        )
        self._log_target_coordinates(target_coordinates)
        move_to_zero = False
        if self.__should_move_to_zero_first(
            current_coordinates, target_coordinates, self.config["safe_height_floor"]
        ):
            mill_control_logger.debug("Moving to Z=0 first")
            # self.execute_command("G01 Z0")
            commands.append("G01 Z0")
            # current_coordinates = self.current_coordinates(instrument)
            move_to_zero = True
        else:
            mill_control_logger.debug("Not moving to Z=0 first")

        self._validate_target_coordinates(target_coordinates)

        commands.extend(
            self._generate_movement_commands(
                current_coordinates, target_coordinates, move_to_zero
            )
        )

        if second_z_cord is not None:
            # Add the movement to the second z coordinate and feed rate
            commands.append(f"G01 Z{second_z_cord} F{second_z_cord_feed}")
            # Restore the feed rate to the default of 2000
            commands.append("F2000")
        # Form the individual movement commands into a block seperated by \n
        commands = "\n".join(commands)
        self._execute_commands(commands)

        return self.current_coordinates(instrument)

    def _is_already_at_target(
        self, goto: Coordinates, current_coordinates: Coordinates, offsets: Coordinates
    ):
        """Check if the mill is already at the target coordinates"""
        return (goto.x + offsets.x, goto.y + offsets.y) == (
            current_coordinates.x,
            current_coordinates.y,
        ) and goto.z + offsets.z == current_coordinates.z

    def _calculate_target_coordinates(
        self, goto: Coordinates, current_coordinates: Coordinates, offsets: Coordinates
    ):
        """
        Calculate the target coordinates for the mill. Checking if the mill is already at the target xy coordinates and only moving if necessary.

        Args:
            goto (Coordinates): The target coordinates.
            current_coordinates (Coordinates): The current coordinates of the mill center.
            offsets (Coordinates): The offsets for the instrument.
        """
        if (goto.x, goto.y) == (current_coordinates.x, current_coordinates.y):
            return Coordinates(x=goto.x, y=goto.y, z=goto.z + offsets.z)
        else:
            return Coordinates(
                x=goto.x + offsets.x,
                y=goto.y + offsets.y,
                z=0 if goto.z + offsets.z > 0 else goto.z + offsets.z,
            )

    def _log_target_coordinates(self, target_coordinates: Coordinates):
        mill_control_logger.debug(
            "Target coordinates: [%s, %s, %s]",
            target_coordinates.x,
            target_coordinates.y,
            target_coordinates.z,
        )

    def _validate_target_coordinates(self, target_coordinates: Coordinates):
        working_volume = Coordinates(**self.config["working_volume"])
        if not working_volume.x <= target_coordinates.x <= 1:
            mill_control_logger.error("x coordinate out of range")
            raise ValueError("x coordinate out of range")
        if not working_volume.y <= target_coordinates.y <= 1:
            mill_control_logger.error("y coordinate out of range")
            raise ValueError("y coordinate out of range")
        if not working_volume.z <= target_coordinates.z <= 1:
            mill_control_logger.error("z coordinate out of range")
            raise ValueError("z coordinate out of range")

    def _generate_movement_commands(
        self,
        current_coordinates: Coordinates,
        target_coordinates: Coordinates,
        move_z_first: bool = False,
    ):
        commands = []
        if current_coordinates.z >= self.config["safe_height_floor"]:
            commands.append(f"G01 X{target_coordinates.x} Y{target_coordinates.y}")
            commands.append(f"G01 Z{target_coordinates.z}")
        else:
            if target_coordinates.x != current_coordinates.x:
                commands.append(f"G01 X{target_coordinates.x}")
            if target_coordinates.y != current_coordinates.y:
                commands.append(f"G01 Y{target_coordinates.y}")
            if target_coordinates.z != current_coordinates.z:
                commands.append(f"G01 Z{target_coordinates.z}")
            if (
                target_coordinates.z == current_coordinates.z and move_z_first
            ):  # The mill moved to Z=0 first, so move back to the target Z
                commands.append(f"G01 Z{target_coordinates.z}")
        return commands

    def _execute_commands(self, commands):
        if isinstance(commands, str):
            self.execute_command(commands)
        else:
            for command in commands:
                self.execute_command(command)

    def __should_move_to_zero_first(
        self,
        current: Coordinates,
        destination: Coordinates,
        safe_height_floor,
    ):
        """
        Determine if the mill should move to Z=0 before moving to the specified coordinates.
        Args:
            current (Coordinates): Current coordinates.
            offset (Coordinates): Target coordinates.
            safe_height_floor (float): Safe floor height.
        Returns:
            bool: True if the mill should move to Z=0 first, False otherwise.
        """
        # If current Z is 0 or at or above the safe floor height, no need to move to Z=0
        if current.z >= 0 or current.z >= safe_height_floor:
            return False

        # If current Z is below the safe floor height and X or Y coordinates are different, move to Z=0
        if current.x != destination.x or current.y != destination.y:
            return True

        return False


class MockMill(Mill):
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

    def __init__(self):
        super().__init__()
        self.ser_mill: serial.Serial = None
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        self.feed_rate = 2000
        self.status_mode = self.config["$10"]

    def connect_to_mill(self):
        """Connect to the mill"""
        mill_control_logger.info("Connecting to the mill")
        self.ser_mill = MagicMock(spec=serial.Serial)
        self.active_connection = True
        return self.ser_mill

    def disconnect(self):
        """Disconnect from the mill"""
        mill_control_logger.info("Disconnecting from the mill")
        if self.homed:
            self.rest_electrode()
        mill_control_logger.info("Closing the serial connection to the mill")
        self.ser_mill.close()
        self.active_connection = False

    def execute_command(self, command) -> str:
        """Simulate executing a command"""
        try:
            mill_control_logger.debug("Command sent: %s", command)

            # command_bytes = str(command).encode()
            self.mock_write(command)
            time.sleep(0.25)
            if command == "$$":
                return self.mock_readline(settings=True)
            else:
                mill_response = self.mock_readline()

            if command == "F2000":
                mill_control_logger.debug("Returned %s", mill_response)

            elif command == "?":
                mill_control_logger.debug("Returned %s", mill_response)

            elif command not in ["$H", "$X", "(ctrl-x)", "$C", "$#", "$G"]:
                # logger.debug("Initially %s", mill_response)
                self.__wait_for_completion(mill_response)
                mill_response = self.current_status()
                mill_control_logger.debug("Returned %s", mill_response)
            else:
                mill_control_logger.debug("Returned %s", mill_response)

            if mill_response.lower() in ["error", "alarm"]:
                if "error:22" in mill_response.lower():
                    # This is a GRBL error that occurs when the feed rate isn't set before moving with G01 command
                    mill_control_logger.error("Error in status: %s", mill_response)
                    # Try setting the feed rate and executing the command again
                    self.set_feed_rate(2000)
                    mill_response = self.execute_command(command)
                else:
                    mill_control_logger.error(
                        "current_status: Error in status: %s", mill_response
                    )
                    raise StatusReturnError(f"Error in status: {mill_response}")

        except Exception as exep:
            mill_control_logger.error(
                "Error executing command %s: %s", command, str(exep)
            )
            raise CommandExecutionError(
                f"Error executing command {command}: {str(exep)}"
            ) from exep

        return self.current_status()

    def set_feed_rate(self, rate):
        """Simulate setting the feed rate"""
        self.feed_rate = rate
        mill_control_logger.info("Setting feed rate to %s", rate)

    def clear_buffers(self):
        """Simulate clearing buffers"""
        mill_control_logger.info("Clearing buffers")

    def current_status(self) -> str:
        """Simulate getting the current status of the mill"""
        homing_pull_off = self.config["$27"]
        if self.status_mode == 0:
            return f"<Idle|WPos:{self.current_x},{self.current_y},{self.current_z}>"
        elif self.status_mode == 1:
            return f"<Idle|MPos:{self.current_x-homing_pull_off},{self.current_y-homing_pull_off},{self.current_z-homing_pull_off}>"

        elif self.status_mode == 2:
            return f"<Idle|WPos:{self.current_x},{self.current_y},{self.current_z}|Bf:15,127|FS:0,0>"

        elif self.status_mode == 3:
            return f"<Idle|MPos:{self.current_x-homing_pull_off},{self.current_y-homing_pull_off},{self.current_z-homing_pull_off}|Bf:15,127|FS:0,0>"

    def fetch_saved_config(self) -> dict:
        with SessionLocal() as session:
            mill_config = (
                session.query(MillConfig).order_by(MillConfig.id.desc()).first()
            )
            if mill_config:
                return mill_config.config
            else:
                pass

    def __wait_for_completion(self, incoming_status, timeout=90):
        """Wait for the mill to complete the previous command"""
        pass

    def mock_write(self, command: str):
        """Simulate writing to the mill"""
        mill_control_logger.debug("Writing to the mill: %s", command)
        ## For mock mill
        if command == "G01 Z0":
            self.current_z = 0.0
        elif command.startswith("G01"):
            # Extract the coordinates from the command when it could be any of the following:
            # G01 X{} Y{} Z{}
            # G01 X{} Y{}
            # G01 Y{} Z{}
            # G01 X{} Z{}
            # G01 X{}
            # G01 Y{}
            # G01 Z{}

            pattern = re.compile(r"G01(?: X([\d.-]+))?(?: Y([\d.-]+))?(?: Z([\d.-]+))?")

            match = pattern.search(command)
            if match:
                self.current_x = float(match.group(1) or self.current_x)
                self.current_y = float(match.group(2) or self.current_y)
                self.current_z = float(match.group(3) or self.current_z)
            else:
                mill_control_logger.warning(
                    "Could not extract coordinates from the command"
                )

    def mock_readline(self, settings: bool = False):
        """Simulate reading from the mill"""
        if settings:
            return self.config
        else:
            return self.current_status()
        ## End of mock mill specific code


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
