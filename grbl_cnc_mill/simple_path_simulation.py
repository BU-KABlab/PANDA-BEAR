from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import CheckButtons

# Define tool offsets
tool_offsets = {
    "center": {"x": 0.0, "y": 0.0, "z": 0.0},
    "pipette": {"x": -107.5, "y": 0.0, "z": 85.0},
    "electrode": {"x": 32.0, "y": 30.0, "z": 80.0},
    "decapper": {"x": -75.5, "y": 0.0, "z": 56.0},
}
# Load G-code file
command_log_path = Path("./grbl_cnc_mill/logs/command.log")
gcode = open(command_log_path, "r")

# Parse G-code file
gcode = gcode.readlines()
# Initialize position and trajectory
current_position = [0, 0, 0]
trajectories = {name: [] for name in tool_offsets}

# Process G-code
for line in gcode:
    if line.startswith("G01"):
        parts = line.split()
        for part in parts[1:]:
            axis = part[0]
            value = float(part[1:])
            if axis == "X":
                current_position[0] = value
            elif axis == "Y":
                current_position[1] = value
            elif axis == "Z":
                current_position[2] = value
        for name, offset in tool_offsets.items():
            trajectories[name].append(
                [
                    current_position[0] - offset["x"],
                    current_position[1] - offset["y"],
                    current_position[2] - offset["z"],
                ]
            )

# Extract coordinates for each tool point
tool_coords = {name: list(zip(*positions)) for name, positions in trajectories.items()}

# Setup figure and 3D axis
fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")
ax.set_xlim(-400, 100)
ax.set_ylim(-200, 200)
ax.set_zlim(-100, 100)
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")

# Plot initialization
lines = {}
highlights = {}
for name, coords in tool_coords.items():
    (line,) = ax.plot([], [], [], label=name, alpha=0.6)  # Set alpha for transparency
    (highlight,) = ax.plot([], [], [], marker="o", label=f"{name}_current", alpha=1.0)
    lines[name] = line
    highlights[name] = highlight


# Animation function
def update(num):
    for name, coords in tool_coords.items():
        lines[name].set_data(coords[0][:num], coords[1][:num])
        lines[name].set_3d_properties(coords[2][:num])
        highlights[name].set_data([coords[0][num - 1]], [coords[1][num - 1]])
        highlights[name].set_3d_properties([coords[2][num - 1]])
    return [*lines.values(), *highlights.values()]


# Animate
ani = FuncAnimation(
    fig, update, frames=len(tool_coords["center"][0]), interval=500, blit=False
)

# Checkboxes for toggling visibility
rax = plt.axes([0.02, 0.4, 0.15, 0.2])  # Adjust as needed
labels = list(tool_offsets.keys())
visibility = {label: True for label in labels}
check = CheckButtons(rax, labels, [True] * len(labels))


def toggle_visibility(label):
    visibility[label] = not visibility[label]
    lines[label].set_visible(visibility[label])
    highlights[label].set_visible(visibility[label])
    plt.draw()


check.on_clicked(toggle_visibility)

plt.legend()
plt.show()
