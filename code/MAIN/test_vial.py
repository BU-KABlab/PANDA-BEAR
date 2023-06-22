from classes import Vial

# Create an instance of a vial
test_x_coord = 0
test_y_coord = -100
Sol1 = Vial(0,-100,'water',0.01)

# Test fetching all attributes
coords = Sol1.coordinates
bottom = Sol1.bottom
contents = Sol1.contents
capcaity = Sol1.capacity 
radius = Sol1.radius
height = Sol1.height
current_volume = Sol1.volume
base = Sol1.base
depth = Sol1.depth 

passing = True
# Do coordinates match the input?
if test_x_coord == coords['x']:
    print('X-coordinates match')
else:
    passing = False
    

if test_y_coord == coords['y']:
    print('Y-coordinates match')
else:
    passing = False



