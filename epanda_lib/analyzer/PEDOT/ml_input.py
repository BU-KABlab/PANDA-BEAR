from epanda_lib import sql_utilities
from epanda_lib.config.config_tools import read_testing_config
import pandas as pd

# pylint: disable=invalid-name

data = {
    'name': ['experiment_id', 'ca_step_1_voltage', 'ca_step_1_time', 'edot_concentration', 'CA_deposition', 'CV_characterization', 'CA_bleaching', 'BeforeDeposition', 'AfterBleaching', 'AfterColoring'],
    'type': ['int', 'float', 'float', 'float', 'ca_data_file', 'cv_data_file', 'ca_data_file', 'image', 'image', 'image'],
    'source': [None, 'parameter', 'parameter', 'parameter', 'result', 'result', 'result', 'result', 'result', 'result'],
    'context': [None, None, None, None, 'CA_deposition', 'CV_characterization', 'CA_bleaching', 'BeforeDeposition', 'AfterBleaching', 'AfterColoring'],
    'value': [None, None, None, None, None, None, None, None, None, None]
}

df = pd.DataFrame(data)

def populate_required_information(experiment_id: int):
    """Populates the required information for the machine learning input."""
    sql_utilities.set_system_status(
        sql_utilities.SystemState.BUSY, "analyzing data", read_testing_config()
    )
    df.loc[df['name'] == 'experiment_id', 'value'] = experiment_id

    # Get the experiment parameters
    parameters = df.loc[df['source'] == 'parameter', 'name']
    for parameter in parameters:
        df.loc[df['name'] == parameter, 'value'] = sql_utilities.select_specific_parameter(
            experiment_id, parameter
        )

    # Get the experiment results
    table = df.loc[df['source'] == 'result'][['name', 'type','context']].values
    for row in table:
        name, result_type, context = row
        value = sql_utilities.select_specific_result(
            experiment_id, result_type, context
        )
        # if result_type == 'image':
        #     value = Image.open(value)
        if value is not None:
            df.loc[(df['name'] == name), 'value'] = value.result_value

    sql_utilities.set_system_status(
        sql_utilities.SystemState.IDLE, "ready", read_testing_config()
    )
    return df

if __name__ == "__main__":
    info = populate_required_information(10000004)
    # Print the required information
    print(info)
    # info.at[7, 'value'].show()
    # info.at[8, 'value'].show()
    # info.at[9, 'value'].show()
