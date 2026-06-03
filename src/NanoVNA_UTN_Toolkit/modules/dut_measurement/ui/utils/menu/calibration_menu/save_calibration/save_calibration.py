from NanoVNA_UTN_Toolkit.utils import safe_import
import logging 
import sys
import os

from pathlib import Path

from datetime import datetime

from PySide6.QtWidgets import QMessageBox

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

get_calibration_path = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils", "get_calibration_path")

# ---------------------------------------------------------------------------------------------------------------- #

def show_calibration_warning(self):
    msg = QMessageBox(self)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle("NanoVNA UTN Toolkit - Calibration Warning")
    msg.setText(
        "Save operation is disabled because calibration was not performed from scratch.\n"
        "Please use the calibration wizard to create a new calibration before saving."
    )
    msg.exec()

def save_kit_dialog(self):
    from PySide6.QtWidgets import QMessageBox
    """Shows a dialog to save the calibration without advancing to graphics window"""

    self.osm_calibration.is_complete_true()
    self.thru_calibration.is_complete_true()

    osm_dir = get_calibration_path(
        "modules/dut_measurement/calibration/osm_results",
        "modules/dut_measurement/calibration/osm_results",
        Path(__file__).resolve()
    )

    thru_dir = get_calibration_path(
        "modules/dut_measurement/calibration/thru_results",
        "modules/dut_measurement/calibration/thru_results",
        Path(__file__).resolve()
    )

    files = [
        os.path.join(osm_dir, "open.s1p"),
        os.path.join(osm_dir, "short.s1p"),
        os.path.join(osm_dir, "match.s1p"),
        os.path.join(thru_dir, "thru.s2p")
    ]

    # Load configuration for calibration

    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    # Method
    selected_method = settings.value("Calibration/Method", "No Kit")

    # Dialog to enter calibration name
    from PySide6.QtWidgets import QInputDialog

    if selected_method == "OSM (Open - Short - Match)":
        prefix = "OSM"
    elif selected_method == "Normalization":
        prefix = "Normalization"
    elif selected_method== "1-Port+N":
        prefix = "1PortN"
    elif selected_method == "Enhanced-Response":
        prefix = "Enhanced Response"

    dialog = QInputDialog(self)

    dialog.setWindowTitle(f"{self.cal_kit_window_title_save}")
    dialog.setLabelText(f"{self.cal_kit_window_save_text}")

    dialog.setTextValue(f"{prefix}_Calibration_{self.get_current_timestamp()}")

    dialog.setOkButtonText(f"{self.cal_kit_window_save}")
    dialog.setCancelButtonText(f"{self.cal_kit_window_cancel}")

    ok = dialog.exec()

    name = dialog.textValue()
    
    if ok and name:
        try:
            # Save calibration (it will save only the available measurements)
            if selected_method != "Normalization": 
                success = self.osm_calibration.save_calibration_file(name, selected_method, False, files)
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
                    #QMessageBox.warning(self, "Error", "Failed to save calibration") hay un error aca y entra primero

            success = self.thru_calibration.save_calibration_file(name, selected_method, True, files, osm_instance=self.osm_calibration)
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

            # Load configuration for calibration

            settings_calibration = get_settings(
                "INI/dut_measurement/dut_measurement/calibration_config/calibration_config.ini",
                "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
                Path(__file__).resolve()
            )
            
            """
            # --- If a kit was previously saved in this session, show its name ---
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

            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # --- Save data ---
            settings_calibration.beginGroup(calibration_entry_name)
            settings_calibration.setValue("kit_name", name)
            settings_calibration.setValue("method", selected_method)
            settings_calibration.setValue("id", next_id)
            settings_calibration.setValue("DateTime_Kits", current_datetime)
            settings_calibration.endGroup()

            # --- Update active calibration reference ---
            settings_calibration.beginGroup("Calibration")
            settings_calibration.setValue("Name", full_calibration_name)
            settings_calibration.endGroup()
            settings_calibration.sync()

            logging.info(f"[welcome_windows.open_save_calibration] Saved calibration {full_calibration_name}")

        except Exception as e:
            logging.error(f"[CalibrationKit] Error saving calibration: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")