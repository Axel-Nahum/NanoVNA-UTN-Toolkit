import os
import sys
from pathlib import Path

from PySide6.QtCore import QSettings

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

def update_calibration_label_from_method(self, parent = None, method=None):

    self.graphics_window = parent

    # Load configuration for calibration settings
    settings_calibration = get_settings(
        "INI/calibration_config/calibration_config.ini",
        "calibration/calibration_config/calibration_config.ini", 
        Path(__file__).resolve()
    )

    settings_calibration.sync()

    kits_ok = settings_calibration.value("Calibration/Kits", False, type=bool)
    no_calibration = settings_calibration.value("Calibration/NoCalibration", False, type=bool)
    calibration_method = settings_calibration.value("Calibration/Method", "---")
    is_import_dut = settings_calibration.value("Calibration/isImportDut", False, type=bool)

    settings_calibration.sync()

    if is_import_dut:
        text = "DUT"

    elif no_calibration:
        text = "No Calibration"

    elif kits_ok:

        selected_full_name = settings_calibration.value("Calibration/Name", "---")
        selected_kit_name = "_".join(selected_full_name.split("_")[:-1])

        kit_found = False
        i = 1

        while settings_calibration.contains(f"Kit_{i}/kit_name"):

            kit_name = settings_calibration.value(f"Kit_{i}/kit_name", "---")
            method_kit = settings_calibration.value(f"Kit_{i}/method", "---")

            if kit_name == selected_kit_name:
                text = f"Calibration Kit | Name: {kit_name} and Method: {method_kit}"
                kit_found = True
                break

            i += 1

        if not kit_found:
            text = f"Calibration Kit: {selected_kit_name or 'Unknown'} (method not found)"
        
    elif not no_calibration:
        text = f"Calibration Wizard | Method: {calibration_method}"

    self.calibration_label.setText(text)



        



