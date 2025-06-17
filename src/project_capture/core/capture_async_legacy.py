"""
Enhanced capture module with streaming, better error handling, and modern Python features.
"""
import asyncio
import logging
import mmap
import os
import time
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Iterator, Optional, Protocol, Set, List, Dict, Tuple
import tempfile
import shutil

import pathspec  # type: ignore
import aiofiles  # type: ignore
from aiofiles import os as aio_os  # type: ignore

from snapshot.constants import BINARY_EXTENSIONS, LANGUAGE_MAP
from snapshot.exceptions import ProjectSnapshotError

logger = logging.getLogger(__name__)


@dataclass
class FileProcessingResult:
    """Result of processing a single file."""
    path: Path
    processed: bool = True
    skipped: bool = False
    error: Optional[str] = None
    size: int = 0
    lines: int = 0


@dataclass
class ProjectSnapshot:
    """Aggregated results of a project snapshot."""
    processed_files: int = 0
    skipped_files: int = 0
    total_lines: int = 0
    total_size: int = 0
    errors: List[str] = field(default_factory=list)
    file_types: Dict[str, int] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    
    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    def add_result(self, result: FileProcessingResult) -> None:
        """Add a file processing result to the snapshot."""
        if result.processed:
            self.processed_files += 1
            self.total_lines += result.lines
            self.total_size += result.size
            
            # Track file types
            ext = result.path.suffix.lower()
            self.file_types[ext] = self.file_types.get(ext, 0) + 1
        elif result.skipped:
            self.skipped_files += 1
        
        if result.error:
            self.errors.append(f"{result.path}: {result.error}")


class PathLike(Protocol):
    """Protocol for path-like objects."""
    def __fspath__(self) -> str:
        ...


@contextmanager
def temporary_file(target_path: Path, mode: str = 'w', encoding: str = 'utf-8'):
    """
    Context manager for writing to a temporary file and atomically moving it.
    
    This ensures we don't lose data if the write fails partway through.
    """
    temp_fd, temp_path = tempfile.mkstemp(
        dir=target_path.parent,
        prefix=f".{target_path.name}.",
        suffix=".tmp"
    )
    temp_file_path = Path(temp_path)
    
    try:
        with os.fdopen(temp_fd, mode, encoding=encoding) as f:
            yield f
        
        # Atomically replace the target file
        temp_file_path.replace(target_path)
        
    except Exception:
        # Clean up the temporary file on error
        try:
            temp_file_path.unlink()
        except OSError:
            pass
        raise


class StreamingCaptureEngine:
    """
    Enhanced capture engine with streaming output and better resource management.
    """
    
    def __init__(
        self,
        root_directory: Path,
        output_path: Path,
        project_name: str,
        include_in_prompt: bool = False,
        check_binary_content: bool = True,
        max_file_size: int = 100_000_000,  # 100MB limit
        max_workers: int = 10,
    ):
        self.root_directory = root_directory
        self.output_path = output_path
        self.project_name = project_name
        self.include_in_prompt = include_in_prompt
        self.check_binary_content = check_binary_content
        self.max_file_size = max_file_size
        self.max_workers = max_workers
        
        self.snapshot = ProjectSnapshot()
        self._gitignore_cache: Dict[Path, pathspec.PathSpec] = {}
    
    def _load_gitignore_patterns(self, directory: Path) -> pathspec.PathSpec:
        """Load and cache gitignore patterns."""
        if directory in self._gitignore_cache:
            return self._gitignore_cache[directory]
        
        gitignore_path = directory / ".gitignore"
        patterns = []
        
        if gitignore_path.exists():
            try:
                patterns = gitignore_path.read_text().splitlines()
                patterns = [
                    line.strip() for line in patterns
                    if line.strip() and not line.startswith("#")
                ]
            except IOError as e:
                logger.warning(f"Error reading .gitignore: {e}")
        
        spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        self._gitignore_cache[directory] = spec
        return spec
    
    def _should_ignore(self, path: Path, patterns: pathspec.PathSpec) -> bool:
        """Check if a path should be ignored."""
        try:
            rel_path = path.relative_to(self.root_directory)
            return patterns.match_file(str(rel_path))
        except ValueError:
            return False
    
    def _is_binary_file(self, path: Path) -> bool:
        """Enhanced binary file detection."""
        # Check extension first (fast)
        if path.suffix.lower() in BINARY_EXTENSIONS:
            return True
        
        # Optional content check
        if self.check_binary_content:
            try:
                with open(path, 'rb') as f:
                    chunk = f.read(8192)  # Read first 8KB
                    # Check for null bytes (common in binary files)
                    if b'\0' in chunk:
                        return True
                    # Check if it's valid UTF-8
                    try:
                        chunk.decode('utf-8')
                    except UnicodeDecodeError:
                        return True
            except Exception:
                return True  # Assume binary if we can't read
        
        return False
    
    async def _read_file_async(self, path: Path) -> Tuple[str, int]:
        """
        Asynchronously read a file and return its content and line count.
        """
        if path.stat().st_size > self.max_file_size:
            raise ProjectSnapshotError(f"File too large: {path}")
        
        if self._is_binary_file(path):
            raise ProjectSnapshotError(f"Binary file: {path}")
        
        async with aiofiles.open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = await f.read()
            line_count = content.count('\n') + (1 if content and not content.endswith('\n') else 0)
            return content, line_count
    
    def _escape_markdown(self, text: str) -> str:
        """Escape markdown syntax in text."""
        # Escape triple backticks first
        text = text.replace("```", "\\`\\`\\`")
        # Then other markdown characters
        for char in r"\_*[]()#+-.!":
            text = text.replace(char, f"\\{char}")
        return text
    
    async def _process_file_async(self, file_path: Path, output_file) -> FileProcessingResult:
        """Process a single file asynchronously and write directly to output."""
        result = FileProcessingResult(path=file_path)
        
        try:
            # Get file stats
            stats = file_path.stat()
            result.size = stats.st_size
            
            # Write file header
            rel_path = file_path.relative_to(self.root_directory)
            await output_file.write(f"### {rel_path}\n\n")
            
            # Read and process content
            content, line_count = await self._read_file_async(file_path)
            result.lines = line_count
            
            # Get language for syntax highlighting
            language = LANGUAGE_MAP.get(file_path.suffix.lower(), "")
            
            # Write content with proper formatting
            await output_file.write(f"```{language}\n")
            
            if language == "markdown":
                content = self._escape_markdown(content)
            
            await output_file.write(content)
            
            if not content.endswith('\n'):
                await output_file.write('\n')
            
            await output_file.write("```\n\n")
            
        except ProjectSnapshotError as e:
            if "Binary file" in str(e):
                result.skipped = True
                result.processed = False
                await output_file.write("```\nBinary file, content not displayed.\n```\n\n")
            else:
                result.processed = False
                result.error = str(e)
                await output_file.write("```\nFile content not displayed due to an error.\n```\n\n")
        except Exception as e:
            result.processed = False
            result.error = str(e)
            logger.error(f"Unexpected error processing {file_path}: {e}")
            await output_file.write("```\nFile content not displayed due to an error.\n```\n\n")
        
        return result
    
    def _walk_directory(self, patterns: pathspec.PathSpec) -> Iterator[Path]:
        """
        Walk directory tree and yield files that should be processed.
        
        This is a generator to avoid loading all paths into memory at once.
        """
        for dirpath, dirnames, filenames in os.walk(self.root_directory):
            current_dir = Path(dirpath)
            
            # Filter directories to prevent descending into ignored ones
            dirnames[:] = [
                d for d in dirnames 
                if not self._should_ignore(current_dir / d, patterns)
            ]
            
            # Yield non-ignored files
            for filename in sorted(filenames):  # Sort for consistent output
                file_path = current_dir / filename
                if not self._should_ignore(file_path, patterns):
                    yield file_path
    
    async def _write_directory_tree_async(self, output_file, patterns: pathspec.PathSpec):
        """Write the directory tree structure to the output file."""
        await output_file.write("## Directory Tree\n\n```\n")
        
        seen_dirs = set()
        
        for file_path in self._walk_directory(patterns):
            # Add all parent directories
            rel_path = file_path.relative_to(self.root_directory)
            
            # Ensure all parent directories are shown
            for parent in rel_path.parents[:-1]:  # Exclude the root
                if parent not in seen_dirs:
                    seen_dirs.add(parent)
                    level = len(parent.parts)
                    indent = "    " * level
                    await output_file.write(f"{indent}{parent.name}/\n")
            
            # Add the file
            level = len(rel_path.parts) - 1
            indent = "    " * (level + 1)
            await output_file.write(f"{indent}{file_path.name}\n")
        
        await output_file.write("```\n\n")
    
    async def capture_async(
        self,
        additional_patterns: Optional[List[str]] = None,
        use_local_gitignore: bool = True,
        use_project_gitignore: bool = True,
    ) -> ProjectSnapshot:
        """
        Capture the project asynchronously with streaming output.
        """
        logger.info(f"Starting streaming capture of: {self.root_directory}")
        
        # Load all gitignore patterns
        all_patterns = []
        
        if use_local_gitignore:
            local_spec = self._load_gitignore_patterns(Path.cwd())
            all_patterns.append(local_spec)
        
        if use_project_gitignore:
            project_spec = self._load_gitignore_patterns(self.root_directory)
            all_patterns.append(project_spec)
        
        if additional_patterns:
            custom_spec = pathspec.PathSpec.from_lines("gitwildmatch", additional_patterns)
            all_patterns.append(custom_spec)
        
        # Combine all patterns
        combined_patterns = sum(all_patterns, pathspec.PathSpec.from_lines("gitwildmatch", []))
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first
        with temporary_file(self.output_path) as sync_file:
            # Convert to async file handle
            async with aiofiles.open(sync_file.name, 'w', encoding='utf-8') as output_file:
                # Write header
                await output_file.write(f"# Project Snapshot: {self.project_name}\n\n")
                
                if self.include_in_prompt:
                    await output_file.write("<project_contents>\n")
                
                # Write directory tree
                await self._write_directory_tree_async(output_file, combined_patterns)
                
                # Write file contents header
                await output_file.write("## File Contents\n\n")
                
                # Process files with limited concurrency
                semaphore = asyncio.Semaphore(self.max_workers)
                
                async def process_with_semaphore(file_path: Path):
                    async with semaphore:
                        result = await self._process_file_async(file_path, output_file)
                        self.snapshot.add_result(result)
                
                # Create tasks for all files
                tasks = []
                for file_path in self._walk_directory(combined_patterns):
                    task = asyncio.create_task(process_with_semaphore(file_path))
                    tasks.append(task)
                
                # Wait for all tasks to complete
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Close prompt wrapper if needed
                if self.include_in_prompt:
                    await output_file.write("</project_contents>\n")
        
        logger.info(
            f"Capture completed in {self.snapshot.elapsed_time:.2f}s. "
            f"Processed: {self.snapshot.processed_files}, "
            f"Skipped: {self.snapshot.skipped_files}, "
            f"Errors: {len(self.snapshot.errors)}"
        )
        
        return self.snapshot


# Compatibility function for existing code
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
) -> Dict[str, any]:
    """
    Compatibility wrapper for the new streaming capture engine.
    """
    engine = StreamingCaptureEngine(
        root_directory=root_directory,
        output_path=output_filename,
        project_name=project_name,
        include_in_prompt=include_in_prompt,
        check_binary_content=check_binary_content,
        max_workers=max_workers or 10,
    )
    
    # Run the async capture in a new event loop
    snapshot = asyncio.run(engine.capture_async(
        additional_patterns=additional_patterns,
        use_local_gitignore=use_local_gitignore,
        use_project_gitignore=use_project_gitignore,
    ))
    
    # Convert to legacy format
    return {
        "processed": snapshot.processed_files,
        "skipped": snapshot.skipped_files,
        "errors": snapshot.errors,
    }