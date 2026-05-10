import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QHBoxLayout
)

from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.graphics_utils import (
    create_left_panel,
    create_right_panel
)

def setup_graphics_window_body(
    self,
    settings,
    config,
    left_graph_type,
    left_s_param
):

    # --- Central widget ---
    central_widget = QWidget()
    self.setCentralWidget(central_widget)

    self.main_layout_vertical = QVBoxLayout(central_widget)
    self.main_layout_vertical.setContentsMargins(10, 10, 10, 10)
    self.main_layout_vertical.setSpacing(10)

    # --- Sweep Control Layout ---
    sweep_control_layout = QHBoxLayout()

    # Reconnect button
    self.reconnect_button = QPushButton("Reconnect")
    self.reconnect_button.setMaximumWidth(100)
    self.reconnect_button.clicked.connect(self.reconnect_device)

    # Sweep button
    self.sweep_button = QPushButton("Run Sweep")
    self.sweep_button.setMaximumWidth(120)
    self.sweep_button.clicked.connect(self.run_sweep)

    self.sweep_info_label = QLabel(
        "Sweep: 0.050 MHz - 1500.000 MHz, 101 points"
    )
    self.sweep_info_label.setStyleSheet("font-size: 12px;")

    # Initialize sweep configuration
    self.load_sweep_configuration()

    # Progress bar
    self.sweep_progress_bar = QProgressBar()
    self.sweep_progress_bar.setMaximumWidth(200)
    self.sweep_progress_bar.setVisible(False)

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

    sweep_control_layout.addWidget(self.reconnect_button)
    sweep_control_layout.addWidget(self.sweep_button)
    sweep_control_layout.addWidget(self.sweep_info_label)
    sweep_control_layout.addWidget(self.sweep_progress_bar)
    sweep_control_layout.addStretch()

    # Calibration label
    self.calibration_label = QLabel()
    self.calibration_label.setStyleSheet("font-size: 12px;")

    sweep_control_layout.addWidget(
        self.calibration_label,
        alignment=Qt.AlignRight
    )

    self.update_calibration_label_from_method()

    self.main_layout_vertical.addLayout(sweep_control_layout)

    # Initial reconnect button state
    self._update_reconnect_button_state()

    # --- Initialize empty data ---
    self.freqs = None
    self.s11 = None
    self.s21 = None

    logging.info(
        "[graphics_window.__init__] "
        "Initializing with empty plots - data will be loaded after first sweep"
    )

    self.left_graph_type = left_graph_type
    self.left_s_param = left_s_param

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
        self.freqs_edit_left_2

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
        self.freqs_edit_right_2

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
        marker2size=config['marker2_size2']
    )

    self._update_cursor_orig = self.update_cursor
    self._update_cursor_2_orig = self.update_cursor_2

    self._update_cursor_right_orig = self.update_right_cursor
    self._update_cursor_2_right_orig = self.update_right_cursor_2

    # =================== PANELS LAYOUT ===================

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

    self.markers_button = QPushButton("Markers Diff")

    self.markers_button_layout = QHBoxLayout()

    self.markers_button_layout.addStretch()
    self.markers_button_layout.addWidget(self.markers_button)
    self.markers_button_layout.addStretch()

    self.main_layout_vertical.addLayout(
        self.markers_button_layout
    )