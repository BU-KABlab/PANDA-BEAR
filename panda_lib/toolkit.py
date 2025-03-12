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
from panda_lib.labware.vials import StockVial, WasteVial, read_vials
from panda_lib.labware.wellplates import Wellplate

# from panda_lib.movement import Mill, MockMill
from panda_lib.panda_gantry import MockPandaMill as MockMill
from panda_lib.panda_gantry import PandaMill as Mill
from panda_lib.slack_tools.slackbot_module import SlackBot
from panda_lib.tools import ArduinoLink, MockArduinoLink, OBSController


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
    arduino: ArduinoLink = None


@dataclass
class Hardware:
    """A class to hold all of the hardware"""

    mill: Union[Mill, MockMill, None] = None
    scale: Union[Scale, MockScale, None] = None
    pump: Union[SyringePump, MockPump, None] = None
    flir_camera: PySpin.Camera = None
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
    - FLIR Camera
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
        arduino=None,
        flir_camera=None,
    )

    if use_mock_instruments:
        logger.info("Using mock instruments")
        instruments.mill = MockMill()
        instruments.mill.connect_to_mill()
        # instruments.scale = MockScale()
        instruments.pump = MockPump()
        # pstat = echem_mock.GamryPotentiostat.connect()
        instruments.arduino = MockArduinoLink()
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

    # Check for FLIR Camera
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
    )

    # Track connected and disconnected instruments for summary
    connected_instruments = []
    disconnected_instruments = []

    if use_mock_instruments:
        logger.info("Using mock instruments")
        print("Using mock instruments")
        instruments.mill = MockMill()
        instruments.mill.connect_to_mill()
        # instruments.scale = MockScale()
        instruments.pump = MockPump()
        instruments.arduino = MockArduinoLink()
        # pstat = echem_mock.GamryPotentiostat.connect()

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

    # Scale connection (commented out in original code)
    # print("Checking scale connection...", end="\r", flush=True)
    # try:
    #     logger.debug("Connecting to scale")
    #     scale = Scale(address="COM6")
    #     info_dict = scale.get_info()
    #     model = info_dict["model"]
    #     serial = info_dict["serial"]
    #     software = info_dict["software"]
    #     if not model:
    #         logger.error("No scale connected")
    #         print("Scale not found                        ", flush=True)
    #         disconnected_instruments.append("Scale")
    #         incomplete = True
    #     else:
    #         logger.debug("Connected to scale:\n%s\n%s\n%s\n", model, serial, software)
    #         print("Scale connected                        ", flush=True)
    #         connected_instruments.append("Scale")
    # except Exception as error:
    #     logger.error("No scale connected, %s", error)
    #     instruments.scale = None
    #     print("Scale not found                        ", flush=True)
    #     disconnected_instruments.append("Scale")
    #     incomplete = True

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

    # FLIR Camera connection
    print("Checking FLIR Camera connection...", end="\r", flush=True)
    try:
        logger.debug("Connecting to FLIR Camera")
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        if cam_list.GetSize() == 0:
            logger.error("No FLIR Camera connected")
            instruments.flir_camera = None
            print("FLIR Camera not found                        ", flush=True)
            disconnected_instruments.append("FLIR Camera")
            incomplete = True
        else:
            instruments.flir_camera = cam_list.GetByIndex(0)
            # instruments.flir_camera.Init()
            cam_list.Clear()
            system.ReleaseInstance()
            print("FLIR Camera connected                        ", flush=True)
            connected_instruments.append("FLIR Camera")
            logger.debug("Connected to FLIR Camera")
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
