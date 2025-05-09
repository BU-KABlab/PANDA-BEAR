# Copyright (c) 2023 Machine Agency
# Adapted from Science Jubilee
#
# Portions of this code are licensed under the MIT License.
# See the LICENSE file in the root directory for the full license text.


import json
import logging
import os

from panda_lib.hardware.arduino_interface import ArduinoLink

logger = logging.getLogger(__name__)


class ToolStateError(Exception):
    """Exception raised when the tool is in an invalid state."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message
        logger.error(message)


def tip_check(func):
    """Decorator to check if the pipette has a tip attached before performing an action."""

    def wrapper(self, *args, **kwargs):
        if not self.has_tip:
            raise ToolStateError(
                "Error: No tip is attached. Cannot complete this action"
            )
        else:
            func(self, *args, **kwargs)

    return wrapper


class Pipette:
    """A class representation of an Opentrons OT2 pipette."""

    def __init__(
        self,
        index,
        name,
        brand,
        model,
        max_volume,
        min_volume,
        zero_position,
        blowout_position,
        drop_tip_position,
        mm_to_ul,
        stepper: ArduinoLink,
    ):
        """Initialize the pipette object


        :param name: The name associated with the tool (e.g. 'p300_single')
        :type name: str
        :param brand: The brand of the pipette
        :type brand: str
        :param model: The model of the pipette
        :type model: str
        :param max_volume: The maximum volume of the pipette in uL
        :type max_volume: float
        :param min_volume: The minimum volume of the pipette in uL
        :type min_volume: float
        :param zero_position: The position of the plunger before using a :method:`aspirate` step
        :type zero_position: float
        :param blowout_position: The position of the plunger for running a :method:`blowout` step
        :type blowout_position: float
        :param drop_tip_position: The position of the plunger for running a :method:`drop_tip` step
        :type drop_tip_position: float
        :param mm_to_ul: The conversion factor for converting motor microsteps in mm to uL
        :type mm_to_ul: float
        """
        self.name = name
        self.brand = brand
        self.model = model
        self.max_volume = max_volume
        self.min_volume = min_volume
        self.zero_position = zero_position
        self.blowout_position = blowout_position
        self.drop_tip_position = drop_tip_position
        self.mm_to_ul = mm_to_ul
        self.has_tip = False
        self.is_primed = False
        self.position = 0.0
        self.stepper: ArduinoLink = stepper

    @classmethod
    def from_config(
        cls,
        index,
        name,
        config_file: str = "src\panda_lib\hardware\panda_pipettes\ot2_pipette\definitions\single_channel\P300.json",
        path: str = os.path.join(os.path.dirname(__file__), "configs"),
    ):
        """Initialize the pipette object from a config file

        :param index: The tool index of the pipette on the machine
        :type index: int
        :param name: The tool name
        :type name: str
        :param config_file: The name of the config file containign the pipette parameters
        :type config_file: str
        :param path: The path to the pipette configuration `.json` files for the tool,
                defaults to the 'config/' in the science_jubilee/tools/configs directory.
        :returns: A :class:`Pipette` object
        :rtype: :class:`Pipette`
        """
        if config_file[-4:] != "json":
            config_file = config_file + ".json"
        config = os.path.join(path, config_file)
        with open(config) as f:
            kwargs = json.load(f)

        return cls(index, name, **kwargs)

    def post_load(self):
        """Prime the Pipette after loading it onto the Machine sot hat it is ready to use"""
        self.prime()

    def vol2move(self, vol):
        """Converts desired volume in uL to a movement of the pipette motor axis

        :param vol: The desired amount of liquid expressed in uL
        :type vol: float
        :return: The corresponding motor movement in mm
        :rtype: float
        """
        dv = vol * self.mm_to_ul

        return dv

    def prime(self, s=2500):
        """Moves the plunger to the low-point on the pipette motor axis to prepare for further commands
        Note::This position should not engage the pipette tip plunger

        :param s: The speed of the plunger movement in mm/min
        :type s: int
        """
        self.stepper.move_to(v=self.zero_position, s=s, wait=True)
        self.is_primed = True

    @tip_check
    def aspirate(self, vol: float, s: int = 2000):
        """Moves the plunger upwards to aspirate liquid into the pipette tip

        :param vol: The volume of liquid to aspirate in uL
        :type vol: float
        :param s: The speed of the plunger movement in mm/min
        :type s: int
        """
        if self.is_primed:
            pass
        else:
            self.prime()

        distance = self.vol2move(vol) * -1
        self.get_status()
        end_pos = self.position + distance

        self.stepper.move_to(end_pos,s, True)

    @tip_check
    def dispense(self, vol: float, s: int = 2000):
        """Moves the plunger downwards to dispense liquid out of the pipette tip

        :param vol: The volume of liquid to dispense in uL
        :type vol: float
        :param s: The speed of the plunger movement in mm/min
        :type s: int

        Note:: Ideally the user does not call this functions directly, but instead uses the :method:`dispense` method
        """
        dv = self.vol2move(vol)
        self.get_status()
        end_pos = self.position + dv

        # TODO: Figure out why checks break for transfer, work fine for manually aspirating and dispensing
        # if end_pos > self.zero_position:
        #    raise ToolStateError("Error: Pipette does not have anything to dispense")
        # elif dv > self.zero_position:
        #    raise ToolStateError ("Error : The volume to be dispensed is greater than what was aspirated")
        self.stepper.move_to(end_pos,s, True)

    @tip_check
    def blowout(self, s: int = 6000):
        """Blows out any remaining liquid in the pipette tip

        :param s: The speed of the plunger movement in mm/min, defaults to 3000
        :type s: int, optional
        """
        self.prime()

    @tip_check
    def air_gap(self, vol):
        """Moves the plunger upwards to aspirate air into the pipette tip

        :param vol: The volume of air to aspirate in uL
        :type vol: float
        """
        # TODO: Add a check to ensure compounded volume does not exceed max volume of pipette

        dv = self.vol2move(vol) * -1
        self.stepper.move(v=-1 * dv)

    @tip_check
    def mix(self, vol: float, n: int, s: int = 5500):  # FIXME
        """Mixes liquid by alternating aspirate and dispense steps for the specified number of times

        :param vol: The volume of liquid to mix in uL
        :type vol: float
        :param n: The number of times to mix
        :type n: int
        :param s: The speed of the plunger movement in mm/min, defaults to 5000
        :type s: int, optional
        """
        v = self.vol2move(vol) * -1

        self.stepper.pipette_move_to(z=self.current_well.top_ + 1)
        self.prime()

        # TODO: figure out a better way to indicate mixing height position that is not hardcoded
        self.stepper.pipette_move_to(z=self.current_well.bottom_ + 1)
        for i in range(0, n):
            self._aspirate(vol, s=s)
            self.prime(s=s)

    @tip_check
    def _drop_tip(self):
        """Moves the plunger to eject the pipette tip

        :raises ToolConfigurationError: If the pipette does not have a tip attached
        """
        self.stepper.pipette_move_to(v=self.drop_tip_position, s=5000)

    def prime(self):
        """Moves the plunger to the low-point on the pipette motor axis to prepare for further commands
        Note::This position should not engage the pipette tip plunger

        :param s: The speed of the plunger movement in mm/min
        :type s: int
        """
        self.stepper.pipette_move_to(v=self.zero_position, s=5000, wait=True)
        self.is_primed = True

    def get_status(self):
        """Returns the current status of the pipette

        :return: The current status of the pipette
        :rtype: dict
        """
        status= self.stepper.get_status()
        self.position = status["p"]
        self.max_volume = status["mxv"]
