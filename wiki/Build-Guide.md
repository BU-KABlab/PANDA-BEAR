# Build Guide

This guide provides instructions for building the physical components of the PANDA-SDL system. The build consists of several key parts: the gantry system, 3D printed components, electronic connections, and the custom wellplate.

**Note:** This section is currently an outline and will be expanded with detailed instructions as they become available.

## Overview

The PANDA-SDL is a custom-built robotics system for polymer film deposition and analysis. The physical build consists of:

1. A 3-axis gantry system for movement
2. Custom 3D printed components for mounting equipment
3. Arduino-based control electronics
4. A specialized wellplate system for electrochemical experiments

## Gantry Construction

The gantry provides the structural framework and motion system for the PANDA-SDL.

### Components Needed

- Linear rails and bearings
- Stepper motors
- Belt drive system
- Aluminum extrusions
- Mounting brackets
- Control electronics

### Assembly Steps

1. **Frame Construction**
   - Assemble the aluminum extrusion base frame
   - Mount Y-axis rails to the base frame
   - Attach X-axis crossbeam to Y-axis carriers

2. **Motion System**
   - Install stepper motors for each axis
   - Mount belt drives and tensioners
   - Install limit switches at axis endpoints

3. **Control Electronics**
   - Mount the control board
   - Connect stepper motor drivers
   - Wire limit switches

4. **Validation**
   - Test movement on all axes
   - Calibrate motion system
   - Verify homing functions

## 3D Printed Components

The PANDA-SDL requires several custom 3D printed parts to mount and integrate equipment.

### Required Files

All STL files for 3D printing can be found in the `documentation/3d-prints/` directory:

- Equipment-Head-Front_v2.stl
- Equipment-Head-Rear_v2.stl
- Paw components
- Pipette Adapter
- Pipette Arm
- SharpieHolder
- Stage Accessories

### Printing Specifications

- **Material**: PLA or PETG recommended
- **Infill**: 20-30% for most parts, 50%+ for structural components
- **Layer Height**: 0.2mm recommended
- **Supports**: Required for overhanging features

### Assembly Instructions

1. **Tool Head Assembly**
   - Print Equipment-Head-Front_v2.stl and Equipment-Head-Rear_v2.stl
   - Attach to the Z-axis carriage
   - Mount the camera and pipette adaptors

2. **Pipette System**
   - Print the Pipette Adapter components
   - Assemble with the appropriate pipette
   - Mount to the tool head

3. **Stage Accessories**
   - Print the required stage accessories
   - Mount to the deck surface
   - Secure vial holders and wellplate fixtures

## Arduino Wiring

The PANDA-SDL uses Arduino-based control systems for various functions.

### Components Needed

- Arduino Mega (or compatible board)
- Motor drivers
- Power supply
- Connection wires
- LED control circuit
- Relay modules (if needed)

### Wiring Diagrams

Refer to the documents in the `documentation/documents/` directory:

- Pawduino - LEDs.pdf
- Pawduino - Neopixels.pdf

### Wiring Steps

1. **Power System**
   - Connect the power supply to the Arduino and motor drivers
   - Wire the 5V and 12V distribution

2. **Motor Connections**
   - Connect stepper motors to their respective drivers
   - Wire the drivers to the Arduino control pins

3. **Sensor Connections**
   - Wire limit switches to the Arduino inputs
   - Connect any additional sensors (temperature, etc.)

4. **LED System**
   - Follow the Pawduino - Neopixels diagram for LED connections
   - Test the LED functionality

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
   - Position and focus the camera
   - Calibrate image coordinates to physical positions

4. **Electrode Position Calibration**
   - Calibrate the position of the electrodes relative to wells
   - Verify electrical connections

## Maintenance

Regular maintenance is necessary to keep the PANDA-SDL functioning properly.

### Routine Maintenance

1. **Mechanical System**
   - Lubricate linear rails and bearings
   - Check belt tension
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
   - Check belt tension
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
