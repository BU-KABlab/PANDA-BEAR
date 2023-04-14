from classes import Vial, Wells

v1 = Vial(10, 10, -30, "water", 100)
v2 = Vial(10, 20, -30, 'bleach',150)
well_plate = Wells()
print(f'Well A1 coordinates {well_plate.get_coordinates("A1")}')