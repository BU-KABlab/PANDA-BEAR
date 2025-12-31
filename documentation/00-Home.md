# PANDA-BEAR Documentation

![PANDA Logo](../PANDAlogo.png)

Welcome to the PANDA (Polymer Analysis and Discovery Array) Self-Driving Lab documentation. This documentation provides comprehensive guides for users and developers working with the PANDA system.

## About PANDA

PANDA is an open-source self-driving lab developed by the [KABLab](https://www.kablab.org/) at [Boston University](https://www.bu.edu/). The system automates electrodeposition and functional characterization of polymer films using electrochemical and optical techniques in a well plate architecture.

## Documentation Structure

### User Guides

These guides are designed for end users who want to install, configure, and use PANDA-BEAR for experiments.

1. **[Installation and Setup](01%20Getting-Started.md#installation)** - Install PANDA-BEAR, configure your environment, and set up the database
2. **[Getting Started](01%20Getting-Started.md)** - Run your first experiment and understand the basic workflow
3. **[Writing Protocols](03%20Writing-Protocols.md)** - Create experimental protocols that define experiment execution
4. **[Creating Generators](02%20Creating-Generators.md)** - Build experiment generators for parameter sweeps and batch experiments
5. **[Using Analyzers](04%20Using-Analyzers.md)** - Process and analyze experiment results
6. **[Main Menu Reference](Main-Menu-Reference.md)** - Complete reference for the command-line interface

### Reference Documentation

Quick reference materials for looking up specific information.

- **[API Reference](API-Reference.md)** - Complete API documentation for protocols, generators, and analyzers
- **[Main Menu Reference](Main-Menu-Reference.md)** - Detailed documentation of all CLI menu options

### Developer Documentation

Information for developers contributing to or extending PANDA-BEAR.

- **[Code Architecture](Code-Architecture.md)** - System architecture and component relationships
- **[Developer Guide](Developer-Guide.md)** - Development environment setup and guidelines
- **[Contributing](Contributing.md)** - Contribution process and best practices

### Hardware Documentation

Physical system construction and hardware setup.

- **[Build Guide](Build-Guide.md)** - Overview of physical system construction
- **[Construction Guide](Construction.md)** - Detailed construction instructions
- **[Arduino Wiring](Arduino-Wiring.md)** - Electronics and wiring diagrams
- **[3D Printed Components](3D-prints/)** - CAD files and specifications for 3D printed parts
- **[Standard Operating Procedures](sops/)** - SOPs for wellplate fabrication and other procedures

## Quick Start Path

For new users, follow this sequence:

1. **Installation**: Follow the [Installation section](01%20Getting-Started.md#installation) in Getting Started
2. **First Experiment**: Complete the [Running Your First Experiment](01%20Getting-Started.md#running-your-first-experiment) section
3. **Create Your Own**: Learn to [write protocols](03%20Writing-Protocols.md) and [create generators](02%20Creating-Generators.md)

## Additional Resources

- **Publication**: [PANDA: a self-driving lab for studying electrodeposited polymer films](https://pubs.rsc.org/en/content/articlelanding/2024/mh/d4mh00797b) - Materials Horizons (2024)
- **GitHub Repository**: [BU-KABlab/PANDA-BEAR](https://github.com/BU-KABlab/PANDA-BEAR) - Source code and issue tracking
- **Main Repository README**: [README.md](../README.md) - Project overview and quick installation

## License

PANDA-BEAR is licensed under the GNU General Public License v2.0. See the [LICENSE](../LICENSE) file for details.
