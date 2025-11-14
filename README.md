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

## Configuration

Settings are stored in `~/.config/cleanfilenames/config.json` (auto-created the first time you run the tool). Example:

```json
{
  "regex": "\\s*\\((?:USA|EU|...)\\)\\s*",
  "rename_directories": true,
  "rename_root": true,
  "stop_on_error": false
}
```

- `regex`: pattern used to strip region tags.
- `tokens`: optional list of region keywords (used to rebuild the regex).
- `rename_directories`: toggle directory renaming.
- `rename_root`: allow renaming the selected root folder.
- `stop_on_error`: halt processing on the first failure.

The GUI exposes these settings via the **Settings** dialog; the CLI can load alternate configs with `--config path/to/config.json`.

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
- Browse for a folder, scan, and apply changes.
- Dry run mode to simulate renames (status column shows "done (dry run)").
- Settings dialog with:
  - Preset selector (full list vs. minimal list vs. custom).
  - Token editor (one region token per line, rebuilt into the regex).
  - Load/save buttons for importing/exporting regex patterns.
  - Toggles for directory/root renames and stop-on-error behavior.

## Building a Windows `.exe`

1. Install PyInstaller in your (virtual) environment: `pip install pyinstaller`.
2. Run: `pyinstaller --onefile cleanfilenames_gui.py`
3. The resulting executable lives in `dist/cleanfilenames_gui.exe`. Distribute the `dist` folder (Qt plugins live alongside the exe). Repeat on each OS to get native bundles.

## Notes

- The regex is identical to the PowerShell version for parity.
- Directories are renamed deepest-first to avoid “path not found” issues.
- Collisions are reported but not auto-resolved (per current PowerShell behavior).
