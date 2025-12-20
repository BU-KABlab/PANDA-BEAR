# Developer Guide

Essential information for developers contributing to or extending PANDA-SDL functionality.

**Navigation**: [Home](00-Home.md) | Developer Guide | [Code Architecture](Code-Architecture.md) | [Contributing](Contributing.md) | [API Reference](API-Reference.md)

## Table of Contents

- [Project Architecture](#project-architecture)
- [Development Environment Setup](#development-environment-setup)
- [Code Organization](#code-organization)
- [Testing](#testing)
- [Next Steps](#next-steps)

## Project Architecture

The PANDA-SDL system is organized into several key components:

### Core Libraries

- **panda_lib**: The main library containing the core functionality
  - **actions**: Functions for performing robot actions (fluid handling, imaging, electrochemistry)
  - **experiments**: Experiment data structures and management
  - **hardware**: Hardware drivers and interfaces
  - **labware**: Labware definitions (wellplates, vials)
  - **utilities**: Helper functions and utilities

- **panda_lib_cli**: Command-line interface for the PANDA system
  - **menu**: Main menu and UI components

- **panda_lib_db**: Database management and SQL operations

- **panda_shared**: Shared utilities across multiple components
  - **config**: Configuration management
  - **logging**: Logging utilities

### User Content

- **panda_experiment_protocols**: User-defined experiment protocols
- **panda_experiment_generators**: User-defined experiment generators
- **panda_experiment_analyzers**: User-defined analyzers for experiment results

### Additional Components

- **tests**: Unit and integration tests
- **validation_scripts**: System validation tools
- **documentation**: User and developer documentation

## Development Environment Setup

### Setting Up for Development

1. **Clone the repository**:

   ```bash
   git clone https://github.com/BU-KABlab/PANDA-SDL.git
   cd PANDA-SDL
   ```

2. **Create a development environment**:

   Linux/MacOS Systems

   ```bash
   # Using UV (recommended)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv sync --reinstall

   # Using Pip
   python -m venv panda_sdl_dev
   panda_sdl_dev\Scripts\activate
   pip install -r requirements.txt
   pip install -e .  # Install in development mode
   ```

   Windows Powershell

   ```powershell
   # Using UV (recommended)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   uv sync --reinstall
   
   # Or using pip
   python -m venv panda_sdl_dev
   panda_sdl_dev\Scripts\activate
   pip install -r requirements.txt
   pip install -e .  # Install in development mode
   ```

3. **Configure for development**:
   - Create a `.env` file with development settings:

     ```env
     PANDA_SDL_CONFIG_PATH = path/to/dev_config.ini
     TEMP_DB='1'  # Use a separate test database
     ```

   - Create a development config file based on the template
   - Install any third party SDKs such as the FLIR SDK if applicable

### Development Tools

The project uses several development tools:

- **Ruff**: For code linting and formatting
- **Pytest**: For unit and integration testing
- **UV**: For dependency management

To install development tools:

```powershell
uv pip install ruff pytest pytest-cov
```

## Contributing Code

### Coding Standards

The PANDA-SDL project follows these coding standards:

1. **PEP 8**: Follow the Python style guide
2. **Type Hints**: Include type hints for function parameters and return values
3. **Docstrings**: Document all classes and functions with clear docstrings
4. **Modular Design**: Keep functions and classes focused on a single responsibility
5. **Error Handling**: Use appropriate error handling and provide informative error messages

### Development Workflow

1. **Create a feature branch**:

   ```powershell
   git checkout -b feature/your-feature-name
   ```

2. **Write tests**:
   - Create unit tests for new functionality in `tests/unit/`
   - Create integration tests in `tests/integration/` if needed

3. **Implement your changes**:
   - Follow the coding standards
   - Ensure backward compatibility when possible
   - Update documentation as needed

4. **Run tests**:

   ```powershell
   pytest tests/
   ```

5. **Check code quality**:

   ```powershell
   ruff check .
   ```

6. **Submit a pull request**:
   - Provide a clear description of the changes
   - Reference any relevant issues
   - Ensure all tests pass

## Extending the System

### Adding New Hardware Support

To add support for new hardware:

1. Create a new module in `panda_lib/hardware/`
2. Implement the appropriate interface for the hardware type
3. Add configuration options in `panda_shared/config/default_config.ini`
4. Update the hardware initialization in `panda_lib/toolkit.py`

### Creating New Actions

To create new actions:

1. Add the new action function to `panda_lib/actions.py` or create a new actions module (e.g., `panda_lib/actions_custom.py`)
2. Ensure your action follows the standard pattern:
   - Takes a toolkit as a parameter
   - Properly handles errors
   - Logs its operations
   - Returns appropriate results

Example:

```python
def my_custom_action(toolkit, param1, param2=None):
    """
    Perform a custom action.
    
    Args:
        toolkit: The system toolkit
        param1: First parameter
        param2: Second parameter (optional)
        
    Returns:
        Result of the action
    """
    toolkit.global_logger.info(f"Performing custom action with {param1}")
    
    # Implement action logic
    
    toolkit.global_logger.info("Custom action completed")
    return result
```

### Modifying the Database Schema

If you need to modify the database schema:

1. Update the SQL scripts in `sql_scripts/`
2. Create a migration script if needed for existing installations
3. Update any affected SQL queries in `panda_lib_db/`
4. Update relevant data models in `panda_lib/experiments.py`

## Testing

### Unit Testing

The project uses pytest for testing. Unit tests should be placed in `tests/unit/`:

```python
# tests/unit/test_my_feature.py
import pytest
from panda_lib import my_module

def test_my_function():
    # Arrange
    input_data = "test"
    
    # Act
    result = my_module.my_function(input_data)
    
    # Assert
    assert result == expected_output
```

### Integration Testing

Integration tests should be placed in `tests/integration/`:

```python
# tests/integration/test_my_integration.py
import pytest
from panda_lib import Toolkit

@pytest.fixture
def toolkit():
    # Setup a test toolkit
    toolkit = Toolkit(testing=True)
    yield toolkit
    # Cleanup
    toolkit.disconnect_all()

def test_integration_scenario(toolkit):
    # Test an integration scenario
    assert toolkit.some_integration_test() == expected_result
```

### Running Tests

To run all tests:

```powershell
pytest
```

To run specific tests:

```powershell
pytest tests/unit/test_my_feature.py
```

To run tests with coverage:

```powershell
pytest --cov=panda_lib
```

## Documentation

### Updating Documentation

When making changes:

1. Update docstrings in the code
2. Update relevant markdown files in `documentation/`
3. Update the wiki if applicable

### Building Documentation

The project uses markdown for documentation. No special build process is required.

## Deployment

### Packaging for Distribution

To create a distributable package:

```powershell
# Using UV
uv pip install build
python -m build

# Or using pip
pip install build
python -m build
```

This will create both source distribution (.tar.gz) and wheel (.whl) files in the `dist/` directory.

## Debugging

### Logging

The PANDA system uses Python's logging module. Logs are stored in the `logs_test/` directory:

- `panda.log`: Main system log
- `experiment_logger.log`: Experiment execution log
- `camera.log`: Camera operations log
- `scheduler.log`: Experiment scheduling log
- `sql_logger.log`: Database operations log
- `timing.log`: Performance timing log
- `vessel.log`: Vessel operations log

### Common Issues

1. **Hardware Communication Errors**:
   - Check physical connections
   - Verify correct port configuration in config.ini
   - Look for specific errors in the logs

2. **Database Issues**:
   - Check SQL queries for syntax errors
   - Verify database schema matches expected structure
   - Inspect SQL logs for detailed error messages

3. **Experiment Execution Problems**:
   - Enable testing mode for isolated debugging
   - Check experiment_logger.log for detailed execution trace
   - Verify experiment parameters are within valid ranges

## Next Steps

As a developer, you might want to explore:

- [Code Architecture](Code-Architecture.md) for detailed system architecture information
- [API Reference](API-Reference.md) for complete API documentation
- [Contributing](Contributing.md) for contribution guidelines and best practices
- [Build Guide](Build-Guide.md) to understand the physical system design
