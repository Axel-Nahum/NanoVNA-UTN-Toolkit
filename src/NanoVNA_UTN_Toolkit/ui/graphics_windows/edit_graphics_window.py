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
from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.edit_graphics_utils.edit_graphics_utils import create_edit_tab1, create_edit_tab2
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.updates.graphics_update import recreate_single_plot, update_plots_with_new_data
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.reset.sliders_cursors_reset import reset_sliders_and_markers_for_graph_change
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.updates.cursors_update import recreate_cursors_for_new_plots
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.db_unit.db_unit import get_graph_unit
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.updates.cursors_visibility import force_marker_visibility, force_marker_visibility_2
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


from NanoVNA_UTN_Toolkit.ui.graphics_window import NanoVNAGraphics

class EditGraphics(QMainWindow):
    def __init__(self, nano_window: NanoVNAGraphics, freqs=None):
        super().__init__()

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

#------------------------------------------------------------------------------------------------------------------------------------------

        # Load configuration for UI colors and styles
        settings = get_settings(
            "INI/dark_light_config/dark_light_config.ini",
            "ui/utils/settings/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve()
        )  

        # QFrame
        qframe_color = settings.value("Dark_Light/QFrame/background-color", "white")

        # Dark-Light mode settings

        dark_light_config(self)

#------------------------------------------------------------------------------------------------------------------------------------------

        # Load configuration for UI colors and styles
        settings = get_settings(
            "INI/dark_light_config/dark_light_config.ini", 
            "ui/utils/settings/dark_light_mode/dark_light_config.ini", 
            Path(__file__).resolve()
        )

        # QWidget
        background_color = settings.value("Dark_Light/QWidget/background-color", "#3a3a3a")

        # Qframe
        qframe_color = settings.value("Dark_Light/Qframe/background-color", "white")

        # QTabWidget pane
        tabwidget_pane_bg = settings.value("Dark_Light/QTabWidget_pane/background-color", "#3b3b3b")

        # QTabBar
        tabbar_bg = settings.value("Dark_Light/QTabBar/background-color", "#2b2b2b")
        tabbar_color = settings.value("Dark_Light/QTabBar/color", "white")
        tabbar_padding = settings.value("Dark_Light/QTabBar/padding", "5px 12px")
        tabbar_border = settings.value("Dark_Light/QTabBar/border", "none")
        tabbar_border_tl_radius = settings.value("Dark_Light/QTabBar/border-top-left-radius", "6px")
        tabbar_border_tr_radius = settings.value("Dark_Light/QTabBar/border-top-right-radius", "6px")

        # QTabBar selected
        tabbar_selected_bg = settings.value("Dark_Light/QTabBar_selected/background-color", "#4d4d4d")
        tabbar_selected_color = settings.value("Dark_Light/QTabBar/color", "white")

        # QSpinBox
        spinbox_bg = settings.value("Dark_Light/QSpinBox/background-color", "#3b3b3b")
        spinbox_color = settings.value("Dark_Light/QSpinBox/color", "white")
        spinbox_border = settings.value("Dark_Light/QSpinBox/border", "1px solid white")
        spinbox_border_radius = settings.value("Dark_Light/QSpinBox/border-radius", "8px")

        # QGroupBox title
        groupbox_title_color = settings.value("Dark_Light/QGroupBox_title/color", "white")

        # QLabel
        label_color = settings.value("Dark_Light/QLabel/color", "white")

        # QLineEdit
        lineedit_bg = settings.value("Dark_Light/QLineEdit/background-color", "#3b3b3b")
        lineedit_color = settings.value("Dark_Light/QLineEdit/color", "white")
        lineedit_border = settings.value("Dark_Light/QLineEdit/border", "1px solid white")
        lineedit_border_radius = settings.value("Dark_Light/QLineEdit/border-radius", "6px")
        lineedit_padding = settings.value("Dark_Light/QLineEdit/padding", "4px")
        lineedit_focus_bg = settings.value("Dark_Light/QLineEdit_focus/background-color", "#454545")
        lineedit_focus_border = settings.value("Dark_Light/QLineEdit_focus/border", "1px solid #4d90fe")

        # QPushButton
        pushbutton_bg = settings.value("Dark_Light/QPushButton/background-color", "#3b3b3b")
        pushbutton_color = settings.value("Dark_Light/QPushButton/color", "white")
        pushbutton_border = settings.value("Dark_Light/QPushButton/border", "1px solid white")
        pushbutton_border_radius = settings.value("Dark_Light/QPushButton/border-radius", "6px")
        pushbutton_padding = settings.value("Dark_Light/QPushButton/padding", "4px 10px")
        pushbutton_hover_bg = settings.value("Dark_Light/QPushButton_hover/background-color", "#4d4d4d")
        pushbutton_pressed_bg = settings.value("Dark_Light/QPushButton_pressed/background-color", "#5c5c5c")

        # QMenu
        menu_bg = settings.value("Dark_Light/QMenu/background", "#3a3a3a")
        menu_color = settings.value("Dark_Light/QMenu/color", "white")
        menu_border = settings.value("Dark_Light/QMenu/border", "1px solid #3b3b3b")
        menu_item_selected_bg = settings.value("Dark_Light/QMenu::item:selected/background-color", "#4d4d4d")

        # QMenuBar
        menu_item_color = settings.value("Dark_Light/QMenu_item_selected/background-color", "4d4d4d")
        menubar_bg = settings.value("Dark_Light/QMenuBar/background-color", "#3a3a3a")
        menubar_color = settings.value("Dark_Light/QMenuBar/color", "white")
        menubar_item_bg = settings.value("Dark_Light/QMenuBar_item/background", "transparent")
        menubar_item_color = settings.value("Dark_Light/QMenuBar_item/color", "white")
        menubar_item_padding = settings.value("Dark_Light/QMenuBar_item/padding", "4px 10px")
        menubar_item_selected_bg = settings.value("Dark_Light/QMenuBar_item_selected/background-color", "#4d4d4d")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {background_color};
            }}
            QFrame#separatorLine {{
                color: {qframe_color};           
                background: {qframe_color};
            }}
            QTabWidget::pane {{
                background-color: {tabwidget_pane_bg}; 
            }}
            QTabBar::tab {{
                background-color: {tabbar_bg}; 
                color: {tabbar_color};
                padding: {tabbar_padding};
                border: {tabbar_border}; 
                border-top-left-radius: {tabbar_border_tl_radius};
                border-top-right-radius: {tabbar_border_tr_radius};
            }}
            QTabBar::tab:selected {{
                background-color: {tabbar_selected_bg};  
                color: {tabbar_selected_color};
            }}
            QSpinBox {{
                background-color: white;
                color: black;
                border: {spinbox_border};
                border-radius: {spinbox_border_radius};
            }}
            QGroupBox:title {{
                color: {groupbox_title_color};  
            }}
            QLabel {{
                color: {label_color};  
            }}
            QLineEdit {{
                background-color: {lineedit_bg};
                color: {lineedit_color};
                border: {lineedit_border};
                border-radius: {lineedit_border_radius};
                padding: {lineedit_padding};
            }}
            QLineEdit:focus {{
                background-color: {lineedit_focus_bg};
                border: {lineedit_focus_border};
            }}
            QPushButton {{
                background-color: {pushbutton_bg};
                color: {pushbutton_color};
                border: {pushbutton_border};
                border-radius: {pushbutton_border_radius};
                padding: {pushbutton_padding};
            }}
            QPushButton:hover {{
                background-color: {pushbutton_hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pushbutton_pressed_bg};
            }}
            QMenuBar {{
                background-color: {menubar_bg};
                color: {menubar_color};
            }}
            QMenuBar::item {{
                background: {menubar_item_bg};
                color: {menubar_item_color};
                padding: {menubar_item_padding};
            }}
            QMenuBar::item:selected {{
                background: {menubar_item_selected_bg};
            }}
            QMenu {{
                background-color: {menu_bg};
                color: {menu_color};
                border: {menu_border};
            }}
            QMenu::item:selected {{
                background-color: {menu_item_color};
            }}
        """)

        # Load configuration for graphics
        settings = get_settings(
            "INI/colors_config/config.ini",
            "ui/graphics_windows/graphics_ini/graphics_config.ini", 
            Path(__file__).resolve()
        )

        self.nano_window = nano_window

        self.setWindowTitle("NanoVNA UTN Toolkit - Edit Graphics")
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

        tab1_widget, trace_color, marker_color, marker2_color, background_color_graphics, text_color, axis_color, line_width, marker_size, marker2_size = create_edit_tab1(self, tabs=tabs, nano_window=nano_window)
        tab2_widget, trace_color2, marker_color2, marker2_color2, background_color_graphics2, text_color2, axis_color2, line_width2, marker_size2, marker2_size2 = create_edit_tab2(self, tabs=tabs, nano_window=nano_window)

        tabs.addTab(tab1_widget, "Graphic 1")
        tabs.addTab(tab2_widget, "Graphic 2")

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
        btn_cancel = QPushButton("Cancel")
        btn_apply = QPushButton("Apply")
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
        
        from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.graphics_utils import create_left_panel, create_right_panel

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

        # Load configuration for graphics
        settings = get_settings(
            "INI/colors_config/config.ini",
            "ui/graphics_windows/graphics_ini/graphics_config.ini", 
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

        recreate_single_plot(
            self,
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
            cursor_graph_2=self.nano_window.cursor_left_2
        )

        recreate_single_plot(
            self,
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
            cursor_graph_2=self.nano_window.cursor_right_2
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

        self.nano_window.show()
        self.close()

if __name__ == "__main__":
    app = QApplication([])
    window = EditGraphics()
    window.show()
    app.exec()
