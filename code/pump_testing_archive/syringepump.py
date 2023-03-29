import nesp_lib
from nesp_lib import Port, Pump, PumpingDirection

# Constructs the port to which the pump is connected.
port = Port('/dev/ttyUSB0',19200)
# Constructs the pump connected to the port.
pump = Pump(port)

# Prints the model number of the pump (e.g. "1000" for NE-1000).
print(pump.model_number)
# Prints the firmware version of the pump (e.g. "(3, 928)" for 3.928).
print(pump.firmware_version)

# Sets the syringe diameter of the pump in units of millimeters.
pump.syringe_diameter = 4.572
# Sets the pumping direction of the pump.
pump.pumping_direction = PumpingDirection.INFUSE
# Sets the pumping volume of the pump in units of milliliters.
pump.pumping_volume = 1.0
# Sets the pumping rate of the pump in units of milliliters per minute.
pump.pumping_rate = 20.0

