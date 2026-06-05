from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from pathlib import Path

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")
stop_realtime = safe_import("NanoVNA_UTN_Toolkit.shared.utils.real_time.real_time", "stop_realtime")

# ------------------------------------------------------------------------------------------------------------------ #

def handle_deleted_current_kit(self):

    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics

    # Load configuration for calibration settings
    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
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

    try:
        stop_realtime(self)
    except:
        pass

    if self.vna_device:
        graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
    else:
        graphics_window = NanoVNAGraphics()

    graphics_window.setGeometry(self.geometry())
    graphics_window.show()
    graphics_window.raise_()
    graphics_window.activateWindow()

    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()
    QApplication.processEvents()  

    self.close()

def handle_all_kits_deleted(self):

    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics

    # Load configuration for calibration settings
    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    kits_ok = settings.value("Calibration/Kits", False, type=bool)
    no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)
    calibration_wizard = settings.value("Calibration/CalibrationWizard", False, type=bool)

    settings.sync()

    if not no_calibration and calibration_wizard:
        # If no kits remain, fallback to a safe state

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

    try:
        stop_realtime(self)
    except:
        pass

    # --- Reopen graphics window in no-calibration mode ---
    if self.vna_device:
        graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
    else:
        graphics_window = NanoVNAGraphics()

    graphics_window.show()

    self.close()