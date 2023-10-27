import datetime
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import time
import gc
import comtypes
import comtypes.client as client
import pathlib
import random
import Analyzer
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict, FilePath, RootModel, TypeAdapter
# pylint: disable = global-statement

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
        print("\tPstat connected: ", DEVICES.EnumSections()[0])
    else:
        print("\tPstat not connected")


class GamryCOMError(Exception):
    pass


def gamry_error_decoder(e):
    if isinstance(e, comtypes.COMError):
        hresult = 2**32 + e.args[0]
        if hresult & 0x20000000:
            return GamryCOMError(
                "0x{0:08x}: {1}".format(2**32 + e.args[0], e.args[1])
            )
    return e


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
    def __init__(self, dtaq, complete_file_name):
        self.dtaq = dtaq
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

    def _IGamryDtaqEvents_OnDataAvailable(self, this):
        self.cook()
        loading = ["|", "/", "-", "\\"]
        print(f"\rmade it to data available{random.choice(loading)}", end="")

    def _IGamryDtaqEvents_OnDataDone(self, this):
        print("\nmade it to data done")
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
    # print(dtaqsink.acquired_points)
    print("number of data points acquired")
    print(len(DTAQ_SINK.acquired_points))
    # savedata
    # column_names = ["Time", "Vf","Vu","Vsig","Ach","Overload","StopTest","Temp"]
    output = pd.DataFrame(DTAQ_SINK.acquired_points)
    # complete_file_name = os.path(complete_file_name)
    np.savetxt(complete_file_name.with_suffix(".txt"), output)
    print("data saved")


def setfilename(id, experiment):
    """set the file name for the experiment"""
    global COMPLETE_FILE_NAME
    current_time = datetime.datetime.now()
    fileDate = current_time.strftime("%Y-%m-%d")
    cwd = pathlib.Path().absolute()
    filePathPar = pathlib.Path(cwd.parents[1].__str__() + "/data")
    filePath = filePathPar / fileDate
    # complete_file_name = filePath / (target_well + "_" + experiment)
    COMPLETE_FILE_NAME = filePath / ("experiment-" + id + "_" + experiment)
    print(f"eChem: complete file name is: {COMPLETE_FILE_NAME}")
    if not pathlib.Path.exists(filePath):
        print(f"folder does not exist. Making folder: {filePath}")
        pathlib.Path.mkdir(filePath, parents=True, exist_ok=True)
    else:
        print(f"folder {filePath} exists")
    return COMPLETE_FILE_NAME


def cyclic(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle):
    """cyclic voltammetry"""
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global ACTIVE
    # global complete_file_name

    print("made it to run")
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
    print("made it to run end")


def chrono(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate):
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global START_TIME
    global ACTIVE
    # global complete_file_name

    ACTIVE = True
    print("made it to run")

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
    print("made it to run end")


def OCP(OCPvi, OCPti, OCPrate):
    global DTAQ
    global SIGNAL
    global DTAQ_SINK
    global CONNECTION
    global ACTIVE

    ACTIVE = True

    print("made it to run")

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


def mock_CA(MCAvi, MCAti, MCArate):
    global DTAQ
    global SIGNAL
    global DTAQSINK
    global CONNECTION
    global ACTIVE
    global COMPLETE_FILE_NAME
    global GAMRY_COM
    global PSTAT

    ACTIVE = True

    print("made it to run")

    # signal and dtaq object creation
    SIGNAL = client.CreateObject("GamryCOM.GamrySignalConst")
    DTAQ = client.CreateObject("GamryCOM.GamryDtaqOcv")

    DTAQSINK = GamryDtaqEvents(DTAQ, COMPLETE_FILE_NAME)
    CONNECTION = client.GetEvents(DTAQ, DTAQSINK)

    SIGNAL.Init(PSTAT, MCAvi, MCAti, MCArate, GAMRY_COM.PstatMode)
    initializepstat()

    DTAQ.Init(PSTAT)
    PSTAT.SetSignal(SIGNAL)
    PSTAT.SetCell(GAMRY_COM.CellOff)

    DTAQ.Run(True)


def activecheck():
    while ACTIVE == True:
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
        print("Vf last row:", vf_last_row_scientific)
        vf_last_row_decimal = float(vf_last_row_scientific)
        print("Vf last row:", vf_last_row_decimal)

        if -1 < vf_last_row_decimal and vf_last_row_decimal < 1:
            print("Vf in valid range (-1 to 1). Proceeding to echem experiment")
            return True
        else:
            print("Vf not in valid range. Aborting echem experiment")
            return False
    except Exception as exception:
        print("Error occurred while checking Vsig:", exception)
        return False


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


# Mock_CA Setup parameters
MCAvi = 0.0
MCAti = 300
MCArate = 0.5

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
            print("made it to try")
            while ACTIVE == True:
                client.PumpEvents(1)
                time.sleep(0.5)
            ## echem plot the data
            Analyzer.plotdata("CV", COMPLETE_FILE_NAME)
        disconnectpstat()
        del CONNECTION

    except Exception as e:
        raise gamry_error_decoder(e)
