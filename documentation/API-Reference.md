# API Reference

This document provides a comprehensive reference of the PANDA-SDL API, covering the main components and functions available for writing protocols, generators, and analyzers.

- [API Reference](#api-reference)
  - [Core Components](#core-components)
    - [Toolkit](#toolkit)
      - [Key Properties and Methods](#key-properties-and-methods)
    - [Experiments](#experiments)
      - [Experiment Types](#experiment-types)
      - [Key Experiment Properties](#key-experiment-properties)
        - [Base Experiment Properties](#base-experiment-properties)
        - [Electrochemistry Experiment Properties](#electrochemistry-experiment-properties)
    - [Scheduler](#scheduler)
      - [Key Scheduler Functions](#key-scheduler-functions)
      - [Scheduler Workflow](#scheduler-workflow)
      - [Experiment Priorities](#experiment-priorities)
  - [Action Functions (aliased as Protocol)](#action-functions-aliased-as-protocol)
    - [Fluid Handling](#fluid-handling)
    - [Movement](#movement)
    - [Electrochemistry](#electrochemistry)
    - [Imaging](#imaging)
    - [Vessel Handling](#vessel-handling)
      - [VesselSelector Class](#vesselselector-class)
    - [Utility Actions](#utility-actions)
  - [Labware](#labware)
    - [Wellplates](#wellplates)
      - [Wellplate Class](#wellplate-class)
      - [Well Class](#well-class)
    - [Vials](#vials)
      - [Vial Classes](#vial-classes)
      - [Vial Methods/Properties](#vial-methodsproperties)
      - [Vial Helper Functions](#vial-helper-functions)
    - [Labware Utilities](#labware-utilities)
  - [Database Functions](#database-functions)
    - [Core Database Functions](#core-database-functions)
    - [Wellplate Functions](#wellplate-functions)
    - [Well Functions](#well-functions)
    - [Protocol Functions](#protocol-functions)
    - [Generator Functions](#generator-functions)
    - [Queue Functions](#queue-functions)
    - [System Functions](#system-functions)
    - [Results Functions](#results-functions)
  - [Utilities](#utilities)
  - [Advanced Features](#advanced-features)
    - [Machine Learning Integration](#machine-learning-integration)
  - [Exception Handling](#exception-handling)
    - [Experiment Related Exceptions](#experiment-related-exceptions)
    - [Labware Related Exceptions](#labware-related-exceptions)
    - [Hardware Related Exceptions](#hardware-related-exceptions)
    - [System Control Exceptions](#system-control-exceptions)
  - [Example Usage Patterns](#example-usage-patterns)
    - [Protocol Example](#protocol-example)
    - [Generator Example](#generator-example)
    - [Analyzer Example](#analyzer-example)
  - [Additional Resources](#additional-resources)

## Core Components

### Toolkit

The `Toolkit` class is the central interface for interacting with the PANDA-SDL hardware and software systems.

```python
from panda_lib import Toolkit

# Create a toolkit instance
toolkit = Toolkit()
```

#### Key Properties and Methods

| Property/Method               | Description                        |
| ----------------------------- | ---------------------------------- |
| `toolkit.mill`                | Access to the gantry               |
| `toolkit.scale`               | Access to the sartorius scale      |
| `toolkit.pipette`             | Access to the OT2 or WPI Pipette   |
| `toolkit.arduino`             | Access to the PAW arduino          |
| `toolkit.camera`              | Access to the camera               |
| `toolkit.experiment_logger`   | Seperate logger for experiment     |
| `toolkit.global_logger`       | System logger for recording events |
| `toolkit.disconnect()`        | Disconnect from all hardware       |
| `toolkit.initialize_camera()` | Connect to FLIR or webcam          |

NOTE: The potentiostat is not included as it is connected and disconnected with each operation.

### Experiments

The experiment classes define the structure and parameters of PANDA-SDL experiments.

```python
from panda_lib.experiments import ExperimentBase

# Create an experiment
experiment = ExperimentBase(
    experiment_id=123,
    protocol_id="my_protocol.py",
    well_id="A1",
    # Additional parameters...
)
```

#### Experiment Types

| Class                 | Description                                 |
| --------------------- | ------------------------------------------- |
| `ExperimentBase`      | Base class for experiments                  |
| `EchemExperimentBase` | Base class for electrochemistry experiments |
| `ExperimentStatus`    | Enum of possible experiment statuses        |

#### Key Experiment Properties

There are ExperimentGenerators and EchemExperimentGenerators for use in the generator scripts to make filling in experiment parameters easier.

##### Base Experiment Properties

| Property                             | Type                 | Description                                           |
| ------------------------------------ | -------------------- | ----------------------------------------------------- |
| `experiment.experiment_id`           | int                  | Unique identifier for the experiment                  |
| `experiment.experiment_name`         | str                  | Name of the experiment                                |
| `experiment.protocol_name`           | Union[int, str]      | Identifier for the protocol used in the experiment    |
| `experiment.priority`                | Optional[int]        | Priority level of the experiment (0 is highest)       |
| `experiment.well_id`                 | Optional[str]        | Well where the experiment will run (e.g., "A1")       |
| `experiment.project_id`              | int                  | Identifier for the project associated with experiment |
| `experiment.solutions`               | dict                 | Dictionary of solutions used in the experiment        |
| `experiment.wellplate_type_id`       | int                  | Type of wellplate to use                              |
| `experiment.pumping_rate`            | float                | Rate at which the solution is pumped                  |
| `experiment.status`                  | ExperimentStatus     | Current status of the experiment                      |
| `experiment.status_date`             | datetime             | Timestamp when status was last updated                |
| `experiment.filename`                | str                  | Filename associated with experiment data              |
| `experiment.results`                 | ExperimentResult     | Results of the experiment                             |
| `experiment.project_campaign_id`     | int                  | Identifier for the project campaign                   |
| `experiment.plate_id`                | Optional[int]        | Identifier for the plate used                         |
| `experiment.override_well_selection` | bool                 | Flag to override automatic well selection             |
| `experiment.well`                    | object               | Well object associated with the experiment            |
| `experiment.analyzer`                | Union[Callable, str] | Analyzer function or script for the experiment        |
| `experiment.generator`               | Union[Callable, str] | Generator function or script for the experiment       |
| `experiment.analysis_id`             | int                  | Identifier for the analysis                           |
| `experiment.needs_analysis`          | int                  | Flag indicating if the experiment needs analysis      |
| `experiment.panda_version`           | float                | Version of the PANDA system used                      |
| `experiment.panda_unit_id`           | int                  | Identifier for the PANDA unit used                    |

##### Electrochemistry Experiment Properties

The `EchemExperimentBase` class extends `ExperimentBase` and adds the following properties:

| Property                           | Type              | Description                                      |
| ---------------------------------- | ----------------- | ------------------------------------------------ |
| `experiment.ocp`                   | int               | Open Circuit Potential flag (0=off, 1=on)        |
| `experiment.ca`                    | int               | Chronoamperometry flag (0=off, 1=on)             |
| `experiment.cv`                    | int               | Cyclic Voltammetry flag (0=off, 1=on)            |
| `experiment.baseline`              | int               | Baseline flag (0=off, 1=on)                      |
| `experiment.flush_sol_name`        | str               | Flush solution name                              |
| `experiment.flush_sol_vol`         | Union[int, float] | Flush solution volume                            |
| `experiment.flush_count`           | int               | Number of flush cycles                           |
| `experiment.mix`                   | int               | Mix flag (0=off, 1=on)                           |
| `experiment.mix_count`             | int               | Number of mixing cycles                          |
| `experiment.mix_volume`            | int               | Volume to mix                                    |
| `experiment.rinse_sol_name`        | str               | Rinse solution name                              |
| `experiment.rinse_count`           | int               | Number of rinse cycles                           |
| `experiment.rinse_vol`             | int               | Rinse volume                                     |
| `experiment.ca_sample_period`      | float             | Chronoamperometry sample period                  |
| `experiment.ca_prestep_voltage`    | float             | Pre-step voltage (V)                             |
| `experiment.ca_prestep_time_delay` | float             | Pre-step delay time (s)                          |
| `experiment.ca_step_1_voltage`     | float             | Step 1 voltage (V), usually deposition potential |
| `experiment.ca_step_1_time`        | float             | Step 1 time (s), usually deposition duration     |
| `experiment.ca_step_2_voltage`     | float             | Step 2 voltage (V)                               |
| `experiment.ca_step_2_time`        | float             | Step 2 time (s)                                  |
| `experiment.ca_sample_rate`        | float             | Chronoamperometry sample rate (s)                |
| `experiment.char_sol_name`         | str               | Characterization solution name                   |
| `experiment.char_vol`              | int               | Characterization solution volume                 |
| `experiment.char_concentration`    | float             | Characterization solution concentration          |
| `experiment.cv_sample_period`      | float             | Cyclic voltammetry sample period                 |
| `experiment.cv_initial_voltage`    | float             | Initial voltage for CV                           |
| `experiment.cv_first_anodic_peak`  | float             | First anodic peak voltage                        |
| `experiment.cv_second_anodic_peak` | float             | Second anodic peak voltage                       |
| `experiment.cv_final_voltage`      | float             | Final voltage for CV                             |
| `experiment.cv_step_size`          | float             | Voltage step size for CV                         |
| `experiment.cv_cycle_count`        | int               | Number of CV cycles                              |
| `experiment.cv_scan_rate_cycle_1`  | float             | Scan rate for first cycle (V/s)                  |
| `experiment.cv_scan_rate_cycle_2`  | float             | Scan rate for second cycle (V/s)                 |
| `experiment.cv_scan_rate_cycle_3`  | float             | Scan rate for third cycle (V/s)                  |
| `experiment.cv_sample_rate`        | float             | Calculated CV sample rate (CVstep/CVsr1)         |

### Scheduler

The scheduler manages experiment queuing and execution, handling the allocation of experiments to wells, prioritization, and status tracking.

```python
from panda_lib import scheduler

# Get next experiment ID
next_id = scheduler.determine_next_experiment_id()

# Add experiments to the queue
scheduler.add_nonfile_experiments(experiments_list)

# Read the next experiment from the queue
experiment, filename = scheduler.read_next_experiment_from_queue()
```

#### Key Scheduler Functions

| Function                                                                          | Description                                                  | Parameters                                                                                                                        |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| `scheduler.determine_next_experiment_id()`                                        | Get the next available experiment ID                         |                                                                                                                                   |
| `scheduler.schedule_experiments(experiments, override=False)`                     | Schedule a list of experiments to be run                     | <ul><li>`experiments`: List of experiment objects</li><li>`override`: Whether to override well selection checks</li></ul>         |
| `scheduler.read_next_experiment_from_queue(random_pick=True, experiment_id=None)` | Get the next experiment from the queue                       | <ul><li>`random_pick`: Whether to randomly select from highest priority</li><li>`experiment_id`: Specific experiment ID</li></ul> |
| `scheduler.check_well_status(well_to_check, plate_id=None)`                       | Check the status of a specific well                          | <ul><li>`well_to_check`: Well ID (e.g., "A1")</li><li>`plate_id`: Plate ID (optional)</li></ul>                                   |
| `scheduler.choose_next_new_well(plate_id=None)`                                   | Get the next available well for an experiment                | <ul><li>`plate_id`: Plate ID (optional)</li></ul>                                                                                 |
| `scheduler.change_well_status(well, experiment)`                                  | Update the status of a well                                  | <ul><li>`well`: Well object or ID</li><li>`experiment`: Experiment object</li></ul>                                               |
| `scheduler.update_experiment_queue_priority(experiment_id, priority)`             | Change the priority of an experiment in the queue            | <ul><li>`experiment_id`: Experiment ID</li><li>`priority`: New priority (lower is higher priority)</li></ul>                      |
| `scheduler.update_experiment_info(experiment, column)`                            | Update a specific column in the experiment database record   | <ul><li>`experiment`: Experiment object</li><li>`column`: Column name to update</li></ul>                                         |
| `scheduler.update_experiment_parameters(experiment, parameter)`                   | Update a specific parameter for an experiment                | <ul><li>`experiment`: Experiment object</li><li>`parameter`: Parameter name to update</li></ul>                                   |
| `scheduler.validate_experiment_plate(experiment)`                                 | Check if the plate configuration is valid for the experiment | <ul><li>`experiment`: Experiment object</li></ul>                                                                                 |
| `scheduler.assign_well_if_unavailable(experiment)`                                | Attempt to find an available well if current well is in use  | <ul><li>`experiment`: Experiment object</li></ul>                                                                                 |

#### Scheduler Workflow

1. **Experiment Creation**: Create experiment objects with appropriate parameters
2. **Scheduling**: Call `schedule_experiments()` to add experiments to the queue
3. **Execution**: System calls `read_next_experiment_from_queue()` to get the next experiment to run
4. **Status Updates**: Throughout execution, `change_well_status()` updates the current state

#### Experiment Priorities

Experiments are processed based on priority (lower number = higher priority):

| Priority | Description                   |
| -------- | ----------------------------- |
| 0        | Highest priority - run first  |
| 1        | Standard priority experiments |
| 2+       | Lower priority experiments    |

## Action Functions (aliased as Protocol)

```python
from panda_lib.actions import ...
```

Or

```python
from panda_lib.protocol import ...
```

### Fluid Handling

| Function                                                                                   | Description                              | Parameters                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------ | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `transfer(volume, src_vessel, dst_vessel, toolkit, source_concentration=None)`             | Transfer liquid between vessels          | <ul><li>`volume`: Volume in μL</li><li>`src_vessel`: Source vessel name or object</li><li>`dst_vessel`: Destination vessel name or object</li><li>`toolkit`: System toolkit</li><li>`source_concentration`: Target concentration in mM (optional)</li></ul>                     |
| `clear_well(toolkit, well)`                                                                | Remove all contents from a well          | <ul><li>`toolkit`: System toolkit</li><li>`well`: Well to clear</li></ul>                                                                                                                                                                                                       |
| `flush_pipette(flush_with, toolkit, flush_volume=120.0, flush_count=1, instructions=None)` | Clean the pipette                        | <ul><li>`flush_with`: Solution to use for flushing</li><li>`toolkit`: System toolkit</li><li>`flush_volume`: Volume to flush with in μL</li><li>`flush_count`: Number of times to flush</li><li>`instructions`: Experiment instructions for setting status (optional)</li></ul> |
| `rinse_well(instructions, toolkit, alt_sol_name=None, alt_vol=None, alt_count=None)`       | Rinse a well with solution               | <ul><li>`instructions`: Experiment instructions</li><li>`toolkit`: System toolkit</li><li>`alt_sol_name`: Alternative solution name</li><li>`alt_vol`: Alternative volume</li><li>`alt_count`: Alternative repeat count</li></ul>                                               |
| `mix(toolkit, well, volume, mix_count=3, mix_height=None)`                                 | Mix solution in a well                   | <ul><li>`toolkit`: System toolkit</li><li>`well`: Well to mix</li><li>`volume`: Volume to mix in μL</li><li>`mix_count`: Number of mix cycles</li><li>`mix_height`: Height to mix at (optional)</li></ul>                                                                       |
| `purge_pipette(toolkit)`                                                                   | Purge pipette contents into waste        | <ul><li>`toolkit`: System toolkit</li></ul>                                                                                                                                                                                                                                     |
| `volume_correction(volume, density=None, viscosity=None)`                                  | Correct volume based on fluid properties | <ul><li>`volume`: Volume to correct in μL</li><li>`density`: Fluid density (default 1.0)</li><li>`viscosity`: Fluid viscosity in cP (default 1.0)</li></ul>                                                                                                                     |

### Movement

| Function                                                   | Description                     | Parameters                                                                                                                                                                          |
| ---------------------------------------------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `move_to_well(well, mill, tool, logger, z_offset=0.0)`     | Move to a specific well         | <ul><li>`well`: Well object</li><li>`mill`: Mill controller</li><li>`tool`: Tool identifier</li><li>`logger`: Logging object</li><li>`z_offset`: Z-axis offset (optional)</li></ul> |
| `move_to_vial(vial, mill, tool, logger, z_offset=0.0)`     | Move to a specific vial         | <ul><li>`vial`: Vial object</li><li>`mill`: Mill controller</li><li>`tool`: Tool identifier</li><li>`logger`: Logging object</li><li>`z_offset`: Z-axis offset (optional)</li></ul> |
| `move_pipette_to_well(well, mill, logger, z_offset=0.0)`   | Move pipette to well            | <ul><li>`well`: Well object</li><li>`mill`: Mill controller</li><li>`logger`: Logging object</li><li>`z_offset`: Z-axis offset (optional)</li></ul>                                 |
| `move_pipette_to_well_bottom(well, mill, logger)`          | Move pipette to well bottom     | <ul><li>`well`: Well object</li><li>`mill`: Mill controller</li><li>`logger`: Logging object</li></ul>                                                                              |
| `move_electrode_to_well(well, mill, logger, z_offset=0.0)` | Move electrode to well          | <ul><li>`well`: Well object</li><li>`mill`: Mill controller</li><li>`logger`: Logging object</li><li>`z_offset`: Z-axis offset (optional)</li></ul>                                 |
| `move_electrode_to_well_bottom(well, mill, logger)`        | Move electrode to well bottom   | <ul><li>`well`: Well object</li><li>`mill`: Mill controller</li><li>`logger`: Logging object</li></ul>                                                                              |
| `decapping_sequence(mill, target_coords, ard_link)`        | Execute vial decapping sequence | <ul><li>`mill`: Mill controller</li><li>`target_coords`: Target coordinates</li><li>`ard_link`: Arduino interface</li></ul>                                                         |
| `capping_sequence(mill, target_coords, ard_link)`          | Execute vial capping sequence   | <ul><li>`mill`: Mill controller</li><li>`target_coords`: Target coordinates</li><li>`ard_link`: Arduino interface</li></ul>                                                         |

### Electrochemistry

| Function                                                                                                        | Description                    | Parameters                                                                                                                                                                                                                                           |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `open_circuit_potential(file_tag, exp=None, testing=False)`                                                     | Measure open circuit potential | <ul><li>`file_tag`: Tag for output files</li><li>`exp`: Experiment object (optional)</li><li>`testing`: Whether in testing mode (optional)</li></ul>                                                                                                 |
| `perform_chronoamperometry(experiment, file_tag=None, custom_parameters=None)`                                  | Perform chronoamperometry      | <ul><li>`experiment`: Experiment object</li><li>`file_tag`: Tag for output files (optional)</li><li>`custom_parameters`: Custom parameters (optional)</li></ul>                                                                                      |
| `perform_cyclic_voltammetry(experiment, file_tag=None, overwrite_initial_voltage=True, custom_parameters=None)` | Perform cyclic voltammetry     | <ul><li>`experiment`: Experiment object</li><li>`file_tag`: Tag for output files (optional)</li><li>`overwrite_initial_voltage`: Whether to overwrite initial voltage (optional)</li><li>`custom_parameters`: Custom parameters (optional)</li></ul> |
| `move_to_and_perform_ca(exp, toolkit, file_tag, well, log=logger)`                                              | Move to well and perform CA    | <ul><li>`exp`: Experiment object</li><li>`toolkit`: System toolkit</li><li>`file_tag`: Tag for output files</li><li>`well`: Target well</li><li>`log`: Logger (optional)</li></ul>                                                                   |
| `move_to_and_perform_cv(exp, toolkit, file_tag, well, log=logger)`                                              | Move to well and perform CV    | <ul><li>`exp`: Experiment object</li><li>`toolkit`: System toolkit</li><li>`file_tag`: Tag for output files</li><li>`well`: Target well</li><li>`log`: Logger (optional)</li></ul>                                                                   |

### Imaging

| Function                                                                        | Description                     | Parameters                                                                                                                                                                                              |
| ------------------------------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `image_well(toolkit, experiment, image_label, curvature_image)`                 | Take an image of a well         | <ul><li>`toolkit`: System toolkit</li><li>`experiment`: Experiment object</li><li>`image_label`: Label for the image</li><li>`curvature_image`: Use the curvature lights</li></ul>                      |
| `capture_new_image(save, num_images, filename, logger, camera_type, camera_id)` | Capture a picture from a camera | <ul><li>`toolkit`: System toolkit</li><li>`path`: Save path</li><li>`file_name`: File name</li><li>`well_id`: Well ID</li><li>`project_id`: Project ID</li><li>`experiment_id`: Experiment ID</li></ul> |

### Vessel Handling

Functions for handling vessels, solution selection, and liquid transfers.

| Function                                                                                                | Description                         | Parameters                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------------------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `solution_selector(solution_name, volume, db_session=SessionLocal)`                                     | Select solution vial for withdrawal | - `solution_name`: Name of the solution to select<br>- `volume`: Volume to be pipetted in μL<br>- `db_session`: Database session for queries (optional)                                                                                                           |
| `waste_selector(solution_name, volume, db_session=SessionLocal)`                                        | Select waste vial for deposit       | - `solution_name`: Name of the waste vial to select<br>- `volume`: Volume to be deposited in μL<br>- `db_session`: Database session for queries (optional)                                                                                                        |
| `_handle_source_vessels(volume, src_vessel, pjct_logger=logger, source_concentration=None, db_session)` | Handle selection of source vessels  | - `volume`: Volume to transfer in μL<br>- `src_vessel`: Source vessel name or object<br>- `pjct_logger`: Logger instance (optional)<br>- `source_concentration`: Target concentration in mM (optional)<br>- `db_session`: Database session for queries (optional) |

#### VesselSelector Class

| Method                                                                                                    | Description                        | Parameters                                                                                                                                                                                                                                                    |
| --------------------------------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VesselSelector.select_solution_vessel(solution_name, volume, db_session=SessionLocal)`                   | Select appropriate solution vessel | - `solution_name`: Name of the required solution<br>- `volume`: Required volume in μL<br>- `db_session`: Database session for queries (optional)                                                                                                              |
| `VesselSelector.select_waste_vessel(solution_name, volume, db_session=SessionLocal)`                      | Select appropriate waste vessel    | - `solution_name`: Name of the waste solution<br>- `volume`: Volume to be deposited in μL<br>- `db_session`: Database session for queries (optional)                                                                                                          |
| `VesselSelector.handle_source_vessels(volume, src_vessel, pjct_logger, source_concentration, db_session)` | Handle source vessel selection     | - `volume`: Required volume in μL<br>- `src_vessel`: Source vessel name or object<br>- `pjct_logger`: Project logger (optional)<br>- `source_concentration`: Target concentration in mM (optional)<br>- `db_session`: Database session for queries (optional) |

### Utility Actions

Utility functions for writing protocols

| Function                     | Description                | Parameters                                                                                                        |
| ---------------------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `delay(seconds, message='')` | Wait for specified seconds | <ul><li>`seconds`: Number of seconds to wait</li><li>`message`: Optional message to display during wait</li></ul> |

## Labware

The PANDA-SDL system works with different types of labware, including wellplates, wells, and vials.

### Wellplates

Wellplates are used to organize wells in a grid format. The system supports various types of wellplates with different configurations.

```python
from panda_lib.labware.wellplates import Wellplate, Well
```

#### Wellplate Class

| Method/Property                                                     | Description                               | Parameters                                                                                                                                                                          |
| ------------------------------------------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Wellplate(session_maker, type_id, plate_id, create_new, **kwargs)` | Constructor for wellplate object          | <ul><li>`session_maker`: Database session maker</li><li>`type_id`: Type ID of wellplate</li><li>`plate_id`: ID of specific plate</li><li>`create_new`: Create new if True</li></ul> |
| `Wellplate.get_well(well_id)`                                       | Get a specific well by ID                 | <ul><li>`well_id`: Well identifier (e.g., "A1")</li></ul>                                                                                                                           |
| `Wellplate.load_plate(plate_id)`                                    | Load an existing wellplate                | <ul><li>`plate_id`: ID of wellplate to load</li></ul>                                                                                                                               |
| `Wellplate.activate_plate()`                                        | Set this wellplate as the active plate    |                                                                                                                                                                                     |
| `Wellplate.deactivate_plate(new_active_plate_id)`                   | Deactivate this wellplate                 | <ul><li>`new_active_plate_id`: Optional ID of plate to activate instead</li></ul>                                                                                                   |
| `Wellplate.id`                                                      | ID of the wellplate                       |                                                                                                                                                                                     |
| `Wellplate.type_id`                                                 | Type ID of the wellplate                  |                                                                                                                                                                                     |
| `Wellplate.name`                                                    | Name of the wellplate                     |                                                                                                                                                                                     |
| `Wellplate.top`                                                     | Z-coordinate of wellplate top             |                                                                                                                                                                                     |
| `Wellplate.bottom`                                                  | Z-coordinate of wellplate bottom          |                                                                                                                                                                                     |
| `Wellplate.echem_height`                                            | Height for electrochemistry operations    |                                                                                                                                                                                     |
| `Wellplate.get_xyz()`                                               | Get (x,y,z) coordinates of the wellplate  |                                                                                                                                                                                     |
| `Wellplate.get_corners()`                                           | Get coordinates of the four corners       |                                                                                                                                                                                     |
| `Wellplate.calculate_well_coordinates(row, col)`                    | Calculate coordinates for a specific well | <ul><li>`row`: Row letter</li><li>`col`: Column number</li></ul>                                                                                                                    |

#### Well Class

| Method/Property                                                | Description                           | Parameters                                                                                                                                                               |
| -------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Well(well_id, plate_id, session_maker, create_new, **kwargs)` | Constructor for well object           | <ul><li>`well_id`: ID of the well</li><li>`plate_id`: ID of the plate</li><li>`session_maker`: Database session maker</li><li>`create_new`: Create new if True</li></ul> |
| `Well.add_contents(from_vessel, volume)`                       | Add contents to the well              | <ul><li>`from_vessel`: Source vessel contents</li><li>`volume`: Volume to add</li></ul>                                                                                  |
| `Well.remove_contents(volume)`                                 | Remove contents from the well         | <ul><li>`volume`: Volume to remove</li></ul>                                                                                                                             |
| `Well.update_status(new_status)`                               | Update the status of the well         | <ul><li>`new_status`: New status string</li></ul>                                                                                                                        |
| `Well.name`                                                    | Name of the well                      |                                                                                                                                                                          |
| `Well.contents`                                                | Dictionary of well contents           |                                                                                                                                                                          |
| `Well.coordinates`                                             | Coordinates dictionary                |                                                                                                                                                                          |
| `Well.x`                                                       | X-coordinate of the well              |                                                                                                                                                                          |
| `Well.y`                                                       | Y-coordinate of the well              |                                                                                                                                                                          |
| `Well.z`                                                       | Z-coordinate of the well              |                                                                                                                                                                          |
| `Well.top`                                                     | Z-coordinate of well top              |                                                                                                                                                                          |
| `Well.bottom`                                                  | Z-coordinate of well bottom           |                                                                                                                                                                          |
| `Well.volume`                                                  | Current volume in the well            |                                                                                                                                                                          |
| `Well.volume_height`                                           | Height of liquid in well              |                                                                                                                                                                          |
| `Well.status`                                                  | Current status of the well            |                                                                                                                                                                          |
| `Well.withdrawal_height`                                       | Height for withdrawing liquid         |                                                                                                                                                                          |
| `Well.top_coordinates`                                         | Coordinates object for top of well    |                                                                                                                                                                          |
| `Well.bottom_coordinates`                                      | Coordinates object for bottom of well |                                                                                                                                                                          |
| `Well.get_xyz()`                                               | Get (x,y,z) coordinates of the well   |                                                                                                                                                                          |

### Vials

Vials are used for storing solutions, samples, and waste. The system supports different types of vials with various configurations.

```python
from panda_lib.labware.vials import Vial, StockVial, WasteVial, read_vials
```

#### Vial Classes

| Class       | Description                                           |
| ----------- | ----------------------------------------------------- |
| `Vial`      | Base class for vials                                  |
| `StockVial` | Vial for stock solutions (cannot have contents added) |
| `WasteVial` | Vial for waste (can accept any contents)              |

#### Vial Methods/Properties

| Method/Property                                        | Description                             | Parameters                                                                                                                                                                   |
| ------------------------------------------------------ | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Vial(position, session_maker, create_new, vial_name)` | Constructor for vial object             | <ul><li>`position`: Position identifier</li><li>`session_maker`: Database session maker</li><li>`create_new`: Create new if True</li><li>`vial_name`: Name of vial</li></ul> |
| `Vial.add_contents(from_vessel, volume)`               | Add contents to the vial                | <ul><li>`from_vessel`: Source vessel contents</li><li>`volume`: Volume to add</li></ul>                                                                                      |
| `Vial.remove_contents(volume)`                         | Remove contents from the vial           | <ul><li>`volume`: Volume to remove</li></ul>                                                                                                                                 |
| `Vial.reset_vial()`                                    | Reset vial to default state             |                                                                                                                                                                              |
| `Vial.name`                                            | Name of the vial                        |                                                                                                                                                                              |
| `Vial.contents`                                        | Dictionary of vial contents             |                                                                                                                                                                              |
| `Vial.x`                                               | X-coordinate of the vial                |                                                                                                                                                                              |
| `Vial.y`                                               | Y-coordinate of the vial                |                                                                                                                                                                              |
| `Vial.z`                                               | Z-coordinate of the vial                |                                                                                                                                                                              |
| `Vial.top`                                             | Z-coordinate of vial top                |                                                                                                                                                                              |
| `Vial.bottom`                                          | Z-coordinate of vial bottom             |                                                                                                                                                                              |
| `Vial.volume`                                          | Current volume in the vial              |                                                                                                                                                                              |
| `Vial.capacity`                                        | Total capacity of the vial              |                                                                                                                                                                              |
| `Vial.coordinates`                                     | Coordinates object                      |                                                                                                                                                                              |
| `Vial.density`                                         | Density of vial contents                |                                                                                                                                                                              |
| `Vial.viscosity_cp`                                    | Viscosity of vial contents (centipoise) |                                                                                                                                                                              |
| `Vial.concentration`                                   | Concentration of vial contents          |                                                                                                                                                                              |
| `Vial.category`                                        | Category of vial (0=stock, 1=waste)     |                                                                                                                                                                              |
| `Vial.withdrawal_height`                               | Height for withdrawing liquid           |                                                                                                                                                                              |
| `Vial.get_xyz()`                                       | Get (x,y,z) coordinates of the vial     |                                                                                                                                                                              |

#### Vial Helper Functions

| Function                             | Description                            | Parameters                                                                                                                                 |
| ------------------------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `read_vial(name, position, session)` | Read a vial by name or position        | <ul><li>`name`: Vial name (optional)</li><li>`position`: Vial position (optional)</li><li>`session`: Database session (optional)</li></ul> |
| `read_vials(vial_group, session)`    | Read all vials of a specific group     | <ul><li>`vial_group`: "stock" or "waste"</li><li>`session`: Database session (optional)</li></ul>                                          |
| `reset_vials(category, session)`     | Reset all vials of a specific category | <ul><li>`category`: Category ID or name</li><li>`session`: Database session (optional)</li></ul>                                           |

### Labware Utilities

```python
from panda_lib.labware import get_xyz
```

| Function           | Description                               | Parameters                                                                |
| ------------------ | ----------------------------------------- | ------------------------------------------------------------------------- |
| `get_xyz(labware)` | Get XYZ coordinates from any labware type | <ul><li>`labware`: Wellplate, Well, Vial, or Coordinates object</li></ul> |

## Database Functions

The provided database functions are meant to assist in executing custom SQL queries or provide ready-made common queries to the system database. These functions are organized into several categories for different database operations.

```python
from panda_lib import sql_tools
```

### Core Database Functions

| Function                                                           | Description            | Parameters                                                                                                                 |
| ------------------------------------------------------------------ | ---------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `sql_tools.execute_query(query, fetch_all=False, fetch_one=False)` | Execute an SQL query   | <ul><li>`query`: SQL query string</li><li>`fetch_all`: Return all results</li><li>`fetch_one`: Return one result</li></ul> |
| `sql_tools.get_experiment(experiment_id)`                          | Get experiment by ID   | <ul><li>`experiment_id`: ID of the experiment</li></ul>                                                                    |
| `sql_tools.get_results(experiment_id, result_type)`                | Get experiment results | <ul><li>`experiment_id`: ID of the experiment</li><li>`result_type`: Type of results</li></ul>                             |

### Wellplate Functions

| Function                                                 | Description                             | Parameters                                                                                                                      |
| -------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `sql_tools.get_wellplate_by_id(plate_id)`                | Get wellplate by ID                     | <ul><li>`plate_id`: ID of the wellplate</li></ul>                                                                               |
| `sql_tools.get_all_wellplates()`                         | Get all wellplates                      |                                                                                                                                 |
| `sql_tools.add_wellplate(plate_type_id, barcode, label)` | Add a new wellplate                     | <ul><li>`plate_type_id`: Type ID of wellplate</li><li>`barcode`: Barcode (optional)</li><li>`label`: Label (optional)</li></ul> |
| `sql_tools.select_current_wellplate_id()`                | Get ID of current active wellplate      |                                                                                                                                 |
| `sql_tools.select_current_wellplate_info()`              | Get info about current active wellplate |                                                                                                                                 |
| `sql_tools.check_if_current_wellplate_is_new()`          | Check if current wellplate is new       |                                                                                                                                 |
| `sql_tools.check_if_plate_type_exists(type_id)`          | Check if plate type exists              | <ul><li>`type_id`: Type ID to check</li></ul>                                                                                   |
| `sql_tools.select_well_characteristics(type_id)`         | Get characteristics of a well type      | <ul><li>`type_id`: Type ID of the wellplate</li></ul>                                                                           |

### Well Functions

| Function                                                            | Description                   | Parameters                                                                                                                        |
| ------------------------------------------------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `sql_tools.get_well_by_id(well_id, plate_id)`                       | Get well by ID                | <ul><li>`well_id`: ID of the well</li><li>`plate_id`: ID of the plate (optional)</li></ul>                                        |
| `sql_tools.get_well_by_experiment_id(experiment_id)`                | Get well by experiment ID     | <ul><li>`experiment_id`: ID of the experiment</li></ul>                                                                           |
| `sql_tools.get_well_history(well_id)`                               | Get history of a well         | <ul><li>`well_id`: ID of the well</li></ul>                                                                                       |
| `sql_tools.select_well_ids(plate_id)`                               | Get IDs of wells in a plate   | <ul><li>`plate_id`: ID of the plate (optional)</li></ul>                                                                          |
| `sql_tools.select_well_status(well_id, plate_id)`                   | Get status of a well          | <ul><li>`well_id`: ID of the well</li><li>`plate_id`: ID of the plate (optional)</li></ul>                                        |
| `sql_tools.select_wellplate_wells(plate_id)`                        | Get all wells in a plate      | <ul><li>`plate_id`: ID of the plate (optional)</li></ul>                                                                          |
| `sql_tools.select_next_available_well(plate_id)`                    | Find next available well      | <ul><li>`plate_id`: ID of the plate (optional)</li></ul>                                                                          |
| `sql_tools.count_wells_with_new_status(plate_id)`                   | Count wells with 'new' status | <ul><li>`plate_id`: ID of the plate (optional)</li></ul>                                                                          |
| `sql_tools.get_number_of_wells(plate_id)`                           | Get total number of wells     | <ul><li>`plate_id`: ID of the plate (optional)</li></ul>                                                                          |
| `sql_tools.get_number_of_clear_wells(plate_id)`                     | Get number of empty wells     | <ul><li>`plate_id`: ID of the plate (optional)</li></ul>                                                                          |
| `sql_tools.save_well_to_db(well_to_save)`                           | Save a well to database       | <ul><li>`well_to_save`: Well object to save</li></ul>                                                                             |
| `sql_tools.save_wells_to_db(wells_to_save)`                         | Save multiple wells           | <ul><li>`wells_to_save`: List of well objects</li></ul>                                                                           |
| `sql_tools.insert_well(well_to_insert)`                             | Insert a new well             | <ul><li>`well_to_insert`: Well object to insert</li></ul>                                                                         |
| `sql_tools.update_well(well_to_update)`                             | Update a well                 | <ul><li>`well_to_update`: Well object with updates</li></ul>                                                                      |
| `sql_tools.update_well_status(well_id, status, plate_id)`           | Update well status            | <ul><li>`well_id`: ID of the well</li><li>`status`: New status</li><li>`plate_id`: ID of the plate (optional)</li></ul>           |
| `sql_tools.update_well_coordinates(well_id, coordinates, plate_id)` | Update well coordinates       | <ul><li>`well_id`: ID of the well</li><li>`coordinates`: New coordinates</li><li>`plate_id`: ID of the plate (optional)</li></ul> |

### Protocol Functions

| Function                                                          | Description                      | Parameters                                                                                                                                       |
| ----------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `sql_tools.select_protocols()`                                    | Get all protocols                |                                                                                                                                                  |
| `sql_tools.select_protocol(protocol_id)`                          | Get protocol by ID               | <ul><li>`protocol_id`: ID of the protocol</li></ul>                                                                                              |
| `sql_tools.select_protocol_id(protocol_name)`                     | Get protocol ID by name          | <ul><li>`protocol_name`: Name of the protocol</li></ul>                                                                                          |
| `sql_tools.select_protocol_name(protocol_id)`                     | Get protocol name by ID          | <ul><li>`protocol_id`: ID of the protocol</li></ul>                                                                                              |
| `sql_tools.insert_protocol(protocol_id, project, name, filepath)` | Insert a protocol                | <ul><li>`protocol_id`: ID for the protocol</li><li>`project`: Project name</li><li>`name`: Protocol name</li><li>`filepath`: File path</li></ul> |
| `sql_tools.update_protocol(protocol_id, new_name)`                | Update a protocol                | <ul><li>`protocol_id`: ID of the protocol</li><li>`new_name`: New name for the protocol</li></ul>                                                |
| `sql_tools.delete_protocol(protocol_id)`                          | Delete a protocol                | <ul><li>`protocol_id`: ID of the protocol to delete</li></ul>                                                                                    |
| `sql_tools.read_in_protocols()`                                   | Import protocols from filesystem |                                                                                                                                                  |

### Generator Functions

| Function                                                                            | Description                       | Parameters                                                                                                                                                                              |
| ----------------------------------------------------------------------------------- | --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sql_tools.get_generators()`                                                        | Get all generators                |                                                                                                                                                                                         |
| `sql_tools.get_generator_by_id(generator_id)`                                       | Get generator by ID               | <ul><li>`generator_id`: ID of the generator</li></ul>                                                                                                                                   |
| `sql_tools.get_generator_id(generator_name)`                                        | Get generator ID by name          | <ul><li>`generator_name`: Name of the generator</li></ul>                                                                                                                               |
| `sql_tools.get_generator_name(generator_id)`                                        | Get generator name by ID          | <ul><li>`generator_id`: ID of the generator</li></ul>                                                                                                                                   |
| `sql_tools.insert_generator(generator_id, project_id, protocol_id, name, filepath)` | Insert a generator                | <ul><li>`generator_id`: ID for the generator</li><li>`project_id`: Project ID</li><li>`protocol_id`: Protocol ID</li><li>`name`: Generator name</li><li>`filepath`: File path</li></ul> |
| `sql_tools.update_generator(generator_id, new_name)`                                | Update a generator                | <ul><li>`generator_id`: ID of the generator</li><li>`new_name`: New name for the generator</li></ul>                                                                                    |
| `sql_tools.delete_generator(generator_id)`                                          | Delete a generator                | <ul><li>`generator_id`: ID of the generator to delete</li></ul>                                                                                                                         |
| `sql_tools.read_in_generators()`                                                    | Import generators from filesystem |                                                                                                                                                                                         |
| `sql_tools.run_generator(generator_id)`                                             | Run a generator                   | <ul><li>`generator_id`: ID of the generator to run</li></ul>                                                                                                                            |

### Queue Functions

| Function                                                | Description                    | Parameters                                                           |
| ------------------------------------------------------- | ------------------------------ | -------------------------------------------------------------------- |
| `sql_tools.select_queue(project_id)`                    | Get experiments in the queue   | <ul><li>`project_id`: Filter by project ID (optional)</li></ul>      |
| `sql_tools.get_next_experiment_from_queue(random_pick)` | Get next experiment from queue | <ul><li>`random_pick`: Whether to pick randomly (optional)</li></ul> |
| `sql_tools.count_queue_length()`                        | Count experiments in queue     |                                                                      |

### System Functions

| Function                                                         | Description       | Parameters                                                                                                                                   |
| ---------------------------------------------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `sql_tools.select_system_status(look_back)`                      | Get system status | <ul><li>`look_back`: Number of status entries to look back (optional)</li></ul>                                                              |
| `sql_tools.set_system_status(system_status, comment, test_mode)` | Set system status | <ul><li>`system_status`: Status object</li><li>`comment`: Comment (optional)</li><li>`test_mode`: Boolean for test mode (optional)</li></ul> |

### Results Functions

| Function                                                                | Description           | Parameters                                                                                                       |
| ----------------------------------------------------------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `sql_tools.query_potentiostat_readouts(experiment_id, instrument_name)` | Get potentiostat data | <ul><li>`experiment_id`: ID of the experiment</li><li>`instrument_name`: Name of instrument (optional)</li></ul> |

## Utilities

```python
from panda_lib.utilities import ...
```

| Class/Function                                                                       | Description                           |
| ------------------------------------------------------------------------------------ | ------------------------------------- |
| `Coordinates`                                                                        | Class for working with 3D coordinates |
| `SystemState`                                                                        | Class for checking system state       |
| `input_validation.validate_parameter(param, param_type, min_val=None, max_val=None)` | Validate a parameter's type and range |

## Advanced Features

### Machine Learning Integration

Coming soon

## Exception Handling

The PANDA-SDL system defines several exception types for handling errors:

```python
from panda_lib.exceptions import ...
```

### Experiment Related Exceptions

| Exception                 | Description                                             |
| ------------------------- | ------------------------------------------------------- |
| `ExperimentError`         | Base exception for experiment failures                  |
| `ExperimentNotFoundError` | Raised when an experiment is not found                  |
| `ProtocolNotFoundError`   | Raised when a protocol is not found in the database     |
| `NoExperimentFromModel`   | Raised when the ML model doesn't generate an experiment |
| `DepositionFailure`       | Raised when deposition process fails                    |
| `CAFailure`               | Raised when chronoamperometry (CA) fails                |
| `CVFailure`               | Raised when cyclic voltammetry (CV) fails               |
| `OCPError`                | Raised when open circuit potential measurement fails    |
| `OCPFailure`              | Raised when OCP fails for a specific experiment/well    |

### Labware Related Exceptions

| Exception                    | Description                                              |
| ---------------------------- | -------------------------------------------------------- |
| `WellImportError`            | Raised when wellplate file has incorrect number of wells |
| `MismatchWellplateTypeError` | Raised when wellplate type doesn't match experiment      |
| `OverFillException`          | Raised when a vessel is over filled                      |
| `OverDraftException`         | Raised when more volume is removed than available        |
| `NoAvailableSolution`        | Raised when no available solution is found               |
| `InsufficientVolumeError`    | Raised when vessel doesn't have enough volume            |

### Hardware Related Exceptions

| Exception                   | Description                                |
| --------------------------- | ------------------------------------------ |
| `ImageCaptureError`         | Raised when image capture fails for a well |
| `InstrumentConnectionError` | Raised when instrument connection fails    |

### System Control Exceptions

| Exception         | Description                                  |
| ----------------- | -------------------------------------------- |
| `ShutDownCommand` | Raised when system is commanded to shut down |
| `StopCommand`     | Raised when a stop command is issued         |

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
