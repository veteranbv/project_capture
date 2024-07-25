import logging
import pyperclip
from pathvalidate import sanitize_filename as validate_filename


def configure_logging():
    """Configure logging settings for the application."""
    logger = logging.getLogger("snapshot")
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler("project_snapshot.log")
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def copy_to_clipboard(text: str) -> bool:
    """Copy the given text to the system clipboard."""
    try:
        pyperclip.copy(text)
        return True
    except pyperclip.PyperclipException as e:
        logging.error(f"Error copying to clipboard: {str(e)}")
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize the filename to ensure it's valid and safe."""
    return validate_filename(filename)
