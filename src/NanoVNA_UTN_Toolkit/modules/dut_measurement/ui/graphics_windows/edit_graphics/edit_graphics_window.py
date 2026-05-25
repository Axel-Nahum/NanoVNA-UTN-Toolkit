"""
Edit graphics window for NanoVNA devices.
"""

import numpy as np
import os
import sys
import logging

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QTabWidget, QApplication, QFrame
)
from PySide6.QtGui import QIcon

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.edit_graphics.edit_graphics_utils.edit_graphics_utils import create_edit_tab1, create_edit_tab2
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.graphics_update import recreate_single_plot
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.db_unit.db_unit import get_graph_unit
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.cursors_visibility import force_marker_visibility, force_marker_visibility_2
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.shared.utils.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.shared.utils.app_icon import apply_window_icon
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.shared.resources.json_resource_loader import JsonResourceLoader
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics

class EditGraphics(QMainWindow):
    def __init__(self, nano_window: NanoVNAGraphics, freqs=None):
        super().__init__()

        apply_window_icon(self)

# ------------------------------------------------------------------------------------------------------------------- #
# Load JSON 
# ------------------------------------------------------------------------------------------------------------------- #

        current_lang = "en"

        self.resourceLoader = JsonResourceLoader(
            self_window = self, 
            module = "dut_measurement", 
            lang = current_lang, 
            json_resource = "dut_measurement_view_edit.json"
        )

        self.resourceLoader.load_view_edit_ui_resources()

# ------------------------------------------------------------------------------------------------------------------- #
# Dark light Mode
# ------------------------------------------------------------------------------------------------------------------- #

        # Load configuration for UI colors and styles
        settings = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini", 
            "ui/utils/settings/dark_light_mode/dark_light_config.ini", 
                Path(__file__).resolve()
        )

        # QFrame
        qframe_color = settings.value("Dark_Light/QFrame/background-color", "white")

        # Dark-Light mode settings

        dark_light_config(self)

#------------------------------------------------------------------------------------------------------------------------------------------

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        self.nano_window = nano_window

        self.setWindowTitle(f"{self.edit_graphics_window_title}")
        self.setFixedSize(800, 630)

        # --- Frequency array placeholder ---
        if freqs is None:
            freqs = np.linspace(1e6, 100e6, 101)
        self.freqs = freqs

        # --- Data placeholders ---
        self.s11 = np.zeros_like(freqs, dtype=complex)  # S11 data
        self.s21 = np.zeros_like(freqs, dtype=complex)  # S21 data

        # --- Central widget setup ---
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(15, 15, 15, 15)
        central_layout.setSpacing(10)

        # --- Tabs setup ---
        tabs = QTabWidget()

        (
            tab1_widget, trace_color, marker_color, marker2_color,
            background_color_graphics, text_color, axis_color,
            line_width, marker_size, marker2_size
        ) = create_edit_tab1(
            self,
            tabs=tabs,
            nano_window=nano_window
        )

        (
            tab2_widget, trace_color2, marker_color2, marker2_color2,
            background_color_graphics2, text_color2, axis_color2,
            line_width2, marker_size2, marker2_size2
        ) = create_edit_tab2(
            self,
            tabs=tabs,
            nano_window=nano_window
        )

        tabs.addTab(tab1_widget, f"{self.edit_graphics_tab_graphic_1}")
        tabs.addTab(tab2_widget, f"{self.edit_graphics_tab_graphic_2}")

        central_layout.addWidget(tabs)

        # --- Line above buttons ---
        line_above_buttons = QFrame()
        line_above_buttons.setStyleSheet(f"""background-color: {qframe_color}; color: {qframe_color}""")
        line_above_buttons.setFrameShape(QFrame.HLine)
        line_above_buttons.setFrameShadow(QFrame.Plain)
        line_above_buttons.setFixedHeight(2)
        central_layout.addWidget(line_above_buttons)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        btn_cancel = QPushButton(f"{self.edit_graphics_cancel}")
        btn_apply = QPushButton(f"{self.edit_graphics_apply}")
        btn_cancel.clicked.connect(self.close)
        btn_apply.clicked.connect(lambda: self.on_apply_clicked(trace_color=trace_color(), trace_color2=trace_color2(), 
                                                                background_color_graphics=background_color_graphics(), background_color_graphics2=background_color_graphics2(),
                                                                marker_color=marker_color(), marker_color2=marker_color2(),
                                                                marker2_color=marker2_color(), marker2_color2=marker2_color2(),
                                                                text_color=text_color(), text_color2=text_color2(),
                                                                axis_color=axis_color(), axis_color2=axis_color2(),
                                                                line_width=line_width(), line_width2=line_width2(),
                                                                marker_size=marker_size(), marker_size2=marker_size2(),
                                                                marker2_size=marker2_size(), marker2_size2=marker2_size2(),
                                                                settings=settings))

        button_layout.addWidget(btn_cancel)
        button_layout.addWidget(btn_apply)
        central_layout.addLayout(button_layout)

        # --- Apply styles ---
        self.setCentralWidget(central_widget)
        #self.setStyleSheet("background-color: #7f7f7f;")

    def on_apply_clicked(self, settings, trace_color="blue", trace_color2="blue",
                     background_color_graphics="blue", background_color_graphics2="blue",
                     marker_color="blue", marker_color2="blue", 
                     marker2_color="blue", marker2_color2="blue", 
                     text_color="blue", text_color2="blue",
                     axis_color="blue", axis_color2="blue",
                     line_width=2, line_width2=2,
                     marker_size=2, marker_size2=2,
                     marker2_size=2, marker2_size2=2):
        
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.graphics_utils import create_left_panel, create_right_panel

        settings.setValue("Graphic1/TraceColor", trace_color)
        settings.setValue("Graphic1/MarkerColor1", marker_color)
        settings.setValue("Graphic1/MarkerColor2", marker2_color)
        settings.setValue("Graphic1/BackgroundColor", background_color_graphics)
        settings.setValue("Graphic1/TextColor", text_color)
        settings.setValue("Graphic1/AxisColor", axis_color)
        settings.setValue("Graphic1/TraceWidth", line_width)
        settings.setValue("Graphic1/MarkerWidth1", marker_size)
        settings.setValue("Graphic1/MarkerWidth2", marker2_size)

        settings.setValue("Graphic2/TraceColor", trace_color2)
        settings.setValue("Graphic2/MarkerColor1", marker_color2)
        settings.setValue("Graphic2/MarkerColor2", marker2_color2)
        settings.setValue("Graphic2/BackgroundColor", background_color_graphics2)
        settings.setValue("Graphic2/TextColor", text_color2)
        settings.setValue("Graphic2/AxisColor", axis_color2)
        settings.setValue("Graphic2/TraceWidth", line_width2)
        settings.setValue("Graphic2/MarkerWidth1", marker_size2)
        settings.setValue("Graphic2/MarkerWidth2", marker2_size2)
        settings.sync()

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        graph_type1 = settings.value("Tab1/GraphType1", "Smith Diagram")
        s_param1 = settings.value("Tab1/SParameter", "S11")
        graph_type2 = settings.value("Tab2/GraphType2", "Magnitude")
        s_param2 = settings.value("Tab2/SParameter", "S11")

        self.s11 = self.nano_window.s11
        self.s21 = self.nano_window.s21
        self.freqs = self.nano_window.freqs

        data_left = self.s11 if s_param1 == "S11" else self.s21
        data_right = self.s11 if s_param2 == "S11" else self.s21

        unit_left = get_graph_unit(self, 1)
        unit_right = get_graph_unit(self, 2)

        self.nano_window.ax_left.clear()
        self.nano_window.ax_right.clear()

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        unit_left = settings.value("Graphic1/db_times", "dB")
        unit_right = settings.value("Graphic2/db_times", "dB")

        recreate_single_plot(
            self.nano_window,
            ax=self.nano_window.ax_left,
            fig=self.nano_window.fig_left,
            s_data=data_left,
            freqs=self.freqs,
            graph_type=graph_type1,
            s_param=s_param1,
            tracecolor=trace_color,
            markercolor=marker_color,
            background_color_graphics=background_color_graphics,
            text_color=text_color,
            axis_color=axis_color,
            linewidth=line_width,
            markersize=marker_size,
            unit=unit_left,
            cursor_graph=self.nano_window.cursor_left,
            cursor_graph_2=self.nano_window.cursor_left_2,
            unit_mode=unit_left
        )

        recreate_single_plot(
            self.nano_window,
            ax=self.nano_window.ax_right,
            fig=self.nano_window.fig_right,
            s_data=data_right,
            freqs=self.freqs,
            graph_type=graph_type2,
            s_param=s_param2,
            tracecolor=trace_color2,
            markercolor=marker_color2,
            background_color_graphics=background_color_graphics2,
            text_color=text_color2,
            axis_color=axis_color2,
            linewidth=line_width2,
            markersize=marker_size2,
            unit=unit_right,
            cursor_graph=self.nano_window.cursor_right,
            cursor_graph_2=self.nano_window.cursor_right_2,
            unit_mode=unit_right
        )

        force_marker_visibility(self.nano_window, marker_color_left=marker_color, marker_color_right=marker_color2, 
                                marker1_size_left=marker_size, marker1_size_right=marker_size2)
        force_marker_visibility_2(self.nano_window, marker_color_left=marker2_color, marker_color_right=marker2_color2, 
                                marker_size_left=marker2_size, marker_size_right=marker2_size2)

        self.nano_window.s11 = self.s11
        self.nano_window.s21 = self.s21
        self.nano_window.freqs = self.freqs
        self.nano_window.left_graph_type = graph_type1
        self.nano_window.left_s_param = s_param1
        self.nano_window.right_graph_type = graph_type2
        self.nano_window.right_s_param = s_param2

        self.nano_window.canvas_left.draw_idle()
        self.nano_window.canvas_right.draw_idle()

        self.nano_window.resourceLoader.load_measurement_graphics_resources()

        self.nano_window.show()
        self.close()

if __name__ == "__main__":
    app = QApplication([])
    window = EditGraphics()
    window.show()
    app.exec()
