"""Starts ePANDA."""

import controller

if __name__ == "__main__":
    print("Welcome to ePANDA!")
    response = input("Do you want to run the main ePANDA program? (y/n) ")
    if response.lower() == 'y':
        controller.main()
    else:
        while True:
            print("What would you like to do?")
            print("00. Run the main ePANDA program")
            print("01. Reset the wellplate")
            print("02. Input new stock vials")
            print("03. Reset the waste vials")
            print("04. Input new stock vials")
            print("05. Input new waste vials")
            print("06. Change the position of the wellplate")
            print("07. Change the position of the pipette")
            print("08. Change the position of the electrode")
            print("09. Change the position of the camera")
            print("10. Change the position of solvent bath")
            print("11. Exit")

            user_choice = input("Enter the number of your choice: ")
            if user_choice == '00':
                controller.main()
            elif user_choice == '1':
                controller.load_new_wellplate()
            elif user_choice == '2':
                controller.reset_vials('stock')
            elif user_choice == '3':
                controller.reset_vials('waste')
            elif user_choice == '4':
                controller.input_new_vial_values('stock')
            elif user_choice == '5':
                controller.input_new_vial_values('waste')
            elif user_choice == '6':
                controller.change_wellplate_location()
            elif user_choice == '7':
                controller.change_pipette()
            elif user_choice == '8':
                controller.change_electrode()
            elif user_choice == '9':
                controller.change_camera()
            elif user_choice == '10':
                controller.change_solvent_bath()
            elif user_choice == '11':
                break
            else:
                print("Invalid choice. Please try again.")
                continue
