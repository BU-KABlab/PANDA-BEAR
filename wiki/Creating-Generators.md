# Creating Generators

Experiment generators allow you to easily set up batches of experiments with varying parameters. Generators are Python scripts that define experiment variables and add the resulting experiments to the PANDA-SDL scheduler.

## Generator Basics

A generator is a Python script that defines the parameters for a series of experiments. Each generator must contain at least one function named `main` that creates and schedules the experiments.

Generators are typically stored in the generators directory as specified in your `config.ini` file.

## Generator Structure

Here's the basic structure of a generator file:

```python
"""
Generator: [Generator Name]
Author: [Your Name]
Date: [YYYY-MM-DD]
Description: [Brief description of the experiments this generator creates]
"""

# Import necessary modules
from panda_lib import scheduler
from panda_lib.experiments import EchemExperimentBase

# Define your experiment variables
def main():
    """Create and schedule experiments."""
    
    # Get the next available experiment ID
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    
    # Create a list to hold your experiments
    experiments = []
    
    # Define experiment parameters
    # ...
    
    # Create experiment objects
    # ...
    
    # Add experiments to the scheduler
    scheduler.add_nonfile_experiments(experiments)
    
    # Return information about the generated experiments
    return f"Generated {len(experiments)} experiments starting at ID {starting_experiment_id}"
```

## Example Generator

Here's a complete example of a generator for a parameter screening experiment:

```python
"""
Generator: Polymer Deposition Voltage Screening
Author: Your Name
Date: 2025-05-16
Description: Series of experiments for polymer deposition voltage screening with 10mm wells
"""

from panda_lib import scheduler
from panda_lib.experiments import EchemExperimentBase

# Define experiment parameters
campaign_id = 1
voltages = [1.0, 1.5, 2.0]  # Voltages to test
replicates = 3              # Number of replicates per voltage

def main():
    """Create and schedule a voltage screening experiment series."""
    
    starting_experiment_id = scheduler.determine_next_experiment_id()
    experiment_id = starting_experiment_id
    experiments = []

    for voltage in voltages:
        for i in range(replicates):
            experiments.append(
                # Define the experiment
                EchemExperimentBase(
                    experiment_id=experiment_id,
                    protocol_id="polymer_deposition_protocol.py",  # Name of your protocol file
                    well_id="A1",  # Will be automatically reassigned if unavailable
                    plate_type_number=7,  # 10 mm diameter wells on gold
                    experiment_name=f"polymer-deposition-v{voltage:.1f}-r{i+1}",
                    project_id=123,  
                    project_campaign_id=campaign_id + i,
                    
                    # Solution definitions
                    solutions={
                        "polymer_solution": {
                            "volume": 320,
                            "concentration": 1.0,
                            "repeated": 1,
                        },
                        "solventA rinse": {
                            "volume": 160,
                            "concentration": 1.0,
                            "repeated": 5,
                        },
                        "solventB rinse": {
                            "volume": 160,
                            "concentration": 1.0,
                            "repeated": 9,
                        },
                    },
                    flush_sol_name="solventB rinse",
                    rinse_sol_name="solventB rinse",
                    filename=f"{experiment_id}_polymer-deposition-v{voltage:.1f}-r{i+1}",

                    # Electrochemistry parameters
                    ocp=1,                    # Perform open circuit potential (1=yes, 0=no)
                    baseline=0,               # Perform baseline (1=yes, 0=no)
                    cv=1,                     # Perform cyclic voltammetry (1=yes, 0=no)
                    ca=1,                     # Perform chronoamperometry (1=yes, 0=no)
                    ca_sample_period=0.1,     # Sample period for CA (seconds)
                    ca_prestep_voltage=0.0,   # Prestep voltage (V)
                    ca_prestep_time_delay=0.0,# Prestep time delay (seconds)
                    ca_step_1_voltage=voltage,# Step 1 voltage (V) - our variable of interest
                    ca_step_1_time=1200,      # Step 1 time (seconds)
                    ca_step_2_voltage=0.0,    # Step 2 voltage (V)
                    ca_step_2_time=0.0,       # Step 2 time (seconds)
                    ca_sample_rate=0.5,       # Sample rate for CA (Hz)
                    
                    # Cyclic voltammetry parameters
                    cv_step_size=0.002,       # Step size for CV (V)
                    cv_first_anodic_peak=1.6, # First anodic peak (V)
                    cv_second_anodic_peak=0.0,# Second anodic peak (V)
                    cv_scan_rate_cycle_1=0.025,# Scan rate for cycle 1 (V/s)
                    cv_scan_rate_cycle_2=0.025,# Scan rate for cycle 2 (V/s)
                    cv_scan_rate_cycle_3=0.025,# Scan rate for cycle 3 (V/s)
                    cv_cycle_count=3,         # Number of cycles
                    cv_initial_voltage=0.0,   # Initial voltage (V)
                    cv_final_voltage=0.0,     # Final voltage (V)
                    cv_sample_period=0.1,     # Sample period for CV (seconds)
                    deposition_voltage=voltage,# Deposition voltage (V)
                )
            )
            experiment_id += 1

    # Add all experiments to the scheduler
    scheduler.add_nonfile_experiments(experiments)
    
    return f"Generated {len(experiments)} voltage screening experiments starting at ID {starting_experiment_id}"
```

## Experiment Parameters

When creating `EchemExperimentBase` objects, you need to specify various parameters:

### Basic Information
- `experiment_id`: Unique identifier for the experiment
- `protocol_id`: Name of the protocol file to use
- `well_id`: Well to use (can be reassigned automatically)
- `plate_type_number`: Type of wellplate to use
- `experiment_name`: Name for the experiment
- `project_id`: ID for grouping related experiments
- `project_campaign_id`: Campaign ID for experiment series

### Solutions
Defined as a dictionary of solution configurations:
```python
solutions={
    "solution_name": {
        "volume": 320,         # Volume in μL
        "concentration": 1.0,  # Concentration value
        "repeated": 1,         # Number of times used
    },
    # Additional solutions...
}
```

### Electrochemistry Parameters
Many parameters are available for configuring electrochemical experiments, such as:
- Chronoamperometry parameters (`ca_*`)
- Cyclic voltammetry parameters (`cv_*`)
- Open circuit potential parameters (`ocp_*`)

## Running Your Generator

To run your generator:

1. Start the PANDA-SDL system with `python main.py`
2. From the main menu, select option `4`, then `1` (Run experiment generator)
3. Select your generator from the list
4. The system will generate and schedule the experiments
5. Run the experiments with option `1` (Run queue)

## Best Practices

1. **Documentation**: Include a clear header with author, date, and description.

2. **Parameter Ranges**: Ensure all parameter values are within the acceptable ranges for your hardware.

3. **Resource Check**: Consider available resources (solutions, wells) when planning experiment batches.

4. **Meaningful Names**: Use descriptive names for experiments that include key parameter values.

5. **Error Handling**: Include error handling for parameter validation.

6. **Testing**: Test generators with small batches before scheduling large experiment series.

## Advanced Generator Features

### Dynamic Well Assignment

If you want to dynamically assign wells based on availability:

```python
# The well_id will be automatically reassigned if unavailable
well_id="A1"
```

### Dependent Parameters

For parameters that depend on other variables:

```python
# Example of dependent parameters
for concentration in concentrations:
    solution_volume = base_volume * concentration
    # Use solution_volume in experiment definition
```

### Complex Parameter Spaces

For more complex parameter spaces, you can use itertools:

```python
import itertools

parameters = {
    "voltage": [1.0, 1.5, 2.0],
    "concentration": [0.1, 0.5, 1.0],
    "time": [600, 1200, 1800]
}

# Create all combinations
parameter_combinations = list(itertools.product(
    parameters["voltage"],
    parameters["concentration"],
    parameters["time"]
))

# Generate experiments for all combinations
for voltage, concentration, time in parameter_combinations:
    # Create experiment with these parameters
```

## Next Steps

After creating your generator, you might want to explore:

- [Using Analyzers](Using-Analyzers.md) to process experiment results
- [Main Menu Reference](Main-Menu-Reference.md) for all available system functions
