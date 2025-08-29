import glob
import threading
import errno
import asyncio
import enum
import logging
import os
import queue
import time
from typing import Any, Dict, Optional

import serial
import serial.tools.list_ports
from serial import Serial

# Define Enums and Custom Exceptions at the top
#TODO: Fix issue with no autoreconnect when dealing with communication failure

class PawduinoFunctions(enum.Enum):
    """Enum for Arduino commands"""

    CMD_HELLO = "0"  # Initial handshake
    CMD_WHITE_ON = "1"  # Turn on white lights
    CMD_WHITE_OFF = "2"  # Turn off white lights
    CMD_CONTACT_ON = "3"  # Turn on contact angle lights (blue/red)
    CMD_CONTACT_OFF = "4"  # Turn off contact angle lights
    CMD_EMAG_ON = "5"  # Turn on electromagnet
    CMD_EMAG_OFF = "6"  # Turn off electromagnet
    CMD_LINE_BREAK = "7"  # Check line break sensor
    CMD_LINE_TEST = "8"  # Test line break sensor (sends multiple responses)
    CMD_PIPETTE_HOME = "10"
    CMD_PIPETTE_MOVE_TO = "11"  # Expected: 11,pos_mm,speed_opt
    CMD_PIPETTE_ASPIRATE = "12"  # Expected: 12,vol_uL,rate_opt
    CMD_PIPETTE_DISPENSE = "13"  # Expected: 13,vol_uL,rate_opt
    CMD_PIPETTE_STATUS = "14"  # Get pipette status (homed, position, max_volume)
    CMD_PIPETTE_MIX = "15"  # Expected: 15,repetitions,volume,rate_opt
    CMD_MOVE_RELATIVE = "16"  # Expected: 16,direction,steps,velocity
    CMD_WHITE_ON_100 = "17"  # Turn on white lights with 100 brightness out of 250
    CMD_WHITE_ON_50 = "18"
    CMD_WHITE_ON_25 = "19"
    CMD_WHITE_ON_15 = "20"
    CMD_WHITE_ON_10 = "21"
    CMD_WHITE_ON_5 = "22"
    CMD_CONTACT_ON_50 = "23"
    CMD_CONTACT_ON_30 = "24"
    CMD_CONTACT_ON_20 = "25"
    CMD_CONTACT_ON_10 = "26"
    CMD_CONTACT_ON_5 = "27"
    

class PawduinoReturnCodes(enum.Enum):
    """Enum for Arduino return codes (used in mock and for validation)"""

    RESP_HELLO = "OK:Hello from Pawduino!"
    RESP_WHITE_ON = "OK:White lights on"
    RESP_WHITE_OFF = "OK:White lights off"
    RESP_CONTACT_ON = "OK:Contact lights on"
    RESP_CONTACT_OFF = "OK:Contact lights off"
    RESP_EMAG_ON = "OK:Electromagnet on"
    RESP_EMAG_OFF = "OK:Electromagnet off"
    RESP_LINE_BREAK = 'OK:{"value1":1}'  # 1 for broken, 0 for unbroken
    RESP_LINE_UNBROKEN = 'OK:{"value1":0}'
    RESP_PIPETTE_HOMED = "OK:Pipette homed"
    RESP_PIPETTE_MOVED = "OK:Pipette moved"
    RESP_PIPETTE_ASPIRATED = "OK:Pipette aspirated"
    RESP_PIPETTE_DISPENSED = "OK:Pipette dispensed"
    RESP_PIPETTE_MIXED = "OK:Pipette mixed"
    # Example: "OK:{homed:1,pos:10.5,max_vol:200}"
    RESP_PIPETTE_STATUS = "OK:{homed:1,pos:0.0,max_vol:200.0}"
    RESP_WHITE_ON_5 = "OK:White lights on 5%"
    RESP_CONTACT_ON_50 = "OK:Contact angle lights on 50%"
    RESP_CONTACT_ON_30 = "OK:Contact angle lights on 30%"
    RESP_CONTACT_ON_20 = "OK:Contact angle lights on 20%"
    RESP_CONTACT_ON_10 = "OK:Contact angle lights on 10%"
    RESP_CONTACT_ON_5 = "OK:Contact angle lights on 5%"

class ArduinoException(Exception):
    """Base class for Arduino communication errors."""


class ArduinoConnectionError(ArduinoException):
    """Error connecting to the Arduino."""


class ArduinoTimeoutError(ArduinoException):
    """Timeout during communication with Arduino."""


class ArduinoResponseError(ArduinoException):
    """Error in the Arduino's response or unexpected response format."""


class ArduinoCommandError(ArduinoException):
    """Error related to sending a command or the command itself."""


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

    def readline(self, timeout=None):
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

    The primary interface uses synchronous methods that will block until completion.
    For advanced use cases, asynchronous alternatives are also provided.

    The class provides the following methods:
    - choose_arduino_port (choose the port that the Arduino is using)
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

    The class provides the following attributes:
    - arduinoPort (the port to which the Arduino is connected)
    - baudRate (the baud rate of the connection)
    - ack (the acknowledgment message from the Arduino)
    - arduinoQueue (a queue to store messages from the Arduino)
    """

    arduinoQueue = queue.Queue()

    def __init__(
        self,
        port_address: str = "COM4",
        baud_rate: int = 115200,
        read_timeout: float = 10.0,
        max_retries: int = 3,
    ):
        self.ser: Serial = None
        self.port_address: Optional[str] = port_address
        self.baud_rate: int = baud_rate
        self.read_timeout: float = read_timeout  # Timeout for serial read operations
        self.max_retries: int = max_retries  # Max retries for sending a command
        self.configured: bool = False
        self.connected: bool = False
        self._monitor_task = None
        self._running = False
        self._send_lock = threading.Lock()
        self._max_reconnect_attempts = 5   # tweak as you like
        self._reconnect_backoff_sec = 0.5  # base backoff
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self.pipette_active = True  # Assuming pipette is active by default
        self.logger = logging.getLogger("panda")
        self.connect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _discover_port(self) -> Optional[str]:
        """
        Pick the most stable path for the Arduino:
        1) /dev/serial/by-id/* (preferred)
        2) VID/PID-matching ACM device
        3) any /dev/ttyACM*
        """
        # 1) stable by-id symlinks
        matches = sorted(glob.glob("/dev/serial/by-id/*Arduino*"))
        if matches:
            return matches[0]

        # 2) VID/PID filter (add yours here if different)
        for p in serial.tools.list_ports.comports():
            if p.vid and p.pid and (p.vid, p.pid) in {(0x2341, 0x8037), (0x2A03, 0x0043)}:
                return p.device

        # 3) last resort
        acms = sorted(glob.glob("/dev/ttyACM*"))
        return acms[0] if acms else None


    def _resolve_config_port(self, val: Optional[str]) -> Optional[str]:
        """
        Supports:
        - 'auto'  -> discover
        - globs   -> e.g. /dev/ttyACM*
        - literal -> exact device path
        """
        if not val or val == "auto":
            return self._discover_port()
        if "*" in val or "?" in val:
            m = sorted(glob.glob(val))
            return m[0] if m else None
        return val

    def _set_dtr_once(self, level: bool = True) -> None:
        if not self.ser:
            return
        try:
            if hasattr(self.ser, "setDTR"):
                self.ser.setDTR(level)  # type: ignore[attr-defined]
            elif hasattr(self.ser, "dtr"):
                self.ser.dtr = level    # type: ignore[attr-defined]
        except Exception as e:
            self.logger.debug("DTR set skipped: %s", e)



    def _choose_arduino_port(self, interactive: bool = False) -> Optional[str]:
        if os.name == "posix":
            ports = list(serial.tools.list_ports.comports())
            candidates = [p for p in ports if ("ttyACM" in p.device or "ttyUSB" in p.device)]
        elif os.name == "nt":
            ports = list(serial.tools.list_ports.comports())
            candidates = [p for p in ports if "COM" in p.device]
        else:
            self.logger.error("Unsupported OS")
            return None

        if not interactive:
            for p in candidates:
                manu = (p.manufacturer or "").lower()
                desc = (p.description or "").lower()
                if "arduino" in manu or "arduino" in desc:
                    return p.device
            return candidates[0].device if candidates else None

        print("Available ports:")
        for i, p in enumerate(ports):
            print(f"{i}: {p.device} ({p.description})")
        try:
            choice = int(input("Choose the port number: "))
            return ports[choice].device if 0 <= choice < len(ports) else None
        except Exception:
            return None

    def _safe_reset_buffers(self):
        if not self.ser:
            return
        try:
            # Prefer pySerial APIs over termios-backed flushInput/flushOutput
            self.ser.reset_input_buffer()
        except Exception as e:
            self.logger.warning("reset_input_buffer failed: %s", e)
        try:
            self.ser.reset_output_buffer()
        except Exception as e:
            self.logger.warning("reset_output_buffer failed: %s", e)

    def _handle_serial_error(self, exc: Exception, during: str):
        self.logger.error("Serial error during %s: %s", during, exc, exc_info=True)
        self._attempt_reconnect()

    def _attempt_reconnect(self):
        # Close first
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        self.connected = False
        self.configured = False

        last_err = None
        for attempt in range(1, self._max_reconnect_attempts + 1):
            backoff = self._reconnect_backoff_sec * (2 ** (attempt - 1))
            self.logger.info("Reconnecting to Arduino (attempt %d/%d)…", attempt, self._max_reconnect_attempts)
            try:
                # Force rediscovery on each attempt
                old_cfg = self.port_address
                self.port_address = "auto"
                self.connect()  # will handshake and set self.port_address to the chosen port
                self.logger.info("Reconnected successfully on attempt %d (port %s).", attempt, self.port_address)
                return
            except Exception as e:
                last_err = e
                self.logger.warning("Reconnect attempt %d failed: %s. Retrying in %.2fs", attempt, e, backoff)
                time.sleep(backoff)

        raise ArduinoConnectionError(
            f"Unable to reconnect to Arduino after {self._max_reconnect_attempts} attempts"
        ) from last_err

    def close(self):
        """Close the connection to the Arduino."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
                self.logger.info("Serial connection closed.")
            except IOError as e:
                self.logger.error("Error closing serial port: %s", e)
        self.connected = False
        self.configured = False

    def connect(self):
        """Establish and configure the connection to the Arduino."""
        if self.connected and self.configured:
            self.logger.info("Already connected and configured.")
            return

        if self.ser and self.ser.is_open:
            self.ser.close()

        chosen_port = None

        cfg = self.port_address
        if cfg in (None, "auto"):
            self.logger.info("Auto-discovering Arduino serial port…")
            chosen_port = self._discover_port()
        else:
            # allow globs like /dev/ttyACM*
            if "*" in cfg or "?" in cfg:
                chosen_port = self._resolve_config_port(cfg)
            else:
                chosen_port = cfg

        if not chosen_port:
            self.logger.error("No serial port found for Arduino (config=%r).", cfg)
            self.connected = False
            self.configured = False
            raise ArduinoConnectionError("No Arduino serial port found")

        self.logger.info(
            "Attempting to connect to Arduino on port: %s at baudrate: %s",
            chosen_port,
            self.baud_rate,
        )

        try:
            self.ser = Serial(
                chosen_port,
                self.baud_rate,
                timeout=self.read_timeout,
                write_timeout=self.read_timeout,
                rtscts=False,
                dsrdtr=False,
                exclusive=True,  # Linux-only; safe to leave if unsupported elsewhere
            )
            try:
                self.ser.setDTR(True)  # set once; avoids repeated reset loops on some boards
            except Exception:
                pass

            if not self.ser.is_open:
                raise ArduinoConnectionError(
                    f"Failed to open serial port {chosen_port}"
                )
            self.port_address = chosen_port
            self.connected = True
            self.logger.info(
                "Serial port opened: %s. Waiting for Arduino to initialize...",
                chosen_port,
            )
            time.sleep(10)
            self._safe_reset_buffers()

            self.logger.info("Attempting handshake with Arduino...")
            self.configured = True
            response = self.send(PawduinoFunctions.CMD_HELLO)

            if response.get("success") and PawduinoReturnCodes.RESP_HELLO.value.split(
                ":", 1
            )[1] in response.get("raw_data", ""):
                self.configured = True
                self.logger.info(
                    "Arduino handshake successful. Connected and configured."
                )
            else:
                self.logger.error("Arduino handshake failed. Response: %s", response)
                self.close()
                raise ArduinoConnectionError(
                    f"Handshake failed with Arduino on {chosen_port}. Response: {response.get('raw_data')}"
                )

        except serial.SerialException as e:
            self.logger.error("SerialException during connection: %s", e, exc_info=True)
            self.connected = False
            self.configured = False
            if self.ser and self.ser.is_open:
                self.ser.close()
            raise ArduinoConnectionError(
                f"Serial error connecting to Arduino on {chosen_port}: {e}"
            ) from e
        except ArduinoException as e:
            self.logger.error(
                "ArduinoException during connection: %s", e, exc_info=True
            )
            self.connected = False
            self.configured = False
            if self.ser and self.ser.is_open:
                self.ser.close()
            raise
        except IOError as e:
            self.logger.error("IOError during connection: %s", e, exc_info=True)
            self.connected = False
            self.configured = False
            if self.ser and self.ser.is_open:
                self.ser.close()
            raise ArduinoConnectionError(
                f"IO error connecting to Arduino on {chosen_port}: {e}"
            ) from e

    def receive(self) -> Optional[str]:
        if not self.ser or not self.ser.is_open:
            self.logger.warning("Receive called but serial port is not open.")
            return None
        try:
            line = self.ser.readline()
            if not line:
                return None
            try:
                decoded_line = line.decode(errors="replace").strip()
            except Exception as e:
                self.logger.warning("Decode error on serial line: %s", e)
                decoded_line = line.decode("latin-1", errors="replace").strip()
            self.logger.debug("Arduino Raw Receive: %s", decoded_line)
            return decoded_line
        except (serial.SerialException, OSError, IOError) as e:
            self._handle_serial_error(e, during="receive")
            return None  # after reconnect, caller may retry

    async def async_receive(self) -> Optional[str]:
        """Asynchronous version of receive"""
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, self.receive)
        return await future
    
    def send(self, cmd_enum_member: PawduinoFunctions, *args) -> Dict[str, Any]:
        if not isinstance(cmd_enum_member, PawduinoFunctions):
            raise ArduinoCommandError(f"send expects a PawduinoFunctions member, got {cmd_enum_member!r}")

        with self._send_lock:
            return self._send_internal(cmd_enum_member, *args)
    
    '''
    #TODO: ensure new function works before deleting old function
    def send(self, cmd_enum_member: PawduinoFunctions, *args) -> Dict[str, Any]:
        """
        Send a command to the Arduino and get the response.
        Handles command construction, retries, and basic response parsing.
        Will block until a properly formatted response (starting with OK: or ERR:) is received,
        or until the total timeout of 60 seconds is reached.

        Args:
            cmd_enum_member: The PawduinoFunctions enum member for the command.
            *args: Any arguments required by the command.

        Returns:
            A dictionary containing:
                'success': bool,
                'raw_data': str (the raw string from Arduino after OK:/ERR:),
                'parsed_data': dict (if response was JSON-like or key-value),
                'error_message': str (if ERR: was received)
        """
        if (
            not self.connected
            or not self.configured
            or not self.ser
            or not self.ser.is_open
        ):
            self.logger.error("Send attempt while not connected or configured.")
            raise ArduinoConnectionError("Not connected to Arduino.")

        command_code = cmd_enum_member.value
        command_str_parts = [command_code]
        command_str_parts.extend(map(str, args))
        command_to_send = ",".join(command_str_parts) + "\n"

        self.logger.debug("Sending to Arduino: %s", command_to_send.strip())

        # Set up total timeout of 60 seconds
        start_time = time.time()
        max_total_time = 60.0  # 1 minute total timeout
        response_str = None

        while time.time() - start_time < max_total_time:
            try:
                self.ser.flushInput()
                self.ser.flushOutput()
                self.ser.write(command_to_send.encode())

                attempt_start_time = time.time()
                attempts_remaining = True

                # Keep reading until we get a properly formatted response or timeout
                while attempts_remaining and time.time() - start_time < max_total_time:
                    # Blocking read until a line ending is received
                    raw_response_bytes = self.ser.readline()

                    if not raw_response_bytes:
                        elapsed = time.time() - attempt_start_time
                        self.logger.warning(
                            "No response from Arduino (elapsed: %.2fs, timeout: %ss) for: %s",
                            elapsed,
                            max_total_time,
                            command_to_send.strip(),
                        )

                        # # If we've been waiting too long for this attempt, reset and try again
                        # if elapsed >= max_total_time * 2:
                        #     attempts_remaining = False

                        time.sleep(1)
                        continue

                    response_str = raw_response_bytes.decode().strip()
                    self.logger.debug(
                        "Raw response: %s (elapsed: %.2fs)",
                        response_str,
                        time.time() - start_time,
                    )

                    # Only accept responses that start with OK: or ERR:
                    if response_str.startswith("OK:") or response_str.startswith(
                        "ERR:"
                    ):
                        return self._process_response(response_str, command_to_send)
                    else:
                        self.logger.warning(
                            "Received malformed response: %s, continuing to wait for proper response",
                            response_str,
                        )
                        # Keep trying with the current attempt
                        time.sleep(1)

            except serial.SerialTimeoutException:
                self.logger.warning(
                    "SerialTimeoutException (elapsed: %.2fs) for: %s",
                    time.time() - start_time,
                    command_to_send.strip(),
                )
                time.sleep(0.1)
            except serial.SerialException as e:
                self.logger.error(
                    "Serial communication error (elapsed: %.2fs) for '%s': %s",
                    time.time() - start_time,
                    command_to_send.strip(),
                    e,
                    exc_info=True,
                )
                time.sleep(1)
            except IOError as e:
                self.logger.error(
                    "IO error during send (elapsed: %.2fs) for '%s': %s",
                    time.time() - start_time,
                    command_to_send.strip(),
                    e,
                    exc_info=True,
                )
                time.sleep(1)

            # Small delay before retrying
            time.sleep(0.2)

        # If we get here, we've reached the 1-minute timeout without a properly formatted response
        elapsed = time.time() - start_time
        self.logger.error(
            "Total timeout exceeded (%.2f seconds) waiting for response to: %s",
            elapsed,
            command_to_send.strip(),
        )
        raise ArduinoTimeoutError(
            f"Timeout after {elapsed:.1f} seconds waiting for properly formatted response for: {command_to_send.strip()}"
        )
    '''

    def _send_internal(self, cmd_enum_member: PawduinoFunctions, *args) -> Dict[str, Any]:
        if (not self.connected) or (not self.configured) or (not self.ser) or (not self.ser.is_open):
            raise ArduinoConnectionError("Not connected to Arduino.")

        command_code = cmd_enum_member.value
        command_to_send = ",".join([command_code, *map(str, args)]) + "\n"
        self.logger.debug("Sending to Arduino: %s", command_to_send.strip())

        start_time = time.time()
        max_total_time = 60.0
        attempted_reconnect = False

        while time.time() - start_time < max_total_time:
            try:
                self._safe_reset_buffers()
                self.ser.write(command_to_send.encode())

                # Wait for OK:/ERR: line
                while time.time() - start_time < max_total_time:
                    raw = self.ser.readline()
                    if not raw:
                        self.logger.warning("No response yet for: %s", command_to_send.strip())
                        time.sleep(0.1)
                        continue

                    response_str = raw.decode(errors="replace").strip()
                    self.logger.debug("Raw response: %s", response_str)

                    if response_str.startswith(("OK:", "ERR:")):
                        return self._process_response(response_str, command_to_send)
                    else:
                        self.logger.warning("Malformed response: %s", response_str)
                        time.sleep(0.1)
                        continue

            except (serial.SerialTimeoutException,) as e:
                self.logger.warning("Serial timeout for '%s': %s", command_to_send.strip(), e)
                time.sleep(0.1)

            except (serial.SerialException, OSError, IOError) as e:
                msg = str(e)
                # If the device vanished (EIO), don’t retry the same FD—jump to reconnect.
                if "Errno 5" in msg or "Input/output error" in msg:
                    self.logger.error("Device I/O error; forcing reconnection.")
                # one reconnect mid-command
                if not attempted_reconnect:
                    attempted_reconnect = True
                    self._handle_serial_error(e, during=f"send({cmd_enum_member.name})")
                    continue
                raise ArduinoConnectionError(f"Serial error during send for {cmd_enum_member.name}: {e}") from e

            time.sleep(0.1)

        elapsed = time.time() - start_time
        raise ArduinoTimeoutError(f"Timeout after {elapsed:.1f}s waiting for response to: {command_to_send.strip()}")

    async def async_send(
        self, cmd_enum_member: PawduinoFunctions, *args
    ) -> Dict[str, Any]:
        """
        Asynchronous version of send. Sends a command to the Arduino and blocks until a
        properly formatted response (starting with OK: or ERR:) is received,
        or until the total timeout of 60 seconds is reached.
        """
        if (
            not self.connected
            or not self.configured
            or not self.ser
            or not self.ser.is_open
        ):
            self.logger.error("Async Send attempt while not connected or configured.")
            raise ArduinoConnectionError("Not connected to Arduino.")

        command_code = cmd_enum_member.value
        command_str_parts = [command_code]
        command_str_parts.extend(map(str, args))
        command_to_send = ",".join(command_str_parts) + "\n"

        self.logger.debug("Async Sending to Arduino: '%s'", command_to_send.strip())

        # Set up total timeout of 60 seconds
        start_time = time.time()
        max_total_time = 60.0  # 1 minute total timeout
        loop = asyncio.get_event_loop()
        response_str = None

        while time.time() - start_time < max_total_time:
            try:
                try:
                    await loop.run_in_executor(None, self.ser.flushInput)
                    await loop.run_in_executor(None, self.ser.flushOutput)
                except Exception as e:
                    self.logger.warning("Async: Could not flush buffers: %s", e)

                await loop.run_in_executor(
                    None, lambda: self.ser.write(command_to_send.encode())
                )

                attempt_start_time = time.time()
                attempts_remaining = True

                # Keep reading until we get a properly formatted response or timeout
                while attempts_remaining and time.time() - start_time < max_total_time:
                    raw_response_bytes = await loop.run_in_executor(
                        None, self.ser.readline
                    )

                    if not raw_response_bytes:
                        elapsed = time.time() - attempt_start_time
                        self.logger.warning(
                            "Async: No response (elapsed: %.2fs, timeout: %ss) for: %s",
                            elapsed,
                            self.read_timeout,
                            command_to_send.strip(),
                        )

                        # If we've been waiting too long for this attempt, reset and try again
                        if elapsed > self.read_timeout * 2:
                            attempts_remaining = False

                        await asyncio.sleep(0.1)
                        continue

                    response_str = raw_response_bytes.decode().strip()
                    self.logger.debug(
                        "Async Raw response: %s (elapsed: %.2fs)",
                        response_str,
                        time.time() - start_time,
                    )

                    # Only accept responses that start with OK: or ERR:
                    if response_str.startswith("OK:") or response_str.startswith(
                        "ERR:"
                    ):
                        return self._process_response(response_str, command_to_send)
                    else:
                        self.logger.warning(
                            "Async: Received malformed response: %s, continuing to wait for proper response",
                            response_str,
                        )
                        # Keep trying with the current attempt
                        await asyncio.sleep(0.1)

            except serial.SerialTimeoutException:
                self.logger.warning(
                    "Async: SerialTimeoutException (elapsed: %.2fs) for: %s",
                    time.time() - start_time,
                    command_to_send.strip(),
                )
                await asyncio.sleep(0.1)
            except serial.SerialException as e:
                self.logger.error(
                    "Async: Serial communication error (elapsed: %.2fs) for '%s': %s",
                    time.time() - start_time,
                    command_to_send.strip(),
                    e,
                    exc_info=True,
                )
                await asyncio.sleep(1)
            except IOError as e:
                self.logger.error(
                    "Async: IO error during send (elapsed: %.2fs) for '%s': %s",
                    time.time() - start_time,
                    command_to_send.strip(),
                    e,
                    exc_info=True,
                )
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(
                    "Async: Unexpected error during send (elapsed: %.2fs) for '%s': %s",
                    time.time() - start_time,
                    command_to_send.strip(),
                    e,
                    exc_info=True,
                )
                await asyncio.sleep(1)

            # Small delay before retrying
            await asyncio.sleep(0.2)

        # If we get here, we've reached the 1-minute timeout without a properly formatted response
        elapsed = time.time() - start_time
        self.logger.error(
            "Async: Total timeout exceeded (%.2f seconds) waiting for response to: %s",
            elapsed,
            command_to_send.strip(),
        )
        raise ArduinoTimeoutError(
            f"Async: Timeout after {elapsed:.1f} seconds waiting for properly formatted response for: {command_to_send.strip()}"
        )

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
                except ArduinoConnectionError as e:
                    self.logger.error("Error in Arduino monitor (Connection): %s", e)
                    self._running = False
                    break
                except Exception as e:
                    self.logger.error(
                        "Unhandled error in Arduino monitor: %s", e, exc_info=True
                    )
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
        response = await self.async_send(PawduinoFunctions.CMD_WHITE_ON)
        return response.get("success", False)

    def white_lights_on(self):
        """Turn on the white lights"""
        response = self.send(PawduinoFunctions.CMD_WHITE_ON)
        return response.get("success", False)

    def white_lights_on5(self):
        """Turn on the white lights"""
        response = self.send(PawduinoFunctions.CMD_WHITE_ON_5)
        return response.get("success", False)
    
    def white_lights_on10(self):
        """Turn on the white lights"""
        response = self.send(PawduinoFunctions.CMD_WHITE_ON_10)
        return response.get("success", False)
    
    def white_lights_on15(self):
        """Turn on the white lights"""
        response = self.send(PawduinoFunctions.CMD_WHITE_ON_15)
        return response.get("success", False)
    
    def white_lights_on25(self):
        """Turn on the white lights"""
        response = self.send(PawduinoFunctions.CMD_WHITE_ON_25)
        return response.get("success", False)
    
    def white_lights_on50(self):
        """Turn on the white lights"""
        response = self.send(PawduinoFunctions.CMD_WHITE_ON_50)
        return response.get("success", False)
    
    def white_lights_on100(self):
        """Turn on the white lights"""
        response = self.send(PawduinoFunctions.CMD_WHITE_ON_100)
        return response.get("success", False)
    
    def white_lights_off(self):
        """Turn off the white lights"""
        response = self.send(PawduinoFunctions.CMD_WHITE_OFF)
        return response.get("success", False)

    async def async_white_lights_off(self):
        """Turn off the white lights asynchronously"""
        response = await self.async_send(PawduinoFunctions.CMD_WHITE_OFF)
        return response.get("success", False)

    def curvature_lights_on(self):
        """Turn on the rb lights"""
        response = self.send(PawduinoFunctions.CMD_CONTACT_ON)
        return response.get("success", False)

    def ca_lights_on_50(self):
        """Turn on the rb lights"""
        response = self.send(PawduinoFunctions.CMD_CONTACT_ON_50)
        return response.get("success", False)
    
    def ca_lights_on_30(self):
        """Turn on the rb lights"""
        response = self.send(PawduinoFunctions.CMD_CONTACT_ON_30)
        return response.get("success", False)
    
    def ca_lights_on_20(self):
        """Turn on the rb lights"""
        response = self.send(PawduinoFunctions.CMD_CONTACT_ON_20)
        return response.get("success", False)
    
    def ca_lights_on_10(self):
        """Turn on the rb lights"""
        response = self.send(PawduinoFunctions.CMD_CONTACT_ON_10)
        return response.get("success", False)
    
    def ca_lights_on_5(self):
        """Turn on the rb lights"""
        response = self.send(PawduinoFunctions.CMD_CONTACT_ON_5)
        return response.get("success", False)

    async def async_curvature_lights_on(self):
        """Turn on the rb lights asynchronously"""
        response = await self.async_send(PawduinoFunctions.CMD_CONTACT_ON)
        return response.get("success", False)

    def curvature_lights_off(self):
        """Turn off the rb lights"""
        response = self.send(PawduinoFunctions.CMD_CONTACT_OFF)
        return response.get("success", False)

    async def async_curvature_lights_off(self):
        """Turn off the rb lights asynchronously"""
        response = await self.async_send(PawduinoFunctions.CMD_CONTACT_OFF)
        return response.get("success", False)

    def no_cap(self):
        """Engage the decapper"""
        response = self.send(PawduinoFunctions.CMD_EMAG_ON)
        time.sleep(0.5)
        return response.get("success", False)

    async def async_no_cap(self):
        """Engage the decapper asynchronously"""
        response = await self.async_send(PawduinoFunctions.CMD_EMAG_ON)
        await asyncio.sleep(0.5)
        return response.get("success", False)

    def ALL_CAP(self):
        """Disengage the decapper"""
        response = self.send(PawduinoFunctions.CMD_EMAG_OFF)
        time.sleep(1.5)
        return response.get("success", False)

    async def async_ALL_CAP(self):
        """Disengage the decapper asynchronously"""
        response = await self.async_send(PawduinoFunctions.CMD_EMAG_OFF)
        await asyncio.sleep(1.5)
        return response.get("success", False)

    def line_break(self) -> Optional[bool]:
        """Check if the capper line is broken (cap is present)"""
        response = self.send(PawduinoFunctions.CMD_LINE_BREAK)
        if response.get("success"):
            parsed = response.get("parsed_data", {})
            data_val = parsed.get("value1")
            if data_val == 1:
                return True
            elif data_val == 0:
                return False
            else:
                self.logger.warning(
                    "line_break: successful response but unexpected data: %s in %s",
                    data_val,
                    response,
                )
                return None
        return None

    async def async_line_break(self) -> Optional[bool]:
        """
        Check if the capper line is broken (cap is present) asynchronously
        Returns True if the line is broken, False if it is not, and None if there was an error or unexpected data.
        """
        response = await self.async_send(PawduinoFunctions.CMD_LINE_BREAK)
        if response.get("success"):
            parsed = response.get("parsed_data", {})
            data_val = parsed.get("value1")
            if data_val == 1:
                return True
            elif data_val == 0:
                return False
            else:
                self.logger.warning(
                    "async_line_break: successful response but unexpected data: %s in %s",
                    data_val,
                    response,
                )
                return None
        return None

    def line_test(self):
        """
        Trigger the line break test.
        NOTE: This command sends multiple responses. The current send/receive
        logic is designed for single request/response. This method needs
        a dedicated implementation or a change in Arduino sketch behavior.
        """
        self.logger.warning(
            "line_test sends multiple responses, which is not fully supported by the current 'send' method pattern."
        )
        response = self.send(PawduinoFunctions.CMD_LINE_TEST)
        print(f"Initial response to CMD_LINE_TEST: {response}")
        raise NotImplementedError(
            "line_test requires multi-response handling not yet implemented in send/receive."
        )

    def _parse_arduino_response_content(
        self, content: str, command_str: str = "Unknown Command"
    ) -> Dict[str, Any]:
        """
        Parses the content part of an Arduino response (after OK: or ERR:).
        Tries to parse as JSON-like ({key:val,...}), then as simple key:value pairs,
        then as comma-separated values if it's just a list of numbers.

        Arguments:
            content: The content string to parse
            command_str: The command string that was sent (for logging)

        Returns:
            A dictionary with parsed key-value pairs or a list of values.

        Raises:
            ValueError: If the content cannot be parsed.
        """
        parsed: Dict[str, Any] = {}
        content = content.strip()

        if not content:
            return parsed

        if content.startswith("{") and content.endswith("}"):
            try:
                inner_content = content[1:-1].strip()
                if inner_content:
                    pairs = inner_content.split(",")
                    for i, part in enumerate(pairs):
                        if ":" not in part:
                            if len(pairs) == 1:
                                parsed[f"value{i + 1}"] = self._auto_convert_type(
                                    part.strip()
                                )
                            else:
                                parsed[f"item{i + 1}"] = part.strip()
                            continue

                        key, value_str = part.split(":", 1)
                        key = key.strip().strip('"')
                        value_str = value_str.strip().strip('"')

                        if value_str.startswith("[") and value_str.endswith("]"):
                            raw_values = value_str[1:-1].split(",")
                            try:
                                num_values = [
                                    self._auto_convert_type(v.strip())
                                    for v in raw_values
                                ]
                                parsed[key] = (
                                    num_values
                                    if len(num_values) > 1
                                    else num_values[0]
                                    if num_values
                                    else []
                                )
                                if key.lower() in ["v", "values", "data"]:
                                    for i_val, num_val in enumerate(num_values):
                                        parsed[f"value{i_val + 1}"] = num_val
                            except ValueError:
                                parsed[key] = [v.strip() for v in raw_values]
                                if key.lower() in ["v", "values", "data"]:
                                    for i_val, str_val in enumerate(
                                        [v.strip() for v in raw_values]
                                    ):
                                        parsed[f"value_str{i_val + 1}"] = str_val
                        else:
                            parsed[key] = self._auto_convert_type(value_str)
                return parsed
            except Exception as e:
                self.logger.warning(
                    "Could not parse JSON-like content '%s' for command '%s': %s. Treating as raw data.",
                    content,
                    command_str,
                    e,
                )
                parsed["raw_value"] = content
                return parsed

        parts = content.split(",")
        if len(parts) > 1:
            all_convertible = True
            converted_values = []
            for part_val in parts:
                try:
                    converted_values.append(self._auto_convert_type(part_val.strip()))
                except ValueError:
                    all_convertible = False
                    break
            if all_convertible:
                for i, val in enumerate(converted_values):
                    parsed[f"value{i + 1}"] = val
                return parsed

        try:
            parsed["value1"] = self._auto_convert_type(content)
        except ValueError:
            parsed["raw_value"] = content

        return parsed

    def _auto_convert_type(self, value_str: str) -> Any:
        """Tries to convert a string to int, then float, otherwise returns string."""
        value_str = value_str.strip()
        if not value_str:
            return value_str
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False
        try:
            return int(value_str)
        except ValueError:
            try:
                return float(value_str)
            except ValueError:
                return value_str

    def _process_response(
        self, response_str: str, command_to_send: str
    ) -> Dict[str, Any]:
        """
        Process the response string from the Arduino and return a standardized result dictionary.

        Args:
            response_str: The response string from the Arduino
            command_to_send: The command that was sent

        Returns:
            Dict: A dictionary with the processed response data
        """
        self.logger.debug("Processing response: '%s'", response_str)

        parsed_result: Dict[str, Any] = {
            "success": False,
            "raw_data": "",
            "parsed_data": {},
            "error_message": "",
        }

        if response_str.startswith("OK:"):
            parsed_result["success"] = True
            content = response_str[3:]
            parsed_result["raw_data"] = content
            parsed_result["parsed_data"] = self._parse_arduino_response_content(
                content, command_to_send.strip()
            )
        elif response_str.startswith("ERR:"):
            parsed_result["success"] = False
            error_content = response_str[4:]
            parsed_result["raw_data"] = error_content
            parsed_result["error_message"] = error_content
            parsed_result["parsed_data"] = self._parse_arduino_response_content(
                error_content, command_to_send.strip()
            )
            self.logger.error(
                "Arduino returned error: %s for command %s",
                error_content,
                command_to_send.strip(),
            )
        else:
            self.logger.error(
                "Unexpected response format from Arduino: '%s' for command '%s'",
                response_str,
                command_to_send.strip(),
            )
            parsed_result["success"] = False
            parsed_result["raw_data"] = response_str
            parsed_result["error_message"] = "Unexpected response format"
            parsed_result["parsed_data"] = self._parse_arduino_response_content(
                response_str, command_to_send.strip()
            )

        if not parsed_result["success"] and not parsed_result["error_message"]:
            parsed_result["error_message"] = (
                f"Command '{command_to_send.strip()}' failed with response: {response_str}"
            )

        return parsed_result

    def home(self) -> bool:
        """
        Home the pipette.

        Returns:
            bool: True if homing was successful
        """
        response = self.send(PawduinoFunctions.CMD_PIPETTE_HOME)
        return response.get("success", False)

    def prime(self) -> bool:
        """
        Prime the pipette, by moving to the 0 volume position
        """
        response = self.move_to()
        return response.get("success", False)

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the pipette (homed, position, max_volume).

        Returns:
            Dict:
            A dictionary with status info, e.g.,
            {'success': True, 'homed': True, 'position': 10.5, 'max_volume': 200.0}
            Returns {'success': False} on error.
        """
        response = self.send(PawduinoFunctions.CMD_PIPETTE_STATUS)
        status_data: Dict[str, Any] = {"success": False}

        if response.get("success"):
            parsed = response.get("parsed_data", {})
            if "homed" in parsed and "pos" in parsed and "max_vol" in parsed:
                try:
                    status_data["success"] = True
                    status_data["homed"] = bool(parsed["homed"])
                    status_data["position"] = float(parsed["pos"])
                    status_data["max_volume"] = float(parsed["max_vol"])
                except (ValueError, TypeError) as e:
                    self.logger.error(
                        "Error parsing numeric status values %s: %s", parsed, e
                    )
                    status_data["success"] = False
                    status_data["error_message"] = "Failed to parse status values"
            elif "value1" in parsed and "value2" in parsed and "value3" in parsed:
                try:
                    status_data["success"] = True
                    status_data["homed"] = bool(parsed["value1"])
                    status_data["position"] = float(parsed["value2"])
                    status_data["max_volume"] = float(parsed["value3"])
                except (ValueError, TypeError) as e:
                    self.logger.error(
                        "Error parsing status from parsed_csv %s: %s", parsed, e
                    )
                    status_data["success"] = False
                    status_data["error_message"] = "Failed to parse CSV status values"
            else:
                self.logger.warning(
                    "Could not determine pipette status from successful response: %s",
                    response,
                )
                status_data["error_message"] = "Unexpected status format"
        else:
            status_data["error_message"] = response.get(
                "error_message", "Failed to get status"
            )

        return status_data

    def move_to(self, position: float, speed: Optional[int] = None) -> Dict[str, Any]:
        """
        Move to a specific position in mm.

        Args:
            position: Position in mm
            speed: Movement speed (steps/second) (optional)

        Returns:
            Dict: Response dictionary containing success status.
        """
        if speed is not None:
            response = self.send(PawduinoFunctions.CMD_PIPETTE_MOVE_TO, position, speed)
        else:
            response = self.send(PawduinoFunctions.CMD_PIPETTE_MOVE_TO, position)
        return response

    def move_relative(
        self, direction: int, steps: int, velocity: int
    ) -> Dict[str, Any]:
        """
        Move the pipette by a relative number of steps.
        Args:
            direction: 0 or 1
            steps: number of steps
            velocity: steps per second
        Returns:
            Dict: Response dictionary containing success status.
        """
        response = self.send(
            PawduinoFunctions.CMD_MOVE_RELATIVE, direction, steps, velocity
        )
        return response

    def aspirate(self, volume: float, rate: Optional[float] = None) -> Dict[str, Any]:
        """
        Aspirate a specific volume in µL.

        Args:
            volume: Volume to aspirate in µL
            rate: Aspiration rate in µL/s (optional)

        Returns:
            Dict[str, Any]: Response dictionary containing success status and any additional data.
        """
        if rate is not None:
            response = self.send(PawduinoFunctions.CMD_PIPETTE_ASPIRATE, volume, rate)
        else:
            response = self.send(PawduinoFunctions.CMD_PIPETTE_ASPIRATE, volume)
        return response

    def dispense(self, volume: float, rate: Optional[float] = None) -> Dict[str, Any]:
        """
        Dispense a specific volume in µL.

        Args:
            volume: Volume to dispense in µL
            rate: Dispensing rate in µL/s (optional)

        Returns:
            Dict: Response dictionary containing success status and any additional data.
        """
        if rate is not None:
            response = self.send(PawduinoFunctions.CMD_PIPETTE_DISPENSE, volume, rate)
        else:
            response = self.send(PawduinoFunctions.CMD_PIPETTE_DISPENSE, volume)
        return response
    
    def mix(self, repetitions: int, volume: float, rate: Optional[float] = None) -> Dict[str, Any]:
        """
        Mix in place by plunger oscillation.

        Args:
            repetitions: Number of mix cycles
            volume: Stroke volume in µL (peak-to-peak per cycle)
            rate: Optional; ignored if None. If set, it’s passed directly to firmware.

        Returns:
            Dict: Response from firmware
        """
        if rate is not None:
            # Pass directly to firmware (firmware will interpret as steps/sec)
            response = self.send(PawduinoFunctions.CMD_PIPETTE_MIX,
                                repetitions, volume, rate)
        else:
            # Don’t send a rate arg → firmware uses its default
            response = self.send(PawduinoFunctions.CMD_PIPETTE_MIX,
                                repetitions, volume)
        return response

    def hello(self) -> bool:
        """Send a hello message to the Arduino and check response"""
        response = self.send(PawduinoFunctions.CMD_HELLO)
        if response.get("success"):
            expected_msg = PawduinoReturnCodes.RESP_HELLO.value.split(":", 1)[1]
            return expected_msg in response.get("raw_data", "")
        return False

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

    def __init__(
        self,
        port_address: str = "/dev/ttyUSB0",
        baud_rate: int = 115200,
        read_timeout: float = 2.0,
        max_retries: int = 3,
    ):
        self.ser: Serial = None
        self.port_address: Optional[str] = port_address
        self.baud_rate: int = baud_rate
        self.read_timeout: float = read_timeout  # Timeout for serial read operations
        self.max_retries: int = max_retries  # Max retries for sending a command
        self.configured: bool = False
        self.connected: bool = False
        self._monitor_task = None
        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self.pipette_active = True  # Assuming pipette is active by default
        self.logger = logging.getLogger("panda")
        self.connect()

    def connect(self):
        self.connected = True
        self.configured = True
        self.logger.info("MockArduinoLink connect() called - already mock connected.")

    def close(self):
        self.connected = False
        self.configured = False
        self.logger.info("MockArduinoLink close() called.")

    def send(self, cmd_enum_member: PawduinoFunctions, *args) -> Dict[str, Any]:
        """Mock send method. Returns a predefined response based on the command."""
        cmd_value = cmd_enum_member.value
        self.logger.debug("Mock Sending: %s with args %s", cmd_enum_member.name, args)

        response: Dict[str, Any] = {
            "success": True,
            "raw_data": "",
            "parsed_data": {},
            "error_message": "",
        }

        if cmd_value == PawduinoFunctions.CMD_HELLO.value:
            response["raw_data"] = PawduinoReturnCodes.RESP_HELLO.value.split(":", 1)[1]
            response["parsed_data"] = self._parse_arduino_response_content(
                response["raw_data"], cmd_enum_member.name
            )
        elif cmd_value == PawduinoFunctions.CMD_WHITE_ON.value:
            response["raw_data"] = "White lights on"
        elif cmd_value == PawduinoFunctions.CMD_WHITE_OFF.value:
            response["raw_data"] = "White lights off"
        elif cmd_value == PawduinoFunctions.CMD_CONTACT_ON.value:
            response["raw_data"] = "Contact lights on"
        elif cmd_value == PawduinoFunctions.CMD_CONTACT_OFF.value:
            response["raw_data"] = "Contact lights off"
        elif cmd_value == PawduinoFunctions.CMD_EMAG_ON.value:
            response["raw_data"] = "Electromagnet on"
        elif cmd_value == PawduinoFunctions.CMD_EMAG_OFF.value:
            response["raw_data"] = "Electromagnet off"
        elif cmd_value == PawduinoFunctions.CMD_LINE_BREAK.value:
            response["raw_data"] = '{"value1":1}'
            response["parsed_data"] = {"value1": 1}
        elif cmd_value == PawduinoFunctions.CMD_LINE_TEST.value:
            response["raw_data"] = "Line test initiated"
        elif cmd_value == PawduinoFunctions.CMD_PIPETTE_HOME.value:
            response["raw_data"] = "Pipette homed"
        elif cmd_value == PawduinoFunctions.CMD_PIPETTE_MOVE_TO.value:
            response["raw_data"] = f"Moved to {args[0]}"
        elif cmd_value == PawduinoFunctions.CMD_PIPETTE_ASPIRATE.value:
            response["raw_data"] = f"Aspirated {args[0]}"
        elif cmd_value == PawduinoFunctions.CMD_PIPETTE_DISPENSE.value:
            response["raw_data"] = f"Dispensed {args[0]}"
        elif cmd_value == PawduinoFunctions.CMD_PIPETTE_MIX.value:
            response["raw_data"] = f"Mixed {args[0]} times, volume {args[1]}"
        elif cmd_value == PawduinoFunctions.CMD_PIPETTE_STATUS.value:
            status_str = "{homed:1,pos:10.0,max_vol:200.0}"
            response["raw_data"] = status_str
            response["parsed_data"] = {"homed": True, "pos": 10.0, "max_vol": 200.0}
        else:
            response["success"] = False
            response["raw_data"] = "Unknown command"
            response["error_message"] = "Mock: Unknown command"

        if response["success"] and not response["parsed_data"] and response["raw_data"]:
            response["parsed_data"] = self._parse_arduino_response_content(
                response["raw_data"], cmd_enum_member.name
            )

        return response

    def receive(self):
        if not self.arduinoQueue.empty():
            return self.arduinoQueue.get()
        return None

    async def async_receive(self):
        if not self.arduinoQueue.empty():
            return self.arduinoQueue.get_nowait()
        return None

    async def async_send(
        self, cmd_enum_member: PawduinoFunctions, *args
    ) -> Dict[str, Any]:
        """Mock async send method"""
        return self.send(cmd_enum_member, *args)

    async def async_line_break(self) -> Optional[bool]:
        return await self.async_send(PawduinoFunctions.CMD_LINE_BREAK)


class AsyncMockArduinoLink(MockArduinoLink):
    """Mock version of ArduinoLink that supports async operations"""

    async def async_send(
        self, cmd_enum_member: PawduinoFunctions, *args
    ) -> Dict[str, Any]:
        """Async version of send for AsyncMock"""
        return super().send(cmd_enum_member, *args)

    # Add async versions of all other methods from MockArduinoLink if they need
    # to differ from just calling the sync version or if specific async mock logic is needed.
    # For now, most will inherit the MockArduinoLink's behavior which calls the sync send.


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

        await arduino.start_monitoring()

        for function in PawduinoFunctions:
            print(f"Sending '{function.name}' to the Arduino")
            response = await arduino.async_send(function.value)
            print(f"Arduino says: {response}")

        await arduino.stop_monitoring()

        print("All tests passed")
    finally:
        arduino.close()


def run_async_test():
    """Run the async test in an event loop"""
    asyncio.run(async_test_of_pawduino())
