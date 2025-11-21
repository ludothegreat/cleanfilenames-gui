"""PySide6 GUI for the cleanfilenames tool."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QComboBox,
    QTextBrowser,
    QMenu,
    QSpinBox,
    QGroupBox,
    QInputDialog,
    QScrollArea,
)

from config_manager import (
    AppConfig,
    ConfigLoadError,
    DEFAULT_PATTERN,
    DEFAULT_TOKENS,
    PRESETS_DIR,
    build_regex,
    load_preset_tokens,
)
from token_manager import (
    TokenSuggestion,
    TokenTracker,
    find_duplicate_tokens,
    normalize_token,
    validate_tokens,
)
from cleanfilenames_core import apply_candidates, collect_candidates, summarize, RenameCandidate


def _normalize_path_for_gui(path: Path) -> str:
    return str(path.resolve()).lower()


def get_presets() -> List[str]:
    """Return a list of available preset names."""
    if not PRESETS_DIR.exists():
        return []
    return sorted([p.stem for p in PRESETS_DIR.glob("*.txt")])


HELP_TEXT = """
<h3>Tokens &amp; Regex</h3>
<p>Each token represents an entire region string that appears inside parentheses.
For example, if your files are named:</p>
<ul>
  <li>Game 1 (USA,EU,JP).zip</li>
  <li>Game 2 (En,Ja,Fr,De,Es,It,Pt,Ko,Ru,Ar).zip</li>
</ul>
<p>Then you need two tokens. One token per line:</p>
<pre>USA,EU,JP
En,Ja,Fr,De,Es,It,Pt,Ko,Ru,Ar</pre>
<p>When the tool rebuilds the regex, those tokens become part of the expression:</p>
<pre>\\s*\\((?:USA,EU,JP|En,Ja,Fr,De,Es,It,Pt,Ko,Ru,Ar|...)\\)\\s*</pre>
<p>Any parentheses containing one of those tokens (with optional spaces) will be removed.</p>
<h4>Customize By</h4>
<ul>
  <li>Choosing a preset to load a known token list.</li>
  <li>Editing tokens (one per line). The regex updates automatically.</li>
  <li>Importing/exporting token lists to share configurations.</li>
  <li>Saving token edits to <code>config.json</code>; the CLI and GUI will both use them.</li>
</ul>
<p>Tokens may include regex syntax if you intentionally want pattern matching (e.g., <code>v\\d+\\.\\d+</code>),
but remember that the entire token is inserted into the regex as-is.</p>
<p>A helpful regex cheat sheet can be found here:
<a href="https://www.rexegg.com/regex-quickstart.php">https://www.rexegg.com/regex-quickstart.php</a></p>
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Clean Filenames")
        self.resize(1100, 650)
        self.candidates = []
        self.current_path: Path | None = None
        self.row_index_map: List[int] = []
        self.token_tracker: Optional[TokenTracker] = None
        self.suggestions: List[TokenSuggestion] = []

        container = QWidget()
        self.setCentralWidget(container)
        self.config = AppConfig.load()
        main_layout = QVBoxLayout(container)

        # Path picker
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select a folder to scan…")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self.on_browse)
        path_layout.addWidget(QLabel("Folder:"))
        path_layout.addWidget(self.path_edit, stretch=1)
        path_layout.addWidget(browse_btn)
        tokens_btn = QPushButton("Token Manager")
        tokens_btn.clicked.connect(self.on_token_manager)
        path_layout.addWidget(tokens_btn)
        main_layout.addLayout(path_layout)

        # Dry run + action buttons
        controls_layout = QHBoxLayout()
        self.dry_run_checkbox = QCheckBox("Dry run (no changes)")
        self.dry_run_checkbox.setChecked(True)
        self.auto_resolve_checkbox = QCheckBox("Auto-resolve conflicts")
        self.auto_resolve_checkbox.setChecked(self.config.auto_resolve_conflicts)
        self.auto_resolve_checkbox.toggled.connect(self.on_auto_resolve_toggled)

        btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self.on_scan)
        self.run_btn = QPushButton("Apply Changes")
        self.run_btn.clicked.connect(self.on_apply)
        self.run_btn.setEnabled(False)
        btn_layout.addWidget(self.scan_btn)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addStretch(1)
        controls_layout.addWidget(self.dry_run_checkbox)
        controls_layout.addWidget(self.auto_resolve_checkbox)
        controls_layout.addLayout(btn_layout)
        main_layout.addLayout(controls_layout)

        # Summary label
        self.summary_label = QLabel("No folder selected.")
        main_layout.addWidget(self.summary_label)
        self.suggestion_group = QGroupBox("Token Suggestions")
        suggestion_layout = QVBoxLayout(self.suggestion_group)
        self.suggestion_info = QLabel("Run a scan to discover new tokens.")
        suggestion_layout.addWidget(self.suggestion_info)
        self.suggestion_table = QTableWidget(0, 3)
        self.suggestion_table.setHorizontalHeaderLabels(["Token", "Count", "Sample"])
        suggestion_header = self.suggestion_table.horizontalHeader()
        suggestion_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        suggestion_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        suggestion_header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.suggestion_table.verticalHeader().setVisible(False)
        self.suggestion_table.setAlternatingRowColors(True)
        self.suggestion_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.suggestion_table.setEditTriggers(QTableWidget.NoEditTriggers)
        suggestion_layout.addWidget(self.suggestion_table)
        suggestion_btns = QHBoxLayout()
        self.add_suggestions_btn = QPushButton("Add Selected to Tokens")
        self.add_suggestions_btn.clicked.connect(self.add_selected_suggestions)
        suggestion_btns.addWidget(self.add_suggestions_btn)
        self.clear_suggestions_btn = QPushButton("Clear Suggestions")
        self.clear_suggestions_btn.clicked.connect(self.clear_suggestions)
        suggestion_btns.addWidget(self.clear_suggestions_btn)
        suggestion_btns.addStretch(1)
        suggestion_layout.addLayout(suggestion_btns)
        self.suggestion_group.setVisible(False)
        main_layout.addWidget(self.suggestion_group)
        self.clear_suggestions()
        self.page_size = 1000
        self.current_page = 0
        self.total_pages = 1
        self.sort_field = "default"
        self.sort_ascending = True
        self.status_filter_mode = "all"
        self.filtered_indices: List[int] = []
        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel("Filter results:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Success only", "Errors only"])
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        controls_row.addWidget(self.filter_combo)
        controls_row.addStretch(1)
        controls_row.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Default", "Type", "Status", "Message"])
        self.sort_combo.currentTextChanged.connect(self.on_sort_changed)
        controls_row.addWidget(self.sort_combo)
        self.sort_order_btn = QPushButton("Asc")
        self.sort_order_btn.clicked.connect(self.toggle_sort_order)
        self.sort_order_btn.setEnabled(False)
        controls_row.addWidget(self.sort_order_btn)
        main_layout.addLayout(controls_row)

        pagination_controls = QHBoxLayout()
        self.pagination_info = QLabel("No results to display.")
        pagination_controls.addWidget(self.pagination_info)
        pagination_controls.addStretch(1)
        pagination_controls.addWidget(QLabel("Rows per page:"))
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(100, 20000)
        self.page_size_spin.setSingleStep(100)
        self.page_size_spin.setValue(self.page_size)
        self.page_size_spin.valueChanged.connect(self.on_page_size_changed)
        pagination_controls.addWidget(self.page_size_spin)
        self.prev_page_btn = QPushButton("Previous")
        self.prev_page_btn.clicked.connect(lambda: self.change_page(-1))
        pagination_controls.addWidget(self.prev_page_btn)
        self.next_page_btn = QPushButton("Next")
        self.next_page_btn.clicked.connect(lambda: self.change_page(1))
        pagination_controls.addWidget(self.next_page_btn)
        main_layout.addLayout(pagination_controls)

        # Table of changes
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Type", "Original (rel)", "New (rel)", "Status", "Message"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_table_menu)
        QShortcut(QKeySequence.Copy, self.table, activated=self.copy_selected_rows)
        main_layout.addWidget(self.table, stretch=1)

    # slots
    def on_browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Folder")
        if directory:
            self.path_edit.setText(directory)

    def on_scan(self) -> None:
        path_text = self.path_edit.text().strip()
        if not path_text:
            QMessageBox.warning(self, "Missing folder", "Please select a folder first.")
            return

        target_path = Path(path_text)
        try:
            tracker_tokens = (
                self.config.tokens if self.config.tokens is not None else DEFAULT_TOKENS
            )
            self.token_tracker = TokenTracker(tracker_tokens)
            self.candidates = collect_candidates(
                target_path, config=self.config, token_tracker=self.token_tracker
            )
            self.current_page = 0
            self.sort_field = "default"
            self.sort_combo.setCurrentText("Default")
            self.sort_order_btn.setEnabled(False)
            self.sort_ascending = True
            self.sort_order_btn.setText("Asc")
            self.status_filter_mode = "all"
            self.filter_combo.setCurrentText("All")
            self.current_path = target_path
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "Folder not found",
                f"The path '{path_text}' does not exist.",
            )
            self.candidates = []
            self.current_page = 0
            self.update_table()
            self.token_tracker = None
            self.clear_suggestions()
            return

        if not self.candidates:
            self.summary_label.setText("No changes needed.")
            self.run_btn.setEnabled(False)
            self.current_page = 0
            self.update_table()
            self.suggestions = self.token_tracker.suggestions() if self.token_tracker else []
            self.update_suggestions_view()
            return

        summary = summarize(self.candidates)
        self.summary_label.setText(
            f"Found {summary['total']} candidates "
            f"({summary['files']} files, {summary['directories']} directories)."
        )
        self.run_btn.setEnabled(True)
        self.update_table()
        self.suggestions = self.token_tracker.suggestions()
        self.update_suggestions_view()

    def on_apply(self) -> None:
        if not self.current_path:
            QMessageBox.warning(self, "No folder scanned", "Please scan a folder first.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm renames",
            f"Apply changes to '{self.current_path.name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.candidates = collect_candidates(
                self.current_path, config=self.config, token_tracker=self.token_tracker
            )
            if not self.candidates:
                QMessageBox.information(self, "No changes", "No changes to apply.")
                return

            dry_run = self.dry_run_checkbox.isChecked()
            apply_candidates(
                self.candidates,
                config=self.config,
                dry_run=dry_run,
            )
            summary = summarize(self.candidates)
        finally:
            QApplication.restoreOverrideCursor()

        self.update_table()
        if dry_run:
            message = (
                f"Dry run complete: {summary['completed']} simulated renames "
                f"({summary['errors']} would fail)."
            )
            if summary["errors"]:
                message += "\n\nErrors are shown in the results table below."
                QMessageBox.warning(self, "Dry run finished", message)
            else:
                QMessageBox.information(self, "Dry run finished", message)
            return

        message = (
            f"Completed {summary['completed']} renames "
            f"({summary['errors']} errors)."
        )
        if summary["errors"]:
            message += "\n\nErrors are shown in the results table below."
            QMessageBox.warning(self, "Finished with errors", message)
        else:
            QMessageBox.information(self, "Finished", message)

    def on_auto_resolve_toggled(self, checked: bool) -> None:
        """Update and save the auto-resolve setting."""
        if self.config.auto_resolve_conflicts == checked:
            return
        self.config.auto_resolve_conflicts = checked
        self.config.save()
        
    def on_token_manager(self) -> None:
        dialog = TokenManagerDialog(self.config, self)
        dialog.exec()
        if dialog.config_updated:
            self.config = AppConfig.load()
            self.token_tracker = None
            QMessageBox.information(
                self,
                "Tokens updated",
                "Token changes saved. Please rescan folders to update suggestions.",
            )
            if self.suggestions:
                token_source = self.config.tokens if self.config.tokens is not None else DEFAULT_TOKENS
                existing_norm = {
                    normalize_token(token)
                    for token in token_source
                    if normalize_token(token)
                }
                self.suggestions = [
                    suggestion
                    for suggestion in self.suggestions
                    if normalize_token(suggestion.token) not in existing_norm
                ]
        self.update_suggestions_view()

    def update_table(self) -> None:
        base_total = len(self.candidates)
        if base_total == 0:
            self.filtered_indices = []
            self.table.setUpdatesEnabled(False)
            self.table.setRowCount(0)
            self.table.setUpdatesEnabled(True)
            self.pagination_info.setText("No results to display.")
            self.prev_page_btn.setEnabled(False)
            self.next_page_btn.setEnabled(False)
            self.summary_label.setText("No changes to be made.")
            self.run_btn.setEnabled(False)
            self.update_suggestions_view()
            return

        status_mode = self.status_filter_mode
        filtered_pairs = []
        for idx, cand in enumerate(self.candidates):
            if status_mode == "success" and not cand.status.startswith("done"):
                continue
            if status_mode == "error" and not (
                cand.status == "error" or cand.status == "error (edited)"
            ):
                continue
            filtered_pairs.append((idx, cand))

        if self.sort_field != "default":
            reverse = not self.sort_ascending
            if self.sort_field == "type":
                filtered_pairs.sort(key=lambda pair: pair[1].item_type, reverse=reverse)
            elif self.sort_field == "status":
                filtered_pairs.sort(key=lambda pair: pair[1].status, reverse=reverse)
            elif self.sort_field == "message":
                filtered_pairs.sort(key=lambda pair: pair[1].message or "", reverse=reverse)

        self.filtered_indices = [idx for idx, _ in filtered_pairs]
        total = len(filtered_pairs)

        if total == 0:
            self.table.setUpdatesEnabled(False)
            self.table.setRowCount(0)
            self.table.setUpdatesEnabled(True)
            self.pagination_info.setText("No results match the current filter.")
            self.prev_page_btn.setEnabled(False)
            self.next_page_btn.setEnabled(False)
            base_files = sum(1 for c in self.candidates if c.item_type == "file")
            base_dirs = sum(1 for c in self.candidates if c.item_type == "directory")
            self.summary_label.setText(
                f"Found {base_total} candidates ({base_files} files, {base_dirs} directories). "
                "Filter matched 0 results."
            )
            self.run_btn.setEnabled(False)
            self.update_suggestions_view()
            return

        self.total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if self.current_page >= self.total_pages:
            self.current_page = self.total_pages - 1
        start_index = self.current_page * self.page_size
        end_index = min(start_index + self.page_size, total)
        display_subset = filtered_pairs[start_index:end_index]
        self.row_index_map = [idx for idx, _ in display_subset]

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        for original_idx, cand in display_subset:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(cand.item_type))
            orig_item = QTableWidgetItem(cand.original_relative_path or str(cand.path))
            new_item = QTableWidgetItem(cand.relative_path or str(cand.new_path))
            self.table.setItem(row, 1, orig_item)
            self.table.setItem(row, 2, new_item)
            status_item = QTableWidgetItem(cand.status)
            if cand.status == "error":
                status_item.setForeground(Qt.red)
            elif cand.status == "error (edited)":
                status_item.setForeground(Qt.darkRed)
            elif cand.status.startswith("done"):
                status_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 3, status_item)
            self.table.setItem(row, 4, QTableWidgetItem(cand.message))

        self.table.setUpdatesEnabled(True)

        file_count = sum(1 for c in self.candidates if c.item_type == "file")
        dir_count = sum(1 for c in self.candidates if c.item_type == "directory")
        filter_note = ""
        if total != base_total or status_mode != "all":
            filter_note = f" Filtered view: {total} shown."
        self.summary_label.setText(
            f"Found {base_total} candidates ({file_count} files, {dir_count} directories).{filter_note}"
        )
        self.pagination_info.setText(
            f"Showing {start_index + 1}-{end_index} of {total} filtered "
            f"(Page {self.current_page + 1}/{self.total_pages})"
        )
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
        self.run_btn.setEnabled(True)
        self.update_suggestions_view()

    def change_page(self, delta: int) -> None:
        if not self.candidates:
            return
        new_page = self.current_page + delta
        new_page = max(0, min(new_page, self.total_pages - 1))
        if new_page == self.current_page:
            return
        self.current_page = new_page
        self.update_table()

    def on_page_size_changed(self, value: int) -> None:
        if value <= 0:
            return
        self.page_size = value
        self.current_page = 0
        self.update_table()

    def on_filter_changed(self, text: str) -> None:
        mapping = {
            "All": "all",
            "Success only": "success",
            "Errors only": "error",
        }
        self.status_filter_mode = mapping.get(text, "all")
        self.current_page = 0
        self.update_table()

    def on_sort_changed(self, text: str) -> None:
        mapping = {
            "Default": "default",
            "Type": "type",
            "Status": "status",
            "Message": "message",
        }
        self.sort_field = mapping.get(text, "default")
        self.sort_order_btn.setEnabled(self.sort_field != "default")
        self.current_page = 0
        self.update_table()

    def toggle_sort_order(self) -> None:
        self.sort_ascending = not self.sort_ascending
        self.sort_order_btn.setText("Asc" if self.sort_ascending else "Desc")
        if self.sort_field != "default":
            self.update_table()

    def update_suggestions_view(self) -> None:
        if not self.suggestions:
            self.suggestion_group.setVisible(False)
            self.suggestion_table.setRowCount(0)
            self.suggestion_info.setText("No new token suggestions.")
            self.add_suggestions_btn.setEnabled(False)
            self.clear_suggestions_btn.setEnabled(False)
            return
        self.suggestion_group.setVisible(True)
        self.suggestion_info.setText("Select tokens to add them to your configuration.")
        self.suggestion_table.setRowCount(0)
        for suggestion in self.suggestions:
            row = self.suggestion_table.rowCount()
            self.suggestion_table.insertRow(row)
            token_item = QTableWidgetItem(suggestion.token)
            count_item = QTableWidgetItem(str(suggestion.count))
            count_item.setTextAlignment(Qt.AlignCenter)
            sample_item = QTableWidgetItem(suggestion.samples[0] if suggestion.samples else "")
            self.suggestion_table.setItem(row, 0, token_item)
            self.suggestion_table.setItem(row, 1, count_item)
            self.suggestion_table.setItem(row, 2, sample_item)
        self.add_suggestions_btn.setEnabled(True)
        self.clear_suggestions_btn.setEnabled(True)

    def clear_suggestions(self) -> None:
        self.suggestions = []
        self.suggestion_group.setVisible(False)
        self.suggestion_table.setRowCount(0)
        self.suggestion_info.setText("No new token suggestions.")
        self.add_suggestions_btn.setEnabled(False)
        self.clear_suggestions_btn.setEnabled(False)

    def add_selected_suggestions(self) -> None:
        if not self.suggestions:
            return
        selection = self.suggestion_table.selectionModel().selectedRows()
        if not selection:
            QMessageBox.information(self, "Add Tokens", "Select at least one suggestion to add.")
            return
        selected_indices = sorted({index.row() for index in selection})
        new_tokens = [
            self.suggestions[idx].token
            for idx in selected_indices
            if idx < len(self.suggestions)
        ]
        if not new_tokens:
            return
        tokens_source = self.config.tokens if self.config.tokens is not None else DEFAULT_TOKENS
        tokens = list(tokens_source)
        existing_norm = {normalize_token(token) for token in tokens if normalize_token(token)}
        added_tokens: List[str] = []
        for token in new_tokens:
            normalized = normalize_token(token)
            if not normalized or normalized in existing_norm:
                continue
            tokens.append(token)
            existing_norm.add(normalized)
            added_tokens.append(token)
        if not added_tokens:
            QMessageBox.information(
                self,
                "Tokens already present",
                "Selected suggestions already exist in your configuration.",
            )
            return
        self.config.tokens = tokens
        self.config.regex = build_regex(tokens)
        self.config.save()
        self.config = AppConfig.load()
        added_norm = {normalize_token(token) for token in added_tokens}
        self.suggestions = [
            suggestion
            for suggestion in self.suggestions
            if normalize_token(suggestion.token) not in added_norm
        ]
        QMessageBox.information(
            self,
            "Tokens added",
            "Selected suggestions were added to your configuration.",
        )
        if self.token_tracker:
            tracker_tokens = (
                self.config.tokens if self.config.tokens is not None else DEFAULT_TOKENS
            )
            self.token_tracker = TokenTracker(tracker_tokens)
        self.update_suggestions_view()

    def copy_selected_rows(self) -> None:
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        if not rows:
            return
        lines = []
        for row in rows:
            if row >= len(self.row_index_map):
                continue
            cand = self.candidates[self.row_index_map[row]]
            lines.append(
                f"{cand.item_type}\t{cand.original_relative_path or cand.path}\t"
                f"{cand.relative_path or cand.new_path}\t{cand.status}\t{cand.message}"
            )
        if lines:
            QApplication.clipboard().setText("\n".join(lines))

    def show_table_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        copy_action = menu.addAction("Copy Selected (Tab-separated)")
        export_action = menu.addAction("Export to CSV…")
        edit_action = menu.addAction("Edit Target Name…")
        resolve_action = menu.addAction("Resolve Multi-Conflicts…")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == copy_action:
            self.copy_selected_rows()
        elif action == export_action:
            self.export_csv()
        elif action == edit_action:
            self.edit_selected_target()
        elif action == resolve_action:
            resolve_conflict(self)

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            str(Path.home() / "cleanfilenames.csv"),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        if rows:
            candidate_indices = [
                self.row_index_map[row]
                for row in rows
                if row < len(self.row_index_map)
            ]
        else:
            candidate_indices = list(self.filtered_indices or range(len(self.candidates)))
        lines = ["type,old,new,status,message"]
        for idx in candidate_indices:
            cand = self.candidates[idx]
            fields = [
                cand.item_type,
                cand.original_relative_path or str(cand.path),
                cand.relative_path or str(cand.new_path),
                cand.status,
                cand.message.replace('"', '""'),
            ]
            lines.append(",".join(f'"{field}"' for field in fields))
        Path(path).write_text("\n".join(lines))

    def edit_selected_target(self) -> None:
        if not self.candidates or not self.row_index_map:
            return
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Edit Target", "Select a row to edit.")
            return
        row = rows[0].row()
        if row >= len(self.row_index_map):
            QMessageBox.warning(self, "Edit Target", "Selected row cannot be edited.")
            return
        cand = self.candidates[self.row_index_map[row]]
        new_name, ok = QInputDialog.getText(
            self,
            "Edit Target Name",
            "New name:",
            text=cand.new_name,
        )
        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()

        # Validate the new name
        if any(sep in new_name for sep in ("/", "\\")):
            QMessageBox.warning(
                self,
                "Invalid name",
                "Name cannot contain path separators (/ or \\).",
            )
            return

        # Confirm the rename operation
        confirm = QMessageBox.question(
            self,
            "Confirm Rename",
            f"This will immediately rename:\n\n"
            f"From: {cand.path.name}\n"
            f"To: {new_name}\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        # Actually rename the file/directory on disk
        if not self.apply_rename_on_disk(cand, new_name):
            return

        # Notify success but don't rescan - let them edit multiple files
        QMessageBox.information(
            self,
            "Rename Complete",
            f"File renamed successfully.\n\n"
            f"Note: You'll need to rescan before applying additional changes.",
        )

    def apply_rename_on_disk(self, cand: "RenameCandidate", new_name: str) -> bool:
        """Actually rename a file or directory on disk."""
        try:
            source = cand.path
            if not source.exists():
                QMessageBox.warning(
                    self,
                    "File Not Found",
                    f"Source file not found: {source}",
                )
                return False

            parent = source.parent
            target = parent / new_name

            if target.exists():
                QMessageBox.warning(
                    self,
                    "Target Exists",
                    f"A file or directory with the name '{new_name}' already exists.",
                )
                return False

            source.rename(target)
            return True

        except OSError as exc:
            QMessageBox.critical(
                self,
                "Rename Failed",
                f"Failed to rename file:\n\n{exc}",
            )
            return False



class TokenManagerDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Token Manager")
        self.resize(600, 480)
        self.config = config
        self._config_updated = False
        self.current_preset_name: Optional[str] = None
        self.current_preset_tokens: List[str] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tokens (one per line, raw text or regex allowed):"))
        
        self.warning_text = QTextBrowser()
        self.warning_text.setReadOnly(True)
        self.warning_text.setStyleSheet("background-color: #fffacd; border: 1px solid #ffebcd; padding: 5px;")
        self.warning_text.setMaximumHeight(60)
        self.warning_text.setVisible(False)
        layout.addWidget(self.warning_text)

        tokens_source = config.tokens if config.tokens is not None else DEFAULT_TOKENS
        tokens_text = "\n".join(tokens_source)
        self.token_edit = QPlainTextEdit(tokens_text)
        self.token_edit.setMinimumHeight(260)
        self.token_edit.textChanged.connect(self.refresh_duplicate_notice)
        self.token_edit.textChanged.connect(self.update_warning_message)
        layout.addWidget(self.token_edit)

        action_layout = QHBoxLayout()
        self.preset_combo = QComboBox()
        action_layout.addWidget(self.preset_combo)
        load_preset_btn = QPushButton("Load Preset")
        load_preset_btn.clicked.connect(self.load_preset)
        action_layout.addWidget(load_preset_btn)
        action_layout.addStretch(1)

        # Determine initial preset state for warning message
        default_preset_tokens = load_preset_tokens("default")
        minimal_preset_tokens = load_preset_tokens("minimal")
        current_config_tokens = config.tokens if config.tokens is not None else []
        
        if sorted(current_config_tokens) == sorted(default_preset_tokens):
            self.current_preset_name = "default"
            self.current_preset_tokens = default_preset_tokens
        elif sorted(current_config_tokens) == sorted(minimal_preset_tokens):
            self.current_preset_name = "minimal"
            self.current_preset_tokens = minimal_preset_tokens
        else:
            self.current_preset_name = None
            self.current_preset_tokens = list(current_config_tokens)

        import_btn = QPushButton("Import List…")
        import_btn.clicked.connect(self.import_tokens)
        action_layout.addWidget(import_btn)
        export_btn = QPushButton("Export List…")
        export_btn.clicked.connect(self.export_tokens)
        action_layout.addWidget(export_btn)

        help_btn = QPushButton("Regex Help…")
        help_btn.clicked.connect(self.show_help)
        action_layout.addWidget(help_btn)

        self.remove_dupes_btn = QPushButton("Remove Duplicates")
        self.remove_dupes_btn.clicked.connect(self.remove_duplicates)
        action_layout.addWidget(self.remove_dupes_btn)
        layout.addLayout(action_layout)

        self.duplicate_display = QPlainTextEdit()
        self.duplicate_display.setReadOnly(True)
        self.duplicate_display.setMaximumHeight(80)
        layout.addWidget(self.duplicate_display)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.refresh_presets()
        self.update_warning_message()
        self.refresh_duplicate_notice()

    @property
    def config_updated(self) -> bool:
        return self._config_updated

    def current_tokens(self) -> List[str]:
        return [
            line.strip()
            for line in self.token_edit.toPlainText().splitlines()
            if line.strip()
        ]

    def update_warning_message(self) -> None:
        """Display a warning if a default/minimal preset is loaded and being edited."""
        if not self.current_preset_name:
            self.warning_text.setVisible(False)
            return

        current_tokens_in_editor = self.current_tokens()
        
        # Compare current editor tokens with the last loaded preset tokens
        if sorted(current_tokens_in_editor) == sorted(self.current_preset_tokens):
            if self.current_preset_name in ["default", "minimal"]:
                self.warning_text.setHtml(
                    "<p>You are viewing a <b>predefined token set</b>. "
                    "Changes will overwrite it globally. "
                    "For custom tokens, consider saving as a new preset or editing your `config.json`.</p>"
                )
                self.warning_text.setVisible(True)
            else:
                self.warning_text.setVisible(False)
        else:
            # User has modified the tokens, hide the warning
            self.warning_text.setVisible(False)

    def refresh_duplicate_notice(self) -> None:
        tokens = self.current_tokens()
        duplicates = find_duplicate_tokens(tokens)
        if duplicates:
            dup_lines = [f"{token} ({count})" for token, count in duplicates.items()]
            self.duplicate_display.setPlainText(
                "Duplicates detected:\n" + "\n".join(dup_lines)
            )
            self.remove_dupes_btn.setEnabled(True)
        else:
            self.duplicate_display.setPlainText("No duplicate tokens detected.")
            self.remove_dupes_btn.setEnabled(False)

    def remove_duplicates(self) -> None:
        tokens = self.current_tokens()
        seen = set()
        deduped: List[str] = []
        for token in tokens:
            normalized = normalize_token(token)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(token)
        if len(deduped) == len(tokens):
            QMessageBox.information(self, "Duplicates", "No duplicates to remove.")
            return
        self.token_edit.setPlainText("\n".join(deduped))
        self.apply_tokens(deduped)
        QMessageBox.information(
            self,
            "Duplicates removed",
            "Duplicate tokens removed and configuration updated.",
        )
        self.refresh_duplicate_notice()

    def save_and_close(self) -> None:
        tokens = self.current_tokens()
        errors = validate_tokens(tokens)
        if errors:
            QMessageBox.warning(
                self,
                "Invalid Tokens",
                "Please fix the following errors:\n\n" + "\n".join(errors),
            )
            return
        self.apply_tokens(tokens)
        QMessageBox.information(self, "Tokens saved", "Token configuration updated.")
        self.accept()

    def import_tokens(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Token List", str(Path.home()), "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            text = Path(path).read_text()
            tokens = [line.strip() for line in text.splitlines() if line.strip()]
            errors = validate_tokens(tokens)
            if errors:
                QMessageBox.warning(
                    self,
                    "Invalid Tokens in File",
                    f"The file '{Path(path).name}' contains errors:\n\n"
                    + "\n".join(errors),
                )
                return
        except OSError as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return
        self.token_edit.setPlainText(text.strip())
        self.refresh_duplicate_notice()

    def export_tokens(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Token List", str(Path.home() / "tokens.txt"), "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            Path(path).write_text(self.token_edit.toPlainText().strip())
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    def refresh_presets(self) -> None:
        """Scan for presets and populate the dropdown."""
        self.presets = get_presets()
        self.preset_combo.clear()
        if self.presets:
            self.preset_combo.addItems([p.replace("_", " ").title() for p in self.presets])
        # After refreshing presets, reset current_preset_name to avoid stale state
        self.current_preset_name = None
        self.current_preset_tokens = []
        self.update_warning_message()

    def load_preset(self) -> None:
        """Load tokens from the selected preset file."""
        if not self.presets:
            QMessageBox.warning(self, "No Presets", "No preset files found in the 'presets' directory.")
            return
        
        selected_index = self.preset_combo.currentIndex()
        if selected_index == -1: # No preset selected, or list is empty
            return
            
        current_preset_name = self.presets[selected_index]
        tokens = load_preset_tokens(current_preset_name)
        
        if not tokens:
            QMessageBox.warning(self, "Preset empty", f"Selected preset '{current_preset_name}' is empty or could not be loaded.")
            return

        current_tokens_in_editor = self.current_tokens()
        if current_tokens_in_editor:
            confirm = QMessageBox.question(
                self,
                "Replace token list?",
                "This will replace your current tokens with the selected preset. Continue?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
        
        self.token_edit.setPlainText("\n".join(tokens))
        self.current_preset_name = current_preset_name
        self.current_preset_tokens = tokens
        self.update_warning_message()
        self.refresh_duplicate_notice()

    def show_help(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Regex & Tokens Help")
        dialog.resize(640, 420)
        layout = QVBoxLayout(dialog)
        text = QTextBrowser()
        text.setHtml(HELP_TEXT)
        text.setOpenExternalLinks(True)
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def apply_tokens(self, tokens: List[str]) -> None:
        stored_tokens = list(tokens)
        self.config.tokens = stored_tokens
        if stored_tokens:
            self.config.regex = build_regex(stored_tokens)
        else:
            self.config.regex = DEFAULT_PATTERN
        self.config.save()
        self._config_updated = True


class ConflictResolutionDialog(QDialog):
    def __init__(
        self,
        candidates: List[RenameCandidate],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Resolve Multi-Conflicts")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Conflicting items:"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout(container)
        self.editors: List[tuple[RenameCandidate, QLineEdit]] = []
        for idx, cand in enumerate(candidates, start=1):
            group = QGroupBox(f"Item {idx}")
            group_layout = QVBoxLayout(group)
            group_layout.addWidget(
                QLabel(f"Original: {cand.original_relative_path or cand.path}")
            )
            edit = QLineEdit(cand.new_name)
            group_layout.addWidget(QLabel("Target name:"))
            group_layout.addWidget(edit)
            container_layout.addWidget(group)
            self.editors.append((cand, edit))
        container_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def names(self) -> List[tuple[RenameCandidate, str]]:
        return [(cand, edit.text()) for cand, edit in self.editors]


def resolve_conflict(self: MainWindow) -> None:
    if not self.row_index_map:
        return
    rows = self.table.selectionModel().selectedRows()
    if not rows:
        QMessageBox.information(
            self,
            "Resolve Multi-Conflicts",
            "Select a conflicting row first.",
        )
        return
    row = rows[0].row()
    if row >= len(self.row_index_map):
        return
    cand = self.candidates[self.row_index_map[row]]
    if not cand.message.startswith("Multiple items"):
        QMessageBox.information(
            self,
            "Resolve Multi-Conflicts",
            "This row is not part of a multi-item conflict.",
        )
        return
    target_norm = _normalize_path_for_gui(cand.new_path)
    collisions = [
        other
        for other in self.candidates
        if _normalize_path_for_gui(other.new_path) == target_norm
    ]
    if len(collisions) < 2:
        QMessageBox.information(
            self,
            "Resolve Multi-Conflicts",
            "Could not locate multiple conflicting items for this entry.",
        )
        return
    dialog = ConflictResolutionDialog(collisions, self)
    if dialog.exec() == QDialog.Accepted:
        # Confirm the rename operation
        confirm = QMessageBox.question(
            self,
            "Confirm Rename",
            f"This will immediately rename {len(collisions)} conflicting items.\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        # Validate and rename each file
        success_count = 0
        failed = []

        for candidate, new_name in dialog.names():
            new_name = new_name.strip()

            # Validate the new name
            if not new_name:
                failed.append(f"{candidate.path.name}: Name cannot be empty")
                continue

            if any(sep in new_name for sep in ("/", "\\")):
                failed.append(f"{candidate.path.name}: Name cannot contain path separators")
                continue

            # Actually rename the file
            if self.apply_rename_on_disk(candidate, new_name):
                success_count += 1
            else:
                failed.append(f"{candidate.path.name}: Rename failed")

        # Show results
        if failed:
            QMessageBox.warning(
                self,
                "Conflicts Partially Resolved",
                f"Successfully renamed {success_count} items.\n\n"
                f"Failed:\n" + "\n".join(failed) +
                f"\n\nNote: You'll need to rescan before applying additional changes.",
            )
        else:
            QMessageBox.information(
                self,
                "Conflicts Resolved",
                f"Successfully renamed all {success_count} items.\n\n"
                f"Note: You'll need to rescan before applying additional changes.",
            )


MainWindow.resolve_conflict = resolve_conflict

def main() -> None:
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
    except ConfigLoadError as exc:
        QMessageBox.critical(
            None,
            "Configuration Error",
            (
                f"{exc}\n\n"
                f"Fix the JSON in '{exc.path}' or delete the file to regenerate "
                "the default settings, then relaunch the app."
            ),
        )
        return
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
