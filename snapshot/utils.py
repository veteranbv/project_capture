import os
import logging
import pathspec

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def load_gitignore_patterns(root_dir):
    """Load .gitignore patterns from the specified directory."""
    gitignore_path = os.path.join(root_dir, '.gitignore')
    patterns = []
    if os.path.exists(gitignore_path):
        logging.info(f"Reading .gitignore from: {gitignore_path}")
        with open(gitignore_path, 'r', encoding='utf-8') as gitignore_file:
            patterns.extend(gitignore_file.read().splitlines())
    else:
        logging.warning(f"No .gitignore found at: {gitignore_path}")
    return patterns

def combine_gitignore_patterns(root_patterns, target_patterns):
    """Combine patterns from root and target .gitignore files."""
    combined_patterns = root_patterns + target_patterns
    logging.debug(f"Combined .gitignore patterns: {combined_patterns}")
    return pathspec.PathSpec.from_lines('gitwildmatch', combined_patterns)

def generate_tree(root_dir, gitignore_spec):
    """Generate a tree-like directory structure, respecting .gitignore."""
    tree_lines = []
    for subdir, dirs, files in os.walk(root_dir):
        logging.debug(f"Traversing directory: {subdir}")
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if not gitignore_spec.match_file(os.path.relpath(os.path.join(subdir, d), root_dir))]
        
        # Add directory to the tree
        level = subdir.replace(root_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        subtree = os.path.basename(subdir) + '/'
        tree_lines.append(f"{indent}{subtree}")

        # Add files to the tree
        for file in files:
            file_path = os.path.relpath(os.path.join(subdir, file), root_dir)
            if not gitignore_spec.match_file(file_path):
                sub_indent = ' ' * 4 * (level + 1)
                tree_lines.append(f"{sub_indent}{file}")

    return "\n".join(tree_lines)