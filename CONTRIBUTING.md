# Contributing to PANDA-BEAR

Thank you for your interest in contributing to PANDA-BEAR! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and professional environment for all contributors.

## Getting Started

1. **Fork the repository** and clone your fork
2. **Set up your development environment**:
   ```bash
   # Create a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   uv sync  # or pip install -r requirements.txt
   ```

3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use `ruff` for linting and formatting (configured in `pyproject.toml`)
- Maximum line length: 88 characters
- Use type hints where appropriate

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_specific.py

# Run with coverage
pytest --cov=src
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality. Install them:

```bash
pre-commit install
```

The hooks will:
- Format code with `ruff`
- Check for linting issues
- Update `requirements.txt` if dependencies change

## Making Changes

### Project Structure

- `src/panda_lib/`: Core library functionality
- `src/panda_lib_cli/`: Command-line interface
- `src/panda_lib_db/`: Database setup and management
- `src/panda_shared/`: Shared utilities and configuration
- `panda_experiment_protocols/`: User-defined experiment protocols
- `panda_experiment_generators/`: User-defined experiment generators
- `panda_experiment_analyzers/`: User-defined analysis modules
- `tests/`: Test suite

### Adding New Features

1. **Hardware Drivers**: Add to `src/panda_lib/hardware/`
2. **Experiment Protocols**: Add to `panda_experiment_protocols/`
3. **Analysis Modules**: Add to `panda_experiment_analyzers/`
4. **CLI Commands**: Add to `src/panda_lib_cli/menu/`

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use pytest fixtures from `tests/conftest.py`
- Aim for >80% code coverage for new code

### Documentation

- Update docstrings for new functions/classes
- Update README.md if adding major features
- Add examples to documentation/ if applicable

## Submitting Changes

1. **Commit your changes**:
   ```bash
   git commit -m "Description of your changes"
   ```
   Use clear, descriptive commit messages.

2. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request** on GitHub:
   - Provide a clear description of your changes
   - Reference any related issues
   - Ensure all tests pass
   - Update documentation as needed

## Review Process

- All pull requests require review before merging
- Address review comments promptly
- Maintain a clean commit history (consider squashing commits)

## Reporting Issues

When reporting bugs or requesting features:

1. Check if the issue already exists
2. Provide a clear description
3. Include steps to reproduce (for bugs)
4. Include relevant system information
5. Add labels if you have permission

## Questions?

Feel free to open an issue for questions or reach out to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the GPL-2.0 license.
