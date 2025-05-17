"""
SQL Tools Queries Package

This package contains all the database query functions for the PANDA database.
"""

# from .experiments import get_experiment_results, get_experiment_summary
from .generators import (
    GeneratorEntry,
    delete_generator,
    get_generator_by_id,
    get_generator_id,
    get_generator_name,
    get_generators,
    insert_generator,
    read_in_generators,
    run_generator,
    update_generator,
)
from .protocols import (
    ProtocolEntry,
    delete_protocol,
    insert_protocol,
    read_in_protocols,
    select_protocol,
    select_protocol_id,
    select_protocol_name,
    select_protocols,
    update_protocol,
)
from .queue import (
    Queue,
    count_queue_length,
    get_next_experiment_from_queue,
    select_queue,
)
from .system import select_system_status, set_system_status
from .wellplates import (
    add_wellplate,
    check_if_current_wellplate_is_new,
    check_if_plate_type_exists,
    count_wells_with_new_status,
    get_all_wellplates,
    get_number_of_clear_wells,
    get_number_of_wells,
    get_well_by_experiment_id,
    get_well_by_id,
    get_well_history,
    get_wellplate_by_id,
    insert_well,
    save_well_to_db,
    save_wells_to_db,
    select_current_wellplate_id,
    select_current_wellplate_info,
    select_next_available_well,
    select_well_characteristics,
    select_well_ids,
    select_well_status,
    select_wellplate_info,
    select_wellplate_wells,
    update_well,
    update_well_coordinates,
    update_well_status,
)

__all__ = [
    # Experiment queries
    "get_experiment_results",
    "get_experiment_summary",
    # Wellplate queries
    "get_wellplate_by_id",
    "get_all_wellplates",
    "add_wellplate",
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
    # Protocol queries
    "ProtocolEntry",  # TODO move to types
    "select_protocols",
    "select_protocol",
    "select_protocol_id",
    "select_protocol_name",
    "insert_protocol",
    "update_protocol",
    "delete_protocol",
    "read_in_protocols",
    # Generator queries
    "GeneratorEntry",  # TODO move to types
    "get_generators",
    "get_generator_id",
    "get_generator_name",
    "get_generator_by_id",
    "insert_generator",
    "update_generator",
    "delete_generator",
    "read_in_generators",
    "run_generator",
    # System queries
    "select_system_status",
    "set_system_status",
    # Queue management
    "Queue",  # TODO move to types
    "select_queue",
    "get_next_experiment_from_queue",
    "count_queue_length",
]
