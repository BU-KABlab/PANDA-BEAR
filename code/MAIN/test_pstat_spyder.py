# -*- coding: utf-8 -*-
"""
Created on Wed Jul 19 14:24:09 2023

@author: Kab Lab
"""
import time
import gamrycontrol as echem
import comtypes.client as client


 
 
if __name__ == "__main__":
    try:
        echem.pstat.Init(echem.devices.EnumSections()[0])  # grab first pstat
        echem.pstat.Open() #open connection to pstat
        echem.setfilename('A1', 'dep')
        ## echem CA - deposition
        echem.chrono(echem.CAvi, echem.CAti, echem.CAv1, echem.CAt1, echem.CAv2, echem.CAt2, echem.CAsamplerate) #CA
        print("made it to try")
        while echem.active == True:
            client.PumpEvents(1)
            time.sleep(0.5)
        ## echem plot the data
        echem.plotdata(echem.CA)
                        

    except Exception as e:
        raise echem.gamry_error_decoder(e)