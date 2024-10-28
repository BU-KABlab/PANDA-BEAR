"""
This module provides a class to link the computer and the Arduino
"""
import enum
import queue
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

    def __init__(self, port_address: str = "COM3", baud_rate: int = 115200):
        self.port = port_address
        self.baud_rate: int = baud_rate
        self.configured: bool = False
        self.serial: serial.Serial = None
        self.configure()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def choose_arduino_port(self):
        ports = serial.tools.list_ports.comports()
        choices = []
        print("PORT\tDEVICE\t\t\tMANUFACTURER")
        for index, value in enumerate(sorted(ports)):
            if value.hwid != "n/a":
                choices.append(index)
                print(index, "\t", value.name, "\t", value.manufacturer)
        choice = int(input("Choose the port that the Arduino is connected to: "))
        if choice in choices:
            self.port = sorted(ports)[choice]

    def close(self):
        self.serial.close()

    def configure(self):
        if self.port is None:
            self.choose_arduino_port()
            self.serial = serial.Serial(self.port.name, self.baud_rate, timeout=1)
        else:
            self.serial = serial.Serial(self.port, self.baud_rate, timeout=1)

        if self.serial.isOpen():
            print(f"Connected to {self.serial.name} at {self.baud_rate} baud")
            rx = self.send(PawduinoFunctions.HELLO.value)
            if rx == PawduinoReturnCodes.HELLO.value:
                print("Arduino is ready")
                self.configured = True
            else:
                print("Arduino is not ready")
                self.configured = False
                return
        else:
            print(f"Failed to connect to {self.port.name} at {self.baud_rate} baud")
            self.configured = False
            return

    def receive(self):
        rx = self.serial.readline()
        # print(f"Received: {rx}")
        if rx:
            rxd = rx.decode().strip()
            # print(f"Received: {rxd}")
            self.arduinoQueue.put(rxd)
            return rxd
        else:
            return None

    def send(self, cmd):
        self.serial.flushInput()
        self.serial.flushOutput()
        msg = str(cmd)
        attempts = 0
        while True:
            self.serial.write(msg.encode())
            time.sleep(0.5)
            rx = self.receive()
            if rx is not None:
                break
            else:
                attempts += 1
                if attempts > 3:
                    print("Failed to communicate with Arduino")
                    return None
        try:
            return int(rx)
        except (ValueError, TypeError):
            return rx


class PawduinoFunctions(enum.Enum):
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

    WHITE_LIGHTS_ON = 1
    WHITE_LIGHTS_OFF = 2
    RB_LIGHTS_ON = 3
    RB_LIGHTS_OFF = 4
    DECAPPPER_ON = 5
    DECAPPPER_OFF = 6
    HELLO = 99


class PawduinoReturnCodes(enum.Enum):
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

    HELLO = 999
    WHITE_LIGHTS_ON = 101
    WHITE_LIGHTS_OFF = 102
    RB_LIGHTS_ON = 103
    RB_LIGHTS_OFF = 104
    DECAPPPER_ON = 105
    DECAPPPER_OFF = 106


def test_of_pawduino():
    """Test the pawduino sketch. By sending commands to the Arduino, and checking the response."""
    with ArduinoLink() as arduino:
        if arduino.configured is False:
            print("Failed to configure the Arduino")
            return
        for function in PawduinoFunctions:
            print(
                f"Sending '{function.name}' to the Arduino. Expecting return code {PawduinoReturnCodes[function.name].value}"
            )
            response = arduino.send(function.value)
            print(f"Arduino says: {response}")
            assert response == PawduinoReturnCodes[function.name].value

    print("All tests passed")


if __name__ == "__main__":
    test_of_pawduino()
