from EdepDemo import move_electrode_to_position, move_pipette_to_position, read_vials, read_instructions
from classes import Wells, MillControl, Vial

mill = MillControl()
wellplate = Wells(-218, -74, 0, 0)
## Set up solutions
waste_vials = read_vials('wasteParameters_08_07_23.json')
stock_vials = read_vials('vialParameters_08_07_23.json')
# Move pipette to position
#move_pipette_to_position(mill, waste_vials[0].coordinates['x'], waste_vials[0].coordinates['y'], 0)

#move_pipette_to_position(mill, wellplate.get_coordinates('H1')['x'], wellplate.get_coordinates('H1')['y'],0)
#move_pipette_to_position(mill, wellplate.get_coordinates('H1')['x'], wellplate.get_coordinates('H1')['y'],-100)

# Move electrode to position
move_electrode_to_position(mill, wellplate.get_coordinates('D11')['x'], wellplate.get_coordinates('D11')['y'],0)
move_electrode_to_position(mill, wellplate.get_coordinates('D11')['x'], wellplate.get_coordinates('D11')['y'],wellplate.echem_height)
        