# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

# Manually collect only essential Qt plugins (not the entire 334MB PySide6 package)
pyside6_datas = []
try:
    import PySide6
    pyside6_path = Path(PySide6.__path__[0])

    # Only include essential plugins for a basic GUI app
    essential_plugins = [
        'plugins/platforms',      # REQUIRED: qwindows.dll for Windows platform
        'plugins/styles',          # Windows visual styles
        'plugins/iconengines',     # Icon rendering
        'plugins/imageformats',    # Image support (PNG, JPG, etc.)
    ]

    for plugin_rel in essential_plugins:
        plugin_path = pyside6_path / plugin_rel
        if plugin_path.exists():
            pyside6_datas.append((str(plugin_path), str(Path('PySide6') / plugin_rel)))
except:
    pass

a = Analysis(
    [
        'cleanfilenames_gui.py',
        'cleanfilenames_core.py',
        'config_manager.py',
        'token_manager.py',
    ],
    pathex=[],
    binaries=[],
    datas=[
        ('presets', 'presets'),
    ] + pyside6_datas,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CleanFilenames',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for GUI app (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon='icon.ico' if you have an icon file
)

# Test generator (separate executable, console app)
test_gen = Analysis(
    ['generate_test_files.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

test_pyz = PYZ(test_gen.pure, test_gen.zipped_data, cipher=block_cipher)

test_exe = EXE(
    test_pyz,
    test_gen.scripts,
    [],
    exclude_binaries=True,
    name='GenerateTestFiles',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console app to show progress
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Collect both executables into the same distribution folder
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    test_exe,
    test_gen.binaries,
    test_gen.zipfiles,
    test_gen.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CleanFilenames',
)
