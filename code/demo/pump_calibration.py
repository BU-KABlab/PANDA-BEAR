import time
import nesp_lib
import winsound  # For making beeping sounds


def withdraw(volume: float, rate: float, ser_pump):
    '''Set the pump direction to withdraw the given volume at the given rate.
    
    volume <float> (ml) | rate <float> (ml/m)
    
    Return the cumulative volume withdrawn when complete.
    '''
    if ser_pump.volume_withdrawn + volume >= 0.2:
        raise Exception("The command will overfill the pipette. Not running")
    else:
        ser_pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
        # Sets the pumping volume of the pump in units of milliliters.
        ser_pump.pumping_volume = volume
        # Sets the pumping rate of the pump in units of milliliters per minute.
        ser_pump.pumping_rate = rate
        ser_pump.run()
        while ser_pump.running:
            pass
        time.sleep(2)
    return ser_pump.volume_withdrawn


def infuse(volume: float, rate: float, pump):
    '''Set the pump direction to infuse the given volume at the given rate.
    
    volume <float> (ml) | rate <float> (ml/m)
    
    Returns the cumulative volume infused when complete.
    '''
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


def set_up_pump():
    # Set up WPI syringe pump
    pump_port = nesp_lib.Port('COM5', 19200)
    pump = nesp_lib.Pump(pump_port)
    pump.syringe_diameter = 4.699  # millimeters
    pump.volume_infused_clear()
    pump.volume_withdrawn_clear()
    print(f'Pump at address: {pump.address}')
    return pump


try:
    # Define your calibration protocol as a list of volumes in microliters
    protocol_ul = [100]  # ,100,100,60,60,60,50,50,50,40,40,40]
    # Define your purge volume for before and after each infusion
    purge_vol_ul = 20

    # Set up the WPI syringe pump
    pump = set_up_pump()

    for i in protocol_ul:
        volume_ml = i / 1000
        purge_ml = purge_vol_ul / 1000
        initial_withdraw = volume_ml + 2 * purge_ml
        response = 0.00
        print('Starting...')
        time.sleep(1)

        # Withdraw the desired volume plus the purge volume
        for _ in range(1, 4):
            winsound.Beep(1000, 250)
        time.sleep(2)
        print(f'Withdrawing {volume_ml}ml with additional {purge_ml*2}ml...')
        response = withdraw(initial_withdraw, 0.4, pump)
        print(f'Pump has withdrawn: {response}ml')
        time.sleep(5)

        # First purge before main infusion
        winsound.Beep(3000, 250)
        time.sleep(2)
        print('Purging...')
        response = infuse(purge_ml, 0.2, pump)
        winsound.Beep(1000, 250)
        print(f'Pump has infused: {response}ml')
        time.sleep(5)

        # Main infusion
        for _ in range(1, 4):
            winsound.Beep(3000, 500)

        print(f'Main infusion of {volume_ml}ml...')
        time.sleep(2)
        response = infuse(volume_ml, 0.2, pump)
        winsound.Beep(1000, 250)
        print(f'Pump has infused: {response} ml')
        time.sleep(5)

        # After infusion purge
        winsound.Beep(3000, 250)
        time.sleep(2)
        print('Purging...')
        response = infuse(purge_ml, 0.2, pump)
        for i in range(1, 4):
            winsound.Beep(1000 + i * 1000, 250)
        print(f'remaining volume in pipette: {pump.volume_withdrawn}')
        time.sleep(5)

finally:
    pass
