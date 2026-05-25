"""
LaTeX Export Dialog for NanoVNA measurement data.

This module provides a pre-export dialog that checks LaTeX installation,
allows path selection, and validates the setup before proceeding with PDF export.
"""

import os
import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QFileDialog, QTextEdit, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap

# Import the LaTeX detection functions
from NanoVNA_UTN_Toolkit.modules.dut_measurement.exporters.latex_exporter import _find_latex_compiler, _test_latex_compiler

# Set up logging
logger = logging.getLogger(__name__)

try:
    from NanoVNA_UTN_Toolkit.shared.resources.json_resource_loader import JsonResourceLoader
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

class LaTeXCheckerThread(QThread):
    """
    Background thread to check LaTeX installation without blocking the UI.
    """
    finished = Signal(bool, str, str)  # success, compiler_info, error_message
    
    def run(self):
        """Run the LaTeX detection in background."""
        try:
            logger.info("Starting LaTeX compiler detection")
            compiler_name, compiler_path = _find_latex_compiler()
            
            if compiler_name is None:
                logger.warning("No LaTeX compiler found on system")
                self.finished.emit(False, "", "No LaTeX compiler found")
                return
            
            logger.info(f"Found LaTeX compiler: {compiler_name} at {compiler_path}")
            
            # Test the compiler
            logger.info("Testing LaTeX compiler functionality")
            if _test_latex_compiler(compiler_path):
                logger.info("LaTeX compiler test successful")
                compiler_info = f"{compiler_name} ({compiler_path})"
                self.finished.emit(True, compiler_info, "")
            else:
                logger.error(f"LaTeX compiler test failed for {compiler_name}")
                self.finished.emit(False, f"{compiler_name} (non-functional)", 
                                 "Compiler found but not working properly")
                
        except Exception as e:
            logger.error(f"Error during LaTeX detection: {str(e)}")
            self.finished.emit(False, "", f"Error checking LaTeX: {str(e)}")


class LaTeXExportDialog(QDialog):
    """
    Dialog window for LaTeX export preparation.
    
    This dialog:
    - Checks for LaTeX compiler availability
    - Allows output path selection
    - Validates setup before proceeding
    - Provides download link if no compiler found
    """
    
    def __init__(self, measurement_self = None, parent=None, default_filename="nanovna_report"):
        """
        Initialize the LaTeX export dialog.
        
        Args:
            parent: Parent widget
            default_filename: Default filename for the export
        """
        super().__init__(parent)

# ------------------------------------------------------------------------------------------------------------------- #
# Load JSON 
# ------------------------------------------------------------------------------------------------------------------- #

        current_lang = "en"

        self.resourceLoader = JsonResourceLoader(
            self_window = self, 
            module = "dut_measurement", 
            lang = current_lang, 
            json_resource = "dut_measurement_features.json"
        )

        self.resourceLoader.load_pdf_export_resources()  

# ------------------------------------------------------------------------------------------------------------------- #

        self.measurement_self = measurement_self

        self.setWindowTitle(f"{self.pdf_export_window_title}")
        self.setModal(True)
        self.setMinimumSize(500, 360)
        
        self.latex_available = False
        self.output_path = ""
        self.default_filename = default_filename
        self.checker_thread = None
        self.manual_compiler_path = None  # Store manually selected compiler

        
        logger.info("Initializing LaTeX Export Dialog")
        self._setup_ui()
        self._start_latex_check()
 
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # LaTeX Status Group
        self._setup_latex_status_group(layout)
        
        # Output Path Group
        self._setup_output_path_group(layout)
        
        # Buttons
        self._setup_buttons(layout)
        
        layout.addStretch()
    
    def _setup_latex_status_group(self, parent_layout):
        """Set up the LaTeX status group box."""
        group = QGroupBox(f"{self.pdf_export_compiler_group_title}")
        layout = QVBoxLayout(group)
        
        # Status label
        self.status_label = QLabel(f"{self.pdf_export_checking_installation}")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(100)
        self.details_text.setReadOnly(True)
        self.details_text.setText(f"{self.pdf_export_scanning_system}")
        layout.addWidget(self.details_text)
        
        # Download link (initially hidden)
        self.download_label = QLabel()
        self.download_label.setOpenExternalLinks(True)
        self.download_label.setVisible(False)
        layout.addWidget(self.download_label)
        
        # Manual compiler selection
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel(f"{self.pdf_export_manual_select_compiler}"))
        
        self.manual_browse_button = QPushButton(f"{self.pdf_export_browse_compiler_button}")
        self.manual_browse_button.clicked.connect(self._browse_manual_compiler)
        manual_layout.addWidget(self.manual_browse_button)
        manual_layout.addStretch()
        
        layout.addLayout(manual_layout)
        
        parent_layout.addWidget(group)
    
    def _setup_output_path_group(self, parent_layout):
        """Set up the output path selection group."""
        group = QGroupBox(f"{self.pdf_export_output_group_title}")
        layout = QVBoxLayout(group)

        # Path selection
        path_layout = QHBoxLayout()

        layout.addSpacing(10)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(f"{self.pdf_export_select_output_placeholder}")
        self.path_edit.setReadOnly(True)

        path_layout.addWidget(self.path_edit, alignment=Qt.AlignVCenter)

        self.browse_button = QPushButton(f"{self.pdf_export_browse_button}")
        self.browse_button.clicked.connect(self._browse_output_path)
        path_layout.addWidget(self.browse_button, alignment=Qt.AlignVCenter)
        
        layout.addLayout(path_layout)
        
        # Path info
        self.path_info_label = QLabel(f"{self.pdf_export_output_hint}")
        self.path_info_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(self.path_info_label)
        
        parent_layout.addWidget(group)
    
    def _setup_buttons(self, parent_layout):

        parent_layout.addSpacing(15)

        """Set up the dialog buttons."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton(f"{self.pdf_export_cancel_button}")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.export_button = QPushButton(f"{self.pdf_export_export_button}")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.open_preview_dialog)
        self.export_button.setStyleSheet("""
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
        button_layout.addWidget(self.export_button)
        
        parent_layout.addLayout(button_layout)
    
    def _start_latex_check(self):
        """Start the background LaTeX check."""
        logger.info("Starting background LaTeX compiler check")
        self.checker_thread = LaTeXCheckerThread()
        self.checker_thread.finished.connect(self._on_latex_check_finished)
        self.checker_thread.start()
    
    def _on_latex_check_finished(self, success, compiler_info, error_message):
        """Handle the completion of LaTeX check."""
        logger.info(f"LaTeX check completed: success={success}")
        
        if success:
            self.latex_available = True
            self.status_label.setText("LaTeX Compiler: Available")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
            self.details_text.setText(f"{self.pdf_export_found_working_compiler}\n{compiler_info}")
            logger.info(f"LaTeX available: {compiler_info}")
        else:
            self.latex_available = False
            self.status_label.setText("LaTeX Compiler: Not Available")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            
            if "not found" in error_message.lower():
                self.details_text.setText(
                    "No LaTeX compiler found on your system.\n"
                    "A LaTeX distribution is required to generate PDF reports.\n\n"
                    "Download MiKTeX from: https://miktex.org/download"
                )
                self._show_download_link()
                logger.warning("No LaTeX compiler found, showing download link")
            else:
                self.details_text.setText(
                    f"LaTeX compiler issue: {error_message}\n\n"
                    "If you don't have LaTeX installed, download MiKTeX from:\n"
                    "https://miktex.org/download"
                )
                self._show_download_link()
                logger.error(f"LaTeX compiler error: {error_message}")
        
        self._update_export_button_state()
    
    def _show_download_link(self):
        """Show the MiKTeX download link."""
        self.download_label.setText(
            '<a href="https://miktex.org/download" style="color: blue; text-decoration: underline;">'
            'Download MiKTeX (recommended LaTeX distribution)</a>'
        )
        self.download_label.setVisible(True)
        logger.info("Displaying MiKTeX download link")
    
    def _browse_output_path(self):
        """Open file dialog to select output path."""
        logger.info("Opening file browser for output path selection")
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save LaTeX PDF Report",
            f"{self.default_filename}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if filename:
            self.output_path = str(Path(filename).with_suffix('.pdf'))
            self.path_edit.setText(self.output_path)
            self.path_info_label.setText(f"Output: {self.output_path}")
            logger.info(f"Output path selected: {self.output_path}")
        else:
            logger.info("Output path selection cancelled by user")
        
        self._update_export_button_state()
    
    def _browse_manual_compiler(self):
        """Open file dialog to manually select LaTeX compiler executable."""
        logger.info("Opening file browser for manual compiler selection")
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select LaTeX Compiler Executable",
            "",
            "Executable Files (*.exe);;All Files (*.*)"
        )
        
        if filename:
            logger.info(f"Manual compiler selected: {filename}")
            
            # Test the manually selected compiler
            if _test_latex_compiler(filename):
                self.manual_compiler_path = filename
                self.latex_available = True
                self.status_label.setText("LaTeX Compiler: Manual Selection")
                self.status_label.setStyleSheet("font-weight: bold; color: blue;")
                self.details_text.setText(f"Manually selected compiler:\n{filename}\n\nCompiler test: PASSED")
                logger.info(f"Manual compiler test successful: {filename}")
            else:
                self.manual_compiler_path = None
                self.status_label.setText("LaTeX Compiler: Invalid Selection")
                self.status_label.setStyleSheet("font-weight: bold; color: red;")
                self.details_text.setText(f"Selected file is not a working LaTeX compiler:\n{filename}\n\nCompiler test: FAILED")
                logger.warning(f"Manual compiler test failed: {filename}")
        else:
            logger.info("Manual compiler selection cancelled by user")
        
        self._update_export_button_state()
    
    def _update_export_button_state(self):
        """Update the export button enabled state based on conditions."""
        can_export = self.latex_available and bool(self.output_path)
        self.export_button.setEnabled(can_export)
        
        if can_export:
            self.export_button.setText("Export PDF")
            logger.debug("Export button enabled - all conditions met")
        else:
            reasons = []
            if not self.latex_available:
                reasons.append("LaTeX not available")
            if not self.output_path:
                reasons.append("no output path selected")
            
            reason_text = ", ".join(reasons)
            self.export_button.setText(f"{self.pdf_export_disabled_button} ({reason_text})")
            logger.debug(f"Export button disabled: {reason_text}")
    
    def get_output_path(self):
        """
        Get the selected output path.
        
        Returns:
            str: Path where to save the PDF, or empty string if not selected
        """
        return self.output_path
    
    def is_latex_available(self):
        """
        Check if LaTeX is available for export.
        
        Returns:
            bool: True if LaTeX is available and working
        """
        return self.latex_available
    
    def get_compiler_path(self):
        """
        Get the path to the selected LaTeX compiler.
        
        Returns:
            str: Path to the compiler executable, or None if using system default
        """
        if self.manual_compiler_path:
            return self.manual_compiler_path
        else:
            # Return the automatically detected compiler path
            compiler_name, compiler_path = _find_latex_compiler()
            return compiler_path
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        logger.info("LaTeX Export Dialog closing")
        if self.checker_thread and self.checker_thread.isRunning():
            logger.info("Terminating background LaTeX checker thread")
            self.checker_thread.terminate()
            self.checker_thread.wait()
        event.accept()

    def open_preview_dialog(self):
        """
        Open the Graph Preview Dialog and pass the selected output path and data.
        """
        if not self.output_path:
            QMessageBox.warning(self, "Missing Path", "Please select an output path before proceeding.")
            return

        # Import the GraphPreviewExportDialog
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.exporters.export.graph_preview_dialog import GraphPreviewExportDialog

        # Obtener los datos del parent
        parent = self.parent()
        if parent is None:
            QMessageBox.critical(self, "Error", "Parent widget not found. Cannot retrieve data.")
            return

        freqs = getattr(parent, "freqs", None)
        s11_data = getattr(parent, "s11", None)
        s21_data = getattr(parent, "s21", None)
        measurement_name = self.default_filename  # Nombre del archivo para guardar

        if freqs is None or s11_data is None or s21_data is None:
            QMessageBox.critical(self, "Error", "Required data (freqs, s11, s21) not found in parent.")
            return
            
        # Create and show the preview dialog
        preview_dialog = GraphPreviewExportDialog(
            parent=self,
            output_path=self.output_path,
            freqs=freqs,
            s11_data=s11_data,
            s21_data=s21_data,
            measurement_name=measurement_name
        )
        preview_dialog.exec()

        self.reject()