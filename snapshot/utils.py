import logging
from pathlib import Path
import pyperclip

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str) -> bool:
    """
    Copy the given text to the system clipboard.

    Args:
        text (str): The text to copy to the clipboard.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        pyperclip.copy(text)
        return True
    except pyperclip.PyperclipException as e:
        logger.error(f"Error copying to clipboard: {str(e)}")
        return False


def sanitize_path(path: str) -> Path:
    """
    Sanitize and validate the given file path.

    Args:
        path (str): The file path to sanitize.

    Returns:
        Path: The sanitized path.

    Raises:
        ValueError: If the path is invalid or potentially dangerous.
    """
    try:
        sanitized_path = Path(path).resolve()
        if not sanitized_path.is_relative_to(Path.cwd()):
            raise ValueError("Path is outside the current working directory")
        return sanitized_path
    except (ValueError, RuntimeError) as e:
        raise ValueError(f"Invalid or potentially dangerous path: {str(e)}")
