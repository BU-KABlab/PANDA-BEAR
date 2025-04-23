"""A class to hold all of the instruments"""

import logging
import os
from dataclasses import dataclass
from logging import Logger
from typing import Union

import PySpin
from sartorius import Scale
from sartorius.mock import Scale as MockScale

from panda_lib.hardware.panda_pipette.syringepump import MockPump, SyringePump
from panda_lib.hardware import ArduinoLink, MockArduinoLink
from panda_lib.labware.vials import StockVial, WasteVial, read_vials
from panda_lib.labware.wellplates import Wellplate
from panda_lib.hardware.gantry_interface import MockPandaMill as MockMill
from panda_lib.hardware.gantry_interface import PandaMill as Mill
from panda_lib.slack_tools.slackbot_module import SlackBot
from shared_utilities.config.config_tools import (
    read_camera_type,
    read_config_value,
    read_webcam_settings,
)

if os.name == "nt":
    from hardware.gamry_potentiostat import gamry_control
else:
    pass


class Toolkit:
    def __init__(self, use_mock_instruments=False):
        # Initialize hardware components with fallbacks
        self.initialize_camera(use_mock_instruments)

    mill: Union[Mill, MockMill, None]
    scale: Union[Scale, MockScale, None]
    pump: Union[SyringePump, MockPump, None]
    wellplate: Wellplate = None
    global_logger: Logger = None
    experiment_logger: Logger = None
    arduino: ArduinoLink = None

    def initialize_camera(self, use_mock=False):
        # Try to use FLIR camera if available, otherwise fall back to OpenCV or mock
        if not use_mock:
            try:
                from panda_lib.hardware.imaging.flir_camera import FlirCamera
                if FlirCamera.is_available():
                    self.camera = FlirCamera()
                    return
            except ImportError:
                pass
        
        # Fallback to OpenCV
        from panda_lib.hardware.imaging.open_cv_camera import OpenCVCamera
        self.camera = OpenCVCamera()

class Hardware:
    """A class to hold all of the hardware"""
    def __init__(self, use_mock_instruments=False):
        # Initialize hardware components with fallbacks
        self.initialize_camera(use_mock_instruments)

    mill: Union[Mill, MockMill, None] = None
    scale: Union[Scale, MockScale, None] = None
    pump: Union[SyringePump, MockPump, None] = None
    arduino: ArduinoLink = None
    # inlcude the global logger so that the hardware can log to the same file
    global_logger: Logger = None
    experiment_logger: Logger = None

    def initialize_camera(self, use_mock=False):
        # Try to use FLIR camera if available, otherwise fall back to OpenCV or mock
        if not use_mock:
            try:
                from panda_lib.hardware.imaging.flir_camera import FlirCamera
                if FlirCamera.is_available():
                    self.camera = FlirCamera()
                    return
            except ImportError:
                pass
        
        # Fallback to OpenCV
        from panda_lib.hardware.imaging.open_cv_camera import OpenCVCamera
        self.camera = OpenCVCamera()

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
            instruments.camera = MockOpenCVCamera(
                camera_id=webcam_id, resolution=resolution
            )
            instruments.camera.connect()
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
        instruments.mill.homing_sequence()
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
    if camera_type:
        if camera_type.lower() == "webcam":
            try:
                logger.debug("Connecting to Webcam")
                webcam_id, resolution = read_webcam_settings()
                instruments.camera = OpenCVCamera(
                    camera_id=webcam_id, resolution=resolution
                )

                if not instruments.camera.connect():
                    logger.error(f"Failed to connect to webcam with ID {webcam_id}")
                    instruments.camera = None
                    incomplete = True
                else:
                    logger.debug(
                        f"Connected to webcam ID {webcam_id} at resolution {resolution}"
                    )
            except Exception as error:
                logger.error(f"No webcam connected, {error}")
                instruments.camera = None
                incomplete = True
        else:
            # Default to FLIR camera
            try:
                logger.debug("Connecting to FLIR Camera")
                system = PySpin.System.GetInstance()
                cam_list = system.GetCameras()
                if cam_list.GetSize() == 0:
                    logger.error("No FLIR Camera connected")
                    instruments.camera = None
                else:
                    instruments.camera = cam_list.GetByIndex(0)
                    # instruments.flir_camera.Init()
                    cam_list.Clear()
                    system.ReleaseInstance()

                    logger.debug("Connected to FLIR Camera")
            except Exception as error:
                logger.error("No FLIR Camera connected, %s", error)
                instruments.camera = None
                incomplete = True
    else:
        logger.error("No camera type specified in the configuration file")
        instruments.camera = None
        incomplete = False

    # Connect to PSTAT

    # Connect to Arduino
    try:
        logger.debug("Connecting to Arduino")
        arduino = ArduinoLink(port_address=read_config_value("ARDUINO", "port"))
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
    """Connects to each instrument, but does not trigger any action. Only tests if connection can be established.
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
        arduino=None,
        global_logger=logger,
        experiment_logger=logger,
        flir_camera=None,
        opencv_camera=None,
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
        instruments.pump = MockPump()
        instruments.arduino = MockArduinoLink()

        # Setup mock camera based on the config
        if camera_type.lower() == "webcam":
            webcam_id, resolution = read_webcam_settings()
            instruments.camera = MockOpenCVCamera(
                camera_id=webcam_id, resolution=resolution
            )
            instruments.camera.connect()
        print("\nMock instruments initialized successfully!")
        return instruments, True

    incomplete = False
    logger.info("Connecting to instruments:")

    # Mill connection
    print("Checking mill connection...", end="\r", flush=True)
    try:
        logger.debug("Connecting to mill")
        mill = Mill()
        mill.connect_to_mill()
        print("Mill connected                        ", flush=True)
        connected_instruments.append("Mill")
        mill.disconnect()
    except Exception as error:
        logger.error("No mill connected, %s", error)
        print("Mill not found                        ", flush=True)
        disconnected_instruments.append("Mill")
        incomplete = True

    # Scale connection
    print("Checking scale connection...", end="\r", flush=True)
    try:
        port = read_config_value("SCALE", "port")
        if not port:
            raise Exception("No scale port specified in the configuration file")
        logger.debug("Connecting to scale")
        scale = Scale(address=port)
        if scale.hw.open:
            info_dict = scale.get_info()
            model = info_dict["model"]
            if not model:
                scale.hw.close()
                raise Exception("Scale connected but no model information returned")
            logger.debug("Connected to scale: %s", model)
            print("Scale connected                        ", flush=True)
            connected_instruments.append("Scale")
            scale.hw.close()
        else:
            raise Exception("Failed to open connection to scale")
    except Exception as error:
        logger.error("No scale connected, %s", error)
        print("Scale not found                        ", flush=True)
        disconnected_instruments.append("Scale")
        incomplete = True

    # Pump connection
    print("Checking pump connection...", end="\r", flush=True)
    try:
        logger.debug("Connecting to pump")
        pump = SyringePump()
        if pump.connected:
            logger.debug("Connected to pump at %s", pump.pump.address)
            print("Pump connected                        ", flush=True)
            connected_instruments.append("Pump")
        else:
            raise Exception("Failed to connect to pump")
        pump.close()
    except Exception as error:
        logger.error("No pump connected, %s", error)
        print("Pump not found                        ", flush=True)
        disconnected_instruments.append("Pump")
        incomplete = True

    # Check for camera based on the configuration
    print("Checking camera connection...", end="\r", flush=True)
    if camera_type.lower() == "webcam":
        try:
            logger.debug("Connecting to Webcam")
            webcam_id, resolution = read_webcam_settings()
            camera = OpenCVCamera(camera_id=webcam_id, resolution=resolution)

            if not camera.connect():
                raise Exception(f"Failed to connect to webcam with ID {webcam_id}")

            logger.debug(
                f"Connected to webcam ID {webcam_id} at resolution {resolution}"
            )
            print("Webcam connected                        ", flush=True)
            connected_instruments.append("Webcam")
            camera.close()
        except Exception as error:
            logger.error(f"No webcam connected, {error}")
            print("Webcam not found                        ", flush=True)
            disconnected_instruments.append("Webcam")
            incomplete = True
    else:
        # Default to FLIR camera
        try:
            logger.debug("Connecting to FLIR Camera")
            system = PySpin.System.GetInstance()
            cam_list = system.GetCameras()
            if cam_list.GetSize() == 0:
                raise Exception("No FLIR Camera found")

            camera = cam_list.GetByIndex(0)
            logger.debug("Connected to FLIR Camera")
            print("FLIR Camera connected                        ", flush=True)
            connected_instruments.append("FLIR Camera")

            # Clean up
            cam_list.Clear()
            system.ReleaseInstance()
        except Exception as error:
            logger.error("No FLIR Camera connected, %s", error)
            print("FLIR Camera not found                        ", flush=True)
            disconnected_instruments.append("FLIR Camera")
            incomplete = True

    # Potentiostat connection
    print("Checking Potentiostat connection...", end="\r", flush=True)
    try:
        if os.name == "nt":
            logger.debug("Connecting to Potentiostat")
            connected = gamry_control.pstatconnect()
            if not connected:
                raise Exception("Failed to connect to Potentiostat")

            logger.debug("Connected to Potentiostat")
            print("Potentiostat connected                        ", flush=True)
            connected_instruments.append("Potentiostat")
            gamry_control.pstatdisconnect()
        else:
            logger.debug(
                "Gamry Potentiostat connection not available on non-Windows OS"
            )
            print(
                "Gamry Potentiostat connection not available on non-Windows OS",
                flush=True,
            )
            connected_instruments.append("Potentiostat")
            incomplete = True
    except Exception as error:
        logger.error("Error connecting to Potentiostat, %s", error)
        print("Potentiostat not found                        ", flush=True)
        disconnected_instruments.append("Potentiostat")
        incomplete = True

    # Arduino connection
    print("Checking Arduino connection...", end="\r", flush=True)
    try:
        logger.debug("Connecting to Arduino")
        arduino = ArduinoLink(port_address=read_config_value("ARDUINO", "port"))
        if not arduino.configured:
            raise Exception("Arduino not properly configured")

        logger.debug("Connected to Arduino")
        print("Arduino connected                        ", flush=True)
        connected_instruments.append("Arduino")
        arduino.close()
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
    if instruments.camera:
        instruments.camera.close()
    if instruments.arduino:
        instruments.arduino.close()
    if instruments.scale:
        instruments.scale.hw.close()
    if instruments.pump:
        instruments.pump.close()
