# from EdepDemo import  read_vials
#
# Run this file using the debug python file option to establish a connection to the mill and be able to send commands via the debug console.

# You can then run the following commands in the debug console to move the pipette and electrode to the desired positions:
# move_center_to_position(mill, x, y, z)
# move_electrode_to_position(mill, x, y, z)
# move_pipette_to_position(mill, x, y, z)

# Because this script reads in the wellplate and vials you can also try sending a tool to one of these objects. For example:
# move_pipette_to_position(mill, wellplate.get_coordinates('H1')['x'], wellplate.get_coordinates('H1')['y'],0)

#
from mill_control import Mill
from wellplate import Wells
from pump_control import Pump
from vials import read_vials
from scale import Sartorius as Scale
import gamry_control_WIP as echem

wellplate = Wells(a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13)

stock_vials = read_vials("vial_status.json")
waste_vials = read_vials("waste_status.json")


def cv_cleaning_test():
    """A protocol to test the cleaning of the platinum electrode using CV in pure electrolyte."""
    with Mill() as mill:
        echem.pstatconnect()

        # define coordinates for easy reference
        a1_coordinates = wellplate.get_coordinates("A1")
        a2_coordinates = wellplate.get_coordinates("A2")
        a3_coordinates = wellplate.get_coordinates("A3")
        a4_coordinates = wellplate.get_coordinates("A4")

        ## Well 1: Characterization of baregold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        mill.safe_move(
            a1_coordinates["x"], a1_coordinates["y"], a1_coordinates["echem_height"]
        )
        input("Press enter to start CV.")
        echem.setfilename("cleaning_test_W1", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=0.3,
            CVap2=-0.2,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(echem.potentiostat_cv_parameters.CVstep / 0.05),
            CVcycle=3,
        )
        echem.activecheck()
        input("Press enter to start continue.")

        ## Well 2: Deposition using polymers (CA V=-1.7V, 300s)
        mill.safe_move(
            a2_coordinates["x"], a2_coordinates["y"], a2_coordinates["echem_height"]
        )
        input("Press enter to start CV.")
        echem.setfilename("cleaning_test_W2", "CA")
        echem.chrono(
            echem.potentiostat_ca_parameters.CAvi,
            echem.potentiostat_ca_parameters.CAti,
            CAv1=-1.5,
            CAt1=300,
            CAv2=echem.potentiostat_ca_parameters.CAv2,
            CAt2=echem.potentiostat_ca_parameters.CAt2,
            CAsamplerate=0.01,
        )  # CA

        echem.activecheck()
        input("Press enter to continue.")

        ## Well 3: Cleaning in pure electrolyte (CV, 10 cycles, -1.5V to 1.5V)
        mill.safe_move(
            a3_coordinates["x"], a3_coordinates["y"], a3_coordinates["echem_height"]
        )
        input("Press enter to start CV cleaning")
        echem.setfilename("cleaning_test_W3", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=1.5,
            CVap2=-1.5,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(echem.potentiostat_cv_parameters.CVstep / 0.05),
            CVcycle=10,
        )
        echem.activecheck()
        input("Press enter to start continue.")

        ## Well 4: Characterization of baregold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        mill.safe_move(
            a4_coordinates["x"], a4_coordinates["y"], a4_coordinates["echem_height"]
        )
        input("Press enter to continue.")
        echem.setfilename("cleaning_test_W4", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=0.3,
            CVap2=-0.2,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(echem.potentiostat_cv_parameters.CVstep / 0.05),
            CVcycle=3,
        )
        echem.activecheck()
        input("Press enter to start end")
        echem.disconnectpstat()


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
    with Mill() as mill:
        while True:
            print("Select an operation:")
            print("1. Move center to position")
            print("2. Move pipette to position")
            print("3. Move electrode to position")
            print("4. Exit")

            choice = input("Enter your choice (1/2/3/4): ")

            if choice == "1":
                x = float(input("Enter X coordinate: "))
                y = float(input("Enter Y coordinate: "))
                z = float(input("Enter Z coordinate: "))
                mill.move_center_to_position(x, y, z)
            elif choice == "2":
                x = float(input("Enter X coordinate: "))
                y = float(input("Enter Y coordinate: "))
                z = float(input("Enter Z coordinate: "))
                mill.move_pipette_to_position(x, y, z)
            elif choice == "3":
                x = float(input("Enter X coordinate: "))
                y = float(input("Enter Y coordinate: "))
                z = float(input("Enter Z coordinate: "))
                mill.move_electrode_to_position(x, y, z)

            elif choice == "4":
                print("Exiting program.")
                break
            else:
                print("Invalid choice. Please enter a valid option.")

        return 0


if __name__ == "__main__":
    cv_cleaning_test()
    #main()
    # interactive()
