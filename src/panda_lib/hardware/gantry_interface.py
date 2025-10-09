import json
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from panda_lib.labware.vials import read_vial
from panda_lib.sql_tools import VialStatus
from panda_shared.config.config_tools import (
    read_config_value,
    read_logging_dir,
    read_testing_config,
    reload_config,
    write_config_value,
)
from panda_shared.db_setup import SessionLocal

from .grbl_cnc_mill import (
    Coordinates,
    Mill,
    MillConnectionError,
    MockMill,
    set_up_mill_logger,
)

# Set up the mill connection
TESTING = read_testing_config()
BaseMill = MockMill if TESTING else Mill
mill_control_logger = set_up_mill_logger(Path(read_logging_dir()))


@dataclass
class Tool:
    """A class representing a tool."""

    name: str
    x: float
    y: float
    z: float


# A wrapper for the grbl_cnc_mill library adding electrode specific functions,
class PandaMill(Mill):
    """A wrapper for the grbl_cnc_mill library adding electrode specific functions."""

    def __init__(self):
        """Initializes the PandaMill class."""
        # Load in all of the tools from the PANDA db
        super().__init__()
        self.load_tools()
        self.logger = mill_control_logger

    def load_tools(self):
        """Loads all of the tools from the local config file."""
        self.tools = {}
        reload_config()
        tools = list(json.loads(read_config_value("TOOLS", "offsets")))
        if not tools:
            mill_control_logger.warning("No tools found in the config file.")
            return

        for tool in tools:
            # NOTE: We use the tool_manager's add_tool method to add the tools from the db without updating the db
            # for this one time operation. Otherwise you would use the add_tool method.
            self.tool_manager.add_tool(tool["name"], (tool["x"], tool["y"], tool["z"]))

    def add_tool(self, tool_name: str, tool_offset: tuple[float, float, float]):
        """Adds a tool to the tool manager."""
        self.tool_manager.add_tool(tool_name, tool_offset)

    def update_tool(self, tool_name: str, tool_offset: tuple[float, float, float]):
        """Updates a tool in the tool manager and config file."""
        self.tool_manager.update_tool(tool_name, tool_offset)

        # Update the config file's tool offsets
        tools = list(json.loads(read_config_value("TOOLS", "offsets")))
        for tool in tools:
            if tool["name"] == tool_name:
                tool["x"] = tool_offset[0]
                tool["y"] = tool_offset[1]
                tool["z"] = tool_offset[2]
                break
        else:
            tools.append(
                {
                    "name": tool_name,
                    "x": tool_offset[0],
                    "y": tool_offset[1],
                    "z": tool_offset[2],
                }
            )
        # Write the updated tools back to the config file
        write_config_value("TOOLS", "offsets", json.dumps(tools))

    def delete_tool(self, tool_name: str):
        """Deletes a tool from the tool manager."""
        self.tool_manager.delete_tool(tool_name)

        # Delete from the config file
        tools = list(json.loads(read_config_value("TOOLS", "offsets")))
        for tool in tools:
            if tool["name"] == tool_name:
                tools.remove(tool)
                break
        else:
            mill_control_logger.warning(f"Tool {tool_name} not found in config file.")
            return
        # Write the updated tools back to the config file
        write_config_value("TOOLS", "offsets", json.dumps(tools))
        mill_control_logger.info(f"Tool {tool_name} deleted from config file.")
        mill_control_logger.info(f"Tool {tool_name} deleted from tool manager.")
        return

    def rinse_electrode(self, rinses: int = 3):
        """Rinse the electrode by moving it to the rinse position and back to the center position."""
        ebath_vial = None
        with SessionLocal() as db:
            ebath_vial = db.scalars(
                select(VialStatus).filter(VialStatus.position == "e1")
            ).first()
        coords: Coordinates = Coordinates(
            x=ebath_vial.x, y=ebath_vial.y, z=ebath_vial.volume_height
        )
        # self.safe_move(coords.x, coords.y, ebath_vial.top, tool="electrode")
        cc = self.current_coordinates()
        coordinate_list = [
            Coordinates(cc.x, cc.y, 0),
            Coordinates(coords.x, coords.y, ebath_vial.volume_height),
            Coordinates(coords.x, coords.y, 0),
            Coordinates(coords.x, coords.y, ebath_vial.volume_height),
            Coordinates(coords.x, coords.y, 0),
            Coordinates(coords.x, coords.y, ebath_vial.volume_height),
            Coordinates(coords.x, coords.y, 0),
        ]
        self.move_to_positions(coordinate_list, tool="electrode")
        # for _ in range(rinses):
        #     self.move_to_position(coordinates=coords, tool="electrode")
        #     self.move_to_position(coords.x, coords.y, 0, tool="electrode")
        return 0

    def rest_electrode(self):
        """Rinse the electrode by moving it to the rinse position and back to the center position."""
        ebath_vial = None
        with SessionLocal() as db:
            ebath_vial = db.scalars(
                select(VialStatus).filter(VialStatus.position == "e1")
            ).first()
        coords: Coordinates = Coordinates(
            x=ebath_vial.x, y=ebath_vial.y, z=ebath_vial.volume_height
        )

        self.safe_move(coordinates=coords, tool="electrode")
        return 0
    
    def disconnect(self):
        """Close the serial connection to the mill safely."""
        mill_control_logger.info("Disconnecting from the mill")

        if self.ser_mill is None:
            mill_control_logger.warning("Serial connection to mill is already None.")
            return

        try:
            self.ser_mill.close()
            time.sleep(2)
            if self.ser_mill.is_open:
                mill_control_logger.error("Failed to close the serial connection to the mill")
                raise MillConnectionError("Error closing serial connection to mill")
            else:
                mill_control_logger.info("Serial connection to mill closed successfully")
        except Exception as e:
            mill_control_logger.error(f"Exception while closing serial connection: {e}")
        finally:
            self.active_connection = False
            self.ser_mill = None


class MockPandaMill(MockMill):
    """Mock Version of the Panda Mill, used to simulate a mill connection for testing purposes."""

    def __init__(self):
        """Initializes the PandaMill class."""
        # Load in all of the tools from the PANDA db
        super().__init__()
        self.load_tools()
        self.logger = mill_control_logger

    def load_tools(self):
        """Loads all of the tools from the local config file."""
        self.tools = {}
        reload_config()
        tools = list(json.loads(read_config_value("TOOLS", "offsets")))
        if not tools:
            mill_control_logger.warning("No tools found in the config file.")
            return

        for tool in tools:
            # NOTE: We use the tool_manager's add_tool method to add the tools from the db without updating the db
            # for this one time operation. Otherwise you would use the add_tool method.
            self.tool_manager.add_tool(tool["name"], (tool["x"], tool["y"], tool["z"]))

    def add_tool(self, tool_name: str, tool_offset: tuple[float, float, float]):
        """Adds a tool to the tool manager."""
        self.tool_manager.add_tool(tool_name, tool_offset)

    def update_tool(self, tool_name: str, tool_offset: tuple[float, float, float]):
        """Updates a tool in the tool manager and config file."""
        self.tool_manager.update_tool(tool_name, tool_offset)

        # Update the config file's tool offsets
        tools = list(json.loads(read_config_value("TOOLS", "offsets")))
        for tool in tools:
            if tool["name"] == tool_name:
                tool["x"] = tool_offset[0]
                tool["y"] = tool_offset[1]
                tool["z"] = tool_offset[2]
                break
        else:
            tools.append(
                {
                    "name": tool_name,
                    "x": tool_offset[0],
                    "y": tool_offset[1],
                    "z": tool_offset[2],
                }
            )
        # Write the updated tools back to the config file
        write_config_value("TOOLS", "offsets", json.dumps(tools))

    def delete_tool(self, tool_name: str):
        """Deletes a tool from the tool manager."""
        self.tool_manager.delete_tool(tool_name)

        # Delete from the config file
        tools = list(json.loads(read_config_value("TOOLS", "offsets")))
        for tool in tools:
            if tool["name"] == tool_name:
                tools.remove(tool)
                break
        else:
            mill_control_logger.warning(f"Tool {tool_name} not found in config file.")
            return
        # Write the updated tools back to the config file
        write_config_value("TOOLS", "offsets", json.dumps(tools))
        mill_control_logger.info(f"Tool {tool_name} deleted from config file.")
        mill_control_logger.info(f"Tool {tool_name} deleted from tool manager.")
        return

    def rinse_electrode(self, rinses: int = 3):
        """Rinse the electrode by moving it to the rinse position and back to the center position."""
        ebath_vial = None
        ebath_vial = read_vial(position="e1")
        coords: Coordinates = Coordinates(
            x=ebath_vial.x, y=ebath_vial.y, z=ebath_vial.vial_data.volume_height
        )
        self.safe_move(coords.x, coords.y, ebath_vial.top, tool="electrode")
        for _ in range(rinses):
            self.move_to_position(coordinates=coords, tool="electrode")
            self.move_to_position(coords.x, coords.y, 0, tool="electrode")
        return 0

    def rest_electrode(self):
        """Rinse the electrode by moving it to the rinse position and back to the center position."""
        ebath_vial = None
        ebath_vial = read_vial(position="e1")
        coords: Coordinates = Coordinates(
            x=ebath_vial.x, y=ebath_vial.y, z=ebath_vial.vial_data.volume_height
        )
        self.move_to_safe_position()
        self.safe_move(coordinates=coords, tool="electrode")
        return 0

    def disconnect(self):
        """Close the serial connection to the mill"""
        mill_control_logger.info("Disconnecting from the mill")

        # if self.homed:
        #     mill_control_logger.debug("Mill was homed, resting electrode")
        #     self.rest_electrode()

        self.ser_mill.close()
        time.sleep(2)
        mill_control_logger.info("Mill connected: %s", self.ser_mill.is_open)
        if self.ser_mill.is_open:
            mill_control_logger.error(
                "Failed to close the serial connection to the mill"
            )
            raise MillConnectionError("Error closing serial connection to mill")
        else:
            mill_control_logger.info("Serial connection to mill closed successfully")
            self.active_connection = False
            self.ser_mill = None
        return
