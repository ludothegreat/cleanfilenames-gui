# Test Checklist for Clean Filenames GUI

This document outlines the test cases for the `cleanfilenames-gui` application to ensure all features and functions are working as expected.

## 1. Folder Selection and Browsing

### GUI
- **Browse Button**
  - [ ] Clicking the "Browse..." button opens a folder selection dialog.
  - [ ] Selecting a folder populates the path edit field with the correct, absolute path.
  - [ ] Canceling the folder selection dialog leaves the path edit field unchanged.
- **Path Edit Field**
  - [ ] Manually entering a valid path in the path edit field is correctly used for scanning.
  - [ ] Manually entering a path to a file (not a folder) is handled gracefully (e.g., error on scan).
  - [ ] Manually entering a non-existent path is handled gracefully (e.g., error on scan).
  - [ ] Manually entering a path with user-relative tilde (e.g., `~/Desktop`) is correctly expanded and used.
- **Scan Button**
  - [ ] Clicking "Scan" with an empty path field shows a warning message and does not proceed.
  - [ ] Clicking "Scan" with a valid folder populates the results table and updates the summary label.
  - [ ] Clicking "Scan" with a valid folder that contains no files to be renamed results in a "No changes needed" message.

### CLI
- **Path Argument**
  - [ ] Running the script with a valid folder path as an argument proceeds with the scan.
  - [ ] Running the script with an invalid or non-existent path shows a "file not found" error and exits.
  - [ ] Running the script with no path argument shows a usage/help message and exits.


## 2. Token Management

### Token Manager Dialog (GUI)
- **Opening & Closing**
  - [ ] Clicking the "Token Manager" button opens the dialog.
  - [ ] Clicking the "Cancel" button closes the dialog without saving changes.
- **Preset Loading**
  - [ ] The preset dropdown is populated with presets from the `/presets` directory (e.g., "Default", "Minimal").
  - [ ] Selecting a preset and clicking "Load Preset" replaces the content of the token editor.
  - [ ] A confirmation dialog is shown before replacing tokens if the editor is not empty.
  - [ ] Attempting to load an empty or missing preset file shows a warning.
- **Token Editing & Saving**
  - [ ] Manually adding, editing, and deleting tokens in the text editor works.
  - [ ] Clicking "Save" persists the new token list to the user's `config.json`.
  - [ ] Clicking "Save" updates the main application's config, so the next scan uses the new tokens.
  - [ ] Saving an empty token list is handled correctly (falls back to a default empty pattern).
- **Import / Export**
  - [ ] "Import List..." opens a file dialog to select a `.txt` file.
  - [ ] Importing a valid `.txt` file correctly populates the token editor.
  - [ ] "Export List..." opens a save file dialog and correctly saves the current tokens to a text file.
- **Validation**
  - [ ] Attempting to save a list with invalid filename characters (e.g., `|`, `<`, `>`) shows a validation error and prevents saving.
  - [ ] Importing a file with invalid characters shows a validation error and prevents the import.
  - [ ] The duplicate token detection correctly identifies and displays duplicates in the "Duplicates detected" area.
  - [ ] Clicking "Remove Duplicates" correctly removes duplicate lines from the editor.
- **Help Dialog**
  - [ ] Clicking "Regex Help..." opens the help dialog with explanatory text.

### Token Suggestions (GUI)
- **Discovery**
  - [ ] After a scan, the "Token Suggestions" groupbox appears if new, unknown tokens are found in filenames.
  - [ ] If no unknown tokens are found, the suggestion box remains hidden.
- **Display**
  - [ ] The table correctly displays the suggested token, its occurrence count, and a sample filename.
  - [ ] The list is sorted with the most frequent suggestions at the top.
- **Adding Tokens**
  - [ ] Selecting one or more suggestions and clicking "Add Selected to Tokens" adds them to the main configuration.
  - [ ] After being added, the token is removed from the suggestion list.
  - [ ] A confirmation message is shown after tokens are successfully added.
  - [ ] Attempting to add a token that is already in the main config (or a normalized duplicate) does not add it again.
- **Clearing Suggestions**
  - [ ] Clicking "Clear Suggestions" removes all current suggestions from the view.



## 3. Configuration Management (CLI)

### Token Configuration via CLI
- **Custom Config File**
  - [ ] Create a custom `config.json` file with a modified token list.
  - [ ] Run `cleanfilenames_core.py` with `--config /path/to/custom_config.json` and verify it uses the specified tokens for renaming.
  - [ ] Run `cleanfilenames_core.py` with `--config` pointing to a non-existent file shows an error and exits gracefully.
  - [ ] Run `cleanfilenames_core.py` with `--config` pointing to a malformed JSON file shows a configuration error and exits gracefully.
- **Default Config Fallback**
  - [ ] Running `cleanfilenames_core.py` without `--config` uses the default token list.



## 4. Renaming Logic

### GUI Renaming
- **Basic Functionality**
  - [ ] Scan a folder with files/directories needing renaming.
  - [ ] Verify the results table accurately reflects the proposed renames (Old, New, Type).
  - [ ] Click "Apply Changes" (with Dry Run unchecked) and confirm files/directories are renamed on disk.
  - [ ] Rescan the folder and verify that no pending candidates remain (or only the unresolved conflicts).
- **Dry Run Mode**
  - [ ] Select "Dry run (no changes)" checkbox.
  - [ ] Click "Apply Changes" and verify that no actual changes are made to the filesystem.
  - [ ] Verify that the status column in the table shows "done (dry run)".
- **File Types**
  - [ ] Test renaming various file types (e.g., .zip, .rar, .nes, .md, .txt).
- **Directory Renaming**
  - [ ] Test renaming directories with region tags.
  - [ ] Test renaming nested directories with region tags (deepest-first logic).
  - [ ] Verify that files within renamed directories have their paths correctly updated in the results table.
- **Root Directory Renaming**
  - [ ] Enable/disable "Rename Root" setting (in config) and verify its effect on renaming the scanned root folder itself.

### CLI Renaming
- **Basic Functionality**
  - [ ] Run `cleanfilenames_core.py /path/to/folder` (preview mode) and verify the console output matches expected renames.
  - [ ] Run `cleanfilenames_core.py /path/to/folder --apply` and confirm files/directories are renamed on disk.
  - [ ] Run `cleanfilenames_core.py /path/to/folder --apply --dry-run` and verify no changes are made to the filesystem, but output shows proposed changes.




## 5. Conflict Resolution

### Manual Conflict Resolution (GUI)
- **"Edit Target Name..." Context Menu Option**
  - [ ] Right-clicking on a single conflicting entry in the results table shows the "Edit Target Name..." option.
  - [ ] Selecting "Edit Target Name..." opens an input dialog pre-populated with the current proposed new name.
  - [ ] Changing the name to a unique, valid name (e.g., `new_name_unique.txt`) resolves the conflict, updates the entry in the table, and changes its status (e.g., to "error (edited)" or "pending" if applicable).
  - [ ] Attempting to change the name to an empty string shows a warning and prevents the change.
  - [ ] Attempting to change the name to a name containing path separators (`/`, `\`) shows a warning and prevents the change.
  - [ ] Attempting to change the name to a name that still conflicts with another entry (or an existing file on disk) shows an error when attempting to apply.
- **"Resolve Conflict..." Context Menu Option**
  - [ ] Right-clicking on a conflicting entry that is part of a multi-item collision (i.e., multiple items would rename to the same target) shows the "Resolve Conflict..." option.
  - [ ] Selecting "Resolve Conflict..." opens a dedicated dialog listing all conflicting items with editable target name fields.
  - [ ] Changing the target names for each item in the dialog to unique, valid names and accepting resolves the conflicts in the table.
  - [ ] Attempting to accept the dialog with unresolved conflicts (e.g., still having duplicate target names among the conflicting items) shows an error.
  - [ ] Canceling the "Resolve Conflict" dialog leaves the entries unchanged.

### Automatic Conflict Resolution (GUI)
- **Checkbox Functionality**
  - [ ] Toggling the "Auto-resolve conflicts" checkbox (checking/unchecking) correctly updates and saves the setting to `config.json`.
  - [ ] The checkbox state persists across application restarts.
- **Behavior with Auto-resolve ON**
  - [ ] With "Auto-resolve conflicts" checked, scan a folder containing collision scenarios (generated by `generate_cleanfilenames_testdata.py`).
  - [ ] Click "Apply Changes" (with Dry Run unchecked).
  - [ ] Verify that all conflicting items are successfully renamed on disk by appending a numeric suffix (e.g., `filename (1).ext`, `filename (2).ext`).
  - [ ] Verify that no "error" statuses are reported for these automatically resolved conflicts in the results table.
- **Behavior with Auto-resolve OFF**
  - [ ] With "Auto-resolve conflicts" unchecked, scan a folder containing collision scenarios.
  - [ ] Click "Apply Changes" (with Dry Run unchecked).
  - [ ] Verify that conflicting items are reported with an "error" status in the results table and are *not* renamed on disk.
  - [ ] Verify the message for these errors correctly indicates a conflict (e.g., "Target already exists on disk" or "Multiple items are targeting this name").



## 6. Table and Display Features

### Pagination
- **Page Size**
  - [ ] Changing the "Rows per page" spinbox value updates the number of rows displayed in the table.
  - [ ] The pagination information (e.g., "Showing 1-100 of 250 filtered...") updates correctly.
- **Navigation**
  - [ ] Clicking the "Next" button navigates to the next page of results.
  - [ ] Clicking the "Previous" button navigates to the previous page of results.
  - [ ] The "Next" button is disabled when on the last page of results.
  - [ ] The "Previous" button is disabled when on the first page of results.
  - [ ] Navigating between pages correctly displays the corresponding subset of candidates.

### Filtering
- **Filter ComboBox**
  - [ ] Selecting "Success only" from the filter dropdown correctly displays only items with a "done" or "done (dry run)" status.
  - [ ] Selecting "Errors only" from the filter dropdown correctly displays only items with an "error" or "error (edited)" status.
  - [ ] Selecting "All" from the filter dropdown correctly displays all candidates.
  - [ ] Changing the filter updates the summary label and pagination information.

### Sorting
- **Sort ComboBox**
  - [ ] Selecting "Type" sorts the table by item type (file/directory).
  - [ ] Selecting "Status" sorts the table by candidate status.
  - [ ] Selecting "Message" sorts the table by the message column.
  - [ ] Selecting "Default" restores the default sorting order (as collected).
- **Sort Order Button**
  - [ ] Clicking the "Asc" / "Desc" button toggles the sort order (ascending/descending).
  - [ ] The sort order button is enabled only when a sort field other than "Default" is selected.

### Context Menu (Right-Click on Table)
- **Copy Selected (Tab-separated)**
  - [ ] Selecting one or more rows and choosing "Copy Selected (Tab-separated)" from the context menu copies the content of the selected rows to the clipboard, with columns separated by tabs.
- **Export to CSV…**
  - [ ] Choosing "Export to CSV..." opens a file save dialog.
  - [ ] Saving to a CSV file correctly exports all currently filtered table data (or selected rows if any) with proper CSV formatting (headers, quoted fields).

### Summary Label
- [ ] The summary label (e.g., "Found X candidates (Y files, Z directories).") accurately reflects the total number of candidates found.
- [ ] The summary label updates to show filter information (e.g., "Filter matched N results.") when a filter is active.




## 7. Error Handling and Edge Cases

### Filesystem and Permissions
- [ ] **Read-Only Directory:** Attempt to scan a directory with read-only permissions. Verify a graceful error is reported.
- [ ] **No-Permissions Directory:** Attempt to scan a directory with no read permissions at all. Verify a graceful error.
- [ ] **No-Write-Permissions:** Attempt to apply renames within a directory where the user does not have write permissions. Verify that the table shows errors for each failed rename with a clear "Permission denied" message.
- [ ] **Locked Files:** (Harder to test) Attempt to rename a file that is locked by another process.

### Filenames and Paths
- [ ] **Very Long Filenames:** Create and scan files with filenames at or near the filesystem's maximum limit (e.g., 255 characters).
- [ ] **Very Long Paths:** Create a deeply nested directory structure and test scanning/renaming files within it.
- [ ] **Special Characters:** Create and scan files with a wide range of Unicode characters, including different languages, emojis, and symbols (`!@#$%^&()[]{}',.`).
- [ ] **Empty/Whitespace Names:** Create files or directories that are just whitespace (e.g., `" .txt"`).

### Application Behavior
- [ ] **Empty Folder:** Scan a folder that contains no files or subdirectories. Verify the application reports "No changes needed".
- [ ] **Interruption (Manual):** Start a large "apply changes" operation and close the application mid-process. Re-open and re-scan the directory to check for inconsistent state (e.g., some files renamed, some not).
- [ ] **Large-Scale Performance:**
    - [ ] Generate the "large" test dataset (`--large`).
    - [ ] Scan the directory and measure the time it takes.
    - [ ] Observe GUI responsiveness while the table is being populated.
    - [ ] Observe memory usage of the application during the scan.

