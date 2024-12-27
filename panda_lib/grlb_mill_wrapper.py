import time
from pathlib import Path

from grbl_cnc_mill import (
    Coordinates,
    Mill,
    MillConnectionError,
    MockMill,
    set_up_mill_logger,
)
from panda_lib.config.config_tools import read_logging_dir, read_testing_config
from panda_lib.sql_tools.db_setup import SessionLocal
from panda_lib.sql_tools.panda_models import Tool, VialStatus

# Set up the mill connection
TESTING = read_testing_config()
BaseMill = MockMill if TESTING else Mill
mill_control_logger = set_up_mill_logger(Path(read_logging_dir()))


# A wrapper for the grbl_cnc_mill library adding electrode specific functions,
class PandaMill(MockMill):
    """A wrapper for the grbl_cnc_mill library adding electrode specific functions."""

    def __init__(self):
        """Initializes the PandaMill class."""
        # Load in all of the tools from the PANDA db
        super().__init__()
        self.load_tools()
        self.logger = mill_control_logger

    def load_tools(self):
        """Loads all of the tools from the PANDA db."""
        self.tools = {}
        with SessionLocal() as db:
            tools = db.query(Tool).all()
            for tool in tools:
                # NOTE: We use the tool_manager's add_tool method to add the tools from the db without updating the db
                # for this one time operation. Otherwise you would use the add_tool method.
                self.tool_manager.add_tool(tool.name, (tool.x, tool.y, tool.z))

    def add_tool(self, tool_name: str, tool_offset: tuple[float, float, float]):
        """Adds a tool to the tool manager."""
        self.tool_manager.add_tool(tool_name, tool_offset)
        with SessionLocal() as db:
            existing_tool = db.query(Tool).filter(Tool.name == tool_name).first()
            if existing_tool:
                existing_tool.x = tool_offset[0]
                existing_tool.y = tool_offset[1]
                existing_tool.z = tool_offset[2]
            else:
                new_tool = Tool(
                    name=tool_name,
                    offset={
                        "x": tool_offset[0],
                        "y": tool_offset[1],
                        "z": tool_offset[2],
                    },
                )
                db.add(new_tool)
            db.commit()

    def update_tool(self, tool_name: str, tool_offset: tuple[float, float, float]):
        """Updates a tool in the tool manager."""
        self.tool_manager.update_tool(tool_name, tool_offset)
        with SessionLocal() as db:
            tool = db.query(Tool).filter(Tool.name == tool_name).first()
            if tool:
                tool.x = tool_offset[0]
                tool.y = tool_offset[1]
                tool.z = tool_offset[2]
                db.commit()
            else:
                raise ValueError(f"Tool {tool_name} does not exist in the PANDA db")

    def delete_tool(self, tool_name: str):
        """Deletes a tool from the tool manager."""
        self.tool_manager.delete_tool(tool_name)
        with SessionLocal() as db:
            tool = db.query(Tool).filter(Tool.name == tool_name).first()
            if tool:
                db.delete(tool)
                db.commit()
            else:
                raise ValueError(f"Tool {tool_name} does not exist in the PANDA db")

    def rinse_electrode(self, rinses: int = 3):
        """Rinse the electrode by moving it to the rinse position and back to the center position."""
        ebath_vial = None
        with SessionLocal() as db:
            ebath_vial = (
                db.query(VialStatus).filter(VialStatus.position == "e1").first()
            )
        coords: Coordinates = Coordinates(
            x=ebath_vial.x, y=ebath_vial.y, z=ebath_vial.volume_height
        )
        self.safe_move(coords.x, coords.y, ebath_vial.top, tool="electrode")
        for _ in range(rinses):
            self.move_to_position(coordinates=coords, tool="electrode")
            self.move_to_position(coords.x, coords.y, 0, tool="electrode")
        return 0

    def rest_electrode(self):
        """Rinse the electrode by moving it to the rinse position and back to the center position."""
        ebath_vial = None
        with SessionLocal() as db:
            ebath_vial = (
                db.query(VialStatus).filter(VialStatus.position == "e1").first()
            )
        coords: Coordinates = Coordinates(
            x=ebath_vial.x, y=ebath_vial.y, z=ebath_vial.volume_height
        )
        self.move_to_safe_position()
        self.safe_move(coordinates=coords, tool="electrode")
        return 0

    def disconnect(self):
        """Close the serial connection to the mill"""
        mill_control_logger.info("Disconnecting from the mill")

        if self.homed:
            mill_control_logger.debug("Mill was homed, resting electrode")
            self.rest_electrode()

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
