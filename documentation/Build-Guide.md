# Build Guide

Overview of the physical PANDA system construction. The PANDA system is built on a modified [PROVerXL 4030 V2](https://www.sainsmart.com/products/proverxl-4030-v2) gantry.

**Navigation**: [Home](00-Home.md) | Build Guide | [Construction Guide](Construction.md) | [Arduino Wiring](Arduino-Wiring.md)

## Overview

The PANDA physical system consists of:
- Modified CNC gantry (PROVerXL 4030 V2)
- Custom deck and deck accessories
- Process Automation Widget (PAW) with integrated instrumentation
- Electronics and control systems

## Construction Steps

1. **Assemble gantry**: Follow manufacturer instructions, but do not install the standard deck
2. **Fabricate deck**: Lasercut or mill your material (polycarbonate, 9 mm thick recommended) using the [deck template](3D-prints/PandaDeck.step)
3. **Install custom deck**: Mount the fabricated deck to the gantry
4. **3D print deck accessories**: Print components from [DeckAccessories](3D-prints/DeckAccessories/) as needed
5. **3D print PAW components**: Print components from [PAW](3D-prints/PAW/) directory

## Resources

- **Bill of Materials**: See [documents/bom.md](documents/bom.md) for parts list, prices, and vendors
- **3D Printed Parts**: All CAD files are in the [3D-prints](3D-prints/) directory
- **Construction Details**: For detailed construction instructions, see the [Construction Guide](Construction.md)
- **Electronics**: See [Arduino Wiring](Arduino-Wiring.md) for electronics and wiring information
