# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for TalkAssist
Builds a standalone executable excluding the frontend directory
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect Whisper data files
whisper_datas = []
try:
    import whisper
    # Get the whisper package location
    whisper_file = whisper.__file__
    whisper_dir = os.path.dirname(whisper_file)
    
    # Find and include the assets directory
    assets_dir = os.path.join(whisper_dir, 'assets')
    if os.path.exists(assets_dir):
        # Include all files in the assets directory
        for root, dirs, files in os.walk(assets_dir):
            for file in files:
                src_path = os.path.join(root, file)
                # Calculate relative path from whisper_dir (e.g., 'assets/mel_filters.npz')
                rel_path = os.path.relpath(src_path, whisper_dir)
                # Destination should preserve the whisper/assets structure
                # So 'assets/mel_filters.npz' becomes 'whisper/assets/mel_filters.npz'
                dest_dir = os.path.join('whisper', os.path.dirname(rel_path))
                whisper_datas.append((src_path, dest_dir))
        print(f"Found {len(whisper_datas)} Whisper asset files to include")
        if whisper_datas:
            print(f"Example: {whisper_datas[0]}")
    else:
        # Fallback: use collect_data_files
        whisper_datas = collect_data_files('whisper')
        print(f"Using collect_data_files, found {len(whisper_datas)} Whisper data files")
except ImportError as e:
    print(f"Warning: Could not import whisper to collect data files: {e}")
except Exception as e:
    print(f"Warning: Error collecting Whisper data files: {e}")
    # Try fallback
    try:
        whisper_datas = collect_data_files('whisper')
    except:
        whisper_datas = []

# Collect reminders.json if it exists
datas = []
if os.path.exists('reminders.json'):
    datas.append(('reminders.json', '.'))

# Collect all Python files
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas + whisper_datas,  # Include Whisper data files
    # Note: tkinter is included by default in Python, no need to add it
    hiddenimports=[
        'whisper',
        'whisper.model',
        'whisper.audio',
        'whisper.decoding',
        'whisper.tokenizer',
        'whisper.utils',
        'pyaudio',
        'pyttsx3',
        'elevenlabs',
        'elevenlabs.conversational_ai',
        'elevenlabs.conversational_ai.conversation',
        'elevenlabs.conversational_ai.default_audio_interface',
        'langchain_community',
        'langchain_community.tools',
        'apscheduler',
        'apscheduler.schedulers',
        'apscheduler.schedulers.background',
        'pynput',
        'keyboard',
        'word2number',
        'werkzeug',
        'flask',
        'numpy',
        'torch',
        'torchaudio',
        'transformers',
        'openai',
        'requests',
        'dotenv',
        'PIL',
        'PIL.Image',
        'tkinter',
        'tkinter.ttk',
        'gui',  # Include our GUI module
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['hook-whisper.py'] if os.path.exists('hook-whisper.py') else [],
    excludes=[
        'frontend',  # Explicitly exclude frontend
        'templates',  # Exclude templates
        'static',  # Exclude static files
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Collect data files for whisper models (if needed)
# Note: Whisper models are typically downloaded on first use
# You may need to include them if you want offline model loading

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TalkAssist',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False if you want a windowless app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: 'icon.ico'
)

