"""Class of the instruments used on the CNC mill."""

import json
from typing import Dict

# NOTE these are not mill agnostic, so they should be implemented by whichever
# project is using this library.

# @dataclasses.dataclass
# class Tools(Enum):
#     """Class for naming of the mill instruments"""

#     CENTER = "center"
#     PIPETTE = "pipette"
#     ELECTRODE = "electrode"
#     LENS = "lens"


class Coordinates:
    """Class for storing coordinates."""

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z})"

    @property
    def x(self):
        """Getter for the x-coordinate."""
        return round(float(self._x), 6)

    @x.setter
    def x(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError("x-coordinate must be an int, float, or Decimal object")
        self._x = round(value, 6)

    @property
    def y(self):
        """Getter for the y-coordinate."""
        return round(float(self._y), 6)

    @y.setter
    def y(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError("y-coordinate must be an int, float, or Decimal object")
        self._y = round(value, 6)

    @property
    def z(self):
        """Getter for the z-coordinate."""
        return round(float(self._z), 6)

    @z.setter
    def z(self, value):
        if not isinstance(value, (int, float)):
            raise ValueError("z-coordinate must be an int, float, or Decimal object")
        self._z = round(value, 6)


class ToolOffset:
    def __init__(self, name: str, offset: Coordinates):
        self.name: str = name
        self.offset: Coordinates = offset

    @classmethod
    def from_dict(cls, data: dict):
        offset = Coordinates(data["x"], data["y"], data["z"])
        return cls(name=data["name"], offset=offset)

    def to_dict(self):
        return {
            "name": self.name,
            "x": self.offset.x,
            "y": self.offset.y,
            "z": self.offset.z,
        }


class ToolManager:
    def __init__(self, json_file: str = "tools.json"):
        self.json_file = json_file
        self.tool_offsets: Dict[str, ToolOffset] = self.load_tools()

        if self.tool_offsets == {}:
            self.tool_offsets = {self.__default_tool().name: self.__default_tool()}
            self.save_tools()

    def load_tools(self) -> Dict[str, ToolOffset]:
        try:
            with open(self.json_file, "r") as file:
                data = json.load(file)
                return {item["name"]: ToolOffset.from_dict(item) for item in data}
        except FileNotFoundError:
            return {}

    def save_tools(self):
        with open(self.json_file, "w") as file:
            json.dump(
                [tool.to_dict() for tool in self.tool_offsets.values()], file, indent=4
            )

    def add_tool(self, name: str, offset: Coordinates):
        self.tool_offsets[name] = ToolOffset(name=name, offset=offset)
        self.save_tools()

    def get_tool(self, name: str) -> ToolOffset:
        return self.tool_offsets.get(name)

    def get_offset(self, name: str) -> Coordinates:
        return self.tool_offsets.get(name).offset

    def update_tool(self, name: str, offset: Coordinates):
        if name in self.tool_offsets:
            self.tool_offsets[name].offset = offset
            self.save_tools()
        else:
            raise ValueError(f"Tool {name} not found")

    def delete_tool(self, name: str):
        if name in self.tool_offsets:
            del self.tool_offsets[name]
            self.save_tools()
        else:
            raise ValueError(f"Tool {name} not found")

    def __default_tool(self):
        return ToolOffset(name="center", offset=Coordinates(0, 0, 0))
