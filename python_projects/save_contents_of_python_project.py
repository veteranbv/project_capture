import os
import pathspec

def load_gitignore_patterns(root_dir):
    """Load .gitignore patterns from the root directory."""
    gitignore_path = os.path.join(root_dir, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as gitignore_file:
            patterns = gitignore_file.read().splitlines()
        return pathspec.PathSpec.from_lines('gitwildmatch', patterns)
    return None

def generate_tree(root_dir, gitignore_spec, prefix=''):
    """Generate a tree-like directory structure, respecting .gitignore."""
    tree_lines = []
    for subdir, dirs, files in os.walk(root_dir):
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

def save_project_contents(root_dir, output_file):
    gitignore_spec = load_gitignore_patterns(root_dir)

    with open(output_file, 'w', encoding='utf-8') as f:
        # Write an introduction
        f.write("# Project Documentation\n\n")
        f.write("This document contains a detailed look at the files within this project, excluding virtual environments, cache directories, and any files listed in .gitignore.\n\n")
        
        # Generate and write the directory tree
        f.write("## Directory Tree\n\n")
        tree = generate_tree(root_dir, gitignore_spec)
        f.write("```\n" + tree + "\n```\n")
        
        # Write file contents
        f.write("## File Contents\n\n")
        for subdir, dirs, files in os.walk(root_dir):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in {'__pycache__', 'venv'} and not gitignore_spec.match_file(os.path.relpath(os.path.join(subdir, d), root_dir))]

            for file in files:
                file_path = os.path.relpath(os.path.join(subdir, file), root_dir)
                if gitignore_spec and gitignore_spec.match_file(file_path):
                    continue
                
                if file.endswith(('.py', '.html', '.css', '.md', '.txt', '.sh')):
                    f.write(f"### {file_path}\n")
                    with open(os.path.join(subdir, file), 'r', encoding='utf-8') as content_file:
                        content = content_file.read()
                        f.write("```" + file.split('.')[-1] + "\n" + content + "\n```\n\n")  # Mark the content as code for better formatting

if __name__ == '__main__':
    root_directory = '.'  # Adjust if your script is not in the project root
    output_filename = 'project_contents.md'
    save_project_contents(root_directory, output_filename)
    print("Project contents saved to:", output_filename)