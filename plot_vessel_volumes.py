"""
This script fetches the volumes for the system's vessels and plots them over a given time period.

The script is intended to be used for testing and validation purposes.

"""

from datetime import tzinfo
from panda_lib.sql_tools import db_setup, panda_models

import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import pandas as pd
import time


# Function to stop the loop
def stop(event):
    global running
    running = False


look_back = 0.01  # Number of days to look back for the data
refresh_interval = 5  # Number of seconds to wait before refreshing the plot
# Connect to the database
db = db_setup.SessionLocal()
running = True

# Create the initial plot for the vials and a plot for the pipette
fig, (stock_vial_plot, waste_vial_plot, pipette_plot) = plt.subplots(3, 1, figsize=(20, 12))

# Create the stop button
ax_stop = plt.axes([0.81, 0.01, 0.1, 0.075])
btn_stop = Button(ax_stop, "Stop")
btn_stop.on_clicked(stop)

while running:
    stock_vial_plot: plt.Axes
    waste_vial_plot: plt.Axes
    pipette_plot: plt.Axes
    pipette_plot.clear()
    stock_vial_plot.clear()
    waste_vial_plot.clear()
    # region Pipette volume
    # Fetch the volume logs for the current pipette
    pipette = db.query(panda_models.Pipette).filter_by(active=1).first()
    pipette_volume_logs = (
        db.query(panda_models.PipetteLog).filter_by(pipette_id=pipette.id).all()
    )
    pipette_volume_logs_df = pd.DataFrame(
        [
            {"volume": log.volume_ul, "timestamp": log.updated}
            for log in pipette_volume_logs
        ]
    )
    pipette_volume_logs_df["updated"] = pd.to_datetime(
        pipette_volume_logs_df["timestamp"]
    )
    pipette_volume_logs_df.set_index("updated", inplace=True)

    # Set the pipette log timezone to utc
    pipette_volume_logs_df.index = pipette_volume_logs_df.index.tz_localize(tz="utc")

    # Filter to the logs to the last 24 hours
    pipette_volume_logs_df = pipette_volume_logs_df[
        pipette_volume_logs_df.index
        > pd.Timestamp.now(tz="utc") - pd.Timedelta(days=look_back)
    ]
    # endregion
    # region Stock Vials
    # Fetch the volume logs for the current stock vials. Note this table is also the log for the waste vials
    stock_vials = db.query(panda_models.Vials).filter_by(category=0).all()
    stock_vials_df = pd.DataFrame(
        [
            {"vial_id": vial.position, "volume": vial.volume, "updated": vial.updated}
            for vial in stock_vials
        ]
    )
    stock_vials_df["updated"] = pd.to_datetime(stock_vials_df["updated"])
    stock_vials_df.set_index("updated", inplace=True)

    # Set the stock vial timezone to utc
    stock_vials_df.index = stock_vials_df.index.tz_localize(tz="utc")

    # Filter to the logs to the last 24 hours
    stock_vials_df = stock_vials_df[
        stock_vials_df.index > pd.Timestamp.now(tz="utc") - pd.Timedelta(days=look_back)
    ]

    # Separate the stock vials into the positions
    stock_vial_positions = stock_vials_df["vial_id"].unique()
    stock_vials_dict = {
        position: stock_vials_df[stock_vials_df["vial_id"] == position]
        for position in stock_vial_positions
    }

    # endregion
    # region Waste Vials
    # Fetch the volume logs for the current stock vials. Note this table is also the log for the waste vials
    waste_vials = db.query(panda_models.Vials).filter_by(category=1).all()
    waste_vials_df = pd.DataFrame(
        [
            {"vial_id": vial.position, "volume": vial.volume, "updated": vial.updated}
            for vial in waste_vials
        ]
    )
    waste_vials_df["updated"] = pd.to_datetime(waste_vials_df["updated"])
    waste_vials_df.set_index("updated", inplace=True)

    # Set the stock vial timezone to utc
    waste_vials_df.index = waste_vials_df.index.tz_localize(tz="utc")

    # Filter to the logs to the last 24 hours
    waste_vials_df = waste_vials_df[
        waste_vials_df.index > pd.Timestamp.now(tz='utc') - pd.Timedelta(days=look_back)
    ]

    # Separate the stock vials into the positions
    waste_vial_positions = waste_vials_df["vial_id"].unique()
    waste_vials_dict = {
        position: waste_vials_df[waste_vials_df["vial_id"] == position]
        for position in waste_vial_positions
    }

    # endregion
    # #region Wells

    # endregion
    # region Plotting
    # Plot the pipette data
    pipette_plot.plot(
        pipette_volume_logs_df.index,
        pipette_volume_logs_df["volume"],
    )
    pipette_plot.set_title("Pipette Volume")
    pipette_plot.set_xlabel("Time")
    pipette_plot.set_ylabel("Volume (ul)")
    pipette_plot.legend(["Pipette Volume"], loc="center left", bbox_to_anchor=(1, 0.5))

    # Plot the stock vial data
    fig.suptitle("Vessel Volumes")

    stock_vial_plot.set_title("Stock Vial Volumes")
    for position, df in stock_vials_dict.items():
        stock_vial_plot.plot(df.index, df["volume"], label=f"Stock Vial {position}",)

    stock_vial_plot.set_xlabel("Time")

    stock_vial_plot.set_ylabel("Volume (ul)")

    # Set up the legend with the vial positions
    stock_vial_plot.legend(loc="center left", bbox_to_anchor=(1, 0.5))

    # Plot the waste vial data


    for position, df in waste_vials_dict.items():
        waste_vial_plot.plot(df.index, df["volume"], label=f"Waste Vial {position}")

    waste_vial_plot.set_title("Waste Volumes")
    waste_vial_plot.set_xlabel("Time")
    waste_vial_plot.set_ylabel("Volume (ul)")

    # Set up the legend with the vial positions
    waste_vial_plot.legend(loc="center left", bbox_to_anchor=(1, 0.5))

    plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1, hspace=0.4)
    plt.draw()
    plt.pause(refresh_interval)

plt.close(fig)

# Close the database connection
db.close()
