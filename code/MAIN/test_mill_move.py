#from EdepDemo import  read_vials
from classes import Wells, MillControl
import gamrycontrol as echem
import Analyzer as analyzer
"""
Run this file using the debug python file option to establish a connection to the mill and be able to send commands via the debug console.

You can then run the following commands in the debug console to move the pipette and electrode to the desired positions:
move_center_to_position(mill, x, y, z)
move_electrode_to_position(mill, x, y, z)
move_pipette_to_position(mill, x, y, z)

Because this script reads in the wellplate and vials you can also try sending a tool to one of these objects. For example:
move_pipette_to_position(mill, wellplate.get_coordinates('H1')['x'], wellplate.get_coordinates('H1')['y'],0)

"""
def main():
    mill = MillControl()
    wellplate = Wells(-218, -74, 0, 0)
    ## Set up solutions
#    waste_vials = read_vials('wasteParameters_08_07_23.json')
#    stock_vials = read_vials('vialParameters_08_07_23.json')

    ## pause for user input
    input("Press Enter to end...")
    return 0


def move_center_to_position(mill: object, x, y, z):
    """
    Move the mill to the specified coordinates.
    Args:
        coordinates (dict): Dictionary containing x, y, and z coordinates.
    Returns:
        str: Response from the mill after executing the command.
    """
    offsets = {"x": 0, "y": 0, "z": 0}

    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(x + offsets["x"], y + offsets["y"], z + offsets["z"])
    mill.execute_command(command)
    return 0


## TODO Add a diagnoal move check to move pipette to position and move electrode to position functions


def move_pipette_to_position(
    mill: object,
    x,
    y,
    z=0.00,
):
    """
    Move the pipette to the specified coordinates.
    Args:
        x (float): X coordinate.
        y (float): Y coordinate.
        z (float): Z coordinate.
    Returns:
        str: Response from the mill after executing the command.
    """
    offsets = {"x": -92, "y": -4, "z": 0}

    mill_move = "G0 X{} Y{} Z{}"  # move to specified coordinates
    command = mill_move.format(
        x + offsets["x"], y + offsets["y"], z + offsets["z"]
    )  # x-coordinate has 92 mm offset for pipette location
    mill.execute_command(str(command))
    return 0


def move_electrode_to_position(mill: object, x, y, z):
    """
    Move the electrode to the specified coordinates.
    Args:
        coordinates (dict): Dictionary containing x, y, and z coordinates.
    Returns:
        str: Response from the mill after executing the command.
    """
    offsets = {"x": 33, "y": 30, "z": 0}
    # move to specified coordinates
    mill_move = "G0 X{} Y{} Z{}"
    command = mill_move.format(x + offsets["x"], y + offsets["y"], z + offsets["z"])
    mill.execute_command(str(command))
    return 0


# Move pipette to position
#move_pipette_to_position(mill, waste_vials[0].coordinates['x'], waste_vials[0].coordinates['y'], 0)

#move_pipette_to_position(mill, wellplate.get_coordinates('H1')['x'], wellplate.get_coordinates('H1')['y'],0)
#move_pipette_to_position(mill, wellplate.get_coordinates('H1')['x'], wellplate.get_coordinates('H1')['y'],-100)

# Move electrode to position
#move_electrode_to_position(mill, wellplate.get_coordinates('F2')['x'], wellplate.get_coordinates('F2')['y'],0)
#move_electrode_to_position(mill, wellplate.get_coordinates('F2')['x'], wellplate.get_coordinates('F2')['y'],wellplate.echem_height)

#start echem experiment
'''
echem.pstatconnect()
#complete_file_name = echem.setfilename(well_run,"OCP")
complete_file_name = "C:\\Users\\gamry\\Documents\\Python Scripts\\EdepDemo\\EdepDemo\\data\\2023-08-16\\F2_OCP.txt"
echem.OCP(echem.pstat, echem.OCPvi, echem.OCPti, echem.OCPsamplerate)
    if echem.check_vsig_range(complete_file_name('CV.txt')):
    echem.chrono(
    CAvi=echem.CAvi,
    CAti=echem.CAti,
    CAv1=echem.CAv1,
    CAt1=echem.CAt1,
    CAv2=echem.CAv2,
    CAt2=echem.CAt2,
    CAsamplerate=echem.CAsamplerate,
)  # CA
    while echem.active == True:
        client.PumpEvents(1)
        time.sleep(0.5)
    ## echem plot the data
    analyzer.plotdata("CA", complete_file_name)
    
'''
if __name__ == "__main__":
    main()