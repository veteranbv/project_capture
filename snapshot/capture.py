import logging
import os
from pathlib import Path
import pathspec
import mmap
from snapshot.exceptions import ProjectSnapshotError

logger = logging.getLogger(__name__)

def load_gitignore_patterns(directory: Path) -> pathspec.PathSpec:
    """
    Load .gitignore patterns from the specified directory.

    Args:
        directory (Path): The directory containing the .gitignore file.

    Returns:
        pathspec.PathSpec: A PathSpec object containing the gitignore patterns.
    """
    gitignore_path = directory / '.gitignore'
    patterns = []
    if gitignore_path.exists():
        try:
            with gitignore_path.open('r') as file:
                patterns = [line.strip() for line in file if line.strip() and not line.startswith('#')]
        except IOError as e:
            logger.warning(f"Error reading .gitignore file: {str(e)}")
    return pathspec.PathSpec.from_lines('gitwildmatch', patterns)

def get_language(file_extension):
    """
    Get the language identifier for syntax highlighting.

    Args:
        file_extension (str): The file extension.

    Returns:
        str: The language identifier for syntax highlighting.
    """
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.java': 'java',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.rs': 'rust',
        '.scala': 'scala',
        '.md': 'markdown',
        '.markdown': 'markdown',
        '.json': 'json',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.xml': 'xml',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bash': 'bash',
        '.ps1': 'powershell',
        '.dockerfile': 'dockerfile',
        '.txt': 'text'
    }

    return language_map.get(file_extension.lower(), '')

def escape_markdown(text):
    """
    Escape markdown syntax in the given text.

    Args:
        text (str): The text to escape.

    Returns:
        str: The escaped text.
    """
    text = text.replace('```', '\\`\\`\\`')
    chars_to_escape = r'\_*[]()#+-.!'
    for char in chars_to_escape:
        text = text.replace(char, '\\' + char)
    return text

def read_file_content(file_path: Path) -> str:
    """
    Read the content of a file, using memory mapping for large files.

    Args:
        file_path (Path): The path to the file.

    Returns:
        str: The content of the file.

    Raises:
        ProjectSnapshotError: If there's an error reading the file.
    """
    try:
        file_size = file_path.stat().st_size
        if file_size > 1_000_000:  # Use mmap for files larger than 1MB
            try:
                with file_path.open('rb') as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
                        return m.read().decode('utf-8')
            except (ValueError, OSError) as e:
                logger.warning(f"Error using mmap for {file_path}: {str(e)}. Falling back to normal read.")
                return file_path.read_text(encoding='utf-8')
        else:
            return file_path.read_text(encoding='utf-8')
    except (IOError, UnicodeDecodeError) as e:
        raise ProjectSnapshotError(f"Error reading file {file_path}: {str(e)}")

def save_project_contents(root_directory: Path, output_filename: Path, project_name: str, include_in_prompt: bool):
    """
    Save the contents of the project to a markdown file.

    Args:
        root_directory (Path): The root directory of the project.
        output_filename (Path): The path to save the output markdown file.
        project_name (str): The name of the project.
        include_in_prompt (bool): Whether to include the project content in the AI prompt.

    Raises:
        ProjectSnapshotError: If there's an error during the process.
    """
    logger.info(f"Saving project contents from: {root_directory}")

    try:
        root_patterns = load_gitignore_patterns(Path.cwd())
        target_patterns = load_gitignore_patterns(root_directory)
        
        all_patterns = root_patterns + target_patterns

        content = [f"# Project Snapshot: {project_name}\n\n"]

        if include_in_prompt:
            content.append("<project_contents>\n")

        content.append("## Directory Tree\n\n```\n")
        
        for dirpath, dirnames, filenames in os.walk(root_directory):
            rel_path = Path(dirpath).relative_to(root_directory)
            
            dirnames[:] = [d for d in dirnames if not all_patterns.match_file(rel_path / d)]
            filenames = [f for f in filenames if not all_patterns.match_file(rel_path / f)]

            level = len(rel_path.parts)
            indent = '    ' * level
            content.append(f"{indent}{Path(dirpath).name}/\n")
            subindent = '    ' * (level + 1)
            for filename in filenames:
                content.append(f"{subindent}{filename}\n")
        content.append("```\n\n")

        content.append("## File Contents\n\n")
        for dirpath, dirnames, filenames in os.walk(root_directory):
            rel_path = Path(dirpath).relative_to(root_directory)
            
            dirnames[:] = [d for d in dirnames if not all_patterns.match_file(rel_path / d)]
            filenames = [f for f in filenames if not all_patterns.match_file(rel_path / f)]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                relative_file_path = file_path.relative_to(root_directory)
                content.append(f"### {relative_file_path}\n\n")
                try:
                    file_content = read_file_content(file_path)
                    language = get_language(file_path.suffix)
                    if language == 'markdown':
                        content.append(f"```{language}\n")
                        content.append(escape_markdown(file_content))
                    else:
                        content.append(f"```{language}\n")
                        content.append(file_content)
                    if not file_content.endswith('\n'):
                        content.append("\n")
                    content.append("```\n\n")
                except ProjectSnapshotError as e:
                    logger.warning(str(e))
                    content.append("```\n")
                    content.append("File content not displayed due to an error.\n")
                    content.append("```\n\n")

        if include_in_prompt:
            content.append("</project_contents>\n\n")
            try:
                with open('prompt.txt', 'r') as f:
                    content.append(f.read())
            except IOError as e:
                logger.error(f"Error reading prompt.txt: {str(e)}")
                content.append("Error: Unable to include prompt content.\n")

        with open(output_filename, 'w') as f:
            f.write(''.join(content))

        logger.info(f"Project contents saved to: {output_filename}")
    except Exception as e:
        raise ProjectSnapshotError(f"Error saving project contents: {str(e)}")