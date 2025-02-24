# Project Snapshot Developer Guide

## Overview
Project Snapshot captures code repositories into AI-optimized snapshots. It generates comprehensive summaries including directory structure and file contents, making it easier for AI assistants to understand and work with entire projects.

## Commands
- Run web UI: `streamlit run streamlit_app.py`
- Run CLI: `python main.py`
- Run tests: `python -m unittest test_snapshot.py`
- Run single test: `python -m unittest test_snapshot.TestSnapshotFunctions.test_name`
- Type check: `mypy .` (install mypy with `pip install mypy`)
- Install deps: `pip install -r requirements.txt`

## Project Structure
- `main.py`: CLI interface with Rich-powered TUI
- `streamlit_app.py`: Web interface using Streamlit
- `snapshot/`: Core library
  - `capture.py`: Project scanning and content capturing
  - `config.py`: Configuration management
  - `constants.py`: Centralized constants
  - `types.py`: TypedDict definitions for configs
  - `utils.py`: Logging, sanitization, clipboard functions
  - `exceptions.py`: Custom error types

## Architecture
The application has a clean separation between:
- **Interfaces**: CLI (main.py) and web UI (streamlit_app.py)
- **Core logic**: snapshot/ module with pure functions
- **Configuration**: JSON-based persistent storage with strong typing
- **Output**: Markdown files with proper formatting for AI consumption

The snapshot process:
1. Load/create user configuration
2. Scan target directory (respecting ignore patterns)
3. Generate directory tree
4. Process and format file contents (in parallel)
5. Write formatted snapshot to output file

## Code Style
- **Imports**: Standard library → third-party → local imports with blank lines
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Type Hints**: Required for all functions with proper return types
- **Documentation**: Google-style docstrings with Args/Returns
- **Error Handling**: Use ProjectSnapshotError with proper logging
- **File Operations**: Use pathlib.Path consistently

## Key Features
- Parallel file processing for performance
- Smart filtering with combined gitignore patterns
- Memory mapping for efficient large file handling
- Binary file detection (extension and content-based)
- Markdown escaping for proper output formatting
- Project-specific configuration management
- Predefined ignore pattern templates for different project types