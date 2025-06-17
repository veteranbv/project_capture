#!/usr/bin/env python3
"""
Performance and behavior comparison test for capture implementations.
"""
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import json

# Import all three implementations
from snapshot.capture import save_project_contents as original_capture
from snapshot.capture_improved import save_project_contents as improved_capture
from snapshot.capture_v2 import save_project_contents as async_capture


def create_test_project(base_path: Path, num_files: int = 100, avg_file_size: int = 1000):
    """Create a test project with various file types."""
    base_path.mkdir(parents=True, exist_ok=True)
    
    # Create some directory structure
    (base_path / "src").mkdir(exist_ok=True)
    (base_path / "src" / "utils").mkdir(exist_ok=True)
    (base_path / "tests").mkdir(exist_ok=True)
    (base_path / "docs").mkdir(exist_ok=True)
    
    # Create .gitignore
    gitignore_content = """
__pycache__/
*.pyc
.env
node_modules/
*.log
"""
    (base_path / ".gitignore").write_text(gitignore_content)
    
    # Create various file types
    file_types = [
        (".py", "python", "def hello():\n    return 'Hello, World!'\n"),
        (".js", "javascript", "function hello() { return 'Hello, World!'; }\n"),
        (".md", "markdown", "# Hello\n\nThis is a **test** file.\n"),
        (".txt", "text", "This is a plain text file.\n"),
        (".json", "json", '{"hello": "world", "test": true}\n'),
    ]
    
    created_files = 0
    for i in range(num_files):
        ext, lang, template = file_types[i % len(file_types)]
        
        # Determine directory
        if i % 4 == 0:
            dir_path = base_path / "src"
        elif i % 4 == 1:
            dir_path = base_path / "src" / "utils"
        elif i % 4 == 2:
            dir_path = base_path / "tests"
        else:
            dir_path = base_path / "docs"
        
        # Create file with repeated content to reach target size
        file_path = dir_path / f"file_{i}{ext}"
        content = template * (avg_file_size // len(template))
        file_path.write_text(content)
        created_files += 1
    
    # Add some binary files to test skipping
    (base_path / "image.png").write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
    (base_path / "data.bin").write_bytes(b'\x00\x01\x02\x03' * 25)
    
    return created_files + 2  # Include binary files


def benchmark_capture(
    capture_func,
    name: str,
    root_dir: Path,
    output_dir: Path
) -> Dict[str, Any]:
    """Benchmark a capture function."""
    output_file = output_dir / f"{name}_output.md"
    
    print(f"\nBenchmarking {name}...")
    start_time = time.time()
    
    try:
        result = capture_func(
            root_directory=root_dir,
            output_filename=output_file,
            project_name=f"test_project_{name}",
            include_in_prompt=True,
            check_binary_content=True,
            use_parallel_processing=True,
            max_workers=5,
        )
        
        elapsed = time.time() - start_time
        
        # Check output file
        if output_file.exists():
            file_size = output_file.stat().st_size
            # Quick check for content integrity
            content = output_file.read_text()
            has_tree = "## Directory Tree" in content
            has_contents = "## File Contents" in content
            file_count = content.count("### ")
        else:
            file_size = 0
            has_tree = False
            has_contents = False
            file_count = 0
        
        return {
            "name": name,
            "success": True,
            "elapsed_time": elapsed,
            "processed_files": result.get("processed", 0),
            "skipped_files": result.get("skipped", 0),
            "errors": len(result.get("errors", [])),
            "output_size": file_size,
            "has_tree": has_tree,
            "has_contents": has_contents,
            "file_sections": file_count,
        }
        
    except Exception as e:
        print(f"  Error: {e}")
        return {
            "name": name,
            "success": False,
            "error": str(e),
            "elapsed_time": time.time() - start_time,
        }


def main():
    """Run performance comparison tests."""
    print("Project Capture Performance Comparison")
    print("=" * 50)
    
    # Create temporary test environment
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_project = temp_path / "test_project"
        output_dir = temp_path / "output"
        output_dir.mkdir()
        
        # Create test project
        print(f"\nCreating test project with files...")
        num_files = create_test_project(test_project, num_files=50, avg_file_size=500)
        print(f"Created {num_files} files")
        
        # Test each implementation
        implementations = [
            (original_capture, "original"),
            (improved_capture, "improved"),
        ]
        
        # Only test async version if aiofiles is available
        try:
            import aiofiles
            implementations.append((async_capture, "async"))
        except ImportError:
            print("\nNote: Skipping async implementation (aiofiles not installed)")
        
        results = []
        for capture_func, name in implementations:
            result = benchmark_capture(capture_func, name, test_project, output_dir)
            results.append(result)
        
        # Print comparison results
        print("\n" + "=" * 50)
        print("RESULTS SUMMARY")
        print("=" * 50)
        
        for result in results:
            print(f"\n{result['name'].upper()} Implementation:")
            if result['success']:
                print(f"  Time: {result['elapsed_time']:.3f}s")
                print(f"  Processed: {result['processed_files']} files")
                print(f"  Skipped: {result['skipped_files']} files")
                print(f"  Errors: {result['errors']}")
                print(f"  Output size: {result['output_size']:,} bytes")
                print(f"  Integrity: Tree={result['has_tree']}, Contents={result['has_contents']}")
                print(f"  File sections: {result['file_sections']}")
            else:
                print(f"  FAILED: {result.get('error', 'Unknown error')}")
        
        # Performance comparison
        successful_results = [r for r in results if r['success']]
        if len(successful_results) > 1:
            print("\n" + "=" * 50)
            print("PERFORMANCE COMPARISON")
            print("=" * 50)
            
            baseline = next(r for r in successful_results if r['name'] == 'original')
            baseline_time = baseline['elapsed_time']
            
            for result in successful_results:
                if result['name'] != 'original':
                    speedup = baseline_time / result['elapsed_time']
                    percent_faster = (speedup - 1) * 100
                    print(f"\n{result['name']} vs original:")
                    print(f"  {speedup:.2f}x faster ({percent_faster:+.1f}%)")
        
        # Save detailed results
        results_file = output_dir / "benchmark_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    main()