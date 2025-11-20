# Clean Filenames (Python Edition)

Python reimplementation of the `cleanfilenames.ps1` utility with both CLI and GUI front-ends. It removes region tags like `(USA)`, `(JP)`, `(En,Fr,De,Es)` from file/folder names and tidies whitespace.

## Layout

```
cleanfilenames-gui/
├── cleanfilenames_core.py              # Core rename logic + CLI
├── cleanfilenames_gui.py               # PySide6 GUI
├── config_manager.py                   # Configuration management + presets
├── token_manager.py                    # Token validation + suggestions
├── generate_cleanfilenames_testdata.py # Test data generator
├── presets/                            # Default + minimal token lists
└── README.md
```

## Requirements

- Python 3.9+ (system Python is 3.13.7)
- PySide6 for the GUI

Install dependencies (recommend a venv):

```bash
cd /hoard/workspace/cleanfilenames-gui
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
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
- The **pattern** is automatically rebuilt from the token list. The tool adds the wrapping `\s*\((?: ... )\)\s*`, which matches any of the listed tokens with surrounding parentheses/spaces.
- Use the **Token Manager** dialog to edit tokens (one per line), import/export token lists, or load the default/minimal presets.
- Custom regex tweaks are still possible by editing `~/.config/cleanfilenames/config.json`, but the GUI always regenerates the regex from the current tokens to keep everything in sync.

The CLI can load alternate configs with `--config path/to/config.json`.

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
- Browse for a folder, scan, and apply changes from a single window.
- Dry run checkbox to simulate renames (status column shows "done (dry run)").
- Auto-resolve checkbox that mirrors the CLI’s `auto_resolve_conflicts` flag.
- Token Manager dialog with preset loader, import/export, duplicate finder, and regex help.
- Token suggestions table that surfaces new tags discovered during scans (append them with one click).
- Built-in manual conflict resolver so you can edit colliding targets directly in the UI.
- Table results support `Ctrl+C`/`Cmd+C` to copy selected rows as tab-separated text.
- Right-click the results to export CSV; the table includes a "Directory" column so you can see the path relative to the scan root (e.g., `Extras/Music/Track 01`). This mirrors the on-disk rename order.
- For large scans, pagination keeps the UI responsive; export to CSV for full results.

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
- Collisions are reported in the results table; if the auto-resolve toggle is enabled, the tool will append ` (1)`, ` (2)`, etc. to keep going, just like the CLI’s conflict resolution path.

## TODO

- [x] **Auto Token Discovery**: When scanning files, detect potential region tokens that aren't in the current config and offer to add them automatically. This would help users discover new patterns without manually editing the token list.

- [x] **Manual Conflict Resolution**: After scanning, if there are filename collisions or conflicts, allow manual renaming directly in the GUI. This would eliminate the need to use a file manager or CLI to resolve conflicts - everything can be managed in one place.
- [x] **Conflict Panel**: Investigate moving the conflict resolver into a dedicated panel so multi-item conflicts can be resolved without giant modal dialogs.
- [x] **Result Sorting & Filtering**: Allow sorting the scan results by type/status/message and filter the table down to only passed/failed entries for easier triage.
- [] **Detect conflicts during scan, not when applying changes:** Find conflicting files before applying changes and having them fail.

## Current Status (2025‑11‑13)

- Platform parity work is complete: the PowerShell snapshot logic now lives in `cleanfilenames_core.py` with both CLI and PySide6 GUI entrypoints, tokenized regex presets, JSON config auto-loading, context menu + CSV export, regex help dialog, and 5K-row UI truncation for large jobs.
- Normalization now drops literal `\` characters and rebuilds the region regex from the saved token list, so dry runs and real runs stay in sync even after editing presets.
- Latest fix (this session) adjusts file renames to reference the post-directory-rename parent path, eliminating the `[Errno 2] No such file or directory` bursts that showed up when applying against `/tmp/clean_test_suite`.
- Smoke test: `python3 cleanfilenames_core.py /tmp/clean_test_suite_sample --apply` succeeded with 6/6 renames; the real 50-folder dataset still needs to be regenerated (previous run already normalized everything under `/tmp/clean_test_suite`, so there is nothing left to rename right now).
- Outstanding follow-ups for tomorrow: (1) recreate `/tmp/clean_test_suite` (and the larger 4k-folder stress data, if needed), (2) re-run a GUI dry-run + apply to confirm the fix at scale, (3) delete temporary exports (`cleanfilenames.csv`, `cleanfilenames.txt`) if they are no longer needed once verification is done.
