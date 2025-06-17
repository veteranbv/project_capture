#!/bin/bash
# Quick test script to verify the project is working

set -e  # Exit on error

echo "🧪 Running Project Capture Tests"
echo "================================"

# Check Python version
echo -e "\n📌 Python version:"
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "\n🔧 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "\n🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo -e "\n⬆️  Upgrading pip..."
pip install --upgrade pip >/dev/null 2>&1

# Install in development mode
echo -e "\n📦 Installing package in development mode..."
pip install -e . >/dev/null 2>&1

# Run a simple capture test
echo -e "\n🔍 Testing basic capture functionality..."
python -c "
import sys
sys.path.insert(0, 'src')
from project_capture import capture_project_contents

result = capture_project_contents(
    root_directory='examples',
    output_path='output/test_capture.md',
    project_name='Test Capture',
    additional_patterns=['*.pyc', '__pycache__'],
)

print(f'✅ Capture successful!')
print(f'   Processed: {result["processed"]} files')
print(f'   Skipped: {result["skipped"]} files')
print(f'   Time: {result["elapsed_time"]:.2f}s')
"

# Test with progress callback
echo -e "\n🚀 Testing progress callback..."
python examples/progress_demo.py

# Check if CLI works
echo -e "\n💻 Testing CLI entry point..."
./project_capture --help >/dev/null 2>&1 && echo "✅ CLI working!" || echo "❌ CLI failed!"

echo -e "\n✨ All tests completed!"