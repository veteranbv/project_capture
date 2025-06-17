"""Base formatter class for output formats."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class FileContent:
    """Represents a file with its content and metadata."""
    path: Path
    content: str
    language: str
    size: int
    lines: int


@dataclass
class ProjectSnapshot:
    """Complete project snapshot data."""
    project_name: str
    root_directory: Path
    directory_tree: str
    files: List[FileContent]
    statistics: Dict[str, any]
    timestamp: str
    include_in_prompt: bool = False


class BaseFormatter(ABC):
    """Abstract base class for output formatters."""
    
    def __init__(self, output_path: Path):
        self.output_path = output_path
    
    @abstractmethod
    def format(self, snapshot: ProjectSnapshot) -> str:
        """Format the project snapshot into the desired output format.
        
        Args:
            snapshot: The project snapshot data
            
        Returns:
            Formatted string representation
        """
        pass
    
    @abstractmethod
    def write(self, snapshot: ProjectSnapshot) -> None:
        """Write the formatted snapshot to the output file.
        
        Args:
            snapshot: The project snapshot data
        """
        pass
    
    def get_file_extension(self) -> str:
        """Get the appropriate file extension for this format.
        
        Returns:
            File extension including the dot (e.g., '.md', '.json')
        """
        return self.output_path.suffix