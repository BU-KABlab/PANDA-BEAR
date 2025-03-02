"""
This module provides a class to link the computer and the Arduino
"""

import enum
import os
import queue
import time

import serial
import serial.tools.list_ports
from serial import Serial


class MockSerial:
    def __init__(self, *args, **kwargs):
        self.is_open = True
        self.in_waiting = 0
        self.output = []
        self.input = queue.Queue()

    def isOpen(self):
        return self.is_open

    def close(self):
        self.is_open = False

    def write(self, data):
        self.output.append(data)

    def readline(self):
        try:
            return self.input.get_nowait()
        except queue.Empty:
            return b""

    def flushInput(self):
        pass

    def flushOutput(self):
        pass

    def mock_input(self, data):
        self.input.put(data)


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

    def __init__(self, port_address: str = "COM4", baud_rate: int = 115200):
        """Initialize the ArduinoLink class"""
        self.ser: Serial = None
        self.port_address: str = port_address
        self.baud_rate: int = baud_rate
        self.timeout: int = 1
        self.configured: bool = False
        self.ack: str = "OK"
        self.configure()

    def __enter__(self):
        """For use in a with statement"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the connection to the Arduino when exiting the with statement"""
        self.close()

    def choose_arduino_port(self):
        """Interactive method to choose the port that the Arduino is connected to"""
        # Check the OS and list the available ports accordingly
        if os.name == "posix":
            ports = serial.tools.list_ports.grep("ttyACM")
        elif os.name == "nt":
            ports = list(serial.tools.list_ports.grep("COM"))
        else:
            print("Unsupported OS")
            return
        # choices = []
        # print("PORT\tDEVICE\t\t\tMANUFACTURER")
        # for index, value in enumerate(sorted(ports)):
        #     if value.hwid != "n/a":
        #         choices.append(index)
        #         print(index, "\t", value.name, "\t", value.manufacturer)
        # choice = int(input("Choose the port that the Arduino is connected to: "))
        # if choice in choices:
        #     port = sorted(ports)[choice]
        #     return port.name

        # Look for Arduino LLC in the manufacturer field
        for port in ports:
            if "Arduino LLC" in port.manufacturer:
                return port.name

    def close(self):
        """Close the connection to the Arduino"""
        self.ser.close()

    def configure(self):
        """Configure the connection to the Arduino"""
        if self.ser is None:
            self.ser = Serial(
                self.choose_arduino_port(), self.baud_rate, timeout=self.timeout
            )
        else:
            self.ser = Serial(self.port_address, self.baud_rate, self.timeout)

        if self.ser.is_open:
            print(f"Connected to {self.ser.name} at {self.baud_rate} baud")

            # Look for acknowlegement
            time.sleep(2)
            rx = self.ser.read_all().decode().strip()
            if rx == self.ack:
                # print("Arduino acknowledged connection")
                self.configured = True
            else:
                # print("Arduino is not ready")
                self.configured = False
                raise ConnectionError

            rx = self.send(PawduinoFunctions.HELLO.value)
            if rx == PawduinoReturnCodes.HELLO.value:
                # print("Arduino is configured")
                self.configured = True
            else:
                # print("Arduino is not configured")
                raise ConnectionError

        else:
            print(f"Failed to connect to {self.ser.name} at {self.baud_rate} baud")
            self.configured = False
            raise ConnectionError

    def receive(self):
        """Listen to the Arduino and put the messages in the queue"""
        rx = self.ser.readline()
        # print(f"Received: {rx}")
        if rx:
            rxd = rx.decode().strip()
            # print(f"Received: {rxd}")
            self.arduinoQueue.put(rxd)
            return rxd
        else:
            return None

    def trecieve(self):
        """Threaded version of receive using the queue.
        To be started elsewere.
        """
        rx = b""
        while True:
            rx = self.ser.readline()
            if rx and rx != b"" and rx != b"\n":
                rxd = rx.decode().strip()
                self.arduinoQueue.put(rxd)
                rx = b""
            time.sleep(0.1)

    def tsend(self, cmd):
        """Threaded version of send using the queue.
        To be started elsewere.
        """
        msg = str(cmd)
        self.ser.flush()
        self.ser.read_all()
        self.ser.write(msg.encode())
        time.sleep(0.5)
        while self.arduinoQueue.empty():
            time.sleep(0.1)
        rx = self.arduinoQueue.get(timeout=1)
        return rx

    def send(self, cmd):
        """Send a message to the Arduino and wait for a response"""
        self.ser.flush()
        self.ser.read_all()
        msg = str(cmd)
        attempts = 0
        while True and attempts < 3:
            self.ser.write(msg.encode())
            time.sleep(0.5)
            rx = self.receive()
            if rx is not None:
                break

            attempts += 1

        if rx is None:
            raise ConnectionError
        try:
            return int(rx)
        except (ValueError, TypeError):
            return rx

    def white_lights_on(self):
        """Turn on the white lights"""
        return self.send(PawduinoFunctions.WHITE_LIGHTS_ON.value)

    def white_lights_off(self):
        """Turn off the white lights"""
        return self.send(PawduinoFunctions.WHITE_LIGHTS_OFF.value)

    def curvature_lights_on(self):
        """Turn on the rb lights"""
        return self.send(PawduinoFunctions.CURVATURE_LIGHTS_ON.value)

    def curvature_lights_off(self):
        """Turn off the rb lights"""
        return self.send(PawduinoFunctions.CURVATURE_LIGHTS_OFF.value)

    def no_cap(self):
        """Engage the decapper"""
        return self.send(PawduinoFunctions.DECAPPPER_ON.value)

    def ALL_CAP(self):
        """Disengage the decapper"""
        return self.send(PawduinoFunctions.DECAPPPER_OFF.value)

    def hello(self):
        """Send a hello message to the Arduino"""
        return self.send(PawduinoFunctions.HELLO.value)

    def lights_off(self):
        """Turn off all lights"""
        self.white_lights_off()
        self.curvature_lights_off()


class MockArduinoLink(ArduinoLink):
    """
    This class provides a mock link between the computer and the Arduino

    The class provides the following methods:
    - send (sends a message to the Arduino and waits for a response)

    The class provides the following attributes:
    - arduinoQueue (a queue to store messages from the Arduino)
    """

    arduinoQueue = queue.Queue()

    def __init__(self):
        """Initialize the MockArduinoLink class"""
        self.configured = True
        self.ser = MockSerial()

    def send(self, cmd):
        """Send a message to the Arduino and wait for a response"""
        if cmd == PawduinoFunctions.WHITE_LIGHTS_ON.value:
            return PawduinoReturnCodes.WHITE_LIGHTS_ON.value
        elif cmd == PawduinoFunctions.WHITE_LIGHTS_OFF.value:
            return PawduinoReturnCodes.WHITE_LIGHTS_OFF.value
        elif cmd == PawduinoFunctions.CURVATURE_LIGHTS_ON.value:
            return PawduinoReturnCodes.CURVATURE_LIGHTS_ON.value
        elif cmd == PawduinoFunctions.CURVATURE_LIGHTS_OFF.value:
            return PawduinoReturnCodes.CURVATURE_LIGHTS_OFF.value
        elif cmd == PawduinoFunctions.DECAPPPER_ON.value:
            return PawduinoReturnCodes.DECAPPPER_ON.value
        elif cmd == PawduinoFunctions.DECAPPPER_OFF.value:
            return PawduinoReturnCodes.DECAPPPER_OFF.value
        elif cmd == PawduinoFunctions.HELLO.value:
            return PawduinoReturnCodes.HELLO.value
        else:
            return None


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
    CURVATURE_LIGHTS_ON = 3
    CURVATURE_LIGHTS_OFF = 4
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
    CURVATURE_LIGHTS_ON = 103
    CURVATURE_LIGHTS_OFF = 104
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
