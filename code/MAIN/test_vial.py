from classes import Vial

# Create an instance of a vial
test_x_coord = 0
test_y_coord = -100
Sol1 = Vial(0,-100,'water',0.1)

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
    print('X-coordinates do not match')
    passing = False
    

if test_y_coord == coords['y']:
    print('Y-coordinates match')
else:
    print('Y-coordinates do not match')
    passing = False
    
print(coords)


# test updating the voluem
try:
    print('\n\nCurrent volume: ',Sol1.volume)
    # No exception should raise
    volume_to_add = 0.05
    print(f'Current depth: {Sol1.depth}')
    print('Adding ',volume_to_add)
    Sol1.update_volume(volume_to_add)
    print('new volume: ',Sol1.volume)
    print(f'new depth: {Sol1.depth}')
except Exception as e:
    print(e)

try:
    print('\nAttempt to overfill:')
    volume_to_add = 0.1
    print('Adding ',volume_to_add)
    Sol1.update_volume(volume_to_add)
    print('Current volume: ',Sol1.volume)

except Exception as e:
    print(e)

try:
    print('\nAttempt to over draft:')
    volume_to_add = -0.2
    print('Adding ',volume_to_add)
    Sol1.update_volume(volume_to_add)
    print('Current volume: ',Sol1.volume)

except Exception as e:
    print(e)

