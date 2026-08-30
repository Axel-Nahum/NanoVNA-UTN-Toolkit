"""
Main launcher menu window for NanoVNA-UTN Toolkit modules.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QMainWindow,
    QFrame
)

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

dark_light_config = safe_import("NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "dark_light_config")

apply_window_icon = safe_import("NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon")

MenuResourceLoader = safe_import("NanoVNA_UTN_Toolkit.shared.resources.menu_resource_loader", "MenuResourceLoader")

open_preferences_dialog = safe_import("NanoVNA_UTN_Toolkit.shared.utils.preferences.preferences", "open_preferences_dialog")

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.welcome_window.welcome_windows import NanoVNAWelcome

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.characterization_welcome.characterization_welcome import MaterialCharacterizationWelcome
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.characterization_welcome.characterization_welcome_false import CharacterizationFalse

# ------------------------------------------------------------------------------------------------------------------- #

class ModuleSelectionWindow(QMainWindow):

    def __init__(self, vna_device=None):
        super().__init__()

        self.vna = vna_device

# ------------------------------------------------------------------------------------------------------------------- #
# Load JSON
# ------------------------------------------------------------------------------------------------------------------- #

        settings = get_settings(
            "INI/dut_measurement/preferences/preferences.ini",
            "shared/utils/preferences/preferences.ini", 
            Path(__file__).resolve()
        )

        current_lang = settings.value("Preferences/language", "en")

        self.resourceLoader = MenuResourceLoader(
            self_window=self,
            module="menu_resource",
            lang=current_lang,
            json_resource="menu_resource.json"
        )

        self.resourceLoader.load_main_menu_resources()

# ------------------------------------------------------------------------------------------------------------------- #
# Dark light Mode
# ------------------------------------------------------------------------------------------------------------------- #

        dark_light_config(self)

        _theme_cfg = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve(),
        )
        self.is_dark_mode = _theme_cfg.value("Dark_Light/is_dark_mode", False, type=bool)
        _is_dark = not self.is_dark_mode
        if _is_dark:
            self._card_style = (
                "QFrame { background-color: #252538; border: 1px solid #383850;"
                " border-radius: 10px; padding: 10px; }"
            )
            self._btn_open_style = """
                QPushButton { background-color: #1a3a5c; color: white; border: 1px solid #2d5a8e;
                    border-radius: 6px; font-size: 14px; font-weight: bold; }
                QPushButton:hover  { background-color: #254e7a; }
                QPushButton:pressed { background-color: #12263d; }
            """
            self._btn_pref_style = """
                QPushButton { background-color: #1c2533; color: #7ab3f5; border: 1px solid #2d5a8e;
                    border-radius: 6px; font-size: 13px; font-weight: 500; padding: 4px 12px; }
                QPushButton:hover  { background-color: #1a3a5c; color: #aacfff; border: 1px solid #4da6ff; }
                QPushButton:pressed { background-color: #12263d; }
            """
        else:
            self._card_style = (
                "QFrame { background-color: #e8e8f4; border: 1px solid #c4c4d8;"
                " border-radius: 10px; padding: 10px; }"
            )
            self._btn_open_style = """
                QPushButton { background-color: #2d5a8e; color: white; border: 1px solid #a0bcd8;
                    border-radius: 6px; font-size: 14px; font-weight: bold; }
                QPushButton:hover  { background-color: #3a6fa8; }
                QPushButton:pressed { background-color: #1a4a7a; }
            """
            self._btn_pref_style = """
                QPushButton { background-color: #e0e0f0; color: #1e1e2e; border: 1px solid #c4c4d8;
                    border-radius: 6px; font-size: 13px; font-weight: 500; padding: 4px 12px; }
                QPushButton:hover  { background-color: #d0d0e8; }
                QPushButton:pressed { background-color: #c0c0d8; }
            """

# ------------------------------------------------------------------------------------------------------------------- #
# Title and Window Size
# ------------------------------------------------------------------------------------------------------------------- #

        self.setWindowTitle(f"{self.menu_title}")
        self.setFixedSize(850, 500)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()

        center_point = screen.center()
        window_geometry.moveCenter(center_point)

        self.move(window_geometry.topLeft())

        logging.info("[ModuleSelectionWindow] Initializing launcher menu")

        apply_window_icon(self)

# ------------------------------------------------------------------------------------------------------------------- #
# Central Widget
# ------------------------------------------------------------------------------------------------------------------- #

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(30)
        main_layout.setAlignment(Qt.AlignTop)

# ------------------------------------------------------------------------------------------------------------------- #
# Header
# ------------------------------------------------------------------------------------------------------------------- #

        self.title_label = QLabel(self.menu_title)

        self.title_label.setAlignment(Qt.AlignCenter)

        self.title_label.setStyleSheet("""
            font-size: 30px;
            font-weight: bold;
        """)

        self.description_label = QLabel(
            self.menu_description
        )

        self.description_label.setAlignment(Qt.AlignCenter)

        self.description_label.setWordWrap(True)

        self.description_label.setStyleSheet("""
            font-size: 15px;
        """)

# ------------------------------------------------------------------------------------------------------------------- #
# Modules Layout
# ------------------------------------------------------------------------------------------------------------------- #

        modules_layout = QHBoxLayout()

        modules_layout.setSpacing(30)
        modules_layout.setAlignment(Qt.AlignCenter)

# ------------------------------------------------------------------------------------------------------------------- #
# DUT Card
# ------------------------------------------------------------------------------------------------------------------- #

        self.dut_card = QFrame()
        self.dut_card.setFixedSize(300, 230)
        self.dut_card.setStyleSheet(self._card_style)

        dut_layout = QVBoxLayout(self.dut_card)

        dut_layout.setSpacing(15)

        self.dut_title_label = QLabel(
            self.dut_measurement_title
        )

        self.dut_title_label.setAlignment(Qt.AlignCenter)

        self.dut_title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            border: none;
        """)

        self.dut_description_label = QLabel(
            self.dut_measurement_description
        )

        self.dut_description_label.setAlignment(Qt.AlignCenter)

        self.dut_description_label.setWordWrap(True)

        self.dut_description_label.setStyleSheet("""
            font-size: 13px;
            border: none;
        """)

        self.dut_button = QPushButton("Open")

        self.dut_button.setFixedSize(140, 40)

        self.dut_button.setStyleSheet(self._btn_open_style)

        self.dut_button.clicked.connect(
            self.open_dut_measurement_module
        )

        dut_layout.addWidget(self.dut_title_label)
        dut_layout.addWidget(self.dut_description_label)

        dut_layout.addStretch()

        dut_layout.addWidget(
            self.dut_button,
            alignment=Qt.AlignCenter
        )

# ------------------------------------------------------------------------------------------------------------------- #
# Materials Card
# ------------------------------------------------------------------------------------------------------------------- #

        self.materials_card = QFrame()
        self.materials_card.setFixedSize(300, 230)
        self.materials_card.setStyleSheet(self._card_style)

        materials_layout = QVBoxLayout(self.materials_card)

        materials_layout.setSpacing(15)

        self.materials_title_label = QLabel(self.materials_characterization_title)
        self.materials_title_label.setAlignment(Qt.AlignCenter)
        self.materials_title_label.setWordWrap(True)
        self.materials_title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            border: none;
        """)

        self.materials_description_label = QLabel(self.materials_characterization_description)
        self.materials_description_label.setAlignment(Qt.AlignCenter)
        self.materials_description_label.setWordWrap(True)
        self.materials_description_label.setStyleSheet("""
            font-size: 13px;
            border: none;
        """)

        self.materials_button = QPushButton("Open")

        self.materials_button.setFixedSize(140, 40)

        self.materials_button.setStyleSheet(self._btn_open_style)

        self.materials_button.clicked.connect(
            self.open_material_characterization_module
        )

        materials_layout.addWidget(self.materials_title_label)
        materials_layout.addWidget(self.materials_description_label)

        materials_layout.addStretch()

        materials_layout.addWidget(
            self.materials_button,
            alignment=Qt.AlignCenter
        )

# ------------------------------------------------------------------------------------------------------------------- #
# Add Cards
# ------------------------------------------------------------------------------------------------------------------- #

        modules_layout.addWidget(self.dut_card)
        modules_layout.addWidget(self.materials_card)

# ------------------------------------------------------------------------------------------------------------------- #
# Preferences Button
# ------------------------------------------------------------------------------------------------------------------- #

        self.preferences_button = QPushButton("⚙ Preferences")
        self.preferences_button.setFixedSize(180, 35)
        self.preferences_button.setStyleSheet(self._btn_pref_style)
        self.preferences_button.clicked.connect(lambda: open_preferences_dialog(self))

# ------------------------------------------------------------------------------------------------------------------- #
# Main Layout
# ------------------------------------------------------------------------------------------------------------------- #

        main_layout.addStretch()

        main_layout.addWidget(self.title_label)

        main_layout.addWidget(self.description_label)

        main_layout.addSpacing(20)

        main_layout.addLayout(modules_layout)

        main_layout.addSpacing(25)

        main_layout.addWidget(
            self.preferences_button,
            alignment=Qt.AlignCenter
        )

        main_layout.addStretch()

# ------------------------------------------------------------------------------------------------------------------- #
# Live theme update
# ------------------------------------------------------------------------------------------------------------------- #

    def setStyleSheet(self, stylesheet: str) -> None:
        super().setStyleSheet(stylesheet)
        if not hasattr(self, "dut_card"):
            return
        # is_dark_mode=True when toggle_menu_dark_mode is about to apply dark
        _going_dark = getattr(self, "is_dark_mode", False)
        if _going_dark:
            _card = (
                "QFrame { background-color: #252538; border: 1px solid #383850;"
                " border-radius: 10px; padding: 10px; }"
            )
            _btn_open = (
                "QPushButton { background-color: #1a3a5c; color: white;"
                " border: 1px solid #2d5a8e; border-radius: 6px;"
                " font-size: 14px; font-weight: bold; }"
                " QPushButton:hover { background-color: #254e7a; }"
                " QPushButton:pressed { background-color: #12263d; }"
            )
            _btn_pref = (
                "QPushButton { background-color: #1c2533; color: #7ab3f5;"
                " border: 1px solid #2d5a8e; border-radius: 6px;"
                " font-size: 13px; font-weight: 500; padding: 4px 12px; }"
                " QPushButton:hover { background-color: #1a3a5c; color: #aacfff;"
                " border: 1px solid #4da6ff; }"
                " QPushButton:pressed { background-color: #12263d; }"
            )
        else:
            _card = (
                "QFrame { background-color: #e8e8f4; border: 1px solid #c4c4d8;"
                " border-radius: 10px; padding: 10px; }"
            )
            _btn_open = (
                "QPushButton { background-color: #2d5a8e; color: white;"
                " border: 1px solid #a0bcd8; border-radius: 6px;"
                " font-size: 14px; font-weight: bold; }"
                " QPushButton:hover { background-color: #3a6fa8; }"
                " QPushButton:pressed { background-color: #1a4a7a; }"
            )
            _btn_pref = (
                "QPushButton { background-color: #e0e0f0; color: #1e1e2e;"
                " border: 1px solid #c4c4d8; border-radius: 6px;"
                " font-size: 13px; font-weight: 500; padding: 4px 12px; }"
                " QPushButton:hover { background-color: #d0d0e8; }"
                " QPushButton:pressed { background-color: #c0c0d8; }"
            )
        self.dut_card.setStyleSheet(_card)
        self.materials_card.setStyleSheet(_card)
        self.dut_button.setStyleSheet(_btn_open)
        self.materials_button.setStyleSheet(_btn_open)
        self.preferences_button.setStyleSheet(_btn_pref)

# ------------------------------------------------------------------------------------------------------------------- #
# Open DUT Module
# ------------------------------------------------------------------------------------------------------------------- #

    def open_dut_measurement_module(self):

        if self.vna:

            device_type = type(self.vna).__name__

            logging.info(
                f"[ModuleSelectionWindow] Device {device_type} available - opening DUT module"
            )

            self.welcome_windows = NanoVNAWelcome(
                vna_device=self.vna
            )

        else:

            logging.info(
                "[ModuleSelectionWindow] No device connected - using placeholder mode"
            )

            self.welcome_windows = NanoVNAWelcome()

        self.welcome_windows.show()

        self.close()

# ------------------------------------------------------------------------------------------------------------------- #
# Open Material Characterization Module
# ------------------------------------------------------------------------------------------------------------------- #

    def open_material_characterization_module(self):

        if self.vna:

            device_type = type(self.vna).__name__

            logging.info(
                f"[ModuleSelectionWindow] Device {device_type} available - opening material characterization module"
            )

            self.welcome_windows = MaterialCharacterizationWelcome(
                vna_device=self.vna
            )

            #self.welcome_windows = CharacterizationFalse()

        else:

            logging.info(
                "[ModuleSelectionWindow] No device connected - using placeholder mode"
            )

            self.welcome_windows = MaterialCharacterizationWelcome()
            #self.welcome_windows = CharacterizationFalse()

        self.welcome_windows.show()

        self.close()

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = ModuleSelectionWindow()

    window.show()

    sys.exit(app.exec())