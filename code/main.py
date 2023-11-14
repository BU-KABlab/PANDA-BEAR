import controller
import sys

def run_epanda():
    """Runs ePANDA."""
    controller.main()

def run_epanda_mock():
    """Runs ePANDA with mock instruments."""
    controller.main(use_mock_instruments=True)

def change_wellplate():
    """Changes the current wellplate."""
    controller.load_new_wellplate(ask = True)

def reset_vials_stock():
    """Resets the stock vials."""
    controller.reset_vials('stock')

def reset_vials_waste():
    """Resets the waste vials."""
    controller.reset_vials('waste')

def input_new_vial_values_stock():
    """Inputs new values for the stock vials."""
    controller.input_new_vial_values('stock')

def input_new_vial_values_waste():
    """Inputs new values for the waste vials."""
    controller.input_new_vial_values('waste')

def change_wellplate_location():
    """Changes the location of the current wellplate."""
    controller.change_wellplate_location()

def exit_program():
    """Exits the program."""
    print("Exiting ePANDA. Goodbye!")
    sys.exit()

options = {
    '0': run_epanda,
    '1': run_epanda_mock,
    '2': change_wellplate,
    '3': reset_vials_stock,
    '4': reset_vials_waste,
    '5': input_new_vial_values_stock,
    '6': input_new_vial_values_waste,
    '7': change_wellplate_location,
    '12': exit_program  # changed from 'exit' to 'exit_program'
}

if __name__ == "__main__":
    print("Welcome to ePANDA!")
    while True:
        print("What would you like to do?")
        for key, value in options.items():
            print(f"{key}. {value.__name__.replace('_', ' ').title()}")

        user_choice = input("Enter the number of your choice: ")
        if user_choice in options:
            options[user_choice]()
        else:
            print("Invalid choice. Please try again.")
            continue
