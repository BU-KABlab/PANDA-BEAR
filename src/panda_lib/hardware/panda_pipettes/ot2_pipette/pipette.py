# Copyright (c) 2023 Machine Agency
# Adapted from Science Jubilee
#
# Portions of this code are licensed under the MIT License.
# See the LICENSE file in the root directory for the full license text.


import json
import logging
import os

from ...arduino_interface import ArduinoLink

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
            return func(self, *args, **kwargs)

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
        self.has_tip = True

        # Initialize the pipette
        self._initialize()

    def _initialize(self):
        """Initialize the pipette by checking status and homing if needed"""
        try:
            response = self.get_status()
            # If we get a valid response, check if the pipette is already homed
            if not response.get("homed", False):
                logger.info("Pipette not homed, homing now...")
                self.home()
        except Exception as e:
            logger.warning("Error initializing pipette: %s. Will try to home.", str(e))
            self.home()

    @classmethod
    def from_config(
        cls,
        index,
        name,
        config_file: str = "src/panda_lib/hardware/panda_pipettes/ot2_pipette/definitions/single_channel/P300.json",
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
        """Prime the Pipette after loading it onto the Machine so that it is ready to use"""
        self.prime()
        logger.info("Pipette %s loaded and primed", self.name)

    def vol2move(self, vol):
        """Converts desired volume in uL to a movement of the pipette motor axis

        :param vol: The desired amount of liquid expressed in uL
        :type vol: float
        :return: The corresponding motor movement in mm
        :rtype: float
        """
        if vol < self.min_volume or vol > self.max_volume:
            logger.warning(
                "Volume %s uL is outside pipette range (%s-%s uL)",
                vol,
                self.min_volume,
                self.max_volume,
            )
            vol = max(min(vol, self.max_volume), self.min_volume)

        return vol * self.mm_to_ul

    def home(self):
        """Home the pipette to establish the zero position

        :return: True if homing was successful
        :rtype: bool
        """
        response = self.stepper.pipette_send("9")  # CMD_PIPETTE_HOME

        if not response.get("success", False):
            error_msg = response.get("message", "Unknown error")
            logger.error("Failed to home pipette: %s", error_msg)
            return False

        logger.info("Pipette successfully homed")
        self.is_primed = False
        return True

    def prime(self, s=2500):
        """Moves the plunger to the low-point on the pipette motor axis to prepare for further commands
        Note::This position should not engage the pipette tip plunger

        :param s: The speed of the plunger movement in mm/min
        :type s: int
        """
        response = self.stepper.pipette_send(f"10{self.zero_position},{s}")

        if response.get("success", False):
            self.is_primed = True
            self.position = self.zero_position
            logger.info("Pipette primed at position %s mm", self.position)
        else:
            error_msg = response.get("message", "Unknown error")
            logger.error("Failed to prime pipette: %s", error_msg)

        return response.get("success", False)

    @tip_check
    def aspirate(self, vol: float, s: int = 2000):
        """Moves the plunger upwards to aspirate liquid into the pipette tip

        :param vol: The volume of liquid to aspirate in uL
        :type vol: float
        :param s: The speed of the plunger movement in mm/min
        :type s: int
        """
        if not self.is_primed:
            self.prime()

        # Send the command
        response = self.stepper.pipette_send(f"11{vol},{s}")

        if response.get("success", False):
            # Update position after successful aspiration
            if "value2" in response:
                self.position = response["value2"]
            logger.info("Aspirated %s uL, new position: %s mm", vol, self.position)
        else:
            error_msg = response.get("message", "Unknown error")
            logger.error("Failed to aspirate %s uL: %s", vol, error_msg)

        return response.get("success", False)

    @tip_check
    def dispense(self, vol: float, s: int = 2000):
        """Moves the plunger downwards to dispense liquid out of the pipette tip

        :param vol: The volume of liquid to dispense in uL
        :type vol: float
        :param s: The speed of the plunger movement in mm/min
        :type s: int
        """
        # Send the command
        response = self.stepper.pipette_send(f"12{vol},{s}")

        if response.get("success", False):
            # Update position after successful dispensing
            if "value2" in response:
                self.position = response["value2"]
            logger.info("Dispensed %s uL, new position: %s mm", vol, self.position)
        else:
            error_msg = response.get("message", "Unknown error")
            logger.error("Failed to dispense %s uL: %s", vol, error_msg)

        return response.get("success", False)

    @tip_check
    def blowout(self, s: int = 6000):
        """Blows out any remaining liquid in the pipette tip

        :param s: The speed of the plunger movement in mm/min, defaults to 6000
        :type s: int, optional
        """
        # Blowout is essentially just moving to the blowout position
        response = self.stepper.pipette_send(f"10{self.blowout_position},{s}")

        if response.get("success", False):
            self.position = self.blowout_position
            logger.info("Performed blowout, position: %s mm", self.position)
        else:
            error_msg = response.get("message", "Unknown error")
            logger.error("Failed to perform blowout: %s", error_msg)

        return response.get("success", False)

    @tip_check
    def air_gap(self, vol, s: int = 2000):
        """Moves the plunger upwards to aspirate air into the pipette tip

        :param vol: The volume of air to aspirate in uL
        :type vol: float
        :param s: The speed of the plunger movement in mm/min
        :type s: int, optional
        """
        # Air gap is functionally the same as aspirate, but we might want to differentiate
        # in logs or behavior later
        logger.info("Creating air gap of %s uL", vol)
        return self.aspirate(vol, s)

    @tip_check
    def mix(self, vol: float, n: int, s: int = 5500):
        """Mixes liquid by alternating aspirate and dispense steps for the specified number of times

        :param vol: The volume of liquid to mix in uL
        :type vol: float
        :param n: The number of times to mix
        :type n: int
        :param s: The speed of the plunger movement in mm/min, defaults to 5500
        :type s: int, optional
        """
        # Use the built-in mix command if available
        response = self.stepper.pipette_send(f"15{vol},{n},{s}")

        if response.get("success", False):
            logger.info("Mixed %s uL %s times at speed %s", vol, n, s)
        else:
            # Fall back to manual mixing if the command failed
            logger.warning("Mix command failed, falling back to manual mixing")
            for _ in range(n):
                self.aspirate(vol, s)
                self.dispense(vol, s)

        return response.get("success", False)

    @tip_check
    def drop_tip(self, s: int = 5000):
        """Moves the plunger to eject the pipette tip

        :param s: The speed of the plunger movement in mm/min, defaults to 5000
        :type s: int, optional
        """
        # Move to the drop tip position
        response = self.stepper.pipette_send(f"10{self.drop_tip_position},{s}")

        if response.get("success", False):
            self.has_tip = False
            self.position = self.drop_tip_position
            logger.info("Tip dropped")
        else:
            error_msg = response.get("message", "Unknown error")
            logger.error("Failed to drop tip: %s", error_msg)

        return response.get("success", False)

    def get_status(self):
        """Returns the current status of the pipette

        :return: The current status of the pipette
        :rtype: dict
        """
        response = self.stepper.pipette_send("13")  # CMD_PIPETTE_STATUS

        if response.get("success", False):
            # Extract key status information
            if "value1" in response and "value2" in response and "value3" in response:
                status = {
                    "homed": bool(response["value1"]),
                    "position": response["value2"],
                    "max_volume": response["value3"],
                }

                # Update the object's state
                self.position = status["position"]
                self.max_volume = status["max_volume"]

                logger.debug("Pipette status: %s", status)
                return status
            else:
                # Legacy format support
                return response
        else:
            error_msg = response.get("message", "Unknown error")
            logger.error("Failed to get pipette status: %s", error_msg)
            return {"success": False, "message": error_msg}
