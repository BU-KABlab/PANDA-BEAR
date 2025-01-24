from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import axes
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.widgets import CheckButtons

# Define tool offsets
tool_offsets = {
    "center": {"x": 0.0, "y": 0.0, "z": 0.0},
    "pipette": {"x": -105, "y": 0.0, "z": 115.0},
    "electrode": {"x": 32.0, "y": 30.0, "z": 102.0},
    "decapper": {"x": -74, "y": 0.0, "z": 57.0},
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
    if line == "$H\n":
        # Homing command, go to origin
        current_position = {"x": 0, "y": 0, "z": 0}
        for name, offset in tool_offsets.items():
            trajectories[name].append(
                [
                    current_position["x"] - offset["x"],
                    current_position["y"] - offset["y"],
                    current_position["z"] - offset["z"],
                ]
            )
        continue

    if line.startswith("$"):
        continue

    if line.startswith("G"):
        parts = line.split()
        new_position = current_position.copy()
        for part in parts[1:]:
            axis = part[0].lower()
            if axis == "f":
                continue
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
ax.set_xlim(-400, 0)
ax.set_ylim(-300, 0)
ax.set_zlim(-200, 0)
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")

# Draw a flat plane at Z=-200 for all xy coordinates
X, Y = np.meshgrid(np.linspace(-400, 0, 30), np.linspace(-300, 0, 30))
Z = -200 * np.ones_like(X)
ax.plot_surface(X, Y, Z, color="grey", alpha=0.2)


# Draw multiple vials as cylinders
vial_centers = [
    {"x": -409.0, "y": -38.0, "z": -196.0},
    {"x": -4.0, "y": -40.0, "z": -196.0},
    {"x": -4.0, "y": -73.0, "z": -196.0},
    {"x": -4.0, "y": -106.0, "z": -196.0},
    {"x": -4.0, "y": -139.0, "z": -196.0},
    {"x": -4.0, "y": -172.0, "z": -196.0},
    {"x": -4.0, "y": -205.0, "z": -196.0},
    {"x": -4.0, "y": -238.0, "z": -196.0},
    {"x": -4.0, "y": -271.0, "z": -196.0},
    {"x": -93.0, "y": -40.0, "z": -196.0},
    {"x": -93.0, "y": -73.0, "z": -196.0},
    {"x": -93.0, "y": -106.0, "z": -196.0},
    {"x": -93.0, "y": -139.0, "z": -196.0},
    {"x": -93.0, "y": -172.0, "z": -196.0},
    {"x": -93.0, "y": -205.0, "z": -196.0},
    {"x": -93.0, "y": -238.0, "z": -196.0},
]

vial_radius = 14
vial_height = 66

theta = np.linspace(0, 2 * np.pi, 30)
vial_z = np.linspace(-200, -200 + vial_height, 30)
theta, vial_z = np.meshgrid(theta, vial_z)

for center in vial_centers:
    vial_x = center["x"] + vial_radius * np.cos(theta)
    vial_y = center["y"] + vial_radius * np.sin(theta)
    ax.plot_surface(vial_x, vial_y, vial_z, color="blue", alpha=0.2)

well_centers = [
    {"x": -222.0, "y": -78.0, "z": -174.0},
    {"x": -222.0, "y": -92.0, "z": -200.0},
    {"x": -222.0, "y": -106.0, "z": -200.0},
    {"x": -222.0, "y": -120.0, "z": -200.0},
    {"x": -222.0, "y": -134.0, "z": -200.0},
    {"x": -222.0, "y": -148.0, "z": -200.0},
    {"x": -222.0, "y": -162.0, "z": -200.0},
    {"x": -222.0, "y": -176.0, "z": -200.0},
    {"x": -235.5, "y": -78.0, "z": -200.0},
    {"x": -235.5, "y": -92.0, "z": -200.0},
    {"x": -235.5, "y": -106.0, "z": -200.0},
    {"x": -235.5, "y": -120.0, "z": -200.0},
    {"x": -235.5, "y": -134.0, "z": -200.0},
    {"x": -235.5, "y": -148.0, "z": -200.0},
    {"x": -235.5, "y": -162.0, "z": -200.0},
    {"x": -235.5, "y": -176.0, "z": -200.0},
    {"x": -249.0, "y": -78.0, "z": -200.0},
    {"x": -249.0, "y": -92.0, "z": -200.0},
    {"x": -249.0, "y": -106.0, "z": -200.0},
    {"x": -249.0, "y": -120.0, "z": -200.0},
    {"x": -249.0, "y": -134.0, "z": -200.0},
    {"x": -249.0, "y": -148.0, "z": -200.0},
    {"x": -249.0, "y": -162.0, "z": -200.0},
    {"x": -249.0, "y": -176.0, "z": -200.0},
    {"x": -262.5, "y": -78.0, "z": -200.0},
    {"x": -262.5, "y": -92.0, "z": -200.0},
    {"x": -262.5, "y": -106.0, "z": -200.0},
    {"x": -262.5, "y": -120.0, "z": -200.0},
    {"x": -262.5, "y": -134.0, "z": -200.0},
    {"x": -262.5, "y": -148.0, "z": -200.0},
    {"x": -262.5, "y": -162.0, "z": -200.0},
    {"x": -262.5, "y": -176.0, "z": -200.0},
    {"x": -276.0, "y": -78.0, "z": -200.0},
    {"x": -276.0, "y": -92.0, "z": -200.0},
    {"x": -276.0, "y": -106.0, "z": -200.0},
    {"x": -276.0, "y": -120.0, "z": -200.0},
    {"x": -276.0, "y": -134.0, "z": -200.0},
    {"x": -276.0, "y": -148.0, "z": -200.0},
    {"x": -276.0, "y": -162.0, "z": -200.0},
    {"x": -276.0, "y": -176.0, "z": -200.0},
]

well_radius = 5
well_height = 6

theta = np.linspace(0, 2 * np.pi, 30)
well_z = np.linspace(-200, -200 + well_height, 30)
theta, well_z = np.meshgrid(theta, well_z)

for center in well_centers:
    well_x = center["x"] + well_radius * np.cos(theta)
    well_y = center["y"] + well_radius * np.sin(theta)
    ax.plot_surface(well_x, well_y, well_z, color="red", alpha=0.2)


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
    fig,
    update,
    frames=len(tool_coords["center"][0]) + 1,
    interval=500,
    blit=False,
    repeat=False,
)


# Function to save animation as GIF
def save_animation(animation, filename):
    writer = PillowWriter(fps=2)
    animation.save(filename, writer=writer)


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


# Save the animation as a GIF
save = input("Save animation as GIF? (y/n): ")
if save.lower() == "y":
    save_animation(ani, "path_simulation.gif")
    print("Animation saved as path_simulation.gif")
else:
    pass
