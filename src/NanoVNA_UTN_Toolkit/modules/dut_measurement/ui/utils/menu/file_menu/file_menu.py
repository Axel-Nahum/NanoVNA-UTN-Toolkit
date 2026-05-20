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

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.calibration.calibration_path_utils import get_calibration_path
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.file_menu.export_touchstone.export_touchstone import show_touchstone_format_dialog
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------------- #

def import_touchstone_data_calibration(self):
    from PySide6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
    import os

    files, _ = QFileDialog.getOpenFileNames(
        self,
        "Select Calibration Files",
        "",
        "Touchstone Files (*.s1p *.s2p);;All Files (*)"
    )

    if not files:
        QMessageBox.warning(self, "No Files Selected", "Please select the 4 calibration files.")
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
        QMessageBox.warning(self, "Missing Files", f"The following calibration files are missing: {', '.join(missing)}")
        return

    if len(files) != 4:
        QMessageBox.warning(self, "Invalid Selection", "You must select exactly 4 calibration files.")
        return

    QMessageBox.information(self, "Success", "All calibration files selected successfully!")
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
    dialog.setWindowTitle("NanoVNA UTN Toolkit - Select Method")

    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(20, 20, 20, 20)
    main_layout.setSpacing(15)  

    label = QLabel("Select Method", dialog)
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
        "Normalization",
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

    # Export error 

    # Load configuration for calibration settings
    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    kit_ok = settings.value(f"Calibration/Kits", False, type=bool)
    no_calibration = settings.value(f"Calibration/NoCalibration", False, type=bool)

    method = settings.value(f"Calibration/Method", "Normalization")

    if not no_calibration and not kit_ok:

        if method == "OSM (Open - Short - Match)":
            src_folder = get_calibration_path(
                "modules/dut_measurement/calibration/osm_results/osm_errors",
                "modules/dut_measurement/calibration/osm_results/osm_errors",
                Path(__file__).resolve()
            )

        elif method == "Normalization":
            src_folder = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results/normalization_errors",
                "modules/dut_measurement/calibration/thru_results/normalization_errors",
                Path(__file__).resolve()
            )

        elif method == "1-Port+N":
            src_folder = get_calibration_path(
                "modules/dut_measurement/modules/dut_measurement/calibration/thru_results/1-Port+N_errors",
                "modules/dut_measurement/modules/dut_measurement/calibration/thru_results/1-Port+N_errors",
                Path(__file__).resolve()
            )

        elif method == "Enhanced-Response":
            src_folder = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results/enhanced_response_errors",
                "modules/dut_measurement/calibration/thru_results/enhanced_response_errors",
                Path(__file__).resolve()
            )

        else:
            return
            
        # --- Copy ---
        if os.path.exists(src_folder):

            default_folder_name = os.path.basename(src_folder)

            dest_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save errors folder as",
                default_folder_name,
                "All Files (*)"
            )

            if not dest_path:
                return

            shutil.copytree(src_folder, dest_path, dirs_exist_ok=True)
        else:
            return

        QMessageBox.information(
            self,
            "Export completed",
            "Errors were exported successfully."
        )

    elif not no_calibration and kit_ok: 
        if getattr(sys, 'frozen', False):

            appdata = os.getenv("APPDATA")
            kits_path = os.path.join(
                appdata,
                "NanoVNA-UTN-Toolkit",
                "Calibration",
                "kits"
            )

            settings.beginGroup("Calibration")
            kit_name = settings.value("Name")
            settings.endGroup()

            if not kit_name:
                return

            base_name = re.sub(r'_\d+$', '', kit_name)

            source_folder = os.path.join(kits_path, base_name)

            if not os.path.exists(source_folder):
                QMessageBox.warning(
                    self,
                    "Kit not found",
                    "The selected kit folder was not found."
                )
                return

        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            kits_path = os.path.join(ui_dir, "Calibration", "kits")

            settings.beginGroup("Calibration")
            kit_name = settings.value("Name")
            settings.endGroup()

            if not kit_name:
                return

            base_name = re.sub(r'_\d+$', '', kit_name)
            source_folder = os.path.join(kits_path, base_name)

            if not os.path.exists(source_folder):
                QMessageBox.warning(
                    self,
                    "Kit not found",
                    "The selected kit folder was not found."
                )
                return

        # --- Copy ---
        default_folder_name = os.path.basename(source_folder)

        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save kit folder as",
            default_folder_name,
            "All Files (*)"
        )

        if not dest_path:
            return

        shutil.copytree(source_folder, dest_path, dirs_exist_ok=True)

        QMessageBox.information(
            self,
            "Export completed",
            "Kit was exported successfully."
        )

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