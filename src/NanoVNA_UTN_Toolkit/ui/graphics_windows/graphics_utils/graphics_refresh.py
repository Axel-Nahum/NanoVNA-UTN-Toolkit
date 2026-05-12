import logging
import os
import sys
import numpy as np
import skrf as rf

from pathlib import Path

from PySide6.QtCore import QTimer, QSettings
from PySide6.QtWidgets import (
    QApplication, QMessageBox
)

from NanoVNA_UTN_Toolkit.ui.calibration.methods import Methods
from NanoVNA_UTN_Toolkit.ui.calibration.kits import KitsCalibrator

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

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.updates.graphics_update import update_plots_with_new_data
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from src.NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.reset.sliders_reset import _reset_sliders_before_sweep
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from src.NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.reset.cursors_reset import _reset_markers_after_sweep
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from src.NanoVNA_UTN_Toolkit.ui.utils.calibration.calibration import update_calibration_label_from_method
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from src.NanoVNA_UTN_Toolkit.ui.utils.sweep_utils.sweep_utils import load_sweep_configuration
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ----------------------------------------------------------------------------------------------------------------- #

def update_reconnect_button_state(self):
    """Update the reconnect button state based on device connection."""
    if not self.vna_device:
        # Instead of disabling, show "Connect" button so user can try to connect
        self.reconnect_button.setEnabled(True)
        self.reconnect_button.setText("Connect")
        self.reconnect_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        return
        
    is_connected = self.vna_device.connected()

    if is_connected:
        # Connected state: standard button saying "Reconnect" (same style as Run Sweep button)
        self.reconnect_button.setEnabled(True)
        self.reconnect_button.setText("Reconnect")
        # Force reset to standard button appearance by setting style to None and updating
        self.reconnect_button.setStyleSheet("")
        self.reconnect_button.style().unpolish(self.reconnect_button)
        self.reconnect_button.style().polish(self.reconnect_button)
        self.reconnect_button.update()
    else:
        # Disconnected state: green button saying "Connect"
        self.reconnect_button.setEnabled(True)
        self.reconnect_button.setText("Connect")
        self.reconnect_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)

def _reset_sweep_ui(self):

    if hasattr(self, "sweep_button"):
        self.sweep_button.setEnabled(True)
        self.sweep_button.setText("Run Sweep")

    if hasattr(self, "sweep_progress_bar"):
        self.sweep_progress_bar.setVisible(False)
        self.sweep_progress_bar.setValue(0)

    if hasattr(self, "_update_reconnect_button_state"):
        update_reconnect_button_state(self)

def run_sweep(self):
    """Run a sweep on the connected device."""
    logging.info("[graphics_window.run_sweep] Starting sweep operation")
    
    if not self.vna_device:
        error_msg = "No VNA device connected. Cannot perform sweep."
        QMessageBox.warning(self, "No Device", error_msg)
        logging.warning(f"[graphics_window.run_sweep] {error_msg}")
        return
        
    # Check and ensure device connection
    if not self.vna_device.connected():
        logging.warning("[graphics_window.run_sweep] Device not connected, attempting to reconnect...")
        try:
            self.vna_device.connect()
            if not self.vna_device.connected():
                error_msg = "VNA device connection failed. Please check device and try again."
                QMessageBox.warning(self, "Connection Failed", error_msg)
                logging.error(f"[graphics_window.run_sweep] {error_msg}")
                return
            logging.info("[graphics_window.run_sweep] Device reconnected successfully")
        except Exception as e:
            error_msg = f"Failed to reconnect to VNA device: {str(e)}"
            QMessageBox.critical(self, "Connection Error", error_msg)
            logging.error(f"[graphics_window.run_sweep] {error_msg}")
            return
        
    try:
        # Reset sliders and clear all marker information before starting sweep
        logging.info("[graphics_window.run_sweep] Preparing for sweep - resetting sliders and clearing info")
        _reset_sliders_before_sweep(self)
        
        # Disable sweep button and show progress bar
        self.sweep_button.setEnabled(False)
        self.sweep_button.setText("Sweeping...")
        self.sweep_progress_bar.setVisible(True)
        self.sweep_progress_bar.setValue(0)
        
        # Also disable reconnect button during sweep
        self.reconnect_button.setEnabled(False)
        
        # Load current sweep configuration
        load_sweep_configuration(self)
        
        device_type = type(self.vna_device).__name__
        logging.info(f"[graphics_window.run_sweep] Running sweep on {device_type}")
        logging.info(f"[graphics_window.run_sweep] Frequency range: {self.start_freq_hz/1e6:.3f} MHz - {self.stop_freq_hz/1e6:.3f} MHz")
        logging.info(f"[graphics_window.run_sweep] Number of points: {self.segments}")
        
        # Validate sweep parameters - get device limits dynamically
        default_min = 11
        default_max = 1023
        
        # Get device-specific limits
        if self.vna_device:
            sweep_min = getattr(self.vna_device, 'sweep_points_min', default_min)
            
            # Check if device has valid_datapoints and use the maximum from there if available
            if hasattr(self.vna_device, 'valid_datapoints') and self.vna_device.valid_datapoints:
                sweep_max = max(self.vna_device.valid_datapoints)
                logging.info(f"[graphics_window.run_sweep] Using max from valid_datapoints: {sweep_max}")
            else:
                sweep_max = getattr(self.vna_device, 'sweep_points_max', default_max)
                logging.info(f"[graphics_window.run_sweep] Using sweep_points_max: {sweep_max}")
        else:
            sweep_min = default_min
            sweep_max = default_max
            logging.warning(f"[graphics_window.run_sweep] No VNA device, using default limits: {sweep_min}-{sweep_max}")
        
        if self.segments < sweep_min or self.segments > sweep_max:
            error_msg = f"Invalid number of sweep points: {self.segments}. Must be between {sweep_min} and {sweep_max}."
            QMessageBox.warning(self, "Invalid Parameters", error_msg)
            logging.error(f"[graphics_window.run_sweep] {error_msg}")
            _reset_sweep_ui(self)
            return
            
        if self.start_freq_hz >= self.stop_freq_hz:
            error_msg = f"Invalid frequency range: start ({self.start_freq_hz/1e6:.3f} MHz) must be less than stop ({self.stop_freq_hz/1e6:.3f} MHz)"
            QMessageBox.warning(self, "Invalid Parameters", error_msg)
            logging.error(f"[graphics_window.run_sweep] {error_msg}")
            _reset_sweep_ui(self)
            return
        
        # Update progress bar
        self.sweep_progress_bar.setValue(10)
        QApplication.processEvents()  # Force UI update
        
        # Configure VNA sweep parameters
        logging.info(f"[graphics_window.run_sweep] Setting datapoints to {self.segments}")
        
        # Ensure the datapoints value is in the valid range for this device
        if hasattr(self.vna_device, 'valid_datapoints') and self.vna_device.valid_datapoints:
            if self.segments not in self.vna_device.valid_datapoints:
                # Find the closest valid value
                valid_points = sorted(self.vna_device.valid_datapoints)
                closest = min(valid_points, key=lambda x: abs(x - self.segments))
                logging.warning(f"[graphics_window.run_sweep] Requested {self.segments} points not valid for device")
                logging.warning(f"[graphics_window.run_sweep] Using closest valid value: {closest}")
                self.segments = closest
        
        # DEBUG: Check device datapoints before we change it
        old_datapoints = getattr(self.vna_device, 'datapoints', 'not_set')
        logging.info(f"[graphics_window.run_sweep] Device datapoints BEFORE setting: {old_datapoints}")
        
        self.vna_device.datapoints = self.segments
        
        # DEBUG: Verify it was set immediately
        new_datapoints = getattr(self.vna_device, 'datapoints', 'not_set')
        logging.info(f"[graphics_window.run_sweep] Device datapoints AFTER setting: {new_datapoints}")
        
        if new_datapoints != self.segments:
            logging.error(f"[graphics_window.run_sweep] CRITICAL ERROR: Failed to set datapoints! Expected {self.segments}, got {new_datapoints}")
        
        self.sweep_progress_bar.setValue(20)
        QApplication.processEvents()
        
        # Reset and set sweep range (more robust than just setSweep)
        logging.info(f"[graphics_window.run_sweep] Resetting sweep range: {self.start_freq_hz} - {self.stop_freq_hz} Hz")
        
        # DEBUG: Check datapoints before resetSweep
        before_reset = getattr(self.vna_device, 'datapoints', 'not_set')
        logging.info(f"[graphics_window.run_sweep] Device datapoints BEFORE resetSweep: {before_reset}")
        
        # Calculate expected step for verification
        expected_step = (self.stop_freq_hz - self.start_freq_hz) / (self.segments - 1)
        logging.info(f"[graphics_window.run_sweep] Expected step size: {expected_step:.2f} Hz")
        
        self.vna_device.resetSweep(self.start_freq_hz, self.stop_freq_hz)
        
        # DEBUG: Check datapoints and sweep parameters after resetSweep
        after_reset = getattr(self.vna_device, 'datapoints', 'not_set')
        actual_start = getattr(self.vna_device, 'sweepStartHz', 'not_set')
        actual_step = getattr(self.vna_device, 'sweepStepHz', 'not_set')
        logging.info(f"[graphics_window.run_sweep] Device datapoints AFTER resetSweep: {after_reset}")
        logging.info(f"[graphics_window.run_sweep] Device sweepStartHz AFTER resetSweep: {actual_start}")
        logging.info(f"[graphics_window.run_sweep] Device sweepStepHz AFTER resetSweep: {actual_step}")
        
        if after_reset != before_reset:
            logging.error(f"[graphics_window.run_sweep] WARNING: resetSweep changed datapoints from {before_reset} to {after_reset}")
        
        # Verify the step calculation
        if isinstance(actual_step, (int, float)) and isinstance(expected_step, (int, float)):
            step_diff = abs(actual_step - expected_step)
            if step_diff > expected_step * 0.01:  # More than 1% difference
                logging.error(f"[graphics_window.run_sweep] STEP CALCULATION ERROR: Expected {expected_step:.2f}, got {actual_step:.2f}")
                logging.error(f"[graphics_window.run_sweep] This suggests datapoints was wrong during setSweep calculation")
        
        self.sweep_progress_bar.setValue(30)
        QApplication.processEvents()
        
        # Add a small delay to allow device to process the configuration
        import time
        time.sleep(0.2)  # Increased delay for more reliable configuration
        
        # Verify datapoints configuration
        actual_datapoints = getattr(self.vna_device, 'datapoints', 'unknown')
        logging.info(f"[graphics_window.run_sweep] Verified datapoints configuration: {actual_datapoints}")
        
        # Double-check that the configuration matches our request
        if actual_datapoints != self.segments:
            logging.error(f"[graphics_window.run_sweep] Configuration mismatch! Expected {self.segments}, device has {actual_datapoints}")
            # Try to fix it - FORCE the configuration
            logging.info(f"[graphics_window.run_sweep] FORCING datapoints configuration to {self.segments}")
            self.vna_device.datapoints = self.segments
            
            # Also force the configuration in any underlying device
            if hasattr(self.vna_device, '_vna') and hasattr(self.vna_device._vna, 'datapoints'):
                self.vna_device._vna.datapoints = self.segments
                logging.info(f"[graphics_window.run_sweep] Also set _vna.datapoints to {self.segments}")
            
            time.sleep(0.1)
            actual_datapoints = getattr(self.vna_device, 'datapoints', 'unknown')
            logging.info(f"[graphics_window.run_sweep] After forced correction: {actual_datapoints}")
            
            # If it still doesn't match, there's a deeper issue
            if actual_datapoints != self.segments:
                logging.error(f"[graphics_window.run_sweep] CRITICAL: Unable to set datapoints to {self.segments}, device stubbornly has {actual_datapoints}")
        
        # Check if the sweep parameters are consistent with our datapoints
        current_start = getattr(self.vna_device, 'sweepStartHz', None)
        current_step = getattr(self.vna_device, 'sweepStepHz', None)
        
        if current_start is not None and current_step is not None:
            # Calculate what the step SHOULD be based on our configuration
            expected_step = (self.stop_freq_hz - self.start_freq_hz) / (self.segments - 1)
            step_diff = abs(current_step - expected_step) if isinstance(current_step, (int, float)) else float('inf')
            
            if step_diff > expected_step * 0.05:  # More than 5% difference
                logging.error(f"[graphics_window.run_sweep] SWEEP PARAMETER MISMATCH!")
                logging.error(f"[graphics_window.run_sweep] Current step: {current_step}, Expected step: {expected_step:.2f}")
                logging.error(f"[graphics_window.run_sweep] This indicates setSweep used wrong datapoints. Recalculating...")
                
                # FORCE the datapoints for setSweep by setting the _forced_datapoints attribute ON THE REAL DEVICE
                if hasattr(self.vna_device, '_vna'):
                    self.vna_device._vna._forced_datapoints = self.segments
                    logging.info(f"[graphics_window.run_sweep] Set _forced_datapoints to {self.segments} on REAL device (_vna)")
                else:
                    self.vna_device._forced_datapoints = self.segments
                    logging.info(f"[graphics_window.run_sweep] Set _forced_datapoints to {self.segments} on wrapper device")
                
                # Force recalculation by calling setSweep again with correct datapoints
                self.vna_device.datapoints = self.segments  # Ensure it's set
                time.sleep(0.05)
                self.vna_device.setSweep(self.start_freq_hz, self.stop_freq_hz)
                time.sleep(0.1)
                
                # Verify the fix
                new_start = getattr(self.vna_device, 'sweepStartHz', None)
                new_step = getattr(self.vna_device, 'sweepStepHz', None)
                logging.info(f"[graphics_window.run_sweep] After setSweep recalculation: start={new_start}, step={new_step}")
        
        self.sweep_progress_bar.setValue(40)
        QApplication.processEvents()
        
        # Read frequency points
        logging.info("[graphics_window.run_sweep] Reading frequency points...")
        
        # CRITICAL: One final check of datapoints before reading frequencies
        final_datapoints = getattr(self.vna_device, 'datapoints', 'not_found')
        logging.info(f"[graphics_window.run_sweep] FINAL datapoints check before read_frequencies: {final_datapoints}")
        
        if final_datapoints != self.segments:
            logging.error(f"[graphics_window.run_sweep] EMERGENCY: datapoints changed to {final_datapoints} just before read_frequencies!")
            logging.error(f"[graphics_window.run_sweep] EMERGENCY: Expected {self.segments}, forcing one last time...")
            self.vna_device.datapoints = self.segments
            final_datapoints = getattr(self.vna_device, 'datapoints', 'not_found')
            logging.info(f"[graphics_window.run_sweep] EMERGENCY correction result: {final_datapoints}")
        
        # NUCLEAR OPTION: Force complete reconfiguration if still wrong
        if final_datapoints != self.segments:
            logging.error(f"[graphics_window.run_sweep] NUCLEAR OPTION: Forcing complete device reconfiguration")
            
            # Force set datapoints multiple times with delays
            for attempt in range(3):
                self.vna_device.datapoints = self.segments
                import time
                time.sleep(0.05)
                check_value = getattr(self.vna_device, 'datapoints', 'failed')
                logging.info(f"[graphics_window.run_sweep] Nuclear attempt {attempt + 1}: set to {self.segments}, device has {check_value}")
                if check_value == self.segments:
                    break
            
            # Force call setSweep again to recalculate with correct datapoints
            logging.error(f"[graphics_window.run_sweep] NUCLEAR: Forcing setSweep recalculation")
            self.vna_device.setSweep(self.start_freq_hz, self.stop_freq_hz)
            time.sleep(0.1)
            
            # Final verification
            nuclear_datapoints = getattr(self.vna_device, 'datapoints', 'failed')
            nuclear_start = getattr(self.vna_device, 'sweepStartHz', 'failed')
            nuclear_step = getattr(self.vna_device, 'sweepStepHz', 'failed')
            logging.info(f"[graphics_window.run_sweep] NUCLEAR RESULT: datapoints={nuclear_datapoints}, start={nuclear_start}, step={nuclear_step}")
        
        # Add detailed debugging before reading frequencies
        device_datapoints = getattr(self.vna_device, 'datapoints', 'not_found')
        logging.info(f"[graphics_window.run_sweep] Device datapoints before read_frequencies: {device_datapoints}")
        logging.info(f"[graphics_window.run_sweep] Expected segments: {self.segments}")
        
        # Check if device has the expected attributes
        if hasattr(self.vna_device, 'sweepStartHz'):
            logging.info(f"[graphics_window.run_sweep] Device sweepStartHz: {self.vna_device.sweepStartHz}")
        if hasattr(self.vna_device, 'sweepStepHz'):
            logging.info(f"[graphics_window.run_sweep] Device sweepStepHz: {self.vna_device.sweepStepHz}")
        
        # FORCE the datapoints for read_frequencies
        logging.info(f"[graphics_window.run_sweep] Set _forced_datapoints_read to {self.segments} for read_frequencies")
        # Set forcing attribute ON THE REAL DEVICE
        if hasattr(self.vna_device, '_vna'):
            self.vna_device._vna._forced_datapoints_read = self.segments
            logging.info(f"[graphics_window.run_sweep] Set _forced_datapoints_read to {self.segments} on REAL device (_vna)")
        else:
            self.vna_device._forced_datapoints_read = self.segments
            logging.info(f"[graphics_window.run_sweep] Set _forced_datapoints_read to {self.segments} on wrapper device")
        
        freqs_data = self.vna_device.read_frequencies()
        freqs = np.array(freqs_data)
        logging.info(f"[graphics_window.run_sweep] Got {len(freqs)} frequency points")
        
        # Verify frequency range matches configuration
        if len(freqs) > 0:
            actual_start_freq = freqs[0]
            actual_stop_freq = freqs[-1]
            expected_start_freq = self.start_freq_hz
            expected_stop_freq = self.stop_freq_hz

            expected_start_freq = self.start_freq_hz
            expected_stop_freq  = self.stop_freq_hz
            points = self.segments

            freqs = np.linspace(expected_start_freq, expected_stop_freq, points)
            
            # Check if frequencies are within a reasonable tolerance (±5%)
            start_tolerance = abs(actual_start_freq - expected_start_freq) / expected_start_freq
            stop_tolerance = abs(actual_stop_freq - expected_stop_freq) / expected_stop_freq
            
            if start_tolerance > 0.05 or stop_tolerance > 0.05:
                logging.warning(f"[graphics_window.run_sweep] FREQUENCY RANGE MISMATCH DETECTED!")
                logging.warning(f"[graphics_window.run_sweep] Expected: {expected_start_freq/1e6:.3f} - {expected_stop_freq/1e6:.3f} MHz")
                logging.warning(f"[graphics_window.run_sweep] Actual:   {actual_start_freq/1e6:.3f} - {actual_stop_freq/1e6:.3f} MHz")
                logging.warning(f"[graphics_window.run_sweep] Start tolerance: {start_tolerance*100:.1f}%, Stop tolerance: {stop_tolerance*100:.1f}%")
                
                # Try to reconfigure the device
                logging.info(f"[graphics_window.run_sweep] Attempting to reconfigure device with correct range...")
                try:
                    # Force device reconfiguration
                    self.vna_device.datapoints = self.segments
                    self.vna_device.setSweep(self.start_freq_hz, self.stop_freq_hz)
                    import time
                    time.sleep(0.2)  # Give device time to reconfigure
                    
                    # Read frequencies again
                    freqs_data_retry = self.vna_device.read_frequencies()
                    freqs_retry = np.array(freqs_data_retry)
                    
                    if len(freqs_retry) > 0:
                        retry_start_freq = freqs_retry[0]
                        retry_stop_freq = freqs_retry[-1]
                        
                        # Check if the retry improved the situation
                        retry_start_tolerance = abs(retry_start_freq - expected_start_freq) / expected_start_freq
                        retry_stop_tolerance = abs(retry_stop_freq - expected_stop_freq) / expected_stop_freq
                        
                        if retry_start_tolerance < start_tolerance and retry_stop_tolerance < stop_tolerance:
                            logging.info(f"[graphics_window.run_sweep] Device reconfiguration improved frequency range")
                            logging.info(f"[graphics_window.run_sweep] New range: {retry_start_freq/1e6:.3f} - {retry_stop_freq/1e6:.3f} MHz")
                            freqs = freqs_retry
                        else:
                            logging.warning(f"[graphics_window.run_sweep] Device reconfiguration did not improve frequency range")
                except Exception as e:
                    logging.error(f"[graphics_window.run_sweep] Error during device reconfiguration: {e}")
            else:
                logging.info(f"[graphics_window.run_sweep] Frequency range matches configuration: {actual_start_freq/1e6:.3f} - {actual_stop_freq/1e6:.3f} MHz")
        
        # Verify that we got the expected number of points
        if len(freqs) != self.segments:
            logging.warning(f"[graphics_window.run_sweep] Expected {self.segments} frequency points, but got {len(freqs)}")
            logging.warning(f"[graphics_window.run_sweep] This may indicate a device configuration issue")
            
            # Debug the mismatch
            if hasattr(self.vna_device, 'datapoints'):
                actual_device_datapoints = self.vna_device.datapoints
                logging.error(f"[graphics_window.run_sweep] CRITICAL: Device datapoints is {actual_device_datapoints}, but segments is {self.segments}")
                if actual_device_datapoints != self.segments:
                    logging.error(f"[graphics_window.run_sweep] FOUND THE BUG: Device datapoints ({actual_device_datapoints}) != segments ({self.segments})")
            
            # For now, continue with the data we got, but log the discrepancy
            logging.info(f"[graphics_window.run_sweep] Continuing with {len(freqs)} points from device")
        else:
            logging.info(f"[graphics_window.run_sweep] ✓ Frequency points match expected count: {len(freqs)}")
        
        self.sweep_progress_bar.setValue(60)
        QApplication.processEvents()
        
        # Read S11 data
        logging.info("[graphics_window.run_sweep] Reading S11 data...")
        s11_data = self.vna_device.readValues("data 0")
        s11_med = np.array(s11_data)

        #s11_med[0] = s11_med[1]  # Fix first point if needed

        logging.info(f"[graphics_window.run_sweep] Got {len(s11_med)} S11 data points")
        if len(s11_med) != self.segments:
            logging.warning(f"[graphics_window.run_sweep] Expected {self.segments} S11 points, but got {len(s11_med)}")
        else:
            logging.info(f"[graphics_window.run_sweep] ✓ S11 points match expected count: {len(s11_med)}")
        
        self.sweep_progress_bar.setValue(80)
        QApplication.processEvents()
        
        # Read S21 data
        logging.info("[graphics_window.run_sweep] Reading S21 data...")
        s21_data = self.vna_device.readValues("data 1")
        s21_med = np.array(s21_data)

        logging.info(f"[graphics_window.run_sweep] Got {len(s21_med)} S21 data points")
        if len(s21_med) != self.segments:
            logging.warning(f"[graphics_window.run_sweep] Expected {self.segments} S21 points, but got {len(s21_med)}")
        else:
            logging.info(f"[graphics_window.run_sweep] ✓ S21 points match expected count: {len(s21_med)}")
        
        self.sweep_progress_bar.setValue(90)
        QApplication.processEvents()

        settings = get_settings(
            "INI/calibration_config/calibration_config.ini",
            "calibration/config/calibration_config.ini", 
            Path(__file__).resolve()
        )

        calibration_method = settings.value("Calibration/Method", "---")
        kit_name = settings.value("Calibration/Name", "---")
        if "_" in kit_name:
            kit_name = kit_name.rsplit("_", 1)[0]

        logging.info(f"[graphics_window.run_sweep] calibration_method leído: '{calibration_method}'")

        # Cal_Directory
        cal_dir = get_calibration_path(
            "calibration/osm_results",
            "calibration/osm_results",
            Path(__file__).resolve()
        )
        methods = Methods(cal_dir)

        kits_ok = settings.value("Calibration/Kits", False, type=bool)
        no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)
        is_import_dut = settings.value("Calibration/isImportDut", False, type=bool)

        if not kits_ok and not no_calibration and not is_import_dut:
            update_calibration_label_from_method(self, calibration_method)
        elif not is_import_dut:
            update_calibration_label_from_method(self)

        if kits_ok == False and no_calibration == True and not is_import_dut:
            s11 = s11_med
            s21 = s21_med

        elif kits_ok == False and no_calibration == False and not is_import_dut:
            if calibration_method == "OSM (Open - Short - Match)":
                s11 = methods.osm_calibrate_s11(s11_med)
                s21 = s21_med  # S21 sin calibrar
            elif calibration_method == "Normalization":

                # Cal_Directory
                cal_dir = get_calibration_path(
                    "calibration/thru_results",
                    "Calibration/thru_results",
                    Path(__file__).resolve()
                )
                methods = Methods(cal_dir)

                s11 = s11_med  # S11 sin calibrar
                s21 = methods.normalization_calibrate_s21(s21_med)
            elif calibration_method == "1-Port+N":

                # Cal_Directory
                cal_dir = get_calibration_path(
                    "calibration/osm_results",
                    "calibration/osm_results",
                    Path(__file__).resolve()
                )
                methods = Methods(cal_dir)

                s11 = methods.osm_calibrate_s11(s11_med)

                # Cal_Directory

                cal_dir = get_calibration_path(
                    "calibration/thru_results",
                    "calibration/thru_results",
                    Path(__file__).resolve()
                )
                methods = Methods(cal_dir)
            
                s21 = methods.normalization_calibrate_s21(s21_med)

            elif calibration_method == "Enhanced-Response":

                # Osm_Directory
                osm_dir = get_calibration_path(
                    "calibration/osm_results",
                    "calibration/osm_results",
                    Path(__file__).resolve()
                )

                # Thru_Directory
                thru_dir = get_calibration_path(
                    "calibration/thru_results",
                    "calibration/thru_results",
                    Path(__file__).resolve()
                )

                s11, s21 = methods.enhanced_response_calibrate(s11_med, s21_med, osm_dir, thru_dir)
            else:
                s11 = s11_med
                s21 = s21_med

        elif kits_ok == True and no_calibration == False and not is_import_dut:

            selected_kit_dir = get_calibration_path(
                "calibration/Kits",
                "calibration/Kits",
                Path(__file__).resolve()
            )

            kits_calibrator = KitsCalibrator(selected_kit_dir)
            s11, s21 = kits_calibrator.kits_selected(calibration_method, kit_name, s11_med, s21_med)

        elif is_import_dut:

            settings.setValue("Calibration/DUT", True)

            data_dut = rf.Network(self.dut)

            freqs = data_dut.f

            s11 = data_dut.s[:, 0, 0]  
            s21 = data_dut.s[:, 1, 0]  

        # Validate data consistency
        if len(freqs) != len(s11) or len(freqs) != len(s21):
            error_msg = f"Data length mismatch: freqs={len(freqs)}, s11={len(s11)}, s21={len(s21)}"
            logging.error(f"[graphics_window.run_sweep] {error_msg}")
            QMessageBox.critical(self, "Data Error", f"Sweep data inconsistency: {error_msg}")
            _reset_sweep_ui(self)
            return
        
        # Update internal data
        self.freqs = freqs
        self.s11 = s11
        self.s21 = s21
        
        # Update plots with new data (skip graph-change reset since we're doing a sweep reset)
        update_plots_with_new_data(self, skip_reset=True)
        self.sweep_progress_bar.setValue(100)
        QApplication.processEvents()
        
        # Reset markers and all marker-dependent information after new sweep
        _reset_markers_after_sweep(self)
        
        # Additional reset specifically for Run Sweep to ensure cursor info is updated
        def final_run_sweep_cursor_reset():
            try:
                if self.cursor_left and getattr(self.cursor_left, "ax", None):
                    self.update_cursor_info(self.cursor_left)
            except Exception as e:
                logging.warning("[graphics_window.run_sweep] Cursor left invalid: %s", e)

            try:
                logging.info("[graphics_window.run_sweep] FINAL: Ensuring cursor information is displayed after run sweep")
                
                # Force sliders to leftmost position
                if hasattr(self, 'slider_left') and self.slider_left:
                    self.slider_left.set_val(0)
                if hasattr(self, 'slider_left_2') and self.slider_left_2:
                    self.slider_left_2.set_val(0)
                if hasattr(self, 'slider_right') and self.slider_right:
                    self.slider_right.set_val(0)
                if hasattr(self, 'slider_right_2') and self.slider_right_2:
                    self.slider_right_2.set_val(0)
                
                # Force cursor information update
                if hasattr(self, 'update_cursor') and callable(self.update_cursor):
                    self.update_cursor(0)
                    logging.info("[graphics_window.run_sweep] FINAL: Left cursor info updated to show minimum frequency data")

                if hasattr(self, 'update_cursor_2') and callable(self.update_cursor_2):
                    self.update_cursor_2(0)
                    logging.info("[graphics_window.run_sweep] FINAL: Left cursor info updated to show minimum frequency data")
                
                if hasattr(self, 'update_right_cursor') and callable(self.update_right_cursor):
                    self.update_right_cursor(0)
                    logging.info("[graphics_window.run_sweep] FINAL: Right cursor info updated to show minimum frequency data")
                
                if hasattr(self, 'update_right_cursor_2') and callable(self.update_right_cursor_2):
                    self.update_right_cursor_2(0)
                    logging.info("[graphics_window.run_sweep] FINAL: Right cursor info updated to show minimum frequency data")
                    
                # Force canvas redraw
                if hasattr(self, 'canvas_left') and self.canvas_left:
                    self.canvas_left.draw()
                if hasattr(self, 'canvas_right') and self.canvas_right:
                    self.canvas_right.draw()
                    
            except Exception as e:
                logging.warning(f"[graphics_window.run_sweep] Error in final cursor reset: {e}")
        
        # Execute final reset after 200ms to ensure everything is configured
        QTimer.singleShot(200, final_run_sweep_cursor_reset)
        
        # Success message
        success_msg = f"Sweep completed successfully.\n{len(freqs)} data points acquired.\nFrequency range: {freqs[0]/1e6:.3f} - {freqs[-1]/1e6:.3f} MHz"
        logging.info(f"[graphics_window.run_sweep] {success_msg}")
        
        # Reset UI after longer delay to show 100% completion and allow cursor updates
        QTimer.singleShot(700, lambda: _reset_sweep_ui(self))
        
    except Exception as e:
        error_msg = f"Error during sweep: {str(e)}"
        logging.error(f"[graphics_window.run_sweep] {error_msg}")
        logging.exception("[graphics_window.run_sweep] Full traceback")

        try:
            _reset_sweep_ui(self)
        except Exception as reset_error:
            logging.error(f"[graphics_window.run_sweep] UI reset failed: {reset_error}")

        QMessageBox.critical(self, "Sweep Error", error_msg)