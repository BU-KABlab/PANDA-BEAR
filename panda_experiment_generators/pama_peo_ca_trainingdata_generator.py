"""Experiment parameters for the edot screening experiments"""

import pandas as pd
from pydantic import ValidationError
from pathlib import Path
import pandas as pd
from panda_lib import scheduler
from panda_lib.experiments import experiment_types

PROJECT_ID = 300 
EXPERIMENT_NAME = "pama_peo_CA_LHStraining"
CAMPAIGN_ID = 4
PLATE_TYPE = 8 


params_path = Path(__file__).parent / "pama_peo_ca_trainingdata_params.csv"
params_df = pd.read_csv(params_path)


def main():
    """Runs the pama contact angle drying experiment generator."""

    # controller.load_new_wellplate(new_wellplate_type_number=6)
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments: list[experiment_types.EchemExperimentBase] = []

    try:
        for _, row in params_df.iterrows():
            v_dep = row["v_dep"]
            pama_conc = row["pama_conc"]
            peo_conc = row["peo_conc"]

            experiments.append(
                experiment_types.EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_name="pama_peo_trainingdata_protocol",
                    analysis_id=999, 
                    well_id="C5",
                    wellplate_type_id=PLATE_TYPE,
                    experiment_name=EXPERIMENT_NAME,
                    project_id=PROJECT_ID,
                    project_campaign_id=CAMPAIGN_ID,
                    solutions={
                        "pama_200": {"volume": 0, "concentration": 200, "repeated": 1},
                        "peo_70": {"volume": 0, "concentration": 70, "repeated": 1},
                        "electrolyte": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "ipa": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "dmf": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "acn": {"volume": 0, "concentration": 0.0, "repeated": 1},
                        "water": {"volume": 0, "concentration": 0.0, "repeated": 1},
                    },
                    rinse_sol_name="dmf",
                    rinse_vol=200,
                    rinse_count=3,
                    flush_sol_name="dmf",
                    flush_sol_vol=200,
                    flush_count=3,
                    dep_sol_conc=pama_conc,
                    dep_sol2_conc=peo_conc,
                    filename=EXPERIMENT_NAME + "_" + str(experiment_id),
                    # Echem specific
                    ocp=1,
                    baseline=0,
                    cv=0,
                    ca=1,
                    ca_sample_period=0.1,
                    ca_prestep_voltage=0.0,
                    ca_prestep_time_delay=0.0,
                    ca_step_1_voltage=v_dep,
                    ca_step_1_time=600, # deposition time in seconds
                    ca_step_2_voltage=0.0,
                    ca_step_2_time=0.0,
                    ca_sample_rate=0.5,
                )
            )
            experiment_id += 1

        scheduler.schedule_experiments(experiments)

    except ValidationError as e:
        raise e


