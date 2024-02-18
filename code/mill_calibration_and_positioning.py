from mill_control import Mill, MockMill, Wellplate, Well, StockVial, WasteVial
from typing import Sequence
import json
from pathlib import Path


def check_mill_settings(mill: Mill):

    mill.connect_to_mill()  # Connect without homing
    if not mill.ser_mill.is_open:
        raise ValueError("Mill is not connected")

    response = mill.execute_command("$$")  # Get settings
    print(response)

    # Check settings
    # Load settings file and compare to current settings
    # List out differences
    # Ask if user wants to change settings
    # Ask for settings to change
    # Ask for the new value
    # Update loaded settings file
    # Send the new setting to the mill
    # Confirm setting has been applied
    # Save the settings file
    # Repeat until user is satisfied

    mill.disconnect()  # Disconnect without moving


def calibrate_mill(
    mill: Mill,
    wellplate: Wellplate,
    stock_vials: Sequence[StockVial],
    waste_vial: WasteVial,
):
    """Calibrate the mill to the wellplate and stock vials"""
    # Connect to the mill
    mill.connect_to_mill()
    if not mill.ser_mill.is_open:
        raise ValueError("Mill is not connected")

    # Home the mill
    mill.homing_sequence()

    ## Calibrate the wellplate
    # Enter well choice loop
    # ask the user for the well id they would like to test, must be in the form of [A-H][1-12]
    # Provide the current coordinates of the well
    # Move the pipette to the top of the well
    # Enter confirmation loop
    # Ask the user to confirm the pipette is in the correct position
    # If the user confirms, do nothing
    # If the user does not confirm, ask the user to input the new coordinates
    # Safe Move to the new coordinates
    # Repeat until the user confirms the position
    # Save the new coordinates to the wellplate object
    # Repeat until the user enters "done"

    ## Check the z_bottom of the wellplate
    # Enter confirmation loop
    # Ask the user to enter a well id to check the z_bottom or to enter "done" to finish
    # Ask the user to confirm the pipette is in the correct position
    # If the user confirms, do nothing
    # If the user does not confirm, ask the user to input the new z_bottom
    # Safe Move to the new z_bottom
    # Repeat until the user confirms the position
    # Save the new z_bottom to the wellplate object
    # Repeat until the user enters "done"

    ## Calibrate the stock vials including the electrode bath

    ## Calibrate the waste vial

    # Disconnect from the mill
    mill.disconnect()
