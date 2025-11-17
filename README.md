# Clean Filenames (Python Edition)

Python reimplementation of the `cleanfilenames.ps1` utility with both CLI and GUI front-ends. It removes region tags like `(USA)`, `(JP)`, `(En,Fr,De,Es)` from file/folder names and tidies whitespace.

## Layout

```
cleanfilenames_py/
├── cleanfilenames_core.py              # Core rename logic + CLI
├── cleanfilenames_gui.py               # PySide6 GUI
├── config_manager.py                   # Configuration management
├── generate_cleanfilenames_testdata.py # Test data generator
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
  "tokens": [
    "USA",
    "Europe",
    "JP",
    "PAL"
  ],
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

### Working with Tokens & Patterns

- **Tokens** represent the literal text that appears in parentheses in your filenames (e.g., `USA`, `Europe`, `En,Fr,De,Es,It`). Each token can include commas or other characters; the tool treats it as raw text unless you add regex syntax yourself.
- The **pattern** is the full regular expression derived from the token list. It adds the wrapping `\s*\((?: ... )\)\s*` around the tokens, which matches any of the listed tokens with surrounding parentheses/spaces.
- To create your own pattern, either:
  1. Edit the token list (one token per line) and let the tool rebuild the regex automatically, or
  2. Paste a fully custom regex into the pattern box (advanced users). When the regex no longer matches a preset, the UI switches to “Custom.”
- Use the **Load Pattern** button to import a saved regex text file, and **Save Pattern** to export the current regex for reuse or version control.

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
  - Token editor (one region token per line, rebuilt into the regex; supports commas and regex syntax if you need ranges).
  - Load/save buttons for importing/exporting regex patterns.
  - Toggles for directory/root renames and stop-on-error behavior.
- Token Manager dialog that tracks duplicate tokens, shows usage counts from the latest scan, and lets you append auto-detected suggestions with a couple of clicks.
- Built-in help dialog explaining tokens, patterns, and customization paths.
- Table results support `Ctrl+C`/`Cmd+C` to copy selected rows as tab-separated text.
- Right-click the results to export CSV; the table includes a "Directory" column so you can see the path relative to the scan root (e.g., `Extras/Music/Track 01`). This mirrors the on-disk rename order.
- For large scans, the table shows the first 5,000 rows; use the CSV export to review the full list.

## Testing

A test data generator is included to create realistic ROM-like test datasets:

```bash
# Small dataset (~500 files)
python3 generate_cleanfilenames_testdata.py --small

# Medium dataset (~1500 files)
python3 generate_cleanfilenames_testdata.py --medium

# Large dataset (~10k files)
python3 generate_cleanfilenames_testdata.py --large
```

The generator creates:
- Realistic ROM filenames with various region tags
- Nested directory structures (Console/Category)
- Directory names with region tags
- Exact collision scenarios (files that would conflict after cleaning)
- Case-insensitive collision scenarios (for Windows testing)
- Test data location: `/tmp/clean_test_suite`

After generating, test with:
```bash
python3 cleanfilenames_core.py /tmp/clean_test_suite          # Preview
python3 cleanfilenames_core.py /tmp/clean_test_suite --apply  # Apply
```

## Building a Windows `.exe`

1. Install PyInstaller in your (virtual) environment: `pip install pyinstaller`.
2. Run: `pyinstaller --onefile cleanfilenames_gui.py`
3. The resulting executable lives in `dist/cleanfilenames_gui.exe`. Distribute the `dist` folder (Qt plugins live alongside the exe). Repeat on each OS to get native bundles.

## Notes

- The regex is identical to the PowerShell version for parity.
- Directories are renamed deepest-first to avoid "path not found" issues.
- Collisions are reported but not auto-resolved (per current PowerShell behavior).

## TODO

- [x] **Auto Token Discovery**: When scanning files, detect potential region tokens that aren't in the current config and offer to add them automatically. This would help users discover new patterns without manually editing the token list.

- [ ] **Manual Conflict Resolution**: After scanning, if there are filename collisions or conflicts, allow manual renaming directly in the GUI. This would eliminate the need to use a file manager or CLI to resolve conflicts - everything can be managed in one place.
- [ ] **Conflict Panel**: Investigate moving the conflict resolver into a dedicated panel so multi-item conflicts can be resolved without giant modal dialogs.
- [ ] **Result Sorting & Filtering**: Allow sorting the scan results by type/status/message and filter the table down to only passed/failed entries for easier triage.

## Current Status (2025‑11‑13)

- Platform parity work is complete: the PowerShell snapshot logic now lives in `cleanfilenames_core.py` with both CLI and PySide6 GUI entrypoints, tokenized regex presets, JSON config auto-loading, context menu + CSV export, regex help dialog, and 5K-row UI truncation for large jobs.
- Normalization now drops literal `\` characters and rebuilds the region regex from the saved token list, so dry runs and real runs stay in sync even after editing presets.
- Latest fix (this session) adjusts file renames to reference the post-directory-rename parent path, eliminating the `[Errno 2] No such file or directory` bursts that showed up when applying against `/tmp/clean_test_suite`.
- Smoke test: `python3 cleanfilenames_core.py /tmp/clean_test_suite_sample --apply` succeeded with 6/6 renames; the real 50-folder dataset still needs to be regenerated (previous run already normalized everything under `/tmp/clean_test_suite`, so there is nothing left to rename right now).
- Outstanding follow-ups for tomorrow: (1) recreate `/tmp/clean_test_suite` (and the larger 4k-folder stress data, if needed), (2) re-run a GUI dry-run + apply to confirm the fix at scale, (3) delete temporary exports (`cleanfilenames.csv`, `cleanfilenames.txt`) if they are no longer needed once verification is done.
