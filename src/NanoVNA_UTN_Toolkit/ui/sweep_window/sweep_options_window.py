"""
Sweep Options window for NanoVNA devices.
Allows configuration of frequency start/stop, segments, and displays calculated values.
"""
import os
import sys
import logging
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QHBoxLayout, QGroupBox, 
    QSpinBox, QDoubleSpinBox, QFormLayout,
    QApplication, QMessageBox, QComboBox, QToolTip
)
from PySide6.QtGui import QIcon, QValidator

from pathlib import Path

try:
    from NanoVNA_UTN_Toolkit.ui.utils.sweep_utils.sweep_utils import load_sweep_configuration
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# Import dark-light mode toggle function with error handling to log issues without crashing the application

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)


from NanoVNA_UTN_Toolkit.ui.graphics_window import NanoVNAGraphics

# -------------------------------------------------------------------------------------------------------------------------------- #

class SmartDatapointsSpinBox(QSpinBox):
    """
    Custom SpinBox that jumps between valid datapoints instead of incrementing by 1.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.valid_datapoints = [11, 51, 101, 201, 301, 501, 1023]  # Default values
        # Don't call setSingleStep here to avoid triggering validate before setup is complete
        
    def set_valid_datapoints(self, valid_points):
        """Set the valid datapoints for this device."""
        if valid_points and len(valid_points) > 0:
            self.valid_datapoints = sorted(list(valid_points))
            self.setMinimum(min(self.valid_datapoints))
            self.setMaximum(max(self.valid_datapoints))
            self.setSingleStep(1)  # Set after valid_datapoints is configured
            logging.info(f"[SmartDatapointsSpinBox] Set valid datapoints: {self.valid_datapoints}")
        
    def stepBy(self, steps):
        """Override stepBy to jump between valid datapoints."""
        current_value = self.value()
        
        try:
            # Find current position in valid_datapoints
            if current_value in self.valid_datapoints:
                current_index = self.valid_datapoints.index(current_value)
            else:
                # Find closest valid datapoint
                current_index = 0
                min_diff = float('inf')
                for i, point in enumerate(self.valid_datapoints):
                    diff = abs(point - current_value)
                    if diff < min_diff:
                        min_diff = diff
                        current_index = i
            
            # Calculate new index
            new_index = current_index + steps
            
            # Clamp to valid range
            new_index = max(0, min(new_index, len(self.valid_datapoints) - 1))
            
            # Set new value
            new_value = self.valid_datapoints[new_index]
            logging.info(f"[SmartDatapointsSpinBox] Stepping from {current_value} to {new_value} (index {current_index} -> {new_index})")
            self.setValue(new_value)
            
        except Exception as e:
            logging.error(f"[SmartDatapointsSpinBox] Error in stepBy: {e}")
            # Fallback to normal behavior
            super().stepBy(steps)
    
    def textFromValue(self, value):
        """Override to ensure we display valid values."""
        if value in self.valid_datapoints:
            return f"{value}"
        else:
            # Find closest valid value and use that for display
            closest = min(self.valid_datapoints, key=lambda x: abs(x - value))
            return f"{closest}"
    
    def valueFromText(self, text):
        """Override to snap to valid values when user types."""
        try:
            typed_value = int(text.replace(" steps", "").strip())
            # Find closest valid datapoint
            closest = min(self.valid_datapoints, key=lambda x: abs(x - typed_value))
            logging.info(f"[SmartDatapointsSpinBox] User typed {typed_value}, snapping to {closest}")
            return closest
        except ValueError:
            return self.value()
    
    def validate(self, text, pos):
        """Override validation to be more lenient during typing."""
        # Allow partial numbers during typing
        if text.replace(" steps", "").strip().isdigit() or text == "":
            return (QValidator.State.Acceptable, text, pos)
        return (QValidator.State.Invalid, text, pos)

# ---------------------------------------------------------------------------------------------------------------- #

class SweepOptionsWindow(QMainWindow):
    def __init__(self, parent: NanoVNAGraphics, vna_device=None):
        super().__init__(parent)

#------------------------------------------------------------------------------------------------------------------------------------------

        # Dark-Light mode settings

        dark_light_config(self)

#------------------------------------------------------------------------------------------------------------------------------------------

        self.last_start_value = 50   
        self.last_stop_value  = 1.5 

        self.main_window = parent

        # Store VNA device reference
        self.vna_device = vna_device
        
        # Log sweep options window initialization
        logging.info("[sweep_options_window.__init__] Initializing sweep options window")
        if vna_device:
            device_type = type(vna_device).__name__
            logging.info(f"[sweep_options_window.__init__] VNA device provided: {device_type}")
            if hasattr(vna_device, 'sweep_points_min') and hasattr(vna_device, 'sweep_points_max'):
                logging.info(f"[sweep_options_window.__init__] Device sweep limits: {vna_device.sweep_points_min} to {vna_device.sweep_points_max}")
            else:
                logging.warning(f"[sweep_options_window.__init__] Device {device_type} has no sweep_points_min/max attributes")
                logging.warning(f"[sweep_options_window.__init__] Available device attributes: {[attr for attr in dir(vna_device) if not attr.startswith('_')][:10]}...")
        else:
            logging.warning("[sweep_options_window.__init__] No VNA device provided - using default limits")
        
        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")
            self.config_path = os.path.join(
                appdata,
                "NanoVNA-UTN-Toolkit",
                "INI",
                "sweep_config",
                "config.ini"
            )
            self.config_path = os.path.normpath(self.config_path)
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            os.makedirs(ui_dir, exist_ok=True)
            self.config_path = os.path.join(ui_dir, "sweep_window", "config", "config.ini")
            self.config_path = os.path.normpath(self.config_path)
        
        self.settings = QSettings(self.config_path, QSettings.Format.IniFormat)
        
        # Load maximum frequency limit from config
        self.max_frequency_hz = self.load_max_frequency()
        
        # Get sweep points limits from VNA device
        self.sweep_points_min, self.sweep_points_max = self.get_sweep_points_limits()
        
        # Get frequency limits from VNA device
        self.freq_min_hz, self.freq_max_hz = self.get_frequency_limits()
        
        # Store original values for cancel functionality
        self.original_values = {}
        
        # Flag to prevent auto-saving during initialization
        self._loading_settings = True
        
        self.init_ui(parent)
        self.load_settings()
        
        # Enable auto-saving after initialization is complete
        self._loading_settings = False
        
        self.store_original_values()  # Store values after loading
        self.calculate_derived_values()
        
    def load_max_frequency(self):
        """Load maximum frequency limit from config.ini file."""
        default_max_freq = 6e9  # 6 GHz default
        max_freq_val = self.settings.value("Limits/MaxFrequencyHz", default_max_freq)
        try:
            return float(str(max_freq_val)) if max_freq_val is not None else default_max_freq
        except (ValueError, TypeError):
            return default_max_freq
            
    def get_sweep_points_limits(self):
        """Get sweep points min and max from VNA device or use defaults."""
        default_min = 11
        default_max = 1001
        
        logging.info("[sweep_options_window.get_sweep_points_limits] Getting sweep points limits")
        
        if self.vna_device:
            device_type = type(self.vna_device).__name__
            logging.info(f"[sweep_options_window.get_sweep_points_limits] Checking device {device_type} for limits")
            
            try:
                # Try to get limits from the connected VNA device
                if hasattr(self.vna_device, 'sweep_points_min'):
                    sweep_min = getattr(self.vna_device, 'sweep_points_min', default_min)
                    logging.info(f"[sweep_options_window.get_sweep_points_limits] Device min found: {sweep_min}")
                else:
                    sweep_min = default_min
                    logging.warning(f"[sweep_options_window.get_sweep_points_limits] Device has no sweep_points_min, using default: {default_min}")
                    
                if hasattr(self.vna_device, 'sweep_points_max'):
                    sweep_max = getattr(self.vna_device, 'sweep_points_max', default_max)
                    logging.info(f"[sweep_options_window.get_sweep_points_limits] Device max found: {sweep_max}")
                else:
                    sweep_max = default_max
                    logging.warning(f"[sweep_options_window.get_sweep_points_limits] Device has no sweep_points_max, using default: {default_max}")
                
                # Check if device has valid_datapoints and use the maximum from there if available
                if hasattr(self.vna_device, 'valid_datapoints') and self.vna_device.valid_datapoints:
                    max_from_valid_datapoints = max(self.vna_device.valid_datapoints)
                    # Use the higher value between sweep_points_max and max(valid_datapoints)
                    if max_from_valid_datapoints > sweep_max:
                        sweep_max = max_from_valid_datapoints
                        logging.info(f"[sweep_options_window.get_sweep_points_limits] Using max from valid_datapoints: {sweep_max}")
                
                logging.info(f"[sweep_options_window.get_sweep_points_limits] Final device limits: {sweep_min} - {sweep_max}")
                return int(sweep_min), int(sweep_max)
            except (AttributeError, ValueError, TypeError) as e:
                logging.error(f"[sweep_options_window.get_sweep_points_limits] Error getting device limits: {e}")
        else:
            logging.warning("[sweep_options_window.get_sweep_points_limits] No VNA device available")
        
        # Fallback to defaults if no device or device doesn't have limits
        logging.info(f"[sweep_options_window.get_sweep_points_limits] Using default limits: {default_min} - {default_max}")
        return default_min, default_max

    def get_frequency_limits(self):
        """Get frequency limits from VNA device or use defaults."""
        default_min_hz = 50000      # 50 kHz default minimum
        default_max_hz = 1500000000 # 1.5 GHz default maximum
        
        logging.info("[sweep_options_window.get_frequency_limits] Getting frequency limits")
        
        if self.vna_device:
            device_type = type(self.vna_device).__name__
            logging.info(f"[sweep_options_window.get_frequency_limits] Checking device {device_type} for frequency limits")
            
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
                    logging.info(f"[sweep_options_window.get_frequency_limits] Device frequency limits: {min_freq_hz/1e6:.3f} - {max_freq_hz/1e6:.3f} MHz")
                    return int(min_freq_hz), int(max_freq_hz)
                else:
                    logging.warning(f"[sweep_options_window.get_frequency_limits] Device {device_type} has no frequency limit attributes")
                    
            except (AttributeError, ValueError, TypeError) as e:
                logging.error(f"[sweep_options_window.get_frequency_limits] Error getting device frequency limits: {e}")
        else:
            logging.warning("[sweep_options_window.get_frequency_limits] No VNA device available")
        
        # Fallback to defaults if no device or device doesn't have limits
        logging.info(f"[sweep_options_window.get_frequency_limits] Using default frequency limits: {default_min_hz/1e6:.3f} - {default_max_hz/1e6:.3f} MHz")
        return default_min_hz, default_max_hz

    def on_frequency_changed_range(self):
        start_val_hz = self.start_freq_edit.value() * self.unit_multiplier(self.start_freq_unit.currentText())
        stop_val_hz = self.stop_freq_edit.value() * self.unit_multiplier(self.stop_freq_unit.currentText())

        # Create dynamic frequency range strings for tooltips
        device_min_str = f"{self.freq_min_hz/1e6:.3f} MHz" if self.freq_min_hz >= 1e6 else f"{self.freq_min_hz/1e3:.1f} kHz"
        device_max_str = f"{self.freq_max_hz/1e9:.3f} GHz" if self.freq_max_hz >= 1e9 else f"{self.freq_max_hz/1e6:.1f} MHz"
        
        # Allow some flexibility beyond device limits but warn if way outside device range
        extended_min = self.freq_min_hz * 0.5  # 50% below device minimum
        extended_max = self.freq_max_hz * 1.5  # 50% above device maximum

        # Start Frequency check with device-aware limits
        if not (extended_min <= start_val_hz <= extended_max):
            self.start_freq_edit.blockSignals(True)
            self.start_freq_edit.setValue(self.last_start_value)
            self.start_freq_edit.blockSignals(False)
            QToolTip.showText(
                self.start_freq_edit.mapToGlobal(self.start_freq_edit.rect().topRight()),
                f"Start frequency should be within device range: {device_min_str} - {device_max_str}\n"
                f"Extended range allows manual override but may not work optimally"
            )
        else:
            self.last_start_value = self.start_freq_edit.value()
            
            # Warn if outside optimal device range but within extended range
            if not (self.freq_min_hz <= start_val_hz <= self.freq_max_hz):
                current_freq_str = f"{start_val_hz/1e6:.3f} MHz" if start_val_hz >= 1e6 else f"{start_val_hz/1e3:.1f} kHz"
                logging.warning(f"[sweep_options_window] Start frequency {current_freq_str} is outside optimal device range {device_min_str} - {device_max_str}")

        # Stop Frequency check with device-aware limits
        if not (extended_min <= stop_val_hz <= extended_max):
            self.stop_freq_edit.blockSignals(True)
            self.stop_freq_edit.setValue(self.last_stop_value)
            self.stop_freq_edit.blockSignals(False)
            QToolTip.showText(
                self.stop_freq_edit.mapToGlobal(self.stop_freq_edit.rect().topRight()),
                f"Stop frequency should be within device range: {device_min_str} - {device_max_str}\n"
                f"Extended range allows manual override but may not work optimally"
            )
        else:
            self.last_stop_value = self.stop_freq_edit.value()
            
            # Warn if outside optimal device range but within extended range  
            if not (self.freq_min_hz <= stop_val_hz <= self.freq_max_hz):
                current_freq_str = f"{stop_val_hz/1e6:.3f} MHz" if stop_val_hz >= 1e6 else f"{stop_val_hz/1e3:.1f} kHz"
                logging.warning(f"[sweep_options_window] Stop frequency {current_freq_str} is outside optimal device range {device_min_str} - {device_max_str}")

    def update_spinbox_range(self, spinbox, unit):
        """Actualiza el rango del spinbox según la unidad actual y los límites del dispositivo."""
        # Convert device limits to the current unit
        min_freq_in_unit = self.freq_min_hz / self.unit_multiplier(unit)
        max_freq_in_unit = self.freq_max_hz / self.unit_multiplier(unit)
        
        # Set a more conservative range that allows some manual override
        extended_min = min_freq_in_unit * 0.5  # Allow going 50% below device minimum
        extended_max = max_freq_in_unit * 1.5  # Allow going 50% above device maximum
        
        # Set the range with extended limits for manual override capability
        spinbox.setRange(extended_min, extended_max)
        
        # Log the configuration for debugging
        logging.info(f"[sweep_options_window.update_spinbox_range] Unit: {unit}")
        logging.info(f"[sweep_options_window.update_spinbox_range] Device limits: {min_freq_in_unit:.6f} - {max_freq_in_unit:.6f} {unit}")
        logging.info(f"[sweep_options_window.update_spinbox_range] Extended range: {extended_min:.6f} - {extended_max:.6f} {unit}")
        
        # Update tooltip to show device-specific limits
        device_min_str = f"{self.freq_min_hz/1e6:.3f} MHz" if self.freq_min_hz >= 1e6 else f"{self.freq_min_hz/1e3:.1f} kHz"
        device_max_str = f"{self.freq_max_hz/1e9:.3f} GHz" if self.freq_max_hz >= 1e9 else f"{self.freq_max_hz/1e6:.1f} MHz"
        tooltip_text = f"Device range: {device_min_str} - {device_max_str}\nExtended range allows manual override"
        spinbox.setToolTip(tooltip_text)

    def unit_multiplier(self, unit):
        return {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[unit]

    def init_ui(self, parent):
        """Initialize the user interface."""
        self.setWindowTitle("NanoVNA UTN Toolkit - Sweep Options")
        self.setGeometry(200, 200, 400, 300)
        
        # Try to set application icon
        if getattr(sys, 'frozen', False):
            # ---- MODO EXE ----
            base_path = sys._MEIPASS
            icon_path = os.path.join(base_path, 'icon.ico')

            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                logging.getLogger(__name__).warning(f"icon.ico not found in exe: {icon_path}")

        else:
            # ---- MODO PYTHON NORMAL ----
            base_path = os.path.dirname(__file__)

            icon_paths = [
                os.path.join(base_path, '..', '..', '..', 'icon.ico'),
                'icon.ico'
            ]

            for path in icon_paths:
                if os.path.exists(path):
                    self.setWindowIcon(QIcon(path))
                    break
            else:
                logging.getLogger(__name__).warning("icon.ico not found in dev mode")
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Frequency Configuration Group
        freq_group = QGroupBox("Frequency Configuration")
        freq_layout = QFormLayout(freq_group)
        
        # Start Frequency with unit selector
        start_freq_layout = QHBoxLayout()
        self.start_freq_edit = QDoubleSpinBox()
        self.start_freq_edit.setRange(50, 1500000000) 
        self.start_freq_edit.setDecimals(3)
        self.start_freq_edit.valueChanged.connect(self.on_frequency_changed)
    
        self.start_freq_unit = QComboBox()
        self.start_freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        self.start_freq_unit.setCurrentText("kHz")
        self.start_freq_unit.currentTextChanged.connect(self.on_frequency_changed)

        self.start_freq_unit.currentTextChanged.connect(
            lambda unit: self.update_spinbox_range(self.start_freq_edit, unit)
        )

        self.update_spinbox_range(self.start_freq_edit, self.start_freq_unit.currentText())

        start_freq_layout.addWidget(self.start_freq_edit)
        start_freq_layout.addWidget(self.start_freq_unit)
        freq_layout.addRow("Start Frequency:", start_freq_layout)
        
        # Stop Frequency with unit selector and max frequency validation
        stop_freq_layout = QHBoxLayout()
        self.stop_freq_edit = QDoubleSpinBox()
        self.stop_freq_edit.setRange(50, 1500000000) 
        self.stop_freq_edit.setDecimals(3)
        self.stop_freq_edit.valueChanged.connect(self.on_frequency_changed)

        self.stop_freq_unit = QComboBox()
        self.stop_freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        self.stop_freq_unit.setCurrentText("GHz")
        self.stop_freq_unit.currentTextChanged.connect(self.on_frequency_changed)

        self.stop_freq_unit.currentTextChanged.connect(
            lambda unit: self.update_spinbox_range(self.stop_freq_edit, unit)
        )

        self.update_spinbox_range(self.stop_freq_edit, self.stop_freq_unit.currentText())
        
        stop_freq_layout.addWidget(self.stop_freq_edit)
        stop_freq_layout.addWidget(self.stop_freq_unit)
        freq_layout.addRow("Stop Frequency:", stop_freq_layout)
        
        # Steps (now just called "Steps") with device limits
        steps_layout = QVBoxLayout()
        
        # Steps input with limits from device
        steps_input_layout = QHBoxLayout()
        self.segments_spinbox = SmartDatapointsSpinBox()
        self.segments_spinbox.setRange(self.sweep_points_min, self.sweep_points_max)
        self.segments_spinbox.valueChanged.connect(self.on_segments_changed)
        self.segments_spinbox.setSuffix(" steps")
        
        # Configure the smart spinbox with device-specific valid datapoints
        if self.vna_device and hasattr(self.vna_device, 'valid_datapoints'):
            self.segments_spinbox.set_valid_datapoints(self.vna_device.valid_datapoints)
            logging.info(f"[sweep_options_window] Configured smart spinbox with device datapoints: {self.vna_device.valid_datapoints}")
        else:
            # Use default datapoints if no device or no valid_datapoints
            default_points = [11, 51, 101, 201, 301, 501, 1023]
            self.segments_spinbox.set_valid_datapoints(default_points)
            logging.info(f"[sweep_options_window] Configured smart spinbox with default datapoints: {default_points}")
        
        steps_input_layout.addWidget(self.segments_spinbox)
        steps_layout.addLayout(steps_input_layout)
        
        # Device info label
        device_info_label = QLabel()
        if self.vna_device and hasattr(self.vna_device, 'name'):
            device_name = getattr(self.vna_device, 'name', 'Unknown Device')
            device_info_label.setText(f"Device: {device_name} (Min: {self.sweep_points_min}, Max: {self.sweep_points_max})")
        else:
            device_info_label.setText(f"No device detected (Default range: {self.sweep_points_min}-{self.sweep_points_max})")
        device_info_label.setStyleSheet("QLabel { font-size: 10px; font-style: italic; }")
        steps_layout.addWidget(device_info_label)
        
        freq_layout.addRow("Steps:", steps_layout)
        
        main_layout.addWidget(freq_group)
        
        # Calculated Values Group
        calc_group = QGroupBox("Calculated Values")
        calc_layout = QFormLayout(calc_group)
        
        # Center Frequency (read-only)
        self.center_freq_label = QLabel("0.000 MHz")
        self.center_freq_label.setStyleSheet("QLabel { font-weight: bold; }")
        calc_layout.addRow("Center Frequency:", self.center_freq_label)
        
        # Span (read-only)
        self.span_label = QLabel("0.000 MHz")
        self.span_label.setStyleSheet("QLabel { font-weight: bold; }")
        calc_layout.addRow("Span:", self.span_label)
        
        # Hz/step (read-only)
        self.hz_step_label = QLabel("0.000 Hz")
        self.hz_step_label.setStyleSheet("QLabel { font-weight: bold; }")
        calc_layout.addRow("Hz/step:", self.hz_step_label)
        
        main_layout.addWidget(calc_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(lambda: self.apply_settings(parent))
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.cancel_changes)
        
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self.reset_to_defaults)
        
        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(apply_button)
        
        main_layout.addLayout(button_layout)
        
    def frequency_to_hz(self, value, unit):
        """Convert frequency value to Hz based on unit."""
        multipliers = {
            "Hz": 1,
            "kHz": 1e3,
            "MHz": 1e6,
            "GHz": 1e9
        }
        return value * multipliers.get(unit, 1e6)  # Default to MHz if unknown
        
    def hz_to_frequency(self, hz_value, target_unit):
        """Convert Hz value to target unit."""
        multipliers = {
            "Hz": 1,
            "kHz": 1e3,
            "MHz": 1e6,
            "GHz": 1e9
        }
        return hz_value / multipliers.get(target_unit, 1e6)  # Default to MHz if unknown
        
    def load_settings(self):
        """Load settings from config.ini file."""
        # Default values (50 kHz to 1.5 GHz)
        default_start_hz = 50e3  # 50 kHz
        default_stop_hz = 1.5e9  # 1.5 GHz
        default_segments = 100
        
        # Load from settings (stored in Hz)
        start_freq_val = self.settings.value("Frequency/StartFreqHz", default_start_hz)
        stop_freq_val = self.settings.value("Frequency/StopFreqHz", default_stop_hz)
        segments_val = self.settings.value("Frequency/Segments", default_segments)
        
        # Load units
        start_unit = self.settings.value("Frequency/StartUnit", "kHz")
        stop_unit = self.settings.value("Frequency/StopUnit", "GHz")
        
        logging.info(f"[sweep_options_window.load_settings] Config file exists: {os.path.exists(self.config_path)}")
        logging.info(f"[sweep_options_window.load_settings] Raw values from config: "
                    f"StartFreqHz={start_freq_val}, StopFreqHz={stop_freq_val}, Segments={segments_val}")
        logging.info(f"[sweep_options_window.load_settings] Raw units from config: "
                    f"StartUnit={start_unit}, StopUnit={stop_unit}")
        
        try:
            start_freq_hz = float(str(start_freq_val)) if start_freq_val is not None else default_start_hz
            stop_freq_hz = float(str(stop_freq_val)) if stop_freq_val is not None else default_stop_hz
            segments = int(str(segments_val)) if segments_val is not None else default_segments
        except (ValueError, TypeError) as e:
            logging.error(f"[sweep_options_window.load_settings] Error parsing values: {e}")
            start_freq_hz = default_start_hz
            stop_freq_hz = default_stop_hz
            segments = default_segments
        
        # Set units first
        self.start_freq_unit.setCurrentText(str(start_unit))
        self.stop_freq_unit.setCurrentText(str(stop_unit))
        
        # Convert and set frequency values
        start_freq_display = self.hz_to_frequency(start_freq_hz, str(start_unit))
        stop_freq_display = self.hz_to_frequency(stop_freq_hz, str(stop_unit))
        
        self.start_freq_edit.setValue(start_freq_display)
        self.stop_freq_edit.setValue(stop_freq_display)
        self.segments_spinbox.setValue(segments)
        
        logging.info(f"[sweep_options_window.load_settings] Final values set in UI: "
                    f"StartFreq={start_freq_display} {start_unit}, "
                    f"StopFreq={stop_freq_display} {stop_unit}, "
                    f"Segments={segments}")
        
    def save_settings(self):

        settings = get_settings(
            "INI/sweep_config/config.ini",
            "ui/sweep_window/config/config.ini", 
            Path(__file__).resolve()
        )

        """Save current settings to config.ini file."""
        logging.info("[sweep_options_window.save_settings] Saving settings to config.ini")
        
        # Convert to Hz for storage
        start_freq_hz = self.frequency_to_hz(self.start_freq_edit.value(), self.start_freq_unit.currentText())
        stop_freq_hz = self.frequency_to_hz(self.stop_freq_edit.value(), self.stop_freq_unit.currentText())
        
        logging.info(f"[sweep_options_window.save_settings] sValues to save: "
                    f"StartFreqHz={start_freq_hz} ({start_freq_hz/1e6:.3f} MHz), "
                    f"StopFreqHz={stop_freq_hz} ({stop_freq_hz/1e6:.3f} MHz), "
                    f"Segments={self.segments_spinbox.value()}")
        
        # Save frequencies in Hz and units separately
        settings.setValue("Frequency/StartFreqHz", start_freq_hz)
        settings.setValue("Frequency/StopFreqHz", stop_freq_hz)
        settings.setValue("Frequency/Segments", self.segments_spinbox.value())
        
        # Save units
        settings.setValue("Frequency/StartUnit", self.start_freq_unit.currentText())
        settings.setValue("Frequency/StopUnit", self.stop_freq_unit.currentText())
        
        settings.sync()
        logging.info("[sweep_options_window.save_settings] Settings saved successfully")

        load_sweep_configuration(self)
        
    def calculate_derived_values(self):
        """Calculate and update center frequency, span, and Hz/step."""
        # Safety check: ensure segments_spinbox exists
        if not hasattr(self, 'segments_spinbox') or self.segments_spinbox is None:
            logging.warning("[sweep_options_window.calculate_derived_values] segments_spinbox not yet initialized, skipping calculation")
            return
            
        # Get frequencies in Hz
        start_freq_hz = self.frequency_to_hz(self.start_freq_edit.value(), self.start_freq_unit.currentText())
        stop_freq_hz = self.frequency_to_hz(self.stop_freq_edit.value(), self.stop_freq_unit.currentText())
        segments = self.segments_spinbox.value()
        
        # Validate frequency range
        if start_freq_hz >= stop_freq_hz:
            self.center_freq_label.setText("Invalid Range")
            self.span_label.setText("Invalid Range")
            self.hz_step_label.setText("Invalid Range")
            return
            
        # Calculate center frequency
        center_freq_hz = (start_freq_hz + stop_freq_hz) / 2
        
        # Format center frequency with appropriate units
        if center_freq_hz >= 1e9:
            self.center_freq_label.setText(f"{center_freq_hz/1e9:.3f} GHz")
        elif center_freq_hz >= 1e6:
            self.center_freq_label.setText(f"{center_freq_hz/1e6:.3f} MHz")
        elif center_freq_hz >= 1e3:
            self.center_freq_label.setText(f"{center_freq_hz/1e3:.3f} kHz")
        else:
            self.center_freq_label.setText(f"{center_freq_hz:.3f} Hz")
        
        # Calculate span
        span_hz = stop_freq_hz - start_freq_hz
        
        # Format span with appropriate units
        if span_hz >= 1e9:
            self.span_label.setText(f"{span_hz/1e9:.3f} GHz")
        elif span_hz >= 1e6:
            self.span_label.setText(f"{span_hz/1e6:.3f} MHz")
        elif span_hz >= 1e3:
            self.span_label.setText(f"{span_hz/1e3:.3f} kHz")
        else:
            self.span_label.setText(f"{span_hz:.3f} Hz")
        
        # Calculate Hz/step
        if segments > 1:
            hz_per_step = span_hz / (segments - 1)
            
            # Format Hz/step with appropriate units
            if hz_per_step >= 1e6:
                self.hz_step_label.setText(f"{hz_per_step/1e6:.3f} MHz")
            elif hz_per_step >= 1e3:
                self.hz_step_label.setText(f"{hz_per_step/1e3:.3f} kHz")
            else:
                self.hz_step_label.setText(f"{hz_per_step:.3f} Hz")
        else:
            self.hz_step_label.setText("0.000 Hz")
            
    def on_frequency_changed(self):
        """Handle frequency changes."""
        self.calculate_derived_values()
        
        # Skip auto-saving during initialization
        if getattr(self, '_loading_settings', False):
            return
            
        # Auto-save frequency changes so they are immediately available for sweep
        try:
            start_freq_hz = self.frequency_to_hz(self.start_freq_edit.value(), self.start_freq_unit.currentText())
            stop_freq_hz = self.frequency_to_hz(self.stop_freq_edit.value(), self.stop_freq_unit.currentText())
            
            self.settings.setValue("Frequency/StartFreqHz", start_freq_hz)
            self.settings.setValue("Frequency/StopFreqHz", stop_freq_hz)
            self.settings.setValue("Frequency/StartUnit", self.start_freq_unit.currentText())
            self.settings.setValue("Frequency/StopUnit", self.stop_freq_unit.currentText())
            self.settings.sync()
            
            logging.info(f"[sweep_options_window.on_frequency_changed] Auto-saved frequencies: {start_freq_hz/1e6:.3f} - {stop_freq_hz/1e6:.3f} MHz")
            
            load_sweep_configuration(self)
            
            # Update main window configuration if available
            if self.parent() and hasattr(self.parent(), 'load_sweep_configuration'):
                logging.info("[sweep_options_window.on_frequency_changed] Updating parent graphics_window configuration")
            else:
                logging.warning("[sweep_options_window.on_frequency_changed] Parent graphics_window not available for config update")
        except Exception as e:
            logging.warning(f"[sweep_options_window.on_frequency_changed] Error auto-saving: {e}")
        
    def on_segments_changed(self):
        """Handle segments changes."""
        self.calculate_derived_values()
        
        # Skip auto-saving during initialization
        if getattr(self, '_loading_settings', False):
            return
            
        # Auto-save segments changes so they are immediately available for sweep
        self.settings.setValue("Frequency/Segments", self.segments_spinbox.value())
        self.settings.sync()
        logging.info(f"[sweep_options_window.on_segments_changed] Auto-saved segments: {self.segments_spinbox.value()}")
        
        # Update main window configuration if available
        if self.parent() and hasattr(self.parent(), 'load_sweep_configuration'):
            logging.info("[sweep_options_window.on_segments_changed] Updating parent graphics_window configuration")
        else:
            logging.warning("[sweep_options_window.on_segments_changed] Parent graphics_window not available for config update")
        load_sweep_configuration(self)

    def apply_settings(self, parent = None):
        """Apply and save current settings."""
        # Get frequencies in Hz for validation
        start_freq_hz = self.frequency_to_hz(self.start_freq_edit.value(), self.start_freq_unit.currentText())
        stop_freq_hz = self.frequency_to_hz(self.stop_freq_edit.value(), self.stop_freq_unit.currentText())
        
        # Validate inputs
        if start_freq_hz >= stop_freq_hz:
            QMessageBox.warning(
                self, 
                "Invalid Range", 
                "Start frequency must be less than stop frequency."
            )
            return
            
        # Validate maximum frequency limit
        if stop_freq_hz > self.max_frequency_hz:
            max_freq_ghz = self.max_frequency_hz / 1e9
            QMessageBox.warning(
                self, 
                "Frequency Limit Exceeded", 
                f"Stop frequency cannot exceed {max_freq_ghz:.1f} GHz.\n"
            )
            return
            
        # Validate steps range according to device limits
        steps_value = self.segments_spinbox.value()
        if steps_value < self.sweep_points_min or steps_value > self.sweep_points_max:
            device_name = getattr(self.vna_device, 'name', 'Current device') if self.vna_device else 'Current device'
            QMessageBox.warning(
                self, 
                "Invalid Steps", 
                f"Number of steps must be between {self.sweep_points_min} and {self.sweep_points_max} "
                f"for {device_name}."
            )
            return
            
        # Save settings
        self.save_settings()

        load_sweep_configuration(self, parent)

        # Close window without confirmation message
        self.close()
        
    def reset_to_defaults(self):
        """Reset all values to default settings."""
        logging.info("[sweep_options_window.reset_to_defaults] Reset to defaults requested")
        
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all values to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logging.info("[sweep_options_window.reset_to_defaults] Resetting to default values")
            
            # Set default values (50 kHz to 1.5 GHz)
            self.start_freq_unit.setCurrentText("kHz")
            self.start_freq_edit.setValue(50.0)  # 50 kHz
            
            self.stop_freq_unit.setCurrentText("GHz")
            self.stop_freq_edit.setValue(1.5)  # 1.5 GHz
            
            self.segments_spinbox.setValue(101)
            
            # Recalculate derived values
            self.calculate_derived_values()
        else:
            logging.info("[sweep_options_window.reset_to_defaults] Reset to defaults cancelled")

    def store_original_values(self):
        """Store original values when window opens for cancel functionality."""
        self.original_values = {
            'start_freq': self.start_freq_edit.value(),
            'start_unit': self.start_freq_unit.currentText(),
            'stop_freq': self.stop_freq_edit.value(),
            'stop_unit': self.stop_freq_unit.currentText(),
            'segments': self.segments_spinbox.value()
        }

    def cancel_changes(self):
        """Cancel changes and restore original values."""
        if hasattr(self, 'original_values') and self.original_values:
            # Restore original values
            self.start_freq_edit.setValue(self.original_values['start_freq'])
            self.start_freq_unit.setCurrentText(self.original_values['start_unit'])
            self.stop_freq_edit.setValue(self.original_values['stop_freq'])
            self.stop_freq_unit.setCurrentText(self.original_values['stop_unit'])
            self.segments_spinbox.setValue(self.original_values['segments'])
            
            # Recalculate derived values with original settings
            self.calculate_derived_values()
        
        # Close window without saving
        self.close()

    def closeEvent(self, event):
        """Handle window closing event to ensure parent is updated."""
        # Ensure parent graphics_window is updated with final configuration
        if self.parent() and hasattr(self.parent(), 'load_sweep_configuration'):
            logging.info("[sweep_options_window.closeEvent] Final update to parent graphics_window configuration")
        load_sweep_configuration(self)
        
        # Call parent closeEvent
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Mock parent for testing
    class MockParent:
        def load_sweep_configuration(self):
            pass
    
    mock_parent = MockParent()
    window = SweepOptionsWindow(mock_parent)
    window.show()
    sys.exit(app.exec())
