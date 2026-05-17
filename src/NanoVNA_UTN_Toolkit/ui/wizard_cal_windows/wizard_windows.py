import logging
import sys
import os
from datetime import datetime
import numpy as np
from shiboken6 import isValid

import matplotlib.pyplot as plt

from pathlib import Path

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
        QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,  
        QMessageBox,QGroupBox, QFormLayout, QDoubleSpinBox, QToolTip
)
from PySide6.QtGui import QIcon, QColor
from PySide6.QtCore import Qt

# Import SmartDatapointsSpinBox for intelligent datapoints navigation
from ..sweep_window.sweep_options_window import SmartDatapointsSpinBox

plt.rcParams['mathtext.fontset'] = 'cm'   
plt.rcParams['text.usetex'] = False      
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'    
plt.rcParams['mathtext.rm'] = 'serif'     

# Import NanoVNAGraphics for the final step
try:
    from NanoVNA_UTN_Toolkit.ui.graphics_window import NanoVNAGraphics
except ImportError as e:
    logging.error("Failed to import NanoVNAGraphics: %s", e)
    NanoVNAGraphics = None  # Safe fallback

# Import calibration data storage
try:
    from NanoVNA_UTN_Toolkit.calibration.calibration_manager import OSMCalibrationManager, THRUCalibrationManager
except ImportError as e:
    logging.error("Failed to import OSMCalibrationManager: %s", e)
    logging.error("Failed to import THRUCalibrationManager: %s", e)
    OSMCalibrationManager = None
    THRUCalibrationManager = None

from NanoVNA_UTN_Toolkit.ui.calibration.errors import CalibrationErrors

try:
    from NanoVNA_UTN_Toolkit.ui.utils.calibration.calibration import update_calibration_label_from_method
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

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
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

# ------------------------------------------------------------------------------------------------------------------- #

class CalibrationWizard(QMainWindow):
    def __init__(self, vna_device=None, parent=None, caller="welcome"):
        super().__init__()

        base_path = get_calibration_path(
            "calibration",
            "calibration",
            Path(__file__).resolve()
        )

        # Inicializar el manager pasándole la ruta
        self.osm_calibration = OSMCalibrationManager(base_path=None)
        self.thru_calibration = THRUCalibrationManager(base_path=None)

        self.last_start_value = 50   
        self.last_stop_value  = 1.5   

        self.parent = parent

        self.caller = caller

 #------------------------------------------------------------------------------------------------------------------------------------------

        # Dark-Light mode settings

        dark_light_config(self)

#------------------------------------------------------------------------------------------------------------------------------------------

        self.setWindowTitle("NanoVNA UTN Toolkit - Calibration Wizard")
        self.setGeometry(150, 150, 1000, 600)

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

        self.vna_device = vna_device
        
        # Initialize OSM calibration storage with new manager
        if OSMCalibrationManager:
            self.osm_calibration = OSMCalibrationManager()
            if vna_device and hasattr(vna_device, 'name'):
                self.osm_calibration.device_name = vna_device.name
            logging.info("[CalibrationWizard] OSM calibration manager initialized")
        else:
            self.osm_calibration = None
            logging.warning("[CalibrationWizard] OSMCalibrationManager not available")
        
        if THRUCalibrationManager:
            self.thru_calibration = THRUCalibrationManager()
            if vna_device and hasattr(vna_device, 'name'):
                self.thru_calibration.device_name = vna_device.name
            logging.info("[CalibrationWizard] THRU calibration manager initialized")
        else:
            self.thru_calibration = None
            logging.warning("[CalibrationWizard] THRUCalibrationManager not available")

        # Store measured data state for UI consistency
        self.measured_data = {
            'open': None,
            'short': None, 
            'match': None
        }
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # Content area (this is where screens are placed)
        self.content_layout = QVBoxLayout()
        self.main_layout.addLayout(self.content_layout)

        # Step tracking
        self.current_step = 0
        self.selected_method = None
        
        # Sweep configuration (persistent across screens)
        self.sweep_start_freq = 50000  # 50 kHz default
        self.sweep_stop_freq = 1500000000  # 1.5 GHz default
        self.sweep_steps = 101  # Default steps

        # Bottom button layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 10, 0, 0)

        # Back button (left)
        self.back_button = QPushButton("◀◀")
        self.back_button.setFixedSize(100, 30)
        self.back_button.setStyleSheet("font-size: 14px;")
        self.back_button.clicked.connect(self.previous_step)
        self.button_layout.addWidget(self.back_button)

        self.button_layout.addStretch()

        # Save Calibration button (will be shown only in final step)
        self.save_button = QPushButton("Save Calibration")
        self.save_button.setFixedSize(130, 30)
        self.save_button.setStyleSheet("font-size: 12px; background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_button.clicked.connect(self.save_calibration_dialog)
        self.save_button.setVisible(False)  # Hidden by default
        self.button_layout.addWidget(self.save_button)

        # Next button (right)
        self.next_button = QPushButton("▶▶")
        self.next_button.setFixedSize(100, 30)
        self.next_button.setStyleSheet("font-size: 14px;")
        self.next_button.clicked.connect(self.next_step)
        self.next_button.setEnabled(False)  # start locked until user selects
        self.button_layout.addWidget(self.next_button)

        self.main_layout.addLayout(self.button_layout)

        # Show first screen
        self.show_first_screen()

    # --- layout clearing helpers ------------------------------------------------
    def clear_layout(self, layout):
        """Recursively remove widgets and nested layouts from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            child_layout = item.layout()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout:
                # Recursively clear nested layout
                self.clear_layout(child_layout)

    def clear_main_content(self):
        """Clear everything inside content_layout and remove old panels if exist."""
        self.clear_content()  # limpia content_layout
        # elimina widgets antiguos si existen
        if hasattr(self, "left_panel_widget") and self.left_panel_widget:
            if isValid(self.left_panel_widget):
                self.left_panel_widget.setParent(None)
            self.left_panel_widget = None

        if hasattr(self, "right_panel_widget") and self.right_panel_widget:
            if isValid(self.right_panel_widget):
                self.right_panel_widget.setParent(None)
            self.right_panel_widget = None

    def clear_content(self):
        """Clear everything inside content_layout (handles nested layouts)."""
        self.clear_layout(self.content_layout)

    from PySide6.QtWidgets import QToolTip

    def on_frequency_changed_range(self):
        start_val_hz = self.start_freq_input.value() * self.unit_multiplier(self.start_freq_unit.currentText())
        stop_val_hz  = self.stop_freq_input.value()  * self.unit_multiplier(self.stop_freq_unit.currentText())

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


    def update_spinbox_range(self, spinbox, unit):
        """Actualiza el rango del spinbox según la unidad actual y los límites del dispositivo."""
        # Use device limits if available, otherwise fallback to defaults
        if hasattr(self, 'freq_min_hz') and hasattr(self, 'freq_max_hz'):
            # Convert device limits to the current unit
            min_freq_in_unit = self.freq_min_hz / self.unit_multiplier(unit)
            max_freq_in_unit = self.freq_max_hz / self.unit_multiplier(unit)
            
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

    def unit_multiplier(self, unit):
        return {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[unit]


    # --- screens --------------------------------------------------------------
    def show_first_screen(self):
        """Initial screen: Calibration Methods dropdown (aligned near top)."""
        self.clear_content()

        # Reset selection state
        self.selected_method = None
        self.next_button.setEnabled(False)

        # --- 🔴 FIX: Reset button when returning to start ---
        self.next_button.setText("▶▶")
        try:
            self.next_button.clicked.disconnect()
        except Exception:
            pass
        self.next_button.clicked.connect(self.next_step)

        # Container que mantiene el contenido arriba
        top_container = QVBoxLayout()
        top_container.setAlignment(Qt.AlignTop)
        top_container.addSpacing(20)

        label = QLabel("Calibration Methods:")
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        label.setAlignment(Qt.AlignLeft)

        self.freq_dropdown = QComboBox()
        self.freq_dropdown.setEditable(False)

        # Placeholder
        self.freq_dropdown.addItem("Select Method")
        item = self.freq_dropdown.model().item(0)
        item.setEnabled(False)
        placeholder_color = QColor(120, 120, 120)
        item.setForeground(placeholder_color)

        methods = [
            "OSM (Open - Short - Match)",
            "Normalization",
            "1-Port+N",
            "Enhanced-Response"
        ]
        self.freq_dropdown.addItems(methods)
        self.freq_dropdown.activated.connect(self.on_method_activated)

        top_container.addWidget(label)
        
        top_container.addSpacing(10)

        top_container.addWidget(self.freq_dropdown)

        top_container.addSpacing(10)
        
        # Add sweep configuration section

        # Load configuration for UI colors and styles
        settings = get_settings(
            "INI/dark_light_config/dark_light_config.ini",
            "ui/utils/settings/dark_light_mode/dark_light_config.ini", 
            Path(__file__).resolve()
        ) 

        groupbox_border = settings.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")
        groupbox_style = f"QGroupBox {{ border: {groupbox_border}; border-radius: 5px; margin-top: 1.3ex; padding-top: 6px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }}"

        sweep_group = QGroupBox("Sweep Configuration")
        sweep_group.setStyleSheet(groupbox_style)
        sweep_layout = QFormLayout()
        
        # Start frequency
        start_freq_layout = QHBoxLayout()
        self.start_freq_input = QDoubleSpinBox()
        self.start_freq_input.setDecimals(4)
        self.start_freq_input.setValue(50)  # 50 kHz inicial
        self.start_freq_input.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 150px;
            }
            QDoubleSpinBox:hover {
                background-color: #4d4d4d;
            }
            QDoubleSpinBox:focus {
                background-color: #4d4d4d;
                border: 2px solid #4CAF50;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background-color: #4d4d4d;
                border: 1px solid white;
                border-radius: 3px;
                width: 16px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #5d5d5d;
            }
        """)
        start_freq_layout.addWidget(self.start_freq_input)
        
        self.start_freq_unit = QComboBox()
        self.start_freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        self.start_freq_unit.setCurrentText("kHz")
        start_freq_layout.addWidget(self.start_freq_unit)
        
        sweep_layout.addRow("Start Frequency:", start_freq_layout)
        
        # Stop frequency
        stop_freq_layout = QHBoxLayout()
        self.stop_freq_input = QDoubleSpinBox()
        self.stop_freq_input.setDecimals(4)
        self.stop_freq_input.setValue(1.5)
        self.stop_freq_input.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 150px;
            }
            QDoubleSpinBox:hover {
                background-color: #4d4d4d;
            }
            QDoubleSpinBox:focus {
                background-color: #4d4d4d;
                border: 2px solid #4CAF50;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background-color: #4d4d4d;
                border: 1px solid white;
                border-radius: 3px;
                width: 16px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #5d5d5d;
            }
        """)
        stop_freq_layout.addWidget(self.stop_freq_input)
        
        self.stop_freq_unit = QComboBox()
        self.stop_freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        self.stop_freq_unit.setCurrentText("GHz")
        stop_freq_layout.addWidget(self.stop_freq_unit)
        
        sweep_layout.addRow("Stop Frequency:", stop_freq_layout)
        
        # Number of steps (using smart datapoints spinbox)
        self.steps_input = SmartDatapointsSpinBox()  # Asumo que sigue siendo un QSpinBox
        self.steps_input.setMinimum(1)
        self.steps_input.setMaximum(32000)  # Default maximum, will be updated based on device
        self.steps_input.setValue(101)
        self.steps_input.setStyleSheet("""
            QSpinBox {
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 150px;
            }
            QSpinBox:hover {
                background-color: #4d4d4d;
            }
            QSpinBox:focus {
                background-color: #4d4d4d;
                border: 2px solid #4CAF50;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #4d4d4d;
                border: 1px solid white;
                border-radius: 3px;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #5d5d5d;
            }
        """)
        sweep_layout.addRow("Number of Steps:", self.steps_input)
        
        sweep_group.setLayout(sweep_layout)
        top_container.addWidget(sweep_group)
        
        # Connect widgets to update sweep configuration
        self.start_freq_input.valueChanged.connect(self.update_sweep_config)
        self.start_freq_unit.currentTextChanged.connect(self.update_sweep_config)

        self.stop_freq_input.valueChanged.connect(self.update_sweep_config)
        self.stop_freq_unit.currentTextChanged.connect(self.update_sweep_config)

        self.steps_input.valueChanged.connect(self.update_sweep_config)

        # Conectar rango dinámico según unidad
        self.start_freq_unit.currentTextChanged.connect(
            lambda unit: self.update_spinbox_range(self.start_freq_input, unit)
        )
        self.stop_freq_unit.currentTextChanged.connect(
            lambda unit: self.update_spinbox_range(self.stop_freq_input, unit)
        )

        # Validación para evitar que el usuario ingrese valores fuera de rango manualmente
        self.start_freq_input.editingFinished.connect(self.on_frequency_changed_range)
        self.stop_freq_input.editingFinished.connect(self.on_frequency_changed_range)

        # Update initial values and device limits
        self.update_sweep_config()
        self.update_device_limits()  # Configure SmartDatapointsSpinBox with device limits
        
        # Get frequency limits from device and configure frequency spinboxes
        self.freq_min_hz, self.freq_max_hz = self.get_frequency_limits()
        self.update_frequency_ranges()  # Configure frequency ranges based on device limits

        self.content_layout.addLayout(top_container)

        # Show back button and configure it to return to welcome screen
        self.back_button.setVisible(True)
        self.back_button.setText("◀◀")
        try:
            self.back_button.clicked.disconnect()
        except Exception:
            pass

        if self.caller == "welcome":
            self.back_button.clicked.connect(self.return_to_welcome)
        elif self.caller == "graphics":
            self.back_button.clicked.connect(self.return_to_graphics)
        
        self.current_step = 0

    def on_method_activated(self, index):
        """Called when user selects a method from the combo box."""

        if index == 0:
            self.selected_method = None
            self.next_button.setEnabled(False)
        else:
            self.selected_method = self.freq_dropdown.itemText(index)
            self.next_button.setEnabled(True)
            # Update device limits when method is selected
            self.update_device_limits()

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

    # --- Step definitions (each step is unique) ---------------------------------
    def step_OSM_OPEN(self):
        label = QLabel("Step 1: OPEN (OSM)")
        label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
        label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        return label

    def step_OSM_SHORT(self):
        label = QLabel("Step 2: SHORT (OSM)")
        label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
        label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        return label

    def step_OSM_MATCH(self):
        label = QLabel("Step 3: MATCH (OSM)")
        label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
        label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        return label

    def step_Normalization(self):
        label = QLabel("Step 1: Normalization")
        label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
        label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        return label

    def step_OnePortN_OPEN(self):
        label = QLabel("Step 1: OPEN (1-Port+N)")
        label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
        label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        return label

    def step_OnePortN_SHORT(self):
        label = QLabel("Step 2: SHORT (1-Port+N)")
        label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
        label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        return label

    def step_OnePortN_MATCH(self):
        label = QLabel("Step 3: MATCH (1-Port+N)")
        label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
        label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        return label

    def step_OnePortN_THRU(self):
        label = QLabel("Step 4: THRU (1-Port+N)")
        label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
        label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        return label

    # You can add unique steps for Enhanced-Response and 1-Path 2-Port in the same way

    # --- Get steps for current method -----------------------------------------
    def get_steps_for_method(self):
        """Return a list of unique step methods for the selected method."""
        if self.selected_method == "OSM (Open - Short - Match)":
            return [
                self.step_OSM_OPEN,
                self.step_OSM_SHORT,
                self.step_OSM_MATCH
            ]
        elif self.selected_method == "Normalization":
            return [self.step_Normalization]
        elif self.selected_method == "1-Port+N":
            return [
                self.step_OnePortN_OPEN,
                self.step_OnePortN_SHORT,
                self.step_OnePortN_MATCH,
                self.step_OnePortN_THRU
            ]
        elif self.selected_method == "Enhanced-Response":
            return [
                lambda: QLabel("Step 1: OPEN (Enhanced-Response)", alignment=Qt.AlignRight | Qt.AlignTop),
                lambda: QLabel("Step 2: SHORT (Enhanced-Response)", alignment=Qt.AlignRight | Qt.AlignTop),
                lambda: QLabel("Step 3: MATCH (Enhanced-Response)", alignment=Qt.AlignRight | Qt.AlignTop),
                lambda: QLabel("Step 4: THRU (Enhanced-Response)", alignment=Qt.AlignRight | Qt.AlignTop)
            ]
        elif self.selected_method == "1-Path 2-Port":
            return [
                lambda: QLabel("Step 1: OPEN (1-Path 2-Port)", alignment=Qt.AlignRight | Qt.AlignTop),
                lambda: QLabel("Step 2: SHORT (1-Path 2-Port)", alignment=Qt.AlignRight | Qt.AlignTop),
                lambda: QLabel("Step 3: MATCH (1-Path 2-Port)", alignment=Qt.AlignRight | Qt.AlignTop),
                lambda: QLabel("Step 4: THRU (1-Path 2-Port)", alignment=Qt.AlignRight | Qt.AlignTop)
            ]
        else:
            return []

    def show_step_screen(self, step):
        """Show the given step with left info panel and right Smith chart."""
        self.clear_main_content()
        steps = self.get_steps_for_method()

        # Pantalla final
        if step > len(steps):
            final_label = QLabel("Calibration Finished!")
            final_label.setAlignment(Qt.AlignCenter)
            final_label.setStyleSheet("font-size: 20px; font-weight: bold;")
            self.content_layout.addWidget(final_label)
            self.back_button.setVisible(True)
            self.next_button.setVisible(False)
            self.current_step = step
            return

        # Panel izquierdo
        self.left_panel_widget = QWidget()
        left_layout = QVBoxLayout(self.left_panel_widget)
        left_layout.setAlignment(Qt.AlignTop)
        info_label = QLabel(f"Method: {self.selected_method}\nStep {step}/{len(steps)}")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px;")
        left_layout.addWidget(info_label)
        
        # Determine which standard is being measured for OSM
        step_name = "UNKNOWN"
        if self.selected_method == "OSM (Open - Short - Match)":
            if step == 1:
                step_name = "OPEN"
            elif step == 2:
                step_name = "SHORT"
            elif step == 3:
                step_name = "MATCH"

        if self.selected_method == "Normalization":
            if step == 1:
                step_name = "THRU"

        if self.selected_method == "1-Port+N":
            if step == 1:
                step_name = "OPEN"
            elif step == 2:
                step_name = "SHORT"
            elif step == 3:
                step_name = "MATCH"
            elif step == 4:
                step_name = "THRU"

        if self.selected_method == "Enhanced-Response":
            if step == 1:
                step_name = "OPEN"
            elif step == 2:
                step_name = "SHORT"
            elif step == 3:
                step_name = "MATCH"
            elif step == 4:
                step_name = "THRU"
        
        # Check if this standard has already been measured
        is_measured = False
        if self.osm_calibration:
            is_measured = self.osm_calibration.is_standard_measured(step_name.lower())

        if self.thru_calibration:
            is_measured = self.thru_calibration.is_standard_measured(step_name.lower())

        # Instrucciones del paso actual
        if is_measured:
            instruction_text = f"{step_name} standard already measured ✓"
            instruction_style = "font-size: 14px; padding: 8px; color: lightgreen;"
        else:
            instruction_text = f"Connect {step_name} standard and press Measure"
            instruction_style = "font-size: 14px; padding: 8px; color: yellow;"
            
        instruction_label = QLabel(instruction_text)
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet(instruction_style)
        instruction_label.setWordWrap(True)
        left_layout.addWidget(instruction_label)
        
        # Button to perform measurement
        measure_button = QPushButton("Re-measure" if is_measured else "Measure")
        measure_button.setStyleSheet("font-size: 16px; padding: 10px; font-weight: bold;")
        measure_button.clicked.connect(lambda: self.perform_calibration_measurement(step, step_name))
        left_layout.addWidget(measure_button)
        
        # Status label to show measurement state
        if is_measured:
            status_text = f"{step_name} measurement complete"
            status_style = "font-size: 12px; padding: 4px; color: lightgreen;"
        else:
            status_text = "Ready to measure"
            status_style = "font-size: 12px; padding: 4px;"
            
        self.status_label = QLabel(status_text)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(status_style)
        left_layout.addWidget(self.status_label)
        
        # Measurement completion status
        if self.osm_calibration and self.selected_method == "OSM (Open - Short - Match)":
            status = self.osm_calibration.get_completion_status()
            
            status_label = QLabel("Calibration Status:")
            status_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
            left_layout.addWidget(status_label)
            
            # Store references to status widgets for later updates
            self.calibration_status_widgets = {}
            
            for standard, completed in status.items():
                if standard == 'complete':
                    continue
                icon = "✓" if completed else "✗"
                color = "green" if completed else "red"
                status_text = 'Completed' if completed else 'Pending'
                label = QLabel(f"{icon} {standard.upper()}: {status_text}")
                label.setStyleSheet(f"font-size: 14px; color: {color}; margin-left: 10px;")
                left_layout.addWidget(label)
                
                # Store reference for later updates
                self.calibration_status_widgets[standard] = label

        # Measurement completion status
        if self.thru_calibration and self.selected_method == "Normalization":
            status = self.thru_calibration.get_completion_status()

            status_label = QLabel("Calibration Status:")
            status_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
            left_layout.addWidget(status_label)
            
            # Store references to status widgets for later updates
            self.calibration_status_widgets = {}
            
            for standard, completed in status.items():
                if standard == 'complete':
                    continue
                icon = "✓" if completed else "✗"
                color = "green" if completed else "red"
                status_text = 'Completed' if completed else 'Pending'
                label = QLabel(f"{icon} {standard.upper()}: {status_text}")
                label.setStyleSheet(f"font-size: 14px; color: {color}; margin-left: 10px;")
                left_layout.addWidget(label)
                
                # Store reference for later updates
                self.calibration_status_widgets[standard] = label
        
        left_layout.addStretch()

        # Panel derecho: Smith chart con canvas de matplotlib usando utils consolidadas
        self.right_panel_widget = QWidget()
        right_layout = QVBoxLayout(self.right_panel_widget)

        # Use consolidated Smith chart creation
        from ...utils.smith_chart_utils import create_wizard_smith_chart
        from ...utils.magnitude_chat_utils import create_wizard_magnitude_chart

        if step_name == "OPEN" or "SHORT" or "MATCH":
            fig, ax, canvas = create_wizard_smith_chart(
                start_freq=self.get_sweep_start_frequency(),
                stop_freq=self.get_sweep_stop_frequency(),
                num_points=self.get_sweep_steps(),
                container_layout=right_layout,
                figsize=(8, 8)  # Significantly larger square aspect ratio for better visibility
            )
            # Store references for later updates
            self.current_fig = fig
            self.current_canvas = canvas
            self.current_ax = ax

        if step_name == "THRU":
            while right_layout.count():
                item = right_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)

            fig_magnitude, ax_magnitude, canvas_magnitude = create_wizard_magnitude_chart(
                start_freq=self.get_sweep_start_frequency(),
                stop_freq=self.get_sweep_stop_frequency(),
                num_points=self.get_sweep_steps(),
                container_layout=right_layout,
                figsize=(5, 5)  # Significantly larger square aspect ratio for better visibility
            )

            # Store references for later updates
            self.current_fig_magnitude = fig_magnitude
            self.current_canvas_magnitude = canvas_magnitude
            self.current_ax_magnitude = ax_magnitude

        # Layout horizontal
        panel_row = QHBoxLayout()
        panel_row.addWidget(self.left_panel_widget, 2)
        panel_row.addWidget(self.right_panel_widget, 2)
        self.content_layout.addLayout(panel_row)

        # Show only the measurement for the current step if it exists
        if self.osm_calibration and self.selected_method == "OSM (Open - Short - Match)":
            self.show_current_step_measurement(step)

        if self.thru_calibration and self.selected_method == "Normalization":
            self.show_current_step_measurement(step)

        self.current_step = step
        self.back_button.setVisible(step > 0)
        
        # Configure back button to use previous_step instead of return_to_welcome
        if step > 0:
            try:
                self.back_button.clicked.disconnect()
            except Exception:
                pass
            self.back_button.clicked.connect(self.previous_step)

        try:
            self.next_button.clicked.disconnect(self.next_step)
        except (TypeError, RuntimeError):
            pass
        try:
            self.next_button.clicked.disconnect(self.finish_wizard)
        except (TypeError, RuntimeError):
            pass

        if step == len(steps):
            # Always show save button in final step for OSM calibration
            if self.osm_calibration and self.selected_method == "OSM (Open - Short - Match)":
                self.save_button.setVisible(True)
            else:
                self.save_button.setVisible(False)
                
            self.next_button.setText("Finish")
            try:
                self.next_button.clicked.disconnect()
            except Exception:
                pass
            self.next_button.clicked.connect(self.finish_wizard)
        else:
            self.save_button.setVisible(False)  # Hide save button in non-final steps
            self.next_button.setText("▶▶")
            try:
                self.next_button.clicked.disconnect()
            except Exception:
                pass
            self.next_button.clicked.connect(self.next_step)

        if step == len(steps):
            # Always show save button in final step for Thru calibration
            if self.thru_calibration and self.selected_method == "Normalization":
                self.save_button.setVisible(True)
            else:
                self.save_button.setVisible(False)
                
            self.next_button.setText("Finish")
            try:
                self.next_button.clicked.disconnect()
            except Exception:
                pass
            self.next_button.clicked.connect(self.finish_wizard)
        else:
            self.save_button.setVisible(False)  # Hide save button in non-final steps
            self.next_button.setText("▶▶")
            try:
                self.next_button.clicked.disconnect()
            except Exception:
                pass
            self.next_button.clicked.connect(self.next_step)

        if step == len(steps):
            # Always show save button in final step for Thru calibration
            if self.thru_calibration and self.selected_method == "1-Port+N":
                self.save_button.setVisible(True)
            else:
                self.save_button.setVisible(False)
                
            self.next_button.setText("Finish")
            try:
                self.next_button.clicked.disconnect()
            except Exception:
                pass
            self.next_button.clicked.connect(self.finish_wizard)
        else:
            self.save_button.setVisible(False)  # Hide save button in non-final steps
            self.next_button.setText("▶▶")
            try:
                self.next_button.clicked.disconnect()
            except Exception:
                pass
            self.next_button.clicked.connect(self.next_step)

        if step == len(steps):
            # Always show save button in final step for Thru calibration
            if self.thru_calibration and self.selected_method == "Enhanced-Response":
                self.save_button.setVisible(True)
            else:
                self.save_button.setVisible(False)
                
            self.next_button.setText("Finish")
            try:
                self.next_button.clicked.disconnect()
            except Exception:
                pass
            self.next_button.clicked.connect(self.finish_wizard)
        else:
            self.save_button.setVisible(False)  # Hide save button in non-final steps
            self.next_button.setText("▶▶")
            try:
                self.next_button.clicked.disconnect()
            except Exception:
                pass
            self.next_button.clicked.connect(self.next_step)


    # --- navigation handlers -------------------------------------------------
    def next_step(self):
        self.next_button.setEnabled(False)

        if self.current_step == 0:
            if not self.selected_method:
                return
            self.show_step_screen(1)
        else:
            steps = self.get_steps_for_method()
            if self.current_step < len(steps):
                self.show_step_screen(self.current_step + 1)
            else:
                self.show_step_screen(self.current_step + 1)

        # --- Control de visibilidad del botón "Save Calibration" ---
        if (
            (self.selected_method == "Normalization" and self.current_step == 1)
            or (self.selected_method == "OSM (Open - Short - Match)" and self.current_step == 3)
            or (self.selected_method == "1-Port+N" and self.current_step == 4)
            or (self.selected_method == "Enhanced-Response" and self.current_step == 4)
        ):
            self.save_button.setVisible(True)
        else:
            self.save_button.setVisible(False)


    def previous_step(self):
        if self.current_step <= 1:
            self.show_first_screen() 
            self.next_button.setEnabled(False)  
        else:
            self.show_step_screen(self.current_step - 1)

    def finish_wizard(self):
        """Finish calibration wizard by calculating OSM errors and opening graphics window."""
        logging.info("Calibration wizard completed - calculating OSM errors")

        if self.selected_method == "OSM (Open - Short - Match)":
            cal_dir = get_calibration_path(
                "calibration/osm_results",
                "calibration/osm_results",
                Path(__file__).resolve()
            )
            os.makedirs(cal_dir, exist_ok=True)

            # Create calibration error handler and compute OSM errors
            errors = CalibrationErrors(cal_dir, error_subfolder="osm_errors")
            errors.calculate_osm_errors()

        elif self.selected_method == "Normalization":
            cal_dir = get_calibration_path(
                "calibration/thru_results",
                "calibration/thru_results",
                Path(__file__).resolve()
            )
            os.makedirs(cal_dir, exist_ok=True)

            errors = CalibrationErrors(cal_dir, error_subfolder="normalization_errors")
            errors.calculate_normalization_errors()

        elif self.selected_method == "1-Port+N":
            osm_dir = get_calibration_path(
                "calibration/osm_results",
                "calibration/osm_results",
                Path(__file__).resolve()
            )
            thru_dir = get_calibration_path(
                "calibration/thru_results",
                "calibration/thru_results",
                Path(__file__).resolve()
            )

            os.makedirs(osm_dir, exist_ok=True)
            os.makedirs(thru_dir, exist_ok=True)

            errors = CalibrationErrors(thru_dir, error_subfolder="1-Port+N_errors")
            errors.calculate_1PortN_errors(osm_dir, thru_dir)

        elif self.selected_method == "Enhanced-Response":
            osm_dir = get_calibration_path(
                "calibration/osm_results",
                "calibration/osm_results",
                Path(__file__).resolve()
            )
            thru_dir = get_calibration_path(
                "calibration/thru_results",
                "calibration/thru_results",
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
            "INI/calibration_config/calibration_config.ini",
            "calibration/calibration_config/calibration_config.ini", 
            Path(__file__).resolve()
        )

        settings_calibration.setValue("Calibration/CalibrationWizard", True)
        settings_calibration.setValue("Calibration/NoCalibration", False)
        settings_calibration.setValue("Calibration/Kits", False)
        settings_calibration.setValue("Calibration/isImportDut", False)

        # Load configuration for sweep settings and frequency range parameters
        settings = get_settings(
                "INI/sweep_config/sweep_config.ini",
                "ui/sweep_window/sweep_config/sweep_config.ini", 
                Path(__file__).resolve()        
        )

        settings.setValue("Frequency/StartFreqHz", self.get_sweep_start_frequency())
        settings.setValue("Frequency/StopFreqHz", self.get_sweep_stop_frequency())
        settings.setValue("Frequency/Segments", self.get_sweep_steps())

        # Open graphics window
        self.open_graphics_window()

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

        try:
            # Update status
            self.status_label.setText(f"Measuring {standard_name}...")
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
                
                # Save data in calibration structure
                if self.osm_calibration:
                    if standard_name == "OPEN":
                        self.osm_calibration.set_measurement("open", freqs, s11)
                    elif standard_name == "SHORT":
                        self.osm_calibration.set_measurement("short", freqs, s11)
                    elif standard_name == "MATCH":
                        self.osm_calibration.set_measurement("match", freqs, s11)
                    
                    # Show completion status
                    status = self.osm_calibration.get_completion_status()
                    logging.info(f"[CalibrationWizard] Calibration status: {status}")
                    
                    # Update the status display immediately after measurement
                    self.update_calibration_status_display()
                    
                    # Update UI state after measurement
                    self.status_label.setText(f"{standard_name} measurement complete")
                    self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")
                
                # Update Smith chart with measured data
                self.update_smith_chart(freqs, s11, standard_name)
                
                # Update status
                self.status_label.setText(f"{standard_name} measured successfully!")
                self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")
                
                logging.info(f"[CalibrationWizard] Measurement for {standard_name} completed successfully")

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

                logging.info(f"[NP S21] DTYPE: {s21.dtype}")
                logging.info(f"[NP S21] SHAPE: {s21.shape}")
                logging.info(f"[NP S21] FIRST 10: {s21[:10]}")
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
                    self.update_calibration_status_display()
                    
                    # Update UI state after measurement
                    self.status_label.setText(f"{standard_name} measurement complete")
                    self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")

                # Update Magnitude chart with measured data
                self.update_magnitude_chart(freqs, s21, standard_name)
                
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

    
    def save_calibration_dialog(self):
        from PySide6.QtWidgets import QMessageBox
        """Shows a dialog to save the calibration without advancing to graphics window"""
        if not self.osm_calibration:
            return

        if not self.thru_calibration:
            return
            
        # Check which measurements are available
        osm_status = self.osm_calibration.get_completion_status()
        thru_status = self.thru_calibration.get_completion_status()

        measured_standards = [
            std for std, completed in osm_status.items() if completed and std != 'complete'
        ] + [
            std for std, completed in thru_status.items() if completed and std != 'complete'
        ]
        
        if not measured_standards:
            QMessageBox.warning(
                self, 
                "No Measurements", 
                "No calibration measurements have been taken yet.\nPlease perform at least one measurement before saving."
            )
            return
            
        # Dialog to enter calibration name
        from PySide6.QtWidgets import QInputDialog

        if self.selected_method == "OSM (Open - Short - Match)":
            prefix = "OSM"
        elif self.selected_method == "Normalization":
            prefix = "Normalization"
        elif self.selected_method == "1-Port+N":
            prefix = "1PortN"
        elif self.selected_method == "Enhanced-Response":
            prefix = "Enhanced Response"

        name, ok = QInputDialog.getText(
            self, 
            'Save Calibration', 
            f'Enter calibration name:\n\nMeasurements to save: {", ".join(measured_standards).upper()}',
            text=f'{prefix}_Calibration_{self.get_current_timestamp()}'
        )
        
        if ok and name:
            try:
                # Save calibration (it will save only the available measurements)
                success = self.osm_calibration.save_calibration_file(name, self.selected_method, False)
                if success:
                    # Show success message
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"Calibration '{name}' saved successfully!\n\nSaved measurements: {', '.join(measured_standards).upper()}\n\nFiles saved in:\n- Touchstone format\n- .cal format\n\nUse 'Finish' button to continue to graphics window."
                    )
                    
                    # Stay in wizard - do not advance to graphics window
                    logging.info(f"Calibration '{name}' saved successfully - staying in wizard")
                    
                else:
                    from PySide6.QtWidgets import QMessageBox
                    #QMessageBox.warning(self, "Error", "Failed to save calibration") hay un error aca y entra primero

                success = self.thru_calibration.save_calibration_file(name, self.selected_method, False, osm_instance=self.osm_calibration)
                if success:
                    # Show success message
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"Calibration '{name}' saved successfully!\n\nSaved measurements: {', '.join(measured_standards).upper()}\n\nFiles saved in:\n- Touchstone format\n- .cal format\n\nUse 'Finish' button to continue to graphics window."
                    )
                    
                    # Stay in wizard - do not advance to graphics window
                    logging.info(f"Calibration '{name}' saved successfully - staying in wizard")
                    
                else:
                    from PySide6.QtWidgets import QMessageBox
                    #QMessageBox.warning(self, "Error", "Failed to save calibration")

                # --- Read current calibration method ---
                # Use new calibration structure

                # Load configuration for calibration settings
                settings_calibration = get_settings(
                    "INI/calibration_config/calibration_config.ini",
                    "calibration/calibration_config/calibration_config.ini", 
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
                settings_calibration.setValue("method", self.selected_method)
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
                logging.error(f"[CalibrationWizard] Error saving calibration: {e}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")

    def get_current_timestamp(self):
        """Generate timestamp for filenames"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
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
                self._save_calibration_config()
                
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
    
    def return_to_welcome(self):
        """Return to the welcome window"""
        try:
            logging.info("Returning to welcome window from calibration wizard")
            
            # Import welcome window
            from NanoVNA_UTN_Toolkit.ui.welcome_windows import NanoVNAWelcome
            
            # Create welcome window with VNA device if available
            self.welcome_window = NanoVNAWelcome(vna_device=self.vna_device) if self.vna_device else NanoVNAWelcome()
            
            # Show welcome window
            self.welcome_window.show()
            logging.info("Welcome window opened successfully")
            
            # Close wizard
            self.close()
            
        except Exception as e:
            logging.error(f"Error returning to welcome window: {e}")
            QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to return to welcome window: {str(e)}"
            )

    def return_to_graphics(self):
        """Return to the graphics window"""
        try:
            logging.info("Returning to graphics window from calibration wizard")
            
            # Import graphic window
            from NanoVNA_UTN_Toolkit.ui.graphics_window import NanoVNAGraphics

            # Create graphics window with VNA device if available
            self.graphics_window = NanoVNAGraphics(vna_device=self.vna_device) if self.vna_device else NanoVNAGraphics()
            
            # Show graphics window
            self.graphics_window.show()
            logging.info("Graphics window opened successfully")

            # Close wizard
            self.close()
            
        except Exception as e:
            logging.error(f"Error returning to graphics window: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to return to graphics window: {str(e)}"
            )
    
    def _save_calibration_config(self):
        """Save calibration configuration to config file"""
        try:
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Load configuration for calibration settings
            settings = get_settings(
                "INI/calibration_config/calibration_config.ini",
                "calibration/calibration_config/calibration_config.ini", 
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
    
    def show_existing_measurements_on_chart(self):
        """Show all existing measurements on Smith chart to preserve state"""
        from ...utils.smith_chart_utils import SmithChartManager
        from ...utils.magnitude_chat_utils import MagnitudeChartManager
        
        if not self.osm_calibration or not hasattr(self, 'current_ax'):
            return

        if not self.thru_calibration or not hasattr(self, 'current_ax'):
            return
            
        try:
            # Collect all existing measurements
            measurements = {}
            for standard_name in ['open', 'short', 'match']:
                if self.osm_calibration.is_standard_measured(standard_name):
                    measurement = self.osm_calibration.get_measurement(standard_name)
                    if measurement:
                        measurements[standard_name] = measurement
            
            # Use consolidated Smith chart functionality
            manager = SmithChartManager()
            manager.show_multiple_measurements(
                ax=self.current_ax,
                measurements_dict=measurements,
                canvas=self.current_canvas,
                start_freq=self.get_sweep_start_frequency(),
                stop_freq=self.get_sweep_stop_frequency(),
                num_points=self.get_sweep_steps()
            )
            
        except Exception as e:
            logging.error(f"[CalibrationWizard] Error showing existing measurements: {e}")

        try:
            # Collect all existing measurements
            measurements = {}
            for standard_name in ['thru']:
                if self.thru_calibration.is_standard_measured(standard_name):
                    measurement = self.thru_calibration.get_measurement(standard_name)
                    if measurement:
                        measurements[standard_name] = measurement

            # Use consolidated Magnitude chart functionality
            manager = MagnitudeChartManager()
            manager.show_multiple_measurements(
                ax=self.current_ax,
                measurements_dict=measurements,
                canvas=self.current_canvas,
                start_freq=self.get_sweep_start_frequency(),
                stop_freq=self.get_sweep_stop_frequency(),
                num_points=self.get_sweep_steps()
            )
            
        except Exception as e:
            logging.error(f"[CalibrationWizard] Error showing existing measurements: {e}")
    
    def show_current_step_measurement(self, step):
        """Show only the measurement for the current step on Smith chart."""
        from ...utils.smith_chart_utils import SmithChartManager
        from ...utils.magnitude_chat_utils import MagnitudeChartManager
        
        if not self.osm_calibration or not hasattr(self, 'current_ax'):
            return

        if not self.thru_calibration or not hasattr(self, 'current_ax'):
            return
            
        try:
            # Determine which standard corresponds to current step
            step_name = None
            if self.selected_method == "OSM (Open - Short - Match)":
                if step == 1:
                    step_name = "open"
                elif step == 2:
                    step_name = "short"
                elif step == 3:
                    step_name = "match"
            elif self.selected_method == "Normalization":
                if step == 1:
                    step_name = "thru"

            # Show only the measurement for the current step if it exists
            if self.selected_method == "OSM (Open - Short - Match)" and step_name in ["open", "short", "match"]:
                if self.osm_calibration and self.osm_calibration.is_standard_measured(step_name):
                    measurement = self.osm_calibration.get_measurement(step_name)
                    if measurement:
                        freqs, s11 = measurement
                        manager = SmithChartManager()
                        manager.update_wizard_measurement(
                            ax=self.current_ax,
                            freqs=freqs,
                            s11_data=s11,
                            standard_name=step_name,
                            canvas=self.current_canvas
                        )
                        return
            else:
                # Clear and show empty Smith chart if no measurement exists
                self.current_ax.clear()
                manager = SmithChartManager()
                base_network = manager.builder.create_empty_network(
                    self.get_sweep_start_frequency(),
                    self.get_sweep_stop_frequency(),
                    self.get_sweep_steps()
                )
                manager.builder.ax = self.current_ax
                manager.builder.draw_base_smith_chart(base_network)
                self.current_canvas.draw()

            if self.selected_method == "Normalization" and step_name == "thru":
                if self.thru_calibration.is_standard_measured(step_name):
                    measurement = self.thru_calibration.get_measurement(step_name)
                    if measurement:
                        freqs, s11 = measurement

                        # Use consolidated Magnitude plot functionality for single measurement
                        manager = MagnitudeChartManager()  # New manager for magnitude
                        manager.update_wizard_measurement(
                            ax=self.current_ax,
                            freqs=freqs,
                            s_data=np.abs(s11),  # Use magnitude instead of complex S11
                            standard_name=step_name,
                            canvas=self.current_canvas_magnitude
                        )
                else:
                    # Clear and show empty magnitude plot if no measurement exists
                    self.current_ax.clear()
                    manager = MagnitudePlotManager()
                    freqs_base = np.linspace(
                        self.get_sweep_start_frequency(),
                        self.get_sweep_stop_frequency(),
                        self.get_sweep_steps()
                    )
                    # Create empty y-data for magnitude plot
                    s_data_empty = np.zeros_like(freqs_base)
                    
                    manager.builder.ax = self.current_ax
                    manager.builder.plot_base_magnitude(freqs_base, s_data_empty)  # Replace Smith chart base with magnitude
                    self.current_canvas.draw()

        except Exception as e:
            logging.error(f"[CalibrationWizard] Error showing current step measurement: {e}")
    
    def update_smith_chart(self, freqs, s11, standard_name):
        """Update Smith chart with measured calibration data."""
        from ...utils.smith_chart_utils import SmithChartManager
        
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
        from ...utils.magnitude_chat_utils import MagnitudeChartManager
        
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
            self.update_spinbox_range(self.start_freq_input, start_unit)
            
            # Update stop frequency range
            stop_unit = self.stop_freq_unit.currentText()
            self.update_spinbox_range(self.stop_freq_input, stop_unit)
            
            logging.info(f"[CalibrationWizard] Updated frequency ranges for device limits: {self.freq_min_hz/1e6:.3f} - {self.freq_max_hz/1e6:.3f} MHz")
            
        except Exception as e:
            logging.error(f"[CalibrationWizard] Error updating frequency ranges: {e}")
            # Use default behavior on error
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = CalibrationWizard()
    wizard.show()
    sys.exit(app.exec())
