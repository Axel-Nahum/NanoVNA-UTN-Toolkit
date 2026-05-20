"""
Material characterization setup window for NanoVNA devices.
"""

import logging
import os
import sys

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
from PySide6.QtGui import QAction, QIcon

# Import calibration data storage
try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.calibration_manager import (
        OSMCalibrationManager,
        THRUCalibrationManager
    )
except ImportError as e:
    logging.error("Failed to import calibration managers: %s", e)
    OSMCalibrationManager = None
    THRUCalibrationManager = None

try:
    from NanoVNA_UTN_Toolkit.shared.utils.settings_utils import get_settings
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
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

# ------------------------------------------------------------------------------------------------------------------ #

class MaterialCharacterizationWelcome(QMainWindow):

    def __init__(self, s11=None, freqs=None, vna_device=None):
        super().__init__()

        self.vna = vna_device

# ------------------------------------------------------------------------------------------------------------------ #

        # Dark-Light mode settings
        dark_light_config(self)

# ------------------------------------------------------------------------------------------------------------------ #

        self.vna_device = vna_device

        logging.info(
            "[material_characterization_welcome.__init__] Initializing material characterization welcome window"
        )

# ---------------------------------------------------------------------------------------------------------- #
# Window Icon
# ---------------------------------------------------------------------------------------------------------- #

        apply_window_icon(self)

# ---------------------------------------------------------------------------------------------------------- #
# Window Configuration
# ---------------------------------------------------------------------------------------------------------- #

        self.setWindowTitle("NanoVNA UTN Toolkit - Material Characterization")
        self.setGeometry(100, 100, 1000, 460)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self._create_characterization_group(main_layout)

        main_layout.addStretch()

        # Menus
        self._create_menus()
# ------------------------------------------------------------------------------------------------------------------ #

    def _create_menus(self):

        #menubar = self.menuBar()

        """
        # FILE
        file_menu = menubar.addMenu("File")

        exit_action = QAction("Back to menu", self)
        exit_action.triggered.connect(self.return_to_menu_window)
        file_menu.addAction(exit_action)
        """
# ------------------------------------------------------------------------------------------------------------------ #

    def _create_characterization_group(self, parent_layout):

        logging.info(
            "[material_characterization_welcome._create_characterization_group] Creating characterization group"
        )

        settings = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "ui/utils/settings/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve()
        )

        groupbox_border = settings.value(
            "Dark_Light/QGroupBox/color",
            "1px solid #b0b0b0"
        )

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

        # ---------------------------------------------------------------------------------------------------------- #
        # DESCRIPTION GROUP
        # ---------------------------------------------------------------------------------------------------------- #

        description_group = QGroupBox("Module Overview")
        description_group.setStyleSheet(groupbox_style)

        description_layout = QVBoxLayout(description_group)

        description_text = QLabel(
            "The Material Characterization module allows the analysis and "
            "electromagnetic characterization of different materials using a NanoVNA.\n\n"
            "The module supports characterization workflows with dedicated calibration "
            "kits adapted to each measurement method, improving accuracy and repeatability "
            "for specific applications.\n\n"
            "Both solid and liquid materials can be characterized depending on the selected "
            "method and measurement setup.\n\n"
            "Through the obtained S-parameters, the system enables the analysis and "
            "estimation of electromagnetic properties such as relative permittivity "
            "and permeability across frequency."
        )

        description_text.setWordWrap(True)

        description_text.setStyleSheet(
            "font-size: 13px; "
            "color: #cccccc; "
            "padding: 10px;"
        )

        description_layout.addWidget(description_text)

        parent_layout.addWidget(description_group)

        # ---------------------------------------------------------------------------------------------------------- #
        # MAIN CHARACTERIZATION GROUP
        # ---------------------------------------------------------------------------------------------------------- #

        characterization_group = QGroupBox("Material Characterization")
        characterization_group.setStyleSheet(groupbox_style)

        characterization_layout = QVBoxLayout(characterization_group)
        characterization_layout.setSpacing(20)

        self._create_calibration_section(characterization_layout)

        parent_layout.addWidget(characterization_group)

# ------------------------------------------------------------------------------------------------------------------ #

    def _create_calibration_section(self, parent_layout):

        section_layout = QHBoxLayout()
        section_layout.setSpacing(40)

        # ---------------------------------------------------------------------------------------------------------- #
        # LEFT SIDE - KIT SELECTION
        # ---------------------------------------------------------------------------------------------------------- #

        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        kit_selector_label = QLabel("Method Characterization Kit Selection:")

        kit_selector_label.setStyleSheet(
            "font-weight: bold; "
            "font-size: 14px;"
        )

        left_layout.addWidget(kit_selector_label)

        self._load_characterization_kits()

        self.kit_dropdown = QComboBox()
        self.kit_dropdown.setFixedHeight(40)
        self.kit_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
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

        self._set_current_kit_selection()

        self.kit_dropdown.currentTextChanged.connect(
            self._on_kit_selection_changed
        )

        left_layout.addWidget(self.kit_dropdown)

        self.kit_info_label = QLabel("")

        self.kit_info_label.setStyleSheet(
            "font-size: 12px; "
            "color: #cccccc; "
            "padding-top: 5px;"
        )

        self.kit_info_label.setWordWrap(True)

        left_layout.addWidget(self.kit_info_label)

        current_text = self.kit_dropdown.currentText()

        if current_text.startswith("None"):
            self.selected_kit_name = None
        else:
            self.selected_kit_name = current_text

        self._update_kit_info_display()

        # ---------------------------------------------------------------------------------------------------------- #
        # OPEN METHODS BUTTON
        # ---------------------------------------------------------------------------------------------------------- #

        self.characterization_methods_button = QPushButton(
            "Open Characterization Methods"
        )

        self.characterization_methods_button.clicked.connect(
            self.open_characterization_methods
        )

        self.characterization_methods_button.setFixedHeight(45)

        self.characterization_methods_button.setStyleSheet(
            "font-size: 14px;"
        )

        left_layout.addWidget(
            self.characterization_methods_button
        )

        section_layout.addLayout(left_layout)

        # ---------------------------------------------------------------------------------------------------------- #
        # RIGHT SIDE - IMPORT
        # ---------------------------------------------------------------------------------------------------------- #

        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)

        import_title = QLabel("Import Characterization Package:")

        import_title.setStyleSheet(
            "font-weight: bold; "
            "font-size: 14px;"
        )

        right_layout.addWidget(import_title)

        import_description = QLabel(
            "Import a complete characterization package that already "
            "contains its associated calibration and configuration data."
        )

        import_description.setWordWrap(True)

        import_description.setStyleSheet(
            "font-size: 12px; "
            "color: #cccccc;"
        )

        right_layout.addWidget(import_description)

        right_layout.addStretch()

        self.import_button = QPushButton("Import")

        self.import_button.clicked.connect(
            self.import_characterization_package
        )

        self.import_button.setFixedHeight(45)

        self.import_button.setStyleSheet(
            "font-size: 14px;"
        )

        right_layout.addWidget(self.import_button)

        section_layout.addLayout(right_layout)

        parent_layout.addLayout(section_layout)

# ------------------------------------------------------------------------------------------------------------------ #

    def _set_current_kit_selection(self):

        logging.info("h")

# ------------------------------------------------------------------------------------------------------------------ #

    def _on_kit_selection_changed(self, selected_text):

        logging.info("h")

# ------------------------------------------------------------------------------------------------------------------ #

    def _update_kit_info_display(self):

        if hasattr(self, 'selected_kit_name') and self.selected_kit_name:

            if self.selected_kit_name in self.kit_names:

                kit_index = self.kit_names.index(self.selected_kit_name)

                kit_id = (
                    self.kit_ids[kit_index]
                    if kit_index < len(self.kit_ids)
                    else "Unknown"
                )

        else:
            self.kit_info_label.setText(
                "No calibration kit selected"
            )

# ------------------------------------------------------------------------------------------------------------------ #

    def _load_characterization_kits(self):

       logging.info("[load_characterization_kits]")
# ------------------------------------------------------------------------------------------------------------------ #

    def _get_current_calibration_name(self):

        settings_calibration = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )

        calibration_name = settings_calibration.value(
            "Calibration/Name",
            "No Calibration"
        )

        return calibration_name

# ------------------------------------------------------------------------------------------------------------------ #

    def import_characterization_package(self):

        logging.info(
            "[material_characterization_welcome.import_characterization_package] Import characterization package clicked"
        )

# ------------------------------------------------------------------------------------------------------------------ #

    def open_characterization_methods(self):

        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.wizard_methods_window import CharacterizationWizard

        logging.info(
            "[material_characterization_welcome.open_characterization_methods] Opening characterization methods window"
        )

        if self.vna:

            device_type = type(self.vna).__name__

            logging.info(
                f"[connection_window.open_characterization_methods] "
                f"Device {device_type} available - passing to welcome window"
            )

            self.welcome_windows = CharacterizationWizard(
                vna_device=self.vna
            )

        else:

            logging.info(
                "[connection_window.open_characterization_methods] "
                "No device connected - using placeholder mode"
            )

            self.welcome_windows = CharacterizationWizard()

        self.welcome_windows.show()

        self.close()

    def return_to_menu_window(self):

        from NanoVNA_UTN_Toolkit.modules.menu_window import ModuleSelectionWindow
        
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

# ------------------------------------------------------------------------------------------------------------------ #

if __name__ == "__main__":

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    ventana = MaterialCharacterizationWelcome()

    ventana.show()

    sys.exit(app.exec())