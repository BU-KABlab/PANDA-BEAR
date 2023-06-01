import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
import gc
import comtypes
import comtypes.client as client

#Bring in gamrycom and pstat
#GamryCOM=client.GetModule(r'C:\Program Files (x86)\Gamry Instruments\Framework\GamryCOM.exe')
GamryCOM = client.GetModule(['{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}', 1, 0])

class GamryCOMError(Exception):
    pass

def gamry_error_decoder(e):
    if isinstance(e, comtypes.COMError):
        hresult = 2**32+e.args[0]
        if hresult & 0x20000000:
            return GamryCOMError('0x{0:08x}: {1}'.format(2**32+e.args[0], e.args[1]))
    return e

def initializepstat(pstat):
    pstat.SetCtrlMode(GamryCOM.PstatMode)
    pstat.SetCell(GamryCOM.CellOff)
    pstat.SetIEStability(GamryCOM.StabilityNorm)
    pstat.SetVchRangeMode(True)
    pstat.SetVchRange(10.0)
    pstat.SetIERangeMode(True)
    #the following command allows us to set our range manually
    #pstat.SetIERange (x)
    
class GamryDtaqEvents(object):
    def __init__(self, dtaq):
        self.dtaq = dtaq
        self.acquired_points = []

    def cook(self):
        count = 1
        while count > 0:
            count, points = self.dtaq.Cook(10)
            # The columns exposed by GamryDtaq.Cook vary by dtaq and are
            # documented in the Toolkit Reference Manual.
            self.acquired_points.extend(zip(*points))
        
    def _IGamryDtaqEvents_OnDataAvailable(self, this):
        self.cook()
        print("made it to data available")

    def _IGamryDtaqEvents_OnDataDone(self, this):
        print("made it to data done")
        self.cook() # a final cook
        time.sleep(2.0)              
        stopacq()
        
def stopacq():
    global active
    global connection
    
    active = False            
    pstat.SetCell(GamryCOM.CellOff)
    time.sleep(1)
    pstat.Close()
    del connection
    gc.collect()
    return    

class savedataCV(object):
    def __init__(self, saveCV):
        self.saveCV = saveCV
        
        print(dtaqsink.acquired_points)
        print(len(dtaqsink.acquired_points))

        #savedata
        column_names = ["Time", "Vf","Vu","Im","Vsig","Ach","IERange","Overload","StopTest","Cycle","Ach2"]
        output = pd.DataFrame(dtaqsink.acquired_points, columns = column_names)
        np.savetxt('2023-05-18_CV-Test1.txt', output)

        #plotdata
        df = pd.read_csv('2023-05-18_CV-Test1.txt', sep=" ", header=None, names=["Time", "Vf","Vu","Im","Vsig","Ach","IERange","Overload","StopTest","Cycle","Ach2"])
        plt.rcParams["figure.dpi"]=150
        plt.rcParams["figure.facecolor"]="white"
        plt.plot(df['Time'], df['Im'])
        plt.xlabel('Time (s)')
        plt.ylabel('Current (A)')
        plt.tight_layout()
        plt.savefig('2023-05-18_CV-Test1')

class savedataCA(object):
    def __init__(self, saveCA):
        self.saveCA = saveCA

        print(dtaqsink.acquired_points)
        print(len(dtaqsink.acquired_points))

        #savedata
        column_names = ["Time", "Vf","Vu","Im","Q","Vsig","Ach","IERange","Overload","StopTest"]
        output = pd.DataFrame(dtaqsink.acquired_points, columns = column_names)
        np.savetxt('2023-05-17_CA-Test3.txt', output)

        #plotdata
        df = pd.read_csv('2023-05-17_CA-Test3.txt', sep=" ", header=None, names=["runtime", "Vf", "Vu","Im","Q","Vsig","Ach","IERange","Over","StopTest"])
        plt.rcParams["figure.dpi"]=150
        plt.rcParams["figure.facecolor"]="white"
        plt.plot(df['runtime'], df['Im'])
        plt.xlabel('Time (s)')
        plt.ylabel('Current (A)')
        plt.tight_layout()
        plt.savefig('2023-05-17_CA-Test3')

class savedataOCP(object):
    def __init__(self, saveOCP):
        self.saveOCP = saveOCP

        print(dtaqsink.acquired_points)
        print(len(dtaqsink.acquired_points))

        #savedata
        column_names = ["Time", "Vf","Vu","Im","Q","Vsig","Ach","IERange","Overload","StopTest"]
        output = pd.DataFrame(dtaqsink.acquired_points, columns = column_names)
        np.savetxt('2023-05-17_CA-Test3.txt', output)

        #plotdata
        df = pd.read_csv('2023-05-17_CA-Test3.txt', sep=" ", header=None, names=["runtime", "Vf", "Vu","Im","Q","Vsig","Ach","IERange","Over","StopTest"])
        plt.rcParams["figure.dpi"]=150
        plt.rcParams["figure.facecolor"]="white"
        plt.plot(df['runtime'], df['Im'])
        plt.xlabel('Time (s)')
        plt.ylabel('Current (A)')
        plt.tight_layout()
        plt.savefig('2023-05-17_CA-Test3')
        
        
def CV(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle):
    global dtaq
    global signal
    global dtaqsink
    global pstat
    global connection
    global dtaqsink
    global start_time
    global end_time
    global total_time

    print("made it to run")

    # signal and dtaq object creation
    signal = client.CreateObject('GamryCOM.GamrySignalRupdn')
    dtaq = client.CreateObject('GamryCOM.GamryDtaqRcv')

    dtaqsink = GamryDtaqEvents(dtaq)
    connection = client.GetEvents(dtaq, dtaqsink)
    pstat = client.CreateObject('GamryCOM.GamryPC6Pstat')
    devices = client.CreateObject('GamryCOM.GamryDeviceList')
    pstat.Init(devices.EnumSections()[0])  # grab first pstat
    pstat.Open()

    signal.Init(pstat, CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, 0.0, 0.0, 0.0, CVsamplerate, CVcycle, GamryCOM.PstatMode)
    initializepstat(pstat)

    dtaq.Init(pstat)
    pstat.SetSignal(signal)
    pstat.SetCell(GamryCOM.CellOn)

    dtaq.Run(True)
    saveCV.Run(True)
    # Code for timing started
    start_time = time.time()
    print("made it to run end")
    
def CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate):
    global dtaq
    global signal
    global dtaqsink
    global pstat
    global connection
    global dtaqsink
    global start_time
    global end_time
    global total_time

    print("made it to run")

    # signal and dtaq object creation
    signal = client.CreateObject('GamryCOM.GamrySignalDstep')
    dtaq = client.CreateObject('GamryCOM.GamryDtaqChrono')

    dtaqsink = GamryDtaqEvents(dtaq)
    connection = client.GetEvents(dtaq, dtaqsink)
    pstat = client.CreateObject('GamryCOM.GamryPC6Pstat')
    devices = client.CreateObject('GamryCOM.GamryDeviceList')
    pstat.Init(devices.EnumSections()[0])  # grab first pstat
    pstat.Open()

    signal.Init(pstat, CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate, GamryCOM.PstatMode)
    initializepstat(pstat)

    dtaq.Init(pstat, GamryCOM.ChronoAmp)
    pstat.SetSignal(signal)
    pstat.SetCell(GamryCOM.CellOn)

    dtaq.Run(True)
    saveCA.Run(True)
    # Code for timing started
    start_time = time.time()
    print("made it to run end")
    
def OCP(OCPvi, OCPti, OCPrate):
    global dtaq
    global signal
    global dtaqsink
    global pstat
    global connection
    global dtaqsink
    print("made it to run")

    # signal and dtaq object creation
    signal = client.CreateObject('GamryCOM.GamrySignalConst')
    dtaq = client.CreateObject('GamryCOM.GamryDtaqOcv')

    dtaqsink = GamryDtaqEvents(dtaq)
    connection = client.GetEvents(dtaq, dtaqsink)
    pstat = client.CreateObject('GamryCOM.GamryPC6Pstat')
    devices = client.CreateObject('GamryCOM.GamryDeviceList')
    pstat.Init(devices.EnumSections()[0])  # grab first pstat

    pstat.Open()

    signal.Init(pstat, OCPvi, OCPti, OCPrate, GamryCOM.PstatMode)
    initializepstat(pstat)

    dtaq.Init(pstat)
    pstat.SetSignal(signal)
    pstat.SetCell(GamryCOM.CellOff)

    dtaq.Run(True)
    print("made it to run end")    
    
active = True

# CV Setup Parameters
CVvi = 0.0
CVap1 = -0.8
CVap2 = -0.1
CVfin = -0.1
CVstep = 0.002
CVsr1 = 0.05
CVcycle = 3

CVsr2 = CVsr1
CVsr3 = CVsr1
CVsamplerate = CVstep / CVsr1

# CA/CP Setup Parameters
CAvi = 0.0
CAti = 0.0
CAv1 = -2.7
CAt1 = 300
CAv2 = 0
CAt2 = 0
CAsamplerate = 0.1

#OCP Setup Parameters
OCPvi = 0.0
OCPti = 150
OCPrate = 0.5


if __name__ == "__main__":
    try:
        #pick one of the following to test
        #CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
        #CV(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)
        print("made it to try")
        while active == True:
            client.PumpEvents(1)
            time.sleep(0.1)
        # code for end time
        end_time = time.time()
        total_time = end_time - start_time
        print("Time to run is ", total_time, " seconds")

    except Exception as e:
        raise gamry_error_decoder(e)
