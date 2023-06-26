import time
import serial
import matplotlib.pyplot as plt
import math



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
        self.z_bottom = -100
        self.z_top = 0
        self.radius = 4.0
        self.well_offset = 9 # mm from center to center
        
        self.well_capacity = 0.2
        a1_coordinates = {"x": a1_X, "y": a1_Y,"z": self.z_top} #TODO set to zero for now, should be real value in future
        volume = 0
        for col_idx, col in enumerate("ABCDEFG"):
            for row in range(1, 14):
                well_id = col + str(row)
                if well_id == "A1":
                    coordinates = a1_coordinates
                    contents = None
                    depth = volume/(math.pi*math.pow(self.radius,2.0)) + self.z_bottom

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
                    contents = None
                    
                    depth = self.z_bottom
                    
                self.wells[well_id] = {
                    "coordinates": coordinates, 
                    "contents": contents, 
                    "volume": volume,
                    "depth":depth
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
    
    def update_volume(self,well_id,added_volume:float):
        

        if self.wells[well_id]["volume"] + added_volume > self.well_capacity:
            raise OverFillException
        
        elif self.wells[well_id]["volume"] + added_volume < 0:
            raise OverDraftException
        else:
            self.wells[well_id]["volume"] += added_volume
            self.wells[well_id]["depth"] = self.wells[well_id]["volume"]/(math.pi*math.pow(self.radius,2.0)) + self.z_bottom

"""class Well:
    def __init__(self, x, y, contents = None, volume=0.00, capacity=0.02, radius = 0.028, height = 0.061, z_bottom = -100):
        self.bottom = z_bottom
        self.capacity = capacity
        self.coordinates = {'x':x,'y':y}
        self.contents = contents
        self.height = height
        self.radius = radius
        self.volume = volume
        self.base = self.volume/(math.pi*math.pow(self.radius,2.0))
        self.depth = (self.volume/self.base) + self.bottom
    
    def update_volume(self,volume:float):
        self.volume += volume
        self.depth = (self.volume/self.base) + self.bottom"""

"""def create_wellplate(a1_X=0, a1_Y=0, orientation=0, WELL_ROWS = "ABCDEF", WELL_COLUMNS = range(1, 14), well_offset = 9):
    for col_idx, col in enumerate(WELL_ROWS):
            for row in WELL_COLUMNS:
                well_id = col + str(row)
                if well_id == "A1":
                    current_well = 'well_'+well_id

                    setattr('well_'+well_id, x = a1_X, y = a1_Y)
                else:
                    x_offset = col_idx * well_offset
                    y_offset = (row - 1) * well_offset
                    if orientation == 0:
                        x = getattr('well_A1', 'x') - x_offset
                        y = getattr('well_A1', 'y') - y_offset
                        setattr('well_'+ well_id,x = x, y = y)
                        
                    elif orientation == 1:
                        x = getattr('well_A1', 'x') + x_offset
                        y = getattr('well_A1', 'y') + y_offset
                        setattr('well_'+ well_id,x = x, y = y)

                    elif orientation == 2:
                        x = getattr('well_A1', 'x') - x_offset
                        y = getattr('well_A1', 'y') - y_offset
                        setattr('well_'+ well_id,x = x, y = y)
                        
                    elif orientation == 3:
                        x = getattr('well_A1', 'x') + x_offset
                        y = getattr('well_A1', 'y') + y_offset
                        setattr('well_'+ well_id,x = x, y = y)

"""
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
    def __init__(self, x: float, y: float, contents: str, volume=0.00, capacity = 20, radius = 0.018, height = -40, z_bottom = -98):
        self.coordinates = {"x": x, "y": y, "z": height}
        self.bottom = z_bottom
        self.contents = contents
        self.capacity = capacity
        self.radius = radius
        self.height = height + z_bottom
        self.volume = volume
        self.base = math.pi*math.pow(self.radius,2.0)
        self.depth = ((self.volume/1000)/self.base) + z_bottom #Note volume must be converted to liters

    @property
    def position(self):
        return self.coordinates
    
    def update_volume(self,added_volume:float):
        print(f'Adding {added_volume} to {self.volume}...')
        if self.volume + added_volume > self.capacity:
            raise OverFillException
        elif self.volume + added_volume < 0:
            raise OverDraftException
        else:
            self.volume += added_volume
            self.depth = ((self.volume/1000)/self.base) + self.bottom
        print(f'Solution volume now: {self.volume}')
        print(f'Solution depth now: {self.depth}')


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
                            timeout=1,
                        )
        time.sleep(2)
        self.home()
        self.ser_mill.flushInput()
        self.ser_mill.flushOutput()
        
    def __enter__(self):
        if not self.ser_mill.isOpen():
            self.ser_mill.open()
        time.sleep(2)
        return self

    def __exit__(self):
        self.ser_mill.close()
        time.sleep(15)

    def execute_command(self, command):
        print(f'Executing command: {command}...')
        command_bytes = command.encode()
        self.ser_mill.write(command_bytes + b'\n')
        time.sleep(1)
        
        if command != '$H':
            time.sleep(0.5)
            status = self.current_status()
            
            while status[:6] == "b'<Run":
                
                status = self.current_status()
                
                time.sleep(0.5)
            out = self.ser_mill.readline()
            print(f'{command} executed and returned: {out}')
        else:
            out = self.ser_mill.readline()
            print(f'{command} executed and returned: {out}')
        time.sleep(3)
        return out
    
    def stop(self):
        self.execute_command('$X')

    def reset(self):
        self.execute_command('(ctrl-x)')

    def home(self):
        self.execute_command('$H')
        time.sleep(30)

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
        #self.ser_mill.write(command_bytes + b'\n') 
        self.ser_mill.write(command_bytes) # version without carriage return because grbl documentation says its not needed
        status = self.ser_mill.readlines()
        if type(status) == list:
            list_length = len(status)
            first = status[0].decode()
            
            if list_length > 1:
                second = status[1].decode()
            
            if first == 'ok':
               out = second
            else:
                out = first
        if type(status) == str:
            out = status.decode()
            
        print(f'{out}')
        return out

    def gcode_mode(self):
        self.execute_command('$C')

    def gcode_parameters(self):
        return self.execute_command('$#')

    def gcode_parser_state(self):
        return self.execute_command('$G')


class OverFillException(Exception):
    """Raised when a vessel if over filled"""
    pass
    
class OverDraftException(Exception):
    """Raised when a vessel if over drawn"""
    pass
    