import sys
import os
import shutil
import re

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QMessageBox

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.calibration.calibration_path_utils import get_calibration_path
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

def export_touchstone_data(self):
    """
    Export sweep data to Touchstone format.
    
    Shows a dialog to choose between S1P and S2P formats.
    """

    # Show format selection dialog
    format_choice = self._show_touchstone_format_dialog()
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

    settings = get_settings(
        "INI/calibration_config/calibration_config.ini",
        "calibration/config/calibration_config.ini", 
        Path(__file__).resolve()
    )

    kit_ok = settings.value(f"Calibration/Kits", False, type=bool)
    no_calibration = settings.value(f"Calibration/NoCalibration", False, type=bool)

    method = settings.value(f"Calibration/Method", "Normalization")

    if not no_calibration and not kit_ok:

        if method == "OSM (Open - Short - Match)":
            src_folder = get_calibration_path(
                "calibration/osm_results/osm_errors",
                "calibration/osm_results/osm_errors",
                Path(__file__).resolve()
            )

        elif method == "Normalization":
            src_folder = get_calibration_path(
                "calibration/thru_results/normalization_errors",
                "calibration/thru_results/normalization_errors",
                Path(__file__).resolve()
            )

        elif method == "1-Port+N":
            src_folder = get_calibration_path(
                "calibration/thru_results/1-Port+N_errors",
                "calibration/thru_results/1-Port+N_errors",
                Path(__file__).resolve()
            )

        elif method == "Enhanced-Response":
            src_folder = get_calibration_path(
                "calibration/thru_results/enhanced_response_errors",
                "calibration/thru_results/enhanced_response_errors",
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