"""Read in the old well hx and backfill the sqlite db"""

from pathlib import Path
import pandas as pd
from epanda_lib import sql_utilities
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

# def result_backfill(plate_id):
#     """Lookup the given wellplate and find the experiment ids. Then, go to the 
#     data folder and find the files named after the experiment ids."""

#     # Get the experiment ids
#     well_hx_file = Path(
#         "//engnas.bu.edu/research/eng_research_kablab/Shared Resources/PANDA/system state/well_history.csv"
#     )
#     well_hx = pd.read_csv(well_hx_file, sep="&", skipinitialspace=True)
#     well_hx = well_hx[well_hx["plate id"] == plate_id]
#     experiment_ids = well_hx["experiment id"].unique()

#     # Get the files
#     data_folder = Path(
#         "//engnas.bu.edu/research/eng_research_kablab/Shared Resources/PANDA/data"
#     )
#     for experiment_id in experiment_ids:
#         file = data_folder / f"{experiment_id}.json"
#         if file.exists():
#             data = pd.read_json(file)
        
#         #Populate ExperimentResultsRecord objects from the data
#         # Example data:
#         #         {
#         #     "id": 10000874,
#         #     "well_id": "D12",
#         #     "ocp_dep_files": [],
#         #     "ocp_dep_passes": [],
#         #     "ocp_char_files": [
#         #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_OCP_CV_0.txt"
#         #     ],
#         #     "ocp_char_passes": [
#         #         true
#         #     ],
#         #     "ocp_char_final_voltages": [],
#         #     "deposition_data_files": [],
#         #     "deposition_plot_files": [],
#         #     "deposition_max_values": [],
#         #     "depsotion_min_values": [],
#         #     "characterization_data_files": [
#         #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_CV_0.txt"
#         #     ],
#         #     "characterization_plot_files": [],
#         #     "characterization_max_values": [],
#         #     "characterization_min_values": [],
#         #     "pumping_record": null,
#         #     "image_files": [
#         #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_before_CV_image_0.tiff",
#         #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_after_CV_image_0.tiff",
#         #         "\\\\engnas.bu.edu\\research\\eng_research_kablab\\Shared Resources\\PANDA\\data\\16_2_10000874_D12_characterizing_after_rinse_image_0.tiff"
#         #     ]
#         # }
#         results_list = []
#         result = ExperimentResultsRecord(
#             experiment_id=data["id"],
#             result_type=,
#             result_value=,
#             context=
#         )

def result_backfill_from_training_data():
    """Get the plate 110 from sql, and then get the experiment ids for each well id.
    Find the well id in the trianing data and backfill the results"""
    plate_id = 110
    # Get the experiment ids
    wells = sql_utilities.select_wellplate_wells(plate_id)
    well_to_experiment = {well.well_id: well.experiment_id for well in wells}

    # Load the MLtraining data
    training_data = pd.read_csv(
        Path("epanda_lib/analyzer/edot/ml_model/training_data/MLTrainingData.csv"
    ))
    # well_id,L*_c,A*_c,B*_c,L*_b,A*_b,B*_b,deltaE,voltage,time,Charge Passed,Capacitance,Deposition Efficiency,bleachCP,Contrast Efficiency,Echromic Efficiency,concentration
    # Each column is a result type, and each row is the value for that result type for that well
    # The colmns first need renaming to be standardized
    # well_id,l_c,a_c,b_c,l_b,a_b,b_b,delta_e00,ca_step_1_voltage,ca_step_1_time,ChargePassed,Capacitance,DepositionEfficiency,BleachChargePassed,DepositionEfficiency,ElectrochromicEfficiency,edot_concentration
    training_data.columns = [
        "well_id",
        "l_c",
        "a_c",
        "b_c",
        "l_b",
        "a_b",
        "b_b",
        "delta_e00",
        "ca_step_1_voltage",
        "ca_step_1_time",
        "ChargePassed",
        "Capacitance",
        "DepositionEfficiency",
        "BleachChargePassed",
        "ContrastEfficiency",
        "ElectrochromicEfficiency",
        "edot_concentration",
    ]
    # Now, we can filter the training data for the experiment ids we have from the sql db
    # and save the results to the db
    for well_id, experiment_id in well_to_experiment.items():
        if well_id not in training_data["well_id"].values:
            print(f"Well id {well_id} not in training data")
            continue
        well_data = training_data[training_data["well_id"] == well_id]
        results = []
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="l_c",
            result_value=well_data["l_c"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="a_c",
            result_value=well_data["a_c"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="b_c",
            result_value=well_data["b_c"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="l_b",
            result_value=well_data["l_b"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="a_b",
            result_value=well_data["a_b"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="b_b",
            result_value=well_data["b_b"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="delta_e00",
            result_value=well_data["delta_e00"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="ca_step_1_voltage",
            result_value=well_data["ca_step_1_voltage"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="ca_step_1_time",
            result_value=well_data["ca_step_1_time"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="ChargePassed",
            result_value=well_data["ChargePassed"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="Capacitance",
            result_value=well_data["Capacitance"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="DepositionEfficiency",
            result_value=well_data["DepositionEfficiency"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="BleachChargePassed",
            result_value=well_data["BleachChargePassed"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="ContrastEfficiency",
            result_value=well_data["ContrastEfficiency"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="DepositionEfficiency",
            result_value=well_data["DepositionEfficiency"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="ElectrochromicEfficiency",
            result_value=well_data["ElectrochromicEfficiency"].values[0],
            context=None,
        ))
        results.append(ExperimentResultsRecord(
            experiment_id=experiment_id,
            result_type="edot_concentration",
            result_value=well_data["edot_concentration"].values[0],
            context=None,
        ))
        sql_utilities.insert_experiment_results(results)

if __name__ == "__main__":
    wellplate_backfill(plate_id=110)
    #result_backfill_from_training_data()
    # result_backfill(plate_id=110)