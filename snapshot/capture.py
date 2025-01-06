import logging
import mmap
import os
from pathlib import Path

import pathspec  # type: ignore

from snapshot.exceptions import ProjectSnapshotError
from snapshot.types import ProjectContentsResult

logger = logging.getLogger(__name__)

BINARY_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".pyc",
}


def is_binary_file(file_path: Path) -> bool:
    """Check if a file is likely to be binary based on its extension."""
    return file_path.suffix.lower() in BINARY_EXTENSIONS


def load_gitignore_patterns(directory: Path) -> pathspec.PathSpec:
    """Load .gitignore patterns from the specified directory."""
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
    """Get the language identifier for syntax highlighting.

    Args:
        file_extension (str): The file extension including the dot (e.g. '.py')

    Returns:
        str: The language identifier for syntax highlighting, or empty string if unknown
    """
    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".java": "java",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".go": "go",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".rs": "rust",
        ".scala": "scala",
        ".md": "markdown",
        ".markdown": "markdown",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".xml": "xml",
        ".sql": "sql",
        ".sh": "bash",
        ".bash": "bash",
        ".ps1": "powershell",
        ".dockerfile": "dockerfile",
        ".txt": "text",
    }
    return language_map.get(file_extension.lower(), "")


def escape_markdown(text: str) -> str:
    """Escape markdown syntax in the given text.

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


def read_file_content(file_path: Path) -> str:
    """Read the content of a file, using memory mapping for large files."""
    if is_binary_file(file_path):
        raise ProjectSnapshotError(f"Skipping binary file: {file_path}")

    try:
        file_size = file_path.stat().st_size
        if file_size > 1_000_000:  # Use mmap for files larger than 1MB
            try:
                with file_path.open("rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
                        return m.read().decode("utf-8")
            except (ValueError, OSError) as e:
                logger.warning(
                    f"Error using mmap for {file_path}: {str(e)}. Falling back to normal read."
                )
                return file_path.read_text(encoding="utf-8")
        else:
            return file_path.read_text(encoding="utf-8")
    except (IOError, UnicodeDecodeError) as e:
        raise ProjectSnapshotError(f"Error reading file {file_path}: {str(e)}")


def save_project_contents(
    root_directory: Path,
    output_filename: Path,
    project_name: str,
    include_in_prompt: bool,
    additional_patterns: list[str] | None = None,
    use_local_gitignore: bool = True,
    use_project_gitignore: bool = True,
) -> ProjectContentsResult:
    """Save the contents of the project to a markdown file.

    Args:
        root_directory (Path): The root directory of the project
        output_filename (Path): The output file path
        project_name (str): The name of the project
        include_in_prompt (bool): Whether to include the content in an AI prompt
        additional_patterns (list[str] | None, optional): Additional patterns to ignore. Defaults to None.
        use_local_gitignore (bool, optional): Whether to use local .gitignore patterns. Defaults to True.
        use_project_gitignore (bool, optional): Whether to use project .gitignore patterns. Defaults to True.

    Returns:
        ProjectContentsResult: A dictionary containing:
            - processed (int): Number of files processed
            - skipped (int): Number of files skipped
            - errors (list[str]): List of error messages
    """
    logger.info(f"Saving project contents from: {root_directory}")

    processed = 0
    skipped = 0
    errors = []
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

        if include_in_prompt:
            content.append("<project_contents>\n")

        content.append("## Directory Tree\n\n```\n")

        for dirpath, dirnames, filenames in os.walk(root_directory):
            rel_path = Path(dirpath).relative_to(root_directory)

            dirnames[:] = [
                d for d in dirnames if not all_patterns.match_file(rel_path / d)
            ]
            filenames = [
                f for f in filenames if not all_patterns.match_file(rel_path / f)
            ]

            level = len(rel_path.parts)
            indent = "    " * level
            content.append(f"{indent}{Path(dirpath).name}/\n")
            subindent = "    " * (level + 1)
            for filename in filenames:
                content.append(f"{subindent}{filename}\n")
        content.append("```\n\n")

        content.append("## File Contents\n\n")
        for dirpath, dirnames, filenames in os.walk(root_directory):
            rel_path = Path(dirpath).relative_to(root_directory)

            dirnames[:] = [
                d for d in dirnames if not all_patterns.match_file(rel_path / d)
            ]
            filenames = [
                f for f in filenames if not all_patterns.match_file(rel_path / f)
            ]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                relative_file_path = file_path.relative_to(root_directory)
                content.append(f"### {relative_file_path}\n\n")
                try:
                    file_content = read_file_content(file_path)
                    language = get_language(file_path.suffix)
                    if language == "markdown":
                        content.append(f"```{language}\n")
                        content.append(escape_markdown(file_content))
                    else:
                        content.append(f"```{language}\n")
                        content.append(file_content)
                    if not file_content.endswith("\n"):
                        content.append("\n")
                    content.append("```\n\n")
                    processed += 1
                except ProjectSnapshotError as e:
                    if "Skipping binary file" in str(e):
                        logger.info(str(e))
                        skipped += 1
                    else:
                        logger.warning(str(e))
                        errors.append(str(e))
                        content.append("```\n")
                        content.append("File content not displayed due to an error.\n")
                        content.append("```\n\n")

        if include_in_prompt:
            content.append("</project_contents>\n")

        # Create output directory if it doesn't exist
        output_filename.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with output_filename.open("w") as f:
            f.writelines(content)

        return {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"Error saving project contents: {str(e)}")
        raise ProjectSnapshotError(f"Failed to save project contents: {str(e)}")
