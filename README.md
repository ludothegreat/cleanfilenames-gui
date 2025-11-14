# Clean Filenames (Python Edition)

Python reimplementation of the `cleanfilenames.ps1` utility with both CLI and GUI front-ends. It removes region tags like `(USA)`, `(JP)`, `(En,Fr,De,Es)` from file/folder names and tidies whitespace.

## Layout

```
cleanfilenames_py/
├── cleanfilenames_core.py   # Core rename logic + CLI
├── cleanfilenames_gui.py    # PySide6 GUI
├── __init__.py
└── README.md
```

## Requirements

- Python 3.9+ (system Python is 3.13.7)
- PySide6 for the GUI

Install dependencies (recommend a venv):

```bash
cd /hoard/scripts/cleanfilenames_py
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install PySide6
```

## CLI Usage

Preview changes:

```bash
python3 cleanfilenames_core.py "/path/to/roms"
```

Apply renames:

```bash
python3 cleanfilenames_core.py "/path/to/roms" --apply
```

The CLI reports collisions (target already exists) and leaves those files untouched.

## GUI Usage

```bash
python3 cleanfilenames_gui.py
```

Features:

- Choose a folder with the Browse button.
- Click **Scan** to preview all pending renames.
- Click **Apply Changes** to run them (confirmation required). Collisions/errors are highlighted in the table and summarized in a dialog.

## Building a Windows `.exe`

1. Install PyInstaller in your (virtual) environment: `pip install pyinstaller`.
2. Run: `pyinstaller --onefile cleanfilenames_gui.py`
3. The resulting executable lives in `dist/cleanfilenames_gui.exe`. Distribute the `dist` folder (Qt plugins live alongside the exe). Repeat on each OS to get native bundles.

## Notes

- The regex is identical to the PowerShell version for parity.
- Directories are renamed deepest-first to avoid “path not found” issues.
- Collisions are reported but not auto-resolved (per current PowerShell behavior).
