#!/usr/bin/env python3

# Standalone script: generate SQL UPDATEs for plate coordinates
# Based on A1 and E8 corner coordinates

# --- CONFIG ---
plate_id = 120
rows = "ABCDE"       # row letters
cols = 8             # number of columns
a1 = {"x": -227.6, "y": -154.4, "z": -194.3}   # A1 coords
e8 = {"x": -282.6, "y": -250.4, "z": -194.3}   # E8 coords
# ---------------

# steps per row/col
x_step = (e8["x"] - a1["x"]) / (len(rows) - 1)
y_step = (e8["y"] - a1["y"]) / (cols - 1)
z_val = a1["z"]

for ri, r in enumerate(rows):
    for c in range(1, cols + 1):
        x = a1["x"] + ri * x_step
        y = a1["y"] + (c - 1) * y_step
        coords = '{{"x": {:.1f}, "y": {:.1f}, "z": {}}}'.format(
            round(x, 1), round(y, 1), int(z_val) if float(z_val).is_integer() else z_val
        )
        print(
            f"UPDATE panda_well_hx SET coordinates = '{coords}' "
            f"WHERE plate_id = {plate_id} AND well_id = '{r}{c}';"
        )


