from enum import Enum, auto
from typing import Any, Dict, List, Literal, NotRequired, Optional, TypedDict, Union


class OutputFormat(Enum):
    """Supported output formats for project snapshots."""
    MARKDOWN = auto()
    HTML = auto()
    JSON = auto()
    TEXT = auto()


class ProjectStatistics(TypedDict):
    """Statistics about the project."""
    total_files: int
    total_directories: int
    total_lines: int
    file_types: Dict[str, int]  # Extension to count
    languages: Dict[str, int]  # Language to line count


class ProjectConfig(TypedDict):
    """Type definition for a project configuration."""
    project_name: str
    directory: str
    output_pattern: str
    include_in_prompt: bool
    
    # Required gitignore settings
    use_local_gitignore: bool
    use_project_gitignore: bool
    ignore_patterns: List[str]
    last_used: str
    
    # Optional settings with defaults
    output_format: NotRequired[Literal["markdown", "html", "json", "text"]]
    check_binary_content: NotRequired[bool]
    use_parallel_processing: NotRequired[bool]
    max_workers: NotRequired[Optional[int]]
    include_statistics: NotRequired[bool]


class AppConfig(TypedDict):
    """Type definition for the application configuration."""
    configurations: List[ProjectConfig]
    last_directory: NotRequired[str]
    theme: NotRequired[str]
    recent_projects: NotRequired[List[str]]
    default_ignore_templates: NotRequired[List[str]]


class ProjectContentsResult(TypedDict):
    """Type definition for the result of save_project_contents."""
    processed: int
    skipped: int
    errors: List[str]
    statistics: NotRequired[ProjectStatistics]
    elapsed_time: NotRequired[float]


def is_valid_project_config(obj: Any) -> bool:
    """
    Check if an object is a valid ProjectConfig.

    Args:
        obj (Any): The object to validate

    Returns:
        bool: True if the object is a valid ProjectConfig
    """
    # Required fields
    required_valid = (
        isinstance(obj, dict)
        and "project_name" in obj
        and isinstance(obj["project_name"], str)
        and "directory" in obj
        and isinstance(obj["directory"], str)
        and "output_pattern" in obj
        and isinstance(obj["output_pattern"], str)
        and "include_in_prompt" in obj
        and isinstance(obj["include_in_prompt"], bool)
        and "ignore_patterns" in obj
        and isinstance(obj["ignore_patterns"], list)
        and all(isinstance(p, str) for p in obj["ignore_patterns"])
        and "last_used" in obj
        and isinstance(obj["last_used"], str)
    )
    
    if not required_valid:
        return False
    
    # Gitignore settings - added in newer versions but might not be in older configs
    if "use_local_gitignore" in obj and not isinstance(obj["use_local_gitignore"], bool):
        return False
        
    if "use_project_gitignore" in obj and not isinstance(obj["use_project_gitignore"], bool):
        return False
    
    # Optional fields validation
    if "output_format" in obj and obj["output_format"] not in ("markdown", "html", "json", "text"):
        return False
        
    if "check_binary_content" in obj and not isinstance(obj["check_binary_content"], bool):
        return False
        
    if "use_parallel_processing" in obj and not isinstance(obj["use_parallel_processing"], bool):
        return False
        
    if "max_workers" in obj and obj["max_workers"] is not None and not isinstance(obj["max_workers"], int):
        return False
        
    if "include_statistics" in obj and not isinstance(obj["include_statistics"], bool):
        return False
    
    return True


def is_valid_app_config(obj: Any) -> bool:
    """
    Check if an object is a valid AppConfig.

    Args:
        obj (Any): The object to validate

    Returns:
        bool: True if the object is a valid AppConfig
    """
    # Basic validation
    if not isinstance(obj, dict) or "configurations" not in obj or not isinstance(obj["configurations"], list):
        return False
    
    # Validate each configuration
    if not all(is_valid_project_config(c) for c in obj["configurations"]):
        return False
    
    # Optional fields validation
    if "last_directory" in obj and not isinstance(obj["last_directory"], str):
        return False
        
    if "theme" in obj and not isinstance(obj["theme"], str):
        return False
        
    if "recent_projects" in obj:
        if not isinstance(obj["recent_projects"], list) or not all(isinstance(p, str) for p in obj["recent_projects"]):
            return False
            
    if "default_ignore_templates" in obj:
        if not isinstance(obj["default_ignore_templates"], list) or not all(isinstance(t, str) for t in obj["default_ignore_templates"]):
            return False
    
    return True
