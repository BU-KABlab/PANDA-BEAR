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

mill.tool_manager.add_tool("lens", (0, 0, 0))
mill.tool_manager.add_tool("pipette", (-85.5, 0, 0))
mill.tool_manager.add_tool("electrode", (34, 35.5, 0))
mill.tool_manager.add_tool("decapper", (0, 0, -55.5))
for tool in mill.tool_manager.tool_offsets.values():
    print(tool)

mill.tool_manager.update_tool("lens", (0, 0, -35.5))
print(mill.tool_manager.get_tool("lens"))
mill.tool_manager.add_tool("lens", (0, 0, 0))
print(mill.tool_manager.get_tool("lens"))


mill.tool_manager.delete_tool("lens")
for tool in mill.tool_manager.tool_offsets.values():
    print(tool)

print(mill.current_status())
machine_coord, tool_coord = mill.current_coordinates()
print(f"Machine Coord: {machine_coord} | Tool Coord: {tool_coord}")

machine_coord, tool_coord = mill.current_coordinates("pipette")
print(f"Machine Coord: {machine_coord} | pipette Coord: {tool_coord}")

machine_coord, tool_coord = mill.current_coordinates("electrode")
print(f"Machine Coord: {machine_coord} | electrode Coord: {tool_coord}")

machine_coord, tool_coord = mill.current_coordinates("decapper")
print(f"Machine Coord: {machine_coord} | decapper Coord: {tool_coord}")

mill.safe_move(0, 0, 0, tool="pipette")
machine_coord, tool_coord = mill.current_coordinates("pipette")
print(f"Machine Coord: {machine_coord} | pipette Coord: {tool_coord}")

mill.move_to_safe_position()

# Run through all of the functions in the Mill class


print(f"Connection closed: {mill.ser_mill.is_open}")
