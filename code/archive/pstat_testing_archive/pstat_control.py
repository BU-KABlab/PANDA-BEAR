
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

#Gamry classes and definitions
class GamryCOMError(Exception):
    pass

def gamry_error_decoder(e):
    if isinstance(e, comtypes.COMError):
        hresult = 2**32+e.args[0]
        if hresult & 0x20000000:
            return GamryCOMError('0x{0:08x}: {1}'.format(2**32+e.args[0], e.args[1]))
    return e

######################################################
######################################################
######################################################
#### WIP on adding classes
class CV:
    ...
        **kwargs:
            qt # s, quit time
    ...
    def __init__(self,initv,apex1,apex2,finalv,stepsize,scanrate1,cycles,folder,filename,header,path_lib, **kwargs):
        self.fileName = filename
        self.folder = folder
        self.text = ''

        if 'qt' in kwargs:
            qt = kwargs.get('qt')
        else:
            qt = 2

        self.head = 'c\x02\0\0\nfolder: ' + folder + '\nfileoverride\n' + \
                    'header: ' + header + '\n\n'
        self.body = 'tech=cv\nVi=' + str(Vi) + '\neh=' + str(eh) + '\nel=' + \
                    str(el) + '\npn=' + pn + '\ncl=' + str(nSweeps) + \
                    '\nefon\nef=' + str(Efin) + '\nsi=' + str(dE) + \
                    '\nqt=' + str(qt) + '\nv=' + str(sr) + '\nsens=' + str(sens)
        self.body2 = self.body + '\nrun\nsave:' + self.fileName + \
                         '\ntsave:' + self.fileName 
        self.foot = '\n forcequit: yesiamsure\n'
        self.text = self.head + self.body2 + self.foot
######################################################
######################################################
######################################################

# inital settings for pstat. Sets DC Offset here based on dc setup parameter
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
              
    pstat.SetCell(GamryCOM.CellOff)
    time.sleep(1)
    pstat.Close()
    del connection
    gc.collect()
    return

def run(init, ap1, ap2, fin, sr1, sr2, sr3, sample, cycle):
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
    
    signal.Init(pstat, init, ap1, ap2, fin, sr1, sr2, sr3, 0.0, 0.0, 0.0, sample, cycle, GamryCOM.PstatMode)
    initializepstat(pstat)

    dtaq.Init(pstat)
    pstat.SetSignal(signal)
    pstat.SetCell(GamryCOM.CellOn)

    dtaq.Run(True)
    # Code for timing started
    start_time = time.time()
    print("made it to run end")

active = True

# CV Setup Parameters
initv = 0.0
apex1 = -0.8
apex2 = -0.1
finalv = -0.1
stepsize = 0.002
scanrate1 = 0.05
cycles = 3

scanrate2 = scanrate1
scanrate3 = scanrate1
samplerate = stepsize / scanrate1

#########################################
#########################################
if __name__ == "__main__":
    try:
        run(initv, apex1, apex2, finalv, scanrate1, scanrate2, scanrate3, samplerate, cycles)
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