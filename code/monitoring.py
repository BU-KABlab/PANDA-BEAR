'''
monitoring interface for epanda

a visual interface for monitoring the status of the robot
and experiments

things that will be shown in the interface:
- current experiment
- current state of the robot
    - current position of each instrument
    - current status and position of each well
    - current status and position of each vial
- the length of the current queue

'''
#pylint: disable=line-too-long
import json
import csv
import time
from tkinter import ttk
import tkinter as tk
import matplotlib
import pandas as pd
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from config.config import QUEUE, WELL_STATUS, WELL_TYPE, WASTE_STATUS, STOCK_STATUS
from wellplate import Wellplate, CircularWellPlate, GraceBioLabsWellPlate

# Define a class for the monitoring interface
class MonitoringInterface:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("e_panda Monitoring Interface")

        # Create a Notebook widget (tab control)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, columnspan=7, sticky='NESW')

        # Create frames for each tab
        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)

        # Add the frames to the notebook
        self.notebook.add(self.tab1, text='Status')
        self.notebook.add(self.tab2, text='Vial Levels')

        # Move the existing widgets to the first tab
        self.experiment_label = ttk.Label(self.tab1, text=f"Current Experiment: {self.current_experiment()}")
        self.experiment_label.grid(row=0, column=0)

        self.robot_state_label = ttk.Label(self.tab1, text="Current Robot State:    ")
        self.robot_state_label.grid(row=0, column=2)

        self.queue_length_label = ttk.Label(self.tab1, text=f"Current Queue Length: {self.queue_length()}")
        self.queue_length_label.grid(row=0, column=4)

        # Move the vial levels button to the second tab
        self.vial_levels_button = ttk.Button(self.tab2, text="Vial Levels", command=self.vial_levels)
        self.vial_levels_button.grid(row=0, column=0)

        # Create a Figure and a FigureCanvasTkAgg object in the first tab
        self.fig = plt.figure(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab1)
        self.canvas.get_tk_widget().grid(row=1, column=0, columnspan=7)

        # Create the animation
        self.animation = animation.FuncAnimation(self.fig,
                                                 self.deck_view,
                                                 interval=1000,
                                                 cache_frame_data=False
                                                 )

    def load_vial_data(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data

    def process_vial_data(self, vials):
        x_coordinates = []
        y_coordinates = []
        color = []
        marker = []

        for vial in vials:
            x_coordinates.append(vial["x"])
            y_coordinates.append(vial["y"])
            volume = vial["volume"]
            capacity = vial["capacity"]
            if vial['category'] == 1:
                if vial["name"] is None or vial["name"] == "":
                    color.append("black")
                    marker.append("o")
                elif volume / capacity > 0.75:
                    color.append("red")
                    marker.append("o")
                elif volume / capacity > 0.5:
                    color.append("yellow")
                    marker.append("o")
                else:
                    color.append("green")
                    marker.append("o")
            elif vial['category'] == 0:
                if vial["name"] is None or vial["name"] == "":
                    color.append("black")
                    marker.append("o")
                elif volume / capacity > 0.5:
                    color.append("green")
                    marker.append("o")
                elif volume / capacity > 0.25:
                    color.append("yellow")
                    marker.append("o")
                else:
                    color.append("red")
                    marker.append("o")

        return x_coordinates, y_coordinates, color, marker

    def deck_view(self, frame):
        """Create a deck view of the wells and vials on the robot deck."""
        # Check current wellplate type
        with open(WELL_STATUS, "r", encoding="utf-8") as well:
            data = json.load(well)
            type_number = data["type_number"]
        with open(WELL_TYPE, "r", encoding="utf-8") as well:
            data = csv.reader(well)
            for row in data:
                if str(row[0]) == str(type_number):
                    wellplate_type = str(row[4]).strip()
                    break

        # Choose the correct wellplate object based on the wellplate type
        wellplate: Wellplate = None
        if wellplate_type == "circular":
            wellplate = CircularWellPlate(
                a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13, type_number=type_number
            )
        elif wellplate_type == "square":
            wellplate = GraceBioLabsWellPlate(
                a1_x=-218, a1_y=-74, orientation=0, columns="ABCDEFGH", rows=13, type_number=type_number
            )

        # Well coordinates
        x_coordinates, y_coordinates, color = wellplate.well_coordinates_and_status_color()
        if wellplate.shape == "circular":
            well_marker = "o"
        else:
            well_marker = "s"

        # Vial coordinates
        vials = self.load_vial_data(WASTE_STATUS) + self.load_vial_data(STOCK_STATUS)
        vial_x, vial_y, vial_color, vial_marker = self.process_vial_data(vials)

        rinse_vial = {"x": -411, "y": -30}
        vial_x.append(rinse_vial["x"])
        vial_y.append(rinse_vial["y"])
        vial_color.append("black")

        # Combine the well and vial coordinates
        x_coordinates.extend(vial_x)
        y_coordinates.extend(vial_y)
        color.extend(vial_color)

        # Plot the well plate
        plt.scatter(x_coordinates, y_coordinates, marker=well_marker, c=color, s=75, alpha=0.5)
        plt.scatter(vial_x, vial_y, marker="o", c=vial_color, s=200, alpha=1)
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.title("Status of Stage Items")
        plt.grid(True, "both")
        plt.xlim(-420, 10)
        plt.ylim(-310, 10)

    def vial_levels(self):
        """Sends the vial status to the user."""
        # Get vial status
        ## Load the vial status json file
        stock_vials = pd.read_json(STOCK_STATUS)
        ## Filter for just the vial position and volume
        stock_vials = stock_vials[["position", "volume", "name"]]
        # Drop any vials that have null values
        stock_vials = stock_vials.dropna()
        ## set position to be a string and volume to be a float
        stock_vials["position"] = stock_vials["position"].astype(str)
        stock_vials["volume"] = stock_vials["volume"].astype(float)
        ## Create a bar graph with volume on the x-axis and position on the y-axis
        fig, ax = plt.subplots()
        ax.bar(stock_vials["position"], stock_vials["volume"], align="center", alpha=0.5, color="blue")
        # label each bar with the volume
        for i, v in enumerate(stock_vials["volume"]):
            ax.text(i, v, str(v/1000), color="black", ha="center")

        # Draw a horizontal line at 4000
        ax.axhline(y=4000, color="red", linestyle="-")
        # Write the name of the vial vertically in the bar
        for i, v in enumerate(stock_vials["name"]):
            ax.text(i, 10, str(v), color="black", ha="center", rotation=90)
        ax.set_xlabel("Position")
        ax.set_ylabel("Volume")
        ax.set_title("Stock Vial Status")

        # Create a FigureCanvasTkAgg instance and display the graph in the GUI
        canvas = FigureCanvasTkAgg(fig, master=self.root)
        canvas.get_tk_widget().grid(row=4, column=0, columnspan=3)

        # And the same for the waste vials
        waste_vials = pd.read_json(WASTE_STATUS)
        waste_vials = waste_vials[["position", "volume", "name"]]
        # Drop any vials that have null values
        waste_vials = waste_vials.dropna()
        waste_vials["position"] = waste_vials["position"].astype(str)
        waste_vials["volume"] = waste_vials["volume"].astype(float)
        fig, ax = plt.subplots()
        ax.bar(waste_vials["position"], waste_vials["volume"], align="center", alpha=0.5, color="blue")
        for i, v in enumerate(waste_vials["volume"]):
            ax.text(i, v, str(v), color="black", ha="center")
        ax.axhline(y=20000, color="red", linestyle="-")
        for i, v in enumerate(waste_vials["name"]):
            ax.text(i, 10, str(v), color="black", ha="center", rotation=90)
        ax.set_xlabel("Position")
        ax.set_ylabel("Volume")
        ax.set_title("Waste Vial Status")

        # Create a FigureCanvasTkAgg instance and display the graph in the GUI
        canvas = FigureCanvasTkAgg(fig, master=self.root)
        canvas.get_tk_widget().grid(row=5, column=0, columnspan=3)
    
    def queue_length(self):
        """Sends the queue length to the user."""
        # Get the queue length
        queue = pd.read_csv(QUEUE)
        queue_length = queue.shape[0]
        # # Display the queue length
        # queue_label = ttk.Label(self.root, text=f"Queue Length: {queue_length}")
        # queue_label.grid(row=6, column=0, columnspan=3)
        return queue_length
    def current_experiment(self):
        """Sends the current experiment to the user."""
        # current_experiment = pd.read_csv("experiment_queue.csv")
        # current_experiment = current_experiment.iloc[0, 0]

        # Get the current experiment from the well status file and look for a status of running
        with open(WELL_STATUS, "r", encoding="utf-8") as well:
            data = json.load(well)

        wells = data["wells"]
        current_experiment = 'None'
        for well in wells:
            if well["status"] == "running":
                current_experiment = well["experiment"]
                break

        # Display the current experiment
        # experiment_label = ttk.Label(self.root, text=f"Current Experiment: {current_experiment}")
        # experiment_label.grid(row=7, column=0, columnspan=3)
        return current_experiment
    
    def run(self):
        # Run the GUI main loop
        self.root.mainloop()

# Create an instance of the MonitoringInterface class
monitoring_interface = MonitoringInterface()

# Run the monitoring interface
monitoring_interface.run()
