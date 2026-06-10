import logging
import numpy as np

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
        QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QToolTip
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

# ------------------------------------------------------------------------------------------------------------------ #

def update_smith_chart(self, freqs, s11, standard_name):
    """Update Smith chart with measured calibration data."""
    from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import SmithChartManager
    
    if not hasattr(self, 'current_ax') or not self.current_ax:
        logging.warning("[CalibrationWizard] No Smith chart axis available")
        return
    
    # Use consolidated Smith chart functionality
    manager = SmithChartManager()
    manager.update_wizard_measurement(
        ax=self.current_ax,
        freqs=freqs,
        s11_data=s11,
        standard_name=standard_name,
        canvas=self.current_canvas
    )

def update_magnitude_chart(self, freqs, s21, standard_name):
    """Update Magnitude chart with measured calibration data."""
    from NanoVNA_UTN_Toolkit.utils.magnitude_chat_utils import MagnitudeChartManager
    
    if not hasattr(self, 'current_ax') or not self.current_ax:
        logging.warning("[CalibrationWizard] No Magnitude chart axis available")
        return

    # Use consolidated Magnitude chart functionality
    manager = MagnitudeChartManager()
    manager.update_wizard_measurement(
        ax=self.current_ax_magnitude,
        freqs=freqs,
        s21_data=s21,
        standard_name=standard_name,
        canvas=self.current_canvas_magnitude,
        in_dB=False  # Display in linear scale for calibration
        )

def update_calibration_status_display(self):
    """Update the calibration status display in the final step"""
    # Only update if we're in the final step and have the status widgets
    if hasattr(self, 'calibration_status_widgets') and self.osm_calibration:
        status = self.osm_calibration.get_completion_status()
        
        # Update each status widget
        for standard, widget in self.calibration_status_widgets.items():
            if standard in status:
                completed = status[standard]
                icon = "✓" if completed else "✗"
                color = "green" if completed else "red"
                status_text = 'Completed' if completed else 'Pending'
                widget.setText(f"{icon} {standard.upper()}: {status_text}")
                widget.setStyleSheet(f"font-size: 14px; color: {color}; margin-left: 10px;")

    if hasattr(self, 'calibration_status_widgets') and self.thru_calibration:
        status = self.thru_calibration.get_completion_status()

        # Update each status widget
        for standard, widget in self.calibration_status_widgets.items():
            if standard in status:
                completed = status[standard]
                icon = "✓" if completed else "✗"
                color = "green" if completed else "red"
                status_text = 'Completed' if completed else 'Pending'
                widget.setText(f"{icon} {standard.upper()}: {status_text}")
                widget.setStyleSheet(f"font-size: 14px; color: {color}; margin-left: 10px;")

    if hasattr(self, 'calibration_status_widgets') and hasattr(self, 'os_calibration') and self.os_calibration:
        status = self.os_calibration.get_completion_status()

        for standard, widget in self.calibration_status_widgets.items():
            if standard in status:
                completed = status[standard]
                icon = "✓" if completed else "✗"
                color = "green" if completed else "red"
                status_text = 'Completed' if completed else 'Pending'
                widget.setText(f"{icon} {standard.upper()}: {status_text}")
                widget.setStyleSheet(f"font-size: 14px; color: {color}; margin-left: 10px;")

def unit_multiplier(self, unit):
    return {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[unit]

def update_spinbox_range(self, spinbox, unit):
    """Actualiza el rango del spinbox según la unidad actual y los límites del dispositivo."""
    # Use device limits if available, otherwise fallback to defaults
    if hasattr(self, 'freq_min_hz') and hasattr(self, 'freq_max_hz'):
        # Convert device limits to the current unit
        min_freq_in_unit = self.freq_min_hz / unit_multiplier(self, unit)
        max_freq_in_unit = self.freq_max_hz / unit_multiplier(self, unit)
        
        # Set a more generous range that allows manual override but starts with device limits
        extended_min = min_freq_in_unit * 0.5  # Allow going 50% below device minimum
        extended_max = max_freq_in_unit * 1.5   # Allow going 50% above device maximum
        
        # Set the range with extended limits for manual override capability
        spinbox.setRange(extended_min, extended_max)
        
        # Update tooltip to show device-specific limits
        device_min_str = f"{self.freq_min_hz/1e6:.3f} MHz" if self.freq_min_hz >= 1e6 else f"{self.freq_min_hz/1e3:.1f} kHz"
        device_max_str = f"{self.freq_max_hz/1e9:.3f} GHz" if self.freq_max_hz >= 1e9 else f"{self.freq_max_hz/1e6:.1f} MHz"
        tooltip_text = f"Device range: {device_min_str} - {device_max_str}\nExtended range allows manual override"
        spinbox.setToolTip(tooltip_text)
        
        logging.info(f"[CalibrationWizard] Set {unit} range: {extended_min:.6f} - {extended_max:.6f} (device: {min_freq_in_unit:.6f} - {max_freq_in_unit:.6f})")
    else:
        # Fallback to hardcoded ranges if device limits not available
        if unit == "Hz":
            spinbox.setRange(50_000, 1_500_000_000)
        elif unit == "kHz":
            spinbox.setRange(50, 1_500_000)
        elif unit == "MHz":
            spinbox.setRange(0.05, 1500)
        elif unit == "GHz":
            spinbox.setRange(0.00005, 1.5)
        
        spinbox.setToolTip("Default frequency range: 50 kHz - 1.5 GHz")
        logging.info(f"[CalibrationWizard] Using default {unit} range (device limits not available)")

def get_sweep_start_frequency(self):
    """Get start frequency in Hz from instance variable"""
    return self.sweep_start_freq

def get_sweep_stop_frequency(self):
    """Get stop frequency in Hz from instance variable"""
    return self.sweep_stop_freq

def get_sweep_steps(self):
    """Get number of sweep steps from instance variable"""
    return self.sweep_steps

def update_device_limits(self):
    """Update step limits based on connected device"""
    try:
        # Try to get device from vna_device
        device = None
        if self.vna_device:
            device = self.vna_device
        elif hasattr(self, 'hardware') and self.hardware and hasattr(self.hardware, 'getDevice'):
            device = self.hardware.getDevice()
        
        if device and hasattr(device, 'valid_datapoints') and device.valid_datapoints:
            # Configure SmartDatapointsSpinBox with device-specific valid points
            self.steps_input.set_valid_datapoints(device.valid_datapoints)
            max_points = max(device.valid_datapoints)
            logging.info(f"[CalibrationWizard] Configured datapoints for device: {device.valid_datapoints}")
            self.steps_input.setToolTip(f"Valid datapoints for this device: {device.valid_datapoints}")
        else:
            # Default valid datapoints for generic VNA
            default_points = [11, 51, 101, 201, 301, 501, 1023]
            self.steps_input.set_valid_datapoints(default_points)
            logging.info(f"[CalibrationWizard] Using default datapoints: {default_points}")
            self.steps_input.setToolTip(f"Default valid datapoints: {default_points}")
            
    except Exception as e:
        logging.error(f"[CalibrationWizard] Error updating device limits: {e}")
        # Fallback to default
        default_points = [11, 51, 101, 201, 301, 501, 1023]
        self.steps_input.set_valid_datapoints(default_points)
        self.steps_input.setToolTip(f"Default valid datapoints: {default_points}")

def update_sweep_config(self):
    """Update sweep configuration from UI widgets to instance variables"""
    try:
        # Calculate start frequency in Hz
        start_value = self.start_freq_input.value()
        start_unit = self.start_freq_unit.currentText()
        multipliers = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
        self.sweep_start_freq = int(start_value * multipliers[start_unit])
        
        # Calculate stop frequency in Hz
        stop_value = self.stop_freq_input.value()
        print(f"esto vale siempre: {stop_value}")
        stop_unit = self.stop_freq_unit.currentText()
        self.sweep_stop_freq = int(stop_value * multipliers[stop_unit])
        
        # Get number of steps
        self.sweep_steps = self.steps_input.value()
        
        logging.info(f"[CalibrationWizard] Sweep config updated: {self.sweep_start_freq/1e6:.3f} - {self.sweep_stop_freq/1e6:.3f} MHz, {self.sweep_steps} points")
        
    except Exception as e:
        logging.error(f"[CalibrationWizard] Error updating sweep config: {e}")
        # Use default values on error
        self.sweep_start_freq = 50000  # 50 kHz
        self.sweep_stop_freq = 1500000000  # 1.5 GHz
        self.sweep_steps = 101

def perform_calibration_measurement(self, step, standard_name):
        """Perform sweep measurement for calibration standard."""
        logging.info(f"[CalibrationWizard] Starting measurement for {standard_name}")
        
        # Check if we have a device or need to simulate
        device_available = self.vna_device and hasattr(self.vna_device, 'connected')
        
        if not device_available:
            # No device available - show error instead of simulating
            error_msg = "No VNA device detected. Please connect a NanoVNA device before attempting calibration measurements."
            logging.error(f"[CalibrationWizard] {error_msg}")
            
            # Update status to show error
            self.status_label.setText("No VNA device connected!")
            self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: red;")
            
            # Show error dialog
            QMessageBox.critical(self, "VNA Device Required", 
                               f"{error_msg}\n\n"
                               "Calibration requires a connected NanoVNA device to perform real measurements.\n"
                               "Please:\n"
                               "1. Connect your NanoVNA device\n"
                               "2. Ensure drivers are installed\n"
                               "3. Check the connection and try again")
            return
        
        
        # Real device measurement
        if not self.vna_device.connected():
            logging.warning("[CalibrationWizard] Device not connected, attempting to connect...")
            try:
                self.vna_device.connect()
                if not self.vna_device.connected():
                    QMessageBox.warning(self, "Connection Failed", "Could not connect to VNA device.")
                    return
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", f"Failed to connect: {str(e)}")
                return

        # Display name for status messages — Open/Short Normalization shows "Open/Short" instead of "OPEN"
        if getattr(self, 'selected_method', None) == "Open/Short Normalization" and standard_name in ("OPEN", "SHORT"):
            display_name = "Open/Short"
        else:
            display_name = standard_name

        try:
            # Update status
            self.status_label.setText(f"Measuring {display_name}...")
            self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: orange;")
            QApplication.processEvents()
            
            # Get sweep configuration from user settings
            start_freq = self.get_sweep_start_frequency()
            stop_freq = self.get_sweep_stop_frequency()
            num_points = self.get_sweep_steps()
            
            # Validate and constrain values against device limits if available
            if hasattr(self.vna_device, 'sweep_max_freq_hz'):
                if stop_freq > self.vna_device.sweep_max_freq_hz:
                    stop_freq = self.vna_device.sweep_max_freq_hz
                    logging.warning(f"[CalibrationWizard] Stop frequency limited to device max: {stop_freq/1e6:.3f} MHz")
            
            # Check device limits for sweep points
            device_max_points = None
            if hasattr(self.vna_device, 'valid_datapoints') and self.vna_device.valid_datapoints:
                device_max_points = max(self.vna_device.valid_datapoints)
                logging.info(f"[CalibrationWizard] Using max from valid_datapoints: {device_max_points}")
            elif hasattr(self.vna_device, 'sweep_points_max'):
                device_max_points = self.vna_device.sweep_points_max
                logging.info(f"[CalibrationWizard] Using sweep_points_max: {device_max_points}")
            
            if device_max_points and num_points > device_max_points:
                num_points = device_max_points
                logging.warning(f"[CalibrationWizard] Number of points limited to device max: {num_points}")
            
            logging.info(f"[CalibrationWizard] User Sweep config: {start_freq/1e6:.3f} - {stop_freq/1e6:.3f} MHz, {num_points} points")
            
            # Configure sweep with datapoints verification
            logging.info(f"[CalibrationWizard] Setting device datapoints to {num_points}")
            self.vna_device.datapoints = num_points
            
            # Verify datapoints were set correctly
            actual_datapoints = getattr(self.vna_device, 'datapoints', 'unknown')
            logging.info(f"[CalibrationWizard] Device datapoints after setting: {actual_datapoints}")
            
            if hasattr(self.vna_device, '_vna'):
                actual_real_datapoints = getattr(self.vna_device._vna, 'datapoints', 'unknown')
                logging.info(f"[CalibrationWizard] Real device (_vna) datapoints: {actual_real_datapoints}")
            
            # Configure sweep
            self.vna_device.setSweep(start_freq, stop_freq)
            
            # Final verification after setSweep
            final_datapoints = getattr(self.vna_device, 'datapoints', 'unknown')
            logging.info(f"[CalibrationWizard] Device datapoints after setSweep: {final_datapoints}")
            
            if final_datapoints != num_points:
                logging.warning(f"[CalibrationWizard] Datapoints mismatch! Expected {num_points}, got {final_datapoints}")
            else:
                logging.info(f"[CalibrationWizard] Datapoints correctly configured: {final_datapoints}")
            
            # Perform measurements
            logging.info(f"[CalibrationWizard] Reading frequencies...")
            freqs_data = self.vna_device.read_frequencies()
            freqs = np.array(freqs_data)
            
            logging.info(f"[CalibrationWizard] Reading S11 data...")
            s11_data = self.vna_device.readValues("data 0")
            s11 = np.array(s11_data)
            
            logging.info(f"[CalibrationWizard] Got {len(freqs)} frequency points and {len(s11)} S11 points")
            
            # Verify that we got the expected number of points
            if len(freqs) != num_points:
                logging.warning(f"[CalibrationWizard] Frequency points mismatch! Expected {num_points}, got {len(freqs)}")
            if len(s11) != num_points:
                logging.warning(f"[CalibrationWizard] S11 points mismatch! Expected {num_points}, got {len(s11)}")
            
            if len(freqs) == num_points and len(s11) == num_points:
                logging.info(f"[CalibrationWizard] All data points match expected count: {num_points}")
            else:
                logging.error(f"[CalibrationWizard] Data count mismatch - this may indicate datapoints configuration issues")

            if standard_name == "OPEN" or standard_name == "SHORT" or standard_name == "MATCH":

                if getattr(self, 'selected_method', None) == "Open/Short Normalization" and standard_name in ("OPEN", "SHORT"):
                    # Route to Open/Short Normalization calibration manager
                    if hasattr(self, 'os_calibration') and self.os_calibration:
                        standard_key = standard_name.lower()
                        self.os_calibration.set_measurement(standard_key, freqs, s11)
                        status = self.os_calibration.get_completion_status()
                        logging.info(f"[CalibrationWizard] Open/Short calibration status: {status}")
                        update_calibration_status_display(self)
                        self.status_label.setText(f"{display_name} measurement complete")
                        self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")
                else:
                    # Route to OSM calibration manager
                    if self.osm_calibration:
                        if standard_name == "OPEN":
                            self.osm_calibration.set_measurement("open", freqs, s11)
                        elif standard_name == "SHORT":
                            self.osm_calibration.set_measurement("short", freqs, s11)
                        elif standard_name == "MATCH":
                            self.osm_calibration.set_measurement("match", freqs, s11)

                        status = self.osm_calibration.get_completion_status()
                        logging.info(f"[CalibrationWizard] Calibration status: {status}")
                        update_calibration_status_display(self)
                        self.status_label.setText(f"{display_name} measurement complete")
                        self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")

                # Update Smith chart with measured data
                update_smith_chart(self, freqs, s11, standard_name)

                # Update status
                self.status_label.setText(f"{display_name} measured successfully!")
                self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")

                logging.info(f"[CalibrationWizard] Measurement for {display_name} completed successfully")

            elif standard_name == "THRU":
                logging.info(f"[CalibrationWizard] Reading S11 data for THRU...")
                s11_data = self.vna_device.readValues("data 0")
                s11 = np.array(s11_data)
                
                logging.info(f"[CalibrationWizard] Reading S21 data for THRU...")
                s21_data = self.vna_device.readValues("data 1")
                logging.info(f"[CalibrationWizard] Reading S21 data for THRU...")
                s21_data = self.vna_device.readValues("data 1")

                logging.info(f"[RAW S21] TYPE: {type(s21_data)}")

                try:
                    logging.info(f"[RAW S21] LEN: {len(s21_data)}")
                except Exception as e:
                    logging.error(f"[RAW S21] LEN ERROR: {e}")

                logging.info(f"[RAW S21] FIRST 10: {s21_data[:10]}")

                if len(s21_data) > 0:
                    logging.info(f"[RAW S21] FIRST ELEMENT TYPE: {type(s21_data[0])}")
                    logging.info(f"[RAW S21] FIRST ELEMENT: {s21_data[0]}")

                s21 = np.array(s21_data)

                logging.info(f"[CalibrationWizard] Got {len(freqs)} freq, {len(s11)} S11, and {len(s21)} S21 points")
                
                # Verify that we got the expected number of points for THRU
                if len(s11) != num_points:
                    logging.warning(f"[CalibrationWizard] THRU S11 points mismatch! Expected {num_points}, got {len(s11)}")
                if len(s21) != num_points:
                    logging.warning(f"[CalibrationWizard] THRU S21 points mismatch! Expected {num_points}, got {len(s21)}")
                
                if len(freqs) == num_points and len(s11) == num_points and len(s21) == num_points:
                    logging.info(f"[CalibrationWizard] All THRU data points match expected count: {num_points}")
                else:
                    logging.error(f"[CalibrationWizard] THRU data count mismatch - this may indicate datapoints configuration issues")

                # Save data in calibration structure
                if self.thru_calibration:
                    if standard_name == "THRU":
                        self.thru_calibration.set_measurement("thru", freqs, s11, s21)
                    
                    # Show completion status
                    status = self.thru_calibration.get_completion_status()
                    logging.info(f"[CalibrationWizard] Calibration status: {status}")
                    
                    # Update the status display immediately after measurement
                    update_calibration_status_display(self)
                    
                    # Update UI state after measurement
                    self.status_label.setText(f"{standard_name} measurement complete")
                    self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")

                # Update Magnitude chart with measured data
                update_magnitude_chart(self, freqs, s21, standard_name)
                
                # Update status
                self.status_label.setText(f"{standard_name} measured successfully!")
                self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")
                
                logging.info(f"[CalibrationWizard] Measurement for {standard_name} completed successfully")
            
        except Exception as e:
            error_msg = f"Error during measurement: {str(e)}"
            logging.error(f"[CalibrationWizard] {error_msg}")
            QMessageBox.critical(self, "Measurement Error", error_msg)
            self.status_label.setText("Measurement failed!")
            self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: red;")

        # Enable Next button after successful measurement
        self.next_button.setEnabled(True)
        logging.info(f"[CalibrationWizard] Next step unlocked after {standard_name} measurement")
