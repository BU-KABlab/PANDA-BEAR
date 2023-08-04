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
import pathlib



def modify_function(value):
    return value *100000/(7.25*7.25) #converts the current from amps to milliamps and changes the current column to current density


def orignal(file_path):

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

    df['Im'] = df['Im'].apply(modify_function)

    # Plot values for vsig vs Im for each cycle with different dash patterns
    for i in range(1, max_cycle + 1):
        df2 = df[df['Cycle'] == i]
        dashes = dash_patterns[i - 1]  # Use the corresponding dash pattern from the list
        plt.plot(df2['Vsig'], df2['Im'], linestyle='--', dashes=dashes, color=colors[i - 1], label=f'Cycle {i}')

    plt.xlabel('V vs Ag/AgCl (V)')
    plt.ylabel('Current Density (mA/cm²)')

    # Uncomment the following line if you want to plot all cycles in the same color
    # plt.plot(df['Vsig'], df['Im'])

    # Add legend to the plot
    plt.legend()      

    plt.tight_layout()
    plt.savefig('2023-07-27_A3_CV.png')
    print("plot saved")

def plot(folder_path, rows, columns,echem_funcion):
    for row in rows:
        for column in columns:
            if (row == 'A' and column == 1):
                continue
            elif (row == 'C' and column == 8):
                break
            else:
                print('plotting', row, column)
                file_path = folder_path / f"{row}{column}_{echem_funcion}.txt"
                df = pd.read_csv(file_path, 
                                sep=" ", 
                                header=None, 
                                names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])
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

                df['Im'] = df['Im'].apply(modify_function)

                # Plot values for vsig vs Im for each cycle with different dash patterns
                for i in range(max_cycle):
                    df2 = df[df['Cycle'] == i]
                    dashes = dash_patterns[i - 1]  # Use the corresponding dash pattern from the list
                    plt.plot(df2['Vsig'], df2['Im'], linestyle='--', dashes=dashes, color=colors[i - 1], label=f'Cycle {i}')

                plt.xlabel('V vs Ag/AgCl (V)')
                plt.ylabel('Current Density (mA/cm²)')

                # Uncomment the following line if you want to plot all cycles in the same color
                # plt.plot(df['Vsig'], df['Im'])

                # Add legend to the plot
                plt.legend()      

                plt.tight_layout()
                #plt.show()
                plt.savefig(folder_path / f"{row}{column}_{echem_funcion}.png")
                print(f"{row}{column}_{echem_funcion} plot saved")
                plt.close()


rows = 'D'
columns = [9]
folder_path = pathlib.Path(__file__).parents[2] /  "data" / "2023-08-03"
#folder_path = pathlib.Path("C:\\Users\\Kab Lab\\Documents\\data\\2023-08-03")
plot(folder_path, rows, columns,"CV")
#plot(folder_path, rows, columns,"dep")
