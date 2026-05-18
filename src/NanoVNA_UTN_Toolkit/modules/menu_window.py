"""
Main launcher menu window for NanoVNA-UTN Toolkit modules.
"""

import logging
import sys
import os

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QMainWindow,
)

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)


# ------------------------------------------------------------------------------------------------------------ #

class ModuleSelectionWindow(QMainWindow):

    def __init__(self, vna_device=None):
        super().__init__()

        self.vna = vna_device

#------------------------------------------------------------------------------------------------------------------------------------------

        # Dark-Light mode settings

        dark_light_config(self)

#------------------------------------------------------------------------------------------------------------------------------------------

        self.setWindowTitle("NanoVNA-UTN Toolkit")
        self.resize(700, 400)

        # === Store VNA device reference ===
        self.vna_device = vna_device
        logging.info("[welcome_windows.__init__] Initializing welcome window")

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

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(70)

        title = QLabel("NanoVNA-UTN Toolkit")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
        """)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(60)
        buttons_layout.setAlignment(Qt.AlignCenter)

        self.dut_button = QPushButton("DUT Measurement")
        self.dut_button.setFixedSize(260, 120)

        self.materials_button = QPushButton("Materials Characterization")
        self.materials_button.setFixedSize(260, 120)

        self.dut_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
            }
        """)

        self.materials_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
            }
        """)

        self.dut_button.clicked.connect(self.open_dut_measurement_module)
        self.materials_button.clicked.connect(self.open_material_characterization_module)

        buttons_layout.addWidget(self.dut_button)
        buttons_layout.addWidget(self.materials_button)

        main_layout.addWidget(title)
        main_layout.addLayout(buttons_layout)

    def open_dut_measurement_module(self):

        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.welcome_window.welcome_windows import NanoVNAWelcome

        """Open the welcome window."""
        # Log device transfer to welcome window
        if self.vna:
            device_type = type(self.vna).__name__
            logging.info(f"[connection_window.open_welcome_window] Device {device_type} available - passing to welcome window")
            self.welcome_windows = NanoVNAWelcome(vna_device=self.vna)
        else:
            logging.info("[connection_window.open_welcome_window] No device connected - using placeholder mode")
            self.welcome_windows = NanoVNAWelcome()
            
        self.welcome_windows.show()
        self.close() 

    def open_material_characterization_module(self):

        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.material_characterization_window.material_characterization_window import MaterialCharacterizationWelcome

        """Open the material welcome window."""
        # Log device transfer to welcome window
        if self.vna:
            device_type = type(self.vna).__name__
            logging.info(f"[connection_window.open_material_characterization_module] Device {device_type} available - passing to welcome window")
            self.welcome_windows = MaterialCharacterizationWelcome(vna_device=self.vna)
        else:
            logging.info("[connection_window.open_material_characterization_module] No device connected - using placeholder mode")
            self.welcome_windows = MaterialCharacterizationWelcome()
            
        self.welcome_windows.show()
        self.close() 

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = ModuleSelectionWindow()
    window.show()

    sys.exit(app.exec())