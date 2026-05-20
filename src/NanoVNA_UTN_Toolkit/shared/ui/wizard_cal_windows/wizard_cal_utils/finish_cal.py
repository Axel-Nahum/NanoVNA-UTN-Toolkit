import logging
import os

from datetime import datetime

from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.errors import CalibrationErrors

try:
    from NanoVNA_UTN_Toolkit.shared.utils.calibration_path_utils import get_calibration_path
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.shared.utils.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# Import NanoVNAGraphics for the final step
try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics
except ImportError as e:
    logging.error("Failed to import NanoVNAGraphics: %s", e)
    NanoVNAGraphics = None  # Safe fallback

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.calibration.calibration import update_calibration_label_from_method
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.shared.ui.wizard_cal_windows.wizard_cal_utils.sweep_cal import get_sweep_start_frequency, get_sweep_stop_frequency, get_sweep_steps
                                                                                
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------ #

def save_calibration_config(self):
    """Save calibration configuration to config file"""
    try:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Load configuration for calibration settings
        settings = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )

        settings.setValue("Calibration/Method", self.selected_method)
        settings.setValue("Calibration/DateTime_Calibration", current_datetime)
        settings.setValue("Calibration/NoCalibration", False)
        settings.setValue("Calibration/Kits", False)

        if self.selected_method == "OSM (Open - Short - Match)":
            parameter = "S11"
        elif self.selected_method == "Normalization":
            parameter = "S21"
        else:
            parameter = "S11, S21"

        settings.setValue("Calibration/Parameter", parameter)
        settings.sync()

        logging.info(f"Calibration method saved: {self.selected_method}")
        logging.info(f"Calibrated parameter saved: {parameter}")
        
    except Exception as e:
        logging.error(f"Failed to save calibration config: {e}")

def open_graphics_window(self):
    """Open the NanoVNA Graphics window and update calibration info"""
    try:
        logging.info("Opening NanoVNAGraphics window after calibration completion")
        
        if NanoVNAGraphics:
            # Create graphics window with VNA device if available
            if self.vna_device:
                graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
            else:
                graphics_window = NanoVNAGraphics()

            # Update calibration label with current method
            try:
                update_calibration_label_from_method(self, self.parent, self.selected_method)
            except Exception as e:
                logging.error(f"Failed to update calibration label in graphics window: {e}")
            
            # Save calibration configuration to config file
            save_calibration_config(self)
            
            # Show the graphics window
            graphics_window.show()
            logging.info("Graphics window opened successfully")
            
            # Close wizard after opening graphics window
            self.close()

            if hasattr(self, "caller") and hasattr(self.caller, "update_calibration_label_from_method"):
                update_calibration_label_from_method(self, self.parent, self.selected_method)
            
        else:
            logging.error("NanoVNAGraphics not available - cannot open graphics window")
            QMessageBox.warning(
                self, 
                "Warning", 
                "Graphics window is not available. Please restart the application."
            )
            
    except Exception as e:
        logging.error(f"Error opening graphics window: {e}")
        QMessageBox.critical(
            self, 
            "Error", 
            f"Failed to open graphics window: {str(e)}"
        )

def finish_wizard(self, parent = None):
    """Finish calibration wizard by calculating OSM errors and opening graphics window."""
    logging.info("Calibration wizard completed - calculating OSM errors")

    if self.selected_method == "OSM (Open - Short - Match)":
        cal_dir = get_calibration_path(
            "modules/dut_measurement/calibration/osm_results",
            "modules/dut_measurement/calibration/osm_results",
            Path(__file__).resolve()
        )
        os.makedirs(cal_dir, exist_ok=True)

        # Create calibration error handler and compute OSM errors
        errors = CalibrationErrors(cal_dir, error_subfolder="osm_errors")
        errors.calculate_osm_errors()

    elif self.selected_method == "Normalization":
        cal_dir = get_calibration_path(
            "modules/dut_measurement/calibration/thru_results",
            "modules/dut_measurement/calibration/thru_results",
            Path(__file__).resolve()
        )
        os.makedirs(cal_dir, exist_ok=True)

        errors = CalibrationErrors(cal_dir, error_subfolder="normalization_errors")
        errors.calculate_normalization_errors()

    elif self.selected_method == "1-Port+N":
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

        os.makedirs(osm_dir, exist_ok=True)
        os.makedirs(thru_dir, exist_ok=True)

        errors = CalibrationErrors(thru_dir, error_subfolder="1-Port+N_errors")
        errors.calculate_1PortN_errors(osm_dir, thru_dir)

    elif self.selected_method == "Enhanced-Response":
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

        os.makedirs(osm_dir, exist_ok=True)
        os.makedirs(thru_dir, exist_ok=True)

        errors = CalibrationErrors(thru_dir, error_subfolder="enhanced_response_errors")
        errors.calculate_enhanced_response_errors(osm_dir, thru_dir)

    # Store results for later use if needed
    self.directivity = errors.directivity
    self.reflection_tracking = errors.reflection_tracking
    self.source_match = errors.source_match

    # Load configuration for calibration settings
    settings_calibration = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    settings_calibration.setValue("Calibration/CalibrationWizard", True)
    settings_calibration.setValue("Calibration/NoCalibration", False)
    settings_calibration.setValue("Calibration/Kits", False)
    settings_calibration.setValue("Calibration/isImportDut", False)
    settings_calibration.setValue("Calibration/Method", self.selected_method)
    
    # Load configuration for sweep settings and frequency range parameters
    settings = get_settings(
        "INI/dut_measurement/sweep_config/sweep_config.ini",
        "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini", 
        Path(__file__).resolve()        
    )

    settings.setValue("Frequency/StartFreqHz", get_sweep_start_frequency(self))
    settings.setValue("Frequency/StopFreqHz", get_sweep_stop_frequency(self))
    settings.setValue("Frequency/Segments", get_sweep_steps(self))

    # Open graphics window
    open_graphics_window(self)