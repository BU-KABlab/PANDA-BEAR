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
        pstat.Close()
        print("pstat closed")

    except Exception as e:
        raise gamry_error_decoder(e)