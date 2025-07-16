#!/bin/bash

# RoboMaster TT 3D Simulator - Virtual Environment Setup Script (Linux/Mac)
# This script creates a Python virtual environment and installs all required dependencies

echo "🚁 RoboMaster TT 3D Simulator - Virtual Environment Setup"
echo "========================================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or higher and try again"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Error: Python $PYTHON_VERSION detected, but Python $REQUIRED_VERSION or higher is required"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Remove existing virtual environment if it exists
if [ -d "venv" ]; then
    echo "🗑️  Removing existing virtual environment..."
    rm -rf venv
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create virtual environment"
    echo "Make sure you have python3-venv installed:"
    echo "  Ubuntu/Debian: sudo apt install python3-venv"
    echo "  CentOS/RHEL: sudo yum install python3-venv"
    echo "  macOS: Should be included with Python 3"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing dependencies from requirements.txt..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install dependencies"
    echo "Please check requirements.txt and try again"
    exit 1
fi

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🎯 Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Start the simulation:"
echo "   python -m backend.server"
echo "   python -m mock_drone.drone_manager --count 3"
echo ""
echo "3. Open your browser to:"
echo "   http://localhost:8000"
echo ""
echo "💡 Remember to activate the virtual environment every time you work on this project!"
echo "   Run: source venv/bin/activate"