import os
import logging

def load_gitignore_patterns(directory):
    gitignore_path = os.path.join(directory, '.gitignore')
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as file:
            patterns = [line.strip() for line in file if line.strip() and not line.startswith('#')]
    return patterns

def is_ignored(path, patterns):
    for pattern in patterns:
        if pattern in path:
            return True
    return False

def save_project_contents(root_directory, output_filename):
    logging.info(f"Saving project contents from: {root_directory}")

    # Load .gitignore patterns from both root and target directories
    root_patterns = load_gitignore_patterns(os.getcwd())
    target_patterns = load_gitignore_patterns(root_directory)
    all_patterns = set(root_patterns + target_patterns)
    all_patterns.add('.git/')  # Explicitly exclude .git directory
    all_patterns.add('.gitignore')  # Explicitly exclude .gitignore file
    all_patterns.add('yarn.lock')  # Explicitly exclude yarn.lock file

    with open(output_filename, 'w') as f:
        f.write("# Project Documentation\n\n")
        f.write("This document contains a detailed look at the files within this project, excluding build artifacts, dependencies, and any files listed in .gitignore.\n\n")
        f.write("## Directory Tree\n\n")
        f.write("```\n")
        for dirpath, dirnames, filenames in os.walk(root_directory):
            # Exclude specified directories and files based on .gitignore patterns
            dirnames[:] = [d for d in dirnames if not is_ignored(os.path.join(dirpath, d), all_patterns)]
            filenames = [f for f in filenames if not is_ignored(os.path.join(dirpath, f), all_patterns)]

            # Print the directory tree structure
            level = dirpath.replace(root_directory, '').count(os.sep)
            indent = ' ' * 4 * (level)
            f.write(f"{indent}{os.path.basename(dirpath)}/\n")
            subindent = ' ' * 4 * (level + 1)
            for filename in filenames:
                f.write(f"{subindent}{filename}\n")
        f.write("```\n\n")

        f.write("## File Contents\n\n")
        for dirpath, dirnames, filenames in os.walk(root_directory):
            # Exclude specified directories and files based on .gitignore patterns
            dirnames[:] = [d for d in dirnames if not is_ignored(os.path.join(dirpath, d), all_patterns)]
            filenames = [f for f in filenames if not is_ignored(os.path.join(dirpath, f), all_patterns)]

            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                f.write(f"### {file_path}\n\n")
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        f.write("```\n")
                        f.write(file.read())
                        f.write("\n```\n\n")
                except UnicodeDecodeError:
                    logging.warning(f"Skipping binary file: {file_path}")
                    f.write("```\n")
                    f.write("Binary file content not displayed.\n")
                    f.write("```\n\n")

    logging.info(f"Project contents saved to: {output_filename}")