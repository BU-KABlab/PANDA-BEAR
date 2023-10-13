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
from mill_control import Mill, Instruments
from wellplate import Wells
from vials import read_vials
import gamry_control_WIP as echem

wellplate = Wells(a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13)

#stock_vials = read_vials("vial_status.json")
#waste_vials = read_vials("waste_status.json")


def cv_cleaning_test():
    """A protocol to test the cleaning of the platinum electrode using CV in pure electrolyte."""
    with Mill() as mill:
        mill.homing_sequence()
        echem.pstatconnect()

        # define coordinates for easy reference
        a1_coord = wellplate.get_coordinates("A1")
        a2_coord = wellplate.get_coordinates("A2")
        a3_coord = wellplate.get_coordinates("A3")
        a4_coord = wellplate.get_coordinates("A4")

        # ## Well 1: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        # mill.safe_move(a1_coord["x"], a1_coord["y"], a1_coord["echem_height"], Instruments.ELECTRODE)
        # input("Press enter to start CV.")
        # echem.setfilename("cleaning_test_W1", "CV")
        # echem.cyclic(
        #     CVvi=echem.potentiostat_cv_parameters.CVvi,
        #     CVap1=0.3,
        #     CVap2=-0.2,
        #     CVvf=echem.potentiostat_cv_parameters.CVvf,
        #     CVsr1=0.05,
        #     CVsr2=0.05,
        #     CVsr3=0.05,
        #     CVsamplerate=(0.1 / 0.05),
        #     CVcycle=3,
        # )
        # echem.activecheck()
        # mill.rinse_electrode()
        # input("Press enter to start continue to well 2.")

        # ## Well 2: Deposition using polymers (CA V=-1.7V, 300s)
        # mill.safe_move(
        #     a2_coord["x"],
        #     a2_coord["y"],
        #     a2_coord["echem_height"],
        #     Instruments.ELECTRODE,
        # )
        # input("Press enter to start CA.")
        # echem.setfilename("cleaning_test_W2", "CA")
        # echem.chrono(
        #     echem.potentiostat_ca_parameters.CAvi,
        #     echem.potentiostat_ca_parameters.CAti,
        #     CAv1=-1.7,
        #     CAt1=300,
        #     CAv2=echem.potentiostat_ca_parameters.CAv2,
        #     CAt2=echem.potentiostat_ca_parameters.CAt2,
        #     CAsamplerate=0.01,
        # )  # CA

        # echem.activecheck()
        # mill.rinse_electrode()
        # input("Press enter to continue to well 3.")

        # ## Well 3: Cleaning in pure electrolyte (CV, 10 cycles, -1.5V to 1.5V)
        # mill.safe_move(
        #     a3_coord["x"],
        #     a3_coord["y"],
        #     a3_coord["echem_height"],
        #     Instruments.ELECTRODE,
        # )
        # input("Press enter to start CV cleaning")
        # echem.setfilename("cleaning_test_W3", "CV")
        # echem.cyclic(
        #     CVvi=echem.potentiostat_cv_parameters.CVvi,
        #     CVap1=1.5,
        #     CVap2=-1.5,
        #     CVvf=echem.potentiostat_cv_parameters.CVvf,
        #     CVsr1=0.05,
        #     CVsr2=0.05,
        #     CVsr3=0.05,
        #     CVsamplerate=(0.1 / 0.05),
        #     CVcycle=10,
        # )
        # echem.activecheck()
        # mill.rinse_electrode()
        # input("Press enter to start continue to well 4.")

        # ## Well 4: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        # mill.safe_move(
        #     a4_coord["x"],
        #     a4_coord["y"],
        #     a4_coord["echem_height"],
        #     Instruments.ELECTRODE,
        # )
        # input("Press enter to continue.")
        # echem.setfilename("cleaning_test_W4", "CV")
        # echem.cyclic(
        #     CVvi=echem.potentiostat_cv_parameters.CVvi,
        #     CVap1=0.3,
        #     CVap2=-0.2,
        #     CVvf=echem.potentiostat_cv_parameters.CVvf,
        #     CVsr1=0.05,
        #     CVsr2=0.05,
        #     CVsr3=0.05,
        #     CVsamplerate=(0.1 / 0.05),
        #     CVcycle=3,
        # )
        # echem.activecheck()
        # mill.rinse_electrode()

        # ## Well 5: Deposition using polymers (CA V=-1.7V, 300s)
        # print("Well 5: Deposition using polymers (CA V=-1.7V, 300s)")
        # a5_coord = wellplate.get_coordinates("A5")
        # input("Press enter to continue to well 5.")
        # mill.safe_move(
        #     a5_coord["x"],
        #     a5_coord["y"],
        #     a5_coord["echem_height"],
        #     Instruments.ELECTRODE,
        # )
        # input("Press enter to start CA.")
        # echem.setfilename("cleaning_test_W5", "CA")
        # echem.chrono(
        #     echem.potentiostat_ca_parameters.CAvi,
        #     echem.potentiostat_ca_parameters.CAti,
        #     CAv1=-1.7,
        #     CAt1=300,
        #     CAv2=echem.potentiostat_ca_parameters.CAv2,
        #     CAt2=echem.potentiostat_ca_parameters.CAt2,
        #     CAsamplerate=0.01,
        # )  # CA

        # echem.activecheck()
        # mill.rinse_electrode()
        # input("Press enter to continue to well 6.")

        # ## Well 6: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        # print("Well 6: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)")
        # a6_coord = wellplate.get_coordinates("A6")
        # input("Press enter to continue.")
        # mill.safe_move(
        #     a6_coord["x"],
        #     a6_coord["y"],
        #     a6_coord["echem_height"],
        #     Instruments.ELECTRODE,
        # )
        # input("Press enter to start CV.")
        # echem.setfilename("cleaning_test_W6", "CV")
        # echem.cyclic(
        #     CVvi=echem.potentiostat_cv_parameters.CVvi,
        #     CVap1=0.3,
        #     CVap2=-0.2,
        #     CVvf=echem.potentiostat_cv_parameters.CVvf,
        #     CVsr1=0.05,
        #     CVsr2=0.05,
        #     CVsr3=0.05,
        #     CVsamplerate=(0.01 / 0.05),
        #     CVcycle=3,
        # )
        # echem.activecheck()
        # mill.rinse_electrode()

        ## Well 7: Deposition using polymers (CA V=-1.7V, 300s)
        print("Well 7: Deposition using polymers (CA V=-1.7V, 300s)")
        a7_coord = wellplate.get_coordinates("A7")
        #input("Press enter to continue to well 7.")
        mill.safe_move(
            a7_coord["x"],
            a7_coord["y"],
            a7_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        #input("Press enter to start CA.")
        echem.setfilename("cleaning_test_W7", "CA")
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
        #input("Press enter to continue to well 8.")

        ## Well 8: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        print("Well 8: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)")
        a8_coord = wellplate.get_coordinates("A8")
        #input("Press enter to continue.")
        mill.safe_move(
            a8_coord["x"],
            a8_coord["y"],
            a8_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        #input("Press enter to start CV.")
        echem.setfilename("cleaning_test_W8", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=0.3,
            CVap2=-0.2,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(0.01 / 0.05),
            CVcycle=3,
        )
        echem.activecheck()
        mill.rinse_electrode()

        ## Well 9: Deposition using polymers (CA V=-1.7V, 300s)
        print("Well 9: Deposition using polymers (CA V=-1.7V, 300s)")
        a9_coord = wellplate.get_coordinates("A9")
        #input("Press enter to continue to well 9.")
        mill.safe_move(
            a9_coord["x"],
            a9_coord["y"],
            a9_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        #input("Press enter to start CA.")
        echem.setfilename("cleaning_test_W9", "CA")
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
        #input("Press enter to continue to well 10.")

        ## Well 10: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        print("Well 10: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)")
        a10_coord = wellplate.get_coordinates("A10")
        #input("Press enter to continue.")
        mill.safe_move(
            a10_coord["x"],
            a10_coord["y"],
            a10_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        #input("Press enter to start CV.")
        echem.setfilename("cleaning_test_W10", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=0.3,
            CVap2=-0.2,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(0.01 / 0.05),
            CVcycle=3,
        )
        echem.activecheck()
        mill.rinse_electrode()

        ## Well 11: Deposition using polymers (CA V=-1.7V, 300s)
        print("Well 11: Deposition using polymers (CA V=-1.7V, 300s)")
        a11_coord = wellplate.get_coordinates("A11")
        #input("Press enter to continue to well 11.")
        mill.safe_move(
            a11_coord["x"],
            a11_coord["y"],
            a11_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        #input("Press enter to start CA.")
        echem.setfilename("cleaning_test_W11", "CA")
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
        #input("Press enter to continue to well 12.")

        ## Well 12: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        print("Well 12: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)")
        a12_coord = wellplate.get_coordinates("A12")
        #input("Press enter to continue.")
        mill.safe_move(
            a12_coord["x"],
            a12_coord["y"],
            a12_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        #input("Press enter to start CV.")
        echem.setfilename("cleaning_test_W12", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=0.3,
            CVap2=-0.2,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(0.01 / 0.05),
            CVcycle=3,
        )
        echem.activecheck()
        mill.rinse_electrode()

        ## Well 13: Deposition using polymers (CA V=-1.7V, 300s)
        print("Well 13: Deposition using polymers (CA V=-1.7V, 300s)")
        b1_coord = wellplate.get_coordinates("B1")
        #input("Press enter to continue to well 13.")
        mill.safe_move(
            b1_coord["x"],
            b1_coord["y"],
            b1_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        #input("Press enter to start CA.")
        echem.setfilename("cleaning_test_W13", "CA")
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
        #input("Press enter to continue to well 14.")

        ## Well 14: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)
        print("Well 14: Characterization of bare gold with DmFC sol (CV, 3 cycles, -0.2, 0.3V)")
        b2_coord = wellplate.get_coordinates("B2")
        #input("Press enter to continue.")
        mill.safe_move(
            b2_coord["x"],
            b2_coord["y"],
            b2_coord["echem_height"],
            Instruments.ELECTRODE,
        )
        #input("Press enter to start CV.")
        echem.setfilename("cleaning_test_W14", "CV")
        echem.cyclic(
            CVvi=echem.potentiostat_cv_parameters.CVvi,
            CVap1=0.3,
            CVap2=-0.2,
            CVvf=echem.potentiostat_cv_parameters.CVvf,
            CVsr1=0.05,
            CVsr2=0.05,
            CVsr3=0.05,
            CVsamplerate=(0.01 / 0.05),
            CVcycle=3,
        )
        echem.activecheck()
        mill.rinse_electrode()
        #input("Press enter to end")
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
    # main()
    # interactive()
