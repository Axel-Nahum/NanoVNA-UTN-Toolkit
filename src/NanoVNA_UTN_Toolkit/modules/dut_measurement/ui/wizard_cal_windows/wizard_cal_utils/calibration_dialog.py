from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys
import os
import shutil

from datetime import datetime

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QCheckBox, QDialogButtonBox
)

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

# ------------------------------------------------------------------------------------------------------------------ #

def get_current_timestamp(self):
    """Generate timestamp for filenames"""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _extract_success(result):
    """Extract bool from either a plain bool or a (bool, extras) tuple."""
    if isinstance(result, tuple):
        return bool(result[0])
    return bool(result)

def _reset_all_managers(self):
    """Clear all calibration managers after a save so the next method starts fresh."""
    if self.osm_calibration:
        self.osm_calibration.clear_all_measurements()
    if self.thru_calibration:
        self.thru_calibration.clear_all_measurements()
    if hasattr(self, 'os_calibration') and self.os_calibration:
        self.os_calibration.clear_all_measurements()

def save_calibration_dialog(self):
    from PySide6.QtWidgets import QMessageBox
    """Shows a dialog to save the calibration without advancing to graphics window"""
    if not self.osm_calibration:
        return

    if not self.thru_calibration:
        return

    # Check which measurements are available
    if self.selected_method == "Open/Short Normalization":
        if not hasattr(self, 'os_calibration') or not self.os_calibration:
            QMessageBox.warning(self, "No Measurements", "No calibration measurements have been taken yet.")
            return
        os_status = self.os_calibration.get_completion_status()
        measured_standards = [std for std, completed in os_status.items() if completed and std != 'complete']
    else:
        osm_status = self.osm_calibration.get_completion_status()
        thru_status = self.thru_calibration.get_completion_status()
        measured_standards = [
            std for std, completed in osm_status.items() if completed and std != 'complete'
        ] + [
            std for std, completed in thru_status.items() if completed and std != 'complete'
        ]

    if not measured_standards:
        QMessageBox.warning(
            self,
            "No Measurements",
            "No calibration measurements have been taken yet.\nPlease perform at least one measurement before saving."
        )
        return

    _prefix_map = {
        "OSM (Open - Short - Match)": "OSM",
        "Thru Normalization": "Thru_Normalization",
        "Open/Short Normalization": "OpenShort_Normalization",
        "1-Port+N": "1PortN",
        "Enhanced-Response": "Enhanced_Response",
    }
    prefix = _prefix_map.get(self.selected_method, "Calibration")

    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.calibration_menu.save_calibration.save_calibration import _SaveKitDialog
    dlg = _SaveKitDialog(
        self,
        default_name=f"{prefix}_Calibration_{get_current_timestamp(self)}"
    )
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return

    name = dlg.kit_name
    save_internal = dlg.save_internal
    save_custom = dlg.save_custom

    if not name:
        return

    dest_root = None
    if save_custom:
        from PySide6.QtWidgets import QFileDialog
        dest_root = QFileDialog.getExistingDirectory(
            self, "Select folder to export calibration kit"
        )
        if not dest_root:
            return

    if name:
        try:
            import zipfile
            from PySide6.QtWidgets import QMessageBox

            # --- Save to internal library ---
            saved = False

            if self.selected_method == "Open/Short Normalization":
                result = self.os_calibration.save_calibration_file(name, self.selected_method, False)
                if _extract_success(result):
                    saved = True
                    logging.info(f"Open/Short Normalization kit '{name}' saved")
            else:
                if self.selected_method in ("OSM (Open - Short - Match)", "1-Port+N", "Enhanced-Response"):
                    result = self.osm_calibration.save_calibration_file(name, self.selected_method, False)
                    if _extract_success(result):
                        saved = True
                        logging.info(f"OSM calibration '{name}' saved")

                if self.selected_method in ("Thru Normalization", "1-Port+N", "Enhanced-Response"):
                    result = self.thru_calibration.save_calibration_file(name, self.selected_method, False, osm_instance=self.osm_calibration)
                    if _extract_success(result):
                        saved = True
                        logging.info(f"Thru calibration '{name}' saved")

            if not saved:
                QMessageBox.warning(self, "Save Failed",
                                    f"Could not save calibration '{name}'.\nCheck that all required measurements have been performed.")
                return

            _reset_all_managers(self)

            # --- Register in INI ---
            settings_calibration = get_settings(
                "INI/dut_measurement/calibration_config/calibration_config.ini",
                "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
                Path(__file__).resolve()
            )

            existing_groups = settings_calibration.childGroups()
            for g in existing_groups:
                if g.startswith("Kit_") and settings_calibration.value(f"{g}/kit_name", "") == name:
                    QMessageBox.warning(self, "Duplicate Name",
                                        f"The kit name '{name}' already exists.\nPlease choose another name.")
                    return

            kit_ids = [int(g.split("_")[1]) for g in existing_groups if g.startswith("Kit_") and g.split("_")[1].isdigit()]
            next_id = max(kit_ids, default=0) + 1
            calibration_entry_name = f"Kit_{next_id}"
            full_calibration_name = f"{name}_{next_id}"
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            settings_calibration.beginGroup(calibration_entry_name)
            settings_calibration.setValue("kit_name", name)
            settings_calibration.setValue("method", self.selected_method)
            settings_calibration.setValue("id", next_id)
            settings_calibration.setValue("DateTime_Kits", current_datetime)
            settings_calibration.endGroup()

            settings_calibration.beginGroup("Calibration")
            settings_calibration.setValue("Name", full_calibration_name)
            settings_calibration.endGroup()
            settings_calibration.sync()

            logging.info(f"[CalibrationDialog] Registered calibration {full_calibration_name}")

            # --- Single final message ---
            if save_custom:
                from NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils import get_calibration_path
                kits_base = get_calibration_path(
                    "modules/dut_measurement/calibration/kits",
                    "modules/dut_measurement/calibration/kits",
                    Path(__file__).resolve()
                )
                kit_folder = os.path.join(kits_base, name)

                sweep_settings = get_settings(
                    "INI/dut_measurement/sweep_config/sweep_config.ini",
                    "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini",
                    Path(__file__).resolve()
                )

                ini_lines = [
                    "[Kit]\n",
                    f"name = {name}\n",
                    f"method = {self.selected_method}\n",
                    f"date = {current_datetime}\n",
                    f"start_freq_hz = {sweep_settings.value('Frequency/StartFreqHz', 0)}\n",
                    f"stop_freq_hz = {sweep_settings.value('Frequency/StopFreqHz', 0)}\n",
                    f"segments = {sweep_settings.value('Frequency/Segments', 101)}\n",
                    f"start_unit = {sweep_settings.value('Frequency/StartUnit', 'MHz')}\n",
                    f"stop_unit = {sweep_settings.value('Frequency/StopUnit', 'MHz')}\n",
                ]

                zip_path = os.path.join(dest_root, f"{name}.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    if os.path.isdir(kit_folder):
                        for root, dirs, fnames in os.walk(kit_folder):
                            for fname in fnames:
                                fpath = os.path.join(root, fname)
                                arcname = os.path.relpath(fpath, kit_folder)
                                zf.write(fpath, arcname)
                    zf.writestr("kit_info.ini", "".join(ini_lines))

                logging.info(f"[CalibrationDialog] Exported ZIP: {zip_path}")
                if save_internal:
                    msg = f"Kit '{name}' saved to the internal library and exported as:\n{zip_path}"
                else:
                    msg = f"Kit '{name}' exported as:\n{zip_path}"
                QMessageBox.information(self, "Calibration kit saved", msg)
            else:
                QMessageBox.information(
                    self, "Calibration kit saved",
                    f"Kit '{name}' saved to the internal library."
                )

        except Exception as e:
            logging.error(f"[CalibrationWizard] Error saving calibration: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")
