"""Module to inferface with Gamry Potentiostat"""

import gc
import logging
import pathlib
import time
from decimal import Decimal
from typing import Tuple
from pathlib import Path
import numpy as np
import pandas as pd
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


from .errors import ErrorCodeLookup, GamryCOMError, check_platform_compatibility

import comtypes
from comtypes import client

# pylint: disable=global-statement, invalid-name, global-variable-undefined

## set up logging to log to both the pump_control.log file and the PANDA_SDL.log file
logger = logging.getLogger("panda")

# global variables
global PSTAT
global DEVICES
global GAMRY_COM
global DTAQ
global SIGNAL
global DTAQ_SINK
global CONNECTION
global ACTIVE
global COMPLETE_FILE_NAME
global OPEN_CONNECTION

# Initialize global variables
PSTAT = None
DEVICES = None
GAMRY_COM = None
DTAQ = None
SIGNAL = None
DTAQ_SINK = None
CONNECTION = None
ACTIVE = False
COMPLETE_FILE_NAME = None
OPEN_CONNECTION = False


@dataclass(config=ConfigDict(validate_assignment=True))
class cv_parameters:
    """CV Setup Parameters
    
    Parameters:
        CVvi(float): Initial voltage (V)
        CVap1(float): First anodic peak (V)
        CVap2(float): Second anodic peak (V)
        CVvf(float): Final voltage (V)
        CVstep(float): Step size (V)
        CVsr1(float): Scan rate cycle 1 (V/s)
        CVsr2(float): Scan rate cycle 2 (V/s)
        CVsr3(float): Scan rate cycle 3 (V/s)
        CVsamplerate(float): Sample rate (s)
        CVcycle(int): Number of cycles
    """

    # CV Setup Parameters
    CVvi: float = 0.0  # initial voltage
    CVap1: float = 0.5  # first anodic peak
    CVap2: float = -0.2  # second anodic peak
    CVvf: float = 0.0  # final voltage
    CVstep: float = 0.01  # step size
    CVsr1: float = 0.1  # scan rate cycle 1
    CVsr2: float = CVsr1  # scan rate cycle 2
    CVsr3: float = CVsr1  # scan rate cycle 3
    CVsamplerate: float = CVstep / CVsr1
    CVcycle: int = 3  # number of cycles


@dataclass(config=ConfigDict(validate_assignment=True))
class chrono_parameters:
    """CA Setup Parameters

    Parameters:
        CAvi(float): Pre-step voltage (V)
        CAti(float):  Pre-step delay time (s)
        CAv1(float):  Step 1 voltage (V)
        CAt1(float):  Run time (s)
        CAv2(float):  Step 2 voltage (V)
        CAt2(float):  Step 2 time (s)
        CAsamplerate(float): Sample period (s)
    """

    # CA/CP Setup Parameters
    CAvi: float = 0.0  # Pre-step voltage (V)
    CAti: float = 0.0  # Pre-step delay time (s)
    CAv1: float = -1.7  # Step 1 voltage (V)
    CAt1: float = 300.0  # run time 300 seconds
    CAv2: float = 0.0  # Step 2 voltage (V)
    CAt2: float = 0.0  # Step 2 time (s)
    CAsamplerate: float = 0.5  # sample period (s)
    # Max current (mA)
    # Limit I (mA/cm^2)
    # PF Corr. (ohm)
    # Equil. time (s)
    # Expected Max V (V)
    # Initial Delay on
    # Initial Delay (s)


@dataclass(config=ConfigDict(validate_assignment=True))
class potentiostat_ocp_parameters:
    """OCP Setup Parameters
    
    Parameters:
        OCPvi(float): Initial voltage (V)
        OCPti(float): Time interval (s)
        OCPrate(float): Rate of change (V/s)"""

    # OCP Setup Parameters
    OCPvi: float = 0.0
    OCPti: float = 15.0
    OCPrate: float = 0.5


class GamryDtaqEvents(object):
    """Class to handle events from the data acquisition."""

    def __init__(self, dtaq_value, complete_file_name):
        self.dtaq = dtaq_value
        self.acquired_points = []
        self.complete_file_name = complete_file_name

    def call_stopacq(self):
        """stop the acquisition"""
        stopacq()

    def call_savedata(self, complete_file_name):
        """save the data to a file"""
        savedata(complete_file_name)

    def cook(self):
        """Cook the data acquired from the data acquisition."""
        count = 1
        while count > 0:
            count, points = self.dtaq.Cook(10)
            # The columns exposed by GamryDtaq.Cook vary by dtaq and are
            # documented in the Toolkit Reference Manual.
            self.acquired_points.extend(zip(*points))

    def _IGamryDtaqEvents_OnDataAvailable(self):
        """Called when data is available from the data acquisition."""
        self.cook()
        # loading = ["|", "/", "-", "\\"]
        # logger.debug("\rmade it to data available %s{random.choice(loading)}", end="")

    def _IGamryDtaqEvents_OnDataDone(self):
        """Called when the data acquisition is complete."""
        logger.debug("made it to data done")
        self.cook()  # a final cook
        time.sleep(2.0)
        self.call_stopacq()
        self.call_savedata(self.complete_file_name)


def gamry_error_decoder(err) -> GamryCOMError:
    """Decode a COM error from GamryCOM into a more useful exception."""
    if comtypes and isinstance(err, comtypes.COMError):
        hresult = 2**32 + err.args[0]
        if hresult & 0x20000000:
            error_description = ErrorCodeLookup.get_error_description(hresult)
            return GamryCOMError(
                f"0x{hresult:08x}: {err.args[1]} - {error_description}"
            )
    return err


def pstatconnect() -> bool:
    """connect to the pstat

    Returns:
        bool: True if the connection is successful, False otherwise

    Raises:
        GamryPlatformError: If not running on Windows
    """
    global PSTAT
    global DEVICES
    global GAMRY_COM
    global OPEN_CONNECTION

    # Check platform compatibility
    check_platform_compatibility()

    try:
        GAMRY_COM = client.GetModule(["{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}", 1, 0])
        PSTAT = client.CreateObject("GamryCOM.GamryPC6Pstat")
        DEVICES = client.CreateObject("GamryCOM.GamryDeviceList")
        if not DEVICES.EnumSections():
            logger.error("No Gamry devices found")
            OPEN_CONNECTION = False
            return False

        PSTAT.Init(DEVICES.EnumSections()[0])  # grab first pstat
        PSTAT.Open()  # open connection to pstat

        logger.debug("\tPstat connected: %s", DEVICES.EnumSections()[0])
        OPEN_CONNECTION = True
        return True
    except Exception as e:
        logger.error("Failed to connect to potentiostat: %s", str(e))
        OPEN_CONNECTION = False
        raise gamry_error_decoder(e)


def initializepstat():
    """initialize the pstat"""
    PSTAT.SetCtrlMode(GAMRY_COM.PstatMode)
    PSTAT.SetCell(GAMRY_COM.CellOff)
    PSTAT.SetIEStability(GAMRY_COM.StabilityNorm)
    PSTAT.SetVchRangeMode(True)
    PSTAT.SetVchRange(10.0)  # Expected Max Voltage
    PSTAT.SetIERangeMode(True)  # True = Auto, False = Manual
    # the following command allows us to set our range manually
    # pstat.SetIERange (x)


def stopacq():
    """stop the acquisition"""
    global ACTIVE
    global PSTAT
    global GAMRY_COM
    ACTIVE = False
    PSTAT.SetCell(GAMRY_COM.CellOff)
    time.sleep(1)
    gc.collect()
    return


def pstatdisconnect():
    """disconnect the pstat"""
    global PSTAT
    global OPEN_CONNECTION
    """disconnect the pstat"""
    logger.debug("disconnecting pstat")
    PSTAT.Close()
    OPEN_CONNECTION = False
    # del connection
    time.sleep(2)


def savedata(complete_file_name):
    """save the data to a file"""
    # logger.debug(dtaqsink.acquired_points)
    logger.debug("number of data points acquired: %d", len(DTAQ_SINK.acquired_points))
    # savedata
    # column_names = ["Time", "Vf","Vu","Vsig","Ach","Overload","StopTest","Temp"]
    output = pd.DataFrame(DTAQ_SINK.acquired_points)
    # complete_file_name = os.path(complete_file_name)
    np.savetxt(Path(complete_file_name).with_suffix(".txt"), output,fmt="%s")
    logger.debug("data saved")


def setfilename(
    experiment_id,
    experiment_type,
    data_dir,
    project_campaign_id: int = None,
    campaign_id: int = None,
    well_id: str = None,
) -> pathlib.Path:
    """set the file name for the experiment"""
    global COMPLETE_FILE_NAME
    if project_campaign_id is None and campaign_id is None and well_id is None:
        file_name = f"{experiment_id}_{experiment_type}"
        file_name = file_name.replace(" ", "_")
        file_name_start = file_name + "_0"
        filepath: pathlib.Path = (data_dir / file_name_start).with_suffix(".txt")
        i = 1
        while filepath.exists():
            next_file_name = f"{file_name}_{i}"
            filepath = pathlib.Path(data_dir / str(next_file_name)).with_suffix(
                ".txt"
            )
            i += 1
    else:
        file_name = f"{project_campaign_id}_{campaign_id}_{experiment_id}_{well_id}_{experiment_type}"
        file_name = file_name.replace(" ", "_")
        file_name_start = file_name + "_0"
        filepath: pathlib.Path = (data_dir / file_name_start).with_suffix(".txt")
        # Check if the file already exists. If it does then add a number to the end of the file name
        i = 1
        while filepath.exists():
            next_file_name = f"{file_name}_{i}"
            filepath = pathlib.Path(data_dir / str(next_file_name)).with_suffix(
                ".txt"
            )
            i += 1

    COMPLETE_FILE_NAME = filepath
    return COMPLETE_FILE_NAME


def cyclic(params: cv_parameters):
    """cyclic voltammetry"""
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global GAMRY_COM
    global ACTIVE
    # global complete_file_name

    logger.debug("cyclic: made it to run start")
    ACTIVE = True

    # signal and dtaq object creation
    SIGNAL = client.CreateObject("GamryCOM.GamrySignalRupdn")
    DTAQ = client.CreateObject("GamryCOM.GamryDtaqRcv")
    DTAQ_SINK = GamryDtaqEvents(DTAQ, COMPLETE_FILE_NAME)
    CONNECTION = client.GetEvents(DTAQ, DTAQ_SINK)

    SIGNAL.Init(
        PSTAT,  # Pstat object
        params.CVvi,  # initial voltage
        params.CVap1,  # first anodic peak
        params.CVap2,  # second anodic peak
        params.CVvf,  # final voltage
        params.CVsr1,  # scan rate cycle 1
        params.CVsr2,  # scan rate cycle 2
        params.CVsr3,  # scan rate cycle 3
        0.0,  # HoltTime0
        0.0,  # HoldTime1
        0.0,  # HoldTime2
        params.CVsamplerate,  # sample rate
        params.CVcycle,  # number of cycles
        GAMRY_COM.PstatMode,  # mode
    )
    initializepstat()
    DTAQ.Init(PSTAT)
    PSTAT.SetSignal(SIGNAL)
    PSTAT.SetCell(GAMRY_COM.CellOn)

    DTAQ.Run(True)


    logger.debug("cyclic: made it to run end")


def chrono(params: chrono_parameters):
    """chronoamperometry

    :param CAvi: initial voltage
    :param CAti: time interval
    :param CAv1: voltage 1
    :param CAt1: time 1
    :param CAv2: voltage 2
    :param CAt2: time 2
    :param CAsamplerate: sample rate

    """
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global GAMRY_COM
    global ACTIVE
    # global complete_file_name

    ACTIVE = True
    logger.debug("chrono: made it to run")

    # signal and dtaq object creation
    SIGNAL = client.CreateObject("GamryCOM.GamrySignalDstep")
    DTAQ = client.CreateObject("GamryCOM.GamryDtaqChrono")

    DTAQ_SINK = GamryDtaqEvents(DTAQ, COMPLETE_FILE_NAME)
    CONNECTION = client.GetEvents(DTAQ, DTAQ_SINK)

    SIGNAL.Init(
        PSTAT,
        params.CAvi,
        params.CAti,
        params.CAv1,
        params.CAt1,
        params.CAv2,
        params.CAt2,
        params.CAsamplerate,
        GAMRY_COM.PstatMode,
    )
    initializepstat()

    DTAQ.Init(PSTAT, GAMRY_COM.ChronoAmp)
    PSTAT.SetSignal(SIGNAL)
    PSTAT.SetCell(GAMRY_COM.CellOn)

    DTAQ.Run(True)
    logger.debug("chrono: made it to run end")


def OCP(OCPvi, OCPti, OCPrate):
    """
    open circuit potential

    :param OCPvi: initial voltage
    :param OCPti: time interval
    :param OCPrate: rate of change

    """
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global ACTIVE
    global GAMRY_COM
    global PSTAT
    global COMPLETE_FILE_NAME

    ACTIVE = True

    logger.debug("ocp: made it to run")

    # signal and dtaq object creation
    SIGNAL = client.CreateObject("GamryCOM.GamrySignalConst")
    DTAQ = client.CreateObject("GamryCOM.GamryDtaqOcv")

    DTAQ_SINK = GamryDtaqEvents(DTAQ, COMPLETE_FILE_NAME)
    CONNECTION = client.GetEvents(DTAQ, DTAQ_SINK)

    SIGNAL.Init(PSTAT, OCPvi, OCPti, OCPrate, GAMRY_COM.PstatMode)
    initializepstat()

    DTAQ.Init(PSTAT)
    PSTAT.SetSignal(SIGNAL)
    PSTAT.SetCell(GAMRY_COM.CellOff)

    DTAQ.Run(True)
    # start_time = time.time()
    logger.debug("ocp: made it to run end")


def activecheck():
    """check if an experiment is active"""
    while ACTIVE is True:
        client.PumpEvents(1)
        time.sleep(0.5)


def check_vf_range(filename) -> Tuple[bool, float]:
    """Check if the Vf value is in the valid range for an echem experiment."""
    try:
        ocp_data = pd.read_csv(
            filename,
            sep=" ",
            header=None,
            names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"],
        )
        vf_last_row_scientific = ocp_data.iloc[-2, ocp_data.columns.get_loc("Vf")]
        logger.debug("Vf last row (sci): %.2E", Decimal(vf_last_row_scientific))
        vf_last_row_decimal = float(vf_last_row_scientific)
        logger.debug("Vf last row (float): %f", vf_last_row_decimal)

        if -1 < vf_last_row_decimal and vf_last_row_decimal < 1:
            logger.debug("Vf in valid range (-1 to 1). Proceeding to echem experiment")
            return True, vf_last_row_decimal
        else:
            logger.error("Vf not in valid range. Aborting echem experiment")
            return False, 0.0
    except Exception as error:
        logger.error("Error occurred while checking Vf: %s", error)
        return False, 0.0


if __name__ == "__main__":
    try:
        pstatconnect()  # grab first pstat
        COMPLETE_FILE_NAME = setfilename(10000384,"OCP", ".",  16, 2, "B4")
        OCP(
            potentiostat_ocp_parameters.OCPvi,
            potentiostat_ocp_parameters.OCPti,
            potentiostat_ocp_parameters.OCPrate,
        )
        activecheck()
        #        while active == True:
        # client.PumpEvents(1)
        # time.sleep(0.5)
        ## echem CA - deposition
        if check_vf_range(COMPLETE_FILE_NAME.with_suffix(".txt")):
            COMPLETE_FILE_NAME = setfilename(10000384, "CV", ".",  16, 2, "B4")
            cv_params = cv_parameters(
                0.0, 1.0, -0.3, 1.0, 0.025, 0.025, 0.025, 0.002, 3
            )
            cyclic(cv_params)
            # chrono(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
            logger.debug("made it to try")
            while ACTIVE is True:
                client.PumpEvents(1)
                time.sleep(0.5)
            ## echem plot the data
            # Analyzer.plotdata("CV", COMPLETE_FILE_NAME)
        pstatdisconnect()
        del CONNECTION

    except Exception as e:
        raise gamry_error_decoder(e)
