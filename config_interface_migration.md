# Configuration Interface Migration Guide

This guide helps you migrate from the old `config_tools.py` module to the new `config_interface.py` configuration system.

## Why Migrate?

The new configuration interface provides several benefits:

1. **Better Testing Support**: Easier to mock and replace configuration during tests
2. **Cleaner API**: More consistent methods and error handling
3. **Type Safety**: Better type annotations and more explicit return types
4. **Dependency Injection**: Classes can accept configuration objects directly
5. **No Caching Issues**: Avoids the problems with LRU cache and global state

## Migration Steps

### Step 1: Update Imports

Replace imports from `config_tools.py` with imports from `config_interface.py`:

```python
# Old imports
from src.shared_utilities.config.config_tools import read_config, read_config_value

# New imports
from src.shared_utilities.config.config_interface import get_config
```

### Step 2: Replace Function Calls

| Old Function                                     | New Function                                    | Notes                                                      |
| ------------------------------------------------ | ----------------------------------------------- | ---------------------------------------------------------- |
| `read_config()`                                  | `get_config()`                                  | Returns a ConfigInterface instance instead of ConfigParser |
| `read_config_value(section, key, default)`       | `get_config().get(section, key, default)`       | Same behavior                                              |
| `read_config_value_int(section, key, default)`   | `get_config().get_int(section, key, default)`   | Same behavior                                              |
| `read_config_value_float(section, key, default)` | `get_config().get_float(section, key, default)` | Same behavior                                              |
| `read_config_value_bool(section, key, default)`  | `get_config().get_bool(section, key, default)`  | Same behavior                                              |
| `get_config_path()`                              | `get_config().get_config_path()`                | Same behavior                                              |
| `reload_config()`                                | `reset_config()`                                | Similar behavior                                           |

### Step 3: Update Access Patterns

```python
# Old way
config = read_config()
value = config.get("SECTION", "key", fallback="default")

# New way
config = get_config()
value = config.get("SECTION", "key", "default")
```

### Step 4: Update Class-Based Code

For classes that need configuration, consider using dependency injection:

```python
# Old way
class MyClass:
    def __init__(self):
        self.config = read_config()
        self.value = self.config.get("SECTION", "key")

# New way
class MyClass:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.value = self.config.get("SECTION", "key")
```

This makes your classes more testable because you can inject a mock configuration.

### Step 5: Update Tests

Use the new testing utilities in your tests:

```python
# Old way (creating test config file)
with tempfile.NamedTemporaryFile() as temp:
    # Write config
    temp.write(b"[SECTION]\nkey=value\n")
    temp.flush()
    
    # Set environment variables
    os.environ["PANDA_TESTING_CONFIG_PATH"] = temp.name
    os.environ["PANDA_TESTING_MODE"] = "1"
    reload_config()
    
    # Run test...

# New way (using fixtures)
def test_with_config(patch_global_config):
    # patch_global_config fixture handles everything
    assert get_config().get("PANDA", "unit_id") == "99"
    
# Alternative new way (using manual config)
def test_with_custom_config():
    from src.shared_utilities.config.config_interface import create_test_config
    
    # Create test config
    test_config = create_test_config({
        "SECTION": {"key": "value"}
    })
    
    # Use in test or inject into class
    my_instance = MyClass(config=test_config)
    assert my_instance.value == "value"
```

## Complete Example

```python
# Before
from src.shared_utilities.config.config_tools import read_config, read_config_value

def get_mill_port():
    return read_config_value("MILL", "port", "COM1")

class MillController:
    def __init__(self):
        self.config = read_config()
        self.port = self.config.get("MILL", "port")
        self.baudrate = int(self.config.get("MILL", "baudrate", fallback="9600"))
```

```python
# After
from src.shared_utilities.config.config_interface import get_config

def get_mill_port():
    return get_config().get("MILL", "port", "COM1")

class MillController:
    def __init__(self, config=None):
        self.config = config or get_config()
        self.port = self.config.get("MILL", "port")
        self.baudrate = self.config.get_int("MILL", "baudrate", 9600)
```

## Testing Examples

### Testing Functions

```python
# Test a function that uses configuration
def test_get_mill_port(patch_global_config):
    # The patch_global_config fixture sets up a test config
    assert get_mill_port() == "MOCK_PORT"
```

### Testing Classes

```python
# Test a class that uses configuration
def test_mill_controller():
    # Create a test configuration
    test_config = create_test_config({
        "MILL": {
            "port": "TEST_PORT",
            "baudrate": "115200"
        }
    })
    
    # Inject the test configuration
    controller = MillController(config=test_config)
    
    # Verify it used our test values
    assert controller.port == "TEST_PORT"
    assert controller.baudrate == 115200
```

## Need Help?

If you encounter any issues during migration, please refer to the example code in:
- `src/shared_utilities/examples/config_example.py`
- `tests/config/test_config_example.py`

These files demonstrate the recommended patterns for using the new configuration interface.
