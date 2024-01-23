import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pathlib
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
import matplotlib.colors as mcolors
from matplotlib.colors import ListedColormap
import math

#################
# Book keeeping #
#################
def modify_function(value):
    #Square wells
    #return value *100000/(7.25*7.25) #converts the current from amps to milliamps and changes the current column to current density
    #circular wells
    return value *100000/(math.pi*3.25*3.25) #converts the current from amps to milliamps and changes the current column to current density

def create_custom_colormap(num_colors, start_color, end_color, name):
    start_rgb = mcolors.hex2color(start_color)
    end_rgb = mcolors.hex2color(end_color)
    
    color_list = []
    for i in range(num_colors):
        r = start_rgb[0] + (end_rgb[0] - start_rgb[0]) * i / (num_colors - 1)
        g = start_rgb[1] + (end_rgb[1] - start_rgb[1]) * i / (num_colors - 1)
        b = start_rgb[2] + (end_rgb[2] - start_rgb[2]) * i / (num_colors - 1)
        color_list.append((r, g, b))

    custom_cmap = ListedColormap(color_list, name="purplegreen")
    return custom_cmap


###################################
# Summary Plots within ONE folder #
###################################

#This code will generate ONE plot of ALL second cycles for all CV files in the folder
def plot_all_second_cycles(folder_path, echem_function):
    plt.figure(figsize=(8, 6))  # Create a single plot for all second cycles
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    colors = cm.cool(np.linspace(0, 1, 3))  # Adjust the number of colors if needed

    cycle_count = 0

    for file_path in folder_path.glob(f"*{echem_function}*.txt"):
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

        # Assuming you have the 'modify_function' defined as in your previous code snippet
        df_second_cycle_copy = df_second_cycle.copy()
        df_second_cycle_copy['Im'] = df_second_cycle_copy['Im'].apply(modify_function)

        color = colors[cycle_count % len(colors)]

        plt.plot(df_second_cycle_copy['Vsig'], df_second_cycle_copy['Im'], label=f'{file_name}', color=color)
        cycle_count += 1

    plt.xlabel('V vs V_Ag/AgCl (V)')
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



###########################################
# Plots generated from experiment numbers #
###########################################

#This code will generate ONE plot of ALL second cycles for all CV files listed in the experiment list**********This is the most recent code, other sections might need to be modified.
def plot_list_second_cycles(folder_path, echem_function, experiment_numbers, colormap_name, start_c, end_c, campaign):
    #plt.figure(figsize=(8, 8))  # Create a single plot for all second cycles
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    cycle_count = 0
    ratio_values =[]

    custom_cmap = create_custom_colormap(len(experiment_numbers), start_c, end_c, colormap_name)       
    
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
        
        plt.plot(df_second_cycle_copy['Vsig'], df_second_cycle_copy['Im'], label={legend_value_column}, color=custom_cmap(cycle_count / len(experiment_numbers)), linewidth = '2')
        
        cycle_count += 1
    #paste comment from below when not using color bar
    if not any(isinstance(value,(int,float)) for value in ratio_values):
            print("No numeric values found in {legend_value_column}. Skipping color bar...")
    else:
        norm = plt.Normalize(min(ratio_values), max(ratio_values))
        sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=plt.gca(), label={legend_value_column})

    plt.xlabel('V vs Ag (V)')
    plt.ylabel('Current Density (mA/cm²)')
    #plt.legend()
    plt.tight_layout()
    #plt.ylim(-.05,.08)

    plt.savefig(folder_path / f"all_second_cycles_{echem_function}_{legend_value_column}_{campaign}.png")
    print(f"All second cycles plot saved")
    plt.close()

''' #delete from here to 
    plt.xlabel('Voltage (V vs Ag)')
    plt.ylabel('Current Density (mA/cm²)')
    #plt.legend()
    plt.tight_layout()
    plt.ylim(-.12,.12)
    

    plt.savefig(folder_path / f"all_second_cycles_{echem_function}_{legend_value_column}_{campaign}.png")
    print(f"All second cycles plot saved")
    plt.close()
''' #here when using the color bar

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

#Deposition plot, time vs current density
def plot_list_deposition_I(folder_path, echem_function, experiment_numbers,start_c,end_c,campaign):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    exp_count = 0
    legend_handles = []  # List to store legend handles
    legend_labels = []   # List to store legend labels
    custom_cmap = create_custom_colormap(len(experiment_numbers), start_c, end_c, colormap_name)       
    
    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path, file_name)
                
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Q", "Vsig", "Ach", "IERange", "Over", "StopTest"])
                    
        
        df_copy = df.copy()
        df_copy['Im'] = df_copy['Im'].apply(modify_function)
        
        plt.plot(df_copy['Time'], df_copy['Im'], color=custom_cmap(exp_count / len(experiment_numbers)))
        # Create a custom legend handle for this experiment
        legend_handles.append(Line2D([0], [0], color=custom_cmap(exp_count / len(experiment_numbers)), lw=2))
        legend_labels.append(f'Experiment {experiment_number}')
        exp_count += 1
    plt.xscale('log')  # Set X-axis to log scale
    plt.yscale('log')  # Set Y-axis to log scale
    plt.ylim(1e-2, plt.ylim()[1])
    plt.xlabel('Time (s)')
    plt.ylabel('Current Density (mA/cm²)')
    plt.tight_layout()
    plt.legend(legend_handles, legend_labels)
    plt.savefig(folder_path / f"{echem_function}_{campaign}.png")
    print(f"All CA plots saved")
    plt.close()

#Deposition plots for all variables related to voltage
#Vu = Uncompensated voltage
def plot_list_deposition_Vu(folder_path, echem_function, experiment_numbers):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    exp_count = 0
    colors = cm.cool(np.linspace(0,1,len(experiment_numbers)))
    legend_handles = []  # List to store legend handles
    legend_labels = []   # List to store legend labels

    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path, file_name)
                
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Q", "Vsig", "Ach", "IERange", "Over", "StopTest"])
                    
        color = colors[exp_count % len(colors)]
        plt.plot(df['Time'], df['Vu'], color=color)
        # Create a custom legend handle for this experiment
        legend_handles.append(Line2D([0], [0], color=color, lw=2))
        legend_labels.append(f'Experiment {experiment_number}')
        exp_count += 1

    plt.xlabel('Time (s)')
    plt.ylabel('Vu (V)')
    plt.tight_layout()
    plt.legend(legend_handles, legend_labels)
    plt.savefig(folder_path / f"{echem_function}_timevsVu-ALL.png")
    print(f"All CA plots saved")
    plt.close()
#Ach = voltage measured using the A/D input
def plot_list_deposition_Ach(folder_path, echem_function, experiment_numbers):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    exp_count = 0
    colors = cm.cool(np.linspace(0,1,len(experiment_numbers)))
    legend_handles = []  # List to store legend handles
    legend_labels = []   # List to store legend labels

    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path, file_name)
                
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Q", "Vsig", "Ach", "IERange", "Over", "StopTest"])
                    
        color = colors[exp_count % len(colors)]
        plt.plot(df['Time'], df['Ach'], color=color)
        # Create a custom legend handle for this experiment
        legend_handles.append(Line2D([0], [0], color=color, lw=2))
        legend_labels.append(f'Experiment {experiment_number}')
        exp_count += 1

    plt.xlabel('Time (s)')
    plt.ylabel('Ach (V)')
    plt.tight_layout()
    plt.legend(legend_handles, legend_labels)
    plt.savefig(folder_path / f"{echem_function}_timevsAch-ALL.png")
    print(f"All CA plots saved")
    plt.close()
#Vsig = voltage from the signal generator entering the current amplifier
def plot_list_deposition_Vsig(folder_path, echem_function, experiment_numbers):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    exp_count = 0
    colors = cm.cool(np.linspace(0,1,len(experiment_numbers)))
    legend_handles = []  # List to store legend handles
    legend_labels = []   # List to store legend labels

    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path, file_name)
                
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Q", "Vsig", "Ach", "IERange", "Over", "StopTest"])
                    
        color = colors[exp_count % len(colors)]
        plt.plot(df['Time'], df['Vsig'], color=color)
        # Create a custom legend handle for this experiment
        legend_handles.append(Line2D([0], [0], color=color, lw=2))
        legend_labels.append(f'Experiment {experiment_number}')
        exp_count += 1

    plt.xlabel('Time (s)')
    plt.ylabel('Vsig (V)')
    plt.tight_layout()
    plt.legend(legend_handles, legend_labels)
    plt.savefig(folder_path / f"{echem_function}_timevsVsig-ALL.png")
    print(f"All CA plots saved")
    plt.close()
#Vf = measured cell voltage
def plot_list_deposition_Vf(folder_path, echem_function, experiment_numbers):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    exp_count = 0
    colors = cm.cool(np.linspace(0,1,len(experiment_numbers)))
    legend_handles = []  # List to store legend handles
    legend_labels = []   # List to store legend labels

    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}.txt"
        file_path = os.path.join(folder_path, file_name)
                
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Q", "Vsig", "Ach", "IERange", "Over", "StopTest"])
                    
        color = colors[exp_count % len(colors)]
        plt.plot(df['Time'], df['Vf'], color=color)
        # Create a custom legend handle for this experiment
        legend_handles.append(Line2D([0], [0], color=color, lw=2))
        legend_labels.append(f'Experiment {experiment_number}')
        exp_count += 1

    plt.xlabel('Time (s)')
    plt.ylabel('Vf (V)')
    plt.tight_layout()
    plt.legend(legend_handles, legend_labels)
    plt.savefig(folder_path / f"{echem_function}_timevsVf-ALL.png")
    print(f"All CA plots saved")
    plt.close()

#OCP plot, time vs voltage
def plot_list_OCP(folder_path, echem_function, experiment_numbers):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"
    
    cycle_count = 0
    colors = cm.cool(np.linspace(0,1,len(experiment_numbers)))
    legend_handles = []  # List to store legend handles
    legend_labels = []   # List to store legend labels

    for experiment_number in experiment_numbers:
        file_name = f"experiment-{experiment_number}_{echem_function}_char.txt"
        file_path = os.path.join(folder_path, file_name)
                
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"])
                    
        color = colors[cycle_count % len(colors)]
        plt.plot(df['Time'], df['Vf'], color=color)
        # Create a custom legend handle for this experiment
        legend_handles.append(Line2D([0], [0], color=color, lw=2))
        legend_labels.append(f'Experiment {experiment_number}')
        cycle_count += 1

    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.tight_layout()
    plt.legend(legend_handles, legend_labels)
    plt.savefig(folder_path / f"{echem_function}_ALL.png")
    print(f"All OCP plots saved")
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
   
    # Create a 'cool' colormap with the number of colors equal to the number of cycles
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
def plot_all_cycles(folder_path, echem_function, colormap_name):
    plt.rcParams["figure.dpi"] = 150
    plt.rcParams["figure.facecolor"] = "white"

    for file_path in folder_path.glob(f"*{echem_function}.txt"):
        file_name = file_path.stem
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])

        # Check for NaN values in the 'Cycle' column and drop them
        df = df.dropna(subset=['Cycle'])

        # Convert the 'Cycle' column to integers
        df['Cycle'] = df['Cycle'].astype(int)

        # Find the maximum cycle number
        max_cycle = df['Cycle'].max()

        # Create a colormap with the number of colors equal to the number of cycles
        num_colors = max_cycle

        custom_cmap = create_custom_colormap(num_colors, "#9c00ff", "#3c943c", colormap_name)

        #colors = cm.winter_r(np.linspace(0, 1, max_cycle))

        df['Im'] = df['Im'].apply(modify_function)

        plt.figure(figsize=(8, 6))  # Create a new plot for each file

        for i in range(max_cycle):
            df2 = df[df['Cycle'] == i]
            plt.plot(df2['Vsig'], df2['Im'], linestyle='--', color=custom_cmap(i/num_colors), label=f'Cycle {i}')

        plt.xlabel('V vs Ag (V)')
        plt.ylabel('Current Density (mA/cm²)')
        plt.ylim(-.1,.1)
        plt.legend()
        plt.title(f'{file_name}')
        plt.tight_layout()

        # Save the plot for this file
        plt.savefig(folder_path / f"{file_name}_allcycles.png")
        print(f"Plot for {file_name} saved")

        plt.close()  # Close the current figure after saving

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


def calculate_min_max_for_cycle_1(folder_path, echem_function):
    # Create an empty DataFrame to store the minimum and maximum 'Im' values for Cycle 1
    im_summary = pd.DataFrame(columns=["File", "Min_Im_Cycle_1", "Max_Im_Cycle_1"])

    for file_path in folder_path.glob(f"*{echem_function}.txt"):
        file_name = file_path.stem
        df = pd.read_csv(file_path, sep=" ", header=None, names=["Time", "Vf", "Vu", "Im", "Vsig", "Ach", "IERange", "Overload", "StopTest", "Cycle", "Ach2"])

        
        #Current Density Calculation
        df['Im'] = df['Im'].apply(modify_function)
        
        # Filter data for Cycle 1
        cycle_1_df = df[df['Cycle'] == 1]
        
        
        # Calculate the minimum and maximum 'Im' values for Cycle 1
        min_im_cycle_1 = cycle_1_df['Im'].min()
        max_im_cycle_1 = cycle_1_df['Im'].max()

        # Add the results to the im_summary DataFrame
        im_summary = im_summary.concat({"File": file_name, "Min_Im_Cycle_1": min_im_cycle_1, "Max_Im_Cycle_1": max_im_cycle_1}, ignore_index=True)

    # Print the summary DataFrame
    print("Minimum and Maximum 'Im' values for Cycle 1 for each file:")
    print(im_summary)

    im_summary.to_csv(folder_path / f"im_summary.csv", index=False)
    return im_summary



#############
# Variables #
#############
colormap_name = 'purplegreen'
start_c = "#9c00ff"
end_c = "#3c943c"
#Dark Grey
#end_c = "#595959"
#medium Grey
#7F7F7F
#light grey
#start_c ="#BFBFBF"

# Dark Blue
#end_c = "#0E5188"
# Medium blue
#start_c = "#429FEB"

#### Medium green 
#start_c = "#429856"
#### Dark green 
#end_c = "#275B33"

####################
# Individual Plots #
####################

#expnum = 'experiment-166'


##############
# List Plots #
##############
experiment_numbers = [ 
    9994055,
    9994056,
    9994058,
    9994060,
    9994062,
    9994067,
    9994057,
    9994061,
    9994064,
    9994066,
    9994065,
    9994063,
    9994059
]
campaign = "CVscan"

####################
# Shared variables #
####################

#date = '2023-09-09'
#folder_path = prefolder_path / f"{date}"
#folder_path = pathlib.Path(__file__).parents[2] /  "data" / "2023-09-06"
prefolder_path = pathlib.Path("G:\\.shortcut-targets-by-id\\1-5Q8N9FCPTbzY_DvdwwKXIjGIYwbSlFQ\\data\\")
#folder_path = pathlib.Path("G:\\.shortcut-targets-by-id\\1-5Q8N9FCPTbzY_DvdwwKXIjGIYwbSlFQ\\data\\panda-app-dev\\Mixing\\")
folder_path = pathlib.Path("\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\data\\edot\\")
echem_function = "CV"

master_file_path = prefolder_path / f"master_file_CVscan.csv"
master_df = pd.read_csv(master_file_path, sep=",", header='infer')
experiment_number_column = "ExpID"
legend_value_column = "Order"

##############
# User Input #
##############

#echem_function = "CV"
#exp = 174
#expnum = f"experiment-{exp}"

#############
# Functions #
#############

#plot_all_second_cycles(folder_path, echem_function)
#plot_all_second_cycles_baseline(folder_path, echem_function)
#plot_list_second_cycles(folder_path, echem_function, experiment_numbers, colormap_name, start_c, end_c, campaign)
#plot_list_second_cycles_baseline(folder_path, echem_function, experiment_numbers)
#plot_list_deposition_I(folder_path, echem_function, experiment_numbers, start_c, end_c,campaign)
#plot_list_deposition_Vf(folder_path, echem_function, experiment_numbers)
#plot_list_deposition_Vu(folder_path, echem_function, experiment_numbers)
#plot_list_deposition_Vsig(folder_path, echem_function, experiment_numbers)
#plot_list_deposition_Ach(folder_path, echem_function, experiment_numbers)
#plot_list_OCP(folder_path, echem_function, experiment_numbers)

#plot_ind(folder_path, expnum, echem_function)
#plot_second_cycle(folder_path, echem_function)
plot_all_cycles(folder_path, echem_function, colormap_name)
#plot_all_cycles_baseline(folder_path, echem_function)
#calculate_min_max_for_cycle_1(folder_path, echem_function)
