#!/usr/bin/env python3
"""Example demonstrating progress tracking during capture."""

import time
from pathlib import Path
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from project_capture import capture_project_contents


def main():
    """Run capture with progress tracking."""
    
    # Create a Rich progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total} files"),
    ) as progress:
        
        # Create a task for tracking
        task = progress.add_task("Capturing project...", total=100)
        
        # Define progress callback
        def update_progress(completed: int, total: int):
            """Update the progress bar."""
            progress.update(task, completed=completed, total=total)
        
        # Capture with progress tracking
        result = capture_project_contents(
            root_directory=".",
            output_path="output/progress_demo.md",
            project_name="Progress Demo",
            progress_callback=update_progress,
            use_parallel_processing=True,
            max_workers=5,  # Lower worker count to see progress better
        )
        
        # Complete the progress
        progress.update(task, completed=result["processed"], total=result["processed"])
    
    # Print results
    print(f"\nCapture completed!")
    print(f"Processed: {result['processed']} files")
    print(f"Total lines: {result['total_lines']:,}")
    print(f"Total size: {result['total_size']:,} bytes")
    print(f"Time elapsed: {result['elapsed_time']:.2f} seconds")
    print(f"Output saved to: {result['output_path']}")
    
    # Show file type breakdown
    if result['file_types']:
        print("\nFile types processed:")
        for ext, count in sorted(result['file_types'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {ext or '(no extension)'}: {count} files")


if __name__ == "__main__":
    main()