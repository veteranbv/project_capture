"""YAML output formatter for project snapshots."""
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ImportError:
    yaml = None

from project_capture.formats.base import BaseFormatter, ProjectSnapshot


class YAMLFormatter(BaseFormatter):
    """Formatter for YAML output format."""
    
    def __init__(self, output_path: Path):
        super().__init__(output_path)
        if yaml is None:
            raise ImportError(
                "PyYAML is required for YAML output format. "
                "Install it with: pip install pyyaml"
            )
    
    def format(self, snapshot: ProjectSnapshot) -> str:
        """Format the project snapshot as YAML.
        
        Args:
            snapshot: The project snapshot data
            
        Returns:
            YAML string representation
        """
        data = self._snapshot_to_dict(snapshot)
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)
    
    def write(self, snapshot: ProjectSnapshot) -> None:
        """Write the formatted snapshot to a YAML file.
        
        Args:
            snapshot: The project snapshot data
        """
        data = self._snapshot_to_dict(snapshot)
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write YAML file
        with open(self.output_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def _snapshot_to_dict(self, snapshot: ProjectSnapshot) -> Dict[str, Any]:
        """Convert snapshot to a dictionary for YAML serialization.
        
        Args:
            snapshot: The project snapshot data
            
        Returns:
            Dictionary representation of the snapshot
        """
        return {
            "metadata": {
                "project_name": snapshot.project_name,
                "root_directory": str(snapshot.root_directory),
                "timestamp": snapshot.timestamp,
                "include_in_prompt": snapshot.include_in_prompt,
                "statistics": snapshot.statistics,
            },
            "structure": {
                "directory_tree": snapshot.directory_tree,
                "file_count": len(snapshot.files),
            },
            "files": [
                {
                    "path": str(file.path),
                    "language": file.language,
                    "size": file.size,
                    "lines": file.lines,
                    "content": file.content,
                }
                for file in snapshot.files
            ],
        }