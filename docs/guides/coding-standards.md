# Coding Standards

## Python Development Standards

### 1. Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Maximum line length: 100 characters (configured in pyproject.toml)
- Use descriptive variable and function names

### 2. Logging

```python
# Use standard logging instead of print statements
import logging

logger = logging.getLogger(__name__)
logger.info("Processing file: %s", filename)
```

### 3. Error Handling

```python
# Use specific exceptions and provide context
try:
    result = process_file(path)
except FileNotFoundError as e:
    logger.error(f"File not found: {path}")
    raise ProjectSnapshotError(f"Cannot process {path}: {e}") from e
```

### 4. Documentation

```python
def capture_project_contents(
    root_directory: Path,
    output_filename: Path,
    project_name: str,
) -> Dict[str, Any]:
    """Capture project contents and save to file.
    
    Args:
        root_directory: The root directory to capture
        output_filename: Path where the output will be saved
        project_name: Name of the project for display
        
    Returns:
        Dictionary containing capture statistics
        
    Raises:
        ProjectSnapshotError: If capture fails
    """
```

### 5. Path Handling

```python
# Use pathlib for cross-platform compatibility
from pathlib import Path

config_path = Path.home() / ".config" / "project-capture"
config_path.mkdir(parents=True, exist_ok=True)
```

### 6. File Operations

```python
# Always use context managers
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
```

### 7. Testing

- Write tests for all new functionality
- Maintain test coverage above 80%
- Use pytest for unit tests
- Mock external dependencies

### 8. Security

- Validate and sanitize all user inputs
- Never log sensitive information
- Use the security scanner for detecting secrets
- Follow the principle of least privilege

## Development Workflow

### Before Committing

1. Run all tests: `make test`
2. Check code style: `make lint`
3. Format code: `make format`
4. Type check: `make type-check`
5. Security scan: `make security`

### Code Review Checklist

- [ ] Code follows PEP 8 style guide
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] Error handling is comprehensive
- [ ] Tests are included for new functionality
- [ ] No hardcoded paths or credentials
- [ ] Logging is used instead of print statements
- [ ] File operations use context managers

## Performance Guidelines

### Memory Efficiency

- Use generators for large datasets
- Stream output instead of building in memory
- Use memory mapping for large files

### Concurrency

- Use ThreadPoolExecutor for I/O-bound operations
- Implement proper synchronization with locks/queues
- Avoid shared mutable state

### Optimization

- Profile before optimizing
- Cache expensive operations
- Use appropriate data structures
- Minimize file system calls

## Dependency Management

- Pin exact versions in production
- Use version ranges in development
- Document why each dependency is needed
- Regularly update dependencies
- Use `pip-audit` for security checks