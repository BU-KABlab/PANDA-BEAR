import datetime
import os
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
active = True

class pstatcontrol:
    def __init__(self,name,pstat):
        self.name = name
        self.pstat = pstat
  
    @staticmethod
    def gamry_error_decoder(e):
        if isinstance(e, comtypes.COMError):
            hresult = 2**32 + e.args[0]
            if hresult & 0x20000000:
                return pstatcontrol.GamryCOMError('0x{0:08x}: {1}'.format(2**32 + e.args[0], e.args[1]))
        return e

    @staticmethod
    def initializepstat(pstat):
        pstat.SetCtrlMode(GamryCOM.PstatMode)
        pstat.SetCell(GamryCOM.CellOff)
        pstat.SetIEStability(GamryCOM.StabilityNorm)
        pstat.SetVchRangeMode(True)
        pstat.SetVchRange(10.0)
        pstat.SetIERangeMode(True)
        # the following command allows us to set our range manually
        # pstat.SetIERange (x)

    @staticmethod
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

    class GamryCOMError(Exception):
        pass

    class GamryDtaqEvents(object):
        def __init__(self, dtaq):
            self.dtaq = dtaq
            self.acquired_points = []

        def call_stopacq(self):
            pstatcontrol.stopacq()
        
        def call_savedata(self):
            pstatcontrol.savedata()

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
            self.cook()  # a final cook
            time.sleep(2.0)
            self.call_stopacq()
            self.call_savedata()

    @staticmethod
    def savedata(complete_file_name):
        
        #print(dtaqsink.acquired_points)
        print("number of data points acquired")
        print(len(dtaqsink.acquired_points))
        # savedata
        # column_names = ["Time", "Vf","Vu","Vsig","Ach","Overload","StopTest","Temp"]
        output = pd.DataFrame(dtaqsink.acquired_points)
        np.savetxt(complete_file_name + '.txt', output)
        print("data saved")

    def plotdata(exp_name, complete_file_name):
        if exp_name == 'OCP':
                df = pd.read_csv(complete_file_name + '.txt', sep=" ", header=None,
                                names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"])
                plt.rcParams["figure.dpi"] = 150
                plt.rcParams["figure.facecolor"] = "white"
                plt.plot(df['Time'], df['Vf'])
                plt.xlabel('Time (s)')
                plt.ylabel('Voltage (V)')
        elif exp_name == 'CA':
                df = pd.read_csv(complete_file_name + 'CA.txt', sep=" ", header=None,
                                names=["runtime", "Vf", "Vu", "Im", "Q", "Vsig", "Ach", "IERange", "Over", "StopTest"])
                plt.rcParams["figure.dpi"] = 150
                plt.rcParams["figure.facecolor"] = "white"
                plt.plot(df['runtime'], df['Im'])
                plt.xlabel('Time (s)')
                plt.ylabel('Current (A)')
        elif exp_name == 'CV':
                df = pd.read_csv(complete_file_name + 'CV.txt', sep=" ", header=None,
                                names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest",
                                        "Cycle", "Ach2"])
                plt.rcParams["figure.dpi"] = 150
                plt.rcParams["figure.facecolor"] = "white"
                plt.plot(df['Time'], df['Im'])
                plt.xlabel('Time (s)')
                plt.ylabel('Current (A)')

        plt.tight_layout()
        plt.savefig(complete_file_name + '.png')
        print("plot saved")
    
    def setfilename(target_well, experiment):
        current_time = datetime.datetime.now()
        fileDate = current_time.strftime("%Y-%m-%d")
        filePath = os.path.join(os.path.expanduser("~"), "Documents", "Github","PANDA","data")
        complete_file_name = os.path.join(filePath, fileDate, target_well + '_' + experiment)
        print(complete_file_name)
        if not os.path.exists(filePath):
            os.makedirs(filePath, exist_ok = True)
        return
        
        
class exp:
    @staticmethod
    def CV(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle):
        global dtaq
        global signal
        global dtaqsink
        global pstat
        global connection
        global start_time
        global end_time
        global total_time
        global active

        print("made it to run")

        # signal and dtaq object creation
        signal = client.CreateObject('GamryCOM.GamrySignalRupdn')
        dtaq = client.CreateObject('GamryCOM.GamryDtaqRcv')

        dtaqsink = pstatcontrol.GamryDtaqEvents(dtaq)
        connection = client.GetEvents(dtaq, dtaqsink)
        pstat = client.CreateObject('GamryCOM.GamryPC6Pstat')
        devices = client.CreateObject('GamryCOM.GamryDeviceList')
        pstat.Init(devices.EnumSections()[0])  # grab first pstat
        pstat.Open()

        signal.Init(pstat, CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, 0.0, 0.0, 0.0, CVsamplerate, CVcycle, GamryCOM.PstatMode)
        pstatcontrol.initializepstat(pstat)

        dtaq.Init(pstat)
        pstat.SetSignal(signal)
        pstat.SetCell(GamryCOM.CellOn)

        dtaq.Run(True)
        # Code for timing started
        while active == True:
            client.PumpEvents(1)
            time.sleep(0.5)

        start_time = time.time()
        print("made it to run end")
        

    @staticmethod
    def CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate):
        global dtaq
        global signal
        global dtaqsink
        global pstat
        global connection
        global start_time
        global end_time
        global total_time
        global active

        
        while active == True:
            client.PumpEvents(1)
            time.sleep(0.5)
        

        print("made it to run")

        # signal and dtaq object creation
        signal = client.CreateObject('GamryCOM.GamrySignalDstep')
        dtaq = client.CreateObject('GamryCOM.GamryDtaqChrono')

        dtaqsink = pstatcontrol.GamryDtaqEvents(dtaq)
        connection = client.GetEvents(dtaq, dtaqsink)
        pstat = client.CreateObject('GamryCOM.GamryPC6Pstat')
        devices = client.CreateObject('GamryCOM.GamryDeviceList')
        pstat.Init(devices.EnumSections()[0])  # grab first pstat
        pstat.Open()

        signal.Init(pstat, CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate, GamryCOM.PstatMode)
        pstatcontrol.initializepstat(pstat)

        dtaq.Init(pstat, GamryCOM.ChronoAmp)
        pstat.SetSignal(signal)
        pstat.SetCell(GamryCOM.CellOn)

        dtaq.Run(True)

        # Code for timing started
        start_time = time.time()
        print("made it to run end")

    @staticmethod
    def OCP(OCPvi, OCPti, OCPrate):
        global dtaq
        global signal
        global dtaqsink
        global pstat
        global connection
        global start_time
        global end_time
        global total_time
        global active

        active = True
        
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
        pstatcontrol.initializepstat(pstat)

        dtaq.Init(pstat)
        pstat.SetSignal(signal)
        pstat.SetCell(GamryCOM.CellOff)

        dtaq.Run(True)
        start_time = time.time()
        print("made it to run end")

active = True

# CV Setup Parameters
CVvi = 0.0
CVap1 = -0.8
CVap2 = -0.1
CVvf = -0.1
# CVstep = 0.002
CVstep = 0.1
CVsr1 = 0.05
CVcycle = 3

CVsr2 = CVsr1
CVsr3 = CVsr1
CVsamplerate = CVstep / CVsr1

# CA/CP Setup Parameters
CAvi = 0.0
CAti = 0.0
CAv1 = -2.7
CAt1 = 30
# CAt1 = 300
CAv2 = 0
CAt2 = 0
CAsamplerate = 0.1

# OCP Setup Parameters
OCPvi = 0.0
# OCPti = 150
OCPti = 15
OCPrate = 0.5


if __name__ == "__main__":
    try:
        #pick one of the following to test
        exp.OCP(OCPvi, OCPti, OCPrate)
        #exp.CA(CAvi, CAti, CAv1, CAt1, CAv2, CAt2, CAsamplerate)
        #exp.CV(CVvi, CVap1, CVap2, CVvf, CVsr1, CVsr2, CVsr3, CVsamplerate, CVcycle)     
        print("made it to try")
        while active == True:
            client.PumpEvents(1)
            time.sleep(0.5)
        # code for end time
        end_time = time.time()
        total_time = end_time - start_time
        print("Time to run is ", total_time, " seconds")

    except Exception as e:
        raise pstatcontrol.gamry_error_decoder(e)
