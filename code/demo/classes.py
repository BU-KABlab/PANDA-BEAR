import time
import serial
import matplotlib.pyplot as plt

WELL_ROWS = "ABCDEF"
WELL_COLUMNS = range(1, 8)

class Wells:
    '''
    Position of well plate and each well in it. 
    Orientation is defined by:
        0 - Vertical, wells become more negative from A1 
        1 - Vertical, wells become less negative from A1
        2 - Horizontal, wells become more negative from A1
        3 - Horizontal, wells become less negative from A1
    '''
    def __init__(self, a1_X=0, a1_Y=0, orientation=0):
        self.wells = {}
        self.orientation = orientation
        a1_coordinates = {"x": a1_X, "y": a1_Y, "z": -30}
        for col_idx, col in enumerate("ABCDEFG"):
            for row in range(1, 14):
                well_id = col + str(row)
                if well_id == "A1":
                    coordinates = a1_coordinates
                    contents = None
                    volume = 0
                else:
                    well_offset = 9
                    z_base = -30
                    x_offset = col_idx * well_offset
                    y_offset = (row - 1) * well_offset
                    if orientation == 0:
                        coordinates = {"x": a1_coordinates["x"] - x_offset, "y": a1_coordinates["y"] - y_offset, "z": z_base}
                    elif orientation == 1:
                        coordinates = {"x": a1_coordinates["x"] + x_offset, "y": a1_coordinates["y"] + y_offset, "z": z_base}
                    elif orientation == 2:
                        coordinates = {"x": a1_coordinates["x"] - x_offset, "y": a1_coordinates["y"] - y_offset, "z": z_base}
                    elif orientation == 3:
                        coordinates = {"x": a1_coordinates["x"] + x_offset, "y": a1_coordinates["y"] + y_offset, "z": z_base}
                    contents = None
                    volume = 0
                self.wells[well_id] = {"coordinates": coordinates, "contents": contents, "volume": volume}

    def print_well_coordinates_table(self):
        print("Well Coordinates:")
        header_row_start = "   |"
        header_row = "     " + "      |     ".join([f"{row:2}" for row in range(1, 14)])
        header_underline = "     " + "      |     ".join(["--" for row in range(1, 14)])
        print(header_row_start + header_row)
        print(header_row_start + header_underline)
        for col in "ABCDEFG":
            col_str = f" {col} |"
            for row in range(1, 14):
                well_id = col + str(row)
                coordinates = self.wells[well_id]["coordinates"]
                x, y, z = coordinates["x"], coordinates["y"], coordinates["z"]
                col_str += f" {x:3} {y:3} {z or '':3} |"
            print(col_str)

    def visualize_well_coordinates(self):
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
        coordinates_dict = self.wells[well_id]["coordinates"]
        coordinates_list = [coordinates_dict["x"], coordinates_dict["y"], coordinates_dict["z"]]
        return coordinates_list
    
    def contents(self,well_id):
        return self.wells[well_id]["contents"]
    
    def volume(self,well_id):
        return self.wells[well_id]['volume']


class Vial:
    '''
    Class for creating vial objects with their position and contents
    '''
    def __init__(self, x, y, z_top, z_bottom, contents, volume):
        self.coordinates = {"x": x, "y": y, "z": z_top}
        self.depth = z_bottom
        self.contents = contents
        self.volume = volume

    @property
    def position(self):
        return self.coordinates


class MillControl:
    '''
    Set up the mill connection and pass commands, including special commands
    '''
    def __init__(self, ser_mill):
        self.ser_mill = ser_mill

    def __enter__(self):
        if not self.ser_mill.isOpen():
            self.ser_mill.open()
        time.sleep(2)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ser_mill.close()
        time.sleep(15)

    def execute_command(self, command):
        command_bytes = command.encode()
        self.ser_mill.write(command_bytes + b'\n')
        time.sleep(1)
        response = self.ser_mill.readline().strip().decode()
        return response

    def stop(self):
        self.execute_command('$X')

    def reset(self):
        self.execute_command('(ctrl-x)')

    def home(self):
        self.execute_command('$H')

    def current_status(self):
        return self.execute_command('?')

    def gcode_mode(self):
        self.execute_command('$C')

    def gcode_parameters(self):
        return self.execute_command('$#')

    def gcode_parser_state(self):
        return self.execute_command('$G')
