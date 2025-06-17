#!/usr/bin/env python3
"""Quick start example for Project Capture."""

from pathlib import Path
from project_capture import capture_project_contents

# Example 1: Basic capture with default settings
print("Example 1: Basic capture")
result = capture_project_contents(
    root_directory=".",
    output_path="output/my_project_snapshot.md",
    project_name="My Project",
)
print(f"Captured {result['processed']} files, skipped {result['skipped']}")
print(f"Output saved to: {result['output_path']}")
print()

# Example 2: Capture with custom ignore patterns
print("Example 2: Custom ignore patterns")
result = capture_project_contents(
    root_directory=".",
    output_path="output/filtered_snapshot.md",
    project_name="Filtered Project",
    additional_patterns=["*.test.py", "docs/*", "examples/*"],
    use_local_gitignore=True,
    use_project_gitignore=True,
)
print(f"Captured {result['processed']} files with custom filters")
print()

# Example 3: Capture with AI prompt wrapper
print("Example 3: AI-ready format")
result = capture_project_contents(
    root_directory=".",
    output_path="output/ai_ready_snapshot.md",
    project_name="AI Ready Project",
    include_in_prompt=True,
)
print(f"Created AI-ready snapshot with {result['processed']} files")
print()

# Example 4: Performance tuning
print("Example 4: Performance tuning")
result = capture_project_contents(
    root_directory=".",
    output_path="output/fast_snapshot.md",
    project_name="Fast Project",
    use_parallel_processing=True,
    max_workers=20,  # Increase worker threads
    check_binary_content=False,  # Skip binary content checks for speed
)
print(f"Fast capture completed in {result.get('elapsed_time', 'N/A')} seconds")

print("\nAll examples completed!")