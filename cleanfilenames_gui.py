"""PySide6 GUI for the cleanfilenames tool."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
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
)

try:  # pragma: no cover
    from .config_manager import AppConfig, DEFAULT_PATTERN  # type: ignore
except ImportError:  # pragma: no cover
    from config_manager import AppConfig, DEFAULT_PATTERN

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
            ["Type", "Original Path", "New Path", "Status", "Message"]
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

        try:
            self.candidates = collect_candidates(Path(path_text), config=self.config)
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


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._config = config

        layout = QVBoxLayout(self)

        self.regex_edit = QPlainTextEdit()
        self.regex_edit.setPlainText(config.regex)
        self.regex_edit.setMinimumHeight(120)

        self.rename_dirs_cb = QCheckBox("Rename directories")
        self.rename_dirs_cb.setChecked(config.rename_directories)

        self.rename_root_cb = QCheckBox("Rename root folder")
        self.rename_root_cb.setChecked(config.rename_root)

        self.stop_on_error_cb = QCheckBox("Stop on first error")
        self.stop_on_error_cb.setChecked(config.stop_on_error)

        layout.addWidget(QLabel("Region regex:"))
        layout.addWidget(self.regex_edit)
        layout.addWidget(self.rename_dirs_cb)
        layout.addWidget(self.rename_root_cb)
        layout.addWidget(self.stop_on_error_cb)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_config(self) -> AppConfig:
        return AppConfig(
            regex=self.regex_edit.toPlainText().strip() or DEFAULT_PATTERN,
            rename_directories=self.rename_dirs_cb.isChecked(),
            rename_root=self.rename_root_cb.isChecked(),
            stop_on_error=self.stop_on_error_cb.isChecked(),
        )

    def update_table(self) -> None:
        self.table.setRowCount(0)
        for cand in self.candidates:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(cand.item_type))
            self.table.setItem(row, 1, QTableWidgetItem(str(cand.path)))
            self.table.setItem(row, 2, QTableWidgetItem(str(cand.new_path)))
            status_item = QTableWidgetItem(cand.status)
            if cand.status == "error":
                status_item.setForeground(Qt.red)
            elif cand.status == "done":
                status_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 3, status_item)
            self.table.setItem(row, 4, QTableWidgetItem(cand.message))

        if not self.candidates:
            self.summary_label.setText("No changes to be made.")
            self.run_btn.setEnabled(False)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
