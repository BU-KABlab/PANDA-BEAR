# Contributing to PANDA-BEAR

Guidelines and best practices for contributing to the PANDA-BEAR project.

**Navigation**: [Home](00-Home.md) | [Developer Guide](Developer-Guide.md) | Contributing | [Code Architecture](Code-Architecture.md)

## Table of Contents

- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Guidelines](#development-guidelines)
- [Submitting Changes](#submitting-changes)

## Getting Started

### Code of Conduct

We expect all contributors to follow our code of conduct, which promotes a respectful and inclusive environment for collaboration.

### Project Overview

PANDA-BEAR is an open-source self-driving lab for polymer analysis and discovery. Before contributing, familiarize yourself with:

- The [README.md](../README.md) file
- The [Developer Guide](Developer-Guide.md)
- The [API Reference](API-Reference.md)

## How to Contribute

### Reporting Bugs

If you find a bug, please submit an issue on the GitHub repository with:

1. A clear title and description
2. Steps to reproduce the bug
3. Expected behavior vs. actual behavior
4. System information (OS, Python version, etc.)
5. Log files if applicable

### Suggesting Enhancements

We welcome suggestions for new features or improvements! When submitting an enhancement suggestion:

1. Use a clear and descriptive title
2. Provide a detailed description of the proposed functionality
3. Explain why this enhancement would be useful
4. Include examples of how the feature would be used

### Contributing Code

#### Setting Up Your Development Environment

Follow the instructions in the [Developer Guide](Developer-Guide.md#setting-up-for-development) to set up your development environment.

#### Making Changes

1. **Create a branch**:
   ```powershell
   git checkout -b feature/your-feature-name
   ```

2. **Write tests**:
   - Add unit tests for new functionality
   - Ensure all tests pass

3. **Implement your changes**:
   - Follow the [coding standards](#coding-standards)
   - Keep your changes focused and atomic

4. **Document your changes**:
   - Update docstrings for modified code
   - Update documentation files as needed
   - Add comments for complex logic

5. **Commit your changes**:
   - Use clear and descriptive commit messages
   - Reference issue numbers when applicable

6. **Submit a pull request**:
   - Clearly describe what your changes do
   - Mention any related issues
   - Request review from maintainers

#### Pull Request Process

1. Ensure all tests pass
2. Wait for review by project maintainers
3. Address any feedback or requested changes
4. Once approved, your changes will be merged

## Coding Standards

### Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Include type hints for function parameters and return values

### Documentation

- Document all public functions, classes, and methods
- Follow the Google docstring format:
  ```python
  def my_function(param1, param2):
      """Brief description of function.
      
      More detailed description if needed.
      
      Args:
          param1: Description of param1
          param2: Description of param2
          
      Returns:
          Description of return value
          
      Raises:
          ExceptionType: When exception is raised
      """
  ```

### Testing

- Write unit tests for all new functionality
- Use pytest for testing
- Aim for high test coverage
- Include tests for edge cases and error conditions

## Project Structure

Understanding the project structure will help you contribute effectively:

- **src/panda_lib/**: Core library code
- **panda_experiment_protocols/**: Experiment protocols
- **panda_experiment_generators/**: Experiment generators
- **panda_experiment_analyzers/**: Result analyzers
- **tests/**: Test suite
- **documentation/**: User and developer documentation

## Development Workflow

### Feature Development

For developing new features:

1. **Design**: Create a design document outlining your approach
2. **Prototype**: Implement a minimal version to test the concept
3. **Refine**: Iterate based on feedback
4. **Test**: Add comprehensive tests
5. **Document**: Update documentation
6. **Submit**: Create a pull request

### Bug Fixes

For fixing bugs:

1. **Reproduce**: Ensure you can reproduce the issue
2. **Test**: Write a failing test that demonstrates the bug
3. **Fix**: Implement the fix
4. **Verify**: Ensure all tests pass
5. **Document**: Explain the cause and solution
6. **Submit**: Create a pull request

## Communication

### Asking Questions

If you have questions about contributing:

- Open an issue on GitHub for technical questions
- Contact the maintainers for general inquiries

### Discussions

For more extensive discussions about features or improvements:

- Use GitHub Discussions to propose and discuss ideas
- Join the project's communication channels

## Versioning

The project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible new functionality
- **PATCH** version for backward-compatible bug fixes

## Next Steps

After reviewing the contribution guidelines, you may want to:

- Review the [Developer Guide](Developer-Guide.md) for development environment setup
- Study the [Code Architecture](Code-Architecture.md) to understand the system structure
- Consult the [API Reference](API-Reference.md) for detailed function documentation
- Check existing issues on GitHub to find areas where contributions are needed

## License

By contributing to PANDA-BEAR, you agree that your contributions will be licensed under the project's [GNU General Public License v2.0](../LICENSE).

## Acknowledgements

We appreciate all contributors who help improve the PANDA-BEAR project. Contributors will be acknowledged in the project documentation and release notes.
