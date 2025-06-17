# Project Capture Architecture

## Overview

Project Capture is a Python-based tool designed to create AI-optimized snapshots of codebases. It uses a modular architecture with clear separation of concerns.

## Directory Structure

```
project_capture/
├── src/
│   └── project_capture/
│       ├── cli/          # Command-line interface
│       ├── core/         # Core capture logic
│       ├── formats/      # Output format handlers
│       └── web/          # Web interface (Streamlit)
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
└── docs/                # Documentation
```

## Core Components

### 1. Capture Engine (`core/capture.py`)

- **StreamingCapture**: Main class that orchestrates the capture process
- **FileProcessor**: Handles individual file processing
- **PatternMatcher**: Manages gitignore patterns with caching
- Uses threading for parallel processing
- Implements streaming output to handle large projects efficiently

### 2. Configuration Management (`core/config.py`)

- Manages project configurations
- Supports multiple configurations per directory
- Persists settings in `config.json`

### 3. Output Formats (`formats/`)

- **BaseFormatter**: Abstract base class for formatters
- **Markdown**: Default human-readable format
- **JSON**: Structured format (ready for implementation)
- **YAML**: Alternative structured format (ready for implementation)

## Key Design Decisions

### Memory Efficiency

- **Streaming Output**: Files are processed and written incrementally
- **Memory Mapping**: Large files (>1MB) use mmap for efficient reading
- **Queue-based Writing**: Separate thread handles file I/O

### Performance

- **Parallel Processing**: ThreadPoolExecutor for concurrent file processing
- **Pattern Caching**: Gitignore patterns cached per directory
- **Sorted Output**: Deterministic file ordering for consistency

### Error Handling

- **Graceful Degradation**: Individual file errors don't stop the capture
- **Detailed Logging**: Comprehensive error tracking
- **Atomic Writes**: Temporary files prevent corruption

## Data Flow

1. **Configuration Loading**: Load project settings from config.json
2. **Pattern Compilation**: Build ignore patterns from gitignore files
3. **File Discovery**: Walk directory tree, filtering ignored paths
4. **Parallel Processing**: Submit files to thread pool
5. **Streaming Output**: Write results via queue to output file
6. **Statistics Collection**: Track metrics during processing

## Extension Points

### Adding New Output Formats

1. Create new formatter in `formats/` directory
2. Inherit from `BaseFormatter`
3. Implement `format()` and `write()` methods
4. Register in format factory (when implemented)

### Adding File Processors

1. Create processor for specific file types
2. Register in FileProcessor dispatch table
3. Handle special processing (e.g., minification, parsing)

## Security Considerations

- **Path Sanitization**: All paths validated before processing
- **Binary Detection**: Extension and content-based detection
- **Security Scanning**: Pattern detection for API keys/secrets
- **Size Limits**: Configurable limits prevent resource exhaustion