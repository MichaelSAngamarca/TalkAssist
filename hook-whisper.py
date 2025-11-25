"""
PyInstaller runtime hook for Whisper
Helps Whisper find its data files in the frozen executable
"""
import os
import sys

# When running as a PyInstaller bundle, set the path for Whisper assets
if getattr(sys, 'frozen', False):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    base_path = sys._MEIPASS
    
    # Ensure Whisper can find its assets
    whisper_path = os.path.join(base_path, 'whisper')
    if os.path.exists(whisper_path):
        # Add to path so Whisper can find its assets
        if whisper_path not in sys.path:
            sys.path.insert(0, whisper_path)

