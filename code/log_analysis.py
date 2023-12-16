import pandas as pd
from pathlib import Path
from config.config import EPANDA_LOG, WELL_HX
from matplotlib import pyplot as plt


def plate_analysis():
    '''
    This function analyzes the data from the well history and the logs to 
    determine the accuracy of the pump
    '''
    # ## ANALYSIS
    project_ids = ["8"]
    campaign_ids = [
        "8.1",
        "8.2",
        "8.3",
        "8.4",
        "8.5",
        "8.6",
        "8.7",
        "8.8",
        "8.9",
        "8.10",
        "8.11",
    ]
    # Load well history
    # plate id, type number, well id, experiment id, project id, status, status date, contents
    well_hx = pd.read_csv(WELL_HX, skipinitialspace=True)
    # well_hx = pd.read_csv(PATH_TO_NETWORK_DATA + "/well_history.csv", skipinitialspace=True)
    # Filter well history to those ids in the ids list
    well_hx = well_hx[well_hx["project id"].astype(str).isin(project_ids)]
    if len(well_hx) == 0:
        print("No experiments found for project ids: " + str(project_ids))
        exit()
    # Filter well history to only those experiments that were completed
    well_hx = well_hx[well_hx["status"] == "complete"]

    # Set data types for well history
    well_hx["experiment id"] = well_hx["experiment id"].astype(int)
    well_hx["project id"] = well_hx["project id"].astype(str)
    well_hx["plate id"] = well_hx["plate id"].astype(int)
    well_hx["type number"] = well_hx["type number"].astype(int)
    well_hx["well id"] = well_hx["well id"].astype(str)
    well_hx["status"] = well_hx["status"].astype(str)
    well_hx["status date"] = well_hx["status date"].astype(str)
    well_hx["contents"] = well_hx["contents"].astype(str)

    # Get the logs and filter to only those experiments in our filtered well history dataframe
    # The logs have a formatted output of 
    # "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(custom1)s&%(custom2)s&%(custom3)s&%(message)s"
    logs = pd.read_csv(
        EPANDA_LOG,
        skipinitialspace=True,
        sep="&",
        header=None,
        names=[
            "date",
            "name",
            "level",
            "module",
            "function",
            "line",
            "custom1",
            "custom2",
            "custom3",
            "message",
        ],
    )

    # filter on module = e_panda
    logs = logs[logs["module"] == "pump_control"]

    # set custom1 to str, custom2 to int, and custom3 to str
    logs["custom1"] = logs["custom1"].astype(str)
    logs["custom2"] = logs["custom2"].astype(int)
    logs["custom3"] = logs["custom3"].astype(str)
    # rename custom1 to campaign id, custom2 to experiment ID, custom3 to well
    logs = logs.rename(
        columns={
            "custom1": "campaign id",
            "custom2": "experiment id",
            "custom3": "well",
        }
    )
    # filter on experiment ids in the well history dataframe
    logs = logs[logs["experiment id"].isin(well_hx["experiment id"])]

    # filter on campaign ids in the campaign ids list
    logs = logs[logs["campaign id"].isin(campaign_ids)]

    if logs.empty:
        print("No experiments found for project ids: " + str(project_ids))
        exit()

    # filter on message containing 'Data'
    logs = logs[logs["message"].str.contains("Data")]

    # split message into 6 columns called 'message', 'action', 'volume', 'density', 'preweight', 'postweight'
    logs[["message", "action", "volume", "density", "preweight", "postweight"]] = logs[
        "message"
    ].str.split(",", expand=True)

    # add a column called 'weight change' that is postweight - preweight
    logs["weight change"] = logs["postweight"].astype(float) - logs["preweight"].astype(
        float
    )

    # add a column that is percent error betwen the actual weight change and the expected weight change based on the volume * density
    logs["percent error"] = (
        logs["weight change"]
        - (logs["volume"].astype(float) * logs["density"].astype(float))
    ) / (logs["volume"].astype(float) * logs["density"].astype(float))

    # scatter Plot the percent error for each experiment, grouped by experiment id
    logs.plot.scatter(x="experiment id", y="percent error", c="DarkBlue")
    plt.xlabel("Experiment #")
    # set the x axis to be the experiment ids in order and replace with 1 - n, sorting so that the x axis is in order
    plt.xticks(
        logs["experiment id"].sort_values().unique(),
        range(1, len(logs["experiment id"].sort_values().unique()) + 1),
    )
    # rotate the x axis labels by 75 degrees
    plt.xticks(rotation=85)
    plt.ylabel("Percent Error")
    plt.title("Percent Error by Experiment #")
    plt.show()

    # Histogram of the actual volume dispensed vs the expected volume dispensed (.100 mL)
    logs["weight change"].astype(float).hist()

    plt.xlabel("Volume Dispensed (mL)")
    plt.ylabel("Frequency")
    plt.title("Volume Dispensed Histogram")
    plt.show()


def direct_log_analysis():
    # ## ANALYSIS
    campaign_ids = [
        "8.1",
        "8.2",
        "8.3",
        "8.4",
        "8.5",
        "8.6",
        "8.7",
        "8.8",
        "8.9",
        "8.10",
        "8.11",
        "8.12",
        "8.13",
        "8.14",
        "8.15",
        "8.16",
        "8.17",
        "8.18",
        "8.19",
        "8.20",
        "8.21",
        "8.22",
        "8.23",
        "8.24",
        "8.25",
        "8.26",
        "8.27",
        "8.28",
        "8.29",
        "8.30",
        "8.31",
        "8.32",
        "8.33",
        "8.34",
        "8.35",
        "8.36",
        "8.37",
        "8.38",
        "8.39",
        "8.40",
        "8.41",
        "8.42",
        "8.43",
        "8.44",
        "8.45",
        "8.46",
        "8.47",
        "8.48",
        "8.49",
        "8.50",
        "8.51",
        "8.52",
        "8.53",
        "8.54",
        "8.55",
        "8.56",
        "8.57",
        "8.58",
        "8.59",
        "8.60",
        "8.61",
        "8.62",
        "8.63",
        "8.64",
        "8.65",
        "8.66",
        "8.67",
        "8.68",
        "8.69",
        "8.70",
        "8.71",
        "8.72",
        "8.73",
        "8.74",
        "8.75",
        "8.76",
        "8.77",
        "8.78",
        "8.79",
        "8.80",
        "8.81",
        "8.82",
        "8.83",
        "8.84",
        "8.85",
        "8.86",
        "8.87",
        "8.88",
        "8.89",
        "8.90",
        "8.91",
        "8.92",
        "8.93",
        "8.94",
        "8.95",
        "8.96",
        "8.97",
        "8.98",
        "8.99",
        "8.100",
        "8.101",
        "8.102",
        "8.103",
        "8.104",
        "8.105",
        "8.106",
        "8.107",
        "8.108",
        "8.109",
        "8.110",
        "8.111",
        "8.112",
        "8.113",
        "8.114",
        "8",
    ]

    # Get the logs and filter to only those that match the campaign ids
    # The logs have a formatted output of "%(asctime)s&%(name)s&%(levelname)s&%(module)s&%(funcName)s&%(lineno)d&%(custom1)s&%(custom2)s&%(custom3)s&%(message)s"
    logs = pd.read_csv(
        EPANDA_LOG,
        skipinitialspace=True,
        sep="&",
        header=None,
        names=[
            "date",
            "name",
            "level",
            "module",
            "function",
            "line",
            "custom1",
            "custom2",
            "custom3",
            "message",
        ],
    )

    # filter on module = e_panda
    logs = logs[logs["module"] == "pump_control"]

    # set custom1 to str, custom2 to int, and custom3 to str
    logs["custom1"] = logs["custom1"].astype(str)
    # logs['custom2'] = logs['custom2'].astype(int)
    logs["custom3"] = logs["custom3"].astype(str)
    # rename custom1 to campaign id, custom2 to experiment ID, custom3 to well
    logs = logs.rename(
        columns={
            "custom1": "campaign id",
            "custom2": "experiment id",
            "custom3": "well",
        }
    )

    # filter on campaign ids in the campaign ids list
    logs = logs[logs["campaign id"].isin(campaign_ids)]

    if logs.empty:
        print("No experiments found for campaign ids: " + str(campaign_ids))
        exit()

    # filter on message containing 'Data'
    logs = logs[logs["message"].str.contains("Data")]
    # split message into 6 columns called 'message', 'action', 'volume', 'density', 'preweight', 'postweight'
    logs[["message", "action", "volume", "density", "preweight", "postweight"]] = logs[
        "message"
    ].str.split(",", expand=True)
    # add a column called 'weight change' that is postweight - preweight
    logs["weight change"] = logs["postweight"].astype(float) - logs["preweight"].astype(
        float
    )
    # add a column that is percent error betwen the actual weight change and the expected weight change based on the volume * density
    logs["percent error"] = (
        logs["weight change"]
        - (logs["volume"].astype(float) * logs["density"].astype(float))
    ) / (logs["volume"].astype(float) * logs["density"].astype(float))
    # Remove outliers
    logs = logs[logs["percent error"] * 100 < 10]
    logs = logs[logs["percent error"] * 100 > -10]

    # scatter Plot the percent error for each experiment, grouped by experiment id
    logs.plot.scatter(x="experiment id", y="weight change", c="DarkBlue")
    plt.xlabel("Experiment #")
    # set the x axis to be the experiment ids in order and replace with 1 - n, sorting so that the x axis is in order
    plt.xticks(
        logs["experiment id"].sort_values().unique(),
        range(1, len(logs["experiment id"].sort_values().unique()) + 1),
    )
    # rotate the x axis labels by 85 degrees
    plt.xticks(rotation=85)
    # space the xticks evenly
    plt.locator_params(
        axis="x", nbins=len(logs["experiment id"].sort_values().unique())
    )
    # reduce the number of xlabels to 100
    plt.locator_params(axis="x", nbins=100)
    plt.ylabel("Weight Change (g)")
    plt.title("Weight Change by Experiment #")
    plt.show()
    # print out the number of experiments and the average weight change
    print("Number of experiments: " + str(len(logs)))
    print("Average weight change: " + str(logs["weight change"].mean()))


if __name__ == "__main__":
    # plate_analysis()
    direct_log_analysis()
