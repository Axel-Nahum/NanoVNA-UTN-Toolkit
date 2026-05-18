import logging

from pathlib import Path

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QMessageBox,
    QGroupBox, QFormLayout, QDoubleSpinBox, QWidget, QPushButton
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

# Import SmartDatapointsSpinBox for intelligent datapoints navigation
from NanoVNA_UTN_Toolkit.ui.sweep_window.sweep_options_window import SmartDatapointsSpinBox

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.wizard_cal_windows.wizard_cal_utils.screens_utils import(clear_main_content, get_steps_for_method, show_current_step_measurement, 
                                                                                        clear_content)
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.wizard_cal_windows.wizard_cal_utils.sweep_cal import(get_sweep_start_frequency, get_sweep_stop_frequency, get_sweep_steps, 
                                                                                      update_spinbox_range, update_device_limits, 
                                                                                      update_sweep_config, perform_calibration_measurement
                                                                                    )
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.wizard_cal_windows.wizard_cal_utils.frequency_cal import update_frequency_ranges, on_frequency_changed_range, get_frequency_limits
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.wizard_cal_windows.wizard_cal_utils.finish_cal import finish_wizard
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------ #

def return_to_welcome(self):
    """Return to the welcome window"""
    try:
        logging.info("Returning to welcome window from calibration wizard")
        
        # Import welcome window
        from NanoVNA_UTN_Toolkit.ui.welcome_window.welcome_windows import NanoVNAWelcome
        
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
        from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_window import NanoVNAGraphics

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

# --- Navigation Handlers -------------------------------------------------

def next_step(self, parent = None):
    self.next_button.setEnabled(False)

    if self.current_step == 0:
        if not self.selected_method:
            return
        show_step_screen(self, 1)
    else:
        steps = get_steps_for_method(self)
        if self.current_step < len(steps):
            show_step_screen(self, self.current_step + 1, parent = parent)
        else:
            show_step_screen(self, self.current_step + 1, parent = parent)

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
        show_first_screen(self) 
        self.next_button.setEnabled(False)  
    else:
        show_step_screen(self, self.current_step - 1)

def show_first_screen(self):
    """Initial screen: Calibration Methods dropdown (aligned near top)."""
    clear_content(self)

    # Reset selection state
    self.selected_method = None
    self.next_button.setEnabled(False)

    # --- 🔴 FIX: Reset button when returning to start ---
    self.next_button.setText("▶▶")
    try:
        self.next_button.clicked.disconnect()
    except Exception:
        pass
    self.next_button.clicked.connect(lambda: next_step(self))

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
    self.start_freq_input.valueChanged.connect(lambda: update_sweep_config(self))
    self.start_freq_unit.currentTextChanged.connect(lambda: update_sweep_config(self))

    self.stop_freq_input.valueChanged.connect(lambda: update_sweep_config(self))
    self.stop_freq_unit.currentTextChanged.connect(lambda: update_sweep_config(self))

    self.steps_input.valueChanged.connect(lambda: update_sweep_config(self))

    # Conectar rango dinámico según unidad
    self.start_freq_unit.currentTextChanged.connect(
        lambda unit: update_spinbox_range(self, self.start_freq_input, unit)
    )
    self.stop_freq_unit.currentTextChanged.connect(
        lambda unit: update_spinbox_range(self, self.stop_freq_input, unit)
    )

    # Validación para evitar que el usuario ingrese valores fuera de rango manualmente
    self.start_freq_input.editingFinished.connect(lambda: on_frequency_changed_range(self))
    self.stop_freq_input.editingFinished.connect(lambda: on_frequency_changed_range(self))

    # Update initial values and device limits
    update_sweep_config(self)
    update_device_limits(self)  # Configure SmartDatapointsSpinBox with device limits
    
    # Get frequency limits from device and configure frequency spinboxes
    self.freq_min_hz, self.freq_max_hz = get_frequency_limits(self)
    update_frequency_ranges(self)  # Configure frequency ranges based on device limits

    self.content_layout.addLayout(top_container)

    # Show back button and configure it to return to welcome screen
    self.back_button.setVisible(True)
    self.back_button.setText("◀◀")
    try:
        self.back_button.clicked.disconnect()
    except Exception:
        pass

    if self.caller == "welcome":
        self.back_button.clicked.connect(lambda: return_to_welcome(self))
    elif self.caller == "graphics":
        self.back_button.clicked.connect(lambda: return_to_graphics(self))
    
    self.current_step = 0

def show_step_screen(self, step, parent = None):
    """Show the given step with left info panel and right Smith chart."""
    clear_main_content(self)
    steps = get_steps_for_method(self)

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
    measure_button.clicked.connect(lambda: perform_calibration_measurement(self, step, step_name))
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
    from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import create_wizard_smith_chart
    from NanoVNA_UTN_Toolkit.utils.magnitude_chat_utils import create_wizard_magnitude_chart

    if step_name == "OPEN" or "SHORT" or "MATCH":
        fig, ax, canvas = create_wizard_smith_chart(
            start_freq=get_sweep_start_frequency(self),
            stop_freq=get_sweep_stop_frequency(self),
            num_points=get_sweep_steps(self),
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
            start_freq=get_sweep_start_frequency(self),
            stop_freq=get_sweep_stop_frequency(self),
            num_points=get_sweep_steps(self),
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
        show_current_step_measurement(self, step)

    if self.thru_calibration and self.selected_method == "Normalization":
        show_current_step_measurement(self, step)

    self.current_step = step
    self.back_button.setVisible(step > 0)
    
    # Configure back button to use previous_step instead of return_to_welcome
    if step > 0:
        try:
            self.back_button.clicked.disconnect()
        except Exception:
            pass
        self.back_button.clicked.connect(lambda: previous_step(self))

    try:
        self.next_button.clicked.disconnect(lambda: next_step(self))
    except (TypeError, RuntimeError):
        pass
    try:
        self.next_button.clicked.disconnect(lambda: finish_wizard(self, parent = parent))
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
        self.next_button.clicked.connect(lambda: finish_wizard(self))
    else:
        self.save_button.setVisible(False)  # Hide save button in non-final steps
        self.next_button.setText("▶▶")
        try:
            self.next_button.clicked.disconnect()
        except Exception:
            pass
        self.next_button.clicked.connect(lambda: next_step(self))

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
        self.next_button.clicked.connect(lambda: finish_wizard(self))
    else:
        self.save_button.setVisible(False)  # Hide save button in non-final steps
        self.next_button.setText("▶▶")
        try:
            self.next_button.clicked.disconnect()
        except Exception:
            pass
        self.next_button.clicked.connect(lambda: next_step(self))

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
        self.next_button.clicked.connect(lambda: finish_wizard(self))
    else:
        self.save_button.setVisible(False)  # Hide save button in non-final steps
        self.next_button.setText("▶▶")
        try:
            self.next_button.clicked.disconnect()
        except Exception:
            pass
        self.next_button.clicked.connect(lambda: next_step(self))

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
        self.next_button.clicked.connect(lambda: finish_wizard(self))
    else:
        self.save_button.setVisible(False)  # Hide save button in non-final steps
        self.next_button.setText("▶▶")
        try:
            self.next_button.clicked.disconnect()
        except Exception:
            pass
        self.next_button.clicked.connect(lambda: next_step(self))