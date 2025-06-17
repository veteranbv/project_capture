"""
Improved capture module with streaming output, better error handling, and modern Python features.
No async dependencies required.
"""
import logging
import mmap
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple, TextIO
import tempfile
import queue
import threading

import pathspec  # type: ignore

from project_capture.core.constants import BINARY_EXTENSIONS, LANGUAGE_MAP
from project_capture.core.exceptions import ProjectSnapshotError

logger = logging.getLogger(__name__)


@dataclass
class FileResult:
    """Result of processing a single file."""
    path: Path
    content: str = ""
    processed: bool = True
    skipped: bool = False
    error: Optional[str] = None
    size: int = 0
    lines: int = 0


@dataclass
class CaptureStatistics:
    """Statistics for the capture operation."""
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


@contextmanager
def atomic_write(target_path: Path, mode: str = 'w', encoding: str = 'utf-8'):
    """
    Context manager for atomic file writes.
    Writes to a temporary file and moves it to the target on success.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temporary file in the same directory for atomic rename
    temp_fd, temp_path = tempfile.mkstemp(
        dir=target_path.parent,
        prefix=f".{target_path.name}.",
        suffix=".tmp"
    )
    
    try:
        with os.fdopen(temp_fd, mode, encoding=encoding) as f:
            yield f
        
        # Atomic rename on success
        Path(temp_path).replace(target_path)
        
    except Exception:
        # Clean up temporary file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


class PatternMatcher:
    """Efficient pattern matching with caching."""
    
    def __init__(self):
        self._cache: Dict[Path, pathspec.PathSpec] = {}
    
    def load_gitignore(self, directory: Path) -> pathspec.PathSpec:
        """Load and cache gitignore patterns from a directory."""
        if directory in self._cache:
            return self._cache[directory]
        
        gitignore_path = directory / ".gitignore"
        patterns = []
        
        if gitignore_path.exists():
            try:
                with gitignore_path.open('r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.append(line)
            except IOError as e:
                logger.warning(f"Error reading {gitignore_path}: {e}")
        
        spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        self._cache[directory] = spec
        return spec
    
    def combine_patterns(
        self,
        patterns: List[pathspec.PathSpec],
        additional: Optional[List[str]] = None
    ) -> pathspec.PathSpec:
        """Combine multiple pattern specs into one."""
        all_patterns = []
        
        for spec in patterns:
            all_patterns.extend(spec.patterns)
        
        if additional:
            custom_spec = pathspec.PathSpec.from_lines("gitwildmatch", additional)
            all_patterns.extend(custom_spec.patterns)
        
        return pathspec.PathSpec(all_patterns)


class FileProcessor:
    """Handles file reading and content processing."""
    
    def __init__(
        self,
        check_binary_content: bool = True,
        max_file_size: int = 100_000_000,  # 100MB
        mmap_threshold: int = 1_000_000,   # 1MB
    ):
        self.check_binary_content = check_binary_content
        self.max_file_size = max_file_size
        self.mmap_threshold = mmap_threshold
    
    def is_binary(self, path: Path) -> bool:
        """Check if a file is binary."""
        # Fast extension check
        if path.suffix.lower() in BINARY_EXTENSIONS:
            return True
        
        # Content check if enabled
        if self.check_binary_content:
            try:
                with open(path, 'rb') as f:
                    chunk = f.read(8192)
                    # Check for null bytes
                    if b'\0' in chunk:
                        return True
                    # Try UTF-8 decode
                    try:
                        chunk.decode('utf-8')
                    except UnicodeDecodeError:
                        return True
            except Exception:
                return True
        
        return False
    
    def read_file(self, path: Path) -> Tuple[str, int]:
        """Read file content and return (content, line_count)."""
        file_size = path.stat().st_size
        
        if file_size > self.max_file_size:
            raise ProjectSnapshotError(f"File too large ({file_size} bytes)")
        
        if self.is_binary(path):
            raise ProjectSnapshotError("Binary file detected")
        
        # Use mmap for large files
        if file_size > self.mmap_threshold:
            try:
                with open(path, 'rb') as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
                        content = m.read().decode('utf-8', errors='replace')
            except Exception as e:
                logger.debug(f"mmap failed for {path}: {e}, using regular read")
                content = path.read_text(encoding='utf-8', errors='replace')
        else:
            content = path.read_text(encoding='utf-8', errors='replace')
        
        # Count lines efficiently
        line_count = content.count('\n')
        if content and not content.endswith('\n'):
            line_count += 1
        
        return content, line_count
    
    def escape_markdown(self, text: str, language: str) -> str:
        """Escape markdown syntax if needed."""
        if language != "markdown":
            return text
        
        # Escape triple backticks
        text = text.replace("```", "\\`\\`\\`")
        
        # Escape other markdown syntax
        for char in r"\_*[]()#+-.!":
            text = text.replace(char, f"\\{char}")
        
        return text
    
    def format_file_content(self, path: Path, content: str) -> str:
        """Format file content for output."""
        language = LANGUAGE_MAP.get(path.suffix.lower(), "")
        
        # Escape if markdown
        if language == "markdown":
            content = self.escape_markdown(content, language)
        
        # Ensure proper line ending
        if not content.endswith('\n'):
            content += '\n'
        
        return f"```{language}\n{content}```\n\n"


class StreamingCapture:
    """
    Main capture engine with streaming output and efficient resource usage.
    """
    
    def __init__(
        self,
        root_directory: Path,
        output_path: Path,
        project_name: str,
        include_in_prompt: bool = False,
        check_binary_content: bool = True,
        max_workers: int = 10,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        self.root_directory = root_directory.resolve()
        self.output_path = output_path
        self.project_name = project_name
        self.include_in_prompt = include_in_prompt
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        
        self.stats = CaptureStatistics()
        self.pattern_matcher = PatternMatcher()
        self.file_processor = FileProcessor(check_binary_content=check_binary_content)
    
    def _should_ignore(self, path: Path, patterns: pathspec.PathSpec) -> bool:
        """Check if a path should be ignored."""
        try:
            rel_path = path.relative_to(self.root_directory)
            return patterns.match_file(str(rel_path))
        except ValueError:
            return False
    
    def _walk_sorted(self, patterns: pathspec.PathSpec) -> Iterator[Path]:
        """Walk directory tree yielding files in sorted order."""
        # Collect all files first for consistent ordering
        all_files = []
        
        for dirpath, dirnames, filenames in os.walk(self.root_directory):
            current_dir = Path(dirpath)
            
            # Filter directories
            dirnames[:] = sorted([
                d for d in dirnames 
                if not self._should_ignore(current_dir / d, patterns)
            ])
            
            # Collect non-ignored files
            for filename in filenames:
                file_path = current_dir / filename
                if not self._should_ignore(file_path, patterns):
                    all_files.append(file_path)
        
        # Sort by relative path for consistent output
        all_files.sort(key=lambda p: str(p.relative_to(self.root_directory)))
        return iter(all_files)
    
    def _write_directory_tree(self, output: TextIO, patterns: pathspec.PathSpec):
        """Write directory tree structure."""
        output.write("## Directory Tree\n\n```\n")
        output.write(f"{self.root_directory.name}/\n")
        
        seen_dirs = {Path(".")}
        
        for file_path in self._walk_sorted(patterns):
            rel_path = file_path.relative_to(self.root_directory)
            
            # Ensure parent directories are shown
            for i, parent in enumerate(rel_path.parents[:-1]):
                if parent not in seen_dirs:
                    seen_dirs.add(parent)
                    level = len(rel_path.parents) - i - 2
                    indent = "    " * (level + 1)
                    output.write(f"{indent}{parent.name}/\n")
            
            # Write the file
            level = len(rel_path.parents) - 1
            indent = "    " * (level + 1)
            output.write(f"{indent}{file_path.name}\n")
        
        output.write("```\n\n")
    
    def _process_file(self, file_path: Path) -> FileResult:
        """Process a single file."""
        result = FileResult(path=file_path)
        rel_path = file_path.relative_to(self.root_directory)
        
        try:
            # Get file size
            result.size = file_path.stat().st_size
            
            # Read content
            content, line_count = self.file_processor.read_file(file_path)
            result.lines = line_count
            
            # Format output
            output_parts = [
                f"### {rel_path}\n\n",
                self.file_processor.format_file_content(file_path, content)
            ]
            
            result.content = "".join(output_parts)
            
            # Track file type
            ext = file_path.suffix.lower()
            self.stats.file_types[ext] = self.stats.file_types.get(ext, 0) + 1
            
        except ProjectSnapshotError as e:
            if "Binary file" in str(e):
                result.skipped = True
                result.processed = False
                result.content = f"### {rel_path}\n\n```\nBinary file, content not displayed.\n```\n\n"
                logger.info(f"Skipped binary file: {rel_path}")
            else:
                result.processed = False
                result.error = str(e)
                result.content = f"### {rel_path}\n\n```\nError: {e}\n```\n\n"
                logger.warning(f"Error processing {rel_path}: {e}")
                
        except Exception as e:
            result.processed = False
            result.error = str(e)
            result.content = f"### {rel_path}\n\n```\nUnexpected error: {e}\n```\n\n"
            logger.error(f"Unexpected error processing {rel_path}: {e}")
        
        return result
    
    def _writer_thread(self, output: TextIO, result_queue: queue.Queue, done_event: threading.Event):
        """Thread that writes results to output file as they become available."""
        while not done_event.is_set() or not result_queue.empty():
            try:
                result = result_queue.get(timeout=0.1)
                
                # Write content
                output.write(result.content)
                output.flush()  # Ensure data is written
                
                # Update statistics
                if result.processed:
                    self.stats.processed_files += 1
                    self.stats.total_lines += result.lines
                    self.stats.total_size += result.size
                elif result.skipped:
                    self.stats.skipped_files += 1
                
                if result.error:
                    self.stats.errors.append(f"{result.path}: {result.error}")
                
            except queue.Empty:
                continue
    
    def capture(
        self,
        additional_patterns: Optional[List[str]] = None,
        use_local_gitignore: bool = True,
        use_project_gitignore: bool = True,
    ) -> Dict[str, any]:
        """
        Capture project with streaming output.
        """
        logger.info(f"Starting capture of: {self.root_directory}")
        
        # Load patterns
        pattern_specs = []
        
        if use_local_gitignore:
            pattern_specs.append(self.pattern_matcher.load_gitignore(Path.cwd()))
        
        if use_project_gitignore:
            pattern_specs.append(self.pattern_matcher.load_gitignore(self.root_directory))
        
        combined_patterns = self.pattern_matcher.combine_patterns(
            pattern_specs, additional_patterns
        )
        
        # Capture with atomic write
        with atomic_write(self.output_path) as output:
            # Write header
            output.write(f"# Project Snapshot: {self.project_name}\n\n")
            
            if self.include_in_prompt:
                output.write("<project_contents>\n")
            
            # Write directory tree
            self._write_directory_tree(output, combined_patterns)
            
            # Write file contents header
            output.write("## File Contents\n\n")
            
            # Set up streaming pipeline
            result_queue = queue.Queue(maxsize=self.max_workers * 2)
            done_event = threading.Event()
            
            # Start writer thread
            writer = threading.Thread(
                target=self._writer_thread,
                args=(output, result_queue, done_event)
            )
            writer.start()
            
            # Process files in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all files
                file_list = list(self._walk_sorted(combined_patterns))
                total_files = len(file_list)
                
                futures = {
                    executor.submit(self._process_file, file_path): file_path
                    for file_path in file_list
                }
                
                # Process results as they complete
                processed_count = 0
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        result_queue.put(result)
                        processed_count += 1
                        
                        # Call progress callback if provided
                        if self.progress_callback:
                            self.progress_callback(processed_count, total_files)
                            
                    except Exception as e:
                        file_path = futures[future]
                        logger.error(f"Failed to process {file_path}: {e}")
                        # Create error result
                        error_result = FileResult(
                            path=file_path,
                            processed=False,
                            error=str(e),
                            content=f"### {file_path.relative_to(self.root_directory)}\n\n```\nProcessing failed: {e}\n```\n\n"
                        )
                        result_queue.put(error_result)
                        processed_count += 1
                        
                        # Call progress callback even for errors
                        if self.progress_callback:
                            self.progress_callback(processed_count, total_files)
            
            # Signal writer thread to finish
            done_event.set()
            writer.join()
            
            # Write footer
            if self.include_in_prompt:
                output.write("</project_contents>\n")
        
        logger.info(
            f"Capture completed in {self.stats.elapsed_time:.2f}s. "
            f"Processed: {self.stats.processed_files}, "
            f"Skipped: {self.stats.skipped_files}, "
            f"Errors: {len(self.stats.errors)}"
        )
        
        return {
            "processed": self.stats.processed_files,
            "skipped": self.stats.skipped_files,
            "errors": self.stats.errors,
            "total_lines": self.stats.total_lines,
            "total_size": self.stats.total_size,
            "file_types": self.stats.file_types,
            "elapsed_time": self.stats.elapsed_time,
            "output_path": str(self.output_path),
        }


# Drop-in replacement for the original function
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
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, any]:
    """
    Enhanced version of save_project_contents with streaming and better error handling.
    
    Maintains backward compatibility with the original function signature.
    """
    capture = StreamingCapture(
        root_directory=root_directory,
        output_path=output_filename,
        project_name=project_name,
        include_in_prompt=include_in_prompt,
        check_binary_content=check_binary_content,
        max_workers=max_workers or (10 if use_parallel_processing else 1),
        progress_callback=progress_callback,
    )
    
    return capture.capture(
        additional_patterns=additional_patterns,
        use_local_gitignore=use_local_gitignore,
        use_project_gitignore=use_project_gitignore,
    )


# Alias for backward compatibility
capture_project_contents = save_project_contents