from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from datetime import datetime

from pathlib import Path

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

    # Dialog to enter calibration name
    from PySide6.QtWidgets import QInputDialog

    if self.selected_method == "OSM (Open - Short - Match)":
        prefix = "OSM"
    elif self.selected_method == "Thru Normalization":
        prefix = "Thru_Normalization"
    elif self.selected_method == "Open/Short Normalization":
        prefix = "OpenShort_Normalization"
    elif self.selected_method == "1-Port+N":
        prefix = "1PortN"
    elif self.selected_method == "Enhanced-Response":
        prefix = "Enhanced Response"
    else:
        prefix = "Calibration"

    name, ok = QInputDialog.getText(
        self,
        'Save Calibration',
        f'Enter calibration name:\n\nMeasurements to save: {", ".join(measured_standards).upper()}',
        text=f'{prefix}_Calibration_{get_current_timestamp(self)}'
    )

    if ok and name:
        try:
            saved = False

            if self.selected_method == "Open/Short Normalization":
                result = self.os_calibration.save_calibration_file(name, self.selected_method, False)
                if _extract_success(result):
                    saved = True
                    logging.info(f"Open/Short Normalization kit '{name}' saved successfully")
            else:
                if self.selected_method in ("OSM (Open - Short - Match)", "1-Port+N", "Enhanced-Response"):
                    result = self.osm_calibration.save_calibration_file(name, self.selected_method, False)
                    if _extract_success(result):
                        saved = True
                        logging.info(f"OSM calibration '{name}' saved successfully")

                if self.selected_method in ("Thru Normalization", "1-Port+N", "Enhanced-Response"):
                    result = self.thru_calibration.save_calibration_file(name, self.selected_method, False, osm_instance=self.osm_calibration)
                    if _extract_success(result):
                        saved = True
                        logging.info(f"Thru calibration '{name}' saved successfully")

            if saved:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Calibration '{name}' saved successfully!\n\nSaved measurements: {', '.join(measured_standards).upper()}\n\nFiles saved in:\n- Touchstone format\n- .cal format\n\nUse 'Finish' button to continue to graphics window."
                )
                # Reset all managers so this session's data does not bleed into the next calibration
                _reset_all_managers(self)
            else:
                QMessageBox.warning(self, "Save Failed", f"Could not save calibration '{name}'.\nCheck that all required measurements have been performed.")
                return

            # Load configuration for calibration settings
            settings_calibration = get_settings(
                "INI/dut_measurement/calibration_config/calibration_config.ini",
                "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
                Path(__file__).resolve()
            )

            # --- Check if name already exists in any Kit ---
            existing_groups = settings_calibration.childGroups()
            for g in existing_groups:
                if g.startswith("Kit_"):
                    existing_name = settings_calibration.value(f"{g}/kit_name", "")
                    if existing_name == name:
                        QMessageBox.warning(self, "Duplicate Name",
                                            f"The kit name '{name}' already exists.\nPlease choose another name.",
                                            QMessageBox.Ok)
                        return

            # --- Determine ID: always calculate next available to prevent overwriting ---
            kit_ids = [int(g.split("_")[1]) for g in existing_groups if g.startswith("Kit_") and g.split("_")[1].isdigit()]
            next_id = max(kit_ids, default=0) + 1

            calibration_entry_name = f"Kit_{next_id}"
            full_calibration_name = f"{name}_{next_id}"

            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # --- Save data ---
            settings_calibration.beginGroup(calibration_entry_name)
            settings_calibration.setValue("kit_name", name)
            settings_calibration.setValue("method", self.selected_method)
            settings_calibration.setValue("id", next_id)
            settings_calibration.setValue("DateTime_Kits", current_datetime)
            settings_calibration.endGroup()

            # --- Update active calibration reference ---
            settings_calibration.beginGroup("Calibration")
            settings_calibration.setValue("Name", full_calibration_name)
            settings_calibration.endGroup()
            settings_calibration.sync()

            logging.info(f"[CalibrationDialog] Saved calibration {full_calibration_name}")

        except Exception as e:
            logging.error(f"[CalibrationWizard] Error saving calibration: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")
