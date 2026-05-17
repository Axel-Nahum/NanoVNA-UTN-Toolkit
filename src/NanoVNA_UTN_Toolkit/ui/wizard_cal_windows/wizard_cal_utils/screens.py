from pathlib import Path

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QGroupBox, QFormLayout, QDoubleSpinBox
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

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