import json
from unittest.mock import MagicMock

import pytest

from panda_lib.hardware.grbl_cnc_mill.tools import (
    Coordinates,
    ToolManager,
    ToolOffset,
)
from panda_lib.utilities import Instruments


@pytest.fixture
def mock_instruments():
    return Instruments(pump=MagicMock(), sensor=MagicMock(), controller=MagicMock())


@pytest.fixture
def test_json_file(tmp_path):
    test_file = tmp_path / "test_tools.json"
    test_data = [
        {"name": "test_tool", "x": 1.0, "y": 2.0, "z": 3.0},
        {"name": "another_tool", "x": 4.0, "y": 5.0, "z": 6.0},
    ]
    with open(test_file, "w") as f:
        json.dump(test_data, f)
    return test_file


@pytest.fixture
def test_empty_json_file(tmp_path):
    test_file = tmp_path / "test_tools.json"
    test_data = []
    with open(test_file, "w") as f:
        json.dump(test_data, f)
    return test_file


def test_tooloffset_initialization():
    offset = Coordinates(1.0, 2.0, 3.0)
    tool_offset = ToolOffset(name="test_tool", offset=offset)
    assert tool_offset.name == "test_tool"
    assert tool_offset.offset.x == 1.0
    assert tool_offset.offset.y == 2.0
    assert tool_offset.offset.z == 3.0


def test_tooloffset_from_dict():
    data = {"name": "test_tool", "x": 1.0, "y": 2.0, "z": 3.0}
    tool_offset = ToolOffset.from_dict(data)
    assert tool_offset.name == "test_tool"
    assert tool_offset.offset.x == 1.0
    assert tool_offset.offset.y == 2.0
    assert tool_offset.offset.z == 3.0


def test_tooloffset_to_dict():
    offset = Coordinates(1.0, 2.0, 3.0)
    tool_offset = ToolOffset(name="test_tool", offset=offset)
    data = tool_offset.to_dict()
    assert data["name"] == "test_tool"
    assert data["x"] == 1.0
    assert data["y"] == 2.0
    assert data["z"] == 3.0


def test_tooloffset_str():
    offset = Coordinates(1.0, 2.0, 3.0)
    tool_offset = ToolOffset(name="test_tool", offset=offset)
    assert str(tool_offset) == "test_tool: (1.0, 2.0, 3.0)"


def test_tool_manager_initialization(test_json_file):
    """Test the initialization of the ToolManager class, which includes
    loading tools from a JSON file."""
    tool_manager = ToolManager(json_file=test_json_file)
    tool = tool_manager.tool_offsets["test_tool"]
    assert tool.name == "test_tool"
    assert tool.offset.x == 1.0
    assert tool.offset.y == 2.0
    assert tool.offset.z == 3.0


def test_save_tools(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    tool_manager.save_tools()
    with open(test_json_file, "r") as f:
        data = json.load(f)
    assert data[0]["name"] == "test_tool"
    assert data[0]["x"] == 1.0
    assert data[0]["y"] == 2.0
    assert data[0]["z"] == 3.0


def test_get_tool(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    tool = tool_manager.get_tool("test_tool")
    assert tool.name == "test_tool"
    assert tool.offset.x == 1.0
    assert tool.offset.y == 2.0
    assert tool.offset.z == 3.0


def test_get_tool_invalid_tool(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    with pytest.raises(ValueError):
        tool_manager.get_tool(10)


def test_add_tool_str(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    new_tool_name, new_tool_offset = "new_tool", Coordinates(10.0, 20.0, 30.0)
    tool_manager.add_tool(new_tool_name, new_tool_offset)

    assert "new_tool" in tool_manager.tool_offsets
    assert tool_manager.tool_offsets["new_tool"].offset.x == 10.0
    assert tool_manager.tool_offsets["new_tool"].offset.y == 20.0
    assert tool_manager.tool_offsets["new_tool"].offset.z == 30.0


def test_add_tool_ToolOffset(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    new_tool = ToolOffset("new_tool", Coordinates(10.0, 20.0, 30.0))
    tool_manager.add_tool(new_tool.name, new_tool.offset)

    assert "new_tool" in tool_manager.tool_offsets
    assert tool_manager.tool_offsets["new_tool"].offset.x == 10.0
    assert tool_manager.tool_offsets["new_tool"].offset.y == 20.0
    assert tool_manager.tool_offsets["new_tool"].offset.z == 30.0


def test_add_tool_invalid_tool(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    with pytest.raises(ValueError):
        tool_manager.add_tool(10, (10.0, 20.0, 30.0))


def test_get_offset(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    offset = tool_manager.get_offset("test_tool")
    assert offset.x == 1.0
    assert offset.y == 2.0
    assert offset.z == 3.0


def test_update_tool(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    new_offset = Coordinates(10.0, 20.0, 30.0)
    tool_manager.update_tool("test_tool", new_offset)
    assert tool_manager.tool_offsets["test_tool"].offset.x == 10.0
    assert tool_manager.tool_offsets["test_tool"].offset.y == 20.0
    assert tool_manager.tool_offsets["test_tool"].offset.z == 30.0

    with open(test_json_file, "r") as f:
        data = json.load(f)
    assert data[0]["x"] == 10.0
    assert data[0]["y"] == 20.0
    assert data[0]["z"] == 30.0


def test_update_tool_not_found(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    with pytest.raises(ValueError):
        tool_manager.update_tool("not_a_tool", Coordinates(10.0, 20.0, 30.0))


def test_update_tool_invalid_tool(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    with pytest.raises(ValueError):
        tool_manager.update_tool(10, Coordinates(10.0, 20.0, 30.0))


def test_delete_tool(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    tool_manager.delete_tool("test_tool")
    assert "test_tool" not in tool_manager.tool_offsets

    with open(test_json_file, "r") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["name"] == "another_tool"


def test_delete_tool_not_found(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    with pytest.raises(ValueError):
        tool_manager.delete_tool("not_a_tool")


def test_delete_tool_invalid_tool(test_json_file):
    tool_manager = ToolManager(json_file=test_json_file)
    with pytest.raises(ValueError):
        tool_manager.delete_tool(10)


def test_delete_tool_empty_file(tmp_path):
    test_file = tmp_path / "test_tools.json"
    with open(test_file, "w") as f:
        f.write("[]")
    tool_manager = ToolManager(json_file=test_file)
    with pytest.raises(ValueError):
        tool_manager.delete_tool("test_tool")


def test_defualt_tool_offset(test_empty_json_file):
    tool_offset = ToolManager(test_empty_json_file)
    assert "center" in tool_offset.tool_offsets
    tool = tool_offset.tool_offsets["center"]
    assert tool.name == "center"
    assert tool.offset.x == 0.0
    assert tool.offset.y == 0.0
    assert tool.offset.z == 0.0


if __name__ == "__main__":
    pytest.main()
