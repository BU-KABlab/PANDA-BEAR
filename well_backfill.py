"""Read in the old well hx and backfill the sqlite db"""

from pathlib import Path
import pandas as pd
from epanda_lib.sql_tools.models import Experiment
from epanda_lib.sql_utilities import save_wells_to_db, Well, WellCoordinates, ExperimentResultsRecord
import json

def wellplate_backfill(plate_id:int):
    well_hx_file = Path(
        "//engnas.bu.edu/research/eng_research_kablab/Shared Resources/PANDA/system state/well_history.csv"
    )
    well_hx = pd.read_csv(well_hx_file, sep="&", skipinitialspace=True)

    # The well_hx csv has columns:
    # plate id
    # type number
    # well id
    # experiment id
    # project id
    # status
    # status date
    # contents
    # volume
    # oordinates

    # The well_hx table has columns:
    # plate_id INTEGER,
    # well_id TEXT,
    # experiment_id INTEGER,
    # project_id INTEGER,
    # status TEXT,
    # status_date DATETIME,
    # contents JSON,
    # volume REAL,
    # coordinates JSON,
    # updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    # PRIMARY KEY (plate_id, well_id)

    # Filter for the 110 plate id
    well_hx = well_hx[well_hx["plate id"] == plate_id]
    table_df = well_hx[
        [
            "plate id",
            "well id",
            "experiment id",
            "project id",
            "status",
            "status date",
            "contents",
            "volume",
            "coordinates",
            "status date",
        ]
    ]

    table_df.columns = [
        "plate_id",
        "well_id",
        "experiment_id",
        "project_id",
        "status",
        "status_date",
        "contents",
        "volume",
        "coordinates",
        "updated",
    ]

    print(table_df.head())

    # Turn the df into a list of Well objects
    well_list = []
    for i, row in table_df.iterrows():

        well = Well(
            plate_id=row["plate_id"],
            well_id=row["well_id"],
            experiment_id=row["experiment_id"],
            project_id=row["project_id"],
            status=row["status"],
            status_date=row["status_date"],
            contents=row["contents"],
            volume=row["volume"],
            coordinates=WellCoordinates(
            x=row["coordinates"].split(",")[0], y=row["coordinates"].split(",")[1]
        ),
        )
        well_list.append(well)

    # Save the well_list to the db
    save_wells_to_db(well_list)

def result_backfill(plate_id):
    """Lookup the given wellplate and find the experiment ids. Then, go to the 
    data folder and find the files named after the experiment ids."""

    # Get the experiment ids
    well_hx_file = Path(
        "//engnas.bu.edu/research/eng_research_kablab/Shared Resources/PANDA/system state/well_history.csv"
    )
    well_hx = pd.read_csv(well_hx_file, sep="&", skipinitialspace=True)
    well_hx = well_hx[well_hx["plate id"] == plate_id]
    experiment_ids = well_hx["experiment id"].unique()

    # Get the files
    data_folder = Path(
        "//engnas.bu.edu/research/eng_research_kablab/Shared Resources/PANDA/data"
    )
    for experiment_id in experiment_ids:
        file = data_folder / f"{experiment_id}.json"
        if file.exists():
            data = pd.read_json(file)
        
        #Populate ExperimentResultsRecord objects from the data
        # Example data:
        #         {
        #     "id": 10000874,
        #     "well_id": "D12",
        #     "ocp_dep_files": [],
        #     "ocp_dep_passes": [],
        #     "ocp_char_files": [
        #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_OCP_CV_0.txt"
        #     ],
        #     "ocp_char_passes": [
        #         true
        #     ],
        #     "ocp_char_final_voltages": [],
        #     "deposition_data_files": [],
        #     "deposition_plot_files": [],
        #     "deposition_max_values": [],
        #     "depsotion_min_values": [],
        #     "characterization_data_files": [
        #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_CV_0.txt"
        #     ],
        #     "characterization_plot_files": [],
        #     "characterization_max_values": [],
        #     "characterization_min_values": [],
        #     "pumping_record": null,
        #     "image_files": [
        #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_before_CV_image_0.tiff",
        #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_after_CV_image_0.tiff",
        #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_after_rinse_image_0.tiff"
        #     ]
        # }
        results_list = []
        result = ExperimentResultsRecord(
            experiment_id=data["id"],
            result_type=,
            result_value=,
            context=
        )
