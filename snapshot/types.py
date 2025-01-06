from typing import Any, TypedDict


class ProjectConfig(TypedDict):
    """Type definition for a project configuration."""

    project_name: str
    directory: str
    output_pattern: str
    include_in_prompt: bool
    ignore_patterns: list[str]
    last_used: str


class AppConfig(TypedDict):
    """Type definition for the application configuration."""

    configurations: list[ProjectConfig]


class ProjectContentsResult(TypedDict):
    """Type definition for the result of save_project_contents."""

    processed: int
    skipped: int
    errors: list[str]


def is_valid_project_config(obj: Any) -> bool:
    """Check if an object is a valid ProjectConfig.

    Args:
        obj (Any): The object to validate

    Returns:
        bool: True if the object is a valid ProjectConfig
    """
    return (
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


def is_valid_app_config(obj: Any) -> bool:
    """Check if an object is a valid AppConfig.

    Args:
        obj (Any): The object to validate

    Returns:
        bool: True if the object is a valid AppConfig
    """
    return (
        isinstance(obj, dict)
        and "configurations" in obj
        and isinstance(obj["configurations"], list)
        and all(is_valid_project_config(c) for c in obj["configurations"])
    )
