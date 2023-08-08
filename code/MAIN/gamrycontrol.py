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

# Bring in gamrycom and pstat
# GamryCOM=client.GetModule(r'C:\Program Files (x86)\Gamry Instruments\Framework\GamryCOM.exe')

GamryCOM = client.GetModule(["{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}", 1, 0])
pstat = client.CreateObject("GamryCOM.GamryPC6Pstat")
devices = client.CreateObject("GamryCOM.GamryDeviceList")
active = True
# complete_file_name = 'test'


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


def initializepstat(pstat):
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
    global connection

    active = False
    pstat.SetCell(GamryCOM.CellOff)
    time.sleep(1)
    #    pstat.Close()
    #    del connection
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
    global pstat
    global connection

    pstat.Close()
    # del connection
    time.sleep(15)


def savedata(complete_file_name):
    # print(dtaqsink.acquired_points)
    print("number of data points acquired")
    print(len(dtaqsink.acquired_points))
    # savedata
    # column_names = ["Time", "Vf","Vu","Vsig","Ach","Overload","StopTest","Temp"]
    output = pd.DataFrame(dtaqsink.acquired_points)
    # complete_file_name = os.path(complete_file_name)
    np.savetxt(complete_file_name.with_suffix(".txt"), output)
    print("data saved")


def plotdata(exp_name, complete_file_name, showplot=False, is_replicate=False):
    # complete_file_name = os.path(complete_file_name)
    if exp_name == "OCP":
        df = pd.read_csv(
            complete_file_name.with_suffix(".txt"),
            sep=" ",
            header=None,
            names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"],
        )
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["figure.facecolor"] = "white"
        plt.plot(df["Time"], df["Vf"])
        plt.xlabel("Time (s)")
        plt.ylabel("Voltage (V)")
    
    elif exp_name == "CA":
        df = pd.read_csv(
            complete_file_name.with_suffix(".txt"),
            sep=" ",
            header=None,
            names=[
                "runtime",
                "Vf",
                "Vu",
                "Im",
                "Q",
                "Vsig",
                "Ach",
                "IERange",
                "Over",
                "StopTest",
            ],
        )
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["figure.facecolor"] = "white"
        plt.plot(df["runtime"], df["Im"])
        plt.xlabel("Time (s)")
        plt.ylabel("Current (A)")
    
    elif exp_name == "CV":
        df = pd.read_csv(
            complete_file_name.with_suffix(".txt"),
            sep=" ",
            header=None,
            names=[
                "Time",
                "Vf",
                "Vu",
                "Im",
                "Vsig",
                "Ach",
                "IERange",
                "Overload",
                "StopTest",
                "Cycle",
                "Ach2",
            ],
        )
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["figure.facecolor"] = "white"
        # Check for NaN values in the 'Cycle' column and drop them
        df = df.dropna(subset=["Cycle"])

        # Convert the 'Cycle' column to integers
        df["Cycle"] = df["Cycle"].astype(int)

        # Find the maximum cycle number
        max_cycle = df["Cycle"].max()

        # Create a list of custom dash patterns for each cycle
        dash_patterns = [
            (5 * (i + 1), 4 * (i + 1), 3 * (i + 1), 2 * (i + 1))
            for i in range(max_cycle)
        ]

        # Create a 'viridis' colormap with the number of colors equal to the number of cycles
        colors = cm.cool(np.linspace(0, 1, max_cycle))

        # Plot values for vsig vs Im
        # plot only the 2nd cycle
        df2 = df[df["Cycle"] == 1]
        dashes = dash_patterns[1]
        plt.plot(
            df2["Vsig"],
            df2["Im"],
            linestyle="--",
            dashes=dashes,
            color=colors[1],
            label=f"Cycle {1}"
        )

        plt.xlabel("V vs Ag/AgCl (V)")
        plt.ylabel("Current (A)")
        if showplot == True:
            plt.show()

    plt.tight_layout()
    plt.savefig(complete_file_name.with_suffix(".png"))
    # are we doing replicates? If so don't close the plot yet
    if is_replicate:
        pass
    else:
        plt.close()
    print("plot saved")


def setfilename(target_well, experiment):
    global complete_file_name
    current_time = datetime.datetime.now()
    fileDate = current_time.strftime("%Y-%m-%d")
    cwd = pathlib.Path().absolute()
    filePathPar = pathlib.Path(cwd.parents[1].__str__() + "/data")
    filePath = filePathPar / fileDate
    complete_file_name = filePath / (target_well + "_" + experiment)
    print(f"eChem: complete file name is: {complete_file_name}")
    if not pathlib.Path.exists(filePath):
        print(f"folder does not exist. Making folder: {filePath}")
        pathlib.Path.mkdir(filePath, parents=True, exist_ok=True)
    else:
        print(f"folder {filePath} exists")
    return complete_file_name


def cyclic(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle):
    """cyclic chronoamperometry"""
    global dtaq
    global signal
    global dtaqsink
    global pstat
    global connection
    #global start_time
    global end_time
    global total_time
    global active
    global GamryCOM
    # global complete_file_name

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
    initializepstat(pstat)
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
    global pstat
    global connection
    #global start_time
    global end_time
    global total_time
    global active
    global GamryCom
    # global complete_file_name

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
    initializepstat(pstat)

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
    global pstat
    global connection
    #global start_time
    global end_time
    global total_time
    global active

    active = True

    print("made it to run")

    # signal and dtaq object creation
    signal = client.CreateObject("GamryCOM.GamrySignalConst")
    dtaq = client.CreateObject("GamryCOM.GamryDtaqOcv")

    dtaqsink = GamryDtaqEvents(dtaq, complete_file_name)
    connection = client.GetEvents(dtaq, dtaqsink)

    signal.Init(pstat, OCPvi, OCPti, OCPrate, GamryCOM.PstatMode)
    initializepstat(pstat)

    dtaq.Init(pstat)
    pstat.SetSignal(signal)
    pstat.SetCell(GamryCOM.CellOff)

    dtaq.Run(True)
    #start_time = time.time()
    print("made it to run end")


active = True


def errortest():
    testerror = comtypes.COMError(0x20000000, None, (None, None, None, None))
    raise gamry_error_decoder(testerror)


# CV Setup Parameters
CVvi = 0.0  # initial voltage
CVap1 = -0.8
CVap2 = -0.1
CVvf = -0.1

CVstep = 0.01  # testing step, 100 mv/s
CVsr1 = 0.1
CVcycle = 3

CVsr2 = CVsr1
CVsr3 = CVsr1
CVsamplerate = CVstep / CVsr1

# CA/CP Setup Parameters
CAvi = 0.0  # Pre-step voltage (V)
CAti = 0.0  # Pre-step delay time (s)
CAv1 = -2.4  # Step 1 voltage (V)
CAt1 = 300  # run time 300 seconds
CAv2 = 0  # Step 2 voltage (V)
CAt2 = 0  # Step 2 time (s)
CAsamplerate = 0.05  # sample period (s)
# Max current (mA) - see init statement
# Limit I (mA/cm^2)
# PF Corr. (ohm)
# Equil. time (s)
# Expected Max V (V) - see init statement
# Initial Delay on
# Initial Delay (s)

# OCP Setup Parameters
OCPvi = 0.0
# OCPti = 150
OCPti = 15
OCPrate = 0.5


if __name__ == "__main__":
    try:
        pstat.Init(devices.EnumSections()[0])  # grab first pstat
        pstat.Open()  # open connection to pstat
        complete_file_name = setfilename("A1", "dep")
        ## echem CA - deposition
        chrono(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)  # CA
        print("made it to try")
        while active == True:
            client.PumpEvents(1)
            time.sleep(0.5)
        ## echem plot the data
        plotdata("CA", complete_file_name)
        pstat.Close()
        del connection

    except Exception as e:
        raise gamry_error_decoder(e)
