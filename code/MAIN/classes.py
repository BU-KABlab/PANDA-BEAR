import time
#import serial
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
        z_bottom = -100
        z_top = 0
        a1_coordinates = {"x": a1_X, "y": a1_Y,"z": z_top} #TODO set to zero for now, should be real value in future
        for col_idx, col in enumerate("ABCDEFG"):
            for row in range(1, 14):
                well_id = col + str(row)
                if well_id == "A1":
                    coordinates = a1_coordinates
                    contents = None
                    volume = 0
                    depth = z_bottom
                else:
                    well_offset = 9
                    x_offset = col_idx * well_offset
                    y_offset = (row - 1) * well_offset
                    if orientation == 0:
                        coordinates = {
                            "x": a1_coordinates["x"] - x_offset, 
                            "y": a1_coordinates["y"] - y_offset, 
                            "z": z_top
                        }
                    elif orientation == 1:
                        coordinates = {
                            "x": a1_coordinates["x"] + x_offset, 
                            "y": a1_coordinates["y"] + y_offset, 
                            "z": z_top
                            }
                    elif orientation == 2:
                        coordinates = {
                            "x": a1_coordinates["x"] - x_offset, 
                            "y": a1_coordinates["y"] - y_offset, 
                            "z": z_top
                            }
                    elif orientation == 3:
                        coordinates = {
                            "x": a1_coordinates["x"] + x_offset, 
                            "y": a1_coordinates["y"] + y_offset, 
                            "z": z_top
                        }
                    contents = None
                    volume = 0
                    depth = z_bottom
                    
                self.wells[well_id] = {
                    "coordinates": coordinates, 
                    "contents": contents, 
                    "volume": volume,
                    "depth":depth
                }

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
        #coordinates_list = [coordinates_dict["x"], coordinates_dict["y"], coordinates_dict["z"]]
        return coordinates_dict
    
    def contents(self,well_id):
        return self.wells[well_id]["contents"]
    
    def volume(self,well_id):
        return self.wells[well_id]['volume']
    def depth(self,well_id):
        return self.wells[well_id]['depth']


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

    def __exit__(self):
        self.ser_mill.close()
        time.sleep(15)

    def execute_command(self, command):
        command_bytes = command.encode()
        self.ser_mill.write(command_bytes + b'\n')
        time.sleep(1)
        out=''
        while self.ser_mill.inWaiting() > 0:
            out = self.ser_mill.readline()
                    
        if out != '':
            out = (out.strip().decode())
            print(f'{command} executed and returned: {out}')
        #out = self.ser_mill.readline().strip().decode()
        time.sleep(5)
        # TODO check if the below code works for waiting for a command to finish
        # if command != '$H':
        #     while self.current_status()[:4] == '<Run':
        #         time.sleep(0.01)
        time.sleep(5)
        return out

    def stop(self):
        self.execute_command('$X')

    def reset(self):
        self.execute_command('(ctrl-x)')

    def home(self):
        self.execute_command('$H')
        time.sleep(30)

    def current_status(self):
        first = ''
        second = ''
        command = '?'
        command_bytes = command.encode()
        self.ser_mill.write(command_bytes + b'\n')
        reply = self.ser_mill.readlines()
        if type(reply) == list:
            first = reply[0].decode()
            second = reply[1].decode()
            
            if first == 'ok':
               out = second
            else:
                out = first
        if type(reply) == str:
            out = reply[0].decode()
            
        print(f'{out}')
        return out

    def gcode_mode(self):
        self.execute_command('$C')

    def gcode_parameters(self):
        return self.execute_command('$#')

    def gcode_parser_state(self):
        return self.execute_command('$G')
