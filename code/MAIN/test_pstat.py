import time
import gamrycontrol as echem
import comtypes
import comtypes.client as client

def gamry_error_decoder(e):
    if isinstance(e, comtypes.COMError):
        hresult = 2**32 + e.args[0]
        if hresult & 0x20000000:
            return echem.GamryCOMError('0x{0:08x}: {1}'.format(2**32 + e.args[0], e.args[1]))
    return e
 
GamryCOM = client.GetModule(['{BD962F0D-A990-4823-9CF5-284D1CDD9C6D}', 1, 0])
pstat = client.CreateObject('GamryCOM.GamryPC6Pstat')
devices = client.CreateObject('GamryCOM.GamryDeviceList') 
    
if __name__ == "__main__":
    try:
        echem.PSTAT.Init(devices.EnumSections()[0])  # grab first pstat
        echem.PSTAT.Open() #open connection to pstat
        complete_file_name = echem.setfilename('A4', 'dep')
        ## echem CA - deposition
        echem.chrono(echem.CAvi, echem.CAti, echem.CAv1, echem.CAt1, echem.CAv2, echem.CAt2, echem.CAsamplerate) #CA
        print("made it to try")
        while echem.ACTIVE == True:
            client.PumpEvents(1)
            time.sleep(0.5)
        ## echem plot the data
        echem.plotdata('CA', complete_file_name)
        #echem.pstat.Close()

    except Exception as e:
        raise gamry_error_decoder(e)
        
    finally:
        echem.PSTAT.Close()