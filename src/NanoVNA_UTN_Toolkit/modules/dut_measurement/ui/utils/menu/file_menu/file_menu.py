from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys
import os
import shutil
import re
import numpy as np
import skrf as rf

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtGui import QColor

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

get_calibration_path = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils", "get_calibration_path")

show_touchstone_format_dialog = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.file_menu.export_touchstone.export_touchstone", "show_touchstone_format_dialog")

open_error_visualizer = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.file_menu.export_errors.error_visualizer", "open_error_visualizer")

# ------------------------------------------------------------------------------------------------------------------------- #

def import_touchstone_data_calibration(self):
    from PySide6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
    import os

    files, _ = QFileDialog.getOpenFileNames(
        self,
        self.file_menu_select_cal_files_title,
        "",
        self.file_menu_select_cal_files_filter
    )

    if not files:
        QMessageBox.warning(self, self.file_menu_no_files_title, self.file_menu_no_files_message)
        return

    required_names = ["open", "short", "load", "match", "thru"]
    filenames = [os.path.basename(f).lower() for f in files]
    found = {name: any(name in f for f in filenames) for name in required_names}
    has_load_or_match = found["load"] or found["match"]

    missing = []
    if not found["open"]:
        missing.append("open")
    if not found["short"]:
        missing.append("short")
    if not has_load_or_match:
        missing.append("load or match")
    if not found["thru"]:
        missing.append("thru")

    if missing:
        QMessageBox.warning(self, self.file_menu_missing_files_title, f"{self.file_menu_missing_files_prefix}{', '.join(missing)}")
        return

    if len(files) != 4:
        QMessageBox.warning(self, self.file_menu_invalid_selection_title, self.file_menu_invalid_selection_message)
        return

    QMessageBox.information(self, self.file_menu_success_title, self.file_menu_success_message)
    print("Selected calibration files:")
    for f in files:
        print(f)

    # --- TRUNCADO A 101 PUNTOS
    truncated_files = []
    max_points = 101

    for f in files:
        try:
            ntw = rf.Network(f)
            if len(ntw.f) > max_points:
                idx = np.linspace(0, len(ntw.f) - 1, max_points, dtype=int)
                f_trunc = ntw.f[idx]
                s_trunc = ntw.s[idx]
                z0_trunc = ntw.z0[idx]
                ntw_trunc = rf.Network(f=f_trunc, s=s_trunc, z0=z0_trunc)

                base, ext = os.path.splitext(f)
                new_path = f"{base}_trunc{ext}"
                ntw_trunc.write_touchstone(new_path)
                truncated_files.append(new_path)
                print(f"Truncated {os.path.basename(f)} → {os.path.basename(new_path)} ({max_points} points)")
            else:
                truncated_files.append(f)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error processing {f}:\n{str(e)}")
            return

    # "Select Method"
    dialog = QDialog(self)
    dialog.setWindowTitle(self.file_menu_select_method_title)

    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(15)

    label = QLabel(self.file_menu_select_method_label, dialog)
    main_layout.addWidget(label)

    self.select_method = QComboBox()
    self.select_method.setStyleSheet("""
        QComboBox {
            background-color: #3b3b3b;
            color: white;
            border: 2px solid white;
            border-radius: 6px;
            padding: 8px;
            font-size: 14px;
            min-width: 200px;
        }
        QComboBox:hover {
            background-color: #4d4d4d;
        }
        QComboBox::drop-down {
            width: 0px;
            border: none;
            background: transparent;
        }
        QComboBox::down-arrow {
            image: none;
            width: 0px;
            height: 0px;
        }
        QComboBox QAbstractItemView {
            background-color: #3b3b3b;
            color: white;
            selection-background-color: #4d4d4d;
            selection-color: white;
            border: 1px solid white;
        }
        QComboBox:focus {
            background-color: #4d4d4d;
        }
        QComboBox::placeholder {
            color: #cccccc;
        }
    """)

    self.select_method.setEditable(False)

    # Placeholder
    self.select_method.addItem("Select Method")
    item = self.select_method.model().item(0)
    item.setEnabled(False)
    placeholder_color = QColor(120, 120, 120)
    item.setForeground(placeholder_color)

    methods = [
        "OSM (Open - Short - Match)",
        "Thru Normalization",
        "1-Port+N",
        "Enhanced-Response"
    ]
    self.select_method.addItems(methods)

    main_layout.addWidget(self.select_method)

    button_layout = QHBoxLayout()
    button_layout.setSpacing(10) 

    cancel_button = QPushButton("Cancel", dialog)
    cancel_button.clicked.connect(dialog.reject)
    button_layout.addWidget(cancel_button)

    calibrate_button = QPushButton("Calibrate", dialog)
    calibrate_button.clicked.connect(lambda: self.start_calibration(truncated_files, self.select_method.currentText(), dialog))
    button_layout.addWidget(calibrate_button)

    main_layout.addLayout(button_layout)

    dialog.exec()

def import_touchstone_data_dut(self):
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    import os

    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "Select DUT Touchstone File",
        "",
        "Touchstone Files (*.s2p);;All Files (*)"
    )

    if not file_path:
        QMessageBox.warning(self, "No File Selected", "Please select a Touchstone .s2p file.")
        return

    files = file_path

    QMessageBox.information(self, "File Loaded", "Touchstone file loaded successfully!")
    print("Selected DUT file:", file_path)

    # Load configuration for calibration settings
    settings_calibration = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    settings_calibration.setValue("Calibration/isImportDut", True)

    """
    if self.vna_device:
        graphics_window = NanoVNAGraphics(vna_device=self.vna_device, dut=files)
    else:
        graphics_window = NanoVNAGraphics()

    graphics_window.show()
    """
    self.close()

def export_touchstone_data(self):
    """
    Export sweep data to Touchstone format.
    
    Shows a dialog to choose between S1P and S2P formats.
    """

    # Show format selection dialog
    format_choice = show_touchstone_format_dialog(self)
    if format_choice is None:
        return False  # User cancelled
    
    device_name = None
    if self.vna_device:
        device_name = getattr(self.vna_device, 'name', type(self.vna_device).__name__)
    
    if format_choice == "s1p":
        # Export S1P format (S11 only)
        return self.touchstone_exporter.export_to_s1p(
            freqs=self.freqs,
            s11_data=self.s11,
            device_name=device_name
        )
    else:
        # Export S2P format (S11 and S21)
        return self.touchstone_exporter.export_to_s2p(
            freqs=self.freqs,
            s11_data=self.s11,
            s21_data=self.s21,
            device_name=device_name
        )
    
def export_errors(self):
    """
    Export errors.

    """

    open_error_visualizer(self)

def export_latex_pdf(self):
    """
    Export a PDF using LaTeX with a title page and structured sections.
    
    This method now uses the new dialog-based export with LaTeX verification.
    """
    device_name = None
    if self.vna_device:
        device_name = getattr(self.vna_device, 'name', type(self.vna_device).__name__)
    
    return self.latex_exporter.export_to_pdf_with_dialog(
        freqs=self.freqs,
        s11_data=self.s11,
        s21_data=self.s21,
        measurement_name=device_name
    )