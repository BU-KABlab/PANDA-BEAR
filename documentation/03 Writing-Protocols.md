# Writing Protocols

Protocols define the sequence of actions executed during a PANDA-BEAR experiment. Each protocol specifies the steps performed by the system, from solution preparation through data collection.

**Navigation**: [Home](00-Home.md) | [Getting Started](01%20Getting-Started.md) | Writing Protocols | [Creating Generators](02%20Creating-Generators.md) | [Using Analyzers](04%20Using-Analyzers.md)

## Table of Contents

- [Protocol Basics](#protocol-basics)
- [Protocol Structure](#protocol-structure)
- [Available Actions](#available-actions)
- [Testing Your Protocol](#testing-your-protocol)
- [Best Practices](#best-practices)
- [Next Steps](#next-steps)

## Protocol Basics

A protocol is a Python script that defines the sequence of actions to be performed during an experiment. Each protocol must contain at least one function named `run` that accepts an experiment object and a toolkit object.

Protocols are stored in the protocols directory as specified in your `config.ini` file.

## Protocol Structure

Here's the basic structure of a protocol file:

```python
"""
Protocol: [Protocol Name]
Author: [Your Name]
Date: [YYYY-MM-DD]
Description: [Brief description of what this protocol does]
"""

# Import necessary modules
from panda_lib import Toolkit
from panda_lib.actions import (
    chrono_amp,
    clear_well,
    flush_pipette,
    image_well,
    rinse_well,
    transfer,
)
from panda_lib.experiments import EchemExperimentBase
from panda_lib.labware.wellplates import Well

# Optional: Create helper classes if needed
from dataclasses import dataclass

@dataclass
class Solution:
    name: str
    volume: int
    concentration: float
    repeated: int

def run(experiment, toolkit):
    """Run the experiment."""
    
    # Your experiment steps go here
    
    # Log the start of the experiment
    toolkit.global_logger.info(f"Running experiment: {experiment.experiment_name}")
    
    # Implement your experiment logic
    # ...
    
    # Log the end of the experiment
    toolkit.global_logger.info("Experiment complete")
```

## Available Actions

PANDA-BEAR provides a set of predefined actions that you can use in your protocols:

### Fluid Handling
- `transfer(volume, solution_name, destination_well, toolkit)` - Transfers a solution to a well
- `clear_well(toolkit, well)` - Removes all contents from a well
- `flush_pipette(flush_with, toolkit)` - Cleans the pipette
- `rinse_well(instructions, toolkit, alt_sol_name, alt_vol, alt_count)` - Rinses a well with a solution

### Imaging
- `image_well(toolkit, experiment, image_label)` - Takes an image of a well

### Electrochemistry
- `chrono_amp(toolkit, experiment, well)` - Performs chronoamperometry
- `cyclic_volt(toolkit, experiment, well)` - Performs cyclic voltammetry
- `open_circuit_potential(toolkit, experiment, well)` - Measures open circuit potential

## Complete Example Protocol

Here's a complete example protocol for an electrochemical deposition experiment:

```python
from dataclasses import dataclass

from panda_lib import Toolkit
from panda_lib.actions import (
    chrono_amp,
    clear_well,
    flush_pipette,
    image_well,
    rinse_well,
    transfer,
)
from panda_lib.experiments import EchemExperimentBase
from panda_lib.labware.wellplates import Well

@dataclass
class Solution:
    name: str
    volume: int
    concentration: float
    repeated: int

def run(exp, toolkit):
    """Run the electrochemical deposition experiment."""

    # Log the start of the experiment
    toolkit.global_logger.info("Running experiment: " + exp.experiment_name)
    
    # Define solution for easier reference
    solution = Solution(
        "polymer_solution",
        exp.solutions["polymer_solution"]["volume"],
        exp.solutions["polymer_solution"]["concentration"],
        exp.solutions["polymer_solution"]["repeated"],
    ) 

    # Get the well we are working with
    well = toolkit.wellplate.get_well(exp.well_id)

    # Take initial image of the empty well
    image_well(toolkit, exp, "Empty Well")

    # Transfer solution to the well
    transfer(solution.volume, solution.name, well, toolkit)
    
    # Take image of the well with solution
    image_well(toolkit, exp, "Well with Solution")

    # Perform chronoamperometry to deposit the polymer
    chrono_amp(toolkit, exp, well)
    
    # Take image of the well after deposition
    image_well(toolkit, exp, "After Deposition")

    # Clear the well contents
    clear_well(toolkit, well)

    # Rinse the well
    rinse_well(
        instructions=exp,
        toolkit=toolkit,
    )

    # Flush the pipette to reduce contamination
    flush_pipette(
        flush_with=exp.flush_sol_name,
        toolkit=toolkit,
    )

    # Take final image
    image_well(toolkit, exp, "Final Well")

    # Log the completion of the experiment
    toolkit.global_logger.info("Experiment complete")
```

## Best Practices

1. **Documentation**: Always include a header with your name, date, and a description of what the protocol does.

2. **Error Handling**: Implement try/except blocks for critical operations to gracefully handle errors.

3. **Logging**: Use the toolkit's logger to record important events and status information.

4. **Modularity**: Break complex operations into separate functions for better readability and reusability.

5. **Validation**: Include checks to ensure experimental parameters are within acceptable ranges.

6. **Comments**: Add comments to explain the purpose of each major section or complex operation.

## Testing Your Protocol

Before running your protocol on the actual hardware:

1. Enable testing mode in the main menu (option `t`) to use virtual instruments
2. Validate your protocol with the virtual instruments first
3. Check logs in the `logs_test/` directory for any issues

## Next Steps

Once you've created your protocol, you'll need a [generator](02%20Creating-Generators.md) to define the specific parameters for your experiment series. You may also want to create an [analyzer](04%20Using-Analyzers.md) to process the results from experiments using your protocol.
