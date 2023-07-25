import datetime
from http import HTTPStatus
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import time
import gc
import comtypes
import comtypes.client as client
import pathlib
import random

file_path ="https://raw.githubusercontent.com/erasmus95/PANDA-BEAR/main/data/2023-07-21/A1_CV.txt?token=GHSAT0AAAAAACEGYHBHT3LT2FXKAJRCTSQWZF75L7A"
df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])
plt.rcParams["figure.dpi"] = 150
plt.rcParams["figure.facecolor"] = "white"

# Check for NaN values in the 'Cycle' column and drop them
df = df.dropna(subset=['Cycle'])

# Convert the 'Cycle' column to integers
df['Cycle'] = df['Cycle'].astype(int)

# Find the maximum cycle number
max_cycle = df['Cycle'].max()

# Create a list of custom dash patterns for each cycle
dash_patterns = [
    (5 * (i + 1), 4 * (i + 1), 3 * (i + 1), 2 * (i + 1))
    for i in range(max_cycle)
]

# Create a 'viridis' colormap with the number of colors equal to the number of cycles
colors = cm.cool(np.linspace(0, 1, max_cycle))

# Plot values for vsig vs Im for each cycle with different dash patterns
for i in range(1, max_cycle + 1):
    df2 = df[df['Cycle'] == i]
    dashes = dash_patterns[i - 1]  # Use the corresponding dash pattern from the list
    plt.plot(df2['Vsig'], df2['Im'], linestyle='--', dashes=dashes, color=colors[i - 1], label=f'Cycle {i}')

plt.xlabel('V vs Ag/AgCl (V)')
plt.ylabel('Current (A)')

# Uncomment the following line if you want to plot all cycles in the same color
# plt.plot(df['Vsig'], df['Im'])

# Add legend to the plot
plt.legend()      

plt.tight_layout()
plt.savefig('Test2.png')
print("plot saved")