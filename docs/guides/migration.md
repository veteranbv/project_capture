# Migration Guide

## Upgrading from v0.1.x to v0.2.x

Version 0.2.0 introduces significant structural changes while maintaining backward compatibility where possible.

### Import Changes

**Old imports:**
```python
from snapshot.capture import save_project_contents
from snapshot.config import load_config
```

**New imports:**
```python
from project_capture import capture_project_contents
from project_capture.core.config import load_config
```

### CLI Changes

**Old:**
```bash
python main.py
```

**New:**
```bash
./project_capture
# or
python -m project_capture.cli
```

### Web Interface Changes

**Old:**
```bash
streamlit run streamlit_app.py
```

**New:**
```bash
streamlit run src/project_capture/web/app.py
# or
make run-web
```

### API Changes

The main capture function now returns additional information:

```python
# v0.1.x returned:
{"processed": 10, "skipped": 2, "errors": []}

# v0.2.x returns:
{
    "processed": 10,
    "skipped": 2,
    "errors": [],
    "total_lines": 1500,
    "total_size": 50000,
    "file_types": {".py": 8, ".md": 2},
    "elapsed_time": 2.5,
    "output_path": "output/snapshot.md"
}
```

### Configuration File

Your existing `config.json` remains compatible. New fields will be added automatically when you use new features.

### Output Location

Output files continue to be saved in the `output/` directory relative to where you run the command.

## Breaking Changes

### Path Arguments

The capture functions now require Path objects instead of strings:

```python
# Old (still works via type conversion)
capture_project_contents(
    root_directory=".",
    output_filename="output.md",
    ...
)

# New (recommended)
from pathlib import Path

capture_project_contents(
    root_directory=Path("."),
    output_filename=Path("output.md"),
    ...
)
```

### Progress Callback

New optional parameter for progress tracking:

```python
def progress_callback(completed: int, total: int):
    print(f"Progress: {completed}/{total}")

capture_project_contents(
    ...,
    progress_callback=progress_callback
)
```

## Deprecations

- `requirements.txt` is deprecated in favor of `pyproject.toml`
- Direct imports from `snapshot.*` modules are deprecated

## Recommended Migration Steps

1. **Backup your configuration:**
   ```bash
   cp config.json config.json.backup
   ```

2. **Create new virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install the new version:**
   ```bash
   pip install -e .
   ```

4. **Update your scripts** to use new import paths

5. **Test your workflows** with the new version

## Getting Help

If you encounter issues during migration:

1. Check the [CHANGELOG](../../CHANGELOG.md) for detailed changes
2. Review your [configuration](../api/config.md) options
3. Submit an issue on GitHub if you need assistance