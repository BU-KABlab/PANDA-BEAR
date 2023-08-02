from classes import MillControl
'''
For calibrating the location of instruments on the mill head.
'''
# Path: code\MAIN\mill_calibration.py


def mill_calibration():
    '''
    For calibrating the location of instruments on the mill head.
    '''
    
    mill = MillControl()
    mill.move_center_to_position(-100,-100,0)
    ## stop for user input
    input("Press Enter to continue...")

    mill.move_electrode_to_position(-100,-100,0)
    ## stop for user input
    input("Press Enter to continue...")
    mill.move_pipette_to_position(-100,-100,0)
    ## stop for user input
    input("Press Enter to close mill connection...")
    mill.close()
    print("Mill connection closed.")

if __name__ == "__main__":
    mill_calibration()