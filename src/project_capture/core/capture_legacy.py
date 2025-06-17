import logging
import mmap
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import pathspec  # type: ignore

from snapshot.constants import BINARY_EXTENSIONS, LANGUAGE_MAP
from snapshot.exceptions import ProjectSnapshotError
from snapshot.types import ProjectContentsResult
from snapshot.utils import is_binary_file_content

# Set up logging
logger = logging.getLogger(__name__)


def is_binary_file(file_path: Path) -> bool:
    """
    Check if a file is likely to be binary based on its extension.
    
    Args:
        file_path (Path): Path to the file
        
    Returns:
        bool: True if the file is likely binary, False otherwise
    """
    return file_path.suffix.lower() in BINARY_EXTENSIONS


def load_gitignore_patterns(directory: Path) -> pathspec.PathSpec:
    """
    Load .gitignore patterns from the specified directory.
    
    Args:
        directory (Path): Directory containing .gitignore file
        
    Returns:
        pathspec.PathSpec: Object containing the patterns from .gitignore
    """
    gitignore_path = directory / ".gitignore"
    patterns = []
    if gitignore_path.exists():
        try:
            with gitignore_path.open("r") as file:
                patterns = [
                    line.strip()
                    for line in file
                    if line.strip() and not line.startswith("#")
                ]
        except IOError as e:
            logger.warning(f"Error reading .gitignore file: {str(e)}")
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def get_language(file_extension: str) -> str:
    """
    Get the language identifier for syntax highlighting.

    Args:
        file_extension (str): The file extension including the dot (e.g. '.py')

    Returns:
        str: The language identifier for syntax highlighting, or empty string if unknown
    """
    return LANGUAGE_MAP.get(file_extension.lower(), "")


def escape_markdown(text: str) -> str:
    """
    Escape markdown syntax in the given text.

    Args:
        text (str): The text to escape

    Returns:
        str: The escaped text with markdown syntax characters escaped
    """
    text = text.replace("```", "\\`\\`\\`")
    chars_to_escape = r"\_*[]()#+-.!"
    for char in chars_to_escape:
        text = text.replace(char, "\\" + char)
    return text


def read_file_content(file_path: Path, check_binary_content: bool = True) -> str:
    """
    Read the content of a file, using memory mapping for large files.
    
    Args:
        file_path (Path): Path to the file to read
        check_binary_content (bool, optional): Whether to check file content for binary data. Defaults to True.
        
    Returns:
        str: The file content as text
        
    Raises:
        ProjectSnapshotError: If the file is binary or cannot be read
    """
    # Check if it's a binary file by extension
    if is_binary_file(file_path):
        raise ProjectSnapshotError(f"Skipping binary file: {file_path}")

    # Additional content-based check if requested
    if check_binary_content and is_binary_file_content(file_path, check_content=True):
        raise ProjectSnapshotError(f"Skipping binary file (content check): {file_path}")

    try:
        file_size = file_path.stat().st_size
        if file_size > 1_000_000:  # Use mmap for files larger than 1MB
            try:
                with file_path.open("rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
                        return m.read().decode("utf-8", errors="replace")
            except (ValueError, OSError) as e:
                logger.warning(
                    f"Error using mmap for {file_path}: {str(e)}. Falling back to normal read."
                )
                return file_path.read_text(encoding="utf-8", errors="replace")
        else:
            return file_path.read_text(encoding="utf-8", errors="replace")
    except (IOError, UnicodeDecodeError) as e:
        raise ProjectSnapshotError(f"Error reading file {file_path}: {str(e)}")


def process_file(
    file_path: Path, 
    root_directory: Path, 
    check_binary_content: bool = True
) -> Tuple[str, int, int, List[str]]:
    """
    Process a single file for inclusion in the snapshot.
    
    Args:
        file_path (Path): Path to the file to process
        root_directory (Path): Root directory of the project
        check_binary_content (bool, optional): Whether to check for binary content. Defaults to True.
        
    Returns:
        Tuple[str, int, int, List[str]]: (file content markdown, processed count, skipped count, errors)
    """
    processed = 0
    skipped = 0
    errors = []
    content_parts = []
    
    relative_file_path = file_path.relative_to(root_directory)
    content_parts.append(f"### {relative_file_path}\n\n")
    
    try:
        file_content = read_file_content(file_path, check_binary_content)
        language = get_language(file_path.suffix)
        
        if language == "markdown":
            content_parts.append(f"```{language}\n")
            content_parts.append(escape_markdown(file_content))
        else:
            content_parts.append(f"```{language}\n")
            content_parts.append(file_content)
            
        if not file_content.endswith("\n"):
            content_parts.append("\n")
            
        content_parts.append("```\n\n")
        processed += 1
        
    except ProjectSnapshotError as e:
        if "Skipping binary file" in str(e):
            logger.info(str(e))
            skipped += 1
            content_parts.append("```\n")
            content_parts.append("Binary file, content not displayed.\n")
            content_parts.append("```\n\n")
        else:
            logger.warning(str(e))
            errors.append(str(e))
            content_parts.append("```\n")
            content_parts.append("File content not displayed due to an error.\n")
            content_parts.append("```\n\n")
    
    return "".join(content_parts), processed, skipped, errors


def save_project_contents(
    root_directory: Path,
    output_filename: Path,
    project_name: str,
    include_in_prompt: bool,
    additional_patterns: Optional[List[str]] = None,
    use_local_gitignore: bool = True,
    use_project_gitignore: bool = True,
    use_parallel_processing: bool = True,
    max_workers: Optional[int] = None,
    check_binary_content: bool = True,
) -> ProjectContentsResult:
    """
    Save the contents of the project to a markdown file.

    Args:
        root_directory (Path): The root directory of the project
        output_filename (Path): The output file path
        project_name (str): The name of the project
        include_in_prompt (bool): Whether to include the content in an AI prompt
        additional_patterns (Optional[List[str]], optional): Additional patterns to ignore. Defaults to None.
        use_local_gitignore (bool, optional): Whether to use local .gitignore patterns. Defaults to True.
        use_project_gitignore (bool, optional): Whether to use project .gitignore patterns. Defaults to True.
        use_parallel_processing (bool, optional): Whether to use parallel processing for file reading. Defaults to True.
        max_workers (Optional[int], optional): Maximum number of worker threads. Defaults to None (uses CPU count).
        check_binary_content (bool, optional): Whether to check file content for binary data. Defaults to True.

    Returns:
        ProjectContentsResult: A dictionary containing:
            - processed (int): Number of files processed
            - skipped (int): Number of files skipped
            - errors (list[str]): List of error messages
    """
    start_time = time.time()
    logger.info(f"Starting project snapshot from: {root_directory}")

    processed = 0
    skipped = 0
    errors = []
    
    # Initialize content with header
    content = [f"# Project Snapshot: {project_name}\n\n"]
    
    try:
        # Load gitignore patterns based on settings
        root_patterns = (
            load_gitignore_patterns(Path.cwd())
            if use_local_gitignore
            else pathspec.PathSpec.from_lines("gitwildmatch", [])
        )
        target_patterns = (
            load_gitignore_patterns(root_directory)
            if use_project_gitignore
            else pathspec.PathSpec.from_lines("gitwildmatch", [])
        )

        # Create a new PathSpec for additional patterns if provided
        additional_patterns = additional_patterns or []
        custom_patterns = pathspec.PathSpec.from_lines(
            "gitwildmatch", additional_patterns
        )

        # Combine all patterns
        all_patterns = root_patterns + target_patterns + custom_patterns

        # Add AI prompt wrapper if requested
        if include_in_prompt:
            content.append("<project_contents>\n")

        # First pass: generate directory tree
        logger.info("Generating directory tree...")
        content.append("## Directory Tree\n\n```\n")
        
        # Store valid files for later processing
        valid_files = []

        for dirpath, dirnames, filenames in os.walk(root_directory):
            rel_path = Path(dirpath).relative_to(root_directory)

            # Filter directories and files based on patterns
            dirnames[:] = [
                d for d in dirnames if not all_patterns.match_file(rel_path / d)
            ]
            filenames = [
                f for f in filenames if not all_patterns.match_file(rel_path / f)
            ]

            # Add directory to tree
            level = len(rel_path.parts)
            indent = "    " * level
            content.append(f"{indent}{Path(dirpath).name}/\n")
            
            # Add files to tree
            subindent = "    " * (level + 1)
            for filename in filenames:
                content.append(f"{subindent}{filename}\n")
                valid_files.append(Path(dirpath) / filename)
                
        content.append("```\n\n")
        
        # Second pass: process file contents
        logger.info(f"Processing {len(valid_files)} files{'using parallel processing' if use_parallel_processing else ''}...")
        content.append("## File Contents\n\n")
        
        # Process files (either in parallel or sequentially)
        file_contents = []
        
        if use_parallel_processing and valid_files:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all file processing tasks
                future_to_file = {
                    executor.submit(process_file, file_path, root_directory, check_binary_content): file_path 
                    for file_path in valid_files
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_file):
                    file_content, proc_count, skip_count, file_errors = future.result()
                    file_contents.append((future_to_file[future], file_content))
                    processed += proc_count
                    skipped += skip_count
                    errors.extend(file_errors)
                    
            # Sort file contents by relative path to maintain consistent order
            file_contents.sort(key=lambda x: str(x[0].relative_to(root_directory)))
            for _, file_content in file_contents:
                content.append(file_content)
        else:
            # Process files sequentially
            for file_path in valid_files:
                file_content, proc_count, skip_count, file_errors = process_file(
                    file_path, root_directory, check_binary_content
                )
                content.append(file_content)
                processed += proc_count
                skipped += skip_count
                errors.extend(file_errors)

        # Close AI prompt wrapper if needed
        if include_in_prompt:
            content.append("</project_contents>\n")

        # Create output directory if it doesn't exist
        output_filename.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with output_filename.open("w", encoding="utf-8") as f:
            f.writelines(content)

        elapsed_time = time.time() - start_time
        logger.info(
            f"Project snapshot completed in {elapsed_time:.2f}s. "
            f"Processed: {processed}, Skipped: {skipped}, Errors: {len(errors)}"
        )

        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Error saving project contents: {str(e)}")
        raise ProjectSnapshotError(f"Failed to save project contents: {str(e)}")
