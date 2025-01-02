from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import axes
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
with open(command_log_path, "r") as gcode_file:
    gcode = gcode_file.readlines()

# Initialize position and trajectory
current_position = {"x": 0, "y": 0, "z": 0}
trajectories = {name: [] for name in tool_offsets}

# Process G-code
for line in gcode:
    if line.startswith("G01"):
        parts = line.split()
        new_position = current_position.copy()
        for part in parts[1:]:
            axis = part[0].lower()
            value = float(part[1:])
            new_position[axis] = value

        if new_position != current_position:
            distances = {
                axis: new_position[axis] - current_position[axis] for axis in "xyz"
            }
            current_position = {axis: new_position[axis] for axis in "xyz"}
            for name, offset in tool_offsets.items():
                trajectories[name].append(
                    [
                        current_position["x"] - offset["x"],
                        current_position["y"] - offset["y"],
                        current_position["z"] - offset["z"],
                    ]
                )

# Extract coordinates for each tool point
tool_coords = {name: list(zip(*positions)) for name, positions in trajectories.items()}

# Setup figure and 3D axis
fig = plt.figure()
ax: axes = fig.add_subplot(111, projection="3d")
ax.set_xlim(-400, 30)
ax.set_ylim(-200, 30)
ax.set_zlim(-90, 30)
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")

# Add a grey plane at z = -85
plane_z = -85
x = [-400, 30, 30, -400]
y = [-200, -200, 30, 30]
z = [plane_z] * 4
ax.add_collection3d(plt.fill_between(x, y, plane_z, color="grey", alpha=0.5))

# Plot initialization
lines = {}
highlights = {}
for name, coords in tool_coords.items():
    (line,) = ax.plot([], [], [], label=name, alpha=0.6)  # Set alpha for transparency
    (highlight,) = ax.plot([], [], [], marker="o", label=f"{name} current", alpha=1.0)
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
# Play/Pause button
play_pause_ax = plt.axes([0.02, 0.3, 0.1, 0.04])  # Adjust as needed
play_pause_button = plt.Button(play_pause_ax, "Pause")
is_paused = False


def toggle_animation():
    global is_paused
    if is_paused:
        ani.event_source.start()
        play_pause_button.label.set_text("Pause")
    else:
        ani.event_source.stop()
        play_pause_button.label.set_text("Play")
    is_paused = not is_paused


play_pause_button.on_clicked(lambda event: toggle_animation())


def toggle_visibility(label):
    visibility[label] = not visibility[label]
    lines[label].set_visible(visibility[label])
    highlights[label].set_visible(visibility[label])
    plt.draw()


check.on_clicked(toggle_visibility)

plt.legend(loc="upper right")
plt.show()
