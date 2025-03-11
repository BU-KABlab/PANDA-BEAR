"""A class to hold all of the instruments"""

import logging
from dataclasses import dataclass
from logging import Logger
from typing import Union

import PySpin

from hardware.gamry_potentiostat import gamry_control
from hardware.panda_pipette.syringepump import MockPump, SyringePump
from hardware.sartorius.sartorius import Scale
from hardware.sartorius.sartorius.mock import Scale as MockScale
from panda_lib.imaging.open_cv_camera import MockOpenCVCamera, OpenCVCamera
from panda_lib.labware.deck import Deck
from panda_lib.labware.labware_definitions import LabwareRegistry
from panda_lib.labware.vials import StockVial, WasteVial, read_vials
from panda_lib.labware.wellplates import Wellplate
from panda_lib.panda_gantry import MockPandaMill as MockMill
from panda_lib.panda_gantry import PandaMill as Mill
from panda_lib.slack_tools.slackbot_module import SlackBot
from panda_lib.tools import ArduinoLink, MockArduinoLink, OBSController
from shared_utilities.config.config_tools import (
    read_camera_type,
    read_config_value,
    read_webcam_settings,
)


@dataclass
class Toolkit:
    """A class to hold all of the instruments"""

    mill: Union[Mill, MockMill, None]
    scale: Union[Scale, MockScale, None]
    pump: Union[SyringePump, MockPump, None]
    wellplate: Wellplate = None
    global_logger: Logger = None
    experiment_logger: Logger = None
    flir_camera: PySpin.Camera = None
    opencv_camera: Union[OpenCVCamera, MockOpenCVCamera, None] = None
    arduino: ArduinoLink = None
    deck: Deck = None
    labware_registry: LabwareRegistry = None


@dataclass
class Hardware:
    """A class to hold all of the hardware"""

    mill: Union[Mill, MockMill, None] = None
    scale: Union[Scale, MockScale, None] = None
    pump: Union[SyringePump, MockPump, None] = None
    flir_camera: PySpin.Camera = None
    opencv_camera: Union[OpenCVCamera, MockOpenCVCamera, None] = None
    arduino: ArduinoLink = None
    # inlcude the global logger so that the hardware can log to the same file
    global_logger: Logger = None
    experiment_logger: Logger = None


@dataclass
class Labware:
    """A class to hold all of the labware"""

    wellplate: Wellplate = None
    # include the global logger so that the labware can log to the same file
    global_logger: Logger = None

    @property
    def stock_vials(self) -> list[StockVial]:
        return read_vials("stock")[0]  # TODO: Fix this

    @property
    def waste_vials(self) -> list[WasteVial]:
        return read_vials("waste")[0]  # TODO: Fix this


@dataclass
class Monitoring:
    """A class to hold all of the monitoring tools"""

    slack_monitor: SlackBot = None
    obs: OBSController = None


def connect_to_instruments(
    use_mock_instruments: bool = True,
    logger: Logger = logging.getLogger("panda"),
) -> tuple[Toolkit, bool]:
    """Connect to the PANDA SDL instruments:
    - Mill
    - Scale
    - Pump
    - Camera (FLIR or Webcam)
    - Arduino
    Args:
        use_mock_instruments (bool, optional): Whether to use mock instruments. Defaults to True.
        logger (Logger, optional): The logger object. Defaults to "panda" logger.

    Returns:
        tuple[Toolkit, bool]: A tuple containing the Toolkit object and a boolean indicating if all instruments were connected successfully.

    """
    instruments = Toolkit(
        mill=None,
        scale=None,
        pump=None,
        wellplate=None,
        global_logger=logger,
        experiment_logger=logger,
        flir_camera=None,
        opencv_camera=None,
        arduino=None,
        deck=Deck(),
        labware_registry=LabwareRegistry(),
    )

    # Determine which type of camera to use
    camera_type = read_camera_type()
    logger.debug(f"Camera type set to: {camera_type}")

    if use_mock_instruments:
        logger.info("Using mock instruments")
        instruments.mill = MockMill()
        instruments.mill.connect_to_mill()
        # instruments.scale = MockScale()
        instruments.pump = MockPump()
        # pstat = echem_mock.GamryPotentiostat.connect()
        instruments.arduino = MockArduinoLink()

        # Setup mock camera based on the config
        if camera_type.lower() == "webcam":
            webcam_id, resolution = read_webcam_settings()
            instruments.opencv_camera = MockOpenCVCamera(
                camera_id=webcam_id, resolution=resolution
            )
            instruments.opencv_camera.connect()
        else:
            # No mock FLIR camera setup needed, it's handled elsewhere
            pass

        return instruments, True

    incomplete = False
    logger.info("Connecting to instruments:")
    try:
        logger.debug("Connecting to mill")
        instruments.mill = Mill()
        instruments.mill.connect_to_mill()
        # instruments.mill.homing_sequence()
    except Exception as error:
        logger.error("No mill connected, %s", error)
        instruments.mill = None
        # raise error
        incomplete = True

    # try:
    #     logger.debug("Connecting to scale")
    #     scale = Scale(address="COM6")
    #     info_dict = scale.get_info()
    #     model = info_dict["model"]
    #     serial = info_dict["serial"]
    #     software = info_dict["software"]
    #     if not model:
    #         logger.error("No scale connected")
    #         # raise Exception("No scale connected")
    #     logger.debug("Connected to scale:\n%s\n%s\n%s\n", model, serial, software)
    # except Exception as error:
    #     logger.error("No scale connected, %s", error)
    #     instruments.scale = None
    #     # raise error
    #     incomplete = True

    try:
        logger.debug("Connecting to pump")
        instruments.pump = SyringePump()
        logger.debug("Connected to pump at %s", instruments.pump.pump.address)

    except Exception as error:
        logger.error("No pump connected, %s", error)
        instruments.pump = None
        # raise error
        incomplete = True

    # Check for camera based on the configuration
    if camera_type.lower() == "webcam":
        try:
            logger.debug("Connecting to Webcam")
            webcam_id, resolution = read_webcam_settings()
            instruments.opencv_camera = OpenCVCamera(
                camera_id=webcam_id, resolution=resolution
            )

            if not instruments.opencv_camera.connect():
                logger.error(f"Failed to connect to webcam with ID {webcam_id}")
                instruments.opencv_camera = None
                incomplete = True
            else:
                logger.debug(
                    f"Connected to webcam ID {webcam_id} at resolution {resolution}"
                )
        except Exception as error:
            logger.error(f"No webcam connected, {error}")
            instruments.opencv_camera = None
            incomplete = True
    else:
        # Default to FLIR camera
        try:
            logger.debug("Connecting to FLIR Camera")
            system = PySpin.System.GetInstance()
            cam_list = system.GetCameras()
            if cam_list.GetSize() == 0:
                logger.error("No FLIR Camera connected")
                instruments.flir_camera = None
            else:
                instruments.flir_camera = cam_list.GetByIndex(0)
                # instruments.flir_camera.Init()
                cam_list.Clear()
                system.ReleaseInstance()

                logger.debug("Connected to FLIR Camera")
        except Exception as error:
            logger.error("No FLIR Camera connected, %s", error)
            instruments.flir_camera = None
            incomplete = True

    # Connect to PSTAT

    # Connect to Arduino
    try:
        logger.debug("Connecting to Arduino")
        arduino = ArduinoLink()
        if not arduino.configured:
            logger.error("No Arduino connected")
            incomplete = True
            instruments.arduino = None
        logger.debug("Connected to Arduino")
        instruments.arduino = arduino
    except Exception as error:
        logger.error("Error connecting to Arduino, %s", error)
        incomplete = True

    if incomplete:
        print("Not all instruments connected")
        return instruments, False

    logger.info("Connected to instruments")
    return instruments, True


def test_instrument_connections(
    use_mock_instruments: bool = True,
    logger: Logger = logging.getLogger("panda"),
) -> tuple[Toolkit, bool]:
    """Connects to each instrument, but does not trigger any action. Only looks for connection to be established.
    Args:
        use_mock_instruments (bool, optional): Whether to use mock instruments. Defaults to True.
        logger (Logger, optional): The logger object. Defaults to "panda" logger.

    Returns:
        tuple[Toolkit, bool]: A tuple containing the Toolkit object and a boolean indicating if all instruments were connected successfully."""
    instruments = Toolkit(
        mill=None,
        scale=None,
        pump=None,
        wellplate=None,
        arduino=None,
        global_logger=logger,
        experiment_logger=logger,
        flir_camera=None,
        opencv_camera=None,
        deck=Deck(),
        labware_registry=LabwareRegistry(),
    )

    # Track connected and disconnected instruments for summary
    connected_instruments = []
    disconnected_instruments = []
    # Determine which type of camera to use
    camera_type = read_camera_type()
    logger.debug(f"Camera type set to: {camera_type}")

    if use_mock_instruments:
        logger.info("Using mock instruments")
        print("Using mock instruments")
        instruments.mill = MockMill()
        instruments.mill.connect_to_mill()
        # instruments.scale = MockScale()
        instruments.pump = MockPump()
        instruments.arduino = MockArduinoLink()
        # pstat = echem_mock.GamryPotentiostat.connect()

        # Setup mock camera based on the config
        if camera_type.lower() == "webcam":
            webcam_id, resolution = read_webcam_settings()
            instruments.opencv_camera = MockOpenCVCamera(
                camera_id=webcam_id, resolution=resolution
            )
            instruments.opencv_camera.connect()
        print("\nMock instruments initialized successfully!")
        return instruments, True

    incomplete = False
    logger.info("Connecting to instruments:")

    # Mill connection
    print("Checking mill connection...", end="\r", flush=True)
    try:
        logger.debug("Connecting to mill")
        instruments.mill = Mill()
        instruments.mill.connect_to_mill()
        print("Mill connected                        ", flush=True)
        connected_instruments.append("Mill")
    except Exception as error:
        logger.error("No mill connected, %s", error)
        instruments.mill = None
        print("Mill not found                        ", flush=True)
        disconnected_instruments.append("Mill")
        incomplete = True

    print("Checking scale connection...", end="\r", flush=True)
    try:
        if not read_config_value("SCALE", "port"):
            raise Exception("No scale port specified in the configuration file")
        logger.debug("Connecting to scale")
        scale = Scale(address=read_config_value("SCALE", "port"))
        info_dict = scale.get_info()
        model = info_dict["model"]
        serial = info_dict["serial"]
        software = info_dict["software"]
        if not model:
            logger.error("No scale connected")
            print("Scale not found                        ", flush=True)
            disconnected_instruments.append("Scale")
            incomplete = True
        else:
            logger.debug("Connected to scale:\n%s\n%s\n%s\n", model, serial, software)
            print("Scale connected                        ", flush=True)
            connected_instruments.append("Scale")
    except Exception as error:
        logger.error("No scale connected, %s", error)
        instruments.scale = None
        print("Scale not found                        ", flush=True)
        disconnected_instruments.append("Scale")
        incomplete = True

    # Pump connection
    print("Checking pump connection...", end="\r", flush=True)
    try:
        logger.debug("Connecting to pump")
        instruments.pump = SyringePump()
        logger.debug("Connected to pump at %s", instruments.pump.pump.address)
        print("Pump connected                        ", flush=True)
        connected_instruments.append("Pump")
    except Exception as error:
        logger.error("No pump connected, %s", error)
        instruments.pump = None
        print("Pump not found                        ", flush=True)
        disconnected_instruments.append("Pump")
        incomplete = True

    # Check for camera based on the configuration
    print("Checking camera connection...", end="\r", flush=True)
    if camera_type.lower() == "webcam":
        try:
            logger.debug("Connecting to Webcam")
            webcam_id, resolution = read_webcam_settings()
            instruments.opencv_camera = OpenCVCamera(
                camera_id=webcam_id, resolution=resolution
            )

            if not instruments.opencv_camera.connect():
                logger.error(f"Failed to connect to webcam with ID {webcam_id}")
                print("Webcam not found                        ", flush=True)
                disconnected_instruments.append("Webcam")
                instruments.opencv_camera = None
                incomplete = True
            else:
                logger.debug(
                    f"Connected to webcam ID {webcam_id} at resolution {resolution}"
                )
                print("Webcam connected                        ", flush=True)
                connected_instruments.append("Webcam")
                # Disconnect immediately after testing connection
                instruments.opencv_camera.disconnect()
        except Exception as error:
            logger.error(f"No webcam connected, {error}")
            instruments.opencv_camera = None
            incomplete = True
    else:
        # Default to FLIR camera
        try:
            logger.debug("Connecting to FLIR Camera")
            system = PySpin.System.GetInstance()
            cam_list = system.GetCameras()
            if cam_list.GetSize() == 0:
                logger.error("No FLIR Camera connected")
                print("FLIR Camera not found                        ", flush=True)
                disconnected_instruments.append("FLIR Camera")
                instruments.flir_camera = None
                incomplete = True
            else:
                instruments.flir_camera = cam_list.GetByIndex(0)
                # instruments.flir_camera.Init()
                cam_list.Clear()
                system.ReleaseInstance()

                logger.debug("Connected to FLIR Camera")
                print("FLIR Camera connected                        ", flush=True)
                connected_instruments.append("FLIR Camera")

        except Exception as error:
            logger.error("No FLIR Camera connected, %s", error)
            instruments.flir_camera = None
            print("FLIR Camera not found                        ", flush=True)
            disconnected_instruments.append("FLIR Camera")
            incomplete = True

    # Potentiostat connection
    print("Checking Potentiostat connection...", end="\r", flush=True)
    try:
        logger.debug("Connecting to Potentiostat")
        connected = gamry_control.pstatconnect()
        if not connected:
            logger.error("No Potentiostat connected")
            print("Potentiostat not found                        ", flush=True)
            disconnected_instruments.append("Potentiostat")
            incomplete = True
        else:
            logger.debug("Connected to Potentiostat")
            gamry_control.pstatdisconnect()
            print("Potentiostat connected                        ", flush=True)
            connected_instruments.append("Potentiostat")
    except Exception as error:
        logger.error("Error connecting to Potentiostat, %s", error)
        print("Potentiostat not found                        ", flush=True)
        disconnected_instruments.append("Potentiostat")
        incomplete = True

    # Arduino connection
    print("Checking Arduino connection...", end="\r", flush=True)
    try:
        logger.debug("Connecting to Arduino")
        with ArduinoLink() as arduino:
            if not arduino.configured:
                logger.error("No Arduino connected")
                incomplete = True
                instruments.arduino = None
                print("Arduino not found                        ", flush=True)
                disconnected_instruments.append("Arduino")
            else:
                logger.debug("Connected to Arduino")
                instruments.arduino = arduino
                print("Arduino connected                        ", flush=True)
                connected_instruments.append("Arduino")
    except Exception as error:
        logger.error("Error connecting to Arduino, %s", error)
        print("Arduino not found                        ", flush=True)
        disconnected_instruments.append("Arduino")
        incomplete = True

    # Print summary
    print("\n----- Connection Summary -----")
    if connected_instruments:
        print("Connected instruments:")
        for instrument in connected_instruments:
            print(f"  ✓ {instrument}")

    if disconnected_instruments:
        print("Disconnected instruments:")
        for instrument in disconnected_instruments:
            print(f"  ✗ {instrument}")

    if incomplete:
        print("\nWarning: Not all instruments connected")
        logger.warning("Not all instruments connected")
    else:
        print("\nAll instruments successfully connected")
        logger.info("Connected to all instruments")

    return instruments, not incomplete


def disconnect_from_instruments(instruments: Toolkit):
    """Disconnect from the instruments"""
    if instruments.mill:
        instruments.mill.disconnect()
    # if instruments.flir_camera: instruments.flir_camera.DeInit()
    if instruments.opencv_camera:
        instruments.opencv_camera.disconnect()
    if instruments.arduino:
        instruments.arduino.close()
