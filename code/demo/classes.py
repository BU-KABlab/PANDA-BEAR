import time
import serial

WELL_ROWS = "ABCDEFGH"
WELL_COLUMNS = range(1, 13)

class Wells:
    '''Position of well plate and each well in it'''
    def __init__(self):
        self.wells = {}
        for row in WELL_ROWS:
            for col in WELL_COLUMNS:
                well_id = f"{row}{col}"
                if well_id == "A1":
                    coordinates = {"x": 10, "y": 10, "z": -30}
                    contents = None
                    volume = 0
                else:
                    a1_coordinates = self.wells["A1"]["coordinates"]
                    x_offset = (col - 1) * 9  # Adjust the x-coordinate based on the column
                    y_offset = (ord(row) - ord("A")) * 9  # Adjust the y-coordinate based on the row
                    coordinates = {"x": a1_coordinates["x"] + x_offset, "y": a1_coordinates["y"] + y_offset, "z": -30}
                    contents = None
                    volume = 0
                self.wells[well_id] = {"coordinates": coordinates, "contents": contents, "volume": volume}
    
    def get_coordinates(self, well_id):
        coordinates_dict = self.wells[well_id]["coordinates"]
        coordinates_list = [coordinates_dict["x"], coordinates_dict["y"], coordinates_dict["z"]]
        return coordinates_list

class Vial:
    '''Class for creating vial objects with their position and contents'''
    def __init__(self, x, y, z_top, z_bottom, contents, volume):
        self.coordinates = {"x": x, "y": y, "z": z_top}
        self.depth = z_bottom
        self.contents = contents
        self.volume = volume
    
    @property
    def position(self):
        return self.coordinates
    
    
    
class MillControl:
    '''Set up the mill connection and pass commands, including special commands'''
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
        '''Execute a command and return the response from the mill'''
        command_bytes = command.encode()
        self.ser_mill.write(command_bytes + b'\n')
        time.sleep(1)
        response = self.ser_mill.readline().strip().decode()
        return response

    def stop(self):
        '''Stop the mill'''
        self.execute_command('$X')

    def reset(self):
        '''Reset the mill'''
        self.execute_command('(ctrl-x)')

    def home(self):
        '''Home the mill'''
        self.execute_command('$H')

    def current_status(self):
        '''Get the current status of the mill'''
        return self.execute_command('?')

    def gcode_mode(self):
        '''Switch to G-code mode'''
        self.execute_command('$C')

    def gcode_parameters(self):
        '''Get G-code parameters'''
        return self.execute_command('$#')

    def gcode_parser_state(self):
        '''Get the G-code parser state'''
        return self.execute_command('$G')

    