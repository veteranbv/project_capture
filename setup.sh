#!/bin/bash
# Setup script for Project Capture development environment

set -e  # Exit on error

echo "🚀 Setting up Project Capture development environment"
echo "===================================================="

# Check Python version
echo -e "\n📌 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python $PYTHON_VERSION"

# Check if Python version is 3.10 or higher
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "❌ Python 3.10 or later is required. Found Python $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment
echo -e "\n🔧 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Removing old one..."
    rm -rf venv
fi
python3 -m venv venv

# Activate virtual environment
echo -e "\n🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip, setuptools, and wheel
echo -e "\n⬆️  Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# Install package in development mode with all extras
echo -e "\n📦 Installing project with development dependencies..."
pip install -e ".[dev,docs]"

# Install pre-commit hooks
echo -e "\n🪝 Installing pre-commit hooks..."
pre-commit install

# Create necessary directories
echo -e "\n📁 Creating project directories..."
mkdir -p output logs

# Success message
echo -e "\n✅ Setup complete!"
echo -e "\nTo activate the virtual environment, run:"
echo "    source venv/bin/activate"
echo -e "\nUseful commands:"
echo "    make test          # Run tests"
echo "    make lint          # Run linting"
echo "    make format        # Format code"
echo "    make check-all     # Run all checks"
echo "    ./project_capture  # Run the CLI"
echo -e "\nHappy coding! 🎉"