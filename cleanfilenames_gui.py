"""PySide6 GUI for the cleanfilenames tool."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

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
)

try:  # pragma: no cover
    from .config_manager import (  # type: ignore
        AppConfig,
        DEFAULT_PATTERN,
        DEFAULT_TOKENS,
        build_regex,
    )
except ImportError:  # pragma: no cover
    from config_manager import AppConfig, DEFAULT_PATTERN, DEFAULT_TOKENS, build_regex

PRESETS = {
    "Full (default)": DEFAULT_TOKENS,
    "Minimal (USA/EU/JP)": ["USA", "Europe", "JP", "PAL", "World"],
}

HELP_TEXT = """
<h3>Tokens &amp; Regex</h3>
<p>Each token represents an entire region string that appears inside parentheses.
For example, if your files are named:</p>
<ul>
  <li>Game 1 (USA,EU,JP).zip</li>
  <li>Game 2 (En,Ja,Fr,De,Es,It,Pt,Ko,Ru,Ar).zip</li>
</ul>
<p>Then you need two tokens:</p>
<pre>USA,EU,JP
En,Ja,Fr,De,Es,It,Pt,Ko,Ru,Ar</pre>
<p>When the tool rebuilds the regex, those tokens become part of the expression:</p>
<pre>\\s*\\((?:USA,EU,JP|En,Ja,Fr,De,Es,It,Pt,Ko,Ru,Ar|...)\\)\\s*</pre>
<p>Any parentheses containing one of those tokens (with optional spaces) will be removed.</p>
<h4>Customize By</h4>
<ul>
  <li>Choosing a preset to load a known token list.</li>
  <li>Editing tokens (one per line). The regex updates automatically.</li>
  <li>Pasting a custom regex (advanced users) to switch to “Custom” mode.</li>
  <li>Loading or saving regex text files for reuse.</li>
</ul>
<p>Tokens may include regex syntax if you intentionally want pattern matching (e.g., <code>v\\d+\\.\\d+</code>),
but remember that the entire token is inserted into the regex as-is.</p>
<p>A helpful regex cheat sheet can be found here:
<a href="https://www.rexegg.com/regex-quickstart.php">https://www.rexegg.com/regex-quickstart.php</a></p>
"""

if __package__:
    from .cleanfilenames_core import apply_candidates, collect_candidates, summarize
else:  # Allow running as a stand-alone script
    sys.path.append(str(Path(__file__).resolve().parent))
    from cleanfilenames_core import apply_candidates, collect_candidates, summarize


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Clean Filenames")
        self.resize(1100, 650)
        self.candidates = []
        self.current_path: Path | None = None
        self.row_index_map: List[int] = []

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
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.on_settings)
        path_layout.addWidget(settings_btn)
        main_layout.addLayout(path_layout)

        # Dry run + action buttons
        controls_layout = QHBoxLayout()
        self.dry_run_checkbox = QCheckBox("Dry run (no changes)")
        self.dry_run_checkbox.setChecked(True)
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
        controls_layout.addLayout(btn_layout)
        main_layout.addLayout(controls_layout)

        # Summary label
        self.summary_label = QLabel("No folder selected.")
        main_layout.addWidget(self.summary_label)

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
            self.candidates = collect_candidates(target_path, config=self.config)
            self.current_path = target_path
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "Folder not found",
                f"The path '{path_text}' does not exist.",
            )
            self.candidates = []
            self.update_table()
            return

        if not self.candidates:
            self.summary_label.setText("No changes needed.")
            self.run_btn.setEnabled(False)
            self.update_table()
            return

        summary = summarize(self.candidates)
        self.summary_label.setText(
            f"Found {summary['total']} candidates "
            f"({summary['files']} files, {summary['directories']} directories)."
        )
        self.run_btn.setEnabled(True)
        self.update_table()

    def on_apply(self) -> None:
        if not self.candidates:
            return
        confirm = QMessageBox.question(
            self,
            "Confirm renames",
            "Apply all pending renames?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            dry_run = self.dry_run_checkbox.isChecked()
            if not dry_run:
                refresh_needed = any(c.status != "pending" for c in self.candidates)
                if refresh_needed:
                    if not self.current_path:
                        QMessageBox.warning(
                            self,
                            "No scan data",
                            "Please scan a folder before running renames.",
                        )
                        return
                    try:
                        self.candidates = collect_candidates(
                            self.current_path, config=self.config
                        )
                    except FileNotFoundError:
                        QMessageBox.critical(
                            self,
                            "Folder not found",
                            f"The path '{self.current_path}' no longer exists.",
                        )
                        return
            apply_candidates(
                self.candidates,
                dry_run=dry_run,
                stop_on_error=self.config.stop_on_error,
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
                details = "\n".join(
                    f"- {c.path} -> {c.new_path}: {c.message}"
                    for c in self.candidates
                    if c.status == "error"
                )
                QMessageBox.warning(self, "Dry run finished", message + "\n\n" + details)
            else:
                QMessageBox.information(self, "Dry run finished", message)
            return

        message = (
            f"Completed {summary['completed']} renames "
            f"({summary['errors']} errors)."
        )
        if summary["errors"]:
            details = "\n".join(
                f"- {c.path} -> {c.new_path}: {c.message}"
                for c in self.candidates
                if c.status == "error"
            )
            QMessageBox.warning(self, "Finished with errors", message + "\n\n" + details)
        else:
            QMessageBox.information(self, "Finished", message)

    def on_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.Accepted:
            self.config = dialog.result_config()
            self.config.save()
            QMessageBox.information(
                self,
                "Settings saved",
                "Configuration updated. Please rescan to see new results.",
            )

    def update_table(self) -> None:
        MAX_ROWS = 5000
        total = len(self.candidates)
        truncated = total > MAX_ROWS
        display_pairs = list(enumerate(self.candidates[:MAX_ROWS]))
        self.row_index_map = [idx for idx, _ in display_pairs]

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        for idx, cand in display_pairs:
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
            elif cand.status.startswith("done"):
                status_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 3, status_item)
            self.table.setItem(row, 4, QTableWidgetItem(cand.message))

        if truncated:
            row = self.table.rowCount()
            self.table.insertRow(row)
            note = QTableWidgetItem(f"... {total - MAX_ROWS} more rows not shown ...")
            note.setForeground(Qt.gray)
            note.setFlags(Qt.NoItemFlags)
            self.table.setItem(row, 1, note)

        self.table.setUpdatesEnabled(True)

        if not self.candidates:
            self.summary_label.setText("No changes to be made.")
            self.run_btn.setEnabled(False)
        else:
            if truncated:
                self.summary_label.setText(
                    f"Showing first {MAX_ROWS} of {total} candidates (use CSV export for full list)."
                )
            else:
                self.summary_label.setText(self.summary_label.text())

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
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == copy_action:
            self.copy_selected_rows()
        elif action == export_action:
            self.export_csv()

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
            candidate_indices = list(range(len(self.candidates)))
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


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.tokens = list(config.tokens or DEFAULT_TOKENS)

        layout = QVBoxLayout(self)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        for name in PRESETS.keys():
            self.preset_combo.addItem(name)
        self.preset_combo.addItem("Custom")
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo)

        tokens_btn = QPushButton("Edit Tokens…")
        tokens_btn.clicked.connect(self.edit_tokens)
        preset_layout.addWidget(tokens_btn)

        help_btn = QPushButton("Help…")
        help_btn.clicked.connect(self.show_help)
        preset_layout.addWidget(help_btn)

        load_btn = QPushButton("Load Pattern…")
        load_btn.clicked.connect(self.load_pattern)
        preset_layout.addWidget(load_btn)

        save_btn = QPushButton("Save Pattern…")
        save_btn.clicked.connect(self.save_pattern)
        preset_layout.addWidget(save_btn)

        layout.addLayout(preset_layout)

        layout.addWidget(QLabel("Region regex:"))
        self.regex_edit = QPlainTextEdit()
        self.regex_edit.setPlainText(config.regex)
        self.regex_edit.setMinimumHeight(120)
        self.regex_edit.textChanged.connect(self.set_preset_by_regex)
        layout.addWidget(self.regex_edit)

        self.rename_dirs_cb = QCheckBox("Rename directories")
        self.rename_dirs_cb.setChecked(config.rename_directories)

        self.rename_root_cb = QCheckBox("Rename root folder")
        self.rename_root_cb.setChecked(config.rename_root)

        self.stop_on_error_cb = QCheckBox("Stop on first error")
        self.stop_on_error_cb.setChecked(config.stop_on_error)

        layout.addWidget(self.rename_dirs_cb)
        layout.addWidget(self.rename_root_cb)
        layout.addWidget(self.stop_on_error_cb)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.set_preset_by_regex()

    def result_config(self) -> AppConfig:
        regex = self.current_regex() or DEFAULT_PATTERN
        tokens_to_store = None
        if self.tokens and regex == build_regex(self.tokens):
            tokens_to_store = list(self.tokens)
        return AppConfig(
            regex=regex,
            rename_directories=self.rename_dirs_cb.isChecked(),
            rename_root=self.rename_root_cb.isChecked(),
            stop_on_error=self.stop_on_error_cb.isChecked(),
            tokens=tokens_to_store,
        )

    def current_regex(self) -> str:
        return self.regex_edit.toPlainText().strip()

    def on_preset_changed(self, name: str) -> None:
        if name in PRESETS:
            self.tokens = list(PRESETS[name])
            self._set_regex_from_tokens()

    def _set_regex_from_tokens(self) -> None:
        pattern = build_regex(self.tokens)
        self.regex_edit.blockSignals(True)
        self.regex_edit.setPlainText(pattern)
        self.regex_edit.blockSignals(False)

    def set_preset_by_regex(self) -> None:
        regex = self.current_regex()
        for name, tokens in PRESETS.items():
            if regex == build_regex(tokens):
                self._set_preset(name)
                self.tokens = list(tokens)
                return
        self._set_preset("Custom")

    def _set_preset(self, name: str) -> None:
        idx = self.preset_combo.findText(name)
        if idx >= 0 and self.preset_combo.currentIndex() != idx:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(idx)
            self.preset_combo.blockSignals(False)

    def edit_tokens(self) -> None:
        dialog = TokensDialog(self.tokens, self)
        if dialog.exec() == QDialog.Accepted:
            new_tokens = dialog.tokens()
            if new_tokens:
                self.tokens = new_tokens
                self._set_regex_from_tokens()
                self._set_preset("Custom")

    def load_pattern(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Pattern", str(Path.home()), "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            text = Path(path).read_text().strip()
        except OSError as exc:
            QMessageBox.warning(self, "Load failed", str(exc))
            return
        if text:
            self.regex_edit.blockSignals(True)
            self.regex_edit.setPlainText(text)
            self.regex_edit.blockSignals(False)
            self.tokens = []
            self._set_preset("Custom")

    def save_pattern(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Pattern", str(Path.home() / "pattern.txt"), "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            Path(path).write_text(self.current_regex() or DEFAULT_PATTERN)
        except OSError as exc:
            QMessageBox.warning(self, "Save failed", str(exc))

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


class TokensDialog(QDialog):
    def __init__(self, tokens: List[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Tokens")
        layout = QVBoxLayout(self)
        self.text = QPlainTextEdit("\n".join(tokens))
        self.text.setMinimumHeight(200)
        layout.addWidget(QLabel("One token per line (raw regex segments)."))
        layout.addWidget(self.text)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def tokens(self) -> List[str]:
        return [line.strip() for line in self.text.toPlainText().splitlines() if line.strip()]


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
