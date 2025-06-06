import serial
import time
import logging
import threading

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
            return True
        except Exception as e:
            logger.error(f"Error connecting to scale: {e}")
            self.connected = False
            return False
    
    def get(self):
        """Get current weight from scale."""
        with self._lock:
            if not self.connected and not self.connect():
                return 0.0
                
            try:
                # Clear buffer
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)
                
                # Send immediate weight request command
                self.ser.write(b'SI\r\n')
                
                # Wait for response
                time.sleep(0.5)
                
                if self.ser.in_waiting:
                    response = self.ser.read(self.ser.in_waiting)
                    logger.debug(f"Raw response: {response.hex()}")
                    
                    # Parse based on test observations
                    if response and len(response) >= 3 and response[0] == 0x06:
                        # Based on your test data, the first byte after ACK might contain weight info
                        # Extract value and scale it - you may need to adjust this parsing logic
                        value = int.from_bytes(response[1:3], byteorder='big')
                        # Try a few different scaling factors
                        weight = value / 100.0  # Adjust scaling factor as needed
                        
                        logger.debug(f"Parsed weight: {weight}g (raw value: {value})")
                        self._weight = weight
                        return weight
                    else:
                        # If we got a response but couldn't parse it
                        logger.warning(f"Received response but couldn't parse weight: {response.hex()}")
                        
                # If we reach here, we couldn't get a valid reading
                logger.warning("No valid weight reading obtained")
                return self._weight  # Return last known weight
                
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
                
                # Try ESC T command for taring
                self.ser.write(b'\x1bT\r\n')
                time.sleep(1)
                
                if self.ser.in_waiting:
                    response = self.ser.read(self.ser.in_waiting)
                    logger.debug(f"Tare response: {response.hex()}")
                
                # Also try Z command as an alternative
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