"""Module to inferface with Gamry Potentiostat"""
import comtypes
import comtypes.client as client
import datetime
import gc
import logging
import numpy as np
import pandas as pd
import pathlib
import random
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass
import time
import Analyzer
from decimal import Decimal
# pylint: disable=global-statement, invalid-name, global-variable-undefined

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(levelname)s:%(message)s")
system_handler = logging.FileHandler("code/logs/ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

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


def pstatconnect():
    """connect to the pstat"""
    global PSTAT
    global DEVICES
    global GAMRY_COM
    global OPEN_CONNECTION

    GAMRY_COM = client.GetModule(["{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}", 1, 0])
    PSTAT = client.CreateObject("GamryCOM.GamryPC6Pstat")
    DEVICES = client.CreateObject("GamryCOM.GamryDeviceList")
    PSTAT.Init(DEVICES.EnumSections()[0])  # grab first pstat
    PSTAT.Open()  # open connection to pstat

    if DEVICES.EnumSections():
        logger.debug("\tPstat connected: %s", DEVICES.EnumSections()[0])
        OPEN_CONNECTION = True
    else:
        logger.debug("\tPstat not connected")


class GamryCOMError(Exception):
    """Exception raised when a COM error occurs."""

    pass


def gamry_error_decoder(err):
    """Decode a COM error from GamryCOM into a more useful exception."""
    if isinstance(err, comtypes.COMError):
        hresult = 2**32 + err.args[0]
        if hresult & 0x20000000:
            return GamryCOMError(f"0x{hresult:08x}: {err.args[1]}")
    return err


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


def pstatdisconnect():
    """disconnect the pstat"""
    global PSTAT
    global OPEN_CONNECTION
    """disconnect the pstat"""
    logger.debug("disconnecting pstat")
    PSTAT.Close()
    OPEN_CONNECTION = False
    # del connection
    time.sleep(15)


def savedata(complete_file_name):
    """save the data to a file"""
    # logger.debug(dtaqsink.acquired_points)
    logger.debug("number of data points acquired: %d", len(DTAQ_SINK.acquired_points))
    # savedata
    # column_names = ["Time", "Vf","Vu","Vsig","Ach","Overload","StopTest","Temp"]
    output = pd.DataFrame(DTAQ_SINK.acquired_points)
    # complete_file_name = os.path(complete_file_name)
    np.savetxt(complete_file_name.with_suffix(".txt"), output)
    logger.debug("data saved")


def setfilename(experiment_id, experiment_type) -> pathlib.Path:
    """set the file name for the experiment"""
    global COMPLETE_FILE_NAME
    filename:pathlib.Path = (
            pathlib.Path.cwd()
            / "data"
            / ("experiment-" + str(experiment_id) + "_mock_" + experiment_type)
        )
    # Check if the file already exists. If it does then add a number to the end of the file name
    if filename.exists():
        i = 1
        while filename.exists():
            filename = (
                pathlib.Path.cwd()
                / "data"
                / (
                    "experiment-"
                    + str(experiment_id)
                    + "_mock_"
                    + experiment_type
                    + "_"
                    + str(i)
                )
            )
            i += 1
    COMPLETE_FILE_NAME = filename
    return COMPLETE_FILE_NAME


def cyclic(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle):
    """cyclic voltammetry"""
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global GAMRY_COM
    global ACTIVE
    # global complete_file_name

    logger.debug("cyclic: made it to run")
    ACTIVE = True

    # signal and dtaq object creation
    SIGNAL = client.CreateObject("GamryCOM.GamrySignalRupdn")
    DTAQ = client.CreateObject("GamryCOM.GamryDtaqRcv")
    DTAQ_SINK = GamryDtaqEvents(DTAQ, COMPLETE_FILE_NAME)
    CONNECTION = client.GetEvents(DTAQ, DTAQ_SINK)

    SIGNAL.Init(
        PSTAT,
        CVvi,
        CVap1,
        CVap2,
        CVvf,
        CVsr1,
        CVsr2,
        CVsr3,
        0.0,
        0.0,
        0.0,
        CVsamplerate,
        CVcycle,
        GAMRY_COM.PstatMode,
    )
    initializepstat()
    DTAQ.Init(PSTAT)
    PSTAT.SetSignal(SIGNAL)
    PSTAT.SetCell(GAMRY_COM.CellOn)
    DTAQ.Run(True)
    # Code for timing started
    # start_time = time.time()
    logger.debug("cyclic: made it to run end")


def chrono(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate):
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
        PSTAT, CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate, GAMRY_COM.PstatMode
    )
    initializepstat()

    DTAQ.Init(PSTAT, GAMRY_COM.ChronoAmp)
    PSTAT.SetSignal(SIGNAL)
    PSTAT.SetCell(GAMRY_COM.CellOn)

    DTAQ.Run(True)

    # Code for timing started
    # start_time = time.time()
    logger.debug("chrono: made it to run end")


def OCP(OCPvi, OCPti, OCPrate):
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
    while ACTIVE is True:
        client.PumpEvents(1)
        time.sleep(0.5)


def check_vf_range(filename):
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
            return True
        else:
            logger.error("Vf not in valid range. Aborting echem experiment")
            return False
    except Exception as error:
        logger.error("Error occurred while checking Vf: %s", error)
        return False


def mock_CA(MCAvi, MCAti, MCArate):
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global GAMRY_COM
    global ACTIVE
    ACTIVE = True

    logger.debug("mock ca: made it to run")

    # signal and dtaq object creation
    SIGNAL = client.CreateObject("GamryCOM.GamrySignalConst")
    DTAQ = client.CreateObject("GamryCOM.GamryDtaqOcv")

    DTAQ_SINK = GamryDtaqEvents(DTAQ, COMPLETE_FILE_NAME)
    CONNECTION = client.GetEvents(DTAQ, DTAQ_SINK)

    SIGNAL.Init(PSTAT, MCAvi, MCAti, MCArate, GAMRY_COM.PstatMode)
    initializepstat()

    DTAQ.Init(PSTAT)
    PSTAT.SetSignal(SIGNAL)
    PSTAT.SetCell(GAMRY_COM.CellOff)

    DTAQ.Run(True)
    # start_time = time.time()
    logger.debug("mock ca: made it to run end")


@dataclass(config=ConfigDict(validate_assignment=True))
class potentiostat_cv_parameters:
    """CV Setup Parameters"""

    # CV Setup Parameters
    CVvi: float = 0.0  # initial voltage
    CVap1: float = 0.5 
    CVap2: float = -0.2 
    CVvf: float = 0.0  # final voltage
    CVstep: float = 0.01
    CVsr1: float = 0.1
    CVcycle: int = 3
    CVsr2: float = CVsr1
    CVsr3: float = CVsr1
    CVsamplerate: float = CVstep / CVsr1


@dataclass(config=ConfigDict(validate_assignment=True))
class potentiostat_ca_parameters:
    """CA Setup Parameters"""

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
    """OCP Setup Parameters"""

    # OCP Setup Parameters
    OCPvi: float = 0.0
    OCPti: float = 15.0
    OCPrate: float = 0.5


if __name__ == "__main__":
    try:
        pstatconnect()  # grab first pstat
        COMPLETE_FILE_NAME = setfilename("F1", "OCP")
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
            COMPLETE_FILE_NAME = setfilename("F1", "CV")
            cyclic(
                potentiostat_cv_parameters.CVvi,
                potentiostat_cv_parameters.CVap1,
                potentiostat_cv_parameters.CVap2,
                potentiostat_cv_parameters.CVvf,
                potentiostat_cv_parameters.CVsr1,
                potentiostat_cv_parameters.CVsr2,
                potentiostat_cv_parameters.CVsr3,
                potentiostat_cv_parameters.CVsamplerate,
                potentiostat_cv_parameters.CVcycle,
            )
            # chrono(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
            logger.debug("made it to try")
            while ACTIVE is True:
                client.PumpEvents(1)
                time.sleep(0.5)
            ## echem plot the data
            Analyzer.plotdata("CV", COMPLETE_FILE_NAME)
        pstatdisconnect()
        del CONNECTION

    except Exception as e:
        raise gamry_error_decoder(e)
