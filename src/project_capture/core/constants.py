"""
Constants used throughout the Project Snapshot application.
"""
from pathlib import Path
from typing import Dict, FrozenSet, List

# Application constants
CONFIG_FILE = "config.json"
MAX_CONFIGS_PER_PROJECT = 5
DEFAULT_LOG_FILE = "project_snapshot.log"

# File extensions to treat as binary without content checking
BINARY_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".ico", ".webp",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".pyc", ".pyd", ".pyo",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".wav", ".ogg",
})

# Language identifiers for syntax highlighting
LANGUAGE_MAP: Dict[str, str] = {
    # Python
    ".py": "python",
    ".pyi": "python",
    ".pyx": "python",
    ".pyw": "python",
    
    # Web
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    
    # Java and JVM languages
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".groovy": "groovy",
    ".scala": "scala",
    
    # C-family
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c++": "cpp",
    ".cs": "csharp",
    
    # Other languages
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".pl": "perl",
    ".swift": "swift",
    ".rs": "rust",
    ".r": "r",
    ".lua": "lua",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".ps1": "powershell",
    
    # Data & config formats
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".xml": "xml",
    ".sql": "sql",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    
    # Documentation
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".tex": "tex",
    ".txt": "text",
    
    # Other
    ".dockerfile": "dockerfile",
    "dockerfile": "dockerfile",
    ".gitignore": "gitignore",
    "makefile": "makefile",
    ".makefile": "makefile",
}

# Predefined ignore pattern templates
IGNORE_PATTERN_TEMPLATES: Dict[str, List[str]] = {
    "Python": [
        "__pycache__/",
        "*.py[cod]",
        "*$py.class",
        "*.so",
        ".Python",
        "env/",
        "build/",
        "develop-eggs/",
        "dist/",
        "downloads/",
        "eggs/",
        ".eggs/",
        "lib/",
        "lib64/",
        "parts/",
        "sdist/",
        "var/",
        "*.egg-info/",
        ".installed.cfg",
        "*.egg",
        ".env",
        ".venv",
        "venv/",
        "ENV/",
    ],
    "Node.js": [
        "node_modules/",
        "npm-debug.log",
        "yarn-debug.log*",
        "yarn-error.log*",
        ".pnp/",
        ".pnp.js",
        ".yarn/",
        "coverage/",
        ".next/",
        "out/",
        "build/",
        "dist/",
        ".env.local",
        ".env.development.local",
        ".env.test.local",
        ".env.production.local",
    ],
    "Java": [
        "*.class",
        "*.log",
        "*.jar",
        "*.war",
        "*.nar",
        "*.ear",
        "*.zip",
        "*.tar.gz",
        "*.rar",
        "target/",
        ".classpath",
        ".project",
        ".settings/",
        ".idea/",
        "*.iml",
        "*.iws",
        "*.ipr",
        "out/",
        ".gradle/",
        "build/",
    ],
    "Common": [
        ".DS_Store",
        ".AppleDouble",
        ".LSOverride",
        "Thumbs.db",
        "Thumbs.db:encryptable",
        "ehthumbs.db",
        "*.swp",
        "*.bak",
        "*.tmp",
        "*~",
        ".vs/",
        ".vscode/",
        ".history/",
    ],
}