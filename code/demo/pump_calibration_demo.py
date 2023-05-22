# -*- coding: utf-8 -*-
"""
Created on Mon Apr 24 14:54:05 2023

@author: Kab Lab
"""

from nesp_lib import Port, Pump, PumpingDirection
import serial
import time

port = Port('COM5',19200)
pump = Pump(port)
pump.syringe_diameter = 4.699 #milimeters

pump.pumping_rate = 0.5

pump.pumping_volume = 0.1
#pump.pumping_direction = PumpingDirection.INFUSE
pump.pumping_direction = PumpingDirection.WITHDRAW
pump.run(False)