#from EdepDemo import  read_vials
#
# Run this file using the debug python file option to establish a connection to the mill and be able to send commands via the debug console.

# You can then run the following commands in the debug console to move the pipette and electrode to the desired positions:
# move_center_to_position(mill, x, y, z)
# move_electrode_to_position(mill, x, y, z)
# move_pipette_to_position(mill, x, y, z)

# Because this script reads in the wellplate and vials you can also try sending a tool to one of these objects. For example:
# move_pipette_to_position(mill, wellplate.get_coordinates('H1')['x'], wellplate.get_coordinates('H1')['y'],0)

#
from classes import Wells, MillControl
import gamrycontrol as echem
import Analyzer as analyzer
from run_experiments import read_vials, set_up_pump, withdraw, infuse
mill = MillControl()
wellplate = Wells(-218, -74, 0, 0)
pump = set_up_pump()
stock_vials = read_vials('vial_status.json')
waste_vials = read_vials('waste_status.json')

def main():
    input("Press enter to finish.")

def interactive():
    # ferrocene_vial = stock_vials[4]
    # ferrocene_coordinates = ferrocene_vial.coordinates
    # mill.move_pipette_to_position(ferrocene_coordinates['x'],ferrocene_coordinates['y'],0)
    # mill.move_pipette_to_position(ferrocene_coordinates['x'],ferrocene_coordinates['y'],ferrocene_vial.bottom)

    # mill.move_electrode_to_position(wellplate.get_coordinates('F6')['x'], wellplate.get_coordinates('F6')['y'],0)
    # mill.move_electrode_to_position(wellplate.get_coordinates('F6')['x'], wellplate.get_coordinates('F6')['y'],-67)
    # mill.move_electrode_to_position(wellplate.get_coordinates('F6')['x'], wellplate.get_coordinates('F6')['y'], wellplate.depth('F6'))

    # mill.move_electrode_to_position(-200,-240,0)
    # mill.move_electrode_to_position(-200,-240,-20)
    # mill.rinse_electrode()

    while True:
        print("Select an operation:")
        print("1. Move center to position")
        print("2. Move pipette to position")
        print("3. Move electrode to position")
        print("4. Exit")
        
        choice = input("Enter your choice (1/2/3/4): ")
        
        if choice == '1':
            x = float(input("Enter X coordinate: "))
            y = float(input("Enter Y coordinate: "))
            z = float(input("Enter Z coordinate: "))
            mill.move_center_to_position(x, y, z)
        elif choice == '2':
            x = float(input("Enter X coordinate: "))
            y = float(input("Enter Y coordinate: "))
            z = float(input("Enter Z coordinate: "))
            mill.move_pipette_to_position(x, y, z)
        elif choice == '3':
            x = float(input("Enter X coordinate: "))
            y = float(input("Enter Y coordinate: "))
            z = float(input("Enter Z coordinate: "))
            mill.move_electrode_to_position(x, y, z)
        
        elif choice == '4':
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please enter a valid option.")
    
    return 0

if __name__ == "__main__":
    main()