import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pyperclip
from pathvalidate import sanitize_filename as validate_filename


def configure_logging(log_file: str = "project_snapshot.log"):
    """
    Configure logging settings for the application.
    
    Args:
        log_file (str, optional): Path to the log file. Defaults to "project_snapshot.log".
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger("snapshot")
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # File handler for logging to a file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add console handler if running from command line
    if sys.stdin.isatty():
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_format = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
    return logger


def copy_to_clipboard(text: str) -> bool:
    """
    Copy the given text to the system clipboard.
    
    Args:
        text (str): Text to copy to clipboard
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        logging.error(f"Error copying to clipboard: {str(e)}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize the filename to ensure it's valid and safe.
    
    Args:
        filename (str): Filename to sanitize
        
    Returns:
        str: Sanitized filename
    """
    return validate_filename(filename)


def get_subdirectories(path: str | Path) -> List[Path]:
    """
    Get all subdirectories in the given path.
    
    Args:
        path (str | Path): The directory path to scan
        
    Returns:
        List[Path]: List of subdirectory paths
    """
    try:
        return [d for d in Path(path).iterdir() if d.is_dir()]
    except (PermissionError, FileNotFoundError) as e:
        logging.error(f"Error getting subdirectories of {path}: {str(e)}")
        return []


def get_output_path(
    project_name: str, 
    output_pattern: str, 
    base_dir: Optional[Path] = None
) -> Path:
    """
    Get the output file path based on the project name and output pattern.
    
    Args:
        project_name (str): The name of the project
        output_pattern (str): The output filename pattern
        base_dir (Optional[Path]): Base directory for output. Defaults to script location.
        
    Returns:
        Path: The full output file path
    """
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    output_filename = output_pattern.format(time=timestamp)
    
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
        
    output_path = base_dir / "output" / project_name / output_filename
    return output_path


def is_binary_file_content(file_path: Path, check_content: bool = False) -> bool:
    """
    Enhanced method to check if a file is binary by examining content.
    
    Args:
        file_path (Path): Path to the file to check
        check_content (bool, optional): Whether to examine file content. Defaults to False.
        
    Returns:
        bool: True if file is binary, False otherwise
    """
    from snapshot.capture import BINARY_EXTENSIONS
    
    # First use fast extension check
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True
        
    # For uncertain files or when forced, check content (first 1024 bytes)
    if check_content:
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk  # Binary files typically contain null bytes
        except Exception:
            return True  # Consider unreadable files as binary for safety
            
    return False
