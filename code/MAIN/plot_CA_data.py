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
    return value *-100000/(7.25*7.25) #converts the current from amps to milliamps and changes the current column to current density

def plotCA(folder_path, rows, columns, echem_function):
    for row in rows:
        for column in columns:
            if (row == 'A' and column == 1):
                continue
            elif (row == 'H' and column == 12):
                break
            else:
                print('plotting', row, column)
                file_path = folder_path / f"{row}{column}_{echem_function}.txt"
                df = pd.read_csv(file_path, 
                                sep=" ", 
                                header=None, 
                                names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])
                plt.rcParams["figure.dpi"] = 150
                plt.rcParams["figure.facecolor"] = "white"
                df['Im'] = df['Im'].apply(modify_function)
                f=plt.figure()
                f.set_figwidth(4)
                f.set_figheight(4)
                plt.plot(df['Time'], df['Im'])
                plt.xlabel('Time (s)')
                plt.ylabel('Reduction Current Density (mA/cm²)')
          
                plt.tight_layout()
                #plt.show()
                plt.savefig(folder_path / f"{row}{column}_{echem_function}_4.png")
                print(f"{row}{column}_{echem_function}_4 plot saved")
                plt.close()

def plot_all_filesCA(folder_path, echem_function):
    plt.figure(figsize=(8, 6))  # Create a single plot for all files
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    #colors = cm.cool(np.linspace(0, 1, 10))  # Adjust the number of colors if needed

    for i, file_path in enumerate(folder_path.glob("*.txt")):
        file_name = file_path.stem
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])

        # Check for NaN values in the 'Cycle' column and drop them

        df['Im'] = df['Im'].apply(modify_function)

        plt.xlabel('V vs Ag/AgCl (V)')
        plt.ylabel('Reduction Current Density (mA/cm²)')
        #plt.legend()
        plt.tight_layout()
        plt.xlabel('Time (s)')
        plt.ylabel('Reduction Current Density (mA/cm²)')

        # Uncomment the following line if you want to plot all cycles in the same color
        plt.plot(df['Time'], df['Im'])
        plt.savefig(folder_path / f"all_files_{echem_function}.png")
        print(f"All files plot saved")
    #plt.close()

#rows = 'A'
#columns = [4]
folder_path = pathlib.Path(__file__).parents[2] /  "data" / "Wet_Dress_Rehersal"
#folder_path = pathlib.Path("C:\\Users\\Kab Lab\\Documents\\data\\2023-07-31")
echem_function = "dep"
#plotCA(folder_path, rows, columns, echem_function)
#plot_all_filesCA(folder_path, echem_function)
