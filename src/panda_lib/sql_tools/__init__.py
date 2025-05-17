# filepath: e:\GitHub\PANDA\src\panda_lib\sql_tools\__init__.py
"""
PANDA SQL Tools Module

This module provides tools for interacting with the PANDA database, including:
- Database connection and session management
- ORM models for all database tables
- Helper functions for common database operations
- Query utilities for reporting and analysis

The module is organized into three main subpackages:
- models: SQLAlchemy ORM models for the database
- queries: Functions for querying and manipulating data
- utils: Utility functions for database management and testing
"""

# Core database functionality
from panda_shared.db_setup import SessionLocal, engine

# Import from restructured subpackages
from .models import (
    Base,
    ExperimentGenerators,
    ExperimentParameters,
    ExperimentResults,
    Experiments,
    ExperimentStatusView,
    PandaUnits,
    Pipette,
    PipetteLog,
    PlateTypes,
    PotentiostatReadout,
    Projects,
    Protocols,
    SlackTickets,
    SystemStatus,
    Vials,
    VialStatus,
    WellModel,
    Wellplates,
)
from .queries import (
    # Generator queries
    GeneratorEntry,  # TODO move to types
    # Protocol queries
    ProtocolEntry,  # TODO move to types
    # Queue management
    Queue,  # TODO move to types
    add_wellplate,
    check_if_current_wellplate_is_new,
    check_if_plate_type_exists,
    count_queue_length,
    count_wells_with_new_status,
    delete_generator,
    delete_protocol,
    get_all_wellplates,
    # get_experiment_results,
    # get_experiment_summary,
    get_generator_by_id,
    get_generator_id,
    get_generator_name,
    get_generators,
    get_next_experiment_from_queue,
    get_number_of_clear_wells,
    get_number_of_wells,
    get_well_by_experiment_id,
    get_well_by_id,
    get_well_history,
    # Wellplate queries
    get_wellplate_by_id,
    insert_generator,
    insert_protocol,
    insert_well,
    read_in_generators,
    read_in_protocols,
    run_generator,
    save_well_to_db,
    save_wells_to_db,
    select_current_wellplate_id,
    select_current_wellplate_info,
    select_next_available_well,
    # Protocols
    select_protocol,
    select_protocol_id,
    select_protocol_name,
    select_protocols,
    select_queue,
    # System queries
    select_system_status,
    select_well_characteristics,
    select_well_ids,
    select_well_status,
    select_wellplate_info,
    select_wellplate_wells,
    set_system_status,
    update_generator,
    update_protocol,
    update_well,
    update_well_coordinates,
    update_well_status,
)
from .utils import remove_test_experiments

# Define the public API
__all__ = [
    # Core database
    "SessionLocal",
    "engine",
    "Base",
    # Models
    "ExperimentGenerators",
    "ExperimentParameters",
    "ExperimentResults",
    "Experiments",
    "ExperimentStatusView",
    "Protocols",
    "SystemStatus",
    "Vials",
    "VialStatus",
    "WellModel",
    "Wellplates",
    "PlateTypes",
    "PotentiostatReadout",
    "SlackTickets",
    "PandaUnits",
    "Pipette",
    "PipetteLog",
    "Projects",
    # Queue management
    "Queue",
    # Reporting
    "get_experiment_results",
    "get_well_history",
    "get_experiment_summary",
    # System status
    "get_system_status",
    "update_system_status",
    # Protocol management
    "get_protocol_by_id",
    "get_all_protocols",
    "add_protocol",
    # Generator management
    "GeneratorEntry",
    "get_all_generators",
    "add_generator",
    # Wellplate management
    "get_wellplate_by_id",
    "get_all_wellplates",
    "add_wellplate",
    "get_well_by_id",
    "get_well_by_experiment_id",
    "get_well_history",
    "get_well_by_id",
    "get_well_history",
    "get_well_by_experiment_id",
    "select_well_ids",
    "select_well_status",
    "select_well_characteristics",
    "select_wellplate_info",
    "select_wellplate_wells",
    "select_current_wellplate_info",
    "select_current_wellplate_id",
    "select_next_available_well",
    "select_wells_with_new_status",
    "select_well_coordinates",
    "select_well_status",
    "select_wellplate_wells",
    "insert_well",
    "save_well_to_db",
    "save_wells_to_db",
    "update_well",
    "update_well_coordinates",
    "update_well_status",
    "check_if_current_wellplate_is_new",
    "check_if_plate_type_exists",
    "count_wells_with_new_status",
    "get_number_of_wells",
    "get_number_of_clear_wells",
    # Protocol management
    "ProtocolEntry",
    "select_protocols",
    "select_protocol",
    "select_protocol_id",
    "select_protocol_name",
    "insert_protocol",
    "update_protocol",
    "delete_protocol",
    "read_in_protocols",
    # Generator management
    "GeneratorEntry",
    "get_generators",
    "get_generator_id",
    "get_generator_name",
    "get_generator_by_id",
    "insert_generator",
    "update_generator",
    "delete_generator",
    "read_in_generators",
    "run_generator",
    # Queue management
    "Queue",
    "select_queue",
    "get_next_experiment_from_queue",
    "count_queue_length",
    # System queries
    "select_system_status",
    "set_system_status",
    # Utility functions
    "remove_test_experiments",
]


# Backwards compatibility imports
# These help existing code continue to work during migration
import warnings

warnings.warn(
    "Direct imports from individual sql_tools modules are deprecated. "
    "Please use the main sql_tools package imports instead.",
    DeprecationWarning,
    stacklevel=2,
)
