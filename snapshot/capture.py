import os
import logging
from pathlib import Path
import pathspec

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_gitignore_patterns(directory: Path) -> pathspec.PathSpec:
    gitignore_path = directory / '.gitignore'
    patterns = []
    if gitignore_path.exists():
        with gitignore_path.open('r') as file:
            patterns = [line.strip() for line in file if line.strip() and not line.startswith('#')]
    return pathspec.PathSpec.from_lines('gitwildmatch', patterns)

def get_language(file_extension):
    """Get the language identifier for syntax highlighting."""
    language_map = {
        # Programming Languages
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'jsx',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.rs': 'rust',
        '.scala': 'scala',
        '.m': 'objectivec',
        '.pl': 'perl',
        '.r': 'r',
        '.lua': 'lua',
        '.groovy': 'groovy',
        '.dart': 'dart',
        '.elm': 'elm',
        '.erl': 'erlang',
        '.ex': 'elixir',
        '.clj': 'clojure',
        '.hs': 'haskell',
        '.ml': 'ocaml',
        '.f': 'fortran',
        '.jl': 'julia',
        '.vb': 'vbnet',
        
        # Markup and Config Languages
        '.xml': 'xml',
        '.html': 'html',
        '.svg': 'svg',
        '.md': 'markdown',
        '.markdown': 'markdown',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        '.cfg': 'ini',
        
        # Shell Scripts
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'zsh',
        '.fish': 'fish',
        '.bat': 'batch',
        '.cmd': 'batch',
        '.ps1': 'powershell',
        
        # Databases
        '.sql': 'sql',
        '.psql': 'pgsql',
        '.plsql': 'plsql',
        
        # Web Technologies
        '.graphql': 'graphql',
        '.gql': 'graphql',
        '.vue': 'vue',
        '.handlebars': 'handlebars',
        '.hbs': 'handlebars',
        
        # Other
        '.diff': 'diff',
        '.patch': 'diff',
        '.tex': 'tex',
        '.matlab': 'matlab',
        '.asm': 'asm6502',
        '.cmake': 'cmake',
        '.dockerfile': 'dockerfile',
        '.gitignore': 'gitignore',
        '.makefile': 'makefile',
        '.nginx': 'nginx',
        '.proto': 'protobuf',
        '.regex': 'regex',
        
        # Default
        '.txt': 'text'
    }
    return language_map.get(file_extension.lower(), '')

def escape_markdown(text):
    """Escape markdown syntax in the given text."""
    text = text.replace('```', '\\`\\`\\`')
    chars_to_escape = r'\_*[]()#+-.!'
    for char in chars_to_escape:
        text = text.replace(char, '\\' + char)
    return text

def save_project_contents(root_directory: Path, output_filename: Path):
    logging.info(f"Saving project contents from: {root_directory}")

    root_patterns = load_gitignore_patterns(Path.cwd())
    target_patterns = load_gitignore_patterns(root_directory)
    
    all_patterns = root_patterns + target_patterns

    with output_filename.open('w') as f:
        f.write("# Project Documentation\n\n")
        f.write("This document contains a detailed look at the files within this project, excluding build artifacts, dependencies, and any files listed in .gitignore.\n\n")
        f.write("## Directory Tree\n\n")
        f.write("```\n")
        
        for dirpath, dirnames, filenames in os.walk(root_directory):
            rel_path = Path(dirpath).relative_to(root_directory)
            
            dirnames[:] = [d for d in dirnames if not all_patterns.match_file(rel_path / d)]
            filenames = [f for f in filenames if not all_patterns.match_file(rel_path / f)]

            level = len(rel_path.parts)
            indent = '    ' * level
            f.write(f"{indent}{Path(dirpath).name}/\n")
            subindent = '    ' * (level + 1)
            for filename in filenames:
                f.write(f"{subindent}{filename}\n")
        f.write("```\n\n")

        f.write("## File Contents\n\n")
        for dirpath, dirnames, filenames in os.walk(root_directory):
            rel_path = Path(dirpath).relative_to(root_directory)
            
            dirnames[:] = [d for d in dirnames if not all_patterns.match_file(rel_path / d)]
            filenames = [f for f in filenames if not all_patterns.match_file(rel_path / f)]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                relative_file_path = file_path.relative_to(root_directory)
                f.write(f"### {relative_file_path}\n\n")
                try:
                    content = file_path.read_text(encoding='utf-8')
                    language = get_language(file_path.suffix)
                    if language == 'markdown':
                        # For markdown files, escape the content
                        f.write(f"```{language}\n")
                        f.write(escape_markdown(content))
                    else:
                        f.write(f"```{language}\n")
                        f.write(content)
                    if not content.endswith('\n'):
                        f.write("\n")
                    f.write("```\n\n")
                except UnicodeDecodeError:
                    f.write("```\n")
                    f.write("Binary file content not displayed.\n")
                    f.write("```\n\n")

    logging.info(f"Project contents saved to: {output_filename}")

if __name__ == "__main__":
    # Example usage
    root_dir = Path("path/to/your/project")
    output_file = Path("project_contents.md")
    save_project_contents(root_dir, output_file)