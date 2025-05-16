# Build Guide

This guide provides instructions for building the physical components of the PANDA-SDL system. The build consists of several key parts: the gantry system, 3D printed components, electronic connections, and the custom wellplate.

**Note:** This section is currently an outline and will be expanded with detailed instructions as they become available.

## Overview

The PANDA-SDL is a custom-built robotics system for polymer film deposition and analysis. The physical build consists of:

1. A 3-axis gantry system for movement
2. Custom 3D printed components for mounting equipment
3. Arduino-based control electronics 
4. A specialized wellplate system for electrochemical experiments
5. Syringe pump or Opentrons Pipette

## Gantry Construction

The gantry provides the structural framework and motion system for the PANDA-SDL.

### Components Needed

- 

### Assembly Steps

## 3D Printed Components

The PANDA-SDL requires several custom 3D printed parts to mount and integrate equipment.

### Required Files

All STL files for 3D printing can be found in the `documentation/3d-prints/` directory:
- 

### Printing Specifications

- **Material**: PLA or ABS recommended
- **Infill**: 20-30% for most parts, 50%+ for structural components
- **Layer Height**: 0.2mm recommended
- **Supports**: Required for overhanging features

### Assembly Instructions

1. 

## Arduino Wiring

The PANDA-SDL uses Arduino-based control systems for various functions.

### Components Needed

- 

### Wiring Diagrams

Refer to the documents in the `documentation/documents/` directory:
- 

### Wiring Steps

1. 

## Wellplate and Gasket

The PANDA-SDL uses a specialized wellplate system for electrochemical experiments.

### Components Needed

- Base materials as specified in the SOP
- Gasket materials
- Working electrode material
- Conductive connections

### Assembly Steps

Follow the detailed instructions in the [Wellplate and Gasket SOP](../documentation/sops/wellplate_and_gasket_SOP_v1.md).

1. **Prepare Materials**
   - Cut and clean all materials according to specifications
   
2. **Assemble the Wellplate**
   - Follow the layering order specified in the SOP
   - Ensure proper alignment of all components
   
3. **Install Electrical Connections**
   - Connect the working electrode material
   - Install reference and counter electrode fixtures
   
4. **Test Wellplate**
   - Check for leaks
   - Verify electrical connections
   - Test with a standard solution

## System Integration

After building all components, they need to be integrated into a functioning system.

### Integration Steps

1. **Mechanical Assembly**
   - Mount the gantry on a stable platform
   - Install all 3D printed components
   - Position the deck and fixtures

2. **Electronics Connection**
   - Connect all control electronics
   - Install the computer/control system
   - Connect power supplies

3. **Software Setup**
   - Install the PANDA-SDL software
   - Configure the system (see [Getting Started](Getting-Started.md))
   - Calibrate all axes and tools

4. **System Validation**
   - Run through the validation scripts in `validation_scripts/`
   - Test basic operations
   - Perform a test experiment

## Calibration

Proper calibration is essential for accurate and reliable operation.

### Calibration Procedures

1. **Motion System Calibration**
   - Calibrate steps per mm for each axis
   - Verify positioning accuracy
   - Set proper acceleration and speed parameters

2. **Pipette Calibration**
   - Calibrate the pipette for accurate volume dispensing
   - Validate using the `pipette_validation_v2.py` script

3. **Camera Calibration**
   - Calibrate the camera offsets and focus the camera
   - Calibrate image coordinates to physical positions

4. **Electrode Position Calibration**
   - Calibrate the position of the electrodes relative to center of PAW
   - Verify electrical connections

## Maintenance

Regular maintenance is necessary to keep the PANDA-SDL functioning properly.

### Routine Maintenance

1. **Mechanical System**
   - Lubricate linear rails and bearings
   - Inspect for wear or damage

2. **Fluid System**
   - Clean pipette regularly
   - Check for clogs or contamination
   - Replace tubing if necessary

3. **Electronics**
   - Check all connections
   - Verify sensor operations
   - Update firmware if needed

4. **Calibration Checks**
   - Periodically verify system calibration
   - Rerun validation scripts as needed

## Troubleshooting

Common hardware issues and their solutions.

### Common Issues

1. **Motor Skipping Steps**
   - Verify motor current settings
   - Reduce acceleration or speed

2. **Pipette Inaccuracy**
   - Clean the pipette system
   - Rerun pipette validation
   - Check for air bubbles or clogs

3. **Electrical Connection Issues**
   - Check all wire connections
   - Verify power supply voltages
   - Test continuity of connections

4. **Wellplate Leakage**
   - Inspect gasket for damage
   - Check wellplate assembly
   - Replace compromised components

## Future Expansions

The PANDA-SDL system is designed to be modular and expandable.

### Potential Upgrades

1. **Additional Tools**
   - Multiple pipette heads
   - Spectroscopy integrations
   - Advanced imaging capabilities

2. **Environmental Control**
   - Temperature regulation
   - Humidity control
   - Inert atmosphere capability

3. **Advanced Analysis**
   - Real-time data processing
   - Enhanced imaging analysis
   - Additional characterization methods
