## Testing Configuration Issue - Solution

After analyzing the codebase, here's what's happening and how to fix it:

### Current Issues

1. **Cache Persistence**: The `read_config()` function is cached with `@lru_cache(maxsize=1)` and also uses a global `_config_cache` variable, both of which persist across test runs.

2. **Testing Mode Detection**: The testing mode is detected correctly, but the cached config may be initialized before the test environment is set up.

3. **Import Order**: Configuration modules may be imported before test fixtures run, causing initial reads to use the production config.

### Recommended Changes

1. **Modify `config_tools.py`**: Update the `read_config()` function to always reload the config in testing mode:

```python
@lru_cache(maxsize=1)
def read_config() -> ConfigParser:
    """Reads a configuration file with caching.

    Returns:
        ConfigParser object with loaded configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        PermissionError: If config file can't be accessed
    """
    global _config_cache

    config_path = get_config_path()
    logger.debug(f"Reading config from: {config_path}")

    # Always reload if in testing mode to ensure fresh config
    if is_testing_mode():
        validate_config_path(config_path)
        config = ConfigParser()
        config.read(config_path)
        # Store last modified time for cache invalidation
        config.last_modified = os.path.getmtime(config_path)
        _config_cache = config
        return config
    
    # Use normal caching logic for non-test environment
    if _config_cache is None or not hasattr(_config_cache, "last_modified"):
        validate_config_path(config_path)
        config = ConfigParser()
        config.read(config_path)
        # Store last modified time for cache invalidation
        config.last_modified = os.path.getmtime(config_path)
        _config_cache = config
    else:
        # Check if file has been modified
        current_mtime = os.path.getmtime(config_path)
        if current_mtime > _config_cache.last_modified:
            config = ConfigParser()
            config.read(config_path)
            config.last_modified = current_mtime
            _config_cache = config
    
    return _config_cache
```

2. **Enhance `reload_config()`**: Make sure it properly clears both caches:

```python
def reload_config() -> None:
    """Force reload of configuration by clearing caches"""
    global _config_cache
    _config_cache = None
    
    # Clear the lru_cache for read_config
    read_config.cache_clear()
    
    # Log that we're reloading
    logger.debug(f"Configuration reloaded from {get_config_path()}")
```

3. **Modify the testing fixture in `conftest.py`**:

```python
@pytest.fixture(scope="session", autouse=True)
def testing_config_file():
    """
    Creates a temporary testing config file for tests.
    This separates testing configuration from the local environment.
    """
    # Store original environment variables to restore later
    original_env = {}
    env_vars_to_store = [
        "PANDA_SDL_CONFIG_PATH",
        "TEMP_DB",
        "PANDA_UNIT_ID",
        "PANDA_TESTING_CONFIG_PATH",
        "PANDA_TESTING_MODE",
    ]

    for var in env_vars_to_store:
        if var in os.environ:
            original_env[var] = os.environ[var]

    # Create a temporary config file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".ini", prefix="panda_test_config_")
    os.close(temp_fd)
    
    # Write default testing configuration
    with open(temp_path, "w") as f:
        f.write("""
        # Test config content here
        """)

    # Set environment variables BEFORE importing any project modules
    os.environ["PANDA_TESTING_CONFIG_PATH"] = temp_path
    os.environ["PANDA_TESTING_MODE"] = "1"
    os.environ["PANDA_SDL_CONFIG_PATH"] = temp_path
    
    # Clear any existing configuration cache
    try:
        # Import here to ensure environment is set first
        from src.shared_utilities.config.config_tools import read_config, reload_config
        read_config.cache_clear()
        reload_config()
    except (ImportError, AttributeError) as e:
        print(f"Warning: Failed to clear config cache: {e}")

    yield temp_path

    # Clean up temporary file
    os.unlink(temp_path)
    
    # Restore original environment
    for var, value in original_env.items():
        os.environ[var] = value
    
    # Clear cache again to reset for next run
    try:
        from src.shared_utilities.config.config_tools import read_config, reload_config
        read_config.cache_clear()
        reload_config()
    except (ImportError, AttributeError) as e:
        print(f"Warning: Failed to clear config cache: {e}")
```

4. **Consider using a context manager approach**:

For more isolated tests, consider implementing a context manager that temporarily sets up a test configuration:

```python
@contextmanager
def temporary_config(config_content):
    """Context manager for temporary test configuration"""
    original_env = {}
    for var in ["PANDA_SDL_CONFIG_PATH", "PANDA_TESTING_MODE", "PANDA_TESTING_CONFIG_PATH"]:
        if var in os.environ:
            original_env[var] = os.environ[var]
    
    # Create temp file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".ini", prefix="panda_test_config_")
    os.close(temp_fd)
    
    with open(temp_path, "w") as f:
        f.write(config_content)
    
    # Set environment
    os.environ["PANDA_TESTING_CONFIG_PATH"] = temp_path
    os.environ["PANDA_TESTING_MODE"] = "1"
    os.environ["PANDA_SDL_CONFIG_PATH"] = temp_path
    
    # Clear cache
    from src.shared_utilities.config.config_tools import read_config, reload_config
    read_config.cache_clear()
    reload_config()
    
    try:
        yield temp_path
    finally:
        # Cleanup
        os.unlink(temp_path)
        for var, value in original_env.items():
            os.environ[var] = value
        
        read_config.cache_clear()
        reload_config()
```

5. **Add debugging to investigate issues**:

Add temporary print statements to see which config file is being used:

```python
# In read_config:
config_path = get_config_path()
print(f"DEBUG: Reading config from {config_path}, testing mode: {is_testing_mode()}")

# In get_config_path:
if is_testing_mode():
    test_config_path = os.getenv("PANDA_TESTING_CONFIG_PATH")
    print(f"DEBUG: Test mode active, config path from env: {test_config_path}")
```

### Additional Recommendations

1. Ensure all modules that import `read_config` do so AFTER the test configuration is set up.

2. Consider implementing better dependency injection for configuration to make testing easier.

3. Move away from global state/caching in the configuration system to improve testability.
