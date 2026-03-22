#!/bin/bash
# PriAge GUI Application Launcher (Linux/Mac)
# Quick start script for Unix-based systems

echo "========================================"
echo "PriAge - Age Verification System"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "Starting PriAge GUI..."
echo ""
python3 priAge_gui.py
