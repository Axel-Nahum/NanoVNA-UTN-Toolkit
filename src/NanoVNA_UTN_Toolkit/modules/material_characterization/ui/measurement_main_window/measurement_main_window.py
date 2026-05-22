"""
Measurement main window (permittivity & permeability complex analysis).
"""

import sys
import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, 
    QLabel, QMenu, QApplication
)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
    from NanoVNA_UTN_Toolkit.modules.menu_window import ModuleSelectionWindow
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.shared.utils.app_icon import apply_window_icon
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.shared.utils.load_resource import load_resource
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------- #

class MeasurementMainWindow(QMainWindow):

    def __init__(self, vna_device=None, wizard_window=None):
        super().__init__()

        self.vna = vna_device

        self.setWindowTitle("NanoVNA UTN Toolkit - Measurement")
        self.setGeometry(200, 200, 1000, 650)

# ---------------------------------------------------------------------------------------------------------- #
# Window Icon
# ---------------------------------------------------------------------------------------------------------- #

        apply_window_icon(self)


# ------------------------------------------------------------------------------------------------------------------- #
        # Dark-Light mode
# ------------------------------------------------------------------------------------------------------------------- #

        dark_light_config(self)

        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self.title = QLabel(f"Measurement Window (Permittivity / Permeability) {wizard_window.selected_method}")
        self.title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
        """)

        self.main_layout.addWidget(self.title, alignment=Qt.AlignTop)

        self.placeholder = QLabel("Graph area (to be implemented)")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet("""
            font-size: 16px;
            color: gray;
        """)

        self.main_layout.addWidget(self.placeholder)

        # Menus
        self._create_menus()

# ---------------------------------------------------------------------------------------------------------------- #

    def _create_menus(self):

        menubar = self.menuBar()

        # FILE
        file_menu = menubar.addMenu("File")

        exit_action = QAction("Back to menu", self)
        exit_action.triggered.connect(self.return_to_menu_window)
        file_menu.addAction(exit_action)

        # EDIT
        edit_menu = menubar.addMenu("Edit")

        clear_action = QAction("Clear", self)
        edit_menu.addAction(clear_action)

        # VIEW
        view_menu = menubar.addMenu("View")

        view_action = QAction("Refresh", self)
        view_menu.addAction(view_action)

        # HELP
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        help_menu.addAction(about_action)

# ---------------------------------------------------------------------------------------------------------------- #

    def contextMenuEvent(self, event):

        context_menu = QMenu(self)

        option1 = context_menu.addAction("Opción_1")
        option2 = context_menu.addAction("Opción_2")
        option3 = context_menu.addAction("Opción_3")

        action = context_menu.exec(event.globalPos())

        if action == option1:
            logging.info("Context menu: Opción 1")

        elif action == option2:
            logging.info("Context menu: Opción 2")

        elif action == option3:
            logging.info("Context menu: Opción 3")

    def return_to_menu_window(self):

        if self.vna:
            self.menu_windows = (
                ModuleSelectionWindow(vna_device=self.vna)
            )
        else:
            self.menu_windows = (
                ModuleSelectionWindow()
            )

        self.menu_windows.show()

        self.close()

# ---------------------------------------------------------------------------------------------------------------- #

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MeasurementMainWindow()

    window.show()

    sys.exit(app.exec())