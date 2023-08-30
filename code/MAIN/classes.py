"""Classes related to ePANDA"""
import json
import logging
import math
import pathlib
import sys
import time
import matplotlib.pyplot as plt
import regex as re
import serial

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="classes.log",
    filemode="a",
    format="%(asctime)s - %(name)% - %(levelname)% - %(message)%",
    level=logging.INFO,
    )

class Wells:
    """
    Position of well plate and each well in it.
    Orientation is defined by:
        0 - Vertical, wells become more negative from A1

        1 - Vertical, wells become less negative from A1

        2 - Horizontal, wells become more negative from A1

        3 - Horizontal, wells become less negative from A1
    """

    def __init__(self, a1_x=0, a1_y=0, orientation=0, starting_volume=0.00):
        self.wells = {}
        self.orientation = orientation
        self.z_bottom = -77  # -64
        self.z_top = 0
        self.radius = 4.0
        self.well_offset = 9  # mm from center to center
        self.well_capacity = 300  # ul
        self.echem_height = -73 #-68

        a1_coordinates = {"x": a1_x, "y": a1_y, "z": self.z_top}  # coordinates of A1
        volume = starting_volume
        for col_idx, col in enumerate("ABCDEFGH"):
            for row in range(1, 13):
                well_id = col + str(row)
                if well_id == "A1":
                    coordinates = a1_coordinates
                    contents = None
                    depth = self.z_bottom
                    if depth < self.z_bottom:
                        depth = self.z_bottom
                else:
                    x_offset = col_idx * self.well_offset
                    y_offset = (row - 1) * self.well_offset
                    if orientation == 0:
                        coordinates = {
                            "x": a1_coordinates["x"] - x_offset,
                            "y": a1_coordinates["y"] - y_offset,
                            "z": self.z_top,
                        }
                    elif orientation == 1:
                        coordinates = {
                            "x": a1_coordinates["x"] + x_offset,
                            "y": a1_coordinates["y"] + y_offset,
                            "z": self.z_top,
                        }
                    elif orientation == 2:
                        coordinates = {
                            "x": a1_coordinates["x"] - x_offset,
                            "y": a1_coordinates["y"] - y_offset,
                            "z": self.z_top,
                        }
                    elif orientation == 3:
                        coordinates = {
                            "x": a1_coordinates["x"] + x_offset,
                            "y": a1_coordinates["y"] + y_offset,
                            "z": self.z_top,
                        }
                    contents = []

                    depth = self.z_bottom

                self.wells[well_id] = {
                    "coordinates": coordinates,
                    "contents": contents,
                    "volume": volume,
                    "depth": depth,
                    "status": "empty",
                    "CV-results": None,
                }

    def visualize_well_coordinates(self):
        """Plot the well plate on a coordinate plane"""
        x_coordinates = []
        y_coordinates = []
        for well_id, well_data in self.wells.items():
            x_coordinates.append(well_data["coordinates"]["x"])
            y_coordinates.append(well_data["coordinates"]["y"])
        plt.scatter(x_coordinates, y_coordinates)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Well Coordinates")
        plt.grid(True)
        plt.xlim(-400, 0)
        plt.ylim(-300, 0)
        plt.show()

    def get_coordinates(self, well_id):
        """Return the coordinate of a specific well"""
        coordinates_dict = self.wells[well_id]["coordinates"]
        # coordinates_list = [coordinates_dict["x"], coordinates_dict["y"], coordinates_dict["z"]]
        return coordinates_dict

    def contents(self, well_id):
        """Return the contents of a specific well"""
        return self.wells[well_id]["contents"]

    def volume(self, well_id):
        """Return the volume of a specific well"""
        return self.wells[well_id]["volume"]

    def depth(self, well_id):
        """Return the depth of a specific well"""
        return self.wells[well_id]["depth"]

    def check_volume(self, well_id, added_volume: float):
        """Check if a volume can fit in a specific well"""
        info_message = f"Checking if {added_volume} can fit in {well_id} ..."
        logging.info(info_message)
        if self.wells[well_id]["volume"] + added_volume >= self.well_capacity:
            raise OverFillException(
                well_id, self.volume, added_volume, self.well_capacity
            )

        # elif self.wells[well_id]["volume"] + added_volume < 0:
        #    raise OverDraftException(well_id, self.volume, added_volume, self.well_capacity)
        else:
            info_message = f"{added_volume} can fit in {well_id}"
            logging.info(info_message)
            return True

    def update_volume(self, well_id, added_volume: float):
        """Update the volume of a specific well"""
        if self.wells[well_id]["volume"] + added_volume > self.well_capacity:
            raise OverFillException(
                self.wells[well_id],
                self.wells[well_id]["volume"],
                added_volume,
                self.well_capacity,
            )

        # elif self.wells[well_id]["volume"] + added_volume < 0:
        #    raise OverDraftException(self.name, self.volume, added_volume, self.capacity)
        else:
            self.wells[well_id]["volume"] += added_volume
            self.wells[well_id]["depth"] = (self.wells[well_id]["volume"] / 1000000) / (
                math.pi * math.pow(self.radius, 2.0)
            ) + self.z_bottom
            if self.wells[well_id]["depth"] < self.z_bottom:
                self.wells[well_id]["depth"] = self.z_bottom
            debug_message = f"New volume: {self.wells[well_id]['volume']} | New depth: {self.wells[well_id]['depth']}"
            logging.debug(debug_message)


class Vial:
    """
    Class for creating vial objects with their position and contents

    Args:
        x
        y
        contents
        volume in ml
        capacity in ml

    """
    def __init__(
        self,
        x_coord: float,
        y_coord: float,
        contents: str,
        volume=0.00,
        capacity=20000,
        radius=14,
        height=-20,
        z_bottom=-75,
        name="vial",
        filepath=None,
    ):
        self.name = name
        self.coordinates = {"x": x_coord, "y": y_coord, "z": height}
        self.bottom = z_bottom
        self.contents = contents
        self.capacity = capacity
        self.radius = radius
        self.height = height
        self.volume = volume
        self.base = math.pi * math.pow(self.radius, 2.0)
        self.depth = self.vial_height_calculator(self.radius*2,self.volume) + self.bottom
        self.contamination = 0
        self.filepath = filepath

    @property
    def position(self):
        """
        Returns
        -------
        DICT
            x, y, z-height

        """
        return self.coordinates

    def check_volume(self, added_volume: float):
        """
        Updates the volume of the vial
        """
        logging_msg = f"Checking if {added_volume} can fit in {self.name} ..."
        logging.info(logging_msg)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )
        else:
            logging_msg = f"{added_volume} can fit in {self.name}"
            logging.info(logging_msg)
            return True

    def write_volume_to_disk(self):
        """
        Writes the current volume to a json file
        """
        # logging.info(f'Writing {self.name} volume to {self.filepath}...')
        # with open(self.filepath, 'w') as f:
        #     json.dump(self.volume, f, indent=4)
        # return 0
        logging.info("Writing %s volume to vial file...", self.name)

        ## Open the file and read the contents
        with open(".\\code\\MAIN\\" + self.filepath, "r", encoding="UTF-8") as f:
            solutions = json.load(f)

        ## Find matching solution name and update the volume
        # solutions = solutions['solutions']
        for solution in solutions:
            if solution["name"] == self.name:
                solution["volume"] = self.volume
                solution["contamination"] = self.contamination
                break

        ## Write the updated contents back to the file
        with open(".\\code\\MAIN\\" + self.filepath, "w", encoding="UTF-8") as f:
            json.dump(solutions, f, indent=4)
        return 0

    def update_volume(self, added_volume: float):
        """
        Updates the volume of the vial
        """
        logging.info("Updating %s volume...", self.name)
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        if self.volume + added_volume < 0:
            raise OverDraftException(
                self.name, self.volume, added_volume, self.capacity
            )
        self.volume += added_volume
        self.write_volume_to_disk()
        self.depth = (
            self.vial_height_calculator((self.radius * 2), self.volume)
            + self.bottom
        )
        if self.depth < self.bottom:
            self.depth = self.bottom
        logging.debug("New volume: %s | New depth: %s", self.volume, self.depth)
        self.contamination += 1
        return 0

    def vial_height_calculator(self, diameter_mm, volume_ul):
        """
        Calculates the height of a volume of liquid in a vial given its diameter (in mm).
        """
        radius_mm = diameter_mm / 2
        area_mm2 = 3.141592653589793 * radius_mm**2
        volume_mm3 = volume_ul  # 1 ul = 1 mm3
        liquid_height_mm = volume_mm3 / area_mm2
        return liquid_height_mm


class MillControl:
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
        config_file_name = "mill_config.json"
        config_file_path = pathlib.Path.cwd() / config_file_name
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
            exception_type, exception_traceback = sys.exc_info()
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
        except Exception as current_status_ecxeption:
            exception_type, exception_traceback = sys.exc_info()
            filename = exception_traceback.tb_frame.f_code.co_filename
            line_number = exception_traceback.tb_lineno
            logging.error("Exception: %s", current_status_ecxeption)
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
        with open("mill_config.json", "w", encoding="UTF-8") as f:
            json.dump(self.config, f, indent=4)
        logging_message = f"Updated {offset_type} to {offset}"
        logging.info(logging_message)
        return 0


class OverFillException(Exception):
    """Raised when a vessel if over filled"""

    def __init__(self, name, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.name = name
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self) -> str:
        return f"OverFillException: {self.name} has {self.volume} + {self.added_volume} > {self.capacity}"


class OverDraftException(Exception):
    """Raised when a vessel if over drawn"""

    def __init__(self, name, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.name = name
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self) -> str:
        return f"OverDraftException: {self.name} has {self.volume} + {self.added_volume} < 0"


def main():
    """Test the classes"""
    wellplate = Wells(-218, -74, 0, 0)
    offsets = {"x": 36, "y": 30, "z": 0}
    coord = wellplate.wells["H2"]["coordinates"]
    print(
        f"x: {coord['x'] + offsets['x']} y: {coord['y'] + offsets['y']} z: {coord['z'] + offsets['z']}"
    )
    # wellplate.visualize_well_coordinates()


if __name__ == "__main__":
    main()
