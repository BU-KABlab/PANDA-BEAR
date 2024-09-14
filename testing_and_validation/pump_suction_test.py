"""Test the syringe and pipette for retention and suction."""
import time
from panda_lib.actions import (
    solution_selector,
    waste_selector,
    forward_pipette_v2,
    Instruments,
)
from panda_lib.controller import (
    establish_system_state,
    connect_to_instruments,
    disconnect_from_instruments,
)

def main():
    """Test the syringe and pipette for retention and suction."""
    # Establish system state
    stock, waste, _ = establish_system_state()

    # Connect to instruments
    toolkit, _ = connect_to_instruments()

    
    while True:
        # Select solution
        test_solution = solution_selector(stock, "water", 1000)
        test_waste = waste_selector(waste, "waste", 1000)

        # Withdraw water, raise to z=0, and hold it for 60 seconds
        toolkit.pump.withdraw(40)
        toolkit.mill.safe_move(
            test_solution.coordinates.x,
            test_solution.coordinates.y,
            test_solution.coordinates.z_bottom,
            Instruments.PIPETTE,
        )
        toolkit.pump.withdraw(1000, test_solution)
        toolkit.mill.move_to_safe_position()
        toolkit.pump.withdraw(25)
        time.sleep(60)
        input("Press enter to continue...")
        toolkit.mill.safe_move(
            test_waste.coordinates.x,
            test_waste.coordinates.y,
            test_waste.coordinates.z_top,
            Instruments.PIPETTE,
        )
        toolkit.pump.infuse(1045, test_waste)

        # Forward pipette
        # test_forward_pipette = input("Do a forward pipette test? (y/n): ")
        # if test_forward_pipette.lower() == "y":
        #     forward_pipette_v2(1000, test_solution, test_waste, toolkit.pump, toolkit.mill)

        go_again = input("Do another test? (y/n): ")
        if go_again.lower() == "n":
            break
    # Disconnect from instruments
    disconnect_from_instruments(toolkit)
