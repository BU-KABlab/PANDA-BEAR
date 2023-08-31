'''
This module contains the MillControl class, which is used to control the a GRBL CNC machine.
'''
import json
import logging
import pathlib
import re
import time
import sys
import serial

# Config file path


## set up logging to log to both the mill_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
file_handler = logging.FileHandler("mill_control.log")
system_handler = logging.FileHandler("ePANDA.log")
file_handler.setFormatter(formatter)
system_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(system_handler)


class Mill:
    """
    Set up the mill connection and pass commands, including special commands
    """

    def __init__(self):
        self.ser_mill = serial.Serial(
            port="COM4",
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=10,
        )
        self.config_file = 'mill_config.json'
        time.sleep(2)
        logging.basicConfig(
            filename="mill.log",
            filemode="w",
            format="%(asctime)s - %(message)s",
            level=logging.DEBUG,
        )
        logging_message = f"Mill connected: {self.ser_mill.isOpen()}"
        logging.info(logging_message)
        self.home()
        self.execute_command("F2000")
        self.ser_mill.flushInput()
        self.ser_mill.flushOutput()
        self.config = self.read_json_config()
        log_message = f"Mill config loaded: {self.config}"
        logging.info(log_message)

    def __enter__(self):
        '''Open the serial connection to the mill'''
        if not self.ser_mill.isOpen():
            self.ser_mill.open()
        time.sleep(2)
        return self

    def exit(self):
        '''Close the serial connection to the mill'''
        self.ser_mill.close()
        time.sleep(15)

    def read_json_config(self):
        """
        Reads a JSON config file and returns a dictionary of the contents.
        """
        config_file_path = pathlib.Path.cwd() / 'code/config' / self.config_file
        if not config_file_path.exists():
            logger.error("Config file not found")
            raise MillConfigNotFound

        with open(config_file_path, "r", encoding="UTF-8") as f:
            configuaration = json.load(f)
        return configuaration

    def execute_command(self, command):
        """encodes and send commands to the mill and returns the response"""
        logging_message = f"Executing command: {command}..."
        logging.debug(logging_message)
        command_bytes = command.encode()
        self.ser_mill.write(command_bytes + b"\n")
        time.sleep(1)
        try:
            if command == "F2000":
                time.sleep(1)
                out = self.ser_mill.readline()
                logging.debug("%s executed", command)

            elif command == "?":
                time.sleep(1)
                out = self.ser_mill.readlines()[0]
                logging.debug("%s executed. Returned %s )", command, out.decode())

            elif command != "$H":
                time.sleep(0.5)
                status = self.current_status()

                while status.find("Run") > 0:
                    status = self.current_status()

                    time.sleep(0.3)
                out = status
                logging.debug("%s executed", command)

            else:
                out = self.ser_mill.readline()
                logging.debug("%s executed", command)
            # time.sleep(1)
        except Exception as mill_exception:
            exception_type, experiment_object, exception_traceback = sys.exc_info()
            filename = exception_traceback.tb_frame.f_code.co_filename
            line_number = exception_traceback.tb_lineno
            logging.error("Exception: %s", mill_exception)
            logging.error("Exception type: %s", exception_type)
            logging.error("File name: %s", filename)
            logging.error("Line number: %d", line_number)
        return out

    def stop(self):
        """Stop the mill"""
        self.execute_command("$X")

    def reset(self):
        """Reset the mill"""
        self.execute_command("(ctrl-x)")

    def home(self):
        """Home the mill"""
        self.execute_command("$H")
        time.sleep(60)

    def current_status(self):
        """
        Instantly queries the mill for its current status.
        DOES NOT RUN during homing sequence.
        """
        self.ser_mill.flushInput()
        self.ser_mill.flushOutput()

        out = ""
        first = ""
        second = ""
        command = "?"
        command_bytes = command.encode()
        self.ser_mill.write(
            command_bytes
        )  # without carriage return because grbl documentation says its not needed
        time.sleep(2)
        status = self.ser_mill.readlines()
        time.sleep(0.5)
        try:
            if isinstance(status, list):
                list_length = len(status)
                if list_length == 0:
                    out = "No response"

                if list_length > 0:
                    first = status[0].decode("utf-8").strip()

                elif list_length > 1:
                    second = status[1].decode("utf-8").strip()

                elif first.find("ok") >= 0:
                    out = second
                else:
                    out = "could not parse response"
            if isinstance(status, str):
                out = status.decode("utf-8").strip()

            logging.info(out)
        except Exception as current_status_exception:
            exception_type, experiment_object ,exception_traceback = sys.exc_info()
            filename = exception_traceback.tb_frame.f_code.co_filename
            line_number = exception_traceback.tb_lineno
            logging.error("Exception: %s", current_status_exception)
            logging.error("Exception type: %s", exception_type)
            logging.error("File name: %s", filename)
            logging.error("Line number: %d", line_number)
        return out

    def gcode_mode(self):
        """Ask the mill for its gcode mode"""
        self.execute_command("$C")

    def gcode_parameters(self):
        """Ask the mill for its gcode parameters"""
        return self.execute_command("$#")

    def gcode_parser_state(self):
        """Ask the mill for its gcode parser state"""
        return self.execute_command("$G")

    def move_center_to_position(self, x_coord, y_coord, z_coord):
        """
        Move the mill to the specified coordinates.
        Args:
            coordinates (dict): Dictionary containing x, y, and z coordinates.
        Returns:
            str: Response from the mill after executing the command.
        """
        # offsets = {"x": 0, "y": 0, "z": 0}

        offsets = self.config["instrument_offsets"]["center"]

        mill_move = "G00 X{} Y{} Z{}"  # move to specified coordinates
        command = mill_move.format(
            x_coord + offsets["x"],
            y_coord + offsets["y"],
            z_coord + offsets["z"]
            )
        self.execute_command(command)
        return 0

    def current_coordinates(self):
        """
        Get the current coordinates of the mill.
        Args:
            None
        Returns:
            list: [x,y,z]
        """
        command = "?"
        status = self.execute_command(command)
        # Regular expression to extract MPos coordinates
        pattern = re.compile(r"MPos:([\d.-]+),([\d.-]+),([\d.-]+)")

        match = pattern.search(status.decode())  # Decoding the bytes to string
        if match:
            x_coord = float(match.group(1)) + 3
            y_coord = float(match.group(2)) + 3
            z_coord = float(match.group(3)) + 3
            log_message = (
                f"MPos coordinates: X = {x_coord}, Y = {y_coord}, Z = {z_coord}"
            )
            logging.info(log_message)
        else:
            logging.info("MPos coordinates not found in the line.")
            raise LocationNotFound
        return [x_coord, y_coord, z_coord]

    def rinse_electrode(self):
        """
        Rinse the electrode by moving it to the rinse position and back to the
        center position.
        Args:
            None
        Returns:
            None
        """
        [initial_x, initial_y, initial_z] = self.current_coordinates()
        self.move_center_to_position(initial_x, initial_y, initial_z * 0)
        self.move_electrode_to_position(-411, -30, 0)
        self.move_electrode_to_position(-411, -30, -45)
        self.move_electrode_to_position(-411, -30, 0)
        return 0

    def move_to_safe_position(self):
        '''Move the mill to its current x,y location and z = 0'''
        [initial_x, initial_y, initial_z] = self.current_coordinates()
        self.move_center_to_position(initial_x, initial_y, initial_z * 0)

    def move_pipette_to_position(
        self,
        x_coord: float = 0,
        y_coord: float = 0,
        z_coord=0.00,
    ):
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
        mill_move = "G00 X{} Y{} Z{}"  # move to specified coordinates
        command = mill_move.format(
            x_coord + offsets["x"], y_coord + offsets["y"], z_coord + offsets["z"]
        )  # x-coordinate has 84 mm offset for pipette location
        self.execute_command(str(command))
        return 0

    def move_electrode_to_position(
        self, x_coord: float, y_coord: float, z_coord: float = 0.00
    ):
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
        mill_move = "G00 X{} Y{} Z{}"
        command = mill_move.format(
            (x_coord + offsets["x"]), (y_coord + offsets["y"]), (z_coord + offsets["z"])
        )
        self.execute_command(str(command))
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
        config_file_path = pathlib.Path.cwd() / 'code/config' / self.config_file
        if not config_file_path.exists():
            logger.error("Config file not found")
            raise MillConfigNotFound

        try:
            with open(config_file_path, "w", encoding="UTF-8") as file:
                json.dump(self.config, file, indent=4)
            logging_message = f"Updated {offset_type} to {offset}"
            logging.info(logging_message)
            return 0
        except MillConfigNotFound as update_offset_exception:
            logging.error(update_offset_exception)
            return 3
        
class StatusReturnError(Exception):
    """Raised when the mill returns an error in the status"""
    pass

class MillConfigNotFound(Exception):
    """Raised when the mill config file is not found"""
    pass
    

class CommandExecutionError(Exception):
    pass

class LocationNotFound(Exception):
    """Raised when the mill cannot find its location"""
    pass
