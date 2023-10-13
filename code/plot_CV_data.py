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
                
def plot_second_cycle(folder_path, echem_function):
    for file_path in folder_path.glob("*.txt"):
        file_name = file_path.stem
        print('Plotting second cycle for:', file_name)
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["figure.facecolor"] = "white"
        f=plt.figure()      
        f.set_figwidth(4)
        f.set_figheight(4)
        # Check for NaN values in the 'Cycle' column and drop them
        df = df.dropna(subset=['Cycle'])

        # Convert the 'Cycle' column to integers
        df['Cycle'] = df['Cycle'].astype(int)

        # Filter data for the second cycle
        df_second_cycle = df[df['Cycle'] == 2]

        if len(df_second_cycle) == 0:
            continue  # Skip files without a second cycle

        df_second_cycle['Im'] = df_second_cycle['Im'].apply(modify_function)

        plt.plot(df_second_cycle['Vsig'], df_second_cycle['Im'], label=f'Second Cycle')

        plt.xlabel('V vs Ag/AgCl (V)')
        plt.ylabel('Current Density (mA/cm²)')
        #plt.legend()

        plt.tight_layout()

        plt.savefig(folder_path / f"{file_name}_{echem_function}_second_cycle.png")
        print(f"{file_name}_{echem_function}_second_cycle plot saved")
        plt.close()

def plot_all_second_cycles(folder_path, echem_function):
    plt.figure(figsize=(8, 6))  # Create a single plot for all second cycles
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    colors = cm.cool(np.linspace(0, 1, 10))  # Adjust the number of colors if needed

    cycle_count = 0

    for file_path in folder_path.glob("*.txt"):
        file_name = file_path.stem
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])

        # Check for NaN values in the 'Cycle' column and drop them
        df = df.dropna(subset=['Cycle'])

        # Convert the 'Cycle' column to integers
        df['Cycle'] = df['Cycle'].astype(int)

        # Filter data for the second cycle
        df_second_cycle = df[df['Cycle'] == 2]

        if len(df_second_cycle) == 0:
            continue  # Skip files without a second cycle

        df_second_cycle['Im'] = df_second_cycle['Im'].apply(modify_function)

        color = colors[cycle_count % len(colors)]

        plt.plot(df_second_cycle['Vsig'], df_second_cycle['Im'], label=f'{file_name}', color=color)
        cycle_count += 1

    plt.xlabel('V vs Ag/AgCl (V)')
    plt.ylabel('Current Density (mA/cm²)')
    #plt.legend()
    plt.tight_layout()

    plt.savefig(folder_path / f"all_second_cycles_{echem_function}.png")
    print(f"All second cycles plot saved")
    plt.close()

rows = 'D'
columns = [9]
#folder_path = pathlib.Path(__file__).parents[2] /  "data"
folder_path = pathlib.Path("C:\\Users\\Kab Lab\\Documents\\GitHub\\PANDA\\data")
echem_function = "CV"
#plot(folder_path, rows, columns, echem_function)
plot_second_cycle(folder_path, echem_function)
#plot_all_second_cycles(folder_path, echem_function)
