import os

from pathlib import Path

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)


def handle_deleted_current_kit(self):

    from NanoVNA_UTN_Toolkit.ui.graphics_window import NanoVNAGraphics

    # Load configuration for calibration 
    settings = get_settings(
        "INI/calibration_config/calibration_config.ini",
        "calibration/config/calibration_config.ini", 
        Path(__file__).resolve()
    )

    # --- Check if there's still a Kit_1 ---
    if settings.contains("Kit_1/kit_name"):
        first_kit_name = settings.value("Kit_1/kit_name", "").strip()
        method = settings.value("Kit_1/method", "")
        
        # Get previous method/parameter if they exist
        prev_method = settings.value("Calibration/Method", method)
        prev_parameter = settings.value("Calibration/Parameter", "S21")

        # --- Update Calibration section ---
        settings.beginGroup("Calibration")
        settings.setValue("Kits", True)
        settings.setValue("NoCalibration", False)
        settings.setValue("Method", prev_method)
        settings.setValue("Parameter", prev_parameter)
        settings.setValue("Name", f"{first_kit_name}_1")
        settings.setValue("id", 1)
        settings.endGroup()

    settings.sync()

    if self.vna_device:
        graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
    else:
        graphics_window = NanoVNAGraphics()
    graphics_window.show()
    self.close()

def handle_all_kits_deleted(self):

    from NanoVNA_UTN_Toolkit.ui.graphics_window import NanoVNAGraphics

    # Load configuration for calibration 
    settings = get_settings(
        "INI/calibration_config/calibration_config.ini",
        "calibration/config/calibration_config.ini", 
        Path(__file__).resolve()
    )

    kits_ok = settings.value("Calibration/Kits", False, type=bool)
    no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)
    calibration_wizard = settings.value("Calibration/CalibrationWizard", False, type=bool)

    settings.sync()

    if not no_calibration and calibration_wizard:
        # If no kits remain, fallback to a safe state

        print(f"CalibrationWizard1: {calibration_wizard}")

        settings.beginGroup("Calibration")
        settings.setValue("Kits", False)
        settings.setValue("NoCalibration", False)
        settings.setValue("CalibrationWizard", True)
        settings.remove("Name")
        settings.remove("id")
        settings.endGroup()
        settings.sync()

    elif not no_calibration and not calibration_wizard:

        # --- Set calibration state to NoCalibration ---
        settings.beginGroup("Calibration")
        settings.setValue("Kits", False)
        settings.setValue("NoCalibration", True)
        settings.setValue("CalibrationWizard", False)
        settings.remove("Name")
        settings.remove("id")
        settings.endGroup()
        settings.sync()

    # --- Reopen graphics window in no-calibration mode ---
    if self.vna_device:
        graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
    else:
        graphics_window = NanoVNAGraphics()

    graphics_window.show()

    self.close()