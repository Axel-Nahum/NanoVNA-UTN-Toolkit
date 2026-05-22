import logging
import sys

from PySide6.QtWidgets import QToolTip

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.wizard_cal_windows.wizard_cal_utils.sweep_cal import update_spinbox_range, unit_multiplier
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------ #

def get_frequency_limits(self):
    """Get frequency limits from VNA device or use defaults."""
    default_min_hz = 50000      # 50 kHz default minimum
    default_max_hz = 1500000000 # 1.5 GHz default maximum
    
    logging.info("[CalibrationWizard] Getting frequency limits")
    
    if self.vna_device:
        device_type = type(self.vna_device).__name__
        logging.info(f"[CalibrationWizard] Checking device {device_type} for frequency limits")
        
        try:
            # Check for device-specific frequency limits
            min_freq_hz = getattr(self.vna_device, 'sweep_min_freq_hz', None)
            max_freq_hz = getattr(self.vna_device, 'sweep_max_freq_hz', None)
            
            # Handle wrapped devices (like PatchedVNA)
            if hasattr(self.vna_device, '_vna'):
                real_device = self.vna_device._vna
                min_freq_hz = min_freq_hz or getattr(real_device, 'sweep_min_freq_hz', None)
                max_freq_hz = max_freq_hz or getattr(real_device, 'sweep_max_freq_hz', None)
            
            if min_freq_hz is not None and max_freq_hz is not None:
                logging.info(f"[CalibrationWizard] Device frequency limits: {min_freq_hz/1e6:.3f} - {max_freq_hz/1e6:.3f} MHz")
                return int(min_freq_hz), int(max_freq_hz)
            else:
                logging.warning(f"[CalibrationWizard] Device {device_type} has no frequency limit attributes")
                
        except (AttributeError, ValueError, TypeError) as e:
            logging.error(f"[CalibrationWizard] Error getting device frequency limits: {e}")
    else:
        logging.warning("[CalibrationWizard] No VNA device available")
    
    # Fallback to defaults if no device or device doesn't have limits
    logging.info(f"[CalibrationWizard] Using default frequency limits: {default_min_hz/1e6:.3f} - {default_max_hz/1e6:.3f} MHz")
    return default_min_hz, default_max_hz

def update_frequency_ranges(self):
    """Update frequency spinbox ranges based on device limits."""
    try:
        # Update start frequency range
        start_unit = self.start_freq_unit.currentText()
        update_spinbox_range(self, self.start_freq_input, start_unit)
        
        # Update stop frequency range
        stop_unit = self.stop_freq_unit.currentText()
        update_spinbox_range(self, self.stop_freq_input, stop_unit)
        
        logging.info(f"[CalibrationWizard] Updated frequency ranges for device limits: {self.freq_min_hz/1e6:.3f} - {self.freq_max_hz/1e6:.3f} MHz")
        
    except Exception as e:
        logging.error(f"[CalibrationWizard] Error updating frequency ranges: {e}")
        # Use default behavior on error
        pass

def on_frequency_changed_range(self):
    start_val_hz = self.start_freq_input.value() * unit_multiplier(self, self.start_freq_unit.currentText())
    stop_val_hz  = self.stop_freq_input.value()  * unit_multiplier(self, self.stop_freq_unit.currentText())

    print(f"Start Frequency: {self.start_freq_input.value()}")
    print(f"Stop Frequency: {self.stop_freq_input.value()}")

    # Use device limits if available, otherwise fallback to defaults
    if hasattr(self, 'freq_min_hz') and hasattr(self, 'freq_max_hz'):
        # Create dynamic frequency range strings for tooltips
        device_min_str = f"{self.freq_min_hz/1e6:.3f} MHz" if self.freq_min_hz >= 1e6 else f"{self.freq_min_hz/1e3:.1f} kHz"
        device_max_str = f"{self.freq_max_hz/1e9:.3f} GHz" if self.freq_max_hz >= 1e9 else f"{self.freq_max_hz/1e6:.1f} MHz"
        
        # Allow some flexibility beyond device limits but warn if way outside device range
        extended_min = self.freq_min_hz * 0.5  # 50% below device minimum
        extended_max = self.freq_max_hz * 1.5  # 50% above device maximum

        # Start Frequency check with device-aware limits
        if not (extended_min <= start_val_hz <= extended_max):
            self.start_freq_input.blockSignals(True)
            self.start_freq_input.setValue(self.last_start_value)
            self.start_freq_input.blockSignals(False)
            QToolTip.showText(
                self.start_freq_input.mapToGlobal(self.start_freq_input.rect().topRight()),
                f"Start frequency should be within device range: {device_min_str} - {device_max_str}\n"
                f"Extended range allows manual override but may not work optimally"
            )
        else:
            self.last_start_value = self.start_freq_input.value()

        # Stop Frequency check with device-aware limits  
        if not (extended_min <= stop_val_hz <= extended_max):
            self.stop_freq_input.blockSignals(True)
            self.stop_freq_input.setValue(self.last_stop_value)
            self.stop_freq_input.blockSignals(False)
            QToolTip.showText(
                self.stop_freq_input.mapToGlobal(self.stop_freq_input.rect().topRight()),
                f"Stop frequency should be within device range: {device_min_str} - {device_max_str}\n"
                f"Extended range allows manual override but may not work optimally"
            )
        else:
            self.last_stop_value = self.stop_freq_input.value()
    else:
        # Fallback to hardcoded ranges if device limits not available
        # Start Frequency check
        if not (50_000 <= start_val_hz <= 1_500_000_000):
            self.start_freq_input.blockSignals(True)
            self.start_freq_input.setValue(self.last_start_value)
            self.start_freq_input.blockSignals(False)
            QToolTip.showText(
                self.start_freq_input.mapToGlobal(self.start_freq_input.rect().topRight()),
                "Start frequency must be between 50 kHz and 1.5 GHz"
            )
        else:
            self.last_start_value = self.start_freq_input.value()

        # Stop Frequency check
        if not (50_000 <= stop_val_hz <= 1_500_000_000):
            self.stop_freq_input.blockSignals(True)
            self.stop_freq_input.setValue(self.last_stop_value)
            self.stop_freq_input.blockSignals(False)
            QToolTip.showText(
                self.stop_freq_input.mapToGlobal(self.stop_freq_input.rect().topRight()),
                "Stop frequency must be between 50 kHz and 1.5 GHz"
            )
        else:
            self.last_stop_value = self.stop_freq_input.value()