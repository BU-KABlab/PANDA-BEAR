# Test Restructuring Plan

## Current Structure
Currently, tests are mostly organized in flat files at the root of the tests directory, with some grouping in subdirectories.

## New Structure
The new structure will mirror the main components of panda_lib:

```
tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── actions/
│   │   ├── __init__.py
│   │   ├── test_electrochemistry.py
│   │   ├── test_imaging.py
│   │   ├── test_movement.py
│   │   └── test_pipetting.py
│   ├── hardware/
│   │   ├── __init__.py
│   │   ├── test_arduino_interface.py
│   │   ├── test_gantry_interface.py
│   │   └── imaging/
│   │       ├── __init__.py
│   │       └── test_camera.py
│   ├── labware/
│   │   ├── __init__.py
│   │   ├── test_vials.py
│   │   ├── test_wellplates.py
│   │   └── test_services.py
│   ├── sql_tools/
│   │   ├── __init__.py
│   │   ├── test_db_setup.py
│   │   └── test_sql_utilities.py
│   ├── experiments/
│   │   ├── __init__.py
│   │   └── test_experiment_loop.py
│   └── utilities/
│       ├── __init__.py
│       └── test_utilities.py
├── integration/
│   ├── __init__.py
│   ├── test_toolkit.py
│   ├── test_experiment_workflow.py
│   └── test_scheduler.py
└── config/
    ├── __init__.py
    ├── config_fixtures.py
    └── test_config_interface.py
```

## Migration Steps

1. Create the new directory structure
2. Move existing tests to appropriate locations
3. Update imports if necessary
4. Create missing `__init__.py` files
5. Run tests to ensure everything still works

## Test Naming Conventions

- Test files should be named `test_<module_name>.py`
- Test functions should be named `test_<function_name>` or `test_<function_name>_<scenario>`
- Test classes should be named `Test<ClassName>`

## Additional Recommendations

- Add more specific tests for major components
- Increase test coverage for critical functionality
- Add integration tests to ensure components work together correctly
- Use fixtures for common setup and teardown operations
