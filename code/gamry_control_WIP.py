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
# pylint: disable=global-statement

## set up logging to log to both the pump_control.log file and the ePANDA.log file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # change to INFO to reduce verbosity
formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")
system_handler = logging.FileHandler("ePANDA.log")
system_handler.setFormatter(formatter)
logger.addHandler(system_handler)

# global variables
PSTAT = None
DEVICES = None
GAMRY_COM = None
DTAQ = None
SIGNAL = None
DTAQ_SINK = None
CONNECTION = None
START_TIME = None
ACTIVE = None
COMPLETE_FILE_NAME = None


def pstatconnect():
    global PSTAT
    global DEVICES
    global GAMRY_COM

    GAMRY_COM = client.GetModule(["{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}", 1, 0])
    PSTAT = client.CreateObject("GamryCOM.GamryPC6Pstat")
    DEVICES = client.CreateObject("GamryCOM.GamryDeviceList")
    PSTAT.Init(DEVICES.EnumSections()[0])  # grab first pstat
    PSTAT.Open()  # open connection to pstat
    if DEVICES.EnumSections():
        logger.debug("\tPstat connected: %s", DEVICES.EnumSections()[0])
    else:
        logger.debug("\tPstat not connected")


class GamryCOMError(Exception):
    pass


def gamry_error_decoder(err):
    if isinstance(err, comtypes.COMError):
        hresult = 2**32 + err.args[0]
        if hresult & 0x20000000:
            return GamryCOMError(
                "0x{0:08x}: {1}".format(2**32 + err.args[0], err.args[1])
            )
    return err


def initializepstat():
    PSTAT.SetCtrlMode(GAMRY_COM.PstatMode)
    PSTAT.SetCell(GAMRY_COM.CellOff)
    PSTAT.SetIEStability(GAMRY_COM.StabilityNorm)
    PSTAT.SetVchRangeMode(True)
    PSTAT.SetVchRange(10.0)  # Expected Max Voltage
    PSTAT.SetIERangeMode(True)  # True = Auto, False = Manual
    # the following command allows us to set our range manually
    # pstat.SetIERange (x)


def stopacq():
    global ACTIVE

    ACTIVE = False
    PSTAT.SetCell(GAMRY_COM.CellOff)
    time.sleep(1)
    gc.collect()
    return


class GamryDtaqEvents(object):
    def __init__(self, dtaq_value, complete_file_name):
        self.dtaq = dtaq_value
        self.acquired_points = []
        self.complete_file_name = complete_file_name

    def call_stopacq(self):
        stopacq()

    def call_savedata(self, complete_file_name):
        savedata(complete_file_name)

    def cook(self):
        count = 1
        while count > 0:
            count, points = self.dtaq.Cook(10)
            # The columns exposed by GamryDtaq.Cook vary by dtaq and are
            # documented in the Toolkit Reference Manual.
            self.acquired_points.extend(zip(*points))

    def _IGamryDtaqEvents_OnDataAvailable(self):
        self.cook()
        #loading = ["|", "/", "-", "\\"]
        #logger.debug("\rmade it to data available %s{random.choice(loading)}", end="")

    def _IGamryDtaqEvents_OnDataDone(self):
        logger.debug("\nmade it to data done")
        self.cook()  # a final cook
        time.sleep(2.0)
        self.call_stopacq()
        self.call_savedata(self.complete_file_name)


def disconnectpstat():
    PSTAT.Close()
    # del connection
    time.sleep(15)


def savedata(complete_file_name):
    """save the data to a file"""
    # logger.debug(dtaqsink.acquired_points)
    logger.debug("number of data points acquired")
    logger.debug(len(DTAQ_SINK.acquired_points))
    # savedata
    # column_names = ["Time", "Vf","Vu","Vsig","Ach","Overload","StopTest","Temp"]
    output = pd.DataFrame(DTAQ_SINK.acquired_points)
    # complete_file_name = os.path(complete_file_name)
    np.savetxt(complete_file_name.with_suffix(".txt"), output)
    logger.debug("data saved")


def setfilename(experiment_id, experiment_type):
    """set the file name for the experiment"""
    global COMPLETE_FILE_NAME
    current_time = datetime.datetime.now()
    fileDate = current_time.strftime("%Y-%m-%d")
    cwd = pathlib.Path().absolute()
    filePathPar = pathlib.Path(cwd.parents[1].__str__() + "/data")
    filePath = filePathPar / fileDate
    # complete_file_name = filePath / (target_well + "_" + experiment)
    COMPLETE_FILE_NAME = filePath / ("experiment-" + experiment_id + "_" + experiment_type)
    logger.debug(f"eChem: complete file name is: {COMPLETE_FILE_NAME}")
    if not pathlib.Path.exists(filePath):
        logger.debug(f"folder does not exist. Making folder: {filePath}")
        pathlib.Path.mkdir(filePath, parents=True, exist_ok=True)
    else:
        logger.debug(f"folder {filePath} exists")
    return COMPLETE_FILE_NAME


def cyclic(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle):
    """cyclic voltammetry"""
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global START_TIME
    global ACTIVE
    # global complete_file_name

    logger.debug("made it to run")
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
    logger.debug("made it to run end")


def chrono(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate):
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global START_TIME
    global ACTIVE
    # global complete_file_name

    ACTIVE = True
    logger.debug("made it to run")

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
    logger.debug("made it to run end")


def OCP(OCPvi, OCPti, OCPrate):
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global ACTIVE

    ACTIVE = True

    logger.debug("made it to run")

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
    # logger.debug("made it to run end")


def activecheck():
    while ACTIVE == True:
        client.PumpEvents(1)
        time.sleep(0.5)


def check_vsig_range(filename):
    try:
        ocp_data = pd.read_csv(
            filename,
            sep=" ",
            header=None,
            names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"],
        )
        vsig_last_row_scientific = ocp_data.iloc[-2, ocp_data.columns.get_loc("Vsig")]
        logger.debug("Vsig last row: %s", vsig_last_row_scientific)
        vsig_last_row_decimal = float(vsig_last_row_scientific)
        logger.debug("Vsig last row: %f", vsig_last_row_decimal)

        if -1 < vsig_last_row_decimal and vsig_last_row_decimal < 1:
            logger.debug("Vsig in valid range (-1 to 1). Proceeding to echem experiment")
            return True
        else:
            logger.debug("Vsig not in valid range. Aborting echem experiment")
            return False
    except Exception as exception:
        logger.debug("Error occurred while checking Vsig: %s", exception)
        return False



def mock_CA(MCAvi, MCAti, MCArate):
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global ACTIVE
    ACTIVE = True

    logger.debug("made it to run")

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
    # logger.debug("made it to run end")


@dataclass(config=ConfigDict(validate_assignment=True))
class potentiostat_cv_parameters:
    """CV Setup Parameters"""

    # CV Setup Parameters
    CVvi: float = 0.0  # initial voltage
    CVap1: float = 0.3
    CVap2: float = -0.2
    CVvf: float = -0.2
    CVstep: float = 0.01  # testing step, 100 mv/s
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
    CAv1: float = -2.4  # Step 1 voltage (V)
    CAt1: float = 300.0  # run time 300 seconds
    CAv2: float = 0.0  # Step 2 voltage (V)
    CAt2: float = 0.0  # Step 2 time (s)
    CAsamplerate: float = 0.05  # sample period (s)
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
        if check_vsig_range(COMPLETE_FILE_NAME.with_suffix(".txt")):
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
            while ACTIVE == True:
                client.PumpEvents(1)
                time.sleep(0.5)
            ## echem plot the data
            Analyzer.plotdata("CV", COMPLETE_FILE_NAME)
        disconnectpstat()
        del CONNECTION

    except Exception as e:
        raise gamry_error_decoder(e)
