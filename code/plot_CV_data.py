import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pathlib


#################
# Book keeeping #
#################
def modify_function(value):
    return value *100000/(7.25*7.25) #converts the current from amps to milliamps and changes the current column to current density



#################
# Summary Plots #
#################

#This code will generate ONE plot of ALL second cycles for all CV files in the folder
def plot_all_second_cycles(folder_path, echem_function):
    plt.figure(figsize=(8, 6))  # Create a single plot for all second cycles
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    colors = cm.cool(np.linspace(0, 1, 3))  # Adjust the number of colors if needed

    cycle_count = 0

    for file_path in folder_path.glob("*{echem_function}.txt"):
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

        df_second_cycle_copy = df_second_cycle.copy()
        df_second_cycle_copy['Im'] = df_second_cycle_copy['Im'].apply(modify_function)

        color = colors[cycle_count % len(colors)]

        plt.plot(df_second_cycle_copy['Vsig'], df_second_cycle_copy['Im'], label=f'{file_name}', color=color)
        cycle_count += 1

    plt.xlabel('V vs Ag/AgCl (V)')
    plt.ylabel('Current Density (mA/cm²)')
    plt.legend()
    plt.tight_layout()

    plt.savefig(folder_path / f"all_second_cycles_{echem_function}.png")
    print(f"All second cycles plot saved")
    plt.close()

#This code will generate ONE plot of ALL second cycles for all CV baseline files in the folder
def plot_all_second_cycles_baseline(folder_path, echem_function):
    plt.figure(figsize=(8, 6))  # Create a single plot for all second cycles
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    colors = cm.cool(np.linspace(0, 1, 3))  # Adjust the number of colors if needed

    cycle_count = 0

    for file_path in folder_path.glob("*{echem_function}_baseline.txt"):
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

        df_second_cycle_copy = df_second_cycle.copy()
        df_second_cycle_copy['Im'] = df_second_cycle_copy['Im'].apply(modify_function)

        color = colors[cycle_count % len(colors)]

        plt.plot(df_second_cycle_copy['Vsig'], df_second_cycle_copy['Im'], label=f'{file_name}', color=color)
        cycle_count += 1

    plt.xlabel('V vs Ag/AgCl (V)')
    plt.ylabel('Current Density (mA/cm²)')
    plt.legend()
    plt.tight_layout()

    plt.savefig(folder_path / f"all_second_cycles_{echem_function}.png")
    print(f"All second cycles plot saved")
    plt.close()    

#This code will generate ONE plot of ALL second cycles for all CV files listed in the experiment list**********This is the most recent code, other sections might need to be modified.
def plot_list_second_cycles(folder_path, echem_function, experiment_numbers):
    #plt.figure(figsize=(8, 8))  # Create a single plot for all second cycles
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    colors = cm.viridis(np.linspace(0,1,36))  # Adjust the number of colors if needed

    cycle_count = 0

    ratio_values =[]

    '''
    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path,file_name)
        try:
            legend_value = master_df.loc[master_df[experiment_number_column] == experiment_number, legend_value_column].values[0]
    
    '''
    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path,file_name)
        try:
            legend_value = master_df.loc[master_df[experiment_number_column] == experiment_number, legend_value_column].values[0]
            if pd.notna(legend_value) and str(legend_value).replace(".","",1).isdigit():
                ratio_values.append(legend_value)
            else:
                print(f"Non-numeric value for experiment {experiment_number}. Skipping...")
                continue
        except IndexError:
            print(f"Experiment number {experiment_number} not found in the master file.")
            continue

        if not os.path.exists(file_path):
            print(f"File not found for experiment {experiment_number}. Skipping...")
            continue
                
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])

        # Check for NaN values in the 'Cycle' column and drop them
        df = df.dropna(subset=['Cycle'])

        # Convert the 'Cycle' column to integers
        df['Cycle'] = df['Cycle'].astype(int)

        # Filter data for the second cycle
        df_second_cycle = df[df['Cycle'] == 2]

        if len(df_second_cycle) == 0:
            continue  # Skip files without a second cycle

        df_second_cycle_copy = df_second_cycle.copy()
        df_second_cycle_copy['Im'] = df_second_cycle_copy['Im'].apply(modify_function)

        color = colors[cycle_count % len(colors)]

        plt.plot(df_second_cycle_copy['Vsig'], df_second_cycle_copy['Im'], label=f"PEG:Acrylate {legend_value}", color=color)
        cycle_count += 1

    if not any(isinstance(value,(int,float)) for value in ratio_values):
            print("No numeric values found in {legend_value_column}. Skipping color bar...")
    else:
        norm = plt.Normalize(min(ratio_values), max(ratio_values))
        sm = plt.cm.ScalarMappable(cmap=cm.viridis, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=plt.gca(), label='PEG:Acrylate - #:1')

    plt.xlabel('V vs Ag (V)')
    plt.ylabel('Current Density (mA/cm²)')
    #plt.legend()
    plt.tight_layout()

    plt.savefig(folder_path / f"all_second_cycles_{echem_function}_{legend_value_column}.png")
    print(f"All second cycles plot saved")
    plt.close()

#This code will generate ONE plot of ALL second cycles for all CV baseline files listed in the experiment list
def plot_list_second_cycles_baseline(folder_path, echem_function, experiment_numbers):
    plt.figure(figsize=(8, 6))  # Create a single plot for all second cycles
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    colors = cm.cool(len(experiment_numbers))  # Adjust the number of colors if needed

    cycle_count = 0

    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}_baseline.txt"
        file_path = os.path.join(folder_path,file_name)
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])

        # Check for NaN values in the 'Cycle' column and drop them
        df = df.dropna(subset=['Cycle'])

        # Convert the 'Cycle' column to integers
        df['Cycle'] = df['Cycle'].astype(int)

        # Filter data for the second cycle
        df_second_cycle = df[df['Cycle'] == 2]

        if len(df_second_cycle) == 0:
            continue  # Skip files without a second cycle

        df_second_cycle_copy = df_second_cycle.copy()
        df_second_cycle_copy['Im'] = df_second_cycle_copy['Im'].apply(modify_function)

        color = colors[cycle_count % len(colors)]

        plt.plot(df_second_cycle_copy['Vsig'], df_second_cycle_copy['Im'], label=f'{file_name}', color=color)
        cycle_count += 1

    plt.xlabel('V vs Ag (V)')
    plt.ylabel('Current Density (mA/cm²)')
    plt.legend()
    plt.tight_layout()

    plt.savefig(folder_path / f"all_second_cycles_{echem_function}.png")
    print(f"All second cycles plot saved")
    plt.close()

def plot_list_deposition_backup(folder_path, echem_function, experiment_numbers):
    #plt.figure(figsize=(8, 8))  # Create a single plot for all second cycles
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    cmap = cm.viridis
    #colors = cm.viridis(np.linspace(0,1,10))  # Adjust the number of colors if needed
    
    exp_count = 0

    ratio_values =[]
    norm = plt.Normalize(min(ratio_values), max(ratio_values))
    '''
    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path,file_name)
        try:
            legend_value = master_df.loc[master_df[experiment_number_column] == experiment_number, legend_value_column].values[0]
    
    '''
    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path,file_name)
        try:
            legend_value = master_df.loc[master_df[experiment_number_column] == experiment_number, legend_value_column].values[0]
            if pd.notna(legend_value) and str(legend_value).replace(".","",1).isdigit():
                ratio_values.append(legend_value)
            else:
                print(f"Non-numeric value for experiment {experiment_number}. Skipping...")
                continue
        except IndexError:
            print(f"Experiment number {experiment_number} not found in the master file.")
            continue

        if not os.path.exists(file_path):
            print(f"File not found for experiment {experiment_number}. Skipping...")
            continue
                
        df = pd.read_csv(file_path, sep=" ", header=None, names=["runtime", "Vf", "Vu", "Im", "Q", "Vsig", "Ach", "IERange", "Over", "StopTest"])


        df_copy = df.copy()
        df_copy['Im'] = df_copy['Im'].apply(modify_function)
        
        color = cmap(norm(legend_value))  # Map legend value to a color
        
        plt.plot(df_copy['runtime'], df_copy['Im'], label=f"PEG:Acr {legend_value}", color=color)
        exp_count += 1

    if not any(isinstance(value,(int,float)) for value in ratio_values):
            print("No numeric values found in {legend_value_column}. Skipping color bar...")
    else:
        norm = plt.Normalize(min(ratio_values), max(ratio_values))
        sm = plt.cm.ScalarMappable(cmap=cm.viridis, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=plt.gca(), label='PEG:Acrylate - #:1')

    plt.xlabel('Time (s)')
    plt.ylabel('Current Density (mA/cm²)')
    #plt.legend()
    plt.tight_layout()

    plt.savefig(folder_path / f"ACR_rich_depositions_noleg_{echem_function}_{legend_value_column}.png")
    print(f"All depositions plot saved")
    plt.close()

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import Normalize

def plot_list_deposition(folder_path, echem_function, experiment_numbers):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    exp_count = 0
    ratio_values = []

    cmap = cm.viridis  # Define the colormap outside of the loop

    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path, file_name)
        
        try:
            legend_value = master_df.loc[master_df[experiment_number_column] == experiment_number, legend_value_column].values[0]
            if pd.notna(legend_value) and str(legend_value).replace(".", "", 1).isdigit():
                if "." in str(legend_value):
                    # Convert non-integer values to integers
                    legend_value = int(float(legend_value))
                else:
                    legend_value = int(legend_value)
                ratio_values.append(legend_value)
                print(f"Added legend value {legend_value} to ratio_values")
            else:
                print(f"Non-numeric value for experiment {experiment_number}. Skipping...")
                continue
        except IndexError:
            print(f"Experiment number {experiment_number} not found in the master file.")
            continue

        if not os.path.exists(file_path):
            print(f"File not found for experiment {experiment_number}. Skipping...")
            continue
                
        df = pd.read_csv(file_path, sep=" ", header=None, names=["runtime", "Vf", "Vu", "Im", "Q", "Vsig", "Ach", "IERange", "Over", "StopTest"])

        df_copy = df.copy()
        df_copy['Im'] = df_copy['Im'].apply(modify_function)
        
        # Create a separate norm for each experiment
        norm = Normalize(vmin=min(ratio_values), vmax=max(ratio_values))
        print(f"Created norm with min: {min(ratio_values)}, max: {max(ratio_values)}")

        # Map legend value to a color using the colormap and norm
        color = cmap(norm(legend_value))
        plt.plot(df_copy['runtime'], df_copy['Im'], label=f"{legend_value}", color=color)

    if not any(isinstance(value, (int, float)) for value in ratio_values):
        print("No numeric values found in {legend_value_column}. Skipping color bar...")
    else:
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])

        # Use the same norm for color mapping in the colorbar
        cbar = plt.colorbar(sm, ax=plt.gca(), label=f'{legend_value_column}')

    plt.xlabel('Time (s)')
    plt.ylabel('Current Density (mA/cm²)')
    plt.tight_layout()
    #plt.legend()
    plt.savefig(folder_path / f"ACR_rich_depositions_{echem_function}_{legend_value_column}.png")
    print(f"All depositions plot saved")
    plt.close()





####################
# Individual Plots #
####################

#This code will generate individual plots based on the experiment number given in the variables at the bottom
def plot_ind(folder_path, expnum, echem_funcion):
    file_path = folder_path / f"{expnum}_{echem_funcion}.txt"
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
   
    # Create a 'viridis' colormap with the number of colors equal to the number of cycles
    colors = cm.cool(np.linspace(0, 1, max_cycle))

    df['Im'] = df['Im'].apply(modify_function)

    # Plot values for vsig vs Im for each cycle with different dash patterns
    for i in range(max_cycle):
        df2 = df[df['Cycle'] == i]
        
        plt.plot(df2['Vsig'], df2['Im'], linestyle='--', color=colors[i - 1], label=f'Cycle {i}')

    plt.xlabel('V vs Ag (V)')
    plt.ylabel('Current Density (mA/cm²)')


    # Add legend to the plot
    plt.legend()      

    plt.tight_layout()
    #plt.show()
    plt.savefig(folder_path / f"{expnum}_{echem_funcion}_allcycles.png")
    print(f"{expnum}_{echem_funcion}_allcycles plot saved")
    plt.close()

#This code will generate individual plots of the second cycles for all files in the folder with the specified echem_function   
def plot_second_cycle(folder_path, echem_function):
    for file_path in folder_path.glob("*{echem_function}.txt"):
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

#This code will generate individual plots of all cycles for all CV files in the folder with the specified echem_function  
def plot_all_cycles(folder_path, echem_function):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    for file_path in folder_path.glob("*{echem_function}.txt"):
        file_name = file_path.stem
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])
        
        # Check for NaN values in the 'Cycle' column and drop them
        df = df.dropna(subset=['Cycle'])

        # Convert the 'Cycle' column to integers
        df['Cycle'] = df['Cycle'].astype(int)

        # Find the maximum cycle number
        max_cycle = df['Cycle'].max()

        # Create a colormap with the number of colors equal to the number of cycles
        colors = cm.winter_r(np.linspace(0, 1, max_cycle))
        
        df['Im'] = df['Im'].apply(modify_function)
        
        plt.figure(figsize=(8, 6))  # Create a new plot for each file
        for i in range(max_cycle):
            df2 = df[df['Cycle'] == i]
            
            plt.plot(df2['Vsig'], df2['Im'], linestyle='--', color=colors[i - 1], label=f'Cycle {i}')
        plt.xlabel('V vs Ag (V)')
        plt.ylabel('Current Density (mA/cm²)')
        plt.legend()
        plt.tight_layout()

        plt.savefig(folder_path / f"{file_name}_allcycles.png")
        print(f"Plot for {file_name} saved")
        plt.close()

#This code will generate individual plots of all cycles for CV baseline all files in the folder with the specified echem_function  
def plot_all_cycles_baseline(folder_path, echem_function):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    for file_path in folder_path.glob("*{echem_function}_baseline.txt"):
        file_name = file_path.stem
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])
        
        # Check for NaN values in the 'Cycle' column and drop them
        df = df.dropna(subset=['Cycle'])

        # Convert the 'Cycle' column to integers
        df['Cycle'] = df['Cycle'].astype(int)

        # Find the maximum cycle number
        max_cycle = df['Cycle'].max()

        # Create a colormap with the number of colors equal to the number of cycles
        colors = cm.winter_r(np.linspace(0, 1, max_cycle))
        
        df['Im'] = df['Im'].apply(modify_function)
        
        plt.figure(figsize=(8, 6))  # Create a new plot for each file
        for i in range(max_cycle):
            df2 = df[df['Cycle'] == i]
            
            plt.plot(df2['Vsig'], df2['Im'], linestyle='--', color=colors[i - 1], label=f'Cycle {i}')
        plt.xlabel('V vs Ag (V)')
        plt.ylabel('Current Density (mA/cm²)')
        plt.legend()
        plt.tight_layout()

        plt.savefig(folder_path / f"{file_name}_allcycles.png")
        print(f"Plot for {file_name} saved")
        plt.close()


#############
# Variables #
#############

####################
# Individual Plots #
####################

#expnum = 'experiment-166'


#################
# Summary Plots #
#################
experiment_numbers = [
106,107,116,117,129,130,141,142,118,119,108,109,131,132,
143,144,110,111,133,134,145,146,120,121,122,123,135,136,
147,148,112,113,149,150,124,125,114,115,137,138, 97, 98
]

'''
experiment_numbers = [
149,
150,
124,
125,
114,
115,
137,
138,
97,
98
]
'''


##########
# Shared #
##########

#date = '2023-09-09'
#folder_path = prefolder_path / f"{date}"
#folder_path = pathlib.Path(__file__).parents[2] /  "data" / "2023-09-06"
#prefolder_path = pathlib.Path("G:\\.shortcut-targets-by-id\\1-5Q8N9FCPTbzY_DvdwwKXIjGIYwbSlFQ\\data\\")

folder_path = pathlib.Path("G:\\.shortcut-targets-by-id\\1-5Q8N9FCPTbzY_DvdwwKXIjGIYwbSlFQ\\data\\panda-app-dev\\")
echem_function = "CA"
master_file_path = folder_path / f"master_file.csv"
master_df = pd.read_csv(master_file_path, sep=",", header='infer')
experiment_number_column = "ExpID"
legend_value_column = "Ratio calc PEG rich"


#############
# Functions #
#############

#plot_all_second_cycles(folder_path, echem_function)
#plot_all_second_cycles_baseline(folder_path, echem_function)
#plot_list_second_cycles(folder_path, echem_function, experiment_numbers)
#plot_list_second_cycles_baseline(folder_path, echem_function, experiment_numbers)
plot_list_deposition(folder_path, echem_function, experiment_numbers)

#plot_ind(folder_path, expnum, echem_function)
#plot_second_cycle(folder_path, echem_function)
#plot_all_cycles(folder_path, echem_function)
#plot_all_cycles_baseline(folder_path, echem_function)


