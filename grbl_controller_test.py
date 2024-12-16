def test_grbl_controller():
    import grbl_cnc_mill as grbl

    # Set up the mill connection
    mill = grbl.MockMill()
    mill.connect_to_mill()
    # Mill will connect to default connections and home the machine
    print(f"Connection opened: {mill.ser_mill.is_open}")

    mill.read_mill_config()
    print("Mill config:")
    for key, value in mill.config["settings"].items():
        print(f"{key}: {value}")

    mill.set_feed_rate(100)
    print(f"Feed rate: {mill.feed_rate}")

    mill.clear_buffers()

    mill.tool_manager.add_tool("test_lens", (0, 0, 0))
    mill.tool_manager.add_tool("test_test_pipette", (-85.5, 0, 0))
    mill.tool_manager.add_tool("test_electrode", (34, 35.5, 0))
    mill.tool_manager.add_tool("test_decapper", (0, 0, -55.5))
    for tool in mill.tool_manager.tool_offsets.values():
        print(tool)

    mill.tool_manager.update_tool("test_lens", (0, 0, -35.5))
    print(mill.tool_manager.get_tool("test_lens"))
    mill.tool_manager.add_tool("test_lens", (0, 0, 0))
    print(mill.tool_manager.get_tool("test_lens"))

    mill.tool_manager.delete_tool("test_lens")
    for tool in mill.tool_manager.tool_offsets.values():
        print(tool)

    print(mill.current_status())
    machine_coord, tool_coord = mill.current_coordinates()
    print(f"Machine Coord: {machine_coord} | Tool Coord: {tool_coord}")

    machine_coord, tool_coord = mill.current_coordinates("test_pipette")
    print(f"Machine Coord: {machine_coord} | test_pipette Coord: {tool_coord}")

    machine_coord, tool_coord = mill.current_coordinates("test_test_electrode")
    print(f"Machine Coord: {machine_coord} | test_electrode Coord: {tool_coord}")

    machine_coord, tool_coord = mill.current_coordinates("test_decapper")
    print(f"Machine Coord: {machine_coord} | test_decapper Coord: {tool_coord}")

    mill.safe_move(0, 0, 0, tool="test_pipette")
    machine_coord, tool_coord = mill.current_coordinates("test_pipette")
    print(f"Machine Coord: {machine_coord} | test_pipette Coord: {tool_coord}")

    mill.move_to_safe_position()

    # Delete added tools
    mill.tool_manager.delete_tool("test_pipette")
    mill.tool_manager.delete_tool("test_electrode")
    mill.tool_manager.delete_tool("test_decapper")
    mill.tool_manager.delete_tool("test_lens")
    for tool in mill.tool_manager.tool_offsets.values():
        print(tool)

    mill.disconnect()

    print(f"Connection closed: {mill.ser_mill.is_open}")


def test_panda_grbl_wrapper():
    """
    The wrapper does a few things on top of the regular driver:
    - It adds tools from the panda db on initialazation, and updates the db when a tool is added or updated
    - It has methods for electrode rinsing and resting
    - On disconnect, it moves the electrode to the rest position
    """
    from panda_lib import grlb_mill_wrapper as grbl

    # Set up the mill connection
    mill = grbl.PandaMill()

    # Check the tools in the tool manager
    print("Tools in the tool manager:")
    for tool in mill.tool_manager.tool_offsets.values():
        print(tool)

    # Add a tool
    mill.add_tool("test_lens", (0, 0, 0))
    print("\n\nTools in the tool manager:")
    for tool in mill.tool_manager.tool_offsets.values():
        print(tool)

    # Move to the center to -100, -100, 0
    mill.safe_move(-100, -100, 0, tool="test_lens")
    # Check the current coordinates of all tools
    print("\n\nCurrent coordinates of all tools:")
    for tool in mill.tool_manager.tool_offsets.keys():
        machine_coord, tool_coord = mill.current_coordinates(tool)
        print(f"Machine Coord: {machine_coord} | {tool} Coord: {tool_coord}")

    # Move to the electrode bath and rinse the electrode
    mill.rinse_electrode()
    # Check the current coordinates of the electrode
    machine_coord, tool_coord = mill.current_coordinates("electrode")
    print(f"\n\nMachine Coord: {machine_coord} | {tool} Coord: {tool_coord}")

    # Rest the electrode
    mill.rest_electrode()
    # Check the current coordinates of the electrode
    machine_coord, tool_coord = mill.current_coordinates("electrode")
    print(f"\n\nMachine Coord: {machine_coord} | {tool} Coord: {tool_coord}")

    # Delete the added tool
    mill.delete_tool("test_lens")
    print("\n\nTools in the tool manager:")
    for tool in mill.tool_manager.tool_offsets.values():
        print(tool)

    # Disconnect from the mill
    mill.disconnect()


if __name__ == "__main__":
    # test_grbl_controller()
    test_panda_grbl_wrapper()
