from .config_print import print_config_values, resolve_config_paths
from .config_tools import (
    get_env_var,
    get_repo_path,
    read_config,
    read_data_dir,
    read_logging_dir,
    read_testing_config,
    reload_config,
    test,
    write_testing_config,
    is_testing_mode,
)
from .test_helpers import (
    get_original_env,
    setup_test_config,
    teardown_test_config,
)

# Only resolve config paths when not in testing mode
if not is_testing_mode():
    resolve_config_paths()

__all__ = [
    "print_config_values",
    "resolve_config_paths",
    "get_env_var",
    "get_repo_path",
    "read_config",
    "read_testing_config",
    "test",
    "write_testing_config",
    "read_data_dir",
    "read_logging_dir",
    "reload_config",
    "setup_test_config",
    "teardown_test_config",
    "get_original_env",
    "is_testing_mode",
]
