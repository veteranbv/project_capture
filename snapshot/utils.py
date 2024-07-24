import logging
from pathlib import Path
from typing import List
import pathspec

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def load_gitignore_patterns(root_dir: Path) -> List[str]:
    """Load .gitignore patterns from the specified directory."""
    gitignore_path = root_dir / '.gitignore'
    if gitignore_path.exists():
        logging.info(f"Reading .gitignore from: {gitignore_path}")
        return gitignore_path.read_text(encoding='utf-8').splitlines()
    else:
        logging.warning(f"No .gitignore found at: {gitignore_path}")
        return []

def combine_gitignore_patterns(root_patterns: List[str], target_patterns: List[str]) -> pathspec.PathSpec:
    """Combine patterns from root and target .gitignore files."""
    combined_patterns = root_patterns + target_patterns
    logging.debug(f"Combined .gitignore patterns: {combined_patterns}")
    return pathspec.PathSpec.from_lines('gitwildmatch', combined_patterns)

def generate_tree(root_dir: Path, gitignore_spec: pathspec.PathSpec) -> str:
    """Generate a tree-like directory structure, respecting .gitignore."""
    tree_lines = []
    for subdir, dirs, files in root_dir.walk():
        logging.debug(f"Traversing directory: {subdir}")
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if not gitignore_spec.match_file(subdir.joinpath(d).relative_to(root_dir))]
        
        # Add directory to the tree
        level = len(subdir.relative_to(root_dir).parts)
        indent = ' ' * 4 * level
        subtree = subdir.name + '/'
        tree_lines.append(f"{indent}{subtree}")

        # Add files to the tree
        for file in files:
            file_path = subdir.joinpath(file).relative_to(root_dir)
            if not gitignore_spec.match_file(file_path):
                sub_indent = ' ' * 4 * (level + 1)
                tree_lines.append(f"{sub_indent}{file}")

    return "\n".join(tree_lines)