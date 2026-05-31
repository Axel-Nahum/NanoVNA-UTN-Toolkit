import logging
import sys

from pathlib import Path

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QMessageBox,QGroupBox, QFormLayout, QDoubleSpinBox, 
    QWidget, QPushButton, QFrame, QStyledItemDelegate
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

# Import SmartDatapointsSpinBox for intelligent datapoints navigation
from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.sweep_window.sweep_options_window import SmartDatapointsSpinBox

try:
    from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.wizard_cal_windows.wizard_cal_utils.screens_utils import(clear_main_content, get_steps_for_method, show_current_step_measurement, 
                                                                                        clear_content)
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.wizard_cal_windows.wizard_cal_utils.sweep_cal import(get_sweep_start_frequency, get_sweep_stop_frequency, get_sweep_steps, 
                                                                                      update_spinbox_range, update_device_limits, 
                                                                                      update_sweep_config, perform_calibration_measurement
                                                                                    )
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.wizard_cal_windows.wizard_cal_utils.frequency_cal import update_frequency_ranges, on_frequency_changed_range, get_frequency_limits
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.wizard_cal_windows.wizard_cal_utils.finish_cal import finish_wizard
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------ #

class CenterDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter

def return_to_welcome(self):
    """Return to the welcome window"""
    try:
        logging.info("Returning to welcome window from calibration wizard")
        
        # Import welcome window
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.welcome_window.welcome_windows import NanoVNAWelcome
        
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
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics

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

    self.selected_method = None
    self.next_button.setEnabled(False)

    self.next_button.setText("▶▶")
    try:
        self.next_button.clicked.disconnect()
    except Exception:
        pass
    self.next_button.clicked.connect(lambda: next_step(self))

    top_container = QVBoxLayout()
    top_container.setAlignment(Qt.AlignTop)

    settings = get_settings(
        "INI/dut_measurement/dark_light_config/dark_light_config.ini",
        "shared/utils/dark_light_mode/dark_light_config.ini",
        Path(__file__).resolve()
    )

    groupbox_border = settings.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")
    groupbox_style = f"QGroupBox {{ border: {groupbox_border}; border-radius: 5px; margin-top: 1.3ex; padding-top: 6px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }}"
    frame_style = f"QFrame {{ border: {groupbox_border}; border-radius: 8px; padding: 10px; }}"

    # ================================================
    # FRAME 1: Calibration Methods
    # ================================================
    methods_frame = QFrame()
    methods_frame.setStyleSheet(frame_style)
    methods_frame_layout = QVBoxLayout(methods_frame)
    methods_frame_layout.setContentsMargins(10, 10, 10, 10)

    label = QLabel(f"{self.dut_wizard_ui_title}")
    label.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    label.setAlignment(Qt.AlignCenter)

    methods_description = QLabel(
        "Calibration methods are used to correct measurement errors in the system. "
        "They include techniques for reflection (S11) calibration and transmission (S21) calibration, "
        "allowing accurate compensation of system imperfections."
    )
    methods_description.setStyleSheet("font-size: 13px; border: none;")
    methods_description.setWordWrap(True)

    self.freq_dropdown = QComboBox()
    self.freq_dropdown.setFixedWidth(600)

    self.freq_dropdown.addItem(self.dut_wizard_ui_label_method_selection)
    self.freq_dropdown.model().item(0).setEnabled(False)
    self.freq_dropdown.setStyleSheet("""
        QComboBox {
            qproperty-alignment: 'AlignCenter';
        }
        QComboBox {
            text-align: center;
        }
        """
    )
    self.freq_dropdown.setItemDelegate(CenterDelegate(self.freq_dropdown))

    self.freq_dropdown.addItems([
        "OSM (Open - Short - Match)",
        "Normalization",
        "1-Port+N",
        "Enhanced-Response"
    ])

    self.freq_dropdown.currentIndexChanged.connect(
        lambda index: (
            setattr(
                self,
                "selected_method",
                self.freq_dropdown.currentText()
            ),
            self.next_button.setEnabled(index > 0)
        )
    )

    dropdown_layout = QHBoxLayout()
    dropdown_layout.setContentsMargins(0, 0, 0, 0)
    dropdown_layout.addStretch()
    dropdown_layout.addWidget(self.freq_dropdown)
    dropdown_layout.addStretch()

    # ================================================
    # GROUPBOX (FIX REAL)
    # ================================================
    methods_group = QGroupBox("Calibration Methods by Parameter")
    methods_group.setStyleSheet(groupbox_style)
    methods_group_layout = QVBoxLayout(methods_group)
    methods_group_layout.setContentsMargins(10, 10, 10, 10)

    # S11 / S21 container
    methods_row = QWidget()
    main_layout = QHBoxLayout(methods_row)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

    def _lbl(text):
        l = QLabel(text)
        l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet("font-size: 13px; border: none;")
        return l

    # LEFT (S11)
    s11_box = QVBoxLayout()
    s11_box.setContentsMargins(0, 0, 0, 0)
    s11_box.setSpacing(2)
    s11_box.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
    s11_title = QLabel("S11 (reflection)")
    s11_title.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")
    s11_title.setAlignment(Qt.AlignCenter)
    s11_box.addWidget(s11_title)
    s11_box.addWidget(_lbl("OSM (Open - Short - Match)"))
    s11_box.addWidget(_lbl("Normalization Open or Short"))

    # MIDDLE (S21)
    s21_box = QVBoxLayout()
    s21_box.setContentsMargins(0, 0, 0, 0)
    s21_box.setSpacing(2)
    s21_box.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
    s21_title = QLabel("S21 (transmission)")
    s21_title.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")
    s21_title.setAlignment(Qt.AlignCenter)
    s21_box.addWidget(s21_title)
    s21_box.addWidget(_lbl("Normalization Thru"))

    # RIGHT (S11 + S21)
    s11_s21_box = QVBoxLayout()
    s11_s21_box.setContentsMargins(0, 0, 0, 0)
    s11_s21_box.setSpacing(2)
    s11_s21_box.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
    s11_s21_title = QLabel("S11 (reflection) and S21 (transmission)")
    s11_s21_title.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")
    s11_s21_title.setAlignment(Qt.AlignCenter)
    s11_s21_box.addWidget(s11_s21_title)
    s11_s21_box.addWidget(_lbl("1-Port+N"))
    s11_s21_box.addWidget(_lbl("Enhanced-Response"))

    # BUILD ROW
    main_layout.addStretch()
    main_layout.addLayout(s11_box)
    main_layout.addSpacing(40)
    main_layout.addLayout(s11_s21_box)
    main_layout.addSpacing(40)
    main_layout.addLayout(s21_box)
    main_layout.addStretch()

    methods_group_layout.addWidget(methods_row)

    # ================================================
    # FRAME ASSEMBLY
    # ================================================
    methods_frame_layout.addWidget(label)
    methods_frame_layout.addWidget(methods_description)
    methods_frame_layout.addSpacing(15)
    methods_frame_layout.addLayout(dropdown_layout)

    methods_frame_layout.addWidget(methods_group)

    # ================================================
    # FRAME 2: Sweep Settings (SIN CAMBIOS)
    # ================================================
    sweep_frame = QFrame()
    sweep_frame.setStyleSheet(frame_style)
    sweep_frame_layout = QVBoxLayout(sweep_frame)
    sweep_frame_layout.setContentsMargins(15, 15, 15, 15)
    sweep_frame_layout.setSpacing(10)

    label_sweep_title = QLabel("Sweep Settings")
    label_sweep_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    label_sweep_title.setAlignment(Qt.AlignCenter)

    sweep_description = QLabel(
        "Sweep settings define the frequency range and resolution used for all measurements. "
        "The selected values directly affect both reflection and transmission results."
    )
    sweep_description.setStyleSheet("font-size: 13px; border: none;")
    sweep_description.setWordWrap(True)

    sweep_group = QGroupBox(f"{self.dut_wizard_ui_sweep_title}")
    sweep_group.setStyleSheet(groupbox_style)
    sweep_layout = QFormLayout()

    start_freq_layout = QHBoxLayout()
    self.start_freq_input = QDoubleSpinBox()
    self.start_freq_input.setDecimals(4)
    self.start_freq_input.setValue(50)
    start_freq_layout.addWidget(self.start_freq_input)

    self.start_freq_unit = QComboBox()
    self.start_freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
    self.start_freq_unit.setCurrentText("kHz")
    self.start_freq_unit.setItemDelegate(CenterDelegate(self.start_freq_unit))
    start_freq_layout.addWidget(self.start_freq_unit)

    label_start_freq = QLabel(f"{self.dut_wizard_ui_start_freq}")

    label_start_freq.setStyleSheet("""
        QLabel {
            border: none;
            background: transparent;
        }
    """)
    sweep_layout.addRow(label_start_freq, start_freq_layout)

    stop_freq_layout = QHBoxLayout()
    self.stop_freq_input = QDoubleSpinBox()
    self.stop_freq_input.setDecimals(4)
    self.stop_freq_input.setValue(1.5)
    stop_freq_layout.addWidget(self.stop_freq_input)

    self.stop_freq_unit = QComboBox()
    self.stop_freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
    self.stop_freq_unit.setCurrentText("GHz")
    self.stop_freq_unit.setItemDelegate(CenterDelegate(self.stop_freq_unit))
    stop_freq_layout.addWidget(self.stop_freq_unit)

    label_stop_freq = QLabel(f"{self.dut_wizard_ui_stop_freq}")
    label_stop_freq.setStyleSheet(
        """
        QLabel {
            border: none; 
            background: transparent;
            }
        """
    )

    sweep_layout.addRow(label_stop_freq, stop_freq_layout)

    self.steps_input = SmartDatapointsSpinBox()
    self.steps_input.setMinimum(1)
    self.steps_input.setMaximum(32000)
    self.steps_input.setValue(101)

    self.steps_input.setStyleSheet("""
        QSpinBox {
            background-color: #2e2e2e;
            color: white;;
            border-radius: 8px;
            font-size: 14px;
            min-height: 20px;
            padding: 4px;
        }
        QSpinBox:hover { background-color: #4d4d4d; }
        QSpinBox:focus { background-color: #4d4d4d; border: 2px solid #4CAF50; }
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #4d4d4d;
            border: 1px solid #4a4a4a;
            border-radius: 3px;
            width: 16px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #5d5d5d; }
                                   QSpinBox::up-arrow {
            image: none;
            border-left: 2px solid transparent;
            border-right: 2px solid transparent;
            border-bottom: 3px solid white;
            width: 0px;
            height: 0px;
        }

        QSpinBox::down-arrow {
            image: none;
            border-left: 2px solid transparent;
            border-right: 2px solid transparent;
            border-top: 3px solid white;
            width: 0px;
            height: 0px;
        }
    """)

    label_steps = QLabel(f"{self.dut_wizard_ui_steps}")
    label_steps.setStyleSheet(
        """
        QLabel {
            border: none;
        }
    """)

    sweep_layout.addRow(label_steps, self.steps_input)

    sweep_group.setLayout(sweep_layout)

    sweep_frame_layout.addWidget(label_sweep_title)
    sweep_frame_layout.addWidget(sweep_description)
    sweep_frame_layout.addWidget(sweep_group)

    # ================================================
    # FINAL LAYOUT
    # ================================================
    top_container.addWidget(methods_frame)
    top_container.addSpacing(10)
    top_container.addWidget(sweep_frame)

    self.content_layout.addLayout(top_container)

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
    info_label = QLabel(f"{self.dut_wizard_ui_steps_title} {self.selected_method}\nStep {step}/{len(steps)}")
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

    if is_measured:
        instruction_text = f"{step_name} standard already measured ✓"
        instruction_style = "font-size: 14px; padding: 8px; color: lightgreen;"
    else:
        instruction_text = f"{self.dut_wizard_ui_instruction_text.format(step_name=step_name)}"
        instruction_style = "font-size: 14px; padding: 8px; color: yellow;"
        
    instruction_label = QLabel(instruction_text)
    instruction_label.setAlignment(Qt.AlignCenter)
    instruction_label.setStyleSheet(instruction_style)
    instruction_label.setWordWrap(True)
    left_layout.addWidget(instruction_label)
    
    # Button to perform measurement
    measure_button = QPushButton(f"{self.dut_wizard_ui_re_measure_label_button}" if is_measured else f"{self.dut_wizard_ui_measure_label_button}")
    measure_button.setStyleSheet("font-size: 16px; padding: 10px; font-weight: bold;")
    measure_button.clicked.connect(lambda: perform_calibration_measurement(self, step, step_name))
    left_layout.addWidget(measure_button)
    
    # Status label to show measurement state
    if is_measured:
        status_text = f"{step_name} measurement complete"
        status_style = "font-size: 12px; padding: 4px; color: lightgreen;"
    else:
        status_text = f"{self.dut_wizard_ui_label_measure}"
        status_style = "font-size: 12px; padding: 4px;"
        
    self.status_label = QLabel(status_text)
    self.status_label.setAlignment(Qt.AlignCenter)
    self.status_label.setStyleSheet(status_style)
    left_layout.addWidget(self.status_label)
    
    # Measurement completion status
    if self.osm_calibration and self.selected_method == "OSM (Open - Short - Match)" or self.selected_method == "1-Port+N" or self.selected_method == "Enhanced-Response":
        status = self.osm_calibration.get_completion_status()
        
        status_label = QLabel(f"{self.dut_wizard_ui_calibration_status}")
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
    if self.thru_calibration and self.selected_method == "Normalization" or self.selected_method == "1-Port+N" or self.selected_method == "Enhanced-Response":
        status = self.thru_calibration.get_completion_status()

        if self.selected_method == "Normalization":
            status_label = QLabel(f"{self.dut_wizard_ui_calibration_status}")
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
            
        self.next_button.setText(f"{self.dut_wizard_ui_label_finish_button}")
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
            
        self.next_button.setText(f"{self.dut_wizard_ui_label_finish_button}")
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
            
        self.next_button.setText(f"{self.dut_wizard_ui_label_finish_button}")
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