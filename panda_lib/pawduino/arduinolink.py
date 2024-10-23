"""
This module provides a class to link the computer and the Arduino
"""
import enum
import queue
import threading
import time

import serial
import serial.tools.list_ports


class ArduinoLink:
    """
    This class provides a link between the computer and the Arduino

    The class provides the following methods:
    - choose_arduino_port (choose the port that the ardiono is using)
    - open (opens a connection to the Arduino)
    - receive (listens to the Arduino and puts the messages in the queue)
    - configure (configures the Arduino)
    - send (sends a message to the Arduino and waits for a response)

    The class provides the following attributes:
    - arduinoPort (the port to which the Arduino is connected)
    - baudRate (the baud rate of the connection)
    - ack (the acknowledgment message from the Arduino)
    - arduinoQueue (a queue to store messages from the Arduino)    
    """
    arduinoQueue = queue.Queue()

    def __init__(self, port_address:str="/dev/ttyACM0", baud_rate:int=115200, ack:str="OK"):
        self.port = port_address
        self.baud_rate = baud_rate
        self.ack = ack
        self.configure()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def choose_arduino_port(self):
        """Use this method to list all available ports on the computer 
        and the corresponding devices connected to the ports
        """
        ports = serial.tools.list_ports.comports()
        choices = []
        # https://pyserial.readthedocs.io/en/latest/tools.html#serial.tools.list_ports.ListPortInfo
        print("PORT\tDEVICE\t\t\tMANUFACTURER")
        for index, value in enumerate(sorted(ports)):
            if value.hwid != "n/a":
                choices.append(index)
                print(index, "\t", value.name, "\t", value.manufacturer)
        choice = int(input("Choose the port that the Arduino is connected to: "))
        if choice in choices:
            self.port = sorted(ports)[choice]

    def open(self, timeout:float=5.0):
        """Use this method to open a connection to the Arduino"""
        start = time.time()
        print(f"Waiting for '{self.ack}' from Arduino on port {self.port} ...")
        while time.time() - start <= timeout:
            if not self.arduinoQueue.empty():
                if self.arduinoQueue.get() == self.ack:
                    print("Connection established")
                    return
        print(f"*** Unable to establish connection within {timeout} seconds")

    def close(self):
        """Use this method to close the connection to the Arduino"""
        self.serial.close()

    def receive(self):
        """This method listens to the Arduino and puts the messages in the queue"""
        message = b""
        while True:
            incoming = self.serial.read()
            if incoming == b"\n":
                self.arduinoQueue.put(message.decode("utf-8").strip().upper())
                message = b""
            else:
                if (incoming != b"") and (incoming != b"\r"):
                    message += incoming

    def configure(self):
        """This method configures the Arduino"""
        if self.port is None:
            self.choose_arduino_port()

        self.serial = serial.Serial(self.port, self.baud_rate, timeout=0.1)
        arduino_thread = threading.Thread(target=self.receive, args=())
        arduino_thread.daemon = True
        arduino_thread.start()

    def send(self, msg:str):
        """This method sends a message to the Arduino and waits for a response"""
        self.serial.write(msg.encode("utf-8"))
        self.serial.write(bytes("\n", encoding="utf-8"))
        while self.arduinoQueue.empty():
            pass
        return self.arduinoQueue.get()

class MockArduinoLink(ArduinoLink):
    """
    This class provides a mock link between the computer and the Arduino

    The class provides the following methods:
    - choose_arduino_port (choose the port that the ardiono is using)
    - open (opens a connection to the Arduino)
    - receive (listens to the Arduino and puts the messages in the queue)
    - configure (configures the Arduino)
    - send (sends a message to the Arduino and waits for a response)

    The class provides the following attributes:
    - arduinoPort (the port to which the Arduino is connected)
    - baudRate (the baud rate of the connection)
    - ack (the acknowledgment message from the Arduino)
    - arduinoQueue (a queue to store messages from the Arduino)    
    """
    def __init__(self, port_address:str="/dev/ttyACM0", baud_rate:int=115200, ack:str="OK"):
        super().__init__(port_address, baud_rate, ack)

    def choose_arduino_port(self):
        """Use this method to list all available ports on the computer 
        and the corresponding devices connected to the ports
        """
        print("PORT\tDEVICE\t\t\tMANUFACTURER")
        print("0\t/dev/ttyACM0\tArduino")
        print("1\t/dev/ttyACM1\tArduino")
        print("2\t/dev/ttyACM2\tArduino")
        print("3\t/dev/ttyACM3\tArduino")

    def open(self, timeout:float=5.0):
        """Use this method to open a connection to the Arduino"""
        print(f"Waiting for '{self.ack}' from Arduino on port {self.port} ...")
        print("Connection established")

    def receive(self):
        """This method listens to the Arduino and puts the messages in the queue"""
        pass

    def configure(self):
        """This method configures the Arduino"""
        pass

    def send(self, msg:str):
        """This method sends a message to the Arduino and waits for a response"""
        if msg == PawduinoFunctions.DECAPPPER_ON.value:
            return PawduinoReturnCodes.DECAPPER_ON
        elif msg == PawduinoFunctions.DECAPPPER_OFF.value:
            return PawduinoReturnCodes.DECAPPER_OFF
        elif msg == PawduinoFunctions.WHITE_LIGHTS_ON.value:
            return PawduinoReturnCodes.WHITE_LIGHTS_ON
        elif msg == PawduinoFunctions.WHITE_LIGHTS_OFF.value:
            return PawduinoReturnCodes.WHITE_LIGHTS_OFF
        elif msg == PawduinoFunctions.RB_LIGHTS_ON.value:
            return PawduinoReturnCodes.RB_LIGHTS_ON
        elif msg == PawduinoFunctions.RB_LIGHTS_OFF.value:
            return PawduinoReturnCodes.RB_LIGHTS_OFF
        else:
            return None

class PawduinoFunctions(str, enum.Enum):
    """
    This class provides the functions that the arduino can perform and the 
    corresponding commands to send to the arduino.
    
    Currently, the arduino can perform the following functions:
    - decapper_engage (engages the decapper)
    - decapper_disengage (disengages the decapper)
    - white_lights_on (turns on the white light)
    - white_lights_off (turns off the white light)
    - rb_lights_on (turns on the rb lights)
    - rb_lights_off (turns off the rb lights)

    """
    HELLO = "hello"
    DECAPPPER_ON = "do"
    DECAPPPER_OFF = "df"
    WHITE_LIGHTS_ON = "wo"
    WHITE_LIGHTS_OFF = "wf"
    RB_LIGHTS_ON = "ro"
    RB_LIGHTS_OFF = "rf"


class PawduinoReturnCodes(int, enum.Enum):
    """
    This class provides the return codes that the arduino can send back to the computer
    
    Currently, the arduino can return the following codes:
    - decapper_engaged (the decapper is engaged)
    - decapper_disengaged (the decapper is disengaged)
    - white_lights_on (the white lights are on)
    - white_lights_off (the white lights are off)
    - rb_lights_on (the rb lights are on)
    - rb_lights_off (the rb lights are off)

    """
    HELLO = "hi"
    DECAPPER_ON = 1
    DECAPPER_OFF = 2
    WHITE_LIGHTS_ON = 3
    WHITE_LIGHTS_OFF = 4
    RB_LIGHTS_ON = 5
    RB_LIGHTS_OFF = 6

if __name__ == "__main__":
    conn = ArduinoLink()
    # conn.showPorts()
    conn.open()

    while True:
        msg_payload = input("=>  message: ")
        response = conn.send(msg_payload)  # blocking, a response from the Arduino is required!
        print(f"<= response: '{response}'")
