# Quick Start Guide

This guide will get you up and running with PANDA-SDL in the fastest way possible.

## Installation (5 minutes)

### Option 1: Install from GitHub (Recommended for Users)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install PANDA-SDL
pip install git+https://github.com/BU-KABlab/PANDA-BEAR.git
```

### Option 2: Clone for Development

```bash
# Clone repository
git clone https://github.com/BU-KABlab/PANDA-BEAR.git
cd PANDA-BEAR

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Initial Setup (5 minutes)

### 1. Set Up Database

```bash
panda-db-setup
```

This creates the SQLite database with the required schema.

### 2. Create Configuration File

Create a `.env` file in your working directory:

```bash
PANDA_SDL_CONFIG_PATH=/path/to/your/config.ini
```

Create `config.ini` (copy from `config.ini.example` or `src/panda_shared/config/default_config.ini`):

```ini
[OPTIONS]
testing = True  # Start with testing mode (mock instruments)

[TESTING]
testing_db_type = sqlite
testing_db_address = test_db.db
```

### 3. Verify Installation

Run the test suite:

```bash
pytest tests/unit/ -v
```

If tests pass, your installation is working!

## Running Your First Experiment (2 minutes)

### Method 1: Using the CLI Menu

```bash
panda-cli
# Or: python main.py
```

Then:
1. Press `t` to enable testing mode (mock instruments)
2. Press `4` then `1` to run a generator
3. Select a generator (e.g., `system_test`)
4. Press `1` to run the queue

### Method 2: Using Python Scripts

```bash
# Run the quick start example
python examples/quick_start.py
```

This runs a minimal experiment in testing mode (no hardware required).

### Method 3: Programmatic Usage

```python
from panda_lib import scheduler
from panda_lib.experiments import EchemExperimentBase
from panda_lib.experiment_loop import experiment_loop_worker

# Create experiment
experiment = EchemExperimentBase(
    experiment_id=scheduler.determine_next_experiment_id(),
    protocol_name="demo",
    well_id="A1",
    wellplate_type_id=4,
    experiment_name="my_first_experiment",
    project_id=1,
    project_campaign_id=1,
    solutions={},
    ocp=0, baseline=0, cv=0, ca=0,
)

# Schedule and run
scheduler.schedule_experiments([experiment])
experiment_loop_worker(
    use_mock_instruments=True,  # Testing mode
    one_off=True,
    specific_experiment_id=experiment.experiment_id,
)
```

## Next Steps

1. **Read the Full Guide**: [Getting Started](documentation/01%20Getting-Started.md)
2. **Explore Examples**: Check `examples/` directory
3. **Write Your Own Protocol**: See [Writing Protocols](documentation/03%20Writing-Protocols.md)
4. **Create Generators**: See [Creating Generators](documentation/02%20Creating-Generators.md)

## Troubleshooting

### Database Errors
```bash
# Recreate database
panda-db-setup --force
```

### Import Errors
- Ensure virtual environment is activated
- Verify Python version is 3.10: `python --version`
- Reinstall: `pip install --force-reinstall git+https://github.com/BU-KABlab/PANDA-BEAR.git`

### Configuration Errors
- Check `.env` file exists and `PANDA_SDL_CONFIG_PATH` is set
- Verify `config.ini` file exists at the specified path
- Check logs in `logs_test/` directory

## Getting Help

- Check [Troubleshooting](README.md#troubleshooting) in README
- Review [Documentation](documentation/)
- Open an issue on [GitHub](https://github.com/BU-KABlab/PANDA-BEAR/issues)
