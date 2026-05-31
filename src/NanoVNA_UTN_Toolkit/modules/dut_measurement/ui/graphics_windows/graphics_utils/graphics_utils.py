import numpy as np
import os
import logging
import gc
import sys

from pathlib import Path

from matplotlib.widgets import Slider
from PySide6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

plt.rcParams['mathtext.fontset'] = 'cm'   # Computer Modern font
plt.rcParams['text.usetex'] = False       # No external LaTeX required
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'     # Matches LaTeX style
plt.rcParams['mathtext.rm'] = 'serif'     # Consistent numbers and text


from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSizePolicy, QLineEdit
from PySide6.QtCore import QSettings

# Import get_settings 

try:
    from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------ #

def format_frequency_smart(freq_hz):
    """Format frequency in the most appropriate unit (Hz, kHz, MHz, GHz)."""
    if freq_hz >= 1e9:
        return f"{freq_hz/1e9:.3f} GHz"
    elif freq_hz >= 1e6:
        return f"{freq_hz/1e6:.3f} MHz"
    elif freq_hz >= 1e3:
        return f"{freq_hz/1e3:.3f} kHz"
    else:
        return f"{freq_hz:.1f} Hz"

def format_frequency_smart_split(freq_hz):
    """Format frequency and return (value, unit) tuple."""
    if freq_hz >= 1e9:
        return f"{freq_hz/1e9:.3f}", "GHz"
    elif freq_hz >= 1e6:
        return f"{freq_hz/1e6:.3f}", "MHz"
    elif freq_hz >= 1e3:
        return f"{freq_hz/1e3:.3f}", "kHz"
    else:
        return f"{freq_hz:.1f}", "Hz"

def parse_frequency_input(text):
    """Parse frequency input with units and return value in Hz."""
    text = text.strip().replace(",", ".")
    
    # Extract numeric part and unit
    import re
    match = re.match(r'(\d+\.?\d*)\s*([a-zA-Z]*)', text)
    if not match:
        return None
        
    value = float(match.group(1))
    unit = match.group(2).lower()
    
    # Convert to Hz based on unit
    if unit.startswith('g'):  # GHz
        return value * 1e9
    elif unit.startswith('m'):  # MHz
        return value * 1e6
    elif unit.startswith('k'):  # kHz
        return value * 1e3
    else:  # Hz or no unit (assume MHz for backward compatibility)
        if unit == '' or unit.startswith('h'):
            return value * 1e6 if unit == '' else value
        return value

#############################################################################################
# =================== LEFT PANEL ========================================================= #
#############################################################################################

def create_left_panel(self, S_data, freqs, settings, graph_type="Smith Diagram", s_param="S11",
                      tracecolor="red", markercolor="red", marker2color="red", linewidth=2,
                      markersize=5, marker2size=5, marker_visible=True, marker_visible_2=False):
    
    # ----------------------------------------------------
    # Plot Manager settings
    # ----------------------------------------------------

    self.settings = get_settings(
        "INI/dut_measurement/plot_manager/plot_manager.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/plot_manager.ini",
        Path(__file__).resolve()
    )

    # ----------------------------------------------------
    # Colors and styles from settings
    # ----------------------------------------------------

    background_color_graphics = settings.value("Graphic1/BackgroundColor", "red")
    text_color = settings.value("Graphic1/TextColor", "red")
    axis_color = settings.value("Graphic1/AxisColor", "red")
    
    # QGroupBox border styling based on dark/light mode
    groupbox_border = settings.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")
    groupbox_style = f"QGroupBox {{ border: {groupbox_border}; border-radius: 5px; margin-top: 1.3ex; padding-top: 10px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }}"
                      
    freqs = freqs if freqs is not None else np.linspace(1e6, 100e6, 101)

    unit_mode = settings.value("Graphic1/db_times", "dB")

    if S_data is None:
        phase = -2*np.pi*freqs/1e8
        S_data = 0.5 * np.exp(1j*phase)
    
    left_panel = QWidget()
    left_layout = QVBoxLayout(left_panel)
    left_layout.setAlignment(Qt.AlignTop)
    left_layout.setContentsMargins(10,10,10,10)
    left_layout.setSpacing(10)

    # --- Figure ---
    if graph_type == "Smith Diagram":
        # Use consolidated Smith chart functionality
        from ......utils.smith_chart_utils import SmithChartConfig, SmithChartManager
        
        # Create custom config to match original settings
        config = SmithChartConfig()
        config.background_color = background_color_graphics
        config.axis_color = axis_color
        config.text_color = axis_color
        config.trace_color = tracecolor
        config.marker_color = markercolor
        config.linewidth = linewidth
        config.markersize = markersize
        config.marker_visible = marker_visible
        config.marker_visible_2 = marker_visible_2
        
        # Create Smith chart with custom configuration
        manager = SmithChartManager(config)
        fig, ax, canvas, cursor_graph, cursor_graph_2 = manager.create_graphics_panel_smith_chart(
            s_data=S_data,
            freqs=freqs,
            s_param=s_param,
            figsize=(10, 10),
            container_layout=left_layout,
            trace_color=tracecolor,
            marker_color=markercolor,
            marker2_color=marker2color
        )

    elif graph_type == "Magnitude":

        fig, ax = plt.subplots(figsize=(4,3))
        fig.subplots_adjust(left=0.22, right=0.8, top=0.8, bottom=0.22)

        fig.patch.set_facecolor(f"{background_color_graphics}")
        ax.set_facecolor(f"{background_color_graphics}")

        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(canvas)

        ax.plot(freqs*1e-6, np.abs(S_data), color=tracecolor, marker='.', linestyle='-', linewidth=linewidth, zorder=2)

        ax.set_xlabel(rf"$\mathrm{{{self.measurement_ui_magnitude_x_axis}}}$", color=text_color)
        ax.set_ylabel(r"$|%s|$" % s_param, color=text_color)
        ax.set_title(rf"${self.measurement_ui_magnitude_title.format(parameter=s_param, db_times=unit_mode)}$", color=f"{text_color}")

        # Set X-axis limits with margins to match actual frequency range of the sweep
        freq_start = freqs[0]*1e-6
        freq_end = freqs[-1]*1e-6
        freq_range = freq_end - freq_start
        margin = freq_range * 0.05  # 5% margin on each side
        ax.set_xlim(freq_start - margin, freq_end + margin)
        # Set Y-axis limits with margins to provide visual spacing
        magnitude_data = np.abs(S_data)
        y_min = np.min(magnitude_data)
        y_max = np.max(magnitude_data)
        y_range = y_max - y_min
        y_margin = y_range * 0.05  # 5% margin on each side
        ax.set_ylim(y_min - y_margin, y_max + y_margin)
        ax.autoscale(False)  # Prevent matplotlib from overriding our xlim/ylim settings
        ax.tick_params(axis='x', colors=f"{axis_color}")
        ax.tick_params(axis='y', colors=f"{axis_color}")

        for spine in ax.spines.values():
            spine.set_color("white")

        current_state_grid = self.settings.value(f"grid/current_left_state", "true", type=bool)
            
        ax.grid(current_state_grid, which='both', axis='both', color='white', linestyle='--', linewidth=0.5, alpha=0.3, zorder=1)

        cursor_graph, = ax.plot([], [], 'o', markersize=markersize, color=markercolor, visible=marker_visible)
        cursor_graph_2, = ax.plot([], [], 'o', markersize=marker2size, color=marker2color, visible=False)

    elif graph_type == "Phase":

        fig, ax = plt.subplots(figsize=(4,3))
        fig.subplots_adjust(left=0.22, right=0.8, top=0.8, bottom=0.22)

        fig.patch.set_facecolor(f"{background_color_graphics}")
        ax.set_facecolor(f"{background_color_graphics}")

        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(canvas)

        ax.plot(freqs*1e-6, np.angle(S_data, deg=True), color=tracecolor, marker='.', linestyle='-', linewidth=linewidth)

        ax.set_xlabel(rf"$\mathrm{{{self.measurement_ui_magnitude_x_axis}}}$", color=text_color)
        ax.set_ylabel(r"$\phi_{%s}\ [^\circ]$" % s_param, color=f"{text_color}")
        ax.set_title(rf"$\mathrm{{{self.measurement_ui_phase_title.format(parameter=s_param)}}}$", color=text_color)

        # Set X-axis limits with margins to match actual frequency range of the sweep
        freq_start = freqs[0]*1e-6
        freq_end = freqs[-1]*1e-6
        freq_range = freq_end - freq_start
        margin = freq_range * 0.05  # 5% margin on each side
        ax.set_xlim(freq_start - margin, freq_end + margin)
        # Set Y-axis limits with margins to provide visual spacing
        phase_data = np.angle(S_data, deg=True)
        y_min = np.min(phase_data)
        y_max = np.max(phase_data)
        y_range = y_max - y_min
        y_margin = y_range * 0.05  # 5% margin on each side
        ax.set_ylim(y_min - y_margin, y_max + y_margin)
        ax.autoscale(False)  # Prevent matplotlib from overriding our xlim/ylim settings
        ax.tick_params(axis='x', colors=f"{axis_color}")
        ax.tick_params(axis='y', colors=f"{axis_color}")

        for spine in ax.spines.values():
            spine.set_color("white")

        current_state_grid = self.settings.value(f"grid/current_left_state", "true", type=bool)
            
        ax.grid(current_state_grid, which='both', axis='both', color='white', linestyle='--', linewidth=0.5, alpha=0.3, zorder=1)

        cursor_graph, = ax.plot([], [], 'o', markersize=markersize, color=markercolor, visible=marker_visible)
        cursor_graph_2, = ax.plot([], [], 'o', markersize=marker2size, color=marker2color, visible=False)

    else:
        raise ValueError(f"Unknown graph_type: {graph_type}")

    # --- Info panel (left side reorganized) ---
    info_panel = QWidget()
    info_layout = QVBoxLayout(info_panel)
    info_layout.setSpacing(10)
    info_layout.setContentsMargins(0, 0, 0, 0)

    # --- Top QGroupBox with title ---
    box_top = QGroupBox(f"{self.measurement_ui_s_parameter_details_title}")
    box_top.setStyleSheet(groupbox_style)
    layout_top = QHBoxLayout(box_top)
    layout_top.setSpacing(20)
    layout_top.setContentsMargins(12, 8, 12, 8)  # balanced margins

    # --- Centered sub-layout for the 4 blocks ---
    center_layout = QHBoxLayout()
    center_layout.setSpacing(15)  # space between columns
    center_layout.setAlignment(Qt.AlignCenter)  # everything centered in the box

    # --- Column 1: Frequency ---
    col_left = QVBoxLayout()
    col_left.setSpacing(5)
    col_left.setAlignment(Qt.AlignVCenter)

    hbox_freq = QHBoxLayout()
    hbox_freq.setAlignment(Qt.AlignLeft)
    hbox_freq.setContentsMargins(0, 0, 0, 0)

    lbl_text = QLabel(f"{self.measurement_ui_s_parameter_frequency}")
    lbl_text.setStyleSheet("font-size:14px;")
    lbl_text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    hbox_freq.addWidget(lbl_text)

    initial_freq_value, initial_freq_unit = format_frequency_smart_split(freqs[0])
    edit_value = QLineEdit(initial_freq_value)
    edit_value.setSelection(0, 0)
    edit_value.setCursorPosition(0)
    edit_value.clearFocus()

    def limit_frequency_input(text, max_digits=6, max_decimals=3, allow_dashes=False):
        if text == "--":   # allow placeholder
            return text
        filtered = "".join(c for c in text if c.isdigit() or c == ".")
        if filtered.count(".") > 1:
            parts = filtered.split(".", 1)
            filtered = parts[0] + "." + "".join(parts[1:]).replace(".", "")
        if "." in filtered:
            integer_part, decimal_part = filtered.split(".", 1)
            integer_part = integer_part[:max_digits]
            decimal_part = decimal_part[:max_decimals]
            filtered = integer_part + "." + decimal_part
        else:
            filtered = filtered[:max_digits]
        return filtered

    def on_text_changed():
        new_text = limit_frequency_input(edit_value.text(), 3, 3)
        if new_text != edit_value.text():
            edit_value.setText(new_text)
        text_width = edit_value.fontMetrics().horizontalAdvance(edit_value.text())
        min_width = max(text_width + 10, 40)
        edit_value.setFixedWidth(min_width)

    edit_value.textChanged.connect(on_text_changed)
    edit_value.setStyleSheet("font-size:14px; border:none; background:transparent;")
    edit_value.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    text_width = edit_value.fontMetrics().horizontalAdvance(edit_value.text())
    min_width = max(text_width + 10, 40)
    edit_value.setFixedWidth(min_width)
    hbox_freq.addWidget(edit_value)

    lbl_unit = QLabel(initial_freq_unit)
    lbl_unit.setStyleSheet("font-size:14px;")
    lbl_unit.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    lbl_unit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    hbox_freq.addWidget(lbl_unit)

    col_left.addLayout(hbox_freq)

    # --- Column 2: S11 real + imag ---
    label_val = QLabel(f"{s_param}: -- + j--")
    label_val.setStyleSheet("font-size:14px; padding:1px;")
    label_val.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_s11 = QVBoxLayout()
    col_s11.setSpacing(5)
    col_s11.setAlignment(Qt.AlignVCenter)
    col_s11.addWidget(label_val)

    # --- Column 3: |S11| ---
    label_mag = QLabel(f"|{s_param}|: --")
    label_mag.setStyleSheet("font-size:14px; padding:1px;")
    label_mag.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_mag = QVBoxLayout()
    col_mag.setSpacing(5)
    col_mag.setAlignment(Qt.AlignVCenter)
    col_mag.addWidget(label_mag)

    # --- Column 4: Phase ---
    label_phase = QLabel(f"{self.measurement_ui_s_parameter_phase} --")
    label_phase.setStyleSheet("font-size:14px; padding:1px;")
    label_phase.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_phase = QVBoxLayout()
    col_phase.setSpacing(5)
    col_phase.setAlignment(Qt.AlignVCenter)
    col_phase.addWidget(label_phase)

    # --- Add columns to centered layout with separators ---
    center_layout.addLayout(col_left)
    
    label_sep = QLabel("-")
    center_layout.addWidget(label_sep)

    center_layout.addLayout(col_s11)

    label_sep = QLabel("-")
    center_layout.addWidget(label_sep)

    center_layout.addLayout(col_mag)

    label_sep = QLabel("-")
    center_layout.addWidget(label_sep)

    center_layout.addLayout(col_phase)

    # --- Add centered layout to top box ---
    layout_top.addLayout(center_layout)

    # --- Bottom QGroupBox ---
    box_bottom = QGroupBox(f"{self.measurement_ui_dut_parameters_title}")
    box_bottom.setStyleSheet(groupbox_style)
    layout_bottom = QHBoxLayout(box_bottom)
    layout_bottom.setSpacing(40)  # increase spacing between labels
    layout_bottom.setContentsMargins(10, 8, 10, 8)
    layout_bottom.setAlignment(Qt.AlignCenter)  # center everything

    # --- Labels dentro del box_bottom ---
    label_z = QLabel(f"{self.measurement_ui_dut_zin} -- + j--")
    label_z.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_z.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom.addWidget(label_z)

    label_sep = QLabel("-")
    layout_bottom.addWidget(label_sep)

    label_il = QLabel(f"{self.measurement_ui_dut_insertion_loss} -- dB")
    label_il.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_il.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom.addWidget(label_il)

    label_sep = QLabel("-")
    layout_bottom.addWidget(label_sep)

    label_vswr = QLabel(f"{self.measurement_ui_dut_vswr} --")
    label_vswr.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_vswr.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom.addWidget(label_vswr)

    # --- Add box_bottom to main layout ---
    info_layout.addWidget(box_top)
    info_layout.addWidget(box_bottom)  

    # Add to external layout
    left_layout.addWidget(info_panel)

    # --- Labels dictionary ---
    labels_dict = {
        "val": label_val,
        "mag": label_mag,
        "phase": label_phase,
        "z": label_z,
        "il": label_il,
        "vswr": label_vswr,
        "freq": edit_value,
        "unit": lbl_unit
    }

    # --- Info panel (left side reorganized) duplicate for marker 2 ---
    info_panel_2 = QWidget()
    info_layout_2 = QVBoxLayout(info_panel_2)
    info_layout_2.setSpacing(10)
    info_layout_2.setContentsMargins(0, 0, 0, 0)

    # --- Top QGroupBox with title ---
    box_top_2 = QGroupBox(f"{self.measurement_ui_s_parameter_details_title} 2")
    box_top_2.setStyleSheet(groupbox_style)
    layout_top_2 = QHBoxLayout(box_top_2)
    layout_top_2.setSpacing(20)
    layout_top_2.setContentsMargins(12, 8, 12, 8)

    center_layout_2 = QHBoxLayout()
    center_layout_2.setSpacing(15)
    center_layout_2.setAlignment(Qt.AlignCenter)

    # --- Column 1: Frequency ---
    col_left_2 = QVBoxLayout()
    col_left_2.setSpacing(5)
    col_left_2.setAlignment(Qt.AlignVCenter)

    hbox_freq_2 = QHBoxLayout()
    hbox_freq_2.setAlignment(Qt.AlignLeft)
    hbox_freq_2.setContentsMargins(0, 0, 0, 0)

    lbl_text_2 = QLabel(f"{self.measurement_ui_s_parameter_frequency}")
    lbl_text_2.setStyleSheet("font-size:14px;")
    lbl_text_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    hbox_freq_2.addWidget(lbl_text_2)

    initial_freq_value_2, initial_freq_unit_2 = format_frequency_smart_split(freqs[0])
    edit_value_2 = QLineEdit(initial_freq_value_2)

    def on_text_changed_2():
        new_text = limit_frequency_input(edit_value_2.text(), 3, 3)
        if new_text != edit_value_2.text():
            edit_value_2.setText(new_text)
        text_width = edit_value_2.fontMetrics().horizontalAdvance(edit_value_2.text())
        min_width = max(text_width + 10, 40)
        edit_value_2.setFixedWidth(min_width)

    edit_value_2.textChanged.connect(on_text_changed_2)
    edit_value_2.setStyleSheet("font-size:14px; border:none; background:transparent;")
    edit_value_2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    text_width = edit_value_2.fontMetrics().horizontalAdvance(edit_value_2.text())
    min_width = max(text_width + 10, 40)
    edit_value_2.setFixedWidth(min_width)
    hbox_freq_2.addWidget(edit_value_2)

    lbl_unit_2 = QLabel(initial_freq_unit_2)
    lbl_unit_2.setStyleSheet("font-size:14px;")
    lbl_unit_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    lbl_unit_2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    hbox_freq_2.addWidget(lbl_unit_2)

    col_left_2.addLayout(hbox_freq_2)

    # --- Column 2: S11 real + imag ---
    label_val_2 = QLabel(f"{s_param}: -- + j--")
    label_val_2.setStyleSheet("font-size:14px; padding:1px;")
    label_val_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_s11_2 = QVBoxLayout()
    col_s11_2.setSpacing(5)
    col_s11_2.setAlignment(Qt.AlignVCenter)
    col_s11_2.addWidget(label_val_2)

    # --- Column 3: |S11| ---
    label_mag_2 = QLabel(f"|{s_param}|: --")
    label_mag_2.setStyleSheet("font-size:14px; padding:1px;")
    label_mag_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_mag_2 = QVBoxLayout()
    col_mag_2.setSpacing(5)
    col_mag_2.setAlignment(Qt.AlignVCenter)
    col_mag_2.addWidget(label_mag_2)

    # --- Column 4: Phase ---
    label_phase_2 = QLabel(f"{self.measurement_ui_s_parameter_phase} --")
    label_phase_2.setStyleSheet("font-size:14px; padding:1px;")
    label_phase_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_phase_2 = QVBoxLayout()
    col_phase_2.setSpacing(5)
    col_phase_2.setAlignment(Qt.AlignVCenter)
    col_phase_2.addWidget(label_phase_2)

    # --- Add columns to centered layout ---
    center_layout_2.addLayout(col_left_2)

    label_sep_2 = QLabel("-")
    center_layout_2.addWidget(label_sep_2)

    center_layout_2.addLayout(col_s11_2)

    label_sep_2 = QLabel("-")
    center_layout_2.addWidget(label_sep_2)

    center_layout_2.addLayout(col_mag_2)

    label_sep_2 = QLabel("-")
    center_layout_2.addWidget(label_sep_2)

    center_layout_2.addLayout(col_phase_2)

    layout_top_2.addLayout(center_layout_2)

    # --- Bottom QGroupBox ---
    box_bottom_2 = QGroupBox(f"{self.measurement_ui_dut_parameters_title} 2")
    box_bottom_2.setStyleSheet(groupbox_style)
    layout_bottom_2 = QHBoxLayout(box_bottom_2)
    layout_bottom_2.setSpacing(40)
    layout_bottom_2.setContentsMargins(10, 8, 10, 8)
    layout_bottom_2.setAlignment(Qt.AlignCenter)

    label_z_2 = QLabel(f"{self.measurement_ui_dut_zin} -- + j--")
    label_z_2.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_z_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom_2.addWidget(label_z_2)

    label_sep_2 = QLabel("-")
    layout_bottom_2.addWidget(label_sep_2)

    label_il_2 = QLabel(f"{self.measurement_ui_dut_insertion_loss} -- dB")
    label_il_2.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_il_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom_2.addWidget(label_il_2)

    label_sep_2 = QLabel("-")
    layout_bottom_2.addWidget(label_sep_2)

    label_vswr_2 = QLabel(f"{self.measurement_ui_dut_vswr} --")
    label_vswr_2.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_vswr_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom_2.addWidget(label_vswr_2)

    # --- Add box_bottom to main layout ---
    info_layout_2.addWidget(box_top_2)
    info_layout_2.addWidget(box_bottom_2)

    left_layout.addWidget(info_panel_2)

    # --- Labels dictionary 2 ---
    labels_dict_2 = {
        "val": label_val_2,
        "mag": label_mag_2,
        "phase": label_phase_2,
        "z": label_z_2,
        "il": label_il_2,
        "vswr": label_vswr_2,
        "freq": edit_value_2,
        "unit": lbl_unit_2
    }

    info_panel_2.hide()

    def update_cursor(index = 0, from_slider=False, new_slider=None, return_values=False):
        import os
        from PySide6.QtCore import QSettings

        val_complex = S_data[index]
        magnitude = abs(val_complex)
        phase_deg = np.angle(val_complex, deg=True)

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        current_s_param = s_param

        unit_mode = settings.value("Graphic1/db_times", "dB")

        unit_mode_S11 = settings.value("Graphic1/db_times_S11", "dB")

        if graph_type == "Smith Diagram":
            cursor_graph.set_data([np.real(val_complex)], [np.imag(val_complex)])

        elif graph_type == "Magnitude":
            if current_s_param == "S21":
                if unit_mode == "dB":
                    mag_value = 20 * np.log10(magnitude)
                elif unit_mode == "Power ratio":
                    mag_value = magnitude ** 2
                elif unit_mode == "times":
                    mag_value = magnitude
                else:
                    mag_value = magnitude

            elif current_s_param == "S11":
                if unit_mode_S11 == "dB":
                    mag_value = 20 * np.log10(magnitude)
                elif unit_mode_S11 == "S11 (reflection coefficient)":
                    mag_value = magnitude 
                else:
                    mag_value = magnitude

            cursor_graph.set_xdata([freqs[index] * 1e-6])
            cursor_graph.set_ydata([mag_value])

        elif graph_type == "Phase":
            cursor_graph.set_data([freqs[index] * 1e-6], [phase_deg])

        # === Actualizar labels ===
        freq_value, freq_unit = format_frequency_smart_split(freqs[index])
        edit_value.setText(freq_value)

        text_width = edit_value.fontMetrics().horizontalAdvance(edit_value.text())
        edit_value.setFixedWidth(max(text_width + 10, 50))

        labels_dict["unit"].setText(freq_unit)
        labels_dict["val"].setText(
            f"{current_s_param}: {np.real(val_complex):.3f} {'+' if np.imag(val_complex) >= 0 else '-'} j{abs(np.imag(val_complex)):.3f}"
        )
        labels_dict["mag"].setText(f"|{current_s_param}|: {magnitude:.3f}")
        labels_dict["phase"].setText(f"{self.measurement_ui_s_parameter_phase} {phase_deg:.2f}°")

        z = (1 + val_complex) / (1 - val_complex)
        labels_dict["z"].setText(f"Z: {np.real(z):.2f} + j{np.imag(z):.2f}")

        il_db = -20 * np.log10(magnitude)
        labels_dict["il"].setText(f"{self.measurement_ui_dut_insertion_loss} {il_db:.2f} dB")

        vswr_val = (1 + magnitude) / (1 - magnitude) if magnitude < 1 else np.inf
        labels_dict["vswr"].setText(f"{self.measurement_ui_dut_vswr} {vswr_val:.2f}" if np.isfinite(vswr_val) else f"{self.measurement_ui_dut_vswr} ∞")

        fig.canvas.draw_idle()

        if not from_slider:

            if new_slider is None or getattr(new_slider, "ax", None) is None or getattr(new_slider.ax, "get_figure", lambda: None)() is None:
                logging.warning("Skipping cursor update: new slider or figure no longer exists_1")
                return
            try:
                new_slider.set_val(0)
            except Exception as e:
                logging.warning(f"Failed to set slider value: {e}")
                return

        edit_value.clearFocus()

        settings.setValue("Cursor_1_1/index", index)

        if return_values:
            return {
                "freq": freqs[index],
                "mag": magnitude,
                "phase": phase_deg,
                "val_complex": val_complex
            }

    def update_cursor_2(index = 0, from_slider=False, new_slider_2=None, return_values=False):
        import os
        from PySide6.QtCore import QSettings

        val_complex = S_data[index]
        magnitude = abs(val_complex)
        phase_deg = np.angle(val_complex, deg=True)

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        current_s_param = s_param

        unit_mode = settings.value("Graphic1/db_times", "dB")

        unit_mode_S11 = settings.value("Graphic1/db_times_S11", "S11 (reflection coefficient)")

        # === Actualizar cursor según graph_type y unidad ===
        if graph_type == "Smith Diagram":
            cursor_graph_2.set_data([np.real(val_complex)], [np.imag(val_complex)])

        elif graph_type == "Magnitude":
        
            if current_s_param == "S21":
                if unit_mode == "dB":
                    mag_value = 20 * np.log10(magnitude)
                elif unit_mode == "Power ratio":
                    mag_value = magnitude ** 2
                elif unit_mode == "times":
                    mag_value = magnitude
                else:
                    mag_value = magnitude

            elif current_s_param == "S11":
                if unit_mode_S11 == "dB":
                    mag_value = 20 * np.log10(magnitude)
                elif unit_mode_S11 == "S11 (reflection coefficient)":
                    mag_value = magnitude 
                else:
                    mag_value = magnitude

            cursor_graph_2.set_xdata([freqs[index] * 1e-6])
            cursor_graph_2.set_ydata([mag_value])

        elif graph_type == "Phase":
            cursor_graph_2.set_data([freqs[index] * 1e-6], [phase_deg])

        # === Actualizar labels del panel 2 ===
        freq_value, freq_unit = format_frequency_smart_split(freqs[index])
        edit_value_2.setText(freq_value)
        text_width = edit_value_2.fontMetrics().horizontalAdvance(edit_value_2.text())
        edit_value_2.setFixedWidth(max(text_width + 10, 50))

        labels_dict_2["unit"].setText(freq_unit)
        labels_dict_2["val"].setText(
            f"{current_s_param}: {np.real(val_complex):.3f} {'+' if np.imag(val_complex) >= 0 else '-'} j{abs(np.imag(val_complex)):.3f}"
        )
        labels_dict_2["mag"].setText(f"|{current_s_param}|: {magnitude:.3f}")
        labels_dict_2["phase"].setText(f"{self.measurement_ui_s_parameter_phase} {phase_deg:.2f}°")

        z = (1 + val_complex) / (1 - val_complex)
        labels_dict_2["z"].setText(f"Z: {np.real(z):.2f} + j{np.imag(z):.2f}")

        il_db = -20 * np.log10(magnitude)
        labels_dict_2["il"].setText(f"{self.measurement_ui_dut_insertion_loss} {il_db:.2f} dB")

        vswr_val = (1 + magnitude) / (1 - magnitude) if magnitude < 1 else np.inf
        labels_dict_2["vswr"].setText(f"{self.measurement_ui_dut_vswr} {vswr_val:.2f}" if np.isfinite(vswr_val) else f"{self.measurement_ui_dut_vswr} ∞")

        fig.canvas.draw_idle()

        if not from_slider:
            if new_slider_2 is None or getattr(new_slider_2, "ax", None) is None or getattr(new_slider_2.ax, "get_figure", lambda: None)() is None:
                logging.warning("Skipping cursor update: new slider or figure no longer exists")
                return
            try:
                new_slider_2.set_val(index)
            except Exception as e:
                logging.warning(f"Failed to set slider value: {e}")
                return

        edit_value_2.clearFocus()
        settings.setValue("Cursor_2_1/index", index)

        if return_values:
            return {
                "freq": freqs[index],
                "mag": magnitude,
                "phase": phase_deg,
                "val_complex": val_complex
            }

    # --- Slider ---

    if fig is not None:
        slider_ax = fig.add_axes([0.25,0.04,0.5,0.03], facecolor='lightgray')
        slider = Slider(slider_ax, '', 0, len(freqs)-1, valinit=0, valstep=1)
        slider.vline.set_visible(False)
        slider.label.set_visible(False)
        slider.valtext.set_visible(False)  # Hide the value text
        slider.on_changed(lambda val: update_cursor(int(val), from_slider=True))

        slider_ax_2 = fig.add_axes([0.55,0.04,0.35,0.03], facecolor='lightgray')
        slider_2 = Slider(slider_ax_2, '', 0, len(freqs)-1, valinit=0, valstep=1)
        slider_2.vline.set_visible(False)
        slider_2.label.set_visible(False)
        slider_2.valtext.set_visible(False)  # Hide the value text
        slider_2.ax.set_visible(False)
    
    def freq_edited(new_slider=None):
        try:
            freq_hz = parse_frequency_input(edit_value.text())
            if freq_hz is not None:
                index = np.argmin(np.abs(freqs - freq_hz))
                update_cursor(index, from_slider=False, new_slider=new_slider)
            edit_value.clearFocus()
        except:
            pass

    edit_value.editingFinished.connect(freq_edited)

    def freq_edited_2(new_slider=None):

        if new_slider is None:
            logging.warning("freq_edited_2 called with new_slider=None")
        else:
            logging.info("freq_edited_2 called with valid new_slider")

        try:
            freq_hz = parse_frequency_input(edit_value_2.text())
            if freq_hz is not None:
                index = np.argmin(np.abs(freqs - freq_hz))
                update_cursor_2(index, from_slider=False, new_slider=new_slider)
            edit_value_2.clearFocus()
        except:
            pass
    edit_value_2.editingFinished.connect(freq_edited_2)

    # --- Cursor draggable ---
    dragging_1 = {"active": False}
    dragging_2 = {"active": False}

    def on_pick(event):
        if event.artist == cursor_graph:
            dragging_1["active"] = True
        elif event.artist == cursor_graph_2:
            dragging_2["active"] = True

    def on_release(event):
        dragging_1["active"] = False
        dragging_2["active"] = False

    def on_motion(event):
        if event.inaxes != ax:
            return

        if dragging_1["active"]:
            if graph_type in ["Magnitude", "Phase"]:
                mouse_x = event.xdata
                index = np.argmin(np.abs(freqs*1e-6 - mouse_x))
                update_cursor(index)
            else:
                mouse_point = complex(event.xdata, event.ydata)
                distances = np.abs(S_data - mouse_point)
                index = np.argmin(distances)
                update_cursor(index)

        elif dragging_2["active"]:
            if graph_type in ["Magnitude", "Phase"]:
                mouse_x = event.xdata
                index = np.argmin(np.abs(freqs*1e-6 - mouse_x))
                update_cursor_2(index)
            else:
                mouse_point = complex(event.xdata, event.ydata)
                distances = np.abs(S_data - mouse_point)
                index = np.argmin(distances)
                update_cursor_2(index)

    # --- Conectar eventos ---
    cursor_graph.set_picker(5)
    cursor_graph_2.set_picker(5)

    canvas.mpl_connect("pick_event", on_pick)
    canvas.mpl_connect("button_release_event", on_release)
    canvas.mpl_connect("motion_notify_event", on_motion)

    def remove_slider(slider, fig, canvas):
        """Safely remove a matplotlib Slider from the figure.
        This releases widget locks, disconnects callbacks, removes the slider axis,
        forces a canvas redraw and triggers garbage collection.
        """
        if slider is None:
            return

        try:
            # 1) Try to release any widget lock that may be held by the figure.
            #    widgetlock.locked() may return a widget or False; call release safely.
            try:
                locked = fig.canvas.widgetlock.locked()
                # If locked is truthy and has 'release' semantics, release it.
                if locked:
                    # Try to release by passing the widget if possible
                    try:
                        fig.canvas.widgetlock.release(locked)
                    except Exception:
                        # fallback: try releasing with slider.ax (if applicable)
                        try:
                            fig.canvas.widgetlock.release(slider.ax)
                        except Exception:
                            pass
            except Exception:
                # Some backends may behave slightly differently; ignore fail here
                pass

            # 2) Disconnect slider internal callbacks to avoid lingering references
            try:
                if hasattr(slider, "_observers") and "changed" in slider._observers.callbacks:
                    for cid in list(slider._observers.callbacks["changed"].keys()):
                        slider._observers.disconnect(cid)
            except Exception:
                pass

            # 3) Remove the slider axis from the figure (this makes it disappear)
            try:
                if slider.ax in fig.axes:
                    fig.delaxes(slider.ax)
            except Exception:
                pass

            # 4) Force a redraw to update the visual state
            try:
                if canvas is not None:
                    canvas.draw_idle()
            except Exception:
                pass

            # 5) Delete the python object and call garbage collector
            try:
                # remove attributes that may hold references
                try:
                    slider.ax = None
                except Exception:
                    pass
                del slider
                gc.collect()
            except Exception:
                pass

        except Exception as e:
            print("Warning in remove_slider:", e)

    def fully_disable_slider(slider):
        """Disconnect all event callbacks and disable slider logic without removing ax yet."""
        if slider is None:
            return

        # Disconnect user callback registered through on_changed()
        try:
            for cid in list(slider._observers.callbacks.get("changed", {}).keys()):
                slider._observers.disconnect(cid)
        except Exception:
            pass

        # Disable slider internal mouse update behavior
        try:
            if hasattr(slider, "disconnect_events"):
                slider.disconnect_events()
        except Exception:
            pass

        # Disable axes interaction temporarily (prevents contains() call)
        try:
            if slider.ax is not None:
                slider.ax.set_navigate(False)
        except Exception:
            pass

    def update_data_references(new_s_data, new_freqs, old_slider=None, old_slider_2=None, 
        canvas=None, fig=None, show_graphic1_marker1=False, show_graphic1_marker2=True, marker1=None, marker2=None,
        info_panel=None, info_panel_2=None, new_s_param=None):

        """Update S_data and freqs and recreate slider safely using remove_slider()."""
        nonlocal S_data, freqs, s_param
        S_data = new_s_data
        freqs = new_freqs
        if new_s_param is not None:
            s_param = new_s_param

        if old_slider is not None:
            try:
                old_slider.disconnect_events() 
            except Exception:
                pass

            # Libera widgetlock si está ocupado
            try:
                locked = fig.canvas.widgetlock.locked()
                if locked:
                    fig.canvas.widgetlock.release(locked)
            except Exception:
                pass

            remove_slider(old_slider, fig, canvas)
            old_slider = None

        if old_slider_2 is not None:
            try:
                old_slider_2.disconnect_events() 
            except Exception:
                pass

            # Libera widgetlock si está ocupado
            try:
                locked = fig.canvas.widgetlock.locked()
                if locked:
                    fig.canvas.widgetlock.release(locked)
            except Exception:
                pass

            remove_slider(old_slider_2, fig, canvas)
            old_slider_2 = None

        # Remove the old slider safely (if provided)
        if old_slider is not None:
            try:
                remove_slider(old_slider, fig, canvas)
            except Exception as e:
                print("⚠️ Warning removing old slider:", e)

        if old_slider_2 is not None:
            try:
                remove_slider(old_slider_2, fig, canvas)
            except Exception as e:
                print("⚠️ Warning removing old slider:", e)

        if old_slider is not None:
            fully_disable_slider(old_slider)  
            if old_slider.ax in fig.axes:
                fig.delaxes(old_slider.ax)
            old_slider = None  
            canvas.draw_idle()

        if old_slider_2 is not None:
            fully_disable_slider(old_slider_2) 
            if old_slider_2.ax in fig.axes:
                fig.delaxes(old_slider_2.ax)
            old_slider_2 = None 
            canvas.draw_idle()

        # Optionally ensure the global widgetlock is free before creating a new slider
        try:
            locked = fig.canvas.widgetlock.locked()
            if locked:
                try:
                    fig.canvas.widgetlock.release(locked)
                except Exception:
                    try:
                        # fallback
                        fig.canvas.widgetlock.release(None)
                    except Exception:
                        pass
        except Exception:
            pass

        if show_graphic1_marker1 and not show_graphic1_marker2:
            new_slider_ax = fig.add_axes([0.25, 0.04, 0.5, 0.03], facecolor='lightgray')
            new_slider_ax_2 = fig.add_axes([0.55,0.04,0.35,0.03], facecolor='lightgray')

            # Create a new slider in the same figure

            new_slider = Slider(new_slider_ax, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)
            new_slider_2 = Slider(new_slider_ax_2, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)

            new_slider_ax.set_visible(True)
            new_slider_ax_2.set_visible(False)

            info_panel_2.hide()
            info_panel.show()

            marker1.set_visible(True)
            marker2.set_visible(False)

        elif not show_graphic1_marker1 and show_graphic1_marker2:
            new_slider_ax = fig.add_axes([0.15,0.04,0.35,0.03], facecolor='lightgray')
            new_slider_ax_2 = fig.add_axes([0.25, 0.04, 0.5, 0.03], facecolor='lightgray')

            # Create a new slider in the same figure

            new_slider = Slider(new_slider_ax, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)
            new_slider_2 = Slider(new_slider_ax_2, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)

            new_slider_ax.set_visible(False)
            new_slider_ax_2.set_visible(True)

            info_panel_2.show()
            info_panel.hide()

            marker1.set_visible(False)
            marker2.set_visible(True)

            canvas.draw_idle()

            marker1.figure.canvas.draw_idle()

        elif show_graphic1_marker1 and show_graphic1_marker2:

            new_slider_ax = fig.add_axes([0.1,0.04,0.35,0.03], facecolor='lightgray')
            new_slider_ax_2 = fig.add_axes([0.55,0.04,0.35,0.03], facecolor='lightgray')

            # Create a new slider in the same figure

            new_slider = Slider(new_slider_ax, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)
            new_slider_2 = Slider(new_slider_ax_2, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)

            new_slider_ax.set_visible(True)
            new_slider_ax_2.set_visible(True)

            marker1.set_visible(True)
            marker2.set_visible(True)  

        elif not show_graphic1_marker1 and not show_graphic1_marker2:

            new_slider_ax = fig.add_axes([0.25,0.04,0.35,0.03], facecolor='lightgray')
            new_slider_ax_2 = fig.add_axes([0.55,0.04,0.35,0.03], facecolor='lightgray')

            # Create a new slider in the same figure

            new_slider = Slider(new_slider_ax, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)
            new_slider_2 = Slider(new_slider_ax_2, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)

            new_slider_ax.set_visible(False)
            new_slider_ax_2.set_visible(False)  

            marker1.set_visible(False)
            marker2.set_visible(False)

        canvas.draw_idle()
  
        # Hide unused slider UI elements
        new_slider.vline.set_visible(False)
        new_slider.label.set_visible(False)
        new_slider.valtext.set_visible(False)

        # Hide unused slider UI elements
        new_slider_2.vline.set_visible(False)
        new_slider_2.label.set_visible(False)
        new_slider_2.valtext.set_visible(False)

        # Reconnect edit_value callback so it uses updated freqs
        def freq_edited_local():
            try:
                freq_hz = parse_frequency_input(edit_value.text())
                if freq_hz is not None:
                    index = np.argmin(np.abs(new_freqs - freq_hz))
                    update_cursor(index)
                edit_value.clearFocus()
            except Exception as e:
                print("Edit freq error:", e)

        try:
            edit_value.editingFinished.disconnect()
        except Exception:
            pass

        edit_value.editingFinished.connect(freq_edited_local)

        def freq_edited_2_local():
            try:
                freq_hz = parse_frequency_input(edit_value_2.text())
                if freq_hz is not None:
                    index = np.argmin(np.abs(new_freqs - freq_hz))
                    update_cursor_2(index)
                edit_value_2.clearFocus()
            except Exception as e:
                print("Edit freq 2 error:", e)

        try:
            edit_value_2.editingFinished.disconnect()
        except Exception:
            pass

        edit_value_2.editingFinished.connect(freq_edited_2_local)

        # Final redraw
        try:
            if canvas is not None:
                canvas.draw_idle()
        except Exception:
            pass

        # Update marker visibility
        if marker1 is not None:
            marker1.set_visible(show_graphic1_marker1)
        if marker2 is not None:
            marker2.set_visible(show_graphic1_marker2)

        # Redraw the canvas to reflect changes
        if canvas is not None:
            canvas.draw_idle()

        return new_slider, new_slider_2

    def update_data_references_2(new_s_data, new_freqs):
        nonlocal S_data, freqs
        S_data = new_s_data
        freqs = new_freqs
        # Update freq_edited function to use new freqs
        def freq_edited():
            try:
                freq_hz = parse_frequency_input(edit_value.text())
                if freq_hz is not None:
                    index = np.argmin(np.abs(freqs - freq_hz))
                    update_cursor_2(index)
                edit_value.clearFocus()
            except:
                pass
        edit_value.editingFinished.disconnect()
        edit_value.editingFinished.connect(freq_edited)

    def update_s_param_only(new_s_param):
        nonlocal s_param
        s_param = new_s_param
    
    return left_panel, info_panel, info_panel_2, fig, ax, canvas, slider, slider_2, cursor_graph, cursor_graph_2, labels_dict, labels_dict_2, update_cursor, update_cursor_2, update_data_references, update_data_references_2, update_s_param_only, freq_edited, freq_edited_2

#############################################################################################
# =================== RIGHT PANEL ========================================================= #
#############################################################################################

def create_right_panel(self, settings, S_data=None, freqs=None, graph_type="Smith Diagram", s_param="S11",
                       tracecolor="red", markercolor="red", marker2color="red", linewidth=2, markersize=5, marker2size=5, marker_visible=True):
    
    # ----------------------------------------------------
    # Plot Manager settings
    # ----------------------------------------------------

    self.settings = get_settings(
        "INI/dut_measurement/plot_manager/plot_manager.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/plot_manager.ini",
        Path(__file__).resolve()
    )

    # ----------------------------------------------------
    # Colors and styles from settings
    # ----------------------------------------------------

    background_color_graphics = settings.value("Graphic2/BackgroundColor", "red")
    text_color = settings.value("Graphic2/TextColor", "red")
    axis_color = settings.value("Graphic2/AxisColor", "red")
    unit_mode = settings.value("Graphic2/db_times", "dB")

    # QGroupBox border styling based on dark/light mode
    groupbox_border = settings.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")
    groupbox_style = f"QGroupBox {{ border: {groupbox_border}; border-radius: 5px; margin-top: 1ex; padding-top: 10px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }}"

    freqs = freqs if freqs is not None else np.linspace(1e6, 100e6, 101)
    
    if S_data is None:
        phase = -2*np.pi*freqs/1e8
        S_data = 0.5 * np.exp(1j*phase)

    right_panel = QWidget()
    right_layout = QVBoxLayout(right_panel)
    right_layout.setAlignment(Qt.AlignTop)
    right_layout.setContentsMargins(10,10,10,10)
    right_layout.setSpacing(10)

    # --- Figure ---
    if graph_type == "Smith Diagram":
        # Use consolidated Smith chart functionality
        from ......utils.smith_chart_utils import SmithChartConfig, SmithChartManager
        
        # Create custom config to match original settings
        config = SmithChartConfig()
        config.background_color = background_color_graphics
        config.axis_color = axis_color
        config.text_color = axis_color
        config.trace_color = tracecolor
        config.marker_color = markercolor
        config.linewidth = linewidth
        config.markersize = markersize
        config.marker_visible = marker_visible
        
        # Create Smith chart with custom configuration
        manager = SmithChartManager(config)
        fig, ax, canvas, cursor_graph, cursor_graph_2 = manager.create_graphics_panel_smith_chart(
            s_data=S_data,
            freqs=freqs,
            s_param=s_param,
            figsize=(5, 5),
            container_layout=right_layout,
            trace_color=tracecolor,
            marker_color=markercolor
        )

    elif graph_type == "Magnitude":
        fig, ax = plt.subplots(figsize=(4,3))
        fig.subplots_adjust(left=0.22, right=0.8, top=0.8, bottom=0.22)

        fig.patch.set_facecolor(f"{background_color_graphics}")
        ax.set_facecolor(f"{background_color_graphics}")

        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(canvas)

        ax.plot(freqs*1e-6, np.abs(S_data), color=tracecolor, marker='.', linestyle='-', linewidth=linewidth)

        ax.set_xlabel(rf"$\mathrm{{{self.measurement_ui_magnitude_x_axis}}}$", color=text_color)
        ax.set_ylabel(r"$|%s|$" % s_param, color=text_color)
        ax.set_title(rf"${self.measurement_ui_magnitude_title.format(parameter=s_param, db_times=unit_mode)}$", color=f"{text_color}")

        # Set X-axis limits with margins to match actual frequency range of the sweep
        freq_start = freqs[0]*1e-6
        freq_end = freqs[-1]*1e-6
        freq_range = freq_end - freq_start
        margin = freq_range * 0.05  # 5% margin on each side
        ax.set_xlim(freq_start - margin, freq_end + margin)
        # Set Y-axis limits with margins to provide visual spacing
        magnitude_data = np.abs(S_data)
        y_min = np.min(magnitude_data)
        y_max = np.max(magnitude_data)
        y_range = y_max - y_min
        y_margin = y_range * 0.05  # 5% margin on each side
        ax.set_ylim(y_min - y_margin, y_max + y_margin)
        ax.autoscale(False)  # Prevent matplotlib from overriding our xlim/ylim settings
        ax.tick_params(axis='x', colors=f"{axis_color}")
        ax.tick_params(axis='y', colors=f"{axis_color}")

        for spine in ax.spines.values():
            spine.set_color("white")

        current_state_grid = self.settings.value(f"grid/current_right_state", "true", type=bool)

            
        ax.grid(current_state_grid, which='both', axis='both', color='white', linestyle='--', linewidth=0.5, alpha=0.3, zorder=1)

        cursor_graph, = ax.plot([], [], 'o', markersize=markersize, color=markercolor, visible=marker_visible)
        cursor_graph_2, = ax.plot([], [], 'o', markersize=marker2size, color=marker2color, visible=False)

    elif graph_type == "Phase":
        fig, ax = plt.subplots(figsize=(4,3))
        fig.subplots_adjust(left=0.22, right=0.8, top=0.8, bottom=0.22)

        fig.patch.set_facecolor(f"{background_color_graphics}")
        ax.set_facecolor(f"{background_color_graphics}")

        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(canvas)

        ax.plot(freqs*1e-6, np.angle(S_data, deg=True), color=tracecolor, marker='.', linestyle='-', linewidth=linewidth)

        ax.set_xlabel(rf"$\mathrm{{{self.measurement_ui_magnitude_x_axis}}}$", color=f"{text_color}")
        ax.set_ylabel(r"$\phi_{%s}\ [^\circ]$" % s_param, color=f"{text_color}")
        ax.set_title(rf"$\mathrm{{{self.measurement_ui_phase_title.format(parameter=s_param)}}}$", color=f"{text_color}")

        # Set X-axis limits with margins to match actual frequency range of the sweep
        freq_start = freqs[0]*1e-6
        freq_end = freqs[-1]*1e-6
        freq_range = freq_end - freq_start
        margin = freq_range * 0.05  # 5% margin on each side
        ax.set_xlim(freq_start - margin, freq_end + margin)
        # Set Y-axis limits with margins to provide visual spacing
        phase_data = np.angle(S_data, deg=True)
        y_min = np.min(phase_data)
        y_max = np.max(phase_data)
        y_range = y_max - y_min
        y_margin = y_range * 0.05  # 5% margin on each side
        ax.set_ylim(y_min - y_margin, y_max + y_margin)
        ax.autoscale(False)  # Prevent matplotlib from overriding our xlim/ylim settings
        ax.tick_params(axis='x', colors=f"{axis_color}")
        ax.tick_params(axis='y', colors=f"{axis_color}")

        for spine in ax.spines.values():
            spine.set_color("white")

        current_state_grid = self.settings.value(f"grid/current_right_state", "true", type=bool)
            
        ax.grid(current_state_grid, which='both', axis='both', color='white', linestyle='--', linewidth=0.5, alpha=0.3, zorder=1)
        
        cursor_graph, = ax.plot([], [], 'o', markersize=markersize, color=markercolor, visible=marker_visible)
        cursor_graph_2, = ax.plot([], [], 'o', markersize=marker2size, color=marker2color, visible=False)

    # --- Info panel (Right side reorganized) ---
    info_panel = QWidget()
    info_layout = QVBoxLayout(info_panel)
    info_layout.setSpacing(10)
    info_layout.setContentsMargins(0, 0, 0, 0)

    # --- Top QGroupBox with title ---
    box_top = QGroupBox(f"{self.measurement_ui_s_parameter_details_title}")
    box_top.setStyleSheet(groupbox_style)
    layout_top = QHBoxLayout(box_top)
    layout_top.setSpacing(20)
    layout_top.setContentsMargins(12, 8, 12, 8)  # balanced margins

    # --- Centered sub-layout for the 4 blocks ---
    center_layout = QHBoxLayout()
    center_layout.setSpacing(15)  # space between columns
    center_layout.setAlignment(Qt.AlignCenter)  # everything centered in the box

    # --- Column 1: Frequency ---
    col_left = QVBoxLayout()
    col_left.setSpacing(5)
    col_left.setAlignment(Qt.AlignVCenter)

    hbox_freq = QHBoxLayout()
    hbox_freq.setAlignment(Qt.AlignLeft)
    hbox_freq.setContentsMargins(0, 0, 0, 0)

    lbl_text = QLabel(f"{self.measurement_ui_s_parameter_frequency}")
    lbl_text.setStyleSheet("font-size:14px;")
    lbl_text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    hbox_freq.addWidget(lbl_text)

    initial_freq_value, initial_freq_unit = format_frequency_smart_split(freqs[0])
    edit_value = QLineEdit(initial_freq_value)

    def limit_frequency_input(text, max_digits=6, max_decimals=3, allow_dashes=False):
        if text == "--":  # allow dashes
            return text
        filtered = "".join(c for c in text if c.isdigit() or c == ".")
        if filtered.count(".") > 1:
            parts = filtered.split(".", 1)
            filtered = parts[0] + "." + "".join(parts[1:]).replace(".", "")
        if "." in filtered:
            integer_part, decimal_part = filtered.split(".", 1)
            integer_part = integer_part[:max_digits]
            decimal_part = decimal_part[:max_decimals]
            filtered = integer_part + "." + decimal_part
        else:
            filtered = filtered[:max_digits]
        return filtered

    def on_text_changed():
        new_text = limit_frequency_input(edit_value.text(), 3, 3, allow_dashes=True)
        if new_text != edit_value.text():
            edit_value.setText(new_text)
        if new_text != edit_value.text():
            edit_value.setText(new_text)
        text_width = edit_value.fontMetrics().horizontalAdvance(edit_value.text())
        min_width = max(text_width + 10, 40)
        edit_value.setFixedWidth(min_width)

    edit_value.textChanged.connect(on_text_changed)
    edit_value.setStyleSheet("font-size:14px; border:none; background:transparent;")
    edit_value.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    text_width = edit_value.fontMetrics().horizontalAdvance(edit_value.text())
    min_width = max(text_width + 10, 40)
    edit_value.setFixedWidth(min_width)
    hbox_freq.addWidget(edit_value)

    lbl_unit = QLabel(initial_freq_unit)
    lbl_unit.setStyleSheet("font-size:14px;")
    lbl_unit.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    lbl_unit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    hbox_freq.addWidget(lbl_unit)

    col_left.addLayout(hbox_freq)

    # --- Column 2: S11 real + imag ---
    label_val = QLabel(f"{s_param}: -- + j--")
    label_val.setStyleSheet("font-size:14px; padding:1px;")
    label_val.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_s11 = QVBoxLayout()
    col_s11.setSpacing(5)
    col_s11.setAlignment(Qt.AlignVCenter)
    col_s11.addWidget(label_val)

    # --- Column 3: |S11| ---
    label_mag = QLabel(f"|{s_param}|: --")
    label_mag.setStyleSheet("font-size:14px; padding:1px;")
    label_mag.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_mag = QVBoxLayout()
    col_mag.setSpacing(5)
    col_mag.setAlignment(Qt.AlignVCenter)
    col_mag.addWidget(label_mag)

    # --- Column 4: Phase ---
    label_phase = QLabel(f"{self.measurement_ui_s_parameter_phase} --")
    label_phase.setStyleSheet("font-size:14px; padding:1px;")
    label_phase.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_phase = QVBoxLayout()
    col_phase.setSpacing(5)
    col_phase.setAlignment(Qt.AlignVCenter)
    col_phase.addWidget(label_phase)

    # --- Add columns to centered layout with separators ---
    center_layout.addLayout(col_left)

    label_sep = QLabel("-")
    center_layout.addWidget(label_sep)

    center_layout.addLayout(col_s11)

    label_sep = QLabel("-")
    center_layout.addWidget(label_sep)

    center_layout.addLayout(col_mag)
    
    label_sep = QLabel("-")
    center_layout.addWidget(label_sep)
    
    center_layout.addLayout(col_phase)

    # --- Add Layout ---
    layout_top.addLayout(center_layout)

    # --- Bottom QGroupBox ---
    box_bottom = QGroupBox(f"{self.measurement_ui_dut_parameters_title}")
    box_bottom.setStyleSheet(groupbox_style)
    layout_bottom = QHBoxLayout(box_bottom)
    layout_bottom.setSpacing(40) 
    layout_bottom.setContentsMargins(10, 8, 10, 8)
    layout_bottom.setAlignment(Qt.AlignCenter)  

    # --- Labels dentro del box_bottom ---
    label_z = QLabel(f"{self.measurement_ui_dut_zin} -- + j--")
    label_z.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_z.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom.addWidget(label_z)

    label_sep = QLabel("-")
    layout_bottom.addWidget(label_sep)

    label_il = QLabel(f"{self.measurement_ui_dut_insertion_loss} -- dB")
    label_il.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_il.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom.addWidget(label_il)

    label_sep = QLabel("-")
    layout_bottom.addWidget(label_sep)

    label_vswr = QLabel(f"{self.measurement_ui_dut_vswr} --")
    label_vswr.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_vswr.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom.addWidget(label_vswr)

    info_layout.addWidget(box_top)
    info_layout.addWidget(box_bottom) 

    # Add to external layout
    right_layout.addWidget(info_panel)

    # --- Labels dictionary ---
    labels_dict = {
        "val": label_val,
        "mag": label_mag,
        "phase": label_phase,
        "z": label_z,
        "il": label_il,
        "vswr": label_vswr,
        "freq": edit_value,
        "unit": lbl_unit
    }

    # --- Info panel (Right side reorganized) duplicate for marker 2 ---
    info_panel_2 = QWidget()
    info_layout_2 = QVBoxLayout(info_panel_2)
    info_layout_2.setSpacing(10)
    info_layout_2.setContentsMargins(0, 0, 0, 0)

    # --- Top QGroupBox with title ---
    box_top_2 = QGroupBox(f"{self.measurement_ui_s_parameter_details_title} 2")
    box_top_2.setStyleSheet(groupbox_style)
    layout_top_2 = QHBoxLayout(box_top_2)
    layout_top_2.setSpacing(20)
    layout_top_2.setContentsMargins(12, 8, 12, 8)

    center_layout_2 = QHBoxLayout()
    center_layout_2.setSpacing(15)
    center_layout_2.setAlignment(Qt.AlignCenter)

    # --- Column 1: Frequency ---
    col_left_2 = QVBoxLayout()
    col_left_2.setSpacing(5)
    col_left_2.setAlignment(Qt.AlignVCenter)

    hbox_freq_2 = QHBoxLayout()
    hbox_freq_2.setAlignment(Qt.AlignLeft)
    hbox_freq_2.setContentsMargins(0, 0, 0, 0)

    lbl_text_2 = QLabel(f"{self.measurement_ui_s_parameter_frequency}")
    lbl_text_2.setStyleSheet("font-size:14px;")
    lbl_text_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    hbox_freq_2.addWidget(lbl_text_2)

    initial_freq_value_2, initial_freq_unit_2 = format_frequency_smart_split(freqs[0])
    edit_value_2 = QLineEdit(initial_freq_value_2)

    def on_text_changed_2():
        new_text = limit_frequency_input(edit_value_2.text(), 3, 3, allow_dashes=True)
        if new_text != edit_value_2.text():
            edit_value_2.setText(new_text)
        text_width = edit_value_2.fontMetrics().horizontalAdvance(edit_value_2.text())
        min_width = max(text_width + 10, 40)
        edit_value_2.setFixedWidth(min_width)

    edit_value_2.textChanged.connect(on_text_changed_2)
    edit_value_2.setStyleSheet("font-size:14px; border:none; background:transparent;")
    edit_value_2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    text_width = edit_value_2.fontMetrics().horizontalAdvance(edit_value_2.text())
    min_width = max(text_width + 10, 40)
    edit_value_2.setFixedWidth(min_width)
    hbox_freq_2.addWidget(edit_value_2)

    lbl_unit_2 = QLabel(initial_freq_unit_2)
    lbl_unit_2.setStyleSheet("font-size:14px;")
    lbl_unit_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    lbl_unit_2.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    hbox_freq_2.addWidget(lbl_unit_2)

    col_left_2.addLayout(hbox_freq_2)

    # --- Column 2: S11 real + imag ---
    label_val_2 = QLabel(f"{s_param}: -- + j--")
    label_val_2.setStyleSheet("font-size:14px; padding:1px;")
    label_val_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_s11_2 = QVBoxLayout()
    col_s11_2.setSpacing(5)
    col_s11_2.setAlignment(Qt.AlignVCenter)
    col_s11_2.addWidget(label_val_2)

    # --- Column 3: |S11| ---
    label_mag_2 = QLabel(f"|{s_param}|: --")
    label_mag_2.setStyleSheet("font-size:14px; padding:1px;")
    label_mag_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_mag_2 = QVBoxLayout()
    col_mag_2.setSpacing(5)
    col_mag_2.setAlignment(Qt.AlignVCenter)
    col_mag_2.addWidget(label_mag_2)

    # --- Column 4: Phase ---
    label_phase_2 = QLabel(f"{self.measurement_ui_s_parameter_phase} --")
    label_phase_2.setStyleSheet("font-size:14px; padding:1px;")
    label_phase_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    col_phase_2 = QVBoxLayout()
    col_phase_2.setSpacing(5)
    col_phase_2.setAlignment(Qt.AlignVCenter)
    col_phase_2.addWidget(label_phase_2)

    # --- Add columns to centered layout ---
    center_layout_2.addLayout(col_left_2)

    label_sep_2 = QLabel("-")
    center_layout_2.addWidget(label_sep_2)

    center_layout_2.addLayout(col_s11_2)

    label_sep_2 = QLabel("-")
    center_layout_2.addWidget(label_sep_2)

    center_layout_2.addLayout(col_mag_2)

    label_sep_2 = QLabel("-")
    center_layout_2.addWidget(label_sep_2)

    center_layout_2.addLayout(col_phase_2)

    layout_top_2.addLayout(center_layout_2)

    # --- Bottom QGroupBox ---
    box_bottom_2 = QGroupBox(f"{self.measurement_ui_dut_parameters_title} 2")
    box_bottom_2.setStyleSheet(groupbox_style)
    layout_bottom_2 = QHBoxLayout(box_bottom_2)
    layout_bottom_2.setSpacing(40)
    layout_bottom_2.setContentsMargins(10, 8, 10, 8)
    layout_bottom_2.setAlignment(Qt.AlignCenter)

    label_z_2 = QLabel(f"{self.measurement_ui_dut_zin} -- + j--")
    label_z_2.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_z_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom_2.addWidget(label_z_2)

    label_sep_2 = QLabel("-")
    layout_bottom_2.addWidget(label_sep_2)

    label_il_2 = QLabel(f"{self.measurement_ui_dut_insertion_loss} -- dB")
    label_il_2.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_il_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom_2.addWidget(label_il_2)

    label_sep_2 = QLabel("-")
    layout_bottom_2.addWidget(label_sep_2)

    label_vswr_2 = QLabel(f"{self.measurement_ui_dut_vswr} --")
    label_vswr_2.setStyleSheet("font-size:14px; padding:1px; border:none; background:transparent;")
    label_vswr_2.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    layout_bottom_2.addWidget(label_vswr_2)

    info_layout_2.addWidget(box_top_2)
    info_layout_2.addWidget(box_bottom_2)

    right_layout.addWidget(info_panel_2)

    # --- Labels dictionary 2 ---
    labels_dict_2 = {
        "val": label_val_2,
        "mag": label_mag_2,
        "phase": label_phase_2,
        "z": label_z_2,
        "il": label_il_2,
        "vswr": label_vswr_2,
        "freq": edit_value_2,
        "unit": lbl_unit_2
    }

    info_panel_2.hide()

    def update_cursor(index = 0, from_slider=False, new_slider=None, return_values = False):
        val_complex = S_data[index]
        magnitude = abs(val_complex)
        phase_deg = np.angle(val_complex, deg=True)

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        current_s_param = s_param

        unit_mode = settings.value("Graphic1/db_times", "dB")

        unit_mode_S11 = settings.value("Graphic1/db_times_S11", "dB")

        if graph_type == "Smith Diagram":
            cursor_graph.set_data([np.real(val_complex)], [np.imag(val_complex)])
        elif graph_type == "Magnitude":
            if current_s_param == "S21":
                if unit_mode == "dB":
                    mag_value = 20 * np.log10(magnitude)
                elif unit_mode == "Power ratio":
                    mag_value = magnitude ** 2
                elif unit_mode == "times":
                    mag_value = magnitude
                else:
                    mag_value = magnitude

            elif current_s_param == "S11":
                if unit_mode_S11 == "dB":
                    mag_value = 20 * np.log10(magnitude)
                elif unit_mode_S11 == "S11 (reflection coefficient)":
                    mag_value = magnitude 
                else:
                    mag_value = magnitude

            cursor_graph.set_xdata([freqs[index] * 1e-6])
            cursor_graph.set_ydata([mag_value])
        elif graph_type == "Phase":
            cursor_graph.set_data([freqs[index]*1e-6], [phase_deg])

        freq_value, freq_unit = format_frequency_smart_split(freqs[index])
        edit_value.setText(f"  {freq_value}")

        # Update field width when frequency changes from slider
        text_width = edit_value.fontMetrics().horizontalAdvance(edit_value.text())
        min_width = max(text_width + 10, 50)
        edit_value.setFixedWidth(min_width)
        labels_dict["unit"].setText(freq_unit)

        labels_dict["val"].setText(f"{current_s_param}: {np.real(val_complex):.3f} {'+' if np.imag(val_complex)>=0 else '-'} j{abs(np.imag(val_complex)):.3f}")
        labels_dict["mag"].setText(f"|{current_s_param}|: {magnitude:.3f}")
        labels_dict["phase"].setText(f"{self.measurement_ui_s_parameter_phase} {phase_deg:.2f}°")
        z = (1 + val_complex)/(1 - val_complex)
        labels_dict["z"].setText(f"Z: {np.real(z):.2f} + j{np.imag(z):.2f}")
        il_db = -20*np.log10(magnitude)
        labels_dict["il"].setText(f"{self.measurement_ui_dut_insertion_loss} {il_db:.2f} dB")
        vswr_val = (1 + magnitude)/(1 - magnitude) if magnitude < 1 else np.inf
        labels_dict["vswr"].setText(f"{self.measurement_ui_dut_vswr} {vswr_val:.2f}" if np.isfinite(vswr_val) else f"{self.measurement_ui_dut_vswr} ∞")
        fig.canvas.draw_idle()

        if not from_slider:
            if new_slider is None or new_slider.ax is None or new_slider.ax.get_figure() is None:
                logging.warning("Skipping cursor update right: slider or figure no longer exists")
                return
            new_slider.set_val(index)

        edit_value.clearFocus()

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        settings.setValue("Cursor_1_2/index", index)

        if return_values:
            return {
                "freq": freqs[index],
                "mag": magnitude,
                "phase": phase_deg,
                "val_complex": val_complex
            }

    def update_cursor_2(index = 0, from_slider=False, new_slider_2=None, return_values = False):
        import os
        from PySide6.QtCore import QSettings

        val_complex = S_data[index]
        magnitude = abs(val_complex)
        phase_deg = np.angle(val_complex, deg=True)

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        current_s_param = s_param

        unit_mode = settings.value("Graphic1/db_times", "dB")

        unit_mode_S11 = settings.value("Graphic1/db_times_S11", "dB")

        # === Actualizar cursor según graph_type y unidad ===
        if graph_type == "Smith Diagram":
            cursor_graph_2.set_data([np.real(val_complex)], [np.imag(val_complex)])
        elif graph_type == "Magnitude":
            if current_s_param == "S21":
                if unit_mode == "dB":
                    mag_value = 20 * np.log10(magnitude)
                elif unit_mode == "Power ratio":
                    mag_value = magnitude ** 2
                elif unit_mode == "times":
                    mag_value = magnitude
                else:
                    mag_value = magnitude

            elif current_s_param == "S11":
                if unit_mode_S11 == "dB":
                    mag_value = 20 * np.log10(magnitude)
                elif unit_mode_S11 == "S11 (reflection coefficient)":
                    mag_value = magnitude 
                else:
                    mag_value = magnitude

            print(f"cursor_right despuéx -> x: {cursor_graph_2.get_xdata()}, y: {cursor_graph_2.get_ydata()}, id: {id(cursor_graph_2)}")
            print("=== update_right_cursor end ===")

            cursor_graph_2.set_xdata([freqs[index] * 1e-6])
            cursor_graph_2.set_ydata([mag_value])

        elif graph_type == "Phase":
            cursor_graph_2.set_data([freqs[index] * 1e-6], [phase_deg])

        # === Actualizar labels del panel 2 ===
        freq_value, freq_unit = format_frequency_smart_split(freqs[index])
        edit_value_2.setText(freq_value)

        text_width = edit_value_2.fontMetrics().horizontalAdvance(edit_value_2.text())
        edit_value_2.setFixedWidth(max(text_width + 10, 50))

        labels_dict_2["unit"].setText(freq_unit)
        labels_dict_2["val"].setText(
            f"{current_s_param}: {np.real(val_complex):.3f} {'+' if np.imag(val_complex) >= 0 else '-'} j{abs(np.imag(val_complex)):.3f}"
        )
        labels_dict_2["mag"].setText(f"|{current_s_param}|: {magnitude:.3f}")
        labels_dict_2["phase"].setText(f"{self.measurement_ui_s_parameter_phase} {phase_deg:.2f}°")

        z = (1 + val_complex) / (1 - val_complex)
        labels_dict_2["z"].setText(f"Z: {np.real(z):.2f} + j{np.imag(z):.2f}")

        il_db = -20 * np.log10(magnitude)
        labels_dict_2["il"].setText(f"{self.measurement_ui_dut_insertion_loss} {il_db:.2f} dB")

        vswr_val = (1 + magnitude) / (1 - magnitude) if magnitude < 1 else np.inf
        labels_dict_2["vswr"].setText(f"{self.measurement_ui_dut_vswr} {vswr_val:.2f}" if np.isfinite(vswr_val) else f"{self.measurement_ui_dut_vswr} ∞")

        fig.canvas.draw_idle()

        if not from_slider:
            if new_slider_2 is None or getattr(new_slider_2, "ax", None) is None or getattr(new_slider_2.ax, "get_figure", lambda: None)() is None:
                logging.warning("Skipping cursor update: new slider or figure no longer exists")
                return
            try:
                new_slider_2.set_val(index)
            except Exception as e:
                logging.warning(f"Failed to set slider value: {e}")
                return

        edit_value_2.clearFocus()
        settings.setValue("Cursor_2_2/index", index)

        if return_values:
            return {
                "freq": freqs[index],
                "mag": magnitude,
                "phase": phase_deg,
                "val_complex": val_complex
            }


    # --- Slider ---
    slider_ax = fig.add_axes([0.25,0.04,0.5,0.03], facecolor='lightgray')
    slider = Slider(slider_ax, '', 0, len(freqs)-1, valinit=0, valstep=1)
    slider.vline.set_visible(False)
    slider.label.set_visible(False)
    slider.valtext.set_visible(False)  # Hide the value text
    slider.on_changed(lambda val: update_cursor(int(val), from_slider=True))

    slider_ax_2 = fig.add_axes([0.55,0.04,0.35,0.03], facecolor='lightgray')
    slider_2 = Slider(slider_ax_2, '', 0, len(freqs)-1, valinit=0, valstep=1)
    slider_2.vline.set_visible(False)
    slider_2.label.set_visible(False)
    slider_2.valtext.set_visible(False)  # Hide the value text
    slider_2.ax.set_visible(False)

    # --- Conectar edición manual ---
    def freq_edited(new_slider=None):
        try:
            freq_hz = parse_frequency_input(edit_value.text())
            if freq_hz is not None:
                index = np.argmin(np.abs(freqs - freq_hz))
                update_cursor(index, from_slider=False, new_slider=new_slider)
            edit_value.clearFocus()
        except:
            pass
    edit_value.editingFinished.connect(freq_edited)

    def freq_edited_2(new_slider=None):

        if new_slider == None:
            logging.warning("freq_edited_2 called with new_slider=None")
        else:
            logging.info("freq_edited_2 called with valid new_slider")

        try:
            freq_hz = parse_frequency_input(edit_value_2.text())
            if freq_hz is not None:
                index = np.argmin(np.abs(freqs - freq_hz))
                update_cursor_2(index, from_slider=False, new_slider=new_slider)
            edit_value_2.clearFocus()
        except:
            pass
    edit_value.editingFinished.connect(freq_edited_2)

    # --- Inicializar ---
    update_cursor(0)

    # --- Cursor draggable ---
    dragging_1 = {"active": False}
    dragging_2 = {"active": False}

    def on_pick(event):
        if event.artist == cursor_graph:
            dragging_1["active"] = True
        elif event.artist == cursor_graph_2:
            dragging_2["active"] = True

    def on_release(event):
        dragging_1["active"] = False
        dragging_2["active"] = False

    def on_motion(event):
        if event.inaxes != ax:
            return

        if dragging_1["active"]:
            if graph_type in ["Magnitude", "Phase"]:
                mouse_x = event.xdata
                index = np.argmin(np.abs(freqs*1e-6 - mouse_x))
                update_cursor(index)
            else:
                mouse_point = complex(event.xdata, event.ydata)
                distances = np.abs(S_data - mouse_point)
                index = np.argmin(distances)
                update_cursor(index)

        elif dragging_2["active"]:
            if graph_type in ["Magnitude", "Phase"]:
                mouse_x = event.xdata
                index = np.argmin(np.abs(freqs*1e-6 - mouse_x))
                update_cursor_2(index)
            else:
                mouse_point = complex(event.xdata, event.ydata)
                distances = np.abs(S_data - mouse_point)
                index = np.argmin(distances)
                update_cursor_2(index)

    # --- Conectar eventos ---
    cursor_graph.set_picker(5)
    cursor_graph_2.set_picker(5)

    canvas.mpl_connect("pick_event", on_pick)
    canvas.mpl_connect("button_release_event", on_release)
    canvas.mpl_connect("motion_notify_event", on_motion)
    
    def remove_slider(slider, fig, canvas):
        """Safely remove a matplotlib Slider from the figure.
        This releases widget locks, disconnects callbacks, removes the slider axis,
        forces a canvas redraw and triggers garbage collection.
        """
        if slider is None:
            return

        try:
            # 1) Try to release any widget lock that may be held by the figure.
            #    widgetlock.locked() may return a widget or False; call release safely.
            try:
                locked = fig.canvas.widgetlock.locked()
                # If locked is truthy and has 'release' semantics, release it.
                if locked:
                    # Try to release by passing the widget if possible
                    try:
                        fig.canvas.widgetlock.release(locked)
                    except Exception:
                        # fallback: try releasing with slider.ax (if applicable)
                        try:
                            fig.canvas.widgetlock.release(slider.ax)
                        except Exception:
                            pass
            except Exception:
                # Some backends may behave slightly differently; ignore fail here
                pass

            # 2) Disconnect slider internal callbacks to avoid lingering references
            try:
                if hasattr(slider, "_observers") and "changed" in slider._observers.callbacks:
                    for cid in list(slider._observers.callbacks["changed"].keys()):
                        slider._observers.disconnect(cid)
            except Exception:
                pass

            # 3) Remove the slider axis from the figure (this makes it disappear)
            try:
                if slider.ax in fig.axes:
                    fig.delaxes(slider.ax)
            except Exception:
                pass

            # 4) Force a redraw to update the visual state
            try:
                if canvas is not None:
                    canvas.draw_idle()
            except Exception:
                pass

            # 5) Delete the python object and call garbage collector
            try:
                # remove attributes that may hold references
                try:
                    slider.ax = None
                except Exception:
                    pass
                del slider
                gc.collect()
            except Exception:
                pass

        except Exception as e:
            print("Warning in remove_slider:", e)

    def fully_disable_slider(slider):
        """Disconnect all event callbacks and disable slider logic without removing ax yet."""
        if slider is None:
            return

        # Disconnect user callback registered through on_changed()
        try:
            for cid in list(slider._observers.callbacks.get("changed", {}).keys()):
                slider._observers.disconnect(cid)
        except Exception:
            pass

        # Disable slider internal mouse update behavior
        try:
            if hasattr(slider, "disconnect_events"):
                slider.disconnect_events()
        except Exception:
            pass

        # Disable axes interaction temporarily (prevents contains() call)
        try:
            if slider.ax is not None:
                slider.ax.set_navigate(False)
        except Exception:
            pass

    def update_data_references(new_s_data, new_freqs, old_slider=None, old_slider_2=None, 
        canvas=None, fig=None, show_graphic2_marker1=False, show_graphic2_marker2=True, marker1=None, marker2=None,
        info_panel=None, info_panel_2=None, new_s_param=None):

        """Update S_data and freqs and recreate slider safely using remove_slider()."""
        nonlocal S_data, freqs, s_param
        S_data = new_s_data
        freqs = new_freqs
        if new_s_param is not None:
            s_param = new_s_param

        if old_slider is not None:
            try:
                old_slider.disconnect_events() 
            except Exception:
                pass

            try:
                locked = fig.canvas.widgetlock.locked()
                if locked:
                    fig.canvas.widgetlock.release(locked)
            except Exception:
                pass

            remove_slider(old_slider, fig, canvas)
            old_slider = None

        if old_slider_2 is not None:
            try:
                old_slider_2.disconnect_events() 
            except Exception:
                pass

            # Libera widgetlock si está ocupado
            try:
                locked = fig.canvas.widgetlock.locked()
                if locked:
                    fig.canvas.widgetlock.release(locked)
            except Exception:
                pass

            remove_slider(old_slider_2, fig, canvas)
            old_slider_2 = None

        # Remove the old slider safely (if provided)
        if old_slider is not None:
            try:
                remove_slider(old_slider, fig, canvas)
            except Exception as e:
                logging.error("Warning removing old slider:", e)

        if old_slider_2 is not None:
            try:
                remove_slider(old_slider_2, fig, canvas)
            except Exception as e:
                logging.error("Warning removing old slider:", e)

        if old_slider is not None:
            fully_disable_slider(old_slider)  
            if old_slider.ax in fig.axes:
                fig.delaxes(old_slider.ax)
            old_slider = None  
            canvas.draw_idle()

        if old_slider_2 is not None:
            fully_disable_slider(old_slider_2) 
            if old_slider_2.ax in fig.axes:
                fig.delaxes(old_slider_2.ax)
            old_slider_2 = None 
            canvas.draw_idle()

        # Optionally ensure the global widgetlock is free before creating a new slider
        try:
            locked = fig.canvas.widgetlock.locked()
            if locked:
                try:
                    fig.canvas.widgetlock.release(locked)
                except Exception:
                    try:
                        # fallback
                        fig.canvas.widgetlock.release(None)
                    except Exception as e:
                        logging.error("Failed to release widgetlock:", e)
                        pass
        except Exception as e:
            logging.error("Widgetlock check error:", e)
            pass

        if show_graphic2_marker1 and not show_graphic2_marker2:
            new_slider_ax = fig.add_axes([0.25, 0.04, 0.5, 0.03], facecolor='lightgray')
            new_slider_ax_2 = fig.add_axes([0.55,0.04,0.35,0.03], facecolor='lightgray')

            # Create a new slider in the same figure

            new_slider = Slider(new_slider_ax, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)
            new_slider_2 = Slider(new_slider_ax_2, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)

            new_slider_ax.set_visible(True)
            new_slider_ax_2.set_visible(False)

            info_panel_2.hide()
            info_panel.show()

            marker1.set_visible(True)
            marker2.set_visible(False)

        elif not show_graphic2_marker1 and show_graphic2_marker2:
            new_slider_ax = fig.add_axes([0.15,0.04,0.35,0.03], facecolor='lightgray')
            new_slider_ax_2 = fig.add_axes([0.25, 0.04, 0.5, 0.03], facecolor='lightgray')

            # Create a new slider in the same figure

            new_slider = Slider(new_slider_ax, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)
            new_slider_2 = Slider(new_slider_ax_2, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)

            new_slider_ax.set_visible(False)
            new_slider_ax_2.set_visible(True)

            marker1.set_visible(False)
            marker2.set_visible(True)

            canvas.draw_idle()

            marker1.figure.canvas.draw_idle()

        elif show_graphic2_marker1 and show_graphic2_marker2:

            new_slider_ax = fig.add_axes([0.1,0.04,0.35,0.03], facecolor='lightgray')
            new_slider_ax_2 = fig.add_axes([0.55,0.04,0.35,0.03], facecolor='lightgray')

            # Create a new slider in the same figure

            new_slider = Slider(new_slider_ax, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)
            new_slider_2 = Slider(new_slider_ax_2, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)

            new_slider_ax.set_visible(True)
            new_slider_ax_2.set_visible(True)

            marker1.set_visible(True)
            marker2.set_visible(True)  

        elif not show_graphic2_marker1 and not show_graphic2_marker2:

            new_slider_ax = fig.add_axes([0.25,0.04,0.35,0.03], facecolor='lightgray')
            new_slider_ax_2 = fig.add_axes([0.55,0.04,0.35,0.03], facecolor='lightgray')

            # Create a new slider in the same figure

            new_slider = Slider(new_slider_ax, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)
            new_slider_2 = Slider(new_slider_ax_2, '', 0, len(new_freqs) - 1, valinit=0, valstep=1)

            new_slider_ax.set_visible(False)
            new_slider_ax_2.set_visible(False)  

            marker1.set_visible(False)
            marker2.set_visible(False)

        canvas.draw_idle()

        # Hide unused slider UI elements
        new_slider.vline.set_visible(False)
        new_slider.label.set_visible(False)
        new_slider.valtext.set_visible(False)

        # Hide unused slider UI elements
        new_slider_2.vline.set_visible(False)
        new_slider_2.label.set_visible(False)
        new_slider_2.valtext.set_visible(False)

        # Reconnect edit_value callback so it uses updated freqs
        def freq_edited_local():
            try:
                freq_hz = parse_frequency_input(edit_value.text())
                if freq_hz is not None:
                    index = np.argmin(np.abs(new_freqs - freq_hz))
                    update_cursor(index)
                edit_value.clearFocus()
            except Exception as e:
                logging.error("Edit freq error:", e)

        try:
            edit_value.editingFinished.disconnect()
        except Exception:
            pass
        edit_value.editingFinished.connect(freq_edited_local)

        # Final redraw
        try:
            if canvas is not None:
                canvas.draw_idle()
        except Exception:
            pass

        # Update marker visibility
        if marker1 is not None:
            marker1.set_visible(show_graphic2_marker1)
        if marker2 is not None:
            marker2.set_visible(show_graphic2_marker2)

        # Redraw the canvas to reflect changes
        if canvas is not None:
            canvas.draw_idle()

        return new_slider, new_slider_2


    def update_s_param_only(new_s_param):
        nonlocal s_param
        s_param = new_s_param
    
    return right_panel, info_panel, info_panel_2, fig, ax, canvas, slider, slider_2, cursor_graph, cursor_graph_2, labels_dict, labels_dict_2, update_cursor, update_cursor_2, update_data_references, update_s_param_only, freq_edited, freq_edited_2

class NoMouseSelectLineEdit(QLineEdit):
    def mousePressEvent(self, event):
        self.setCursorPosition(len(self.text()))

    def mouseMoveEvent(self, event):
        pass

    def mouseDoubleClickEvent(self, event):
        pass