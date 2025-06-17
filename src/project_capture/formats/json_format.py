"""JSON output formatter for project snapshots."""
import json
from pathlib import Path
from typing import Any, Dict

from project_capture.formats.base import BaseFormatter, ProjectSnapshot


class JSONFormatter(BaseFormatter):
    """Formatter for JSON output format."""
    
    def format(self, snapshot: ProjectSnapshot) -> str:
        """Format the project snapshot as JSON.
        
        Args:
            snapshot: The project snapshot data
            
        Returns:
            JSON string representation
        """
        data = self._snapshot_to_dict(snapshot)
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def write(self, snapshot: ProjectSnapshot) -> None:
        """Write the formatted snapshot to a JSON file.
        
        Args:
            snapshot: The project snapshot data
        """
        data = self._snapshot_to_dict(snapshot)
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSON file
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _snapshot_to_dict(self, snapshot: ProjectSnapshot) -> Dict[str, Any]:
        """Convert snapshot to a dictionary for JSON serialization.
        
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