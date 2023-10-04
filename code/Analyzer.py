# Analyzer
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

def plotdata(exp_name, complete_file_name, showplot=False):
    """Plot data from a Gamry experiment"""
    if exp_name == "OCP":
        df = pd.read_csv(
            complete_file_name.with_suffix(".txt"),
            sep=" ",
            header=None,
            names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"],
        )
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["figure.facecolor"] = "white"
        plt.plot(df["Time"], df["Vf"])
        plt.xlabel("Time (s)")
        plt.ylabel("Voltage (V)")
    elif exp_name == "mock_CA":
        df = pd.read_csv(
            complete_file_name.with_suffix(".txt"),
            sep=" ",
            header=None,
            names=["Time", "Vf", "Vu", "Vsig", "Ach", "Overload", "StopTest", "Temp"],
        )
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["figure.facecolor"] = "white"
        plt.plot(df["Time"], df["Vf"])
        plt.xlabel("Time (s)")
        plt.ylabel("Voltage (V)")
    elif exp_name == "CA":
        df = pd.read_csv(
            complete_file_name.with_suffix(".txt"),
            sep=" ",
            header=None,
            names=[
                "runtime",
                "Vf",
                "Vu",
                "Im",
                "Q",
                "Vsig",
                "Ach",
                "IERange",
                "Over",
                "StopTest",
            ],
        )
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["figure.facecolor"] = "white"
        plt.plot(df["runtime"], df["Im"])
        plt.xlabel("Time (s)")
        plt.ylabel("Current (A)")
    elif exp_name == "CV":
        df = pd.read_csv(
            complete_file_name.with_suffix(".txt"),
            sep=" ",
            header=None,
            names=[
                "Time",
                "Vf",
                "Vu",
                "Im",
                "Vsig",
                "Ach",
                "IERange",
                "Overload",
                "StopTest",
                "Cycle",
                "Ach2",
            ],
        )
        plt.rcParams["figure.dpi"] = 150
        plt.rcParams["figure.facecolor"] = "white"
        # Check for NaN values in the 'Cycle' column and drop them
        df = df.dropna(subset=["Cycle"])

        # Convert the 'Cycle' column to integers
        df["Cycle"] = df["Cycle"].astype(int)

        # Find the maximum cycle number
        max_cycle = df["Cycle"].max()

        # Create a list of custom dash patterns for each cycle
        dash_patterns = [
            (5 * (i + 1), 4 * (i + 1), 3 * (i + 1), 2 * (i + 1))
            for i in range(max_cycle)
        ]

        # Create a 'viridis' colormap with the number of colors equal to the number of cycles
        # unused at the moment
        colors = cm.cool(np.linspace(0, 1, max_cycle))

        # Plot values for vsig vs Im for each cycle with different dash patterns
        # for i in range(max_cycle):
        #     df2 = df[df['Cycle'] == i]
        #     dashes = dash_patterns[i - 1]  # Use the corresponding dash pattern from the list
        #     plt.plot(df2['Vsig'], df2['Im'], linestyle='--', dashes=dashes, color=colors[i - 1], label=f'Cycle {i}')

        df2 = df[df["Cycle"] == 1]
        dashes = dash_patterns[0]  # Use the corresponding dash pattern from the list
        # plt.plot(df2['Vsig'], df2['Im'], linestyle='--', dashes=dashes, color=colors[0], label=f'Cycle 1 - index 0')
        plt.plot(
            df2["Vsig"],
            df2["Im"],
            linestyle="--",
            dashes=dashes,
            color="#5b5b5b",
            label="Cycle 1 - index 0",
        )
        plt.xlabel("V vs Ag (V)")
        plt.ylabel("Current (A)")
        if showplot is True:
            plt.show()

        plt.tight_layout()
        plt.savefig(complete_file_name.with_suffix(".png"))
        plt.close()
        print("plot saved")
