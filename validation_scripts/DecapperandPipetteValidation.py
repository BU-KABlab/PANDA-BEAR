import logging
from panda_shared.db_setup import SessionLocal
from panda_lib.actions import solution_selector, transfer, waste_selector
from panda_lib.hardware import ArduinoLink, PandaMill
from panda_lib.hardware.imaging.camera_factory import CameraFactory
from panda_lib.hardware.imaging import CameraType
from panda_lib.hardware.panda_pipettes import Pipette, insert_new_pipette
from panda_lib.toolkit import Toolkit


def main():
    # Logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    log = logging.getLogger("panda")

    # 1) DB: ensure an active pipette record exists
    insert_new_pipette(capacity=300, activate=True, session_maker=SessionLocal)

    # 2) Hardware Toolkit (mirror your example)
    tools = Toolkit(
        mill=PandaMill(),
        arduino=ArduinoLink("/dev/ttyACM1"),
        camera=CameraFactory.create_camera(camera_type=CameraType.FLIR),
        global_logger=log,
    )

    # 3) Hardware pipette attached to toolkit
    tools.pipette = Pipette(arduino=tools.arduino)
    tools.mill.connect_to_mill()
    if not tools.mill.ser_mill:
        raise RuntimeError("Failed to open mill serial port. Check USB/tty path.")
    tools.mill.homing_sequence()
    tools.mill.set_feed_rate(5000)
    # Sanity checks (fail fast with a clear message if config is wrong)
    assert tools.pipette is not None, "No pipette attached to Toolkit"
    assert getattr(tools.pipette, "pipette_tracker", None), "pipette_tracker missing"
    assert getattr(tools.pipette.pipette_tracker, "capacity_ul", 0) > 0, (
        "capacity_ul invalid"
    )

    for i in range(18):
        log.info("Beginning transfer operations... %d of 18", i + 1)

        # IMPORTANT: pass the sessionmaker factory, not a live Session()
        src = solution_selector("water", 100.0, db_session=SessionLocal)
        dst = waste_selector("waste", 100.0, db_session=SessionLocal)

        transfer(
            src_vessel=src,
            dst_vessel=dst,
            volume=100.0,
            toolkit=tools,  # Toolkit instance with pipette attached
        )

    print("Experiment completed successfully.")


if __name__ == "__main__":
    main()
