# Contributing to Alpha-Q

Thank you for your interest in contributing to Alpha-Q! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please read it before contributing.

## Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/alpha-q.git
   cd alpha-q
   git remote add upstream https://github.com/original/alpha-q.git
   ```

2. **Create a Development Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set Up Development Environment**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install development dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt

   # Install pre-commit hooks
   pre-commit install
   ```

## Development Workflow

1. **Before Starting Work**
   - Update your fork: `git fetch upstream && git merge upstream/main`
   - Create a new branch for your feature/fix
   - Ensure all tests pass: `pytest`

2. **During Development**
   - Write tests for new features
   - Follow the code style guide
   - Run tests frequently: `pytest`
   - Format code: `black . && isort .`
   - Check types: `mypy .`
   - Lint code: `flake8`

3. **Before Submitting**
   - Update documentation
   - Add/update tests
   - Run full test suite: `pytest`
   - Ensure all checks pass: `pre-commit run --all-files`

## Code Style Guide

1. **Python Code**
   - Follow PEP 8
   - Use type hints
   - Maximum line length: 88 characters (Black standard)
   - Use docstrings (Google style)
   - Use meaningful variable names

2. **Documentation**
   - Update README.md for user-facing changes
   - Add docstrings for new functions/classes
   - Update API documentation if needed
   - Include examples for complex features

3. **Testing**
   - Write unit tests for new features
   - Include integration tests for API endpoints
   - Maintain test coverage above 80%
   - Use pytest fixtures for test setup

## Pull Request Process

1. **Before Submitting**
   - Update your branch with upstream changes
   - Run all tests and checks
   - Update documentation
   - Squash commits if necessary

2. **Pull Request Template**
   - Description of changes
   - Related issue number
   - Type of change (feature/bugfix/docs)
   - Testing performed
   - Screenshots (if applicable)

3. **Review Process**
   - Address review comments
   - Update PR as needed
   - Ensure CI passes
   - Get required approvals

## Release Process

1. **Versioning**
   - Follow semantic versioning
   - Update version in `__init__.py`
   - Update CHANGELOG.md

2. **Release Checklist**
   - All tests passing
   - Documentation updated
   - Changelog updated
   - Version bumped
   - Release notes prepared

## Getting Help

- Open an issue for bugs
- Use discussions for questions
- Join our community chat
- Check existing documentation

## Additional Resources

- [Python Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
