import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from panda_lib import pawduino
from panda_lib.grlb_mill_wrapper import PandaMill
from panda_lib.obs_controls import OBSController
from panda_lib.sql_tools.panda_models import Base
from panda_lib.vials import Coordinates, StockVial, VialKwargs

# Setup an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

repetitions = 100
pause = 3600


def main():
    # Set up the OBS controller
    try:
        obs_controller = OBSController()
        obs_controller.set_recording_file_name("decapper_validation")
        obs_controller.place_text_on_screen("Decapper validation program")
        obs_controller.start_recording()
        # populate the database with the vial
        vkwargs = VialKwargs(
            category=0,
            name="IPA",
            contents={"IPA": 20000},
            viscosity_cp=1,
            concentration=0.01,
            density=1,
            height=69,
            radius=14,
            volume=20000,
            capacity=20000,
            contamination=0,
            coordinates={"x": -4, "y": -106, "z": -200},
            base_thickness=1,
            dead_volume=1000,
        )
        vial = StockVial(
            position="s0", create_new=True, session_maker=SessionLocal, **vkwargs
        )
        vial.save()
        print(f"Vial {vial} has been created")
        # Set up the hardware connections
        with PandaMill() as mill:
            with pawduino.ArduinoLink() as arduino:
                # Check the tools in the tool manager
                print("Tools in the tool manager:")
                for tool in mill.tool_manager.tool_offsets.values():
                    print(tool)

                if "decapper" not in mill.tool_manager.tool_offsets:
                    mill.add_tool("decapper", (-74, 0, 57))
                if mill.homed:
                    print("Mill has been homed")
                else:
                    print("Mill has not been homed")
                    exit()

                # Run the decapping validation program
                decapping_validation(mill, vial, arduino, obs_controller)
    except Exception as e:
        print(e)
    finally:
        obs_controller.stop_recording()


def decapping_validation(
    mill: PandaMill, vial: StockVial, arduino: pawduino.ArduinoLink, obs: OBSController
):
    # Outline of the validation program:
    # 100x decapping and capping of the vial
    # 1 hr pause
    # 100x decapping, bringing the pipette to the vial bottom, and then capping the vial
    arduino.curvature_lights_on()
    # Decap and cap the vial 100 times with progress bar
    obs.place_text_on_screen(f"Decapping and capping the vial {repetitions} times")
    for i in tqdm(range(repetitions), desc="Decapping and capping"):
        obs.place_text_on_screen(
            f"Decapping and capping the vial {repetitions} times: decapping \n{i + 1} of {repetitions}"
        )
        decapping_sequence(
            mill, Coordinates(vial.coordinates.x, vial.coordinates.y, vial.top), arduino
        )
        obs.place_text_on_screen(
            f"Decapping and capping the vial {repetitions} times: capping \n{i + 1} of {repetitions}"
        )
        capping_sequence(
            mill, Coordinates(vial.coordinates.x, vial.coordinates.y, vial.top), arduino
        )

    # Pause for 1 hour
    obs.place_text_on_screen(f"Pausing for {round(pause / 3600, 0)} hour: 3600 seconds")
    for i in tqdm(range(pause), desc="Pausing for 1 hour"):
        obs.place_text_on_screen(
            f"Pausing for {round(pause / 3600, 0)} hour: {pause - i} seconds"
        )
        time.sleep(1)

    # Decap, move the pipette to the vial bottom, and cap the vial 100 times with progress bar
    obs.place_text_on_screen(
        f"Decapping, dipping pipette, and capping the vial {repetitions} times"
    )
    for i in tqdm(range(repetitions), desc="Decapping, moving pipette, and capping"):
        obs.place_text_on_screen(
            f"Decapping, dipping pipette, and capping the vial {repetitions} times: decapping \n{i + 1} of {repetitions}"
        )
        decapping_sequence(
            mill, Coordinates(vial.coordinates.x, vial.coordinates.y, vial.top), arduino
        )
        obs.place_text_on_screen(
            f"Decapping, dipping pipette, and capping the vial {repetitions} times: moving pipette \n{i + 1} of {repetitions}"
        )
        mill.safe_move(
            vial.coordinates.x,
            vial.coordinates.y,
            vial.bottom,
            tool="pipette",
        )
        obs.place_text_on_screen(
            f"Decapping, dipping pipette, and capping the vial {repetitions} times: capping \n{i + 1} of {repetitions}"
        )
        capping_sequence(
            mill, Coordinates(vial.coordinates.x, vial.coordinates.y, vial.top), arduino
        )

    obs.place_text_on_screen(
        f"Decapping and capping the vial {repetitions} times: Done"
    )
    arduino.curvature_lights_off()


def decapping_sequence(
    mill: PandaMill, target_coords: Coordinates, ard_link: pawduino.ArduinoLink
):
    """
    The decapping sequence is as follows:
    - Move to the target coordinates
    - Activate the decapper
    - Move the decapper up 20mm
    """

    # Move to the target coordinates
    mill.safe_move(target_coords.x, target_coords.y, target_coords.z, tool="decapper")

    # Activate the decapper
    ard_link.no_cap()

    # Move the decapper up 20mm
    mill.move_to_position(
        target_coords.x,
        target_coords.y,
        target_coords.z + 20,
        tool="decapper",
    )


def capping_sequence(
    mill: PandaMill, target_coords: Coordinates, ard_link: pawduino.ArduinoLink
):
    """
    The capping sequence is as follows:
    - Move to the target coordinates
    - deactivate the decapper
    - Move the decapper +10mm in the y direction
    - Move the decapper to 0 z
    """

    # Move to the target coordinates
    mill.safe_move(target_coords.x, target_coords.y, target_coords.z, tool="decapper")

    # Deactivate the decapper
    ard_link.ALL_CAP()

    # Move the decapper +10mm in the y direction
    mill.move_to_position(target_coords.x, target_coords.y + 10, 0, tool="decapper")


if __name__ == "__main__":
    main()
