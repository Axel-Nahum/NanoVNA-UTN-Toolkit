import logging
import sys

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QFileDialog, QMessageBox, QColor

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ---------------------------------------------------------------------------------------------------------------- #

def start_calibration(self, files, selected_method, dialog):
    print(f"Starting calibration with method: {selected_method}")
    for f in files:
        print(f)
    dialog.accept()

    self.save_calibration_dialog(selected_method, files)

def save_calibration_dialog(self, selected_method, files):
    from PySide6.QtWidgets import QMessageBox
    """Shows a dialog to save the calibration without advancing to graphics window"""
    if not self.osm_calibration:
        return

    if not self.thru_calibration:
        return

    # Check which measurements are available
    osm_status = self.osm_calibration.is_complete_true()
    thru_status = self.thru_calibration.is_complete_true()
            
    # Dialog to enter calibration name
    from PySide6.QtWidgets import QInputDialog

    if selected_method == "OSM (Open - Short - Match)":
        prefix = "OSM"
    elif selected_method == "Normalization":
        prefix = "Normalization"
    elif selected_method == "1-Port+N":
        prefix = "1PortN"
    elif selected_method == "Enhanced-Response":
        prefix = "Enhanced Response"

    name, ok = QInputDialog.getText(
        self, 
        'Save Calibration', 
        f'Enter calibration name:',
        text=f'{prefix}_Calibration_{self.get_current_timestamp()}'
    )

    is_external_kit = True
    
    if ok and name:
        try:
            # Save calibration (it will save only the available measurements)
            success = self.osm_calibration.save_calibration_file(name, selected_method, is_external_kit, files)
            if success:
                # Show success message
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Calibration '{name}' saved successfully!\n\nSaved measurements: \n\nFiles saved in:\n- Touchstone format\n- .cal format\n\nUse 'Finish' button to continue to graphics window."
                )
                
                # Stay in wizard - do not advance to graphics window
                logging.info(f"Calibration '{name}' saved successfully - staying in wizard")
                
            else:
                from PySide6.QtWidgets import QMessageBox
                #QMessageBox.warning(self, "Error", "Failed to save calibration")

            success = self.thru_calibration.save_calibration_file(name, selected_method, is_external_kit, files, osm_instance=self.osm_calibration)
            if success:
                # Show success message
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Calibration '{name}' saved successfully!\n\nSaved measurements: \n\nFiles saved in:\n- Touchstone format\n- .cal format\n\nUse 'Finish' button to continue to graphics window."
                )
                
                # Stay in wizard - do not advance to graphics window
                logging.info(f"Calibration '{name}' saved successfully - staying in wizard")
                
            else:
                from PySide6.QtWidgets import QMessageBox
                #QMessageBox.warning(self, "Error", "Failed to save calibration")

            # --- Read current calibration method ---
            # Use new calibration structure

            # Load configuration for calibration settings
            settings_calibration = get_settings(
                "INI/dut_measurement/calibration_config/calibration_config.ini",
                "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
                Path(__file__).resolve()
            )

            """     # --- If a kit was previously saved in this session, show its name ---
            if getattr(self, 'last_saved_kit_id', None):
                last_id = self.last_saved_kit_id
                last_name = settings_calibration.value(f"Kit_{last_id}/kit_name", "")
                if last_name:
                    name_input.setText(last_name)

            if name is None:
                name = name_input.text().strip()
            if not name:
                name_input.setPlaceholderText("Please enter a valid name...")
                return
            """
            # --- Check if name already exists in any Kit ---
            existing_groups = settings_calibration.childGroups()
            for g in existing_groups:
                if g.startswith("Kit_"):
                    existing_name = settings_calibration.value(f"{g}/kit_name", "")
                    if existing_name == name:
                        # Show warning message box if name exists
                        QMessageBox.warning(dialog, "Duplicate Name",
                                            f"The kit name '{name}' already exists.\nPlease choose another name.",
                                            QMessageBox.Ok)
                        return

            # --- Determine ID: use last saved if exists ---
            if getattr(self, 'last_saved_kit_id', None):
                next_id = self.last_saved_kit_id
            else:
                # First save -> calculate next available ID
                kit_ids = [int(g.split("_")[1]) for g in existing_groups if g.startswith("Kit_") and g.split("_")[1].isdigit()]
                next_id = max(kit_ids, default=0) + 1
                self.last_saved_kit_id = next_id  # store ID for overwriting next time

            calibration_entry_name = f"Kit_{next_id}"
            full_calibration_name = f"{name}_{next_id}"

            # --- Save data ---
            settings_calibration.beginGroup(calibration_entry_name)
            settings_calibration.setValue("kit_name", name)
            settings_calibration.setValue("method", selected_method)
            settings_calibration.setValue("id", next_id)
            settings_calibration.endGroup()

            # --- Update active calibration reference ---
            settings_calibration.beginGroup("Calibration")
            settings_calibration.setValue("Name", full_calibration_name)
            settings_calibration.endGroup()
            settings_calibration.sync()

            settings_calibration.setValue("Calibration/Kits", True)
            settings_calibration.setValue("Calibration/NoCalibration", False)

            if selected_method == "OSM (Open - Short - Match)":
                parameter = "S11"
            elif selected_method == "Normalization":
                parameter = "S21"
            else:
                parameter = "S11, S21"

            settings_calibration.setValue("Calibration/Parameter", parameter)
            settings_calibration.sync()

            logging.info(f"[welcome_windows.open_save_calibration] Saved calibration {full_calibration_name}")

        except Exception as e:
            logging.error(f"[CalibrationGraphics] Error saving calibration: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")