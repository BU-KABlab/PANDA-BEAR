import time
import serial

class Wells:
    '''Position of well plate and each well in it'''
    def __init__(self):
        self.wells = {}
        for row in "ABCDEFGH":
            for col in range(1, 13):
                well_id = row + str(col)
                if well_id == "A1":
                    coordinates = {"x": 10, "y": 10, "z": -30}
                    contents = None
                    volume = 0
                else:
                    coordinates = {"x": None, "y": None, "z": None}
                    contents = None
                    volume = 0
                self.wells[well_id] = {"coordinates": coordinates, "contents": contents, "volume": volume}
    def get_coordinates(self, well_id):
        coordinates_dict = self.wells[well_id]["coordinates"]
        coordinates_list = [coordinates_dict["x"], coordinates_dict["y"], coordinates_dict["z"]]
        return coordinates_list

class Vial():
    '''Class for creating vial objects with their position and contents'''
    def __init__(self, x, y, z, contents, volume):
        self.coordinates = {"x": x, "y": y, "z": z}
        self.contents = contents
        self.volume = volume
    def get_volume(self):
        return self.volume
    
class MillControl():
    '''Set up the mill connection and pass commands, including special commands'''
    def __init__(self) -> None:
       
        self.ser_mill = serial.Serial(
            port= 'COM6',
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
            )
        if not self.ser_mill.isOpen():
            self.ser_mill.open()
        time.sleep(2)
    def send_to_mill(self,command:str):
        '''INPUT:
        command: "command to send"
        ser: serial variable for the mill
        OUTPUT: Returns the response from the mill'''
        ser = self.ser_mill
        if command != 'close':
            print(f'Sending: {command.strip()}')
            ser.write(str(command+'\n').encode())
            time.sleep(1)
            out=''
            while ser.inWaiting() > 0:
                out = ser.readline()
                        
            if out != '':
                response = (out.strip().decode())
        else:
            ser.close()
            time.sleep(15)    
        return response
    
    def stop(self):
        '''Stop the mill'''
        Mill_Control.send_to_mill('$X')
    def reset(self):
        Mill_Control.send_to_mill('(ctrl-x)')
    def home(self):
        Mill_Control.send_to_mill('$H')
    def current_status(self):
        Mill_Control.send_to_mill('?')
    def gcode_mode(self):
        Mill_Control.send_to_mill('$C')
    def gcode_paramaters(self):
        Mill_Control.send_to_mill('$#')
    def gcode_parser_state(self):
        Mill_Control.send_to_mill('$G')
    
    