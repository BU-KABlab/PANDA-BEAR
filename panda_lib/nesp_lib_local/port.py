"""
port.py
For handling serial ports.

MIT License:
Copyright (c) 2021 Florian Lapp

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import serial

class Port :
    """Port a pump is connected to."""

    BAUD_RATE_DEFAULT = 9_600
    """Default baud rate."""

    class Unavailability(Exception) :
        """Exception that indicates the unavailability of a port."""
        pass

    def __init__(self, name : str, baud_rate : int = BAUD_RATE_DEFAULT) -> None :
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
        try :
            self.__serial = serial.Serial(
                port = name,
                baudrate = baud_rate
            )
        except ValueError :
            raise ValueError('Baud rate invalid.')
        except serial.SerialException :
            raise Port.Unavailability()

    def _transmit(self, data : bytes) -> None :
        """
        Transmits data to the port.

        :param data:
            Data to transmit.
        """
        self.__serial.write(data)

    def _receive(self, data_length : int) -> bytes :
        """
        Receives data from the port.

        :param data_length:
            Length of the data to receive.
        """
        return self.__serial.read(data_length)

    @property
    def _waiting_transmit(self) -> int :
        """Gets the length of data waiting to be transmitted."""
        return self.__serial.out_waiting

    @property
    def _waiting_receive(self) -> int :
        """Gets the length of data waiting to be received."""
        return self.__serial.in_waiting