# Contributing to Project Capture

Thank you for your interest in contributing to Project Capture! We welcome contributions from the community and are grateful for any help you can provide.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/yourusername/project-capture.git
   cd project-capture
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```
4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Development Process

1. Create a new branch for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, following our coding standards (see below)

3. Run tests to ensure everything works:
   ```bash
   make test
   ```

4. Run linting and type checking:
   ```bash
   make lint
   make type-check
   ```

5. Commit your changes with a descriptive commit message:
   ```bash
   git commit -m "feat: add new feature X"
   ```

6. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

7. Create a Pull Request on GitHub

## Coding Standards

### Python Style
- We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Follow PEP 8 with a line length of 100 characters
- Use type hints for all function signatures
- Write docstrings for all public functions and classes

### Commit Messages
- Use conventional commits format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Keep the first line under 72 characters
- Add a body if needed for more context

### Testing
- Write tests for all new functionality
- Maintain or improve code coverage
- Use pytest for unit tests
- Place tests in the appropriate directory under `tests/`

## Pull Request Guidelines

1. **Description**: Clearly describe what your PR does and why
2. **Tests**: Include tests for any new functionality
3. **Documentation**: Update documentation if needed
4. **Changelog**: Add an entry to CHANGELOG.md if appropriate
5. **Small PRs**: Keep PRs focused on a single feature or fix

## Code Review Process

1. All PRs require at least one review before merging
2. Address all feedback constructively
3. Update your PR based on review comments
4. Squash commits if requested

## Reporting Issues

- Use GitHub Issues to report bugs or request features
- Search existing issues before creating a new one
- Include as much detail as possible:
  - Python version
  - Operating system
  - Steps to reproduce
  - Expected vs actual behavior
  - Error messages or logs

## Development Commands

```bash
# Install development dependencies
make install-dev

# Run all tests
make test

# Run only unit tests
make test-unit

# Run linting
make lint

# Format code
make format

# Type checking
make type-check

# Run all checks
make check-all

# Build documentation
make docs

# Clean build artifacts
make clean
```

## Questions?

If you have questions, feel free to:
- Open an issue for discussion
- Check existing documentation
- Ask in pull request comments

Thank you for contributing to Project Capture!