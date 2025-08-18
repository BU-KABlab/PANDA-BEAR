"""A class to hold all of the instruments"""

import logging
import os
from dataclasses import dataclass
from logging import Logger
from typing import Union

from panda_lib.hardware import ArduinoLink, PandaMill
from panda_lib.hardware.imaging.camera_factory import CameraFactory, CameraType
from panda_lib.hardware.imaging.interface import CameraInterface
from panda_lib.hardware.panda_pipettes import (
    Pipette,
)
from panda_lib.labware.vials import StockVial, WasteVial, read_vials
from panda_lib.labware.wellplates import Wellplate
from panda_lib.slack_tools.slackbot_module import SlackBot
from panda_shared.config.config_tools import (
    read_camera_type,
    read_config_value,
    read_webcam_settings,
)
from panda_lib.hardware.panda_pipettes.ot2_pipette.ot2P300 import OT2P300


if os.name == "nt":
    from panda_lib.hardware.gamry_potentiostat import gamry_control
else:
    pass


class Toolkit:
    def __init__(self, use_mock_instruments=False, **kwargs):
        """
        Initialize hardware components with fallbacks

        Args:
            use_mock_instruments (bool, optional): Whether to use mock instruments. Defaults to False.
            **kwargs: Additional keyword arguments for hardware components.
                - mill: The mill object (PandaMill or MockPandaMill)
                - scale: The scale object (Scale or MockScale)
                - pipette: The pipette object (Pipette)
                - wellplate: The wellplate object (Wellplate)
                - arduino: The Arduino object (ArduinoLink)
                - slack_monitor: The Slack monitor object (SlackBot)
                - global_logger: The global logger object (Logger)
                - experiment_logger: The experiment logger object (Logger)

        """
        self.camera = kwargs.get("camera", None)
        if self.camera is None:
            self.initialize_camera(use_mock_instruments)
        self.mill = kwargs.get("mill", None)
        self.scale = kwargs.get("scale", None)
        self.pipette = kwargs.get("pipette", None)
        self.wellplate = kwargs.get("wellplate", None)
        self.arduino = kwargs.get("arduino", None)
        self.slack_monitor = kwargs.get("slack_monitor", None)
        self.global_logger = kwargs.get("global_logger", None)
        self.experiment_logger = kwargs.get("experiment_logger", None)

    mill: Union[PandaMill, None] = None
    # scale: Union[Scale, None] = None
    pipette: Union[Pipette, None] = None
    wellplate: Wellplate = None
    arduino: ArduinoLink = None
    global_logger: Logger = None
    experiment_logger: Logger = None
    camera: Union[None, CameraInterface] = None
    slack_monitor: SlackBot = None

    def initialize_camera(self, use_mock=False):
        """Initialize the appropriate camera using the factory"""
        camera_type = read_camera_type().lower()
        if use_mock:
            camera_type_enum = CameraType.MOCK
        elif camera_type == "flir":
            camera_type_enum = CameraType.FLIR
        else:
            camera_type_enum = CameraType.OPENCV

        # Get camera parameters
        if camera_type_enum in [CameraType.OPENCV, CameraType.MOCK]:
            webcam_id, resolution = read_webcam_settings()
            self.camera = CameraFactory.create_camera(
                camera_type=camera_type_enum, camera_id=webcam_id, resolution=resolution
            )
        else:
            self.camera = CameraFactory.create_camera(camera_type=camera_type_enum)

        # If camera creation failed or PySpin wasn't available, fallback to OpenCV
        if self.camera is None:
            webcam_id, resolution = read_webcam_settings()
            self.camera = CameraFactory.create_camera(
                camera_type=CameraType.OPENCV if not use_mock else CameraType.MOCK,
                camera_id=webcam_id,
                resolution=resolution,
            )

    def disconnect(self):
        """Disconnect from the instruments"""
        if self.mill:
            self.mill.disconnect()
        # if self.flir_camera: self.flir_camera.DeInit()
        if self.camera:
            self.camera.close()
        if self.arduino:
            self.arduino.close()
        #if self.scale:
        #    self.scale.hw.close()
        if self.pipette:
            self.pipette.close()


class Hardware:
    """A class to hold all of the hardware"""

    def __init__(self, use_mock_instruments=False, **kwargs):
        # Initialize hardware components with fallbacks
        self.camera = kwargs.get("camera", None)
        if self.camera is None:
            self.initialize_camera(use_mock_instruments)
        self.mill = kwargs.get("mill", None)
        #self.scale = kwargs.get("scale", None)
        self.pipette = kwargs.get("pipette", None)
        self.wellplate = kwargs.get("wellplate", None)
        self.arduino = kwargs.get("arduino", None)
        self.slack_monitor = kwargs.get("slack_monitor", None)
        self.global_logger = kwargs.get("global_logger", None)
        self.experiment_logger = kwargs.get("experiment_logger", None)

    mill: Union[PandaMill, None] = None
    #scale: Union[Scale, None] = None
    pipette: Union[Pipette, None] = None
    arduino: ArduinoLink = None
    # include the global logger so that the hardware can log to the same file
    global_logger: Logger = None
    experiment_logger: Logger = None
    camera: Union[None, CameraInterface] = None

    def initialize_camera(self, use_mock=False):
        """Initialize the appropriate camera using the factory"""
        camera_type = read_camera_type().lower()
        if use_mock:
            camera_type_enum = CameraType.MOCK
        elif camera_type == "flir":
            camera_type_enum = CameraType.FLIR
        else:
            camera_type_enum = CameraType.OPENCV

        # Get camera parameters
        if camera_type_enum in [CameraType.OPENCV, CameraType.MOCK]:
            webcam_id, resolution = read_webcam_settings()
            self.camera = CameraFactory.create_camera(
                camera_type=camera_type_enum, camera_id=webcam_id, resolution=resolution
            )
        else:
            self.camera = CameraFactory.create_camera(camera_type=camera_type_enum)

        # If camera creation failed or PySpin wasn't available, fallback to OpenCV
        if self.camera is None:
            webcam_id, resolution = read_webcam_settings()
            self.camera = CameraFactory.create_camera(
                camera_type=CameraType.OPENCV if not use_mock else CameraType.MOCK,
                camera_id=webcam_id,
                resolution=resolution,
            )


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
    - PandaMill
    - Scale
    - Pipette
    - Camera (FLIR or Webcam)
    - Arduino
    Args:
        use_mock_instruments (bool, optional): Whether to use mock instruments. Defaults to True.
        logger (Logger, optional): The logger object. Defaults to "panda" logger.

    Returns:
        tuple[Toolkit, bool]: A tuple containing the Toolkit object and a boolean indicating if all instruments were connected successfully.

    """
    instruments = Toolkit(
        use_mock_instruments=use_mock_instruments,
        mill=None,
        #scale=None,
        pipette=None,
        wellplate=None,
        global_logger=logger,
        experiment_logger=logger,
        camera=CameraFactory.create_camera(camera_type=CameraType.FLIR),
        arduino=None,
    )

    if use_mock_instruments:
        logger.info("Using mock instruments")
        instruments.mill = PandaMill()
        instruments.mill.connect_to_mill()
        instruments.pipette = Pipette()
        # pstat = echem_mock.GamryPotentiostat.connect()
        instruments.arduino = ArduinoLink()

        # Initialize the camera if it wasn't done in the Toolkit constructor
        if instruments.camera is None:
            instruments.initialize_camera(use_mock=True)

        return instruments, True

    incomplete = False
    logger.info("Connecting to instruments:")
    try:
        logger.debug("Connecting to mill")
        instruments.mill = PandaMill()
        instruments.mill.connect_to_mill()
        instruments.mill.homing_sequence()
    except Exception as error:
        logger.error("No mill connected, %s", error)
        instruments.mill = None
        # raise error
        incomplete = True

    # Initialize the camera
    logger.debug("Connecting to camera")
    #if instruments.camera is None:
    #    instruments.initialize_camera(use_mock=False)

    # Connect to the camera
    if instruments.camera is not None:
        if instruments.camera.connect():
            logger.error("Connected to FLIR camera successfully")
        else:
            logger.debug("Failed to connect to FLIR camera")
    else:
        logger.error("Failed to initialize FLIR camera")
        incomplete = True

    # Connect to Arduino
    try:
        cfg_port = (read_config_value("ARDUINO", "port") or "").strip()
        # try the configured value first; if it's not "auto", also try auto as a fallback
        candidates = [cfg_port] if cfg_port else []
        if cfg_port.lower() != "auto":
            candidates.append("auto")
        if not candidates:
            candidates = ["auto"]

        arduino = None
        for cand in candidates:
            try:
                logger.debug("Connecting to Arduino (port=%r)...", cand)
                arduino = ArduinoLink(port_address=cand)
                if arduino.configured:
                    instruments.arduino = arduino
                    logger.debug("Connected to Arduino on %s", arduino.port_address)
                    break
            except Exception as e:
                logger.warning("Connect failed using %r: %s", cand, e, exc_info=True)
                arduino = None

        if not arduino or not arduino.configured:
            logger.error("No Arduino connected (tried: %s)", ", ".join(map(repr, candidates)))
            incomplete = True
            instruments.arduino = None

    except Exception as error:
        logger.error("Error connecting to Arduino: %s", error, exc_info=True)
        incomplete = True
        instruments.arduino = None


    # Connect to the pump or pipette depending on configuration
    # Check if the config specifies a syringe pump. If not skip the check
    '''
    syringe_pump = read_config_value("PIPETTE", "PIPETTE_TYPE")
    pump_port = read_config_value("PUMP", "PORT")

    if not pump_port:
        logger.warning(
            "No pump port specified in the configuration file. Will check for Pipette"
        )
        instruments.pipette = None
        incomplete = True
    elif syringe_pump in ["OT2", "ot2"]:
        logger.debug("Connecting to OT2 Pipette")
        try:
            if instruments.arduino is None:
                raise Exception("No Arduino connected")
            stepper = instruments.arduino
            instruments.pipette = Pipette.from_config(stepper=stepper)
            status = instruments.pipette.get_status()
            if status:
                logger.debug("Connected to OT2 Pipette")
            else:
                raise Exception("Failed to connect to OT2 Pipette")
        except Exception as error:
            logger.error("No OT2 Pipette connected, %s", error)
            instruments.pipette = None
            incomplete = True
    '''
    # TODO: look into why the pump logic wasn't working, for now....specify pipette directly instead of syringe pump because it wasn't connecting to the pipette
    try:
        if instruments.arduino is None:
            raise Exception("No Arduino connected")
        instruments.pipette = OT2P300(arduino=instruments.arduino)
        status = instruments.pipette.get_status()
        if status:
            logger.debug("Connected to OT2 Pipette")
        else:
            raise Exception("Failed to connect to OT2 Pipette")
    except Exception as error:
        logger.error("No OT2 Pipette connected, %s", error)
        instruments.pipette = None
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
        use_mock_instruments=use_mock_instruments,
        mill=None,
        #scale=None,
        pipette=None,
        wellplate=None,
        arduino=None,
        global_logger=logger,
        experiment_logger=logger,
        camera=None,
    )

    # Track connected and disconnected instruments for summary
    connected_instruments = []
    disconnected_instruments = []

    if use_mock_instruments:
        logger.info("Using mock instruments")
        print("Using mock instruments")
        instruments.mill = PandaMill()
        instruments.mill.connect_to_mill()
        instruments.pipette = Pipette()
        instruments.arduino = ArduinoLink()
        #instruments.scale = Scale()
        # Initialize the camera (mock)
        instruments.initialize_camera(use_mock=True)
        connected_instruments = ["PandaMill", "Pipette", "Arduino", "Camera"]

        print("\nMock instruments initialized successfully!")
        return instruments, True

    incomplete = False
    logger.info("Connecting to instruments:")

    # PandaMill connection
    print("Checking mill connection...", end="\r", flush=True)
    try:
        logger.debug("Connecting to mill")
        mill = PandaMill()
        mill.connect_to_mill()
        print("PandaMill connected                        ", flush=True)
        connected_instruments.append("PandaMill")
        mill.disconnect()
    except Exception as error:
        logger.error("No mill connected, %s", error)
        print("PandaMill not found                        ", flush=True)
        disconnected_instruments.append("PandaMill")
        incomplete = True

    # Camera connection

    # Check for camera based on the configuration
    print("Checking camera connection...", end="\r", flush=True)
    camera_type = read_camera_type().lower()

    try:
        logger.debug(f"Connecting to camera (type: {camera_type})")

        # Create appropriate camera based on type
        if camera_type == "flir":
            camera_type_enum = CameraType.FLIR
        else:
            camera_type_enum = CameraType.OPENCV

        # Create the camera
        if camera_type_enum == CameraType.OPENCV:
            webcam_id, resolution = read_webcam_settings()
            camera = CameraFactory.create_camera(
                camera_type=camera_type_enum, camera_id=webcam_id, resolution=resolution
            )
        else:
            camera = CameraFactory.create_camera(camera_type=camera_type_enum)

        # If FLIR camera creation failed but PySpin is available, show specific message
        if camera is None and camera_type == "flir":
            from .hardware.imaging.flir_camera import PYSPIN_AVAILABLE

            if PYSPIN_AVAILABLE:
                raise Exception("Failed to create FLIR camera (hardware not found)")
            else:
                raise Exception("PySpin library not available")

        # If camera is created but fails to connect
        if camera is not None and not camera.connect():
            raise Exception(f"Failed to connect to {camera_type} camera")

        # At this point, we have a successfully connected camera
        logger.debug(f"Successfully connected to {camera_type} camera")
        print(
            f"{camera_type.capitalize()} camera connected                        ",
            flush=True,
        )
        connected_instruments.append(f"{camera_type.capitalize()} Camera")

        # Clean up
        if camera is not None:
            camera.close()

    except Exception as error:
        logger.error(f"No {camera_type} camera connected: {error}")
        print(
            f"{camera_type.capitalize()} camera not found                        ",
            flush=True,
        )
        disconnected_instruments.append(f"{camera_type.capitalize()} Camera")
        incomplete = True

    # Potentiostat connection
    print("Checking Potentiostat connection...", end="\r", flush=True)

    # Check the config for the model of the potentiostat
    potentiostat_model = read_config_value("POTENTIOSTAT", "model")
    if not potentiostat_model:
        logger.error("No potentiostat model specified in the configuration file")
        print("Potentiostat not found                        ", flush=True)
        disconnected_instruments.append("Potentiostat")
        incomplete = True

    # Check if the model is supported by the current OS
    # If gamry, or chi* are not supported on non-windows OS
    if os.name != "nt" and (
        "gamry" in potentiostat_model.lower() or "chi" in potentiostat_model.lower()
    ):
        logger.error("Potentiostat model not supported on non-Windows OS")
        print("Potentiostat not found                        ", flush=True)
        disconnected_instruments.append("Potentiostat")
        incomplete = True

    if "gamry" in potentiostat_model.lower():
        try:
            pstat = gamry_control.pstatconnect()
            if pstat:
                logger.debug("Connected to Gamry Potentiostat")
                print("Potentiostat connected                        ", flush=True)
                connected_instruments.append("Potentiostat")
            else:
                raise Exception("No Gamry Potentiostat found")
        except Exception as error:
            logger.error("No Gamry Potentiostat connected, %s", error)
            print("Potentiostat not found                        ", flush=True)
            disconnected_instruments.append("Potentiostat")
            incomplete = True
        finally:
            try:
                gamry_control.pstatdisconnect()
            except Exception as error:
                logger.error("Error disconnecting from Gamry Potentiostat, %s", error)
                print("Error disconnecting from Gamry Potentiostat, %s", error)

    elif "chi" in potentiostat_model.lower():
        import hardpotato as hp

        try:
            model = potentiostat_model.lower()
            # Write the path where the chi software is installed (this line is optional when
            # using the Pico). Make sure to use / instead of \:
            path = read_config_value("POTENTIOSTAT", "path")
            if not path:
                raise Exception(
                    "No path specified for the Chi software in the configuration file"
                )
            if not os.path.exists(path):
                raise Exception("Path to Chi software does not exist")

            # Write the path where the data and plots are going to be automatically saved:
            folder = read_config_value("TESTING", "data_dir")
            # Setup:
            connection = hp.potentiostat.Setup(model, path, folder, verbose=0)
            if connection:
                logger.debug("Connected to Chi Potentiostat")
                print("Potentiostat connected                        ", flush=True)
                connected_instruments.append("Potentiostat")
            else:
                raise Exception("No Chi Potentiostat found")
        except Exception as error:
            logger.error("No Chi Potentiostat connected, %s", error)
            print("Potentiostat not found                        ", flush=True)
            disconnected_instruments.append("Potentiostat")
            incomplete = True

    elif potentiostat_model.lower() in [
        "palmsense",
        "emstat",
        "pico",
        "emstat4slr",
        "emstat4shr",
    ]:
        try:
            import hardpotato as hp

            model = potentiostat_model.lower()
            # Write the path where the data and plots are going to be automatically saved:
            connection = hp.potentiostat.Setup(model, folder=None, verbose=0)
            if connection:
                logger.debug("Connected to %s Potentiostat", model)
                print("Potentiostat connected                        ", flush=True)
                connected_instruments.append("Potentiostat")
            else:
                raise Exception("No Potentiostat found")
        except Exception as error:
            logger.error("No Potentiostat connected, %s", error)
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

    
    # Pump connection
    # Check if the config specifies a syringe pump. If not skip the check
    syringe_pump = read_config_value("PIPETTE", "PIPETTE_TYPE")
    pump_port = read_config_value("PUMP", "PORT")
    if pump_port:
        print("Checking pump connection...", end="\r", flush=True)
        try:
            logger.debug("Connecting to pump")
            pipette = Pipette()
            if pipette.connected:
                logger.debug("Connected to pump at %s", pipette.pump.address)
                print("pipette connected                        ", flush=True)
                connected_instruments.append("pump")
            else:
                raise Exception("Failed to connect to pump")
            pipette.close()
        except Exception as error:
            logger.error("No pump connected, %s", error)
            print("Pipette not found                        ", flush=True)
            disconnected_instruments.append("pump")
            incomplete = True
    elif syringe_pump in ["OT2", "ot2"]:
        print("Checking OT2 connection...", end="\r", flush=True)
        try:
            stepper = ArduinoLink(port_address=read_config_value("ARDUINO", "port"))
            logger.debug("Connecting to OT2 Pipette")
            pipette = Pipette.from_config(stepper=stepper)
            status = pipette.get_status()
            if status:
                logger.debug("Connected to OT2 Pipette")
                print("OT2 pipette connected                        ", flush=True)
                connected_instruments.append("OT2 Pipette")
            else:
                raise Exception("Failed to connect to OT2 Pipette")
        except Exception as error:
            logger.error("No OT2 Pipette connected, %s", error)
            print("OT2 pipette not found                        ", flush=True)
            disconnected_instruments.append("OT2 Pipette")
            incomplete = True
    
    else:
        print(
            "No pump port nor syringe pump specified in the configuration file",
            flush=True,
        )
        logger.warning(
            "No pump port nor syringe pump specified in the configuration file"
        )
        disconnected_instruments.append("Pump")
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
    #if instruments.camera:
    #    instruments.camera.close()
    if instruments.arduino:
        instruments.arduino.close()
    #if instruments.scale:
    #    instruments.scale.hw.close()
    if instruments.pipette:
        instruments.pipette.close()
