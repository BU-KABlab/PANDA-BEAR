import csv
import time
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from panda_lib.hardware import arduino_interface
from panda_lib.labware.vials import Coordinates, StockVial, VialKwargs
from panda_lib.panda_gantry import PandaMill
from panda_lib.sql_tools.panda_models import Base
from shared_utilities.config.config_tools import read_config_value

# Setup an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def main():
    try:
        print("Decapper validation program")
        # populate the database with the vial
        vkwargs = VialKwargs(
            category=0,
            name="IPA",
            contents={"IPA": 20000},
            viscosity_cp=1,
            concentration=0.01,
            density=1,
            height=66,
            radius=14,
            volume=20000,
            capacity=20000,
            contamination=0,
            coordinates={
                "x": -67.5,
                "y": -45.5,
                "z": -197,
            },  # TODO replace with vial coordinates
            base_thickness=1,
            dead_volume=1000,
        )
        vial = StockVial(
            position="s3", create_new=True, session_maker=SessionLocal, **vkwargs
        )
        vial.save()
        print(
            f"Vial {vial} has been created in memory please place a vial in position s3"
        )
        input("Press Enter to continue...")
        # Set up the hardware connections
        with PandaMill() as mill:
            with arduino_interface.ArduinoLink(
                read_config_value("ARDUINO", "port")
            ) as arduino:
                # Check the tools in the tool manager
                print("Tools in the tool manager:")
                for tool in mill.tool_manager.tool_offsets.values():
                    print(tool)

                if "decapper" not in mill.tool_manager.tool_offsets:
                    print("Adding the decapper tool")
                    mill.add_tool(
                        "decapper", (-64.376, -6.5, 61.5)
                    )  # TODO fix offset for PANDA V2
                if mill.homed:
                    print("Mill has been homed")
                else:
                    print("Mill has not been homed")
                    exit()

                # Run the decapping validation program
                decapping_validation(mill, vial, arduino)
    except Exception as e:
        print(e)
    finally:
        pass


def decapping_validation(
    mill: PandaMill,
    vial: StockVial,
    arduino: arduino_interface.ArduinoLink,
    repetitions: int = 10,
    z_start: float = None,
    z_steps: int = 30,  # Total range is 6mm
    z_increment: float = 0.2,
):
    log_entries = []
    z_start = z_start if z_start is not None else vial.top

    z_heights_to_test = [z_start + i * z_increment for i in range(z_steps)]
    print(f"\nStarting decapping/capping tests at Z heights: {z_heights_to_test}")

    for z_height in z_heights_to_test:
        print(f"\n===== Testing at Z height: {z_height}mm =====")

        for i in tqdm(range(repetitions), desc=f"Decap/Cap at Z ={z_height:.2f}"):
            trial = i + 1
            print(
                f"Decapping and capping the vial {repetitions} times: decapping \n{i + 1} of {repetitions}"
            )

            cap_picked_up, decap_attempts = decapping_sequence(
                mill,
                Coordinates(vial.coordinates.x, vial.coordinates.y, z_height),
                arduino,
            )

            if not cap_picked_up:
                print("ERROR: Decapping failed after max attempts. Pausing test.")
                input(
                    "Press Enter to continue after addressing the issue or Ctrl+C to exit."
                )
                continue

            print(
                f"Decapping and capping the vial {repetitions} times: capping \n{i + 1} of {repetitions}"
            )

            cap_released, cap_attempts = capping_sequence(
                mill,
                Coordinates(vial.coordinates.x, vial.coordinates.y, z_height),
                arduino,
            )

            if not cap_released:
                print("ERROR: Capping failed after max attempts. Pausing test.")
                input(
                    "Press Enter to continue after addressing the issue or Ctrl+C to exit."
                )
                continue

            log_entries.append(
                {
                    "z_height": z_height,
                    "trial": trial,
                    "decap_attempts": decap_attempts,
                    "cap_attempts": cap_attempts,
                    "timestamp": datetime.now().isoformat(),
                }
            )
    log_filename = f"decapper_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(log_filename, mode="w", newline="") as file:
        fieldnames = [
            "z_height",
            "trial",
            "decap_attempts",
            "cap_attempts",
            "timestamp",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(log_entries)

    print(f"Test complete. Combined log saved to {log_filename}")


def decapping_sequence(
    mill: PandaMill,
    target_coords: Coordinates,
    ard_link: arduino_interface.ArduinoLink,
    max_attempts: int = 5,
):
    """
    The decapping sequence is as follows:
    - Move to the target coordinates
    - Activate the decapper
    - Move the decapper up 20mm
    - Check the linebreak sensor to confirm cap presence
    - If the cap is not detected, repeat the sequence up to max_attempts times
    - Report the number of attempts
    """

    # Move to the target coordinates
    mill.safe_move(target_coords.x, target_coords.y, target_coords.z, tool="decapper")

    cap_picked_up = False
    attempts = 0

    while not cap_picked_up and attempts < max_attempts:
        attempts += 1
        print(f"Decapping attempt {attempts} of {max_attempts}")

        # Activate the decapper
        rx = ard_link.no_cap()
        print(f"Decapper activated: {rx == 105}")
        # Move the decapper up 20mm
        mill.move_to_position(target_coords.x, target_coords.y, 0, tool="decapper")

        # Check if cap is present via linebreak sensor
        cap_picked_up = ard_link.line_break()

        if not cap_picked_up:
            print("No cap detected. Retrying...")
            mill.safe_move(
                target_coords.x, target_coords.y, target_coords.z, tool="decapper"
            )
            time.sleep(0.5)

    if cap_picked_up:
        print(f"Cap detected after {attempts} attempt(s).")
    else:
        print("Cap not detected after max attempts.")

    return cap_picked_up, attempts


def capping_sequence(
    mill: PandaMill,
    target_coords: Coordinates,
    ard_link: arduino_interface.ArduinoLink,
    max_attempts: int = 5,
):
    """
    The capping sequence is as follows:
    - Move to the target coordinates
    - deactivate the decapper
    - Move the decapper +5mm in the y direction to dislodge cap
    - Move the decapper to 0 z
    - Confirm cap is no longer held via the linebreak sensor
    - Retry if cap is still detected
    """
    cap_released = False
    attempts = 0

    while not cap_released and attempts < max_attempts:
        attempts += 1
        print(f"Capping attempt {attempts} of {max_attempts}")

        # Move to the target coordinates
        mill.safe_move(
            target_coords.x, target_coords.y, target_coords.z, tool="decapper"
        )

        # Deactivate the decapper
        rx = ard_link.ALL_CAP()
        print(f"Decapper deactivated: {rx == 106}")

        # Move the decapper +5mm in the y direction
        mill.move_to_position(
            target_coords.x, target_coords.y, target_coords.z, tool="decapper"
        )

        # Move the decapper to 0 z
        mill.move_to_position(target_coords.x, target_coords.y, 0, tool="decapper")

        # Check if cap is present via linebreak sensor
        cap_still_held = ard_link.line_break()
        cap_released = not cap_still_held

        if not cap_released:
            print("Cap still present. Retrying...")
            time.sleep(0.5)

    if cap_released:
        print(f"Cap released after {attempts} attempt(s).")
    else:
        print("Failed to release cap after max attempts.")

    return cap_released, attempts


if __name__ == "__main__":
    main()
