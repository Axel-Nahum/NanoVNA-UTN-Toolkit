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

def handle_save_calibration(self):

    settings = get_settings(
        "INI/calibration_config/calibration_config.ini",
        "calibration/config/calibration_config.ini", 
        Path(__file__).resolve()
    )

    settings.sync()

    # Read values from INI
    kits_ok = settings.value("Calibration/Kits", False, type=bool)
    no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)

    # Check if calibration was performed from scratch
    if not kits_ok and not no_calibration:
        # Calibration was done from scratch → execute save
        self.save_kit_dialog()
    else:
        # Calibration was not done from scratch → show warning
        self.show_calibration_warning()