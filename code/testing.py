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
from tkinter import Scale
from pump_control import Pump
from regex import P
from mill_control import Mill, Instruments
from wellplate import Wells
from vials import Vial
import gamry_control_WIP as echem
from scale import Sartorius as Scale
from controller import read_vials, update_vials
from experiment_class import Experiment, ExperimentResult, ExperimentStatus
from config.pin import CURRENT_PIN
from datetime import datetime

wellplate = Wells(a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13)

stock_vials = read_vials("vial_status.json")
waste_vials = read_vials("waste_status.json")


def cv_cleaning_test():
    """A protocol to test the cleaning of the platinum electrode using CV in pure electrolyte."""
    with Mill() as mill:
        echem.pstatconnect()

        # define coordinates for easy reference
        a1_coord = wellplate.get_coordinates("A1")
        a2_coord = wellplate.get_coordinates("A2")
        a3_coord = wellplate.get_coordinates("A3")
        a4_coord = wellplate.get_coordinates("A4")

        ## Well 1: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        mill.safe_move(a1_coord["x"], a1_coord["y"], a1_coord["echem_height"])
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
        input("Press enter to start continue to well 2.")

        ## Well 2: Deposition using polymers (CA V=-1.7V, 300s)
        mill.safe_move(
            a2_coord["x"],
            a2_coord["y"],
            a2_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        input("Press enter to start CV.")
        echem.setfilename("cleaning_test_W2", "CA")
        echem.chrono(
            echem.potentiostat_ca_parameters.CAvi,
            echem.potentiostat_ca_parameters.CAti,
            CAv1=-1.7,
            CAt1=300,
            CAv2=echem.potentiostat_ca_parameters.CAv2,
            CAt2=echem.potentiostat_ca_parameters.CAt2,
            CAsamplerate=0.01,
        )  # CA

        echem.activecheck()
        mill.rinse_electrode()
        input("Press enter to continue to well 3.")

        ## Well 3: Cleaning in pure electrolyte (CV, 10 cycles, -1.5V to 1.5V)
        mill.safe_move(
            a3_coord["x"],
            a3_coord["y"],
            a3_coord["echem_height"],
            Instruments.ELECTRODE,
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
        mill.rinse_electrode()
        input("Press enter to start continue to well 4.")

        ## Well 4: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        mill.safe_move(
            a4_coord["x"],
            a4_coord["y"],
            a4_coord["echem_height"],
            Instruments.ELECTRODE,
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
        mill.rinse_electrode()
        input("Press enter to end")
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

def mixing_test():
    """
    A protocol to test the mixing of the solution in the wellplate.
    Experiment name format: MixingTest_wellID_echemType

    The contents and variable parameters of each well are as follows:
    
    Well | Solution(s)              | Mixing repetitions
    --------------------------------------------------------
    C1   | Premixed Solution        | 0
    C2   | Premix                   | 0
    C3   | PEG, Acrylate, DmFc      | 1
    C4   | PEG, Acrylate, DmFc      | 1
    C5   | PEG, Acrylate, DmFc      | 3
    C6   | PEG, Acrylate, DmFc      | 3
    C7   | PEG, Acrylate, DmFc      | 6
    C8   | PEG, Acrylate, DmFc      | 6
    C9   | PEG, Acrylate, DmFc      | 9
    C10  | PEG, Acrylate, DmFc      | 9
    C11  | Premixed Solution        | 0
    C12  | Premixed Solution        | 0

    For each well, the following steps are also performed:
    - deposition (CA) of the solution onto the substrate.
    - plotting the results
    - clearing the well
    - rinsing the well
    - rinsing the electrode
    - cleaning the electrode (CV)
    - rinsing the electrode
    - characterizing (CV) the well
    - plotting the results
    - rinsing the electrode
    - clearing the well
    - rinsing the well

    
    """
    from mixing_test_experiments import experiments
    wells = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8","C9","C10","C11","C12"]
    solution_names = ["peg", "acrylate", "dmfc"]
    stock_vials = read_vials("stock_status.json")
    waste_vials = read_vials("waste_status.json")

    
    with Mill() as mill:
        with Scale() as scale:
            pump = Pump(mill, scale)
            echem.pstatconnect()
            for experiment in experiments:
                
                



if __name__ == "__main__":
    #cv_cleaning_test()
    # main()
    # interactive()
    mixing_test()
