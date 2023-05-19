import serial
import time
import nesp_lib
import winsound #for making beeping sounds
#from classes import Vial, Wells


def PUMP_WITHDRAW(volume:float,rate:float,ser_pump):
    '''Set the pump direction to withdraw the given volume at the given rate
        volume <float> (ml) | rate <float> (ml/m)
    
    Return the cummulative volue withdrawn when complete'''
    if ser_pump.volume_withdrawn + volume >= 0.2:
        Exception("The command will overfill the pipette. Not running")
    else:
        ser_pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        # Sets the pumping volume of the pump in units of milliliters.
        ser_pump.pumping_volume = volume
        # Sets the pumping rate of the pump in units of milliliters per minute.
        ser_pump.pumping_rate = rate
        ser_pump.run()
        while pump.running:
            pass
        time.sleep(2)
    return ser_pump.volume_withdrawn

def PUMP_INFUSE(volume:float,rate:float,pump):
    '''Set the pump direction to infuse the given volume at the given rate
    
    volume <float> (ml) | rate <float> (ml/m)
    
    Returns the cummulative volume infused when complete'''
    pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
    # Sets the pumping volume of the pump in units of milliliters.
    pump.pumping_volume = volume
    # Sets the pumping rate of the pump in units of milliliters per minute.
    pump.pumping_rate = rate
    pump.run()
    while pump.running:
        pass
    time.sleep(2)
    return pump.volume_infused

def SET_UP_PUMP():
    # set up WPI syringe pump
    pump_port = nesp_lib.Port('COM5',19200)
    pump = nesp_lib.Pump(pump_port)
    pump.syringe_diameter = 4.699 #milimeters
    pump.volume_infused_clear()
    pump.volume_withdrawn_clear()
    print(f'Pump at address: {pump.address}')
    return pump

try:
    
    protocol_ul = [100,100,100,60,60,60,50,50,50,40,40,40]
    purge_vol_ul = 20
    #set up the WPI syringe pump
    pump = SET_UP_PUMP()
    for i in protocol_ul:
        volume_ml = i/1000
        purge_ml = purge_vol_ul/1000
        initial_withdraw = volume_ml + 2*purge_ml
        print(f'Withdrawing {volume_ml}ml with additional {purge_ml*2}ml')    
        response = PUMP_WITHDRAW(initial_withdraw,0.4,pump)
        time.sleep(10)
        print(f'Pump has withdrawn: {response}ml')
        print('Purging')
        response = PUMP_INFUSE(purge_ml,0.2,pump)
        time.sleep(10)
        print(f'Pump has infused: {response}ml')
        print(f'Infusing {volume_ml}ml')
        response = PUMP_INFUSE(volume_ml,0.2,pump)
        time.sleep(10)
        print(f'Pump has infused: {response}ml')
        print('Purging')
        response = PUMP_INFUSE(purge_ml,0.2,pump)
        time.sleep(10)
        print(f'Pump has infused: {response}ml')
        time.sleep(10)

    print(f'Pump has infused: {response}ml')
    print(f'remaining volume in pipette: {pump.volume_withdrawn}')
    
finally:
    pass
   