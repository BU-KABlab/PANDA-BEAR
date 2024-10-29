""" Contains mocks for cnc driver objects for offline testing
"""

# standard libraries
import re
import time
from unittest import mock

# third-party libraries
# from pydantic.dataclasses import dataclass
import serial
from panda_lib.config import read_logging_dir
from .instruments import Instruments
from .exceptions import (
    CommandExecutionError,
    StatusReturnError,
)
from .logger import set_up_mill_logger
from .driver import Mill as RealMill

logger = set_up_mill_logger(read_logging_dir())


class MockMill(RealMill):
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

    def __init__(self, config_file="configuration.json"):
        super().__init__(config_file)
        self.ser_mill: MockSerialToMill = self.connect_to_mill()
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        self.feed_rate = 2000

    def connect_to_mill(self):
        """Connect to the mill"""
        logger.info("Connecting to the mill")
        ser_mill = MockSerialToMill(
            port="COM4",
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=10,
        )
        self.active_connection = True
        return ser_mill

    def disconnect(self):
        """Disconnect from the mill"""
        logger.info("Disconnecting from the mill")
        self.ser_mill.close()
        self.active_connection = False

    def set_feed_rate(self, rate):
        """Simulate setting the feed rate"""
        self.feed_rate = rate
        logger.info("Setting feed rate to %s", rate)

    def clear_buffers(self):
        """Simulate clearing buffers"""
        logger.info("Clearing buffers")

class MockSerialToMill():
    """A class that simulates a serial connection to the mill for testing purposes."""
    def __init__(self, port, baudrate, parity, stopbits, bytesize, timeout):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = 0
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.parity = parity
        self.is_open = True
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0

    def close(self):
        """Simulate closing the serial connection"""
        self.is_open = False

    def write(self, command:bytes):
        """Simulate writing to the serial connection"""
        # decode the command to a string
        command = command.decode("utf-8")
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

            # Regular expression to extract the coordinates
            pattern = re.compile(r"G01 X([\d.-]+)? Y([\d.-]+)? Z([\d.-]+)?")
            match = pattern.search(command)
            if match:
                self.current_x = (
                    float(match.group(1)) if match.group(1) else self.current_x
                )
                self.current_y = (
                    float(match.group(2)) if match.group(2) else self.current_y
                )
                self.current_z = (
                    float(match.group(3)) if match.group(3) else self.current_z
                )
            else:
                logger.warning("Could not extract coordinates from the command")
        else:
            pass


    def read(self):
        """Simulate reading from the serial connection"""
        return f"<Idle|MPos:{self.current_x-3},{self.current_y-3},{self.current_z-3}|Bf:15,127|FS:0,0>"
