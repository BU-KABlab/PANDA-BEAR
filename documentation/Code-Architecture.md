# Code Architecture

This document provides an overview of the PANDA-SDL codebase architecture, explaining the key components and their relationships. Understanding this architecture will help developers navigate the codebase and make effective contributions.

## High-Level Architecture

The PANDA-SDL system is organized into several key components:

```
┌───────────────────────────────────────────────────────────────┐
│                        User Interface                         │
│                       (panda_lib_cli)                         │
└───────────────────────────────┬───────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                      Core Library (panda_lib)                 │
├───────────────┬──────────────┬─────────────────┬──────────────┤
│    Actions    │   Toolkit    │   Experiments   │   Hardware   │
└───────┬───────┴──────┬───────┴────────┬────────┴───────┬──────┘
        │              │                │                │
┌───────▼───────┐ ┌────▼────┐   ┌───────▼───────┐ ┌──────▼──────┐
│  Protocols    │ │ Database│   │   Generators  │ │  Analyzers  │
└───────────────┘ └─────────┘   └───────────────┘ └─────────────┘
```

## Core Components

### 1. panda_lib

The central library containing all core functionality:

- **actions.py**: Core functions for robot actions (fluid handling, imaging, etc.)
- **experiments.py**: Experiment data structures and management
- **toolkit.py**: Main interface for accessing system capabilities
- **hardware/**: Hardware drivers and interfaces
- **utilities/**: Helper functions and classes
- **labware/**: Definitions for labware (wellplates, vials)

### 2. panda_lib_cli

The command-line interface for interacting with the system:

- **menu/**: Main menu and UI components
- **main_menu.py**: Entry point for the CLI

### 3. panda_lib_db

Database interaction layer:

- **sql_tools.py**: Functions for database operations
- **models/**: Database models and schemas

### 4. panda_shared

Shared utilities used across the project:

- **config/**: Configuration management
- **logging/**: Logging utilities

## User Content

### 1. panda_experiment_protocols

User-defined experiment protocols:

- Protocol files (*.py) defining experiment workflows
- Each protocol must have a `run(experiment, toolkit)` function

### 2. panda_experiment_generators

User-defined experiment generators:

- Generator files (*.py) for creating experiment batches
- Each generator must have a `main()` function

### 3. panda_experiment_analyzers

User-defined analysis modules:

- Analyzer files (*.py) for processing experiment results
- Often includes visualization and data processing

## Control Flow

### Experiment Execution Flow

```
┌───────────┐    ┌────────────┐    ┌─────────────┐    ┌─────────┐
│ Generator │───►│ Scheduler  │───►│ Experiment  │───►│Protocol │
│ (defines  │    │ (queues    │    │ Worker      │    │ (runs   │
│  params)  │    │  exps)     │    │ (executes)  │    │  steps) │
└───────────┘    └────────────┘    └─────────────┘    └─────────┘
                                          │
                                          ▼
┌───────────┐    ┌────────────┐    ┌─────────────┐
│ Analyzer  │◄───│ Analysis   │◄───│ Results     │
│ (processes│    │ Worker     │    │ Database    │
│  results) │    │ (processes)│    │ (stores)    │
└───────────┘    └────────────┘    └─────────────┘
```

1. **Generator**: Creates experiment definitions with specific parameters
2. **Scheduler**: Adds experiments to the queue and manages execution order
3. **Experiment Worker**: Executes experiments from the queue
4. **Protocol**: Defines the sequence of actions for an experiment
5. **Results Database**: Stores experiment results
6. **Analysis Worker**: Processes completed experiments
7. **Analyzer**: Analyzes results and may generate new experiments

### Action Execution Flow

```
┌───────────┐    ┌────────────┐    ┌─────────────┐
│ Protocol  │───►│ Action     │───►│ Toolkit     │
│ (calls    │    │ Function   │    │ (hardware   │
│  actions) │    │ (wrapper)  │    │  interface) │
└───────────┘    └────────────┘    └─────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │ Hardware    │
                                   │ Drivers     │
                                   │             │
                                   └─────────────┘
```

1. **Protocol**: Calls action functions with experiment parameters
2. **Action Function**: Wrapper that orchestrates hardware operations
3. **Toolkit**: Provides interfaces to hardware components
4. **Hardware Drivers**: Communicate directly with physical devices

## Key Subsystems

### Database Subsystem

The database stores all experiment data, results, and system configuration:

- **Experiments**: Experiment definitions and parameters
- **Results**: Experimental results (electrochemical data, images)
- **Labware**: Wellplate and vial information
- **System State**: Current state of the system

Database interactions are handled primarily through `sql_tools.py`.

### Hardware Subsystem

Hardware components are abstracted through driver classes:

- **Potentiostat**: Electrochemical measurements
- **Camera**: Imaging system
- **Pipette**: Fluid handling
- **Motion System**: XYZ movement control

Hardware drivers implement common interfaces and are accessed through the `Toolkit` class.

### Experimental Subsystem

Manages the definition, execution, and analysis of experiments:

- **Experiment Classes**: Define experiment parameters
- **Scheduler**: Manages experiment queue
- **Experiment Worker**: Executes experiments
- **Analysis Worker**: Processes results

## File Structure

```
PANDA-SDL/
├── main.py                      # Main entry point
├── documentation/               # Documentation files
├── panda_experiment_analyzers/  # User-defined analyzers
├── panda_experiment_generators/ # User-defined generators
├── panda_experiment_protocols/  # User-defined protocols
├── sql_scripts/                 # Database scripts
├── src/                         # Source code
│   ├── panda_lib/               # Main library
│   ├── panda_lib_cli/           # CLI interface
│   ├── panda_lib_db/            # Database functionality
│   └── panda_shared/            # Shared utilities
├── tests/                       # Test suite
└── validation_scripts/          # Validation tools
```

## Design Patterns

The PANDA-SDL codebase utilizes several design patterns:

### 1. Facade Pattern

The `Toolkit` class serves as a facade, providing a simplified interface to the complex subsystems of hardware, database, and utilities.

```python
# Example of the Facade pattern
class Toolkit:
    def __init__(self):
        self.camera = Camera()
        self.potentiostat = Potentiostat()
        self.pipette = Pipette()
        # ...

    def take_image(self, params):
        # Simplified interface to camera functionality
        return self.camera.capture_image(params)
```

### 2. Factory Pattern

The experiment system uses a factory pattern to create different types of experiments:

```python
# Example of Factory pattern
def create_experiment(experiment_type, params):
    if experiment_type == "echem":
        return EchemExperimentBase(**params)
    elif experiment_type == "imaging":
        return ImagingExperiment(**params)
    # ...
```

### 3. Observer Pattern

The system uses an observer pattern for events and notifications:

```python
# Example of Observer pattern
class ExperimentWorker:
    def __init__(self):
        self.observers = []
        
    def add_observer(self, observer):
        self.observers.append(observer)
        
    def notify_all(self, event):
        for observer in self.observers:
            observer.update(event)
```

## Extension Points

The system is designed with several extension points:

### 1. Custom Actions

New actions can be added by creating functions in `panda_lib/actions.py` or in custom action modules:

```python
# Example of a custom action
def my_custom_action(toolkit, param1, param2):
    """Custom action documentation."""
    # Implementation
    return result
```

### 2. Hardware Drivers

New hardware support can be added by implementing driver classes in `panda_lib/hardware/`:

```python
# Example of a hardware driver
class MyNewDevice:
    def __init__(self, config):
        # Initialize hardware
        
    def connect(self):
        # Connect to device
        
    def perform_operation(self, params):
        # Perform device-specific operation
```

### 3. Experiment Types

New experiment types can be created by extending base experiment classes:

```python
# Example of a custom experiment type
class MyExperimentType(ExperimentBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.custom_param = kwargs.get("custom_param")
```

## Best Practices for Development

When working with the PANDA-SDL codebase:

1. **Follow the existing patterns**: Maintain consistency with the existing architecture
2. **Use abstraction layers**: Don't bypass the toolkit to access hardware directly
3. **Maintain backward compatibility**: Avoid breaking changes to APIs
4. **Document thoroughly**: Add clear docstrings to all new code
5. **Write tests**: Include tests for new functionality
6. **Handle errors appropriately**: Use proper error handling and reporting

## Future Architectural Directions

Areas being considered for future development:

1. **More modular hardware abstraction**: Further decoupling hardware interfaces
2. **Plugin system**: Support for third-party plugins
3. **Web interface**: Additional user interface options
4. **Improved parallel processing**: Enhanced support for parallel experiment execution
5. **Machine learning integration**: Deeper integration with ML frameworks

## Additional Resources

For more detailed information:

- Source code docstrings
- [Developer Guide](Developer-Guide.md)
- [API Reference](API-Reference.md)
