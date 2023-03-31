
import os
import numpy as np
import matplotlib.pyplot as plt

#import crispy.load_data as load_data
#import crispy.save_data as save_data
#import crispy.gamrypstat as gamrypstat

#from __future__ import print_function
import comtypes
import comtypes.client as client

#Bring in gamrycom and pstat
GamryCOM=client.GetModule(r'C:\Program Files (x86)\Gamry Instruments\Framework\GamryCOM.exe')

#Gamry classes and definitions
class GamryCOMError(Exception):
    pass

def gamry_error_decoder(e):
    if isinstance(e, comtypes.COMError):
        hresult = 2**32+e.args[0]
        if hresult & 0x20000000:
            return GamryCOMError('0x{0:08x}: {1}'.format(2**32+e.args[0], e.args[1]))
    return e

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

    def _IGamryDtaqEvents_OnDataDone(self, this):
        self.cook() # a final cook
        #TODO:  indicate completion to enclosing code?

############
# Hardware #
############

#references the devices
devices=client.CreateObject('GamryCOM.GamryDeviceList')
#shows the devices
print(devices.EnumSections())
#loads the potentiostat function
pstat=client.CreateObject('GamryCOM.GamryPC6Pstat')
#initializes the potentiostat of choice
pstat.Init(devices.EnumSections()[0]) # grab first pstat
#Opens communication with the potentiostat
pstat.Open() 

###################
# Data Collection #
###################

#Open Circuit#
#sets up the dtaq (data collector)
#dtaqocv=client.CreateObject('GamryCOM.GamryDtaqOcv')
#initializes the data collection for the potentiostat
#dtaqocv.Init(pstat)
#init - initialize objext prior to use
#NOTE# Cell state for pstat should be left in OFF position
#dtaqocv.Cook(NumPoints, data)
    #cook - retrieves points from the data acquisition queue
        #NumPoints - number of points to cook, returned as number of points actually cooked
        #Data - SAFEARRAY containing cooked points
        #Element/Value/Variant Type
            #0/Time/VT_R4
            #1/Vf/VT_R4
            #2/Vm/VT_R4
            #3/Vsig/VT_R4
            #4/Ach/VT_R4
            #5/Overload/VT_I4
            #6/StopTest/VT_I4
#dtaqocv.SetStopADVMin(Enable, Value) 
    #change in voltage limit that will terminate data acquisition
    #Terminate if abs(dE/dt)<Value
    #used to run a sample until it shows stable behavior
#dtaqocv.SetStopADVMax(Enable, Value)
    #Terminate if abs(dE/dt)>Value


#Chronoamperometry#
#sets up the dtaq (data collector)
dtaqchrono=client.CreateObject('GamryCOM.GamryDtaqChrono')
#initializes the data collection for the potentiostat
dtaqchrono.Init(pstat, GamryCOM.ChronoAmp)
#dtaqchrono.Cook(10) /////////////////NOT HERE/////////////
#cook - retrieves points from the data acquisition queue
    #NumPoints - number of points to cook, returned as number of points actually cooked
    #Data - SAFEARRAY containing cooked points
    #Element/Value/Variant Type
        #0/Time/VT_R4
        #1/Vf/VT_R4
        #2/Vu/VT_R4
        #3/Im/VT_R4
        #4/Q/VT_R4
        #5/Vsig/VT_R4
        #6/Ach/VT_R4
        #7/IERange/VT_R4
        #7/Overload/VT_I4
        #8/StopTest/VT_I4
        #Ref pg 245
#dtaqchrono.SetThreshIMin(Enable, Value) #enable StopAt if I<Value
#dtaqchrono.SetThreshIMax(Enable, Value) #enable StopAt if I>Value
#dtaqchrono.SetThreshVMin(Enable, Value) #enable StopAt if V<Value
##//dtaqchrono.SetThreshVMax(Enable, 1) #enable StopAt if V>Value
#dtaqchrono.SetThreshTMin(Enable, Value) #enable StopAt if T<Value
#dtaqchrono.SetThreshTMax(Enable, Value) #enable StopAt if T>Value
#dtaqchrono.SetThreshXMin(Enable, Value) #enable StopAt if I,Q,V<Value, used to limit a negative current, charge, or voltage swing
#dtaqchrono.SetThreshXMax(Enable, Value) #enable StopAt if I,Q,V>Value
#dtaqchrono.SetStopAtDelayMin(Value) #value is the delay for this number of points, used to avoid premature detmination of data acquisiton due to noise
#stop

#Cyclic Voltammetry#
#sets up the dtaq (data collector)
#dtaqrcv=client.CreateObject('GamryCOM.GamryDtaqRcv')
#initializes the data collection for the potentiostat
#dtaqrcv.Init(pstat)
#init - initialize objext prior to use
#NOTE# Cell state for pstat should be left in OFF position
#dtaqrcv.Cook(NumPoints, data)
    #cook - retrieves points from the data acquisition queue
        #NumPoints - number of points to cook, returned as number of points actually cooked
        #Data - SAFEARRAY containing cooked points
        #Element/Value/Variant Type
            #0/Time/VT_R4
            #1/Vf/VT_R4
            #2/Vm/VT_R4
            #3/Vsig/VT_R4
            #4/Ach/VT_R4
            #5/Overload/VT_I4
            #6/StopTest/VT_I4
#dtaqrcv.SetThreshIMin(Enable, Value) #enable StopAt if I<Value
#dtaqrcv.SetThreshIMax(Enable, Value) #enable StopAt if I>Value
#dtaqrcv.SetThreshVMin(Enable, Value) #enable StopAt if V<Value
#dtaqrcv.SetThreshVMax(Enable, Value) #enable StopAt if V>Value
#dtaqrcv.SetThreshTMin(Enable, Value) #enable StopAt if T<Value
#dtaqrcv.SetThreshTMax(Enable, Value) #enable StopAt if T>Value
#dtaqrcv.SetStopIMin(Enable, Value) 
    #change in voltage limit that will terminate data acquisition
    #Terminate if abs(dE/dt)<Value
    #used to run a sample until it shows stable behavior
#dtaqrcv.SetStopIMax(Enable, Value)
    #Terminate if abs(dE/dt)>Value
#dtaqrcv.SetStopAtDelayIMin(Enable, Value) 
#dtaqrcv.SetStopAtDelayIMax(Enable, Value) 



####################
# Technique to run #
####################

#Open Circuit#
#GamrySignalArray (p351)
#sigarray=client.CreateObject('GamryCOM.GamrySignalArray')
#sigarray.Init(pstat, 
#              Cycles, 
#              SampleRate, 
#              SamplesPerCycle, 
#              SignalArray, 
#              GamryCOM.PstatMode)

#Chronoamperometry#
#GamrySignalRamp (p362) - ramp waveform, starting value, ending value, ramp rate, data acquisition rate
sigramp=client.CreateObject('GamryCOM.GamrySignalRamp')
sigramp.Init(pstat, 
             0, 
             1, 
             .1, 
             1, 
             GamryCOM.PstatMode)
#all values are in V or V/s or s
######sigramp.Init(pstat, Sinitial, Sfinal, Scanrate, Samplerate, CtrlMode)

#Cyclic Voltammetry#
#GamrySignalRupdn (p373)
#Tri-value ramp waveform typically used for CV, combined with RCV dtaq for data acquisition
#sigRupdn=client.CreateObject('GamryCOM.GamrySignalRupdn')
#sigRupdn.Init(pstat, 
#              Sinit, #V
#              Sapex1,#V
#              Sapex2,#V
#              Sfinal, #V
#              ScanInit, #V/s
#              ScanApex,#V/s
#              ScanFinal,#V/s
#              HoldTime0,#time to hold apex1 in s
#              HoldTime1,#time to hold apex2 in s
#              HoldTime2,#stime to hold Sfinal in s
#              SampleRate,#time between data acquisition steps in s
#              Cycles, #number of cycles to run
#              GamryCOM.PstatMode)

pstat.SetSignal(sigramp)
pstat.SetCell(GamryCOM.CellOn)

dtaqsink = GamryDtaqEvents(dtaqchrono)

client.ShowEvents(dtaqchrono)
connection = client.GetEvents(dtaqchrono, dtaqsink)

try:
    dtaqchrono.Run(True)
except Exception as e:
    raise gamry_error_decoder(e)

client.PumpEvents(1)
print(len(dtaqsink.acquired_points))

del connection 

pstat.SetCell(GamryCOM.CellOff)
import time
time.sleep(20)
dtaqchrono.Stop()
acquired_points = []
count = 1
while count > 0:
    count, points = dtaqchrono.cook(10)
    # The columns exposed by GamryDtaq.Cook vary by dtaq and are
    # documented in the Toolkit Reference Manual.
    acquired_points.extend(zip(*points))

acquired_points = np.array(acquired_points)
np.savetxt('testhq22.csv', acquired_points)

pstat.Close()
return 
#return jsonify({'data': acquired_points.tolist()})


