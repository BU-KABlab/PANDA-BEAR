#from EdepDemo import  read_vials
from classes import Wells, MillControl
import gamrycontrol as echem
import Analyzer as analyzer
from run_experiments import read_vials
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
    waste_vials = read_vials('vial_status.json')
    stock_vials = read_vials('waste_status.json')
    
    input("Press Enter to progress...")
    ## Move center to position
    mill.move_center_to_position(-200, -240,0)

    ## Move pipette to position
    input("Press Enter to progress...")
    mill.move_pipette_to_position(-200, -240,0)

    ## Move electrode to position
    input("Press Enter to progress...")
    mill.move_electrode_to_position(-200, -240,0)

    ## pause for user input
    input("Press Enter to end...")
    return 0

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