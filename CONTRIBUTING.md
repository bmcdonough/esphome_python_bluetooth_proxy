# Contributing to ESPHome Python Bluetooth Proxy

Thank you for your interest in contributing to this project! This document outlines the development setup and workflow.

## Development Setup

### Prerequisites
- Python 3.12 or higher
- Git

### Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/bmcdonough/esphome_python_bluetooth_proxy.git
cd esphome_python_bluetooth_proxy
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Development Workflow

### Code Quality Standards

This project enforces strict code quality standards. All code must pass the following checks:

- **isort**: Import sorting (alphabetical order)
- **black**: Code formatting (88 character line length)
- **flake8**: Linting and style checking
- **pytest**: All tests must pass

### Running Quality Checks Locally

Before committing, run these commands to ensure your code meets our standards:

```bash
# Sort imports
isort .

# Format code
black .

# Check linting
flake8 .

# Run tests
pytest
```

### Pre-commit Hooks

Pre-commit hooks are automatically installed and will run these checks before each commit. If any check fails, the commit will be blocked until you fix the issues.

### Continuous Integration

Our GitHub Actions CI pipeline runs on every push and pull request:

1. **Code Quality Checks**: isort, black, flake8
2. **Tests**: pytest with coverage reporting
3. **Coverage**: Results uploaded to Codecov

**Important**: Pull requests will be blocked if CI checks fail.

## Project Structure

```
esphome_python_bluetooth_proxy/
├── src/
│   └── esphome_bluetooth_proxy/    # Main package
│       └── __init__.py
├── tests/                          # Test files
│   ├── __init__.py
│   └── test_basic.py
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Development dependencies
├── pyproject.toml                  # Project configuration
├── .pre-commit-config.yaml         # Pre-commit hooks
└── CONTRIBUTING.md                 # This file
```

## Writing Tests

- Place test files in the `tests/` directory
- Name test files with `test_` prefix
- Use pytest conventions for test functions
- Aim for good test coverage

## Making Changes

1. Create a feature branch from `main`
2. Make your changes
3. Run quality checks locally
4. Commit your changes (pre-commit hooks will run)
5. Push your branch and create a pull request
6. Ensure CI passes before requesting review

## Questions?

If you have questions about the development process, please open an issue or reach out to the maintainers.
