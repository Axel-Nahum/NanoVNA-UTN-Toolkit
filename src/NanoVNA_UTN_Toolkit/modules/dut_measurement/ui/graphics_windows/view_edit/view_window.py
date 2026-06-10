"""
Graphic view window for NanoVNA devices.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import numpy as np
import sys
import logging 

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QTabWidget, QFrame, QApplication, 
)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.view_edit.view_graphics_utils.view_utils import create_tab1
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.view_edit.view_graphics_utils.view_utils import create_tab2
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and install all dependencies with: pip install -r requirements.txt")
    sys.exit(1)

recreate_single_plot = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.graphics_update", "recreate_single_plot")

reset_sliders_and_markers_for_graph_change = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.sliders_cursors_reset", "reset_sliders_and_markers_for_graph_change")

get_graph_unit = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.db_unit.db_unit", "get_graph_unit")

force_marker_visibility, force_marker_visibility_2 = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.cursors_visibility", "force_marker_visibility", "force_marker_visibility_2")

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

# Import dark-light mode toggle function with error handling to log issues without crashing the application

dark_light_config = safe_import("NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "dark_light_config")

apply_window_icon = safe_import("NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon")

JsonResourceLoader = safe_import("NanoVNA_UTN_Toolkit.shared.resources.json_resource_loader", "JsonResourceLoader")

# ------------------------------------------------------------------------------------------------------------------ #

class View(QMainWindow):
    def __init__(self, nano_window=None, freqs=None):
        super().__init__()

        apply_window_icon(self)

        self.nano_window = nano_window 

# ------------------------------------------------------------------------------------------------------------------- #
# Load JSON 
# ------------------------------------------------------------------------------------------------------------------- #

        settings = get_settings(
            "INI/dut_measurement/preferences/preferences.ini",
            "shared/utils/preferences/preferences.ini", 
            Path(__file__).resolve()
        )

        current_lang = settings.value("Preferences/language", "en")

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
            "shared/utils/dark_light_mode/dark_light_config.ini", 
            Path(__file__).resolve()
        )

        # QFrame
        qframe_color = settings.value("Dark_Light/QFrame/background-color", "white")

        # Dark-Light mode settings

        dark_light_config(self)

#------------------------------------------------------------------------------------------------------------------------------------------

        self.setWindowTitle(f"{self.graphic_view_window_title}")
        self.setFixedSize(800, 500)

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

        tab1_widget, self.fig, self.ax, self.canvas, self.left_panel, self.update_graph, self.current_s_tab1, self.current_graph_tab1 = create_tab1(self)

        tab2_widget, self.fig_right, self.ax_right, self.canvas_right, self.right_panel2, self.update_graph_right, self.current_s_tab2, self.current_graph_tab2 = create_tab2(self)

        tabs.addTab(tab1_widget, f"{self.graphic_view_tab_graphic_1}")
        tabs.addTab(tab2_widget, f"{self.graphic_view_tab_graphic_2}")

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
        btn_cancel = QPushButton(f"{self.graphic_view_cancel}")
        btn_apply = QPushButton(f"{self.graphic_view_apply}")
        btn_cancel.clicked.connect(self.close)
        btn_apply.clicked.connect(lambda: self.on_apply_clicked())

        button_layout.addWidget(btn_cancel)
        button_layout.addWidget(btn_apply)
        central_layout.addLayout(button_layout)

        self.setCentralWidget(central_widget)

        # --- Initial plot ---
        self.update_graph()

    def on_apply_clicked(self):

         # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
                "INI/dut_measurement/graphics_config/graphics_config.ini",
                "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
                Path(__file__).resolve()
        )

        graph_type_tab1 = settings.value("Tab1/GraphType1", "Smith Diagram")
        s_param_tab1    = settings.value("Tab1/SParameter", "S11")
        graph_type_tab2 = settings.value("Tab2/GraphType2", "Magnitude")
        s_param_tab2    = settings.value("Tab2/SParameter", "S11")
        
        trace_color1 = settings.value("Graphic1/TraceColor", "red")
        marker_color1 = settings.value("Graphic1/MarkerColor1", "red")
        marker2_color1 = settings.value("Graphic1/MarkerColor2", "red")
        background_color1 = settings.value("Graphic1/BackgroundColor", "red")
        text_color1 = settings.value("Graphic1/TextColor", "red")
        axis_color1 = settings.value("Graphic1/AxisColor", "red")
        trace_size1 = int(settings.value("Graphic1/TraceWidth", 2))
        marker_size1 = int(settings.value("Graphic1/MarkerWidth", 6))
        marker2_size1 = int(settings.value("Graphic1/MarkerWidth", 6))
        db_times_1 = settings.value("Graphic1/db_times", "dB")
        db_times_S11 = settings.value("Graphic1/db_times_S11", "dB")
        
        trace_color2 = settings.value("Graphic2/TraceColor", "red")
        marker_color2 = settings.value("Graphic2/MarkerColor1", "red")
        marker2_color2 = settings.value("Graphic2/MarkerColor2", "red")
        background_color2 = settings.value("Graphic2/BackgroundColor", "red")
        text_color2 = settings.value("Graphic2/TextColor", "red")
        axis_color2 = settings.value("Graphic2/AxisColor", "red")
        trace_size2 = int(settings.value("Graphic2/TraceWidth", 2))
        marker_size2 = int(settings.value("Graphic2/MarkerWidth", 6))
        marker2_size2 = int(settings.value("Graphic2/MarkerWidth2", 6))
        db_times_2 = settings.value("Graphic2/db_times", "dB")
        db_times_S11_2 = settings.value("Graphic2/db_times_S11", "dB")

        self.s11 = self.nano_window.s11
        self.s21 = self.nano_window.s21
        self.freqs = self.nano_window.freqs

        data_left = self.s11 if self.current_s_tab1 == "S11" else self.s21
        data_right = self.s11 if self.current_s_tab2 == "S11" else self.s21

        selected_graph_left = self.current_graph_tab1
        selected_graph_right = self.current_graph_tab2

        settings.setValue("Tab1/SParameter", self.current_s_tab1)
        settings.setValue("Tab1/GraphType1", selected_graph_left)
        settings.setValue("Tab2/SParameter", self.current_s_tab2)
        settings.setValue("Tab2/GraphType2", selected_graph_right)
        settings.sync()

        unit_left = get_graph_unit(self, 1)
        unit_right = get_graph_unit(self, 2)

        if self.nano_window is not None:
            # --- Save markers before recreating ---
            left_markers_data = []
            right_markers_data = []

            for marker in getattr(self.nano_window, "markers_left", []):
                x, y = marker["cursor"].get_data()
                left_markers_data.append((x, y))

            for marker in getattr(self.nano_window, "markers_right", []):
                x, y = marker["cursor"].get_data()
                right_markers_data.append((x, y))

            # --- Reset aspect only if graph type changes ---
            if self.nano_window.left_graph_type == "Smith Diagram" and self.current_graph_tab1 != "Smith Diagram":
                self.nano_window.ax_left.remove()
                self.nano_window.ax_left = self.nano_window.fig_left.add_subplot(111)
                self.nano_window.ax_left.set_aspect("auto")

            elif self.nano_window.left_graph_type != "Smith Diagram" and self.current_graph_tab1 == "Smith Diagram":
                self.nano_window.ax_left.remove()
                self.nano_window.ax_left = self.nano_window.fig_left.add_subplot(111)
                self.nano_window.ax_left.set_aspect("equal")

            if self.nano_window.right_graph_type == "Smith Diagram" and self.current_graph_tab2 != "Smith Diagram":
                self.nano_window.ax_right.remove()
                self.nano_window.ax_right = self.nano_window.fig_right.add_subplot(111)
                self.nano_window.ax_right.set_aspect("auto")

            elif self.nano_window.right_graph_type != "Smith Diagram" and self.current_graph_tab2 == "Smith Diagram":
                self.nano_window.ax_right.remove()
                self.nano_window.ax_right = self.nano_window.fig_right.add_subplot(111)
                self.nano_window.ax_right.set_aspect("equal")

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

            self.nano_window.line_left = recreate_single_plot(
                self.nano_window,
                ax=self.nano_window.ax_left,
                fig=self.nano_window.fig_left,
                s_data=data_left,
                freqs=self.freqs,
                graph_type=self.current_graph_tab1,
                s_param=self.current_s_tab1,
                tracecolor=trace_color1,
                markercolor=marker_color1,
                background_color_graphics=background_color1,
                text_color=text_color1,
                axis_color=axis_color1,
                linewidth=trace_size1,
                markersize=marker_size1,
                unit=unit_left,
                cursor_graph=self.nano_window.cursor_left,
                cursor_graph_2=self.nano_window.cursor_left_2,
                ax_type="left",
                unit_mode=unit_left
            )

            self.nano_window.line_right = recreate_single_plot(
                self.nano_window,
                ax=self.nano_window.ax_right,
                fig=self.nano_window.fig_right,
                s_data=data_right,
                freqs=self.freqs,
                graph_type=self.current_graph_tab2,
                s_param=self.current_s_tab2,
                tracecolor=trace_color2,
                markercolor=marker_color2,
                background_color_graphics=background_color2,
                text_color=text_color2,
                axis_color=axis_color2,
                linewidth=trace_size2,
                markersize=marker_size2,
                unit=unit_right,
                cursor_graph=self.nano_window.cursor_right,
                cursor_graph_2=self.nano_window.cursor_right_2,
                ax_type="right",
                unit_mode=unit_right
            )

            force_marker_visibility(self.nano_window, marker_color_left=marker_color1, marker_color_right=marker_color2,
                marker1_size_left=marker_size1, marker1_size_right=marker_size2)
            force_marker_visibility_2(self.nano_window, marker_color_left=marker2_color1, marker_color_right=marker2_color2,
                marker_size_left=marker2_size1, marker_size_right=marker2_size2)

            nw = self.nano_window

            if hasattr(nw, 'update_cursor'):
                nw.update_cursor(0)
            if hasattr(nw, 'update_right_cursor'):
                nw.update_right_cursor(0)

            # --- Update states ---
            nw.s11 = self.s11
            nw.s21 = self.s21
            nw.freqs = self.freqs
            nw.left_graph_type = self.current_graph_tab1
            nw.left_s_param = self.current_s_tab1
            nw.right_graph_type = self.current_graph_tab2
            nw.right_s_param = self.current_s_tab2

            # --- Update s_param references in panel functions ---
            if hasattr(nw, 'update_left_s_param') and callable(nw.update_left_s_param):
                nw.update_left_s_param(self.current_s_tab1)
            if hasattr(nw, 'update_right_s_param') and callable(nw.update_right_s_param):
                nw.update_right_s_param(self.current_s_tab2)

            # --- Reset sliders and update QGroupBox information ---
            reset_sliders_and_markers_for_graph_change(nw)

            # Enforce marker 2 visibility last — nothing after this should override it
            nw.cursor_left_2.set_visible(nw.show_graphic1_marker2)
            nw.cursor_right_2.set_visible(nw.show_graphic2_marker2)

            nw.fig_left.canvas.draw_idle()
            nw.fig_right.canvas.draw_idle()

            nw.show()

        self.close()

if __name__ == "__main__":
    app = QApplication([])
    window = View()
    window.show()
    app.exec()
