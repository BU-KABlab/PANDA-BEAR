# import unittest
# from unittest.mock import patch
# import __init__ as pawduino

# class TestArduinoCommunication(unittest.TestCase):
#     @patch('serial.Serial')
#     def test_communicate_with_arduino(self, mock_serial):
#         # Set up the mock serial port
#         mock_serial_instance = mock_serial.return_value
#         mock_serial_instance.read.return_value = b'response from arduino'
#         mock_serial_instance.write.return_value = 5

#         # Call the function you want to test
#         response = pawduino('command to send')

#         # Assert the expected behavior
#         mock_serial.assert_called_with('/dev/ttyUSB0', 9600)
#         mock_serial_instance.write.assert_called_with(b'command to send')
#         self.assertEqual(response, 'response from arduino')


# if __name__ == '__main__':
#     unittest.main()

from . import ArduinoLink

with ArduinoLink(port_address=None) as arduino:
    print("Sending 'Hello' to the Arduino")
    print(f'Arduino says: {arduino.send("Hello")}')


