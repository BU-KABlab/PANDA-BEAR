import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt

"""
Orientation of the wellplate:
    0 - Vertical, wells become more negative from A1, column-wise
    1 - Vertical, wells become less negative from A1, column-wise
    2 - Horizontal, wells become more negative from A1, row-wise
    3 - Horizontal, wells become less negative from A1, row-wise
"""
wells = {
    "A1": {"x": 0, "y": 0},
    "A2": {"x": 9, "y": 0},
    "A3": {"x": 18, "y": 0},
    "A4": {"x": 27, "y": 0},
    "A5": {"x": 36, "y": 0},
    "B1": {"x": 0, "y": -9},
    "B2": {"x": 9, "y": -9},
    "B3": {"x": 18, "y": -9},
    "B4": {"x": 27, "y": -9},
    "B5": {"x": 36, "y": -9},
}

x_spacing = 9
y_spacing = 9
orientation = 3
a1_x = 0
a1_y = 0


def recalculate_well_positions():
    wells_new = {}
    for well_id, well in wells.items():
        row, col = well_id[0], int(well_id[1:])
        wells_new[well_id] = calculate_well_coordinates(row, col)

    return wells_new


def calculate_well_coordinates(row: str, col: int) -> dict:
    # if orientation in [0, 1]:
    #     x = (col - 1) * x_spacing
    #     y = (ord(row.upper()) - ord("A")) * y_spacing
    # elif orientation in [2, 3]:
    #     x = (ord(row.upper()) - ord("A")) * y_spacing
    #     y = (col - 1) * x_spacing
    # x, y = __calculate_rotated_position(
    #     x,
    #     y,
    #     orientation,
    #     a1_x,
    #     a1_y,
    # )
    # return {"x": x, "y": y}
    if row.upper() == "A" and col == 1:
        return {"x": a1_x, "y": a1_y}
    elif orientation == 0:
        x = a1_x - (ord(row.upper()) - ord("A")) * x_spacing
        y = a1_y - (col - 1) * y_spacing
    elif orientation == 1:
        x = a1_x + (ord(row.upper()) - ord("A")) * x_spacing
        y = a1_y + (col - 1) * y_spacing
    elif orientation == 2:
        x = a1_x + (col - 1) * y_spacing
        y = a1_y - (ord(row.upper()) - ord("A")) * x_spacing
    elif orientation == 3:
        x = a1_x - (col - 1) * y_spacing
        y = a1_y + (ord(row.upper()) - ord("A")) * x_spacing
    return {"x": x, "y": y}


def __calculate_rotated_position(
    x: float, y: float, orientation: int, a1_x: float, a1_y: float
) -> tuple:
    if orientation == 0:
        return a1_x - x, a1_y - y
    elif orientation == 1:
        return a1_x + x, a1_y + y
    elif orientation == 2:
        return a1_x + y, a1_y - x
    elif orientation == 3:
        return a1_x - y, a1_y + x
    else:
        raise ValueError("Invalid orientation value. Must be 0, 1, 2, or 3.")


# Create a figure with 5 subplots
fig = plt.figure(figsize=(15, 10))
fig.suptitle("Well Positions")
gs = gridspec.GridSpec(3, 2, width_ratios=[1, 1])

# Plot the original well positions
ax0 = plt.subplot(gs[0])
for well_id, well in wells.items():
    ax0.scatter(well["x"], well["y"])
    ax0.text(well["x"], well["y"], well_id)
ax0.set_xlim(-50, 50)
ax0.set_ylim(-50, 50)
ax0.set_title("Original Well Positions")
ax0.axhline(0, color="black", linewidth=1)
ax0.axvline(0, color="black", linewidth=1)
ax0.grid(True, which="both", linestyle="--", linewidth=1)

# Recalculate well positions
orientation = 0
wells_new_0 = recalculate_well_positions()

# Plot the new well positions
ax1 = plt.subplot(gs[2])
for well_id, well in wells_new_0.items():
    ax1.scatter(well["x"], well["y"])
    ax1.text(well["x"], well["y"], well_id)
ax1.set_xlim(-50, 50)
ax1.set_ylim(-50, 50)
ax1.set_title(f"New Well Positions with Orientation {orientation}")
ax1.axhline(0, color="black", linewidth=1)
ax1.axvline(0, color="black", linewidth=1)
ax1.grid(True, which="both", linestyle="--", linewidth=1)

# Recalculate well positions
orientation = 1
wells_new_1 = recalculate_well_positions()

# Plot the new well positions
ax2 = plt.subplot(gs[3])
for well_id, well in wells_new_1.items():
    ax2.scatter(well["x"], well["y"])
    ax2.text(well["x"], well["y"], well_id)
ax2.set_xlim(-50, 50)
ax2.set_ylim(-50, 50)
ax2.set_title(f"New Well Positions with Orientation {orientation}")
ax2.axhline(0, color="black", linewidth=1)
ax2.axvline(0, color="black", linewidth=1)
ax2.grid(True, which="both", linestyle="--", linewidth=1)

# Recalculate well positions
orientation = 2
wells_new_2 = recalculate_well_positions()

# Plot the new well positions
ax3 = plt.subplot(gs[4])
for well_id, well in wells_new_2.items():
    ax3.scatter(well["x"], well["y"])
    ax3.text(well["x"], well["y"], well_id)
ax3.set_xlim(-50, 50)
ax3.set_ylim(-50, 50)
ax3.set_title(f"New Well Positions with Orientation {orientation}")
ax3.axhline(0, color="black", linewidth=1)
ax3.axvline(0, color="black", linewidth=1)
ax3.grid(True, which="both", linestyle="--", linewidth=1)

# Recalculate well positions
orientation = 3
wells_new_3 = recalculate_well_positions()

# Plot the new well positions
ax4 = plt.subplot(gs[5])
for well_id, well in wells_new_3.items():
    ax4.scatter(well["x"], well["y"])
    ax4.text(well["x"], well["y"], well_id)
ax4.set_xlim(-50, 50)
ax4.set_ylim(-50, 50)
ax4.set_title(f"New Well Positions with Orientation {orientation}")
ax4.axhline(0, color="black", linewidth=1)
ax4.axvline(0, color="black", linewidth=1)
ax4.grid(True, which="both", linestyle="--", linewidth=1)

plt.tight_layout()
plt.show()

# Output the well, and the wells_new_0, wells_new_1, wells_new_2, and wells_new_3 dictionaries as json
import json

with open("well_positions.json", "w") as f:
    json.dump(
        {
            "original": wells,
            "orientation_0": wells_new_0,
            "orientation_1": wells_new_1,
            "orientation_2": wells_new_2,
            "orientation_3": wells_new_3,
        },
        f,
        indent=4,
    )
