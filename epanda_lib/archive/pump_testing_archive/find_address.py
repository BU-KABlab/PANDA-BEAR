import serial

class Port:
    """Port a pump is connected to."""
    
    BAUD_RATE_DEFAULT = 19200
    """Default baud rate."""

    class Unavailability(Exception):
        """Exception that indicates the unavailability of a port."""
        pass
    
    def __init__(self, name: str, baud_rate: int = BAUD_RATE_DEFAULT) -> None:
        """
        Constructs a port.
        
        :param name: 
            Name of the port.
        :param baud_rate: 
            Baud rate at which data is exchanged via the port.
        
        :raises ValueError: 
            Baud rate invalid.
        :raises Unavailability: 
            Port unavailable (e.g. in use or not connected).
        """
        try:
            self.__serial = serial.Serial(
                port=name,
                baudrate=baud_rate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=10)
        
        except ValueError:
            raise ValueError('Baud rate invalid.')
        except serial.SerialException:
            raise Port.Unavailability()
    
    def _transmit(self, data: bytes) -> None:
        """
        Transmits data to the port.
        
        :param data: 
            Data to transmit.
        """
        self.__serial.write(data)
    
    def _receive(self, data_length: int) -> bytes:
        """
        Receives data from the port.
        
        :param data_length: 
            Length of the data to receive.
        """
        return self.__serial.read(16)
    
    @property
    def _waiting_transmit(self) -> int:
        """Gets the length of data waiting to be transmitted."""
        return self.__serial.out_waiting
    
    @property
    def _waiting_receive(self) -> int:
        """Gets the length of data waiting to be received."""
        return self.__serial.in_waiting
    
    def get_address(self) -> str:
     # Send the "A?" command to the pump
     self._transmit(b'\ADR\r')
     print('Sent: ADR')
     
     # Read the response from the pump
     response = self._receive(1)
     print('Received:', response)
     
     # Convert the response to a string and return it
     return response.decode('utf-8')


port = Port('/dev/ttyUSB0', 19200)  # Replace with the name of your serial port
address = port.get_address()  # Get the pump address
print('The pump address is:', address)
