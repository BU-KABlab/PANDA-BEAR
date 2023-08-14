import time
import serial
import matplotlib.pyplot as plt
import math
import sys
import logging
import pathlib
import json



class Wells:
    '''
    Position of well plate and each well in it. 
    Orientation is defined by:
        0 - Vertical, wells become more negative from A1

        1 - Vertical, wells become less negative from A1

        2 - Horizontal, wells become more negative from A1

        3 - Horizontal, wells become less negative from A1  
    '''
    def __init__(self, a1_X=0, a1_Y=0, orientation=0, starting_volume = 0.00):
        self.wells = {}
        self.orientation = orientation
        self.z_bottom = -64 #64
        self.z_top = 0
        self.radius = 4.0
        self.well_offset = 9 # mm from center to center
        self.well_capacity = 300 # ul
        self.echem_height = -68

        a1_coordinates = {"x": a1_X, "y": a1_Y,"z": self.z_top} # coordinates of A1
        volume = starting_volume
        for col_idx, col in enumerate("ABCDEFGH"):
            for row in range(1, 13):
                well_id = col + str(row)
                if well_id == "A1":
                    coordinates = a1_coordinates
                    contents = None
                    #depth = (volume/1000000)/(math.pi*math.pow(self.radius,2.0)) + self.z_bottom #Note volume must be converted to liters
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
                            "z": self.z_top
                        }
                    elif orientation == 1:
                        coordinates = {
                            "x": a1_coordinates["x"] + x_offset, 
                            "y": a1_coordinates["y"] + y_offset, 
                            "z": self.z_top
                            }
                    elif orientation == 2:
                        coordinates = {
                            "x": a1_coordinates["x"] - x_offset, 
                            "y": a1_coordinates["y"] - y_offset, 
                            "z": self.z_top
                            }
                    elif orientation == 3:
                        coordinates = {
                            "x": a1_coordinates["x"] + x_offset, 
                            "y": a1_coordinates["y"] + y_offset, 
                            "z": self.z_top
                        }
                    contents = []
                    
                    depth = self.z_bottom
                    
                self.wells[well_id] = {
                    "coordinates": coordinates, 
                    "contents": contents, 
                    "volume": volume,
                    "depth":depth,
                    "status": "empty",
                    "CV-results": None

                }

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
    
    def check_volume(self,well_id,added_volume:float):
        logging.info(f'Checking if {added_volume} can fit in {well_id} ...',end='')
        if self.wells[well_id]["volume"] + added_volume >= self.well_capacity:
            raise OverFillException(well_id, self.volume, added_volume, self.well_capacity)
        
        #elif self.wells[well_id]["volume"] + added_volume < 0:
        #    raise OverDraftException(well_id, self.volume, added_volume, self.well_capacity)
        else:
            logging.info(f'{added_volume} can fit in {well_id}')
            return True


    def update_volume(self,well_id,added_volume:float):
        

        if self.wells[well_id]["volume"] + added_volume > self.well_capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        
        #elif self.wells[well_id]["volume"] + added_volume < 0:
        #    raise OverDraftException(self.name, self.volume, added_volume, self.capacity)
        else:
            self.wells[well_id]["volume"] += added_volume
            self.wells[well_id]["depth"] = (self.wells[well_id]["volume"]/1000000)/(math.pi*math.pow(self.radius,2.0)) + self.z_bottom
            if self.wells[well_id]["depth"] < self.z_bottom:
                self.wells[well_id]["depth"] = self.z_bottom
            logging.debug(f'\tNew Well volume: {self.wells[well_id]["volume"]} | Solution depth: {self.wells[well_id]["depth"]}')

class Vial:
    '''
    Class for creating vial objects with their position and contents
    
    Args:
        x
        y
        contents
        volume in ml
        capacity in ml
        
    '''
    # TODO how to rewrite this to use disk stored information isntead of all in memory

    def __init__(self, x: float, y: float, contents: str, volume=0.00, capacity = 20000, radius = 13.5, height = -14, z_bottom = -64, name = 'vial',filepath = None):
        self.name = name
        self.coordinates = {"x": x, "y": y, "z": height}
        self.bottom = z_bottom
        self.contents = contents
        self.capacity = capacity
        self.radius = radius
        self.height = height
        self.volume = volume
        self.base = math.pi*math.pow(self.radius,2.0)
        self.depth = ((self.volume/1000000)/self.base) + z_bottom #Note volume must be converted to liters
        self.contamination = 0
        self.filepath = filepath

    @property
    def position(self):
        '''
        Returns
        -------
        DICT
            x, y, z-height

        '''
        return self.coordinates
    
    def check_volume(self,added_volume:float):
        '''
        Updates the volume of the vial
        '''
        logging.info(f'Check if {added_volume} can fit in {self.name} ...',end='')
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(self.name, self.volume, added_volume, self.capacity)
        else:
            logging.info(f'{added_volume} can fit in {self.name}')
            return True


    def update_volume(self,added_volume:float):
        '''
        Updates the volume of the vial
        '''
        logging.info(f'Updating {self.name} volume...')
        logging.debug(f'\tCurrent volume: {self.volume} | Current depth: {self.depth}')
        #logging.info(f'\tAdding {added_volume} to {self.volume}...')
        if self.volume + added_volume > self.capacity:
            raise OverFillException(self.name, self.volume, added_volume, self.capacity)
        elif self.volume + added_volume < 0:
            raise OverDraftException(self.name, self.volume, added_volume, self.capacity)
        else:
            self.volume += added_volume
            self.depth = self.vial_height_calculator(self.radius*2, self.volume) + self.bottom #Note volume must be converted to liters
        logging.debug(f'\tNew Solution volume: {self.volume} | Solution depth: {self.depth}')
        self.contamination += 1
        
    def vial_height_calculator(diameter_mm, volume_ul):
        """
        Calculates the height of a liquid in a vial given its diameter (in mm), height (in mm), and volume (in ul).
        """
        radius_mm = diameter_mm / 2
        area_mm2 = 3.141592653589793 * radius_mm ** 2
        volume_mm3 = volume_ul # 1 ul = 1 mm3
        liquid_height_mm = volume_mm3 / area_mm2
        return liquid_height_mm


class MillControl:
    '''
    Set up the mill connection and pass commands, including special commands
    '''
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
        logging.info(f'Mill connected: {self.ser_mill.isOpen()}')
        self.home()
        self.execute_command('F2000')
        self.ser_mill.flushInput()
        self.ser_mill.flushOutput()
        self.config = self.read_json_config()
        logging.info(f'Mill config loaded: {self.config}')
        
    def __enter__(self):
        if not self.ser_mill.isOpen():
            self.ser_mill.open()
        time.sleep(2)
        return self

    def __exit__(self):
        self.ser_mill.close()
        time.sleep(15)

    def read_json_config(self):
        '''
        Reads a JSON config file and returns a dictionary of the contents.
        '''
        config_file_name = 'mill_config.json'
        config_file_path = pathlib.Path.cwd() / config_file_name
        with open(config_file_path, 'r') as f:
            configuaration = json.load(f)
        return configuaration

    def execute_command(self, command):
        logging.debug(f'Executing command: {command}...')
        command_bytes = command.encode()
        self.ser_mill.write(command_bytes + b'\n')
        time.sleep(1)
        try:
            if command == 'F2000':
                time.sleep(1)
                out = self.ser_mill.readline()
                logging.debug(f'{command} executed')

            elif command != '$H':
                time.sleep(0.5)
                status = self.current_status()
                
                while status.find('Run') > 0:
                    
                    status = self.current_status()
                    
                    time.sleep(0.3)
                out = status
                logging.debug(f'{command} executed')
            
            else:
                out = self.ser_mill.readline()
                logging.debug(f'{command} executed')
            #time.sleep(1)
        except Exception as e:
            exception_type, exception_object, exception_traceback = sys.exc_info()
            filename = exception_traceback.tb_frame.f_code.co_filename
            line_number = exception_traceback.tb_lineno
            logging.error('Exception: ',e)
            logging.error("Exception type: ", exception_type)
            logging.error("File name: ", filename)
            logging.error("Line number: ", line_number)
        return out
    
    def stop(self):
        self.execute_command('$X')

    def reset(self):
        self.execute_command('(ctrl-x)')

    def home(self):
        self.execute_command('$H')
        time.sleep(90)

    def current_status(self):
        """
        Instantly queries the mill for its current status.
        DOES NOT RUN during homing sequence.
        """
        self.ser_mill.flushInput()
        self.ser_mill.flushOutput()
        
        out = ''
        first = ''
        second = ''
        command = '?'
        command_bytes = command.encode()
        self.ser_mill.write(command_bytes) # without carriage return because grbl documentation says its not needed
        time.sleep(2)
        status = self.ser_mill.readlines()
        time.sleep(2)
        try:
            if type(status) == list:
                list_length = len(status)
                if list_length == 0:
                    out = 'No response'

                if list_length > 0:
                    first = status[0].decode("utf-8").strip()
                
                if list_length > 1:
                    second = status[1].decode("utf-8").strip()
                
                if first.find('ok') >=0:
                   out = second
                else:
                    out = 'could not parse response'
            if type(status) == str:
                out = status.decode("utf-8").strip()
                
            #logging.info(f'\t\t{out}')
        except Exception as e:
            exception_type, exception_object, exception_traceback = sys.exc_info()
            filename = exception_traceback.tb_frame.f_code.co_filename
            line_number = exception_traceback.tb_lineno
            logging.error('Exception: ',e)
            logging.error("Exception type: ", exception_type)
            logging.error("File name: ", filename)
            logging.error("Line number: ", line_number)
        return out

    def gcode_mode(self):
        self.execute_command('$C')

    def gcode_parameters(self):
        return self.execute_command('$#')

    def gcode_parser_state(self):
        return self.execute_command('$G')
    
    def move_center_to_position(self, x, y, z):
        """
        Move the mill to the specified coordinates.
        Args:
            coordinates (dict): Dictionary containing x, y, and z coordinates.
        Returns:
            str: Response from the mill after executing the command.
        """
        #offsets = {"x": 0, "y": 0, "z": 0}

        offsets = self.config['instrument_offsets']['center']

        mill_move = "G00 X{} Y{} Z{}"  # move to specified coordinates
        command = mill_move.format(x + offsets["x"], y + offsets["y"], z + offsets["z"])
        self.execute_command(command)
        return 0


    ## TODO Add a diagnoal move check to move pipette to position and move electrode to position functions


    def move_pipette_to_position(
        self,
        x,
        y,
        z=0.00,
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
        #offsets = {"x": -88, "y": 0, "z": 0}
        offsets = self.config['instrument_offsets']['pipette']
        mill_move = "G00 X{} Y{} Z{}"  # move to specified coordinates
        command = mill_move.format(
            x + offsets["x"], y + offsets["y"], z + offsets["z"]
        )  # x-coordinate has 84 mm offset for pipette location
        self.execute_command(str(command))
        return 0


    def move_electrode_to_position(self, x, y, z):
        """
        Move the electrode to the specified coordinates.
        Args:
            coordinates (dict): Dictionary containing x, y, and z coordinates.
        Returns:
            str: Response from the mill after executing the command.
        """
        #offsets = {"x": 36, "y": 30, "z": 0}
        offsets = self.config['instrument_offsets']['electrode']
        # move to specified coordinates
        mill_move = "G00 X{} Y{} Z{}"
        command = mill_move.format(x + offsets["x"], y + offsets["y"], z + offsets["z"])
        self.execute_command(str(command))
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
        return f'OverFillException: {self.name} has {self.volume} + {self.added_volume} > {self.capacity}'
    
    
class OverDraftException(Exception):
    """Raised when a vessel if over drawn"""
    def __init__(self, name, volume, added_volume, capacity) -> None:
        super().__init__(self)
        self.name = name
        self.volume = volume
        self.added_volume = added_volume
        self.capacity = capacity

    def __str__(self) -> str:
        return f'OverDraftException: {self.name} has {self.volume} + {self.added_volume} < 0'
    
def main():
     wellplate = Wells(-218, -74, 0, 0)
     offsets = {"x": 36, "y": 30, "z": 0}
     coord = wellplate.wells['H2']['coordinates']
     print(f"x: {coord['x'] + offsets['x']} y: {coord['y'] + offsets['y']} z: {coord['z'] + offsets['z']}"
           
            )
     #wellplate.visualize_well_coordinates()

if __name__ == '__main__':
    main()