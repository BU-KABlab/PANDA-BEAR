from classes import Vial, Wells, MillControl
import serial

v1 = Vial(-10, -10, -10, -30, "water", 100)
v2 = Vial(-10, -20, -10, -30, 'bleach',150)


wells = Wells(a1_X = -300, a1_Y =-200, orientation=1)  # Choose the desired orientation
wells.print_well_coordinates_table()
wells.visualize_well_coordinates()

#v1_coords = v1.position
#print(v1_coords)
#mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
#command = mill_move.format(v1.position['x'],v1.position['y'],v1.position['z'])
#print(command)
def SET_UP_MILL():
    ser_mill = serial.Serial(
        port= 'COM4',
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
        )
    return ser_mill
serial_mill = SET_UP_MILL()
mill = MillControl(serial_mill)
mill.__enter__
mill.home
