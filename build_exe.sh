#!/bin/bash
# Build script for creating TalkAssist standalone executable
# This excludes the frontend directory

echo "========================================"
echo "Building TalkAssist Standalone Executable"
echo "========================================"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: Virtual environment not detected."
    echo "It's recommended to build from within your virtual environment."
    echo ""
    read -p "Press enter to continue..."
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist __pycache__
echo ""

# Build the executable
echo "Building executable..."
pyinstaller talkassist.spec --clean --noconfirm

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "Build successful!"
    echo "========================================"
    echo ""
    echo "The executable is located in: dist/TalkAssist"
    echo ""
    echo "Note: The frontend directory has been excluded from the build."
    echo "To use the web interface, run Flask separately with: --start-flask"
    echo ""
else
    echo ""
    echo "========================================"
    echo "Build failed!"
    echo "========================================"
    echo ""
    echo "Please check the error messages above."
    echo ""
fi

