import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from project_capture.core.exceptions import ProjectSnapshotError
from project_capture.core.types import AppConfig, ProjectConfig, is_valid_app_config, is_valid_project_config
from project_capture.core.utils import sanitize_filename

# Default configuration file path
CONFIG_FILE = "config.json"
# Maximum configurations per project
MAX_CONFIGS_PER_PROJECT = 5

logger = logging.getLogger("snapshot")


def load_config(config_file: str = CONFIG_FILE) -> AppConfig:
    """
    Load configuration from the JSON file with validation.

    Args:
        config_file (str, optional): Path to the configuration file. Defaults to CONFIG_FILE.

    Returns:
        AppConfig: The loaded configuration or a default configuration if the file doesn't exist or is invalid.
    """
    if Path(config_file).exists():
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                if not is_valid_app_config(config):
                    raise ValueError("Invalid configuration structure")
                return cast(AppConfig, config)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                f"Error loading {config_file}: {str(e)}. Using default configuration."
            )
    return cast(AppConfig, {"configurations": []})


def save_config(config: AppConfig, config_file: str = CONFIG_FILE) -> None:
    """
    Save configuration to the JSON file.

    Args:
        config (AppConfig): The configuration to save.
        config_file (str, optional): Path to the configuration file. Defaults to CONFIG_FILE.
    """
    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        logger.error(f"Error writing to {config_file}: {str(e)}")
        raise ProjectSnapshotError(f"Failed to save configuration: {str(e)}")


def create_default_config(root_directory: str | Path) -> ProjectConfig:
    """
    Create a default configuration for a project.

    Args:
        root_directory (str | Path): The root directory of the project.

    Returns:
        ProjectConfig: A default configuration.
    """
    project_name = Path(root_directory).name
    timestamp = "{time}"
    
    config = {
        "project_name": project_name,
        "directory": str(root_directory),
        "output_pattern": f"{project_name}_contents-{timestamp}.md",
        "include_in_prompt": True,
        "use_local_gitignore": True,
        "use_project_gitignore": True,
        "ignore_patterns": [],
        "last_used": datetime.now().strftime("%Y-%m-%d"),
    }
    
    if not is_valid_project_config(config):
        raise ProjectSnapshotError("Failed to create valid default configuration")
    
    return cast(ProjectConfig, config)


def is_duplicate_config(new_config: ProjectConfig, existing_configs: List[ProjectConfig]) -> bool:
    """
    Check if a configuration is a duplicate of an existing one.

    Args:
        new_config (ProjectConfig): The new configuration to check.
        existing_configs (List[ProjectConfig]): List of existing configurations.

    Returns:
        bool: True if the configuration is a duplicate, False otherwise.
    """
    for config in existing_configs:
        if (
            config["project_name"] == new_config["project_name"]
            and config["directory"] == new_config["directory"]
            and config["output_pattern"] == new_config["output_pattern"]
            and config["include_in_prompt"] == new_config["include_in_prompt"]
        ):
            return True
    return False


def add_configuration(app_config: AppConfig, new_config: ProjectConfig) -> None:
    """
    Add a new configuration, managing the maximum number of configurations per project.

    Args:
        app_config (AppConfig): The application configuration.
        new_config (ProjectConfig): The new configuration to add.
    """
    matching_configs = [
        c for c in app_config["configurations"] 
        if c["directory"] == new_config["directory"]
    ]

    if len(matching_configs) >= MAX_CONFIGS_PER_PROJECT:
        # Remove the oldest configuration for this project
        oldest_config = min(
            matching_configs,
            key=lambda x: datetime.strptime(x["last_used"], "%Y-%m-%d"),
        )
        app_config["configurations"].remove(oldest_config)
        logger.info(f"Removed oldest configuration for {new_config['project_name']}")

    app_config["configurations"].append(new_config)
    logger.info(f"Added new configuration for {new_config['project_name']}")


def update_configuration(app_config: AppConfig, index: int, updated_config: ProjectConfig) -> None:
    """
    Update an existing configuration.

    Args:
        app_config (AppConfig): The application configuration.
        index (int): The index of the configuration to update.
        updated_config (ProjectConfig): The updated configuration.
    """
    if 0 <= index < len(app_config["configurations"]):
        app_config["configurations"][index] = updated_config
        logger.info(f"Updated configuration for {updated_config['project_name']}")
    else:
        raise ProjectSnapshotError(f"Invalid configuration index: {index}")


def delete_configuration(app_config: AppConfig, index: int) -> None:
    """
    Delete a configuration.

    Args:
        app_config (AppConfig): The application configuration.
        index (int): The index of the configuration to delete.
    """
    if 0 <= index < len(app_config["configurations"]):
        deleted_config = app_config["configurations"].pop(index)
        logger.info(f"Deleted configuration for {deleted_config['project_name']}")
    else:
        raise ProjectSnapshotError(f"Invalid configuration index: {index}")