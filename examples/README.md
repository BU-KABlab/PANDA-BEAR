# Example Scripts

This directory contains example scripts demonstrating how to use PANDA-SDL programmatically.

## Quick Start Example

**File**: `quick_start.py`

A minimal working example showing how to:
- Set up the database
- Create an experiment
- Schedule and run it

**Usage**:
```bash
python examples/quick_start.py
```

## Running Experiments Programmatically

**File**: `run_experiment.py`

Shows how to run a single experiment by ID without using the CLI menu.

**Usage**:
```bash
python examples/run_experiment.py --experiment-id 1
```

## Creating and Running a Generator

**File**: `run_generator.py`

Demonstrates how to programmatically:
- Load a generator
- Run it to create experiments
- Execute the generated experiments

**Usage**:
```bash
python examples/run_generator.py --generator system_test
```

## Testing Mode Example

**File**: `test_with_mocks.py`

Shows how to run experiments in testing mode (with mock instruments) for validation.

**Usage**:
```bash
python examples/test_with_mocks.py
```

## Notes

- All examples assume you have:
  - Installed PANDA-SDL
  - Set up your configuration file
  - Initialized the database (`panda-db-setup`)
  - Created necessary directories (logs, data)

- Examples use testing mode by default to avoid requiring actual hardware
- Modify examples to suit your specific needs
