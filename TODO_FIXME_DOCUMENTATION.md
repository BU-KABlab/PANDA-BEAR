# TODO and FIXME Documentation

This document catalogs all TODO and FIXME comments in the codebase with analysis and suggestions for resolution.

## Summary Statistics

- **Total TODO/FIXME comments**: ~288 instances
- **Critical issues**: ~15
- **Code cleanup**: ~50
- **Documentation**: ~30
- **Debug/logging**: ~193 (mostly DEBUG logging, not actual issues)

## Critical Issues (High Priority)

### 1. Toolkit Stock/Waste Vials Property

**Location**: `src/panda_lib/toolkit.py:180, 184`

```python
@property
def stock_vials(self) -> list[StockVial]:
    return read_vials("stock")[0]  # TODO: Fix this

@property
def waste_vials(self) -> list[WasteVial]:
    return read_vials("waste")[0]  # TODO: Fix this
```

**Issue**: Returns first element of tuple, unclear what the tuple contains.

**Suggestion**:
```python
@property
def stock_vials(self) -> list[StockVial]:
    vials, _ = read_vials("stock")  # Unpack tuple explicitly
    return vials

@property
def waste_vials(self) -> list[WasteVial]:
    vials, _ = read_vials("waste")  # Unpack tuple explicitly
    return vials
```

**Action**: Check `read_vials()` return signature and fix accordingly.

---

### 2. OT2 Pipette Driver from_config Method

**Location**: `src/panda_lib/hardware/panda_pipettes/ot2_pipette/pipette_driver.py:128`

```python
#TODO fix this whole thing because it DOES NOT WORK.
```

**Issue**: Method marked as non-functional.

**Suggestion**:
- **Option A**: Remove the method if it's not used
- **Option B**: Fix the implementation by:
  1. Verifying JSON config file format
  2. Testing with actual hardware
  3. Adding proper error handling
  4. Updating documentation

**Action**: Check if this method is called anywhere. If unused, remove. If used, investigate and fix.

---

### 3. OT2 Pipette Deprecated Functions

**Location**: `src/panda_lib/hardware/panda_pipettes/ot2_pipette/pipette_driver.py:312, 332`

```python
):  # TODO remove this function and fix all references to it
):  # TODO remove this function and all references to it
```

**Issue**: Functions marked for removal.

**Suggestion**:
1. Search codebase for all references
2. Update callers to use replacement functions
3. Remove deprecated functions
4. Update tests

**Action**: Use `grep` to find all references, create replacement if needed, then remove.

---

### 4. OT2P300 Blowout Function

**Location**: `src/panda_lib/hardware/panda_pipettes/ot2_pipette/ot2P300.py:50, 476`

```python
#TODO remove this. Blowout is not necessary. Dispensing will go to the blowout position.
# TODO remove this blowout function, but verify that nothing references it.
```

**Issue**: Blowout function should be removed.

**Suggestion**:
1. Search for `blowout` method calls
2. Verify dispensing handles blowout automatically
3. Remove function if confirmed unused
4. Update documentation

**Action**: 
```bash
grep -r "\.blowout" src/
```
If no references found, remove the function.

---

### 5. OT2P300 Tip Attachment Location

**Location**: `src/panda_lib/hardware/panda_pipettes/ot2_pipette/pipette_driver.py:406`

```python
self.has_tip = True  # Mark tip as attached #TODO: Fix this so it's in a different location... technically it doesn't have the tip at this point
```

**Issue**: State set before tip is actually attached.

**Suggestion**:
```python
# Move this after successful tip pickup confirmation
# In the method that confirms tip pickup:
if tip_pickup_confirmed:
    self.has_tip = True
```

**Action**: Move state update to after hardware confirmation.

---

### 6. Mill Safe Z Height

**Location**: `src/panda_lib/hardware/grbl_cnc_mill/driver.py:124`

```python
self.safe_z_height = -10.0  # TODO: In the PANDA wrapper, set the safe floor height to the max height of any active object on the mill + the pipette length
```

**Issue**: Hardcoded safe height should be calculated dynamically.

**Suggestion**:
```python
def calculate_safe_z_height(self) -> float:
    """Calculate safe Z height based on active objects."""
    max_object_height = max(
        (obj.height for obj in self.active_objects),
        default=0.0
    )
    pipette_length = self.tool_manager.get_tool("pipette").length
    return max_object_height + pipette_length + safety_margin

self.safe_z_height = self.calculate_safe_z_height()
```

**Action**: Implement dynamic calculation in PANDA wrapper.

---

### 7. Wellplate Orientation Assumption

**Location**: `src/panda_lib/labware/wellplates.py:584`

```python
# FIXME: This assumes one orientation for the wellplate
```

**Issue**: Code assumes single wellplate orientation.

**Suggestion**:
1. Add orientation parameter to wellplate initialization
2. Update `get_corners()` to account for rotation
3. Test with different orientations

**Action**: Add orientation support or document limitation.

---

### 8. Experiment Base Status Methods

**Location**: `src/panda_lib/experiments/experiment_types.py:234`

```python
# FIXME: separate the set status, and set status and save methods from the experimentbase. The experiment base should just be a dataclass
```

**Issue**: ExperimentBase mixing data and behavior.

**Suggestion**:
- Create separate `ExperimentStatusManager` class
- Keep `ExperimentBase` as pure data class
- Move status management to manager class

**Action**: Refactor for separation of concerns.

---

## Code Organization Issues

### 9. Type Definitions Location

**Location**: Multiple files in `src/panda_lib/sql_tools/`

```python
GeneratorEntry,  # TODO move to types
ProtocolEntry,  # TODO move to types
Queue,  # TODO move to types
```

**Issue**: Types should be in dedicated types module.

**Suggestion**:
1. Create `src/panda_lib/sql_tools/types.py`
2. Move type definitions there
3. Update imports throughout codebase

**Action**: Create types module and migrate.

---

### 10. Experiment Parameters Location

**Location**: `src/panda_lib/experiments/experiment_parameters.py:3`

```python
# TODO: Should this be with experiment_tools or should it be with SQL_tools?
```

**Issue**: Unclear module organization.

**Suggestion**: 
- Keep with experiments (current location is correct)
- Update comment or remove if decision made

**Action**: Document decision or move if needed.

---

## Configuration and Calibration TODOs

### 11. Hardware Calibration Values

**Location**: `src/panda_lib_cli/hardware_calibration/line_break_validation.py:21, 44, 71`

```python
CAP_NUM = 5  # TODO replace with the actual cap number
# TODO replace with vial coordinates
# TODO fix offset for PANDA V2
```

**Issue**: Hardcoded calibration values need updating.

**Suggestion**:
1. Move to configuration file
2. Document calibration procedure
3. Add validation

**Action**: Update with actual values or move to config.

---

### 12. Mill Calibration Function

**Location**: `src/panda_lib_cli/hardware_calibration/mill_calibration_and_positioning.py:770`

```python
# TODO: Implement this function
```

**Issue**: Function not implemented.

**Suggestion**: Implement or remove placeholder.

**Action**: Implement function or remove if not needed.

---

## Code Quality Improvements

### 13. Pipette Pump Connection Logic

**Location**: `src/panda_lib/toolkit.py:330`

```python
# TODO: look into why the pump logic wasn't working, for now....specify pipette directly instead of syringe pump because it wasn't connecting to the pipette
```

**Issue**: Workaround in place, root cause unknown.

**Suggestion**:
1. Investigate pump connection issue
2. Add better error handling/logging
3. Fix root cause
4. Remove workaround

**Action**: Debug pump connection and fix.

---

### 14. Image Tools Logger

**Location**: `src/panda_lib/hardware/imaging/panda_image_tools.py:92`

```python
# TODO: add logger to this module
```

**Issue**: Missing logging.

**Suggestion**:
```python
from panda_shared.log_tools import setup_default_logger

logger = setup_default_logger(log_name="panda_image_tools")
```

**Action**: Add logger following existing patterns.

---

### 15. Queue Well ID Reference

**Location**: `src/panda_lib/experiment_loop.py:628-630`

```python
# TODO: this is silly but we need to reference the queue to get the well_id because the experiment object isn't updated with the correct target well_id
# TODO: make a function that just gets the well_id from the queue and returns it
# TODO: Replace with checking for available well, unless given one.
```

**Issue**: Workaround for well_id retrieval.

**Suggestion**:
```python
def get_well_id_from_queue(experiment_id: int) -> str:
    """Get well_id from queue for experiment."""
    queue_entry = get_queue_entry_by_experiment_id(experiment_id)
    return queue_entry.well_id if queue_entry else None
```

**Action**: Create helper function and use it.

---

## Deprecated Code

### 16. Scheduler Deprecated Function

**Location**: `src/panda_lib/scheduler.py:223`

```python
def schedule_experiment(
    experiment: ExperimentBase, override_well_available=False
) -> int:
    """
    Deprecated function kept temporarily. It delegates to schedule_experiments.
    """
```

**Issue**: Function marked deprecated but still present.

**Suggestion**:
1. Add deprecation warning
2. Update all callers to use `schedule_experiments()`
3. Remove in next major version

**Action**: Add warning and plan removal.

---

## Minor Issues

### 17. Commented Code

Multiple locations have commented-out code that should be removed:
- `src/panda_lib/hardware/gamry_potentiostat/gamry_control.py`
- `src/panda_lib/hardware/emstat_potentiostat/emstat_control.py`
- Various other files

**Suggestion**: Remove commented code or convert to proper comments explaining why.

**Action**: Clean up commented code.

---

### 18. Debug Logging

Many `logger.debug()` calls throughout codebase. These are not issues but could be:
- Changed to appropriate log levels
- Removed if too verbose
- Kept if useful for debugging

**Action**: Review and adjust log levels as needed.

---

## Recommendations

### Priority Order

1. **Fix critical bugs** (items 1-8)
2. **Remove deprecated code** (items 3, 4, 16)
3. **Improve code organization** (items 9-10)
4. **Clean up workarounds** (items 13-15)
5. **Documentation and minor fixes** (items 11-12, 17-18)

### Implementation Strategy

1. **Create GitHub issues** for each category
2. **Fix in-place** where straightforward
3. **Plan refactoring** for complex changes
4. **Test thoroughly** before removing deprecated code
5. **Update documentation** as you go

### Testing Considerations

When addressing TODOs:
- Add tests for fixed functionality
- Verify backward compatibility
- Update integration tests if needed
- Document breaking changes

---

## Notes

- Many "DEBUG" entries in grep results are logging statements, not actual issues
- Some TODOs are reminders for future enhancements, not bugs
- Prioritize based on impact and effort required
- Consider creating a tracking issue for each major TODO category
