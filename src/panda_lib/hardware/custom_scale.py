import serial
import time
import logging
import threading
import struct

logger = logging.getLogger("panda.scale")

class CustomScale:
    """Custom implementation for Sartorius scale using direct serial communication."""
    
    def __init__(self, port="/dev/ttyUSB0", baudrate=19200, timeout=1):
        """Initialize scale connection."""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.connected = False
        self._weight = 0.0
        self._lock = threading.Lock()
        
        # Connect to scale
        self.connect()
        
    def connect(self):
        """Establish connection to scale."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            
            # Clear buffer
            if self.ser.in_waiting:
                self.ser.read(self.ser.in_waiting)
                
            self.connected = True
            logger.info(f"Connected to scale at {self.port}")
            
            # Initialize the scale
            self._initialize_scale()
            
            return True
        except Exception as e:
            logger.error(f"Error connecting to scale: {e}")
            self.connected = False
            return False
    
    def _initialize_scale(self):
        """Send initialization commands to the scale."""
        try:
            # Reset communication
            self.ser.write(b'\x1bR\r\n')
            time.sleep(0.5)
            if self.ser.in_waiting:
                response = self.ser.read(self.ser.in_waiting)
                logger.debug(f"Reset response: {response.hex()}")
            
            # Try different modes and formats
            commands = [
                (b'\x1bP\r\n', "Switch to print mode"),
                (b'\x1bZ\r\n', "Switch to continuous mode"),
                (b'\x1bK\r\n', "Toggle continuous mode"),
                (b'\x1bL\r\n', "Set data output format")
            ]
            
            for cmd, desc in commands:
                logger.debug(f"Sending {desc}")
                self.ser.write(cmd)
                time.sleep(0.5)
                if self.ser.in_waiting:
                    response = self.ser.read(self.ser.in_waiting)
                    logger.debug(f"{desc} response: {response.hex()}")
            
        except Exception as e:
            logger.error(f"Error initializing scale: {e}")
    
    def get(self):
        """Get current weight from scale."""
        with self._lock:
            if not self.connected and not self.connect():
                return 0.0
                
            try:
                # Clear buffer
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)
                
                # Try different commands to see which ones return changing data
                commands = [
                    (b'SI\r\n', "Send Immediate"),
                    (b'P\r\n', "Print"),
                    (b'\x1bP\r\n', "ESC P command")
                ]
                
                for cmd, desc in commands:
                    logger.debug(f"Trying {desc} command")
                    self.ser.write(cmd)
                    time.sleep(0.5)
                    
                    if self.ser.in_waiting:
                        response = self.ser.read(self.ser.in_waiting)
                        logger.debug(f"{desc} response: {response.hex()}")
                        
                        # Try different parsing methods
                        if response and len(response) >= 4:
                            # Attempt different parsing strategies
                            
                            # Method 1: First two bytes after ACK
                            if response[0] == 0x06:
                                method1 = int.from_bytes(response[1:3], byteorder='big')
                                logger.debug(f"Method 1 (bytes 1-3): {method1}")
                            
                            # Method 2: Second and third bytes
                            if len(response) >= 4:
                                method2 = int.from_bytes(response[2:4], byteorder='big')
                                logger.debug(f"Method 2 (bytes 2-4): {method2}")
                            
                            # Method 3: Try to interpret as IEEE float (4 bytes)
                            if len(response) >= 5:
                                try:
                                    # Try big-endian
                                    method3_be = struct.unpack('>f', response[1:5])[0]
                                    logger.debug(f"Method 3 BE (bytes 1-5): {method3_be}")
                                    
                                    # Try little-endian
                                    method3_le = struct.unpack('<f', response[1:5])[0]
                                    logger.debug(f"Method 3 LE (bytes 1-5): {method3_le}")
                                except:
                                    pass
                            
                            # Method 4: Each byte as its own value
                            for i, b in enumerate(response):
                                logger.debug(f"Byte {i}: {b} (decimal), 0x{b:02x} (hex)")
                
                # Try one more direct approach
                self.ser.write(b'SI\r\n')
                time.sleep(0.5)
                
                if self.ser.in_waiting:
                    response = self.ser.read(self.ser.in_waiting)
                    logger.debug(f"Final response: {response.hex()}")
                    
                    # For now, use a placeholder weight
                    # After running the debug above, you'll find which parsing method works
                    self._weight = 0.0
                    return self._weight
                else:
                    logger.warning("No response received from scale")
                    return self._weight
                    
            except Exception as e:
                logger.error(f"Error getting weight: {e}")
                return self._weight
    
    def tare(self):
        """Zero the scale."""
        with self._lock:
            if not self.connected and not self.connect():
                return False
                
            try:
                # Clear buffer
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)
                
                # Try both tare commands
                self.ser.write(b'\x1bT\r\n')
                time.sleep(1)
                
                if self.ser.in_waiting:
                    response = self.ser.read(self.ser.in_waiting)
                    logger.debug(f"Tare response: {response.hex()}")
                
                self.ser.write(b'Z\r\n')
                time.sleep(1)
                
                if self.ser.in_waiting:
                    response = self.ser.read(self.ser.in_waiting)
                    logger.debug(f"Z command response: {response.hex()}")
                
                # Reset internal weight
                self._weight = 0.0
                return True
                
            except Exception as e:
                logger.error(f"Error taring scale: {e}")
                return False
    
    def disconnect(self):
        """Close connection to scale."""
        with self._lock:
            if self.ser and self.connected:
                self.ser.close()
                self.connected = False
                logger.info("Disconnected from scale")