"""
This module provides a class to link the computer and the Arduino
"""

import asyncio
import enum
import logging
import os
import queue
import time
from typing import Any, Dict, Optional, Union

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

    def flush(self):
        pass

    def read_all(self):
        pass

    def mock_input(self, data):
        self.input.put(data)


class ArduinoLink:
    """
    This class provides a link between the computer and the Arduino

    The class provides the following methods:
    - choose_arduino_port (choose the port that the ardiono is using)
    - open (opens a connection to the Arduino) *can be used contextually
    - close (closes the connection to the Arduino) *can be used contextually
    - receive (listens to the Arduino and puts the messages in the queue)
    - configure (configures the Arduino)
    - send (sends a message to the Arduino and waits for a response) *available asynchronously
    - receive (receives a message from the Arduino) *available asynchronously
    - start_monitoring (starts a background task to monitor the Arduino messages)
    - stop_monitoring (stops the background task to monitor the Arduino messages)
    - get_next_message (gets the next message from the event queue) *available asynchronously

    Pipette Specific Methods:
    - home (homes the pipette)
    - get_status (gets the current status of the pipette)
    - move_to (moves the pipette to a specific position in mm)
    - aspirate (aspirates a specific volume in µL)
    - dispense (dispenses a specific volume in µL)
    - mix (mixes by performing multiple aspirate/dispense cycles)
    - move_relative (moves the pipette in a specific direction by a certain number of steps)


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
        self.timeout: int = 60
        self.configured: bool = False
        self.connected: bool = False
        self.ack: str = "OK"
        self._monitor_task = None
        self._running = False
        self._event_queue = asyncio.Queue()
        self.pipette_active = True
        self.logger = logging.getLogger("panda")

        # Automatically connect
        self.connect()

    def __enter__(self):
        """For use in a with statement"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the connection to the Arduino when exiting the with statement"""
        self.close()

    def _choose_arduino_port(self, interactive: bool = False) -> str:
        """Interactive method to choose the port that the Arduino is connected to"""
        # Check the OS and list the available ports accordingly
        if os.name == "posix":
            ports = serial.tools.list_ports.grep("ttyACM")
        elif os.name == "nt":
            ports = list(serial.tools.list_ports.grep("COM"))
        else:
            print("Unsupported OS")
            return
        if not interactive:
            # Look for Arduino LLC in the manufacturer field
            for port in ports:
                return port.name

        # If interactive, ask the user to choose the port
        print("Available ports:")
        for i, port in enumerate(ports):
            print(f"{i}: {port.device} ({port.description})")
        while True:
            try:
                choice = int(input("Choose the port number: "))
                if choice < 0 or choice >= len(ports):
                    print("Invalid choice")
                    return
                return ports[choice].device
            except ValueError:
                print("Invalid choice")

            except KeyboardInterrupt:
                print("\nExiting...")
                return
            except Exception as e:
                print(f"Error: {e}")
                return

    def close(self):
        """Close the connection to the Arduino"""
        self.ser.close()

    def connect(self):
        """Configure the connection to the Arduino"""
        try:
            if self.ser is None and self.port_address is None:
                # If no port address is provided, choose the port interactively
                self.ser = Serial(
                    self._choose_arduino_port(), self.baud_rate, timeout=self.timeout
                )
            else:
                self.ser = Serial(
                    self.port_address, self.baud_rate, timeout=self.timeout
                )

            if self.ser.is_open:
                # Look for acknowlegement
                time.sleep(10)
                rx = self.ser.read_all().decode().strip()
                if self.ack in rx:
                    self.configured = True
                    self.connected = True
                else:
                    self.configured = False
                    raise ConnectionError

                rx = self.send(PawduinoFunctions.CMD_HELLO.value)
                if str(PawduinoReturnCodes.RESP_HELLO.value) in rx:
                    self.configured = True
                    self.connected = True
                else:
                    raise ConnectionError

            else:
                self.configured = False
                raise ConnectionError

        except ConnectionError:
            # Attempt to connect using the port finder if a port was supplied but didnt work
            if self.port_address is not None:
                self.ser = None
                self.port_address = None
                self.connect()
                return

        except serial.SerialException:
            self.configured = False

    def receive(self):
        """Listen to the Arduino and put the messages in the queue"""
        rx = self.ser.readline()
        if rx:
            rxd = rx.decode().strip()
            if "OK:" in rxd:
                rxd = rxd.replace("OK:", "")
            elif "ERR:" in rxd:
                raise Exception(f"Arduino error: {rxd}")
            elif "DONE" in rxd:
                rxd = rxd.replace("DONE", "")
            self.arduinoQueue.put(rxd)
            return rxd
        else:
            return None

    async def async_receive(self) -> Optional[str]:
        """Asynchronous version of receive"""
        # Create a future to wait for in the event loop
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, self.receive)
        return await future

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
        self.ser.flush()  # Flush the input buffer
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

        if ":" in rx:
            sucess = rx.split(":")[0] == "OK"
            if not sucess:
                raise Exception(f"Arduino error: {rx}")
        return rx

    async def async_send(self, cmd) -> Union[int, str]:
        """Asynchronous version of send"""
        loop = asyncio.get_event_loop()
        self.ser.flush()
        await loop.run_in_executor(None, self.ser.read_all)

        msg = str(cmd)
        attempts = 0
        rx = None

        while attempts < 3:
            await loop.run_in_executor(None, lambda: self.ser.write(msg.encode()))
            await asyncio.sleep(0.5)
            rx = await self.async_receive()
            if rx is not None:
                break
            attempts += 1

        if rx is None:
            raise ConnectionError

        else:
            if ":" in rx:
                success = rx.split(":")[0] == "OK"
                if not success:
                    raise Exception(f"Arduino error: {rx}")

        return rx

    async def start_monitoring(self):
        """Start monitoring Arduino messages in the background"""
        if self._running:
            return

        self._running = True

        async def monitor():
            while self._running:
                try:
                    rx = await self.async_receive()
                    if rx is not None:
                        await self._event_queue.put(rx)
                except Exception as e:
                    print(f"Error in Arduino monitor: {e}")
                    await asyncio.sleep(1)
                await asyncio.sleep(0.1)

        self._monitor_task = asyncio.create_task(monitor())
        return self._monitor_task

    async def stop_monitoring(self):
        """Stop the background monitor"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def get_next_message(self, timeout=None):
        """Get the next message from the event queue"""
        try:
            return await asyncio.wait_for(self._event_queue.get(), timeout)
        except asyncio.TimeoutError:
            return None

    # Helper methods that can be used either synchronously or asynchronously

    async def async_white_lights_on(self):
        """Turn on the white lights asynchronously"""
        return await self.async_send(PawduinoFunctions.CMD_WHITE_ON.value)

    def white_lights_on(self):
        """Turn on the white lights"""
        return self.send(PawduinoFunctions.CMD_WHITE_ON.value)

    def white_lights_off(self):
        """Turn off the white lights"""
        return self.send(PawduinoFunctions.CMD_WHITE_OFF.value)

    async def async_white_lights_off(self):
        """Turn off the white lights asynchronously"""
        return await self.async_send(PawduinoFunctions.CMD_WHITE_OFF.value)

    def curvature_lights_on(self):
        """Turn on the rb lights"""
        return self.send(PawduinoFunctions.CMD_CONTACT_ON.value)

    async def async_curvature_lights_on(self):
        """Turn on the rb lights asynchronously"""
        return await self.async_send(PawduinoFunctions.CMD_CONTACT_ON.value)

    def curvature_lights_off(self):
        """Turn off the rb lights"""
        return self.send(PawduinoFunctions.CMD_CONTACT_OFF.value)

    async def async_curvature_lights_off(self):
        """Turn off the rb lights asynchronously"""
        return await self.async_send(PawduinoFunctions.CMD_CONTACT_OFF.value)

    def no_cap(self):
        """Engage the decapper"""
        resp = self.send(PawduinoFunctions.CMD_EMAG_ON.value)
        time.sleep(0.1)
        return resp

    async def async_no_cap(self):
        """Engage the decapper asynchronously"""
        resp = await self.async_send(PawduinoFunctions.CMD_EMAG_ON.value)
        await asyncio.sleep(0.1)
        return resp
    
    def ALL_CAP(self):
        """Disengage the decapper"""
        resp = self.send(PawduinoFunctions.CMD_EMAG_OFF.value)
        time.sleep(0.5)
        return resp

    async def async_ALL_CAP(self):
        """Disengage the decapper asynchronously"""
        resp = await self.async_send(PawduinoFunctions.CMD_EMAG_OFF.value)
        await asyncio.sleep(0.5)
        return resp

    def line_break(self):
        """Check if the capper line is broken (cap is present)"""
        value = self.send(PawduinoFunctions.CMD_LINE_BREAK.value)
        if value == str(PawduinoReturnCodes.RESP_LINE_BREAK.value):
            return True
        elif value == str(PawduinoReturnCodes.RESP_LINE_UNBROKEN.value):
            return False
        else:
            return None

    async def async_line_break(self) -> bool:
        """
        Check if the capper line is broken (cap is present) asynchronously

        Returns True if the line is broken, False if it is not, and None if there was an error
        """
        value = await self.async_send(PawduinoFunctions.CMD_LINE_BREAK.value)
        if value == str(PawduinoReturnCodes.RESP_LINE_BREAK.value):
            return True
        elif value == str(PawduinoReturnCodes.RESP_LINE_UNBROKEN.value):
            return False
        else:
            return None

    def line_test(self):
        """Trigger the line break test which runs the line break test 10 times, returning the results"""
        i = 10
        value = self.send(PawduinoFunctions.CMD_LINE_TEST.value)
        print(value)
        while i > 0:
            value = self.receive()
            print(value)
            i -= 1

    def pipette_send(self, cmd) -> dict:
        """Send a command to the pipette

        Arguments:
            cmd: The command to send to the pipette

        Returns:
            dict: The parsed response from the pipette

        Raises:
            Exception: If there is an error during communication with the pipette
            ConnectionError: If the pipette is not connected or configured properly
        """
        try:
            self.ser.flush()
            self.ser.read_all()
            self.ser.write(str(cmd).encode())
            time.sleep(0.5)

            # Read until we get a newline
            rx = self.ser.read_until(b"\n").strip()

            # Parse the response
            if rx.startswith(b"OK:"):
                response_data = rx[3:].decode()  # Remove OK: prefix

                # Check if this is a JSON-like response
                if response_data.startswith("{") and response_data.endswith("}"):
                    return self._parse_json_response(response_data, success=True)

                # Handle legacy format if needed
                if "DONE" in response_data:
                    response_data = response_data.replace("DONE", "").strip()

                # Simple comma-separated values format
                if "," in response_data:
                    parts = response_data.split(",")
                    if len(parts) >= 3:
                        return {
                            "success": True,
                            "homed": bool(int(parts[0].strip())),
                            "position": float(parts[1].strip()),
                            "max_volume": float(parts[2].strip()),
                        }
                return {"success": True, "data": response_data}

            elif rx.startswith(b"ERR:"):
                response_data = rx[4:].decode()  # Remove ERR: prefix

                # Check if this is a JSON-like response
                if response_data.startswith("{") and response_data.endswith("}"):
                    return self._parse_json_response(response_data, success=False)

                # Legacy error format
                return {"success": False, "error": response_data}

            else:
                raise ConnectionError(f"Unexpected response format: {rx}")

        except ConnectionError as e:
            self.logger.error("Pipette not connected or configured properly")
            raise ConnectionError("Pipette not connected or configured properly") from e

        except Exception as e:
            self.logger.error("Error during pipette send: %s", str(e))
            raise Exception(f"Error during pipette send: {str(e)}") from e

    def _parse_json_response(self, response_str, success=True):
        """Parse a JSON-like response from the Arduino

        Args:
            response_str: The JSON-like response string
            success: Whether this was marked as a success response

        Returns:
            dict: Parsed response data
        """
        result = {"success": success}

        # Remove curly braces
        content = response_str.strip("{}").strip()

        if not content:
            return result

        # Parse the key-value pairs
        parts = content.split(",")

        for part in parts:
            if ":" not in part:
                continue

            key, value = part.split(":", 1)

            # Clean up keys and values
            key = key.strip().strip('"')
            value = value.strip().strip('"')

            if key == "msg":
                result["message"] = value
            elif key == "v":
                # Parse array values
                if value.startswith("[") and value.endswith("]"):
                    values = value.strip("[]").split(",")
                    if len(values) >= 1:
                        try:
                            result["value1"] = float(values[0].strip())
                            if len(values) >= 2:
                                result["value2"] = float(values[1].strip())
                            if len(values) >= 3:
                                result["value3"] = float(values[2].strip())
                        except ValueError:
                            # If any conversion fails, just store the raw values
                            result["values"] = [v.strip() for v in values]

        return result

    def home(self) -> bool:
        """
        Home the pipette.

        Returns:
            bool: True if homing was successful
        """
        try:
            response = self.send(PawduinoFunctions.CMD_PIPETTE_HOME.value)
            return response
        except Exception as e:
            self.logger.error("Error during homing: %s", str(e))
            raise Exception(f"Error during homing: {str(e)}") from e

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the pipette.

        Returns:
            dict: Status information including position and volume
        """
        try:
            response = self.send(PawduinoFunctions.CMD_PIPETTE_STATUS.value)
            status = {}
            parts = []

            # Parse the new format: "OK:isHomed,position,maxVolume"
            # Example: "1,25,300"
            if "OK:" in response:
                parts = response.strip().split(",")
            if len(parts) >= 3:
                status["h"] = bool(int(parts[0].strip()))
                status["p"] = float(parts[1].strip())
                status["mxv"] = float(parts[2].strip())
        except Exception as e:
            self.logger.error("Error getting status: %s", str(e))
            return {}
        return status

    def move_to(self, position: float, speed: Optional[int] = None) -> bool:
        """
        Move to a specific position in mm.

        Args:
            position: Position in mm
            speed: Movement speed (steps/second)
            wait: Wait for the movement to complete

        Returns:
            bool: True if movement was successful
        """
        cmd = f"10{position}"
        if speed:
            cmd += f",{speed}"
        try:
            response = self.pipette_send(cmd)
            return response
        except Exception as e:
            self.logger.error("Error during movement: %s",str(e))
            raise Exception(f"Error during movement: {str(e)}") from e

    def move_relative(self, direction, steps, velocity, wait):
        """
        Move the pipette in a specific direction by a certain number of steps.

        Arguments:
            direction: Direction to move (1 for up, 0 for down)
            steps: Number of steps to move
            velocity: Speed of movement (steps/second)
            wait: Wait for the movement to complete

        """
        cmd = f"16{direction},{steps},{velocity}"
        try:
            response = self.pipette_send(cmd)
            return response
        except Exception as e:
            self.logger.error("Error during movement: %s",str(e))
            raise Exception(f"Error during movement: {str(e)}") from e

    def aspirate(self, volume: float, rate: Optional[float] = None) -> bool:
        """
        Aspirate a specific volume in µL.

        Args:
            volume: Volume to aspirate in µL
            rate: Aspiration rate in µL/s

        Returns:
            bool: True if aspiration was successful
        """
        cmd = f"11{volume}"
        if rate:
            cmd += f",{rate}"
        try:
            response = self.pipette_send(cmd)
            return response
        except Exception as e:
            self.logger.error("Error during aspiration: %s", str(e))
            raise Exception(f"Error during aspiration: {str(e)}") from e

    def dispense(self, volume: float, rate: Optional[float] = None) -> bool:
        """
        Dispense a specific volume in µL.

        Args:
            volume: Volume to dispense in µL
            rate: Dispensing rate in µL/s

        Returns:
            bool: True if dispensing was successful
        """
        cmd = f"12{volume}"
        if rate:
            cmd += f",{rate}"

        try:
            response = self.pipette_send(cmd)
            return response
        except Exception as e:
            self.logger.error("Error during dispensing: %s", str(e))
            raise Exception(f"Error during dispensing: {str(e)}")

    def mix(
        self, repetitions: int, volume: float, rate: Optional[float] = None
    ) -> bool:
        """
        Mix by performing multiple aspirate/dispense cycles.

        Args:
            repetitions: Number of mix cycles
            volume: Volume to mix in µL
            rate: Mixing rate in µL/s

        Returns:
            bool: True if mixing was successful
        """
        cmd = f"X{repetitions}"
        if volume:
            cmd += f",{volume}"
        if rate:
            cmd += f",{rate}"

        try:
            response = self.pipette_send(cmd)
            return response
        except Exception as e:
            self.logger.error("Error during mixing: %s", str(e))
            raise Exception(f"Error during mixing: {str(e)}") from e

    def hello(self):
        """Send a hello message to the Arduino"""
        return self.send(PawduinoFunctions.CMD_HELLO.value)

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
        self.ser.write(str(cmd).encode())
        if isinstance(cmd, tuple):
            cmd = cmd[0]  # Handle tuple values from the enum

        if cmd == PawduinoFunctions.CMD_WHITE_ON.value:
            return PawduinoReturnCodes.RESP_WHITE_ON.value
        elif cmd == PawduinoFunctions.CMD_WHITE_OFF.value:
            return PawduinoReturnCodes.RESP_WHITE_OFF.value
        elif cmd == PawduinoFunctions.CMD_CONTACT_ON.value:
            return PawduinoReturnCodes.RESP_CONTACT_ON.value
        elif cmd == PawduinoFunctions.CMD_CONTACT_OFF.value:
            return PawduinoReturnCodes.RESP_CONTACT_OFF.value
        elif cmd == PawduinoFunctions.CMD_EMAG_ON.value:
            return PawduinoReturnCodes.RESP_EMAG_ON.value
        elif cmd == PawduinoFunctions.CMD_EMAG_OFF.value:
            return PawduinoReturnCodes.RESP_EMAG_OFF.value
        elif cmd == PawduinoFunctions.CMD_LINE_BREAK.value:
            return True
        elif cmd == PawduinoFunctions.CMD_LINE_TEST.value:
            return PawduinoReturnCodes.RESP_LINE_UNBROKEN.value
        elif cmd == PawduinoFunctions.CMD_PIPETTE_HOME.value:
            return PawduinoReturnCodes.RESP_PIPETTE_HOMED.value
        elif cmd == PawduinoFunctions.CMD_PIPETTE_MOVE_TO.value:
            return PawduinoReturnCodes.RESP_PIPETTE_MOVED.value
        elif cmd == PawduinoFunctions.CMD_PIPETTE_ASPIRATE.value:
            return PawduinoReturnCodes.RESP_PIPETTE_ASPIRATED.value
        elif cmd == PawduinoFunctions.CMD_PIPETTE_DISPENSE.value:
            return PawduinoReturnCodes.RESP_PIPETTE_DISPENSED.value
        elif cmd == PawduinoFunctions.CMD_PIPETTE_STATUS.value:
            return PawduinoReturnCodes.RESP_PIPETTE_STATUS.value
        elif cmd == PawduinoFunctions.CMD_HELLO.value:
            return PawduinoReturnCodes.RESP_HELLO.value
        else:
            return None

    def receive(self):
        """Mock receive method"""
        if not self.arduinoQueue.empty():
            return self.arduinoQueue.get()
        return None

    async def async_receive(self):
        """Mock async receive method"""
        if not self.arduinoQueue.empty():
            return self.arduinoQueue.get_nowait()
        return None

    async def async_send(self, cmd):
        """Mock async send method"""
        self.ser.write(str(cmd).encode())
        if isinstance(cmd, tuple):
            cmd = cmd[0]
        return self.send(cmd)

    async def async_line_break(self):
        return await self.async_send(PawduinoFunctions.CMD_LINE_BREAK.value)


class AsyncMockArduinoLink(MockArduinoLink):
    """Mock version of ArduinoLink that supports async operations"""

    async def async_send(self, cmd):
        """Async version of send"""
        return self.send(cmd)

    # Add async versions of all other methods from MockArduinoLink


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

    CMD_WHITE_ON = 1
    CMD_WHITE_OFF = 2
    CMD_CONTACT_ON = 3
    CMD_CONTACT_OFF = 4
    CMD_EMAG_ON = 5
    CMD_EMAG_OFF = 6
    CMD_LINE_BREAK = 7
    CMD_LINE_TEST = 8
    CMD_PIPETTE_HOME = 9
    CMD_PIPETTE_MOVE_TO = 10
    CMD_PIPETTE_ASPIRATE = 11
    CMD_PIPETTE_DISPENSE = 12
    CMD_PIPETTE_STATUS = 13
    CMD_LED_TEST = 14
    CMD_PIPETTE_MIX = 15
    CMD_PIPETTE_MOVE_DIRECTION = 16
    CMD_HELLO = 99


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

    RESP_WHITE_ON = 101
    RESP_WHITE_OFF = 102
    RESP_CONTACT_ON = 103
    RESP_CONTACT_OFF = 104
    RESP_EMAG_ON = 105
    RESP_EMAG_OFF = 106
    RESP_LINE_BREAK = 107
    RESP_LINE_UNBROKEN = 108
    RESP_PIPETTE_HOMED = 109
    RESP_PIPETTE_MOVED = 110
    RESP_PIPETTE_ASPIRATED = 111
    RESP_PIPETTE_DISPENSED = 112
    RESP_PIPETTE_STATUS = 113
    RESP_LINE_TEST = 114
    RESP_PIPETTE_MIX = 115
    RESP_PIPETTE_MOVE_DIRECTION = 116
    RESP_HELLO = 999


def test_of_pawduino():
    """Test the pawduino sketch by sending each command, and checking the response."""
    with ArduinoLink() as arduino:
        if arduino.configured is False:
            print("Failed to configure the Arduino")
            return
        for function in PawduinoFunctions:
            print(
                f"Sending '{function.name}'. Expecting {PawduinoReturnCodes[function.name].value}"
            )
            response = arduino.send(function.value)
            print(f"Arduino returned: {response}")
            assert response == PawduinoReturnCodes[function.name].value

    print("All tests passed")


async def async_test_of_pawduino():
    """Test the pawduino sketch asynchronously."""
    arduino = ArduinoLink()
    try:
        if arduino.configured is False:
            print("Failed to configure the Arduino")
            return

        # Start background monitoring
        await arduino.start_monitoring()

        for function in PawduinoFunctions:
            print(f"Sending '{function.name}' to the Arduino")
            response = await arduino.async_send(function.value)
            print(f"Arduino says: {response}")

        # Stop background monitoring
        await arduino.stop_monitoring()

        print("All tests passed")
    finally:
        arduino.close()


# Function to run the async test from synchronous code
def run_async_test():
    """Run the async test in an event loop"""
    asyncio.run(async_test_of_pawduino())


# if __name__ == "__main__":
# test_of_pawduino()
# run_async_test()
# async def main():
#     arduino = ArduinoLink()
#     await arduino.start_monitoring()
#     response = await arduino.async_white_lights_on()
#     print(f"Response: {response}")

#     # Listen for incoming messages
#     while True:
#         msg = await arduino.get_next_message(timeout=1.0)
#         if msg is not None:
#             print(f"Received: {msg}")

#     await arduino.stop_monitoring()
#     arduino.close()

# asyncio.run(main())
