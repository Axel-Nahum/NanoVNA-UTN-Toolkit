from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QProgressBar,
    QVBoxLayout, QHBoxLayout, QCheckBox, QGridLayout
)

from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.graphics_utils import (
    create_left_panel,
    create_right_panel
)

from pathlib import Path

update_reconnect_button_state = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.graphics_refresh",
    "update_reconnect_button_state"
)

run_sweep = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.graphics_refresh_thread", "run_sweep")

update_calibration_label_from_method = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.calibration.calibration",
    "update_calibration_label_from_method"
)

reconnect_device = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.reconect.reconect_button",
    "reconnect_device"
)

on_realtime_toggled = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.real_time.real_time",
    "on_realtime_toggled"
)

# Import get_settings 

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

# ------------------------------------------------------------------------------------------------------------------ #

def setup_graphics_window_body(self, settings, config, left_graph_type, left_s_param):

    central_widget = QWidget()
    self.setCentralWidget(central_widget)

    self.main_layout_vertical = QVBoxLayout(central_widget)
    self.main_layout_vertical.setContentsMargins(10, 10, 10, 10)
    self.main_layout_vertical.setSpacing(10)

    # =================== TOP CONTROL AREA ===================
    top_grid = QGridLayout()
    top_grid.setHorizontalSpacing(6)   # ↓ menos espacio entre botones
    top_grid.setVerticalSpacing(10)
    top_grid.setContentsMargins(0, 0, 0, 0)

    # ---------- ROW 0 ----------
    self.reconnect_button = QPushButton(f"{self.measurement_ui_button_reconnect}")
    self.reconnect_button.setMaximumWidth(100)
    self.reconnect_button.clicked.connect(lambda: reconnect_device(self))
    top_grid.addWidget(self.reconnect_button, 0, 0, Qt.AlignLeft)

    self.sweep_button = QPushButton(f"{self.measurement_ui_button_run_sweep}")
    self.sweep_button.setEnabled(False)
    self.sweep_button.setMaximumWidth(120)
    self.sweep_button.clicked.connect(lambda: run_sweep(self))
    self.sweep_button.setEnabled(False)
    top_grid.addWidget(self.sweep_button, 0, 1, Qt.AlignLeft)

    settings_sweep = get_settings(
        "INI/dut_measurement/sweep_config/sweep_config.ini",
        "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini", 
        Path(__file__).resolve()        
    )

    freq_start = settings_sweep.value("Frequency/StartFreqHz", "50000", type=float)
    freq_stop = settings_sweep.value("Frequency/StopFreqHz", "1000000", type=float)
    steps = settings_sweep.value("Frequency/Segments", "101", type=float)
    unit_start = settings_sweep.value("Frequency/StartUnit", "KHz")
    unit_stop = settings_sweep.value("Frequency/StopUnit", "MHz")

    # START
    if unit_start.lower() == "hz":
        freq_start_display = round(freq_start, 3)
    elif unit_start.lower() == "khz":
        freq_start_display = round(freq_start / 1e3, 3)
    elif unit_start.lower() == "mhz":
        freq_start_display = round(freq_start / 1e6, 3)
    elif unit_start.lower() == "ghz":
        freq_start_display = round(freq_start / 1e9, 3)
    else:
        freq_start_display = freq_start

    # STOP
    if unit_stop.lower() == "hz":
        freq_stop_display = round(freq_stop, 2)
    elif unit_stop.lower() == "khz":
        freq_stop_display = round(freq_stop / 1e3, 2)
    elif unit_stop.lower() == "mhz":
        freq_stop_display = round(freq_stop / 1e6, 2)
    elif unit_stop.lower() == "ghz":
        freq_stop_display = round(freq_stop / 1e9, 2)
    else:
        freq_stop_display = freq_stop

    self.sweep_info_label = QLabel(f"Sweep: {freq_start_display} {unit_start} - {freq_stop_display} {unit_stop}, {steps} points")
    self.sweep_info_label.setStyleSheet("font-size: 12px; margin-left: 12px;")
    top_grid.addWidget(self.sweep_info_label, 0, 2, Qt.AlignVCenter)

    # ---------- ROW 1 ----------

    self.realtime_checkbox = QCheckBox("Single Sweep Mode")
    self.realtime_checkbox.setChecked(False)
    self.realtime_checkbox.toggled.connect(lambda checked: on_realtime_toggled(self, checked))
    checkbox_row = QHBoxLayout()

    checkbox_row.addStretch(1)
    checkbox_row.addWidget(self.realtime_checkbox)
    checkbox_row.addStretch(2)

    top_grid.addLayout(checkbox_row, 1, 0, 1, 2)

    sf_settings = get_settings(
        "INI/dut_measurement/signal_filters/signal_filters.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/signal_filters/signal_filters.ini",
        Path(__file__).resolve()
    )

    preset = sf_settings.value("kalman/preset", "Default")

    if preset == "Custom":
        q = sf_settings.value("kalman/custom_Q", 0.01, type=float)
        r = sf_settings.value("kalman/custom_R", 1.0, type=float)
    else:
        q = sf_settings.value("kalman/Q", 0.01, type=float)
        r = sf_settings.value("kalman/R", 1.0, type=float)

    if preset == "Off":
        self.kalman_label = QLabel(
            "Kalman filter is disabled"
        )
    else:
        self.kalman_label = QLabel(
            f"Kalman Filter: {preset} - Q = {q:.3f} · R = {r:.3f}"
        )
    self.kalman_label.setStyleSheet("font-size: 12px; margin-left: 12px;")
    top_grid.addWidget(self.kalman_label, 1, 2, Qt.AlignVCenter)

    # columnas
    top_grid.setColumnMinimumWidth(0, 80)
    top_grid.setColumnMinimumWidth(1, 100)
    top_grid.setColumnMinimumWidth(2, 200)

    top_grid.setColumnStretch(3, 0)
    top_grid.setColumnStretch(5, 1)

    top_grid.setColumnMinimumWidth(3, 50)

    # ---------- RIGHT SIDE ----------
    self.sweep_progress_bar = QProgressBar()
    self.sweep_progress_bar.setMinimumWidth(170)
    self.sweep_progress_bar.setMaximumWidth(170)
    self.sweep_progress_bar.setRange(0, 100)
    self.sweep_progress_bar.setValue(0)

    self.sweep_progress_bar.setVisible(True)
    self.sweep_progress_bar.setStyleSheet("""
        QProgressBar {
            border: 2px solid grey;
            border-radius: 5px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 3px;
        }
    """)

    top_grid.addWidget(
        self.sweep_progress_bar,
        0, 4, 2, 1,
        Qt.AlignVCenter
    )

    self.calibration_label = QLabel()
    self.calibration_label.setStyleSheet("font-size: 12px;")

    calib_wrapper = QHBoxLayout()
    calib_wrapper.setContentsMargins(120, 0, 0, 0) 

    calib_wrapper.addWidget(self.calibration_label)

    top_grid.addLayout(
        calib_wrapper,
        0, 6, 2, 1,
        Qt.AlignRight | Qt.AlignVCenter
    )

    update_calibration_label_from_method(self)
    update_reconnect_button_state(self)

    self.main_layout_vertical.addLayout(top_grid)

    # --- Initialize empty data ---
    self.freqs = None
    self.s11 = None
    self.s21 = None

    logging.info(
        "[graphics_window.__init__] "
        "Initializing with empty plots - data will be loaded after first sweep"
    )

    # =================== LEFT PANEL ===================
    (
        self.left_panel,
        self.info_panel_left,
        self.info_panel_left_2,
        self.fig_left,
        self.ax_left,
        self.canvas_left,
        self.slider_left,
        self.slider_left_2,
        self.cursor_left,
        self.cursor_left_2,
        self.labels_left,
        self.labels_left_2,
        self.update_cursor,
        self.update_cursor_2,
        self.update_left_data,
        self.update_left_data_2,
        self.update_left_s_param,
        self.freqs_edit_left,
        self.freqs_edit_left_2,
        self.line_left
    ) = create_left_panel(
        self,
        S_data=None,
        freqs=None,
        settings=settings,
        graph_type=config['graph_type_tab1'],
        s_param=config['s_param_tab1'],
        tracecolor=config['trace_color1'],
        markercolor=config['marker_color1'],
        marker2color=config['marker_color2'],
        linewidth=config['trace_size1'],
        markersize=config['marker_size1'],
        marker2size=config['marker_size2']
    )

    # =================== RIGHT PANEL ===================
    (
        self.right_panel,
        self.info_panel_right,
        self.info_panel_right_2,
        self.fig_right,
        self.ax_right,
        self.canvas_right,
        self.slider_right,
        self.slider_right_2,
        self.cursor_right,
        self.cursor_right_2,
        self.labels_right,
        self.labels_right_2,
        self.update_right_cursor,
        self.update_right_cursor_2,
        self.update_right_data,
        self.update_right_s_param,
        self.freqs_edit_right,
        self.freqs_edit_right_2,
        self.line_right
    ) = create_right_panel(
        self,
        settings=settings,
        S_data=None,
        freqs=None,
        graph_type=config['graph_type_tab2'],
        s_param=config['s_param_tab2'],
        tracecolor=config['trace_color2'],
        markercolor=config['marker_color2'],
        marker2color=config['marker2_color2'],
        linewidth=config['trace_size2'],
        markersize=config['marker_size2'],
        marker2size=config['marker_size2']
    )

    self._update_cursor_orig = self.update_cursor
    self._update_cursor_2_orig = self.update_cursor_2
    self._update_cursor_right_orig = self.update_right_cursor
    self._update_cursor_2_right_orig = self.update_right_cursor_2

    panels_layout = QHBoxLayout()

    while panels_layout.count():
        item = panels_layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)

    panels_layout.addWidget(self.left_panel, 1)
    panels_layout.addWidget(self.right_panel, 1)

    self.main_layout_vertical.addLayout(panels_layout)

    # =================== MARKERS BUTTON ===================
    self.markers_button = QPushButton(f"{self.measurement_ui_marker_diff}")

    self.markers_button_layout = QHBoxLayout()
    self.markers_button_layout.addStretch()
    self.markers_button_layout.addWidget(self.markers_button)
    self.markers_button_layout.addStretch()

    self.main_layout_vertical.addLayout(self.markers_button_layout)


def _load_sweep_configuration(self):
    load_sweep_configuration = safe_import(
        "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.sweep_window.sweep_utils.sweep_utils",
        "load_sweep_configuration"
    )

    load_sweep_configuration(self)