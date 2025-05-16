# API Reference

This document provides a comprehensive reference of the PANDA-SDL API, covering the main components and functions available for writing protocols, generators, and analyzers.

## Core Components

### Toolkit

The `Toolkit` class is the central interface for interacting with the PANDA-SDL hardware and software systems.

```python
from panda_lib import Toolkit

# Create a toolkit instance
toolkit = Toolkit()
```

#### Key Properties and Methods

| Property/Method                        | Description                            |
| -------------------------------------- | -------------------------------------- |
| `toolkit.wellplate`                    | Access to the current wellplate        |
| `toolkit.potentiostat`                 | Access to the potentiostat             |
| `toolkit.camera`                       | Access to the camera                   |
| `toolkit.pipette`                      | Access to the pipetting system         |
| `toolkit.get_ml_model()`               | Get access to a ML model               |
| `toolkit.use_specific_deck_zone(zone)` | Position robot at a specific deck zone |
| `toolkit.move_pipette_to_well(well)`   | Move pipette to a specific well        |
| `toolkit.global_logger`                | System logger for recording events     |
| `toolkit.disconnect_all()`             | Disconnect from all hardware           |

### Experiments

The experiment classes define the structure and parameters of PANDA-SDL experiments.

```python
from panda_lib.experiments import EchemExperimentBase

# Create an experiment
experiment = EchemExperimentBase(
    experiment_id=123,
    protocol_id="my_protocol.py",
    well_id="A1",
    # Additional parameters...
)
```

#### Experiment Types

| Class                 | Description                                |
| --------------------- | ------------------------------------------ |
| `EchemExperimentBase` | Base class for electrochemical experiments |
| `ExperimentStatus`    | Enum for experiment status values          |

#### Key Experiment Properties

| Property                       | Description                                    |
| ------------------------------ | ---------------------------------------------- |
| `experiment.experiment_id`     | Unique identifier for the experiment           |
| `experiment.protocol_id`       | ID of the protocol to run                      |
| `experiment.well_id`           | Well where the experiment will run             |
| `experiment.plate_type_number` | Type of wellplate to use                       |
| `experiment.experiment_name`   | Name of the experiment                         |
| `experiment.solutions`         | Dictionary of solutions used in the experiment |
| `experiment.status`            | Current status of the experiment               |

### Scheduler

The scheduler manages experiment queuing and execution.

```python
from panda_lib import scheduler

# Get next experiment ID
next_id = scheduler.determine_next_experiment_id()

# Add experiments to the queue
scheduler.add_nonfile_experiments(experiments_list)
```

#### Key Scheduler Functions

| Function                                         | Description                          |
| ------------------------------------------------ | ------------------------------------ |
| `scheduler.determine_next_experiment_id()`       | Get the next available experiment ID |
| `scheduler.add_nonfile_experiments(experiments)` | Add experiments to the queue         |
| `scheduler.get_experiment_queue()`               | Get the current experiment queue     |
| `scheduler.clear_queue()`                        | Clear the experiment queue           |

## Action Functions

### Fluid Handling

```python
from panda_lib.actions import transfer, clear_well, flush_pipette, rinse_well
```

| Function                                                                             | Description                     | Parameters                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------ | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `transfer(volume, solution_name, destination_well, toolkit)`                         | Transfer solution to a well     | <ul><li>`volume`: Volume in μL</li><li>`solution_name`: Name of solution</li><li>`destination_well`: Target well</li><li>`toolkit`: System toolkit</li></ul>                                                                      |
| `clear_well(toolkit, well)`                                                          | Remove all contents from a well | <ul><li>`toolkit`: System toolkit</li><li>`well`: Well to clear</li></ul>                                                                                                                                                         |
| `flush_pipette(flush_with, toolkit)`                                                 | Clean the pipette               | <ul><li>`flush_with`: Solution to use for flushing</li><li>`toolkit`: System toolkit</li></ul>                                                                                                                                    |
| `rinse_well(instructions, toolkit, alt_sol_name=None, alt_vol=None, alt_count=None)` | Rinse a well with solution      | <ul><li>`instructions`: Experiment instructions</li><li>`toolkit`: System toolkit</li><li>`alt_sol_name`: Alternative solution name</li><li>`alt_vol`: Alternative volume</li><li>`alt_count`: Alternative repeat count</li></ul> |

### Imaging

```python
from panda_lib.actions import image_well
```

| Function                                       | Description             | Parameters                                                                                                                     |
| ---------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `image_well(toolkit, experiment, image_label)` | Take an image of a well | <ul><li>`toolkit`: System toolkit</li><li>`experiment`: Experiment object</li><li>`image_label`: Label for the image</li></ul> |

### Electrochemistry

```python
from panda_lib.actions import chrono_amp, cyclic_volt, open_circuit_potential
```

| Function                                            | Description                    | Parameters                                                                                                      |
| --------------------------------------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `chrono_amp(toolkit, experiment, well)`             | Perform chronoamperometry      | <ul><li>`toolkit`: System toolkit</li><li>`experiment`: Experiment object</li><li>`well`: Target well</li></ul> |
| `cyclic_volt(toolkit, experiment, well)`            | Perform cyclic voltammetry     | <ul><li>`toolkit`: System toolkit</li><li>`experiment`: Experiment object</li><li>`well`: Target well</li></ul> |
| `open_circuit_potential(toolkit, experiment, well)` | Measure open circuit potential | <ul><li>`toolkit`: System toolkit</li><li>`experiment`: Experiment object</li><li>`well`: Target well</li></ul> |

## Labware

### Wellplates

```python
from panda_lib.labware.wellplates import Wellplate, Well
```

| Class/Method                  | Description                              |
| ----------------------------- | ---------------------------------------- |
| `Wellplate`                   | Class representing a wellplate           |
| `Wellplate.get_well(well_id)` | Get a specific well by ID                |
| `Well`                        | Class representing a well in a wellplate |
| `Well.get_volume()`           | Get the current volume in a well         |
| `Well.get_position()`         | Get the position of a well               |

## Database Functions

```python
from panda_lib import sql_tools
```

| Function                                                           | Description            | Parameters                                                                                                                 |
| ------------------------------------------------------------------ | ---------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `sql_tools.execute_query(query, fetch_all=False, fetch_one=False)` | Execute an SQL query   | <ul><li>`query`: SQL query string</li><li>`fetch_all`: Return all results</li><li>`fetch_one`: Return one result</li></ul> |
| `sql_tools.get_experiment(experiment_id)`                          | Get experiment by ID   | <ul><li>`experiment_id`: ID of the experiment</li></ul>                                                                    |
| `sql_tools.get_results(experiment_id, result_type)`                | Get experiment results | <ul><li>`experiment_id`: ID of the experiment</li><li>`result_type`: Type of results</li></ul>                             |

## Utilities

```python
from panda_lib.utilities import Coordinates, SystemState
```

| Class/Function                                                                       | Description                           |
| ------------------------------------------------------------------------------------ | ------------------------------------- |
| `Coordinates`                                                                        | Class for working with 3D coordinates |
| `SystemState`                                                                        | Class for checking system state       |
| `input_validation.validate_parameter(param, param_type, min_val=None, max_val=None)` | Validate a parameter's type and range |

## Advanced Features

### Machine Learning Integration

```python
# Get a ML model
model = toolkit.get_ml_model("my_model_name")

# Use the model
predictions = model.predict(input_data)
```

### Custom Hardware Communication

```python
# Direct serial communication
serial_device = toolkit.get_serial_device("device_name")
serial_device.write("command")
response = serial_device.read()
```

## Exception Handling

The PANDA-SDL system defines several exception types for handling errors:

```python
from panda_lib.exceptions import PandaError, HardwareError, ExperimentError
```

| Exception         | Description                                   |
| ----------------- | --------------------------------------------- |
| `PandaError`      | Base exception class for all PANDA-SDL errors |
| `HardwareError`   | Exception for hardware-related errors         |
| `ExperimentError` | Exception for experiment-related errors       |

## Example Usage Patterns

### Protocol Example

```python
def run(experiment, toolkit):
    """Run an electrochemical deposition experiment."""
    
    # Log the start of the experiment
    toolkit.global_logger.info(f"Running experiment: {experiment.experiment_name}")
    
    # Get the well for this experiment
    well = toolkit.wellplate.get_well(experiment.well_id)
    
    # Take an initial image
    image_well(toolkit, experiment, "Initial Well")
    
    # Transfer solution to the well
    transfer(
        experiment.solutions["polymer_solution"]["volume"],
        "polymer_solution",
        well,
        toolkit
    )
    
    # Perform chronoamperometry
    chrono_amp(toolkit, experiment, well)
    
    # Image the result
    image_well(toolkit, experiment, "After Deposition")
    
    # Clean up
    clear_well(toolkit, well)
    rinse_well(instructions=experiment, toolkit=toolkit)
    flush_pipette(flush_with=experiment.flush_sol_name, toolkit=toolkit)
    
    # Log completion
    toolkit.global_logger.info("Experiment complete")
```

### Generator Example

```python
def main():
    """Generate a series of experiments with different voltages."""
    
    voltages = [1.0, 1.5, 2.0]
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments = []
    
    for voltage in voltages:
        experiments.append(
            EchemExperimentBase(
                experiment_id=experiment_id,
                protocol_id="deposition_protocol.py",
                well_id="A1",
                # Set voltage-specific parameters
                ca_step_1_voltage=voltage,
                deposition_voltage=voltage,
                experiment_name=f"deposition-v{voltage}",
                # Other parameters...
            )
        )
        experiment_id += 1
    
    scheduler.add_nonfile_experiments(experiments)
    return f"Generated {len(experiments)} experiments"
```

### Analyzer Example

```python
def analyze_experiment(experiment_id):
    """Analyze an experiment's results."""
    
    # Get experiment data
    experiment = sql_tools.get_experiment(experiment_id)
    results = sql_tools.get_results(experiment_id, "echem")
    
    # Process the data
    # ...
    
    # Update experiment status
    sql_tools.update_experiment_status(
        experiment_id, 
        ExperimentStatus.ANALYZED.value
    )
    
    return "Analysis complete"
```

## Additional Resources

For more detailed information about specific components, refer to:

- Source code docstrings in the respective modules
- [End User Manual](../documentation/end_user_manual.md)
- [Developer Manual](../documentation/developer_manual.md)
