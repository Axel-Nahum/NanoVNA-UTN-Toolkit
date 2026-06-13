"""
This method contains the implementation of the Preferences dialog for the NanoVNA UTN Toolkit application.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QComboBox, QFrame, QSizePolicy
)

toggle_menu_dark_mode = safe_import("NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "toggle_menu_dark_mode")

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

MenuResourceLoader = safe_import("NanoVNA_UTN_Toolkit.shared.resources.menu_resource_loader", "MenuResourceLoader")

# ------------------------------------------------------------------------------------------------------------------- #
# Open Preferences Dialog
# ------------------------------------------------------------------------------------------------------------------- #

def open_preferences_dialog(self):

    dialog = QDialog(self)

    dialog.setWindowTitle("Preferences")

    dialog.setFixedSize(340, 260)

    dialog.setStyleSheet(self.styleSheet())

# ------------------------------------------------------------------------------------------------------------------- #
# Main Layout
# ------------------------------------------------------------------------------------------------------------------- #

    layout = QVBoxLayout(dialog)

    layout.setContentsMargins(20, 20, 20, 20)

    layout.setSpacing(20)

# ------------------------------------------------------------------------------------------------------------------- #
# Preferences Title
# ------------------------------------------------------------------------------------------------------------------- #

    settings_title = QLabel("Application Settings")

    settings_title.setStyleSheet("""
        font-size: 15px;
        font-weight: bold;
    """)

# ------------------------------------------------------------------------------------------------------------------- #
# Preferences Frame
# ------------------------------------------------------------------------------------------------------------------- #

    preferences_frame = QFrame()

    preferences_frame.setStyleSheet("""
        QFrame {
            border: 1px solid gray;
            border-radius: 10px;
        }
    """)

    preferences_layout = QVBoxLayout(preferences_frame)

    preferences_layout.setContentsMargins(20, 20, 20, 20)

    preferences_layout.setSpacing(20)

# ------------------------------------------------------------------------------------------------------------------- #
# Theme
# ------------------------------------------------------------------------------------------------------------------- #

    theme_layout = QHBoxLayout()

    theme_label = QLabel("Theme:")

    theme_label.setStyleSheet("""
        font-size: 15px;
        border: none;
    """)

    self.theme_combo = QComboBox()

    self.theme_combo.addItems([
        "Dark",
        "Light"
    ])

    settings = get_settings(
        "INI/dut_measurement/preferences/preferences.ini",
        "shared/utils/preferences/preferences.ini", 
        Path(__file__).resolve()
    )

    dark_light_mode = settings.value("Preferences/dark_light_mode", "Dark")

    if dark_light_mode == "Dark":
        self.theme_combo.setCurrentIndex(0)
    else:
        self.theme_combo.setCurrentIndex(1)

    self.theme_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    self.theme_combo.setFixedSize(85, 30)

    theme_layout.addWidget(theme_label)

    theme_layout.addStretch()

    theme_layout.addWidget(self.theme_combo)

# ------------------------------------------------------------------------------------------------------------------- #
# Language
# ------------------------------------------------------------------------------------------------------------------- #

    language_layout = QHBoxLayout()

    language_label = QLabel("Language:")
    language_label.setStyleSheet("font-size: 15px;")

    language_label.setStyleSheet("""
        font-size: 15px;
        border: none;
    """)

    self.language_combo = QComboBox()

    self.language_combo.addItems([
        "EN",
        "ES"
    ])

    language = settings.value("Preferences/language", "EN")

    if language == "EN":
        self.language_combo.setCurrentIndex(0)
    elif language == "ES":
        self.language_combo.setCurrentIndex(1)

    self.language_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    self.language_combo.setFixedSize(85, 30)

    language_layout.addWidget(language_label)

    language_layout.addStretch()

    language_layout.addWidget(self.language_combo)

# ------------------------------------------------------------------------------------------------------------------- #
# Add Settings Layouts
# ------------------------------------------------------------------------------------------------------------------- #

    preferences_layout.addLayout(theme_layout)

    preferences_layout.addLayout(language_layout)

# ------------------------------------------------------------------------------------------------------------------- #
# Buttons
# ------------------------------------------------------------------------------------------------------------------- #

    buttons_layout = QHBoxLayout()

    buttons_layout.setSpacing(15)

    apply_button = QPushButton("Apply")
    close_button = QPushButton("Close")

    apply_button.setFixedWidth(100)
    close_button.setFixedWidth(100)

    apply_button.clicked.connect(lambda: apply_preferences(self,dialog))
    close_button.clicked.connect(dialog.close)

    buttons_layout.addStretch()

    buttons_layout.addWidget(apply_button)
    buttons_layout.addWidget(close_button)

    buttons_layout.addStretch()

# ------------------------------------------------------------------------------------------------------------------- #
# Final Layout
# ------------------------------------------------------------------------------------------------------------------- #

    layout.addWidget(settings_title)

    layout.addWidget(preferences_frame)

    layout.addStretch()

    layout.addLayout(buttons_layout)

# ------------------------------------------------------------------------------------------------------------------- #

    dialog.exec()

# ------------------------------------------------------------------------------------------------------------------- #
# Apply Preferences
# ------------------------------------------------------------------------------------------------------------------- #

def apply_preferences(self, dialog):

    change_theme(self, self.theme_combo.currentText(), dialog)
    change_language(self, self.language_combo.currentText(), dialog)

# ------------------------------------------------------------------------------------------------------------------- #
# Change Theme
# ------------------------------------------------------------------------------------------------------------------- #

def change_theme(self, theme, dialog):

    settings = get_settings(
        "INI/dut_measurement/preferences/preferences.ini",
        "shared/utils/preferences/preferences.ini", 
        Path(__file__).resolve()
    )

    if theme == "Dark":

        self.is_dark_mode = True

        settings.setValue("Preferences/dark_light_mode", "Dark")

    elif theme == "Light":

        self.is_dark_mode = False

        settings.setValue("Preferences/dark_light_mode", "Light")

    toggle_menu_dark_mode(self, self.is_dark_mode, preference_menu = "True")

    dialog.close()

# ------------------------------------------------------------------------------------------------------------------- #
# Change Language
# ------------------------------------------------------------------------------------------------------------------- #

def change_language(self, language, dialog):

    settings = get_settings(
        "INI/dut_measurement/preferences/preferences.ini",
        "shared/utils/preferences/preferences.ini", 
        Path(__file__).resolve()
    )

    if language == "EN":

        current_lang = "en"

        settings.setValue("Preferences/language", "EN")

    elif language == "ES":

        current_lang = "es"

        settings.setValue("Preferences/language", "ES")

    resourceLoader = MenuResourceLoader(
        self_window=self,
        module="menu_resource",
        lang=current_lang,
        json_resource="menu_resource.json"
    )

    resourceLoader.load_main_menu_resources()

    update_ui_texts(self)

    dialog.close()

# ------------------------------------------------------------------------------------------------------------------- #
# Update UI Menu Texts
# ------------------------------------------------------------------------------------------------------------------- #

def update_ui_texts(self):

    self.description_label.setText(
        self.menu_description
    )

    self.dut_title_label.setText(
        self.dut_measurement_title
    )

    self.dut_description_label.setText(
        self.dut_measurement_description
    )

    self.materials_title_label.setText(
        self.materials_characterization_title
    )

    self.materials_description_label.setText(
        self.materials_characterization_description
    )