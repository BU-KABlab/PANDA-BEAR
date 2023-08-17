import logging, time, nesp_lib

class Pump:

    def __init__(self):
        self.pump = self.set_up_pump()
    
    def set_up_pump(self):
        pump_port = nesp_lib.Port("COM5", 19200)
        pump = nesp_lib.Pump(pump_port)
        pump.syringe_diameter = 4.699  # millimeters
        pump.volume_infused_clear()
        pump.volume_withdrawn_clear()
        logging.info(f"Pump found at address: {pump.address}")
        time.sleep(2)
        return pump

    def withdraw(self, volume: float, rate: float):
        """
        Withdraw the given volume at the given rate and depth from the specified position.
        Args:
            volume (float): Volume to be withdrawn in milliliters but given as microliters.
            position (dict): Dictionary containing x, y, and z coordinates of the position.
            depth (float): Depth to plunge from the specified position in millimeters.
            rate (float): Pumping rate in milliliters per minute.
        """
        # Perform the withdrawl

        ## convert the volume argument from ul to ml
        volume = volume / 1000

        if (
            self.pump.volume_withdrawn + volume > 0.2
        ):  # 0.2 is the maximum volume for the pipette tip
            raise Exception(
                f"The command to withdraw {volume} ml will overfill the 0.2 ml pipette with {self.pump.volume_withdrawn} ml inside. Stopping run"
            )
        else:
            self.pump.pumping_direction = nesp_lib.PumpingDirection.WITHDRAW
            self.pump.pumping_volume = (
                volume  # Sets the pumping volume of the pump in units of milliliters.
            )
            self.pump.pumping_rate = rate  # in units of milliliters per minute.
            self.pump.run()
            logging.debug("Withdrawing...")
            time.sleep(0.5)
            while self.pump.running:
                pass
            logging.debug("Done withdrawing")
            time.sleep(2)

            logging.debug(f"Pump has withdrawn: {self.pump.volume_withdrawn} ml")

        return 0

    def infuse(self, volume: float, rate: float):
        """
        Infuse the given volume at the given rate and depth from the specified position.
        Args:
            volume (float): Volume to be infused in milliliters but given as microliters.
            position (dict): Dictionary containing x, y, and z coordinates of the position.
            depth (float): Depth to lower from the specified position in millimeters.
            rate (float): Pumping rate in milliliters per minute.
        """
        # then lower to the pipetting depth
        # mill.move_pipette_to_position(position["x"], position["y"], depth)
        # Perform infusion

        ## convert the volume argument from ul to ml
        volume = volume / 1000

        if volume > 0.0:
            self.pump.pumping_direction = nesp_lib.PumpingDirection.INFUSE
            self.pump.pumping_volume = (
                volume  # Sets the pumping volume of the pump in units of milliliters.
            )
            self.pump.pumping_rate = rate  # Sets the pumping rate of the pump in units of milliliters per minute.
            self.pump.run()
            logging.debug("Infusing...")
            time.sleep(0.5)
            while self.pump.running:
                pass
            #logging.debug("Done infusing")
            time.sleep(2)
            logging.debug(f"Pump has infused: {self.pump.volume_infused} ml")
        else:
            pass
        return 0
