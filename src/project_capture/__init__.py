"""Project Capture: AI-Ready Project Snapshot Tool.

A powerful tool for capturing project contents in AI-optimized formats.
"""

__version__ = "0.2.0"
__author__ = "Project Capture Team"
__email__ = "support@projectcapture.dev"

from project_capture.core.capture import capture_project_contents
from project_capture.core.config import load_config, save_config
from project_capture.core.types import ProjectConfig, AppConfig

__all__ = [
    "capture_project_contents",
    "load_config",
    "save_config",
    "ProjectConfig",
    "AppConfig",
    "__version__",
]