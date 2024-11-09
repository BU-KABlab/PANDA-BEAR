"""Test the syringe and pipette for retention and suction."""

import time

from panda_lib.actions import (
    Instruments,
    solution_selector,
    waste_selector,
)
from panda_lib.correction_factors import correction_factor
from panda_lib.experiment_loop import (
    connect_to_instruments,
    disconnect_from_instruments,
    establish_system_state,
)
from panda_lib.utilities import input_validation

purge = 40
drip_stop = 5


def main():
    """Test the syringe and pipette for retention and suction."""
    # Establish system state
    _, _, _ = establish_system_state()

    # Connect to instruments
    toolkit, _ = connect_to_instruments(False)

    test_volume = input_validation(
        "Enter the volume to test (uL): ", (float, int), (0, 200), 0, "Invalid volume."
    )

    test_volume = correction_factor(test_volume)

    # Test the syringe and pipette for retention and suction
    while True:
        # Select solution
        test_solution = solution_selector("water", test_volume)
        test_waste = waste_selector("waste", test_volume)

        # Withdraw water, raise to z=0, and hold it for 60 seconds
        toolkit.pump.withdraw(purge)

        toolkit.mill.safe_move(
            test_solution.coordinates.x,
            test_solution.coordinates.y,
            test_solution.coordinates.z_top,
            Instruments.DECAPPER,
        )

        toolkit.arduino.no_cap()

        toolkit.mill.safe_move(
            test_solution.coordinates.x,
            test_solution.coordinates.y,
            test_solution.coordinates.z_bottom,
            Instruments.PIPETTE,
        )
        toolkit.pump.withdraw(test_volume, test_solution)
        toolkit.mill.move_to_safe_position()
        toolkit.pump.withdraw(drip_stop)

        toolkit.mill.safe_move(
            test_solution.coordinates.x,
            test_solution.coordinates.y,
            test_solution.coordinates.z_top,
            Instruments.DECAPPER,
        )

        toolkit.arduino.ALL_CAP()
        toolkit.mill.move_to_safe_position()
        time.sleep(15)
        input("Press enter to continue...")
        toolkit.mill.safe_move(
            test_waste.coordinates.x,
            test_waste.coordinates.y,
            test_waste.coordinates.z_top,
            Instruments.PIPETTE,
        )
        toolkit.pump.infuse(
            test_volume, test_solution, test_waste, blowout_ul=drip_stop + purge
        )
        # Forward pipette
        # test_forward_pipette = input("Do a forward pipette test? (y/n): ")
        # if test_forward_pipette.lower() == "y":
        #     forward_pipette_v2(test_volume, test_solution, test_waste, toolkit.pump, toolkit.mill)

        go_again = input("Do another test? (y/n): ")
        if go_again.lower() == "n":
            break

    toolkit.mill.rest_electrode()
    # Disconnect from instruments
    disconnect_from_instruments(toolkit)
