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

def pstatconnect():    
    global pstat
    global devices
    global GamryCOM

    GamryCOM = client.GetModule(["{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}", 1, 0])
    pstat = client.CreateObject("GamryCOM.GamryPC6Pstat")
    devices = client.CreateObject("GamryCOM.GamryDeviceList")
    pstat.Init(devices.EnumSections()[0])  # grab first pstat
    pstat.Open()  # open connection to pstat
    if devices.EnumSections():
        print("\tPstat connected: ", devices.EnumSections()[0])
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
    pstat.SetCtrlMode(GamryCOM.PstatMode)
    pstat.SetCell(GamryCOM.CellOff)
    pstat.SetIEStability(GamryCOM.StabilityNorm)
    pstat.SetVchRangeMode(True)
    pstat.SetVchRange(10.0) #Expected Max Voltage
    pstat.SetIERangeMode(True) #True = Auto, False = Manual
    # the following command allows us to set our range manually
    # pstat.SetIERange (x)


def stopacq():
    global active
    
    active = False
    pstat.SetCell(GamryCOM.CellOff)
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
    pstat.Close()
    # del connection
    time.sleep(15)


def savedata(complete_file_name):
    ''' save the data to a file'''
    #print(dtaqsink.acquired_points)
    print("number of data points acquired")
    print(len(dtaqsink.acquired_points))
    # savedata
    # column_names = ["Time", "Vf","Vu","Vsig","Ach","Overload","StopTest","Temp"]
    output = pd.DataFrame(dtaqsink.acquired_points)
    # complete_file_name = os.path(complete_file_name)
    np.savetxt(complete_file_name.with_suffix(".txt"), output)
    print("data saved")

def setfilename(id, experiment):
    ''' set the file name for the experiment'''
    global complete_file_name
    current_time = datetime.datetime.now()
    fileDate = current_time.strftime("%Y-%m-%d")
    cwd = pathlib.Path().absolute()
    filePathPar = pathlib.Path(cwd.parents[1].__str__() + "/data")
    filePath = filePathPar / fileDate
    #complete_file_name = filePath / (target_well + "_" + experiment)
    complete_file_name = filePath / ("experiment-" + id + "_" + experiment)
    print(f"eChem: complete file name is: {complete_file_name}")
    if not pathlib.Path.exists(filePath):
        print(f"folder does not exist. Making folder: {filePath}")
        pathlib.Path.mkdir(filePath, parents=True, exist_ok=True)
    else:
        print(f"folder {filePath} exists")
    return complete_file_name
        
        

def cyclic(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle):
    ''' cyclic voltammetry'''
    global dtaq
    global signal
    global dtaqsink
    global connection
    global start_time
    global active
    #global complete_file_name
    
    print("made it to run")
    active = True

    # signal and dtaq object creation
    signal = client.CreateObject("GamryCOM.GamrySignalRupdn")
    dtaq = client.CreateObject("GamryCOM.GamryDtaqRcv")
    dtaqsink = GamryDtaqEvents(dtaq, complete_file_name)
    connection = client.GetEvents(dtaq, dtaqsink)

    signal.Init(
        pstat,
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
        GamryCOM.PstatMode,
    )
    initializepstat()
    dtaq.Init(pstat)
    pstat.SetSignal(signal)
    pstat.SetCell(GamryCOM.CellOn)
    dtaq.Run(True)
    # Code for timing started
    #start_time = time.time()
    print("made it to run end")


def chrono(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate):
    global dtaq
    global signal
    global dtaqsink
    global connection
    global start_time
    global active
    #global complete_file_name

    active = True
    print("made it to run")

    # signal and dtaq object creation
    signal = client.CreateObject("GamryCOM.GamrySignalDstep")
    dtaq = client.CreateObject("GamryCOM.GamryDtaqChrono")

    dtaqsink = GamryDtaqEvents(dtaq, complete_file_name)
    connection = client.GetEvents(dtaq, dtaqsink)

    signal.Init(
        pstat, CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate, GamryCOM.PstatMode
    )
    initializepstat()

    dtaq.Init(pstat, GamryCOM.ChronoAmp)
    pstat.SetSignal(signal)
    pstat.SetCell(GamryCOM.CellOn)

    dtaq.Run(True)

    # Code for timing started
    #start_time = time.time()
    print("made it to run end")


def OCP(OCPvi, OCPti, OCPrate):
    global dtaq
    global signal
    global dtaqsink
    global connection
    global start_time
    global active

    active = True

    print("made it to run")

    # signal and dtaq object creation
    signal = client.CreateObject("GamryCOM.GamrySignalConst")
    dtaq = client.CreateObject("GamryCOM.GamryDtaqOcv")

    dtaqsink = GamryDtaqEvents(dtaq, complete_file_name)
    connection = client.GetEvents(dtaq, dtaqsink)
    
    signal.Init(pstat, OCPvi, OCPti, OCPrate, GamryCOM.PstatMode)
    initializepstat()

    dtaq.Init(pstat)
    pstat.SetSignal(signal)
    pstat.SetCell(GamryCOM.CellOff)

    dtaq.Run(True)
    #start_time = time.time()
    #print("made it to run end")


def mock_CA(MCAvi, MCAti, MCArate):
    global dtaq
    global signal
    global dtaqsink
    global connection
    global start_time
    global active

    active = True

    print("made it to run")

    # signal and dtaq object creation
    signal = client.CreateObject("GamryCOM.GamrySignalConst")
    dtaq = client.CreateObject("GamryCOM.GamryDtaqOcv")

    dtaqsink = GamryDtaqEvents(dtaq, complete_file_name)
    connection = client.GetEvents(dtaq, dtaqsink)
    
    signal.Init(pstat, MCAvi, MCAti, MCArate, GamryCOM.PstatMode)
    initializepstat()

    dtaq.Init(pstat)
    pstat.SetSignal(signal)
    pstat.SetCell(GamryCOM.CellOff)

    dtaq.Run(True)
    #start_time = time.time()
    #print("made it to run end")

def activecheck():
    while active == True:
        client.PumpEvents(1)
        time.sleep(0.5)

def check_vsig_range(filename):
    try:
        ocp_data = pd.read_csv(filename, sep=" ", header=None, names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"])
        vsig_last_row_scientific = ocp_data.iloc[-2, ocp_data.columns.get_loc("Vsig")]
        print("Vsig last row:", vsig_last_row_scientific)
        vsig_last_row_decimal = float(vsig_last_row_scientific)
        print("Vsig last row:", vsig_last_row_decimal)

        if -1 < vsig_last_row_decimal and vsig_last_row_decimal < 1:
            print("Vsig in valid range (-1 to 1). Proceeding to echem experiment")
            return True
        else:
            print("Vsig not in valid range. Aborting echem experiment")
            return False
    except Exception as e:
        print("Error occurred while checking Vsig:", e)
        return False

# CV Setup Parameters
CVvi = 0.0  # initial voltage
CVap1 = 0.3
CVap2 = -0.2
CVvf = -0.2

CVstep = 0.01  # testing step, 100 mv/s
CVsr1 = 0.1
CVcycle = 3

CVsr2 = CVsr1
CVsr3 = CVsr1
CVsamplerate = CVstep / CVsr1

# CA/CP Setup Parameters
CAvi = 0.0 #Pre-step voltage (V)
CAti = 0.0 #Pre-step delay time (s)
CAv1 = -2.4 #Step 1 voltage (V)
CAt1 = 300 #run time 300 seconds
CAv2 = 0 #Step 2 voltage (V)
CAt2 = 0 #Step 2 time (s)
CAsamplerate = 0.05 #sample period (s)
# Max current (mA)
# Limit I (mA/cm^2)
# PF Corr. (ohm)
# Equil. time (s)
# Expected Max V (V)
# Initial Delay on
# Initial Delay (s)

# OCP Setup Parameters
OCPvi = 0.0
# OCPti = 150
OCPti = 15
OCPrate = 0.5

#Mock_CA Setup parameters
MCAvi = 0.0
MCAti = 300
MCArate = 0.5

if __name__ == "__main__":
    try:
        pstatconnect()  # grab first pstat
        complete_file_name = setfilename('F1','OCP')
        OCP(OCPvi, OCPti,OCPrate)
        activecheck()
#        while active == True:
                #client.PumpEvents(1)
                #time.sleep(0.5)
        ## echem CA - deposition
        if check_vsig_range(complete_file_name.with_suffix('.txt')):
            complete_file_name = setfilename('F1', 'CV')
            cyclic(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)
            #chrono(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
            print("made it to try")
            while active == True:
                client.PumpEvents(1)
                time.sleep(0.5)
            ## echem plot the data
            Analyzer.plotdata('CV', complete_file_name)
        disconnectpstat()
        del connection

    except Exception as e:
        raise gamry_error_decoder(e)
