"""
Material characterization setup window for NanoVNA devices.
"""

import logging
import os
import sys

from datetime import datetime

from pathlib import Path

# Suppress verbose matplotlib logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QHBoxLayout, QGroupBox, QComboBox
)
from PySide6.QtGui import QIcon

try:
    from NanoVNA_UTN_Toolkit.shared.ui.wizard_cal_windows.wizard_windows import CalibrationWizard
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# Import calibration data storage
try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.calibration_manager import OSMCalibrationManager, THRUCalibrationManager
except ImportError as e:
    logging.error("Failed to import OSMCalibrationManager: %s", e)
    logging.error("Failed to import THRUCalibrationManager: %s", e)
    OSMCalibrationManager = None
    THRUCalibrationManager = None

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------ #

class MaterialCharacterizationWelcome(QMainWindow):

    def __init__(self, s11=None, freqs=None, vna_device=None):
        super().__init__()

        self.vna = vna_device

# ------------------------------------------------------------------------------------------------------------------------------------------ #

        # Dark-Light mode settings

        dark_light_config(self)

# ------------------------------------------------------------------------------------------------------------------------------------------ #

        # === Store VNA device reference ===
        self.vna_device = vna_device
        logging.info("[material_characterization_welcome.__init__] Initializing material characterization welcome window")

        # Try to set application icon
        if getattr(sys, 'frozen', False):

            # ---- EXE MODE ----
            base_path = sys._MEIPASS
            icon_path = os.path.join(base_path, 'icon.ico')

            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                logging.getLogger(__name__).warning(f"icon.ico not found in exe: {icon_path}")

        else:

            # ---- NORMAL PYTHON MODE ----
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

        if OSMCalibrationManager:
            self.osm_calibration = OSMCalibrationManager()

            if vna_device and hasattr(vna_device, 'name'):
                self.osm_calibration.device_name = vna_device.name

            logging.info("[MaterialCharacterizationWelcome] OSM calibration manager initialized")

        else:
            self.osm_calibration = None
            logging.warning("[MaterialCharacterizationWelcome] OSMCalibrationManager not available")

        if THRUCalibrationManager:
            self.thru_calibration = THRUCalibrationManager()

            if vna_device and hasattr(vna_device, 'name'):
                self.thru_calibration.device_name = vna_device.name

            logging.info("[MaterialCharacterizationWelcome] THRU calibration manager initialized")

        else:
            self.thru_calibration = None
            logging.warning("[MaterialCharacterizationWelcome] THRUCalibrationManager not available")

        self.setWindowTitle("NanoVNA UTN Toolkit - Material Characterization")
        self.setGeometry(100, 100, 1000, 480)

        # === Central widget and main layout ===
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === Create main content area ===
        self._create_calibration_group(main_layout)
        self._create_characterization_group(main_layout)

        main_layout.addStretch()

    def _create_calibration_group(self, parent_layout):

        logging.info("[material_characterization_welcome._create_calibration_group] Creating calibration group")

        settings = get_settings(
            "INI/dark_light_config/dark_light_config.ini",
            "ui/utils/settings/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve()
        )

        groupbox_border = settings.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")

        groupbox_style = (
            f"QGroupBox {{ "
            f"border: {groupbox_border}; "
            f"border-radius: 5px; "
            f"margin-top: 1.3ex; "
            f"padding-top: 6px; "
            f"}} "
            f"QGroupBox::title {{ "
            f"subcontrol-origin: margin; "
            f"left: 10px; "
            f"padding: 0 3px 0 3px; "
            f"font-size: 30pt;"
            f"}}"
        )

        calibration_group = QGroupBox("Calibration Wizard")
        calibration_group.setStyleSheet(groupbox_style)

        calibration_layout = QVBoxLayout(calibration_group)
        calibration_layout.setSpacing(15)

        description_text = (
            "Calibration is essential for accurate material characterization measurements. "
            "It removes systematic errors from cables, connectors, and the VNA itself by "
            "measuring known reference standards. The Calibration Wizard guides you through "
            "this process step-by-step, ensuring your measurements are precise and reliable."
        )

        description_label = QLabel(description_text)
        description_label.setWordWrap(True)

        description_label.setStyleSheet(
            "font-weight: normal; "
            "font-size: 14px; "
            "color: #cccccc; "
            "padding: 10px;"
        )

        calibration_layout.addWidget(description_label)

        self.calibration_wizard_button = QPushButton("Open Calibration Wizard")
        self.calibration_wizard_button.clicked.connect(self.open_calibration_wizard)

        self.calibration_wizard_button.setFixedHeight(50)

        self.calibration_wizard_button.setStyleSheet(
            "font-size: 16px; "
            "margin: 10px;"
        )

        calibration_layout.addWidget(
            self.calibration_wizard_button,
            alignment=Qt.AlignCenter
        )

        parent_layout.addWidget(calibration_group)

        logging.info("[material_characterization_welcome._create_calibration_group] Calibration group created successfully")

    def _create_characterization_group(self, parent_layout):

        logging.info("[material_characterization_welcome._create_characterization_group] Creating characterization group")

        settings = get_settings(
            "INI/dark_light_config/dark_light_config.ini",
            "ui/utils/settings/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve()
        )

        groupbox_border = settings.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")

        groupbox_style = (
            f"QGroupBox {{ "
            f"border: {groupbox_border}; "
            f"border-radius: 5px; "
            f"margin-top: 1.3ex; "
            f"padding-top: 6px; "
            f"}} "
            f"QGroupBox::title {{ "
            f"subcontrol-origin: margin; "
            f"left: 10px; "
            f"padding: 0 3px 0 3px; "
            f"}}"
        )

        characterization_group = QGroupBox("Material Characterization")
        characterization_group.setStyleSheet(groupbox_style)

        characterization_layout = QVBoxLayout(characterization_group)
        characterization_layout.setSpacing(15)

        self._create_calibration_kit_selector(characterization_layout)
        self._create_action_buttons(characterization_layout)

        parent_layout.addWidget(characterization_group)

        logging.info("[material_characterization_welcome._create_characterization_group] Characterization group created successfully")

    def _create_calibration_kit_selector(self, parent_layout):

        logging.info("[material_characterization_welcome._create_calibration_kit_selector] Creating kit selector dropdown")

        kit_selector_label = QLabel("Calibration Kit Selection:")

        kit_selector_label.setStyleSheet(
            "font-weight: bold; "
            "font-size: 14px; "
            "margin-bottom: 10px;"
        )

        parent_layout.addWidget(kit_selector_label)

        self._load_calibration_kits()

        self.kit_dropdown = QComboBox()

        self.kit_dropdown.setFixedHeight(40)
        self.kit_dropdown.setMinimumWidth(400)

        self.kit_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 400px;
            }

            QComboBox:hover {
                background-color: #4d4d4d;
            }

            QComboBox::drop-down {
                width: 0px;
                border: none;
                background: transparent;
            }

            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }

            QComboBox QAbstractItemView {
                background-color: #3b3b3b;
                color: white;
                selection-background-color: #4d4d4d;
                selection-color: white;
                border: 1px solid white;
            }
        """)

        self.kit_dropdown.addItem("None")

        for kit_name in self.kit_names:
            self.kit_dropdown.addItem(kit_name)

        self._set_current_kit_selection()

        self.kit_dropdown.currentTextChanged.connect(self._on_kit_selection_changed)

        parent_layout.addWidget(
            self.kit_dropdown,
            alignment=Qt.AlignmentFlag.AlignLeft
        )

        self.kit_info_label = QLabel("")

        self.kit_info_label.setStyleSheet(
            "font-size: 12px; "
            "color: #cccccc; "
            "margin-top: 10px; "
            "margin-left: 0px; "
            "padding: 5px;"
        )

        self.kit_info_label.setWordWrap(True)
        self.kit_info_label.setMinimumWidth(400)

        parent_layout.addWidget(
            self.kit_info_label,
            alignment=Qt.AlignmentFlag.AlignLeft
        )

        current_text = self.kit_dropdown.currentText()

        if current_text.startswith("None"):
            self.selected_kit_name = None
        else:
            self.selected_kit_name = current_text

        self._update_kit_info_display()

    def _set_current_kit_selection(self):

        calibration_name = self._get_current_calibration_name()

        if "_" in str(calibration_name):
            calibration_name_split = str(calibration_name).rsplit("_", 1)[0]
        else:
            calibration_name_split = str(calibration_name)

        if calibration_name_split in self.kit_names:
            kit_index = self.kit_names.index(calibration_name_split) + 1
            self.kit_dropdown.setCurrentIndex(kit_index)

        else:
            self.kit_dropdown.setCurrentIndex(0)

    def _on_kit_selection_changed(self, selected_text):

        if selected_text.startswith("None"):
            self.selected_kit_name = None
        else:
            self.selected_kit_name = selected_text

        self._update_kit_info_display()

    def _update_kit_info_display(self):

        if hasattr(self, 'selected_kit_name') and self.selected_kit_name:

            if self.selected_kit_name in self.kit_names:

                kit_index = self.kit_names.index(self.selected_kit_name)
                kit_id = self.kit_ids[kit_index] if kit_index < len(self.kit_ids) else "Unknown"

                settings = get_settings(
                    "INI/calibration_config/calibration_config.ini",
                    "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
                    Path(__file__).resolve()
                )

                kit_method = settings.value(f"Kit_{kit_id}/method", "Unknown")
                kit_datetime = settings.value(f"Kit_{kit_id}/DateTime_Kits", "Unknown")

                info_text = (
                    f"Selected Kit: {self.selected_kit_name}\n"
                    f"Method: {kit_method}\n"
                    f"Created: {kit_datetime}"
                )

                self.kit_info_label.setText(info_text)

        else:
            self.kit_info_label.setText("No calibration kit selected")

    def _create_action_buttons(self, parent_layout):

        logging.info("[material_characterization_welcome._create_action_buttons] Creating action buttons")

        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)

        self.characterization_methods_button = QPushButton("Open Characterization Methods")

        self.characterization_methods_button.clicked.connect(
            self.open_characterization_methods
        )

        self.characterization_methods_button.setFixedHeight(50)

        self.characterization_methods_button.setStyleSheet(
            "font-size: 16px; "
            "margin: 10px;"
        )

        button_layout.addWidget(self.characterization_methods_button)

        self.import_button = QPushButton("Import Calibration")

        self.import_button.clicked.connect(self.import_calibration)

        self.import_button.setFixedHeight(50)

        self.import_button.setStyleSheet(
            "font-size: 16px; "
            "margin: 10px;"
        )

        button_layout.addWidget(self.import_button)

        parent_layout.addLayout(button_layout)

    def _load_calibration_kits(self):

        settings_calibration = get_settings(
            "INI/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )

        kit_groups = [
            g for g in settings_calibration.childGroups()
            if g.startswith("Kit_")
        ]

        self.kit_names = [
            settings_calibration.value(f"{g}/kit_name", "")
            for g in kit_groups
        ]

        self.kit_ids = [
            int(settings_calibration.value(f"{g}/id", 0))
            for g in kit_groups
        ]

    def _get_current_calibration_name(self):

        settings_calibration = get_settings(
            "INI/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )

        calibration_name = settings_calibration.value(
            "Calibration/Name",
            "No Calibration"
        )

        return calibration_name

    def import_calibration(self):
        logging.info("[material_characterization_welcome.import_calibration] Import calibration clicked")

    def open_calibration_wizard(self):

        settings_calibration = get_settings(
            "INI/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )

        settings_calibration.setValue("Calibration/Kits", False)
        settings_calibration.setValue("Calibration/NoCalibration", False)
        settings_calibration.setValue("Calibration/CalibrationWizard", True)

        settings_calibration.sync()

        logging.info("[material_characterization_welcome.open_calibration_wizard] Opening calibration wizard")

        if self.vna_device:
            self.welcome_windows = CalibrationWizard(
                self.vna_device,
                caller="material_characterization"
            )

        else:
            self.welcome_windows = CalibrationWizard()

        self.welcome_windows.show()
        self.close()

    def open_characterization_methods(self):

        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.characterization_methods_window.characterization_methods_window import CharacterizationWizard

        logging.info("[material_characterization_welcome.open_characterization_methods] Opening characterization methods window")

        """Open the material welcome window."""
        # Log device transfer to welcome window
        if self.vna:
            device_type = type(self.vna).__name__
            logging.info(f"[connection_window.open_characterization_methods] Device {device_type} available - passing to welcome window")
            self.welcome_windows = CharacterizationWizard(vna_device=self.vna)
        else:
            logging.info("[connection_window.open_characterization_methods] No device connected - using placeholder mode")
            self.welcome_windows = CharacterizationWizard()
            
        self.welcome_windows.show()
        self.close() 

        

if __name__ == "__main__":

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    ventana = MaterialCharacterizationWelcome()
    ventana.show()

    sys.exit(app.exec())