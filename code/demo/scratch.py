from classes import Vial, Wells

v1 = Vial(-10, -10, -10, -30, "water", 100)
v2 = Vial(-10, -20, -10, -30, 'bleach',150)
well_plate = Wells()
print(f'Well A1 coordinates {well_plate.get_coordinates("A1")}')
print(f'Well B6 coordinates {well_plate.get_coordinates("B6")}')
v1_coords = v1.position
print(v1_coords)
mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
command = mill_move.format(v1.position['x'],v1.position['y'],v1.position['z'])
print(command)
