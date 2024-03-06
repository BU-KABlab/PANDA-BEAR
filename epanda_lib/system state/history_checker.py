import pandas
from pathlib import Path

# Read in the well history
well_hx = pandas.read_csv(Path("data/well_history.csv"), skipinitialspace=True)
well_hx = well_hx.dropna(subset=["experiment id"])
# filter the dataframe for campaigns specified
campaign_of_interest = input("Enter the campaign ID of interest: ")
well_hx = well_hx[well_hx["campaign id"] == int(campaign_of_interest)]

