"""
LaTeX Export Setup Dialog — Material Characterization.

Pre-export dialog that mirrors the DUT LaTeXExportDialog:
detects the LaTeX compiler in a background thread, lets the user
browse for the output path (and optionally select a compiler
manually), and opens the PDF preview dialog when ready.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QTextEdit, QGroupBox, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.export.permittivity_exporter import (
    _find_latex_compiler, _test_latex_compiler,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #


class _LaTeXCheckerThread(QThread):
    """Background thread — detects and tests the LaTeX compiler."""

    finished = Signal(bool, str, str)   # success, compiler_info_str, error_msg

    def run(self):
        try:
            compiler_name, compiler_path = _find_latex_compiler()
            if compiler_name is None:
                self.finished.emit(False, "", "No LaTeX compiler found")
                return
            if _test_latex_compiler(compiler_path):
                self.finished.emit(True, f"{compiler_name} ({compiler_path})", "")
            else:
                self.finished.emit(
                    False,
                    f"{compiler_name} (non-functional)",
                    "Compiler found but not working properly",
                )
        except Exception as exc:
            self.finished.emit(False, "", f"Error checking LaTeX: {exc}")


# --------------------------------------------------------------------------- #

class PermittivityLatexSetupDialog(QDialog):
    """
    Setup dialog for characterization PDF export.

    Shows compiler status, lets the user pick an output path
    (and optionally browse for the compiler manually), then
    opens PermittivityPdfPreviewDialog on Accept.
    """

    def __init__(self, parent=None, default_filename="characterization_report"):
        super().__init__(parent)
        self.setWindowTitle("Export PDF Report — Setup")
        self.setModal(True)
        self.setMinimumSize(500, 360)

        self.latex_available = False
        self.output_path = ""
        self.default_filename = default_filename
        self.manual_compiler_path = None
        self.checker_thread = None

        self._setup_ui()
        self._start_latex_check()

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._setup_compiler_group(layout)
        self._setup_path_group(layout)
        self._setup_options_group(layout)
        self._setup_buttons(layout)
        layout.addStretch()

    def _setup_compiler_group(self, parent_layout):
        group = QGroupBox("LaTeX Compiler")
        layout = QVBoxLayout(group)

        self.status_label = QLabel("Checking installation…")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)

        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(100)
        self.details_text.setReadOnly(True)
        self.details_text.setText("Scanning system for LaTeX compilers…")
        layout.addWidget(self.details_text)

        self.download_label = QLabel()
        self.download_label.setOpenExternalLinks(True)
        self.download_label.setVisible(False)
        layout.addWidget(self.download_label)

        manual_row = QHBoxLayout()
        manual_row.addWidget(QLabel("Manual compiler:"))
        self.manual_browse_btn = QPushButton("Browse…")
        self.manual_browse_btn.clicked.connect(self._browse_manual_compiler)
        manual_row.addWidget(self.manual_browse_btn)
        manual_row.addStretch()
        layout.addLayout(manual_row)

        parent_layout.addWidget(group)

    def _setup_path_group(self, parent_layout):
        group = QGroupBox("Output Path")
        layout = QVBoxLayout(group)
        layout.addSpacing(10)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select output file…")
        self.path_edit.setReadOnly(True)
        path_row.addWidget(self.path_edit, alignment=Qt.AlignVCenter)

        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.clicked.connect(self._browse_output_path)
        path_row.addWidget(self.browse_btn, alignment=Qt.AlignVCenter)
        layout.addLayout(path_row)

        self.path_hint = QLabel("The PDF will be saved to the selected location.")
        self.path_hint.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(self.path_hint)

        parent_layout.addWidget(group)

    def _setup_options_group(self, parent_layout):
        group = QGroupBox("Report Options")
        layout = QVBoxLayout(group)
        self.include_steps_chk = QCheckBox(
            "Include calibration standard measurements (S11 chart + table per step)"
        )
        self.include_steps_chk.setChecked(False)
        layout.addWidget(self.include_steps_chk)
        self.include_notes_chk = QCheckBox("Include notes / comments section")
        self.include_notes_chk.setChecked(False)
        layout.addWidget(self.include_notes_chk)
        parent_layout.addWidget(group)

    def _setup_buttons(self, parent_layout):
        parent_layout.addSpacing(15)
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._open_preview)
        self.apply_btn.setStyleSheet("""
            QPushButton:enabled {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        btn_row.addWidget(self.apply_btn)
        parent_layout.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    # Compiler check
    # ------------------------------------------------------------------ #

    def _start_latex_check(self):
        self.checker_thread = _LaTeXCheckerThread()
        self.checker_thread.finished.connect(self._on_check_finished)
        self.checker_thread.start()

    def _on_check_finished(self, success, compiler_info, error_msg):
        if success:
            self.latex_available = True
            self.status_label.setText("LaTeX Compiler: Available")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
            self.details_text.setText(f"Found working compiler:\n{compiler_info}")
        else:
            self.latex_available = False
            self.status_label.setText("LaTeX Compiler: Not Available")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            self.details_text.setText(
                f"No LaTeX compiler found on your system.\n"
                f"A LaTeX distribution is required to generate PDF reports.\n\n"
                f"Download MiKTeX from: https://miktex.org/download"
            )
            self.download_label.setText(
                '<a href="https://miktex.org/download" style="color: blue; '
                'text-decoration: underline;">Download MiKTeX (recommended)</a>'
            )
            self.download_label.setVisible(True)

        self._refresh_apply_button()

    def _browse_manual_compiler(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select LaTeX Compiler Executable", "",
            "Executable Files (*.exe);;All Files (*.*)",
        )
        if not filename:
            return
        if _test_latex_compiler(filename):
            self.manual_compiler_path = filename
            self.latex_available = True
            self.status_label.setText("LaTeX Compiler: Manual Selection")
            self.status_label.setStyleSheet("font-weight: bold; color: blue;")
            self.details_text.setText(
                f"Manually selected compiler:\n{filename}\n\nCompiler test: PASSED"
            )
        else:
            self.manual_compiler_path = None
            self.status_label.setText("LaTeX Compiler: Invalid Selection")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            self.details_text.setText(
                f"Selected file is not a working LaTeX compiler:\n{filename}\n\n"
                "Compiler test: FAILED"
            )
        self._refresh_apply_button()

    # ------------------------------------------------------------------ #
    # Output path
    # ------------------------------------------------------------------ #

    def _browse_output_path(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report",
            f"{self.default_filename}.pdf",
            "PDF Files (*.pdf)",
        )
        if filename:
            self.output_path = str(Path(filename).with_suffix(".pdf"))
            self.path_edit.setText(self.output_path)
            self.path_hint.setText(f"Output: {self.output_path}")
        self._refresh_apply_button()

    # ------------------------------------------------------------------ #

    def _refresh_apply_button(self):
        can = self.latex_available and bool(self.output_path)
        self.apply_btn.setEnabled(can)
        self.apply_btn.setText("Apply" if can else "Apply (pending…)")

    def get_compiler_path(self):
        if self.manual_compiler_path:
            return self.manual_compiler_path
        _, path = _find_latex_compiler()
        return path

    # ------------------------------------------------------------------ #
    # Open preview
    # ------------------------------------------------------------------ #

    def _open_preview(self):
        if not self.output_path:
            QMessageBox.warning(self, "Missing Path", "Please select an output path first.")
            return

        main_window = self.parent()
        if main_window is None:
            QMessageBox.critical(self, "Error", "Parent window not found.")
            return

        cal = getattr(getattr(main_window, "wizard_window", None), "perm_calibration", None)
        dut = cal.get_measurement("dut") if cal is not None else None
        if dut is None:
            QMessageBox.critical(self, "Error", "No S11 data available.")
            return

        result = getattr(main_window, "_result", None)
        if result is None:
            QMessageBox.critical(self, "Error", "No permittivity result available.")
            return

        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.export.pdf_preview_dialog import (
            PermittivityPdfPreviewDialog,
        )

        preview = PermittivityPdfPreviewDialog(
            parent=main_window,
            freqs=np.asarray(dut[0], dtype=float),
            s11_data=np.asarray(dut[1], dtype=complex),
            eps_selected=result.eps_selected,
            sample_name=main_window._sample_name(),
            output_path=self.output_path,
            wizard_window=main_window.wizard_window,
            include_steps=self.include_steps_chk.isChecked(),
            include_notes=self.include_notes_chk.isChecked(),
        )
        preview.exec()
        self.reject()

    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        if self.checker_thread and self.checker_thread.isRunning():
            self.checker_thread.terminate()
            self.checker_thread.wait()
        event.accept()
