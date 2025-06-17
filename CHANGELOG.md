# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-16

### Added

- Modern Python project structure with src-layout
- Comprehensive development tooling (ruff, mypy, pre-commit)
- GitHub Actions CI/CD pipeline
- Streaming output for memory efficiency
- Atomic file writes to prevent corruption
- Enhanced statistics tracking (file types, sizes, line counts)
- Pattern caching for improved performance
- Progress callback support
- Makefile for common development tasks
- CONTRIBUTING.md with contribution guidelines
- pyproject.toml for modern Python packaging

### Changed

- Migrated from requirements.txt to pyproject.toml
- Restructured project to use src-layout
- Consolidated three capture implementations into one
- Improved error handling and recovery
- Enhanced binary file detection
- Updated imports to use new package structure

### Fixed

- Memory efficiency issues with large projects
- Binary file detection accuracy
- Import path issues

### Removed

- Redundant capture module implementations
- Legacy requirements.txt file

## [0.1.0] - 2024-02-24

### Added

- Initial release
- CLI interface with Rich library
- Web interface with Streamlit
- Basic project snapshot functionality
- Gitignore pattern support
- Syntax highlighting for 50+ languages
- Configuration persistence
- Parallel file processing
- Memory mapping for large files
- Custom ignore patterns
- Template system for common project types

[0.2.0]: https://github.com/veteranbv/project-capture/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/veteranbv/project-capture/releases/tag/v0.1.0
