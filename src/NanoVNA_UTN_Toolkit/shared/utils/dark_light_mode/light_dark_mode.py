from NanoVNA_UTN_Toolkit.utils import safe_import
import sys
import logging
from turtle import color

logging.basicConfig(level=logging.INFO)

from pathlib import Path

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

# ------------------------------------------------------------------------------------------------------------------ #

def toggle_menu_dark_mode(self, light_dark_mode, preference_menu = "False"):

    # Load configuration for UI colors and styles
    settings = get_settings(
        "INI/dut_measurement/dark_light_config/dark_light_config.ini", 
        "shared/utils/dark_light_mode/dark_light_config.ini",
        Path(__file__).resolve()
    )

    if self.is_dark_mode:
        if preference_menu == "False":
            light_dark_mode.setText("Light Mode 🔆")

        # --- QWidget ---
        settings.setValue("Dark_Light/QWidget/background-color", "#1e1e2e")

        # --- Qframe ---
        settings.setValue("Dark_Light/Qframe/background-color", "white")
        settings.setValue("Dark_Light/Qframe/color", "white")

        # --- QTabWidget pane ---
        settings.setValue("Dark_Light/QTabWidget_pane/background-color", "#2e2e42")

        # --- QTabBar ---
        settings.setValue("Dark_Light/QTabBar/background-color", "#2a2a3e")
        settings.setValue("Dark_Light/QTabBar/color", "white")
        settings.setValue("Dark_Light/QTabBar/padding", "5px 12px")
        settings.setValue("Dark_Light/QTabBar/border", "none")
        settings.setValue("Dark_Light/QTabBar/border-top-left-radius", "6px")
        settings.setValue("Dark_Light/QTabBar/border-top-right-radius", "6px")

        # --- QTabBar selected ---
        settings.setValue("Dark_Light/QTabBar_selected/background-color", "#3a3a54")
        settings.setValue("Dark_Light/QTabBar_selected/color", "white")

        # --- QSpinBox ---
        settings.setValue("Dark_Light/QSpinBox/color", "white")
        settings.setValue("Dark_Light/QSpinBox/background-color", "#252538")
        settings.setValue("Dark_Light/QSpinBox/border", "1px solid #383850")
        settings.setValue("Dark_Light/QSpinBox/border-radius", "8px")

        # --- QGroupBox title ---
        settings.setValue("Dark_Light/QGroupBox_title/color", "white")

        # --- QGroupBox border ---
        settings.setValue("Dark_Light/QGroupBox/border", "1px solid white")
        settings.setValue("Dark_Light/QGroupBox/border-radius", "8px")
        settings.setValue("Dark_Light/QGroupBox/margin-top", "1.5ex")
        settings.setValue("Dark_Light/QGroupBox/padding", "8px")

        # --- QLabel ---
        settings.setValue("Dark_Light/QLabel/color", "white")

        # --- QLineEdit ---
        settings.setValue("Dark_Light/QLineEdit/background-color", "#252538")
        settings.setValue("Dark_Light/QLineEdit/color", "white")
        settings.setValue("Dark_Light/QLineEdit/border", "1px solid #383850")
        settings.setValue("Dark_Light/QLineEdit/border-radius", "6px")
        settings.setValue("Dark_Light/QLineEdit/padding", "4px")

        # --- QLineEdit focus ---
        settings.setValue("Dark_Light/QLineEdit_focus/background-color", "#2e2e42")
        settings.setValue("Dark_Light/QLineEdit_focus/border", "1px solid #6aa2ff")

        # --- QPushButton ---
        settings.setValue("Dark_Light/QPushButton/background-color", "#2e2e42")
        settings.setValue("Dark_Light/QPushButton/color", "white")
        settings.setValue("Dark_Light/QPushButton/border", "1px solid #383850")
        settings.setValue("Dark_Light/QPushButton/border-radius", "6px")
        settings.setValue("Dark_Light/QPushButton/padding", "4px 10px")

        # --- QPushButton hover/pressed ---
        settings.setValue("Dark_Light/QPushButton_hover/background-color", "#3a3a54")
        settings.setValue("Dark_Light/QPushButton_pressed/background-color", "#1a1a2e")

        # --- QPushButton disabled ---
        settings.setValue("Dark_Light/QPushButton_disabled/background-color", "#1e1e2e")
        settings.setValue("Dark_Light/QPushButton_disabled/color", "#5a5a78")
        settings.setValue("Dark_Light/QPushButton_disabled/border", "1px solid #2a2a3e")

        # --- QMenu ---
        settings.setValue("Dark_Light/QMenu/background", "#2e2e42")
        settings.setValue("Dark_Light/QMenu/color", "white")
        settings.setValue("Dark_Light/QMenu/border", "1px solid #383850")

        # --- QMenuBar ---
        settings.setValue("Dark_Light/QMenuBar/background-color", "#1e1e2e")
        settings.setValue("Dark_Light/QMenuBar/color", "white")

        # --- QMenuBar items ---
        settings.setValue("Dark_Light/QMenuBar_item/background", "transparent")
        settings.setValue("Dark_Light/QMenuBar_item/color", "white")
        settings.setValue("Dark_Light/QMenuBar_item/padding", "4px 10px")

        # --- QMenuBar selected item ---
        settings.setValue("Dark_Light/QMenuBar_item_selected/background-color", "#3a3a54")

        # --- QMenu selected item ---
        settings.setValue("Dark_Light/QMenu_item_selected/background-color", "#3a3a54")

        # --- QComboBox ---
        settings.setValue("Dark_Light/QComboBox/color", "white")
        settings.setValue("Dark_Light/QComboBox/background-color", "#2a2a3e")
        settings.setValue("Dark_Light/QComboBox/border", "1px solid #383850")
        settings.setValue("Dark_Light/QComboBox/border-radius", "6px")

        # --- QComboBox hover/focus ---
        settings.setValue("Dark_Light/QComboBox:hover/background-color", "#363650")
        settings.setValue("Dark_Light/QComboBox:focus/background-color", "#363650")

        # --- QComboBox placeholder ---
        settings.setValue("Dark_Light/QComboBox::placeholder/color", "#8888aa")

        # --- QCheckBox ---
        settings.setValue("Dark_Light/QCheckBox/color", "white")
        settings.setValue("Dark_Light/QCheckBox/background-color", "#252538")
        settings.setValue("Dark_Light/QCheckBox/border", "1px solid #383850")

        # --- QCheckBox checked ---
        settings.setValue("Dark_Light/QCheckBox_checked/background-color", "#4d90fe")
        settings.setValue("Dark_Light/QCheckBox_checked/border", "1px solid #4d90fe")

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
            }

            QTabWidget::pane {
                background-color: #2e2e42;
            }

            QMenu::separator {
                height: 1px;
                background: #383850;
                margin: 3px 8px;
            }

            QTabBar::tab {
                background-color: #2a2a3e;
                color: white;
                padding: 5px 12px;
                border: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }

            QTabBar::tab:selected {
                background-color: #3a3a54;
                color: white;
            }

            QSpinBox {
                background-color: #252538;
                color: white;
                border: 1px solid #383850;
                border-radius: 8px;
            }

            QGroupBox:title,
            QLabel,
            QRadioButton,
            QTextEdit {
                color: white;
            }

            QLineEdit {
                background-color: #252538;
                color: white;
                border: 1px solid #383850;
                border-radius: 6px;
                padding: 4px;
            }

            QLineEdit:focus {
                background-color: #2e2e42;
                border: 1px solid #6aa2ff;
            }

            QPushButton {
                background-color: #2e2e42;
                color: white;
                border: 1px solid #383850;
                border-radius: 6px;
                padding: 4px 10px;
            }

            QPushButton:hover {
                background-color: #3a3a54;
            }

            QPushButton:pressed {
                background-color: #1a1a2e;
            }

            QPushButton:disabled {
                background-color: #1e1e2e;
                color: #5a5a78;
                border: 1px solid #2a2a3e;
            }

            QMenuBar {
                background-color: #1e1e2e;
                color: white;
            }

            QMenuBar::item {
                background: transparent;
                color: white;
                padding: 4px 10px;
            }

            QMenuBar::item:selected {
                background: #3a3a54;
            }

            QMenu {
                background-color: #2e2e42;
                color: white;
                border: 1px solid #383850;
            }

            QMenu::item:selected {
                background-color: #3a3a54;
            }

            QComboBox {
                background-color: #2a2a3e;
                color: white;
                border: 1px solid #383850;
                border-radius: 6px;
                padding-left: 8px;
            }

            QComboBox:hover {
                background-color: #363650;
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
                background-color: #2a2a3e;
                color: white;
                selection-background-color: #363650;
                selection-color: white;
                border: 1px solid #383850;
            }

            QComboBox:focus {
                background-color: #363650;
            }

            QComboBox::placeholder {
                color: #8888aa;
            }
        """)
        self.is_dark_mode = False

        settings.setValue("Dark_Light/is_dark_mode", self.is_dark_mode)
        settings.setValue("Dark_Light/text_light_dark", "Light Mode 🔆")

    else:
        if preference_menu == "False":
            light_dark_mode.setText("Dark Mode 🌙")

        # --- QWidget ---
        settings.setValue("Dark_Light/QWidget/background-color", "#f0f0f8")

        # --- Qframe ---
        settings.setValue("Dark_Light/Qframe/background-color", "#c4c4d8")
        settings.setValue("Dark_Light/Qframe/color", "#c4c4d8")

        # --- QTabWidget pane ---
        settings.setValue("Dark_Light/QTabWidget_pane/background-color", "#e8e8f4")

        # --- QTabBar ---
        settings.setValue("Dark_Light/QTabBar/background-color", "#dcdcf0")
        settings.setValue("Dark_Light/QTabBar/color", "#1e1e2e")
        settings.setValue("Dark_Light/QTabBar/padding", "5px 12px")
        settings.setValue("Dark_Light/QTabBar/border", "none")
        settings.setValue("Dark_Light/QTabBar/border-top-left-radius", "6px")
        settings.setValue("Dark_Light/QTabBar/border-top-right-radius", "6px")

        # --- QTabBar selected ---
        settings.setValue("Dark_Light/QTabBar_selected/background-color", "#f0f0f8")
        settings.setValue("Dark_Light/QTabBar/color", "#1e1e2e")

        # --- QTabBar alternate background ---
        settings.setValue("Dark_Light/QTabBar/background-color", "#dcdcf0")

        # --- QSpinBox ---
        settings.setValue("Dark_Light/QSpinBox/background-color", "#f8f8ff")
        settings.setValue("Dark_Light/QSpinBox/color", "#1e1e2e")
        settings.setValue("Dark_Light/QSpinBox/border", "1px solid #c4c4d8")
        settings.setValue("Dark_Light/QSpinBox/border-radius", "8px")

        # --- QGroupBox title ---
        settings.setValue("Dark_Light/QGroupBox_title/color", "#1e1e2e")

        # --- QGroupBox border ---
        settings.setValue("Dark_Light/QGroupBox/border", "1px solid #c4c4d8")
        settings.setValue("Dark_Light/QGroupBox/border-radius", "8px")
        settings.setValue("Dark_Light/QGroupBox/margin-top", "14px")
        settings.setValue("Dark_Light/QGroupBox/padding", "8px")

        # --- QLabel ---
        settings.setValue("Dark_Light/QLabel/color", "#1e1e2e")

        # --- QLineEdit ---
        settings.setValue("Dark_Light/QLineEdit/background-color", "#f8f8ff")
        settings.setValue("Dark_Light/QLineEdit/color", "#1e1e2e")
        settings.setValue("Dark_Light/QLineEdit/border", "1px solid #c4c4d8")
        settings.setValue("Dark_Light/QLineEdit/border-radius", "6px")
        settings.setValue("Dark_Light/QLineEdit/padding", "4px")

        # --- QLineEdit focus ---
        settings.setValue("Dark_Light/QLineEdit_focus/background-color", "#eef0ff")
        settings.setValue("Dark_Light/QLineEdit_focus/border", "1px solid #4d90fe")

        # --- QPushButton ---
        settings.setValue("Dark_Light/QPushButton/background-color", "#e0e0f0")
        settings.setValue("Dark_Light/QPushButton/color", "#1e1e2e")
        settings.setValue("Dark_Light/QPushButton/border", "1px solid #c4c4d8")
        settings.setValue("Dark_Light/QPushButton/border-radius", "6px")
        settings.setValue("Dark_Light/QPushButton/padding", "4px 10px")

        # --- QPushButton hover/pressed ---
        settings.setValue("Dark_Light/QPushButton_hover/background-color", "#d0d0e8")
        settings.setValue("Dark_Light/QPushButton_pressed/background-color", "#c0c0d8")

        # --- QPushButton disabled ---
        settings.setValue("Dark_Light/QPushButton_disabled/background-color", "#eeeef8")
        settings.setValue("Dark_Light/QPushButton_disabled/color", "#8888aa")
        settings.setValue("Dark_Light/QPushButton_disabled/border", "1px solid #d0d0e8")

        # --- QMenu ---
        settings.setValue("Dark_Light/QMenu/background", "#f0f0f8")
        settings.setValue("Dark_Light/QMenu/color", "#1e1e2e")
        settings.setValue("Dark_Light/QMenu/border", "1px solid #c4c4d8")

        # --- QMenuBar ---
        settings.setValue("Dark_Light/QMenuBar/background-color", "#e8e8f4")
        settings.setValue("Dark_Light/QMenuBar/color", "#1e1e2e")

        # --- QMenuBar items ---
        settings.setValue("Dark_Light/QMenuBar_item/background", "transparent")
        settings.setValue("Dark_Light/QMenuBar_item/color", "#1e1e2e")
        settings.setValue("Dark_Light/QMenuBar_item/padding", "4px 10px")

        # --- QMenuBar selected item ---
        settings.setValue("Dark_Light/QMenuBar_item_selected/background-color", "#d0d0e8")

        # --- QMenu selected item ---
        settings.setValue("Dark_Light/QMenu_item_selected/background-color", "#dcdcf0")

        # --- QComboBox ---
        settings.setValue("Dark_Light/QComboBox/color", "#1e1e2e")
        settings.setValue("Dark_Light/QComboBox/background-color", "#ebebf5")
        settings.setValue("Dark_Light/QComboBox/border", "1px solid #c4c4d8")
        settings.setValue("Dark_Light/QComboBox/border-radius", "6px")

        # --- QComboBox hover/focus ---
        settings.setValue("Dark_Light/QComboBox:hover/background-color", "#dcdcf0")
        settings.setValue("Dark_Light/QComboBox:focus/background-color", "#eef0ff")

        # --- QComboBox placeholder ---
        settings.setValue("Dark_Light/QComboBox::placeholder/color", "#8888aa")

        # --- QCheckBox ---
        settings.setValue("Dark_Light/QCheckBox/color", "#1e1e2e")
        settings.setValue("Dark_Light/QCheckBox/background-color", "#f8f8ff")
        settings.setValue("Dark_Light/QCheckBox/border", "1px solid #c4c4d8")

        # --- QCheckBox checked ---
        settings.setValue("Dark_Light/QCheckBox_checked/background-color", "#4d90fe")
        settings.setValue("Dark_Light/QCheckBox_checked/border", "1px solid #4d90fe")

        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f8;
            }

            QTabWidget::pane {
                background-color: #e8e8f4;
            }

            QMenu::separator {
                height: 1px;
                background: #c4c4d8;
                margin: 3px 8px;
            }

            QTabBar::tab {
                background-color: #dcdcf0;
                color: #1e1e2e;
                padding: 5px 12px;
                border: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }

            QTabBar::tab:selected {
                background-color: #f0f0f8;
                color: #1e1e2e;
            }

            QSpinBox {
                background-color: #f8f8ff;
                color: #1e1e2e;
                border: 1px solid #c4c4d8;
                border-radius: 8px;
            }

            QGroupBox:title,
            QLabel,
            QRadioButton,
            QTextEdit {
                color: #1e1e2e;
            }

            QLineEdit {
                background-color: #f8f8ff;
                color: #1e1e2e;
                border: 1px solid #c4c4d8;
                border-radius: 6px;
                padding: 4px;
            }

            QLineEdit:focus {
                background-color: #eef0ff;
                border: 1px solid #4d90fe;
            }

            QPushButton {
                background-color: #e0e0f0;
                color: #1e1e2e;
                border: 1px solid #c4c4d8;
                border-radius: 6px;
                padding: 4px 10px;
            }

            QPushButton:hover {
                background-color: #d0d0e8;
            }

            QPushButton:pressed {
                background-color: #c0c0d8;
            }

            QPushButton:disabled {
                background-color: #eeeef8;
                color: #8888aa;
                border: 1px solid #d0d0e8;
            }

            QMenuBar {
                background-color: #e8e8f4;
                color: #1e1e2e;
            }

            QMenuBar::item {
                background: transparent;
                color: #1e1e2e;
                padding: 4px 10px;
            }

            QMenuBar::item:selected {
                background: #d0d0e8;
            }

            QMenu {
                background-color: #f0f0f8;
                color: #1e1e2e;
                border: 1px solid #c4c4d8;
            }

            QMenu::item:selected {
                background-color: #dcdcf0;
            }

            QComboBox {
                background-color: #ebebf5;
                color: #1e1e2e;
                border: 1px solid #c4c4d8;
                border-radius: 6px;
                padding-left: 8px;
            }

            QComboBox:hover {
                background-color: #dcdcf0;
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
                background-color: #f8f8ff;
                color: #1e1e2e;
                selection-background-color: #dcdcf0;
                selection-color: #1e1e2e;
                border: 1px solid #c4c4d8;
            }

            QComboBox:focus {
                background-color: #eef0ff;
            }

            QComboBox::placeholder {
                color: #8888aa;
            }
        """)

        self.is_dark_mode = True

        settings.setValue("Dark_Light/is_dark_mode", self.is_dark_mode)  
        settings.setValue("Dark_Light/text_light_dark", "Dark Mode 🌙")
    
def dark_light_config(self):

    # Load configuration for UI colors and styles
    settings = get_settings(
        "INI/dut_measurement/dark_light_config/dark_light_config.ini", 
        "shared/utils/dark_light_mode/dark_light_config.ini", 
        Path(__file__).resolve()
    )

    # QWidget
    background_color = settings.value("Dark_Light/QWidget/background-color", "#1e1e2e")

    # QTabWidget
    tabwidget_pane_bg = settings.value("Dark_Light/QTabWidget_pane/background-color", "#2e2e42")

    # QTabBar
    tabbar_bg = settings.value("Dark_Light/QTabBar/background-color", "#2a2a3e")
    tabbar_color = settings.value("Dark_Light/QTabBar/color", "white")
    tabbar_padding = settings.value("Dark_Light/QTabBar/padding", "5px 12px")
    tabbar_border = settings.value("Dark_Light/QTabBar/border", "none")
    tabbar_border_tl_radius = settings.value("Dark_Light/QTabBar/border-top-left-radius", "6px")
    tabbar_border_tr_radius = settings.value("Dark_Light/QTabBar/border-top-right-radius", "6px")

    # QTabBar selected
    tabbar_selected_bg = settings.value("Dark_Light/QTabBar_selected/background-color", "#3a3a54")
    tabbar_selected_color = settings.value("Dark_Light/QTabBar_selected/color", "white")

    # QSpinBox
    spinbox_bg = settings.value("Dark_Light/QSpinBox/background-color", "#252538")
    spinbox_color = settings.value("Dark_Light/QSpinBox/color", "white")
    spinbox_border = settings.value("Dark_Light/QSpinBox/border", "1px solid white")
    spinbox_border_radius = settings.value("Dark_Light/QSpinBox/border-radius", "8px")

    # QGroupBox
    groupbox_title_color = settings.value("Dark_Light/QGroupBox_title/color", "white")
    groupbox_border = settings.value("Dark_Light/QGroupBox/border", "1.5px solid white")
    groupbox_border_radius = settings.value("Dark_Light/QGroupBox/border-radius", "8px")
    groupbox_margin_top = settings.value("Dark_Light/QGroupBox/margin-top", "1.5ex")
    groupbox_padding = settings.value("Dark_Light/QGroupBox/padding", "8px")

    # QLabel
    label_color = settings.value("Dark_Light/QLabel/color", "white")

    # QLineEdit
    lineedit_bg = settings.value("Dark_Light/QLineEdit/background-color", "#252538")
    lineedit_color = settings.value("Dark_Light/QLineEdit/color", "white")
    lineedit_border = settings.value("Dark_Light/QLineEdit/border", "1px solid white")
    lineedit_border_radius = settings.value("Dark_Light/QLineEdit/border-radius", "6px")
    lineedit_padding = settings.value("Dark_Light/QLineEdit/padding", "4px")
    lineedit_focus_bg = settings.value("Dark_Light/QLineEdit_focus/background-color", "#454545")
    lineedit_focus_border = settings.value("Dark_Light/QLineEdit_focus/border", "1px solid #4d90fe")

    # QPushButton
    pushbutton_bg = settings.value("Dark_Light/QPushButton/background-color", "#2e2e42")
    pushbutton_color = settings.value("Dark_Light/QPushButton/color", "white")
    pushbutton_border = settings.value("Dark_Light/QPushButton/border", "1px solid white")
    pushbutton_border_radius = settings.value("Dark_Light/QPushButton/border-radius", "6px")
    pushbutton_padding = settings.value("Dark_Light/QPushButton/padding", "4px 10px")
    pushbutton_hover_bg = settings.value("Dark_Light/QPushButton_hover/background-color", "#3a3a54")
    pushbutton_pressed_bg = settings.value("Dark_Light/QPushButton_pressed/background-color", "#1a1a2e")

    # QPushButton disabled
    pushbutton_disabled_bg = settings.value("Dark_Light/QPushButton_disabled/background-color", "#1e1e2e")
    pushbutton_disabled_color = settings.value("Dark_Light/QPushButton_disabled/color", "#5a5a78")
    pushbutton_disabled_border = settings.value("Dark_Light/QPushButton_disabled/border", "1px solid #2a2a3e")

    # QMenu
    menu_bg = settings.value("Dark_Light/QMenu/background", "#2e2e42")
    menu_color = settings.value("Dark_Light/QMenu/color", "white")
    menu_border = settings.value("Dark_Light/QMenu/border", "1px solid #383850")
    menu_item_selected_bg = settings.value("Dark_Light/QMenu::item:selected/background-color", "#3a3a54")

    # QMenuBar
    menu_item_color = settings.value("Dark_Light/QMenu_item_selected/background-color", "#3a3a54")
    menubar_bg = settings.value("Dark_Light/QMenuBar/background-color", "#1e1e2e")
    menubar_color = settings.value("Dark_Light/QMenuBar/color", "white")
    menubar_item_bg = settings.value("Dark_Light/QMenuBar_item/background", "transparent")
    menubar_item_color = settings.value("Dark_Light/QMenuBar_item/color", "white")
    menubar_item_padding = settings.value("Dark_Light/QMenuBar_item/padding", "4px 10px")
    menubar_item_selected_bg = settings.value("Dark_Light/QMenuBar_item_selected/background-color", "#3a3a54")

    # QComboBox
    combobox_color = settings.value("Dark_Light/QComboBox/color", "white")
    combobox_bg = settings.value("Dark_Light/QComboBox/background-color", "#2a2a3e")
    combobox_border = settings.value("Dark_Light/QComboBox/border", "1px solid #383850")
    combobox_border_radius = settings.value("Dark_Light/QComboBox/border-radius", "6px")
    combobox_hover_bg = settings.value("Dark_Light/QComboBox:hover/background-color", "#363650")
    combobox_focus_bg = settings.value("Dark_Light/QComboBox:focus/background-color", "#363650")
    combobox_placeholder_color = settings.value("Dark_Light/QComboBox::placeholder/color", "#8888aa")

    # QCheckBox

    checkbox_color = settings.value(
        "Dark_Light/QCheckBox/color",
        label_color
    )

    checkbox_bg = settings.value(
        "Dark_Light/QCheckBox/background-color",
        lineedit_bg
    )

    checkbox_border = settings.value(
        "Dark_Light/QCheckBox/border",
        "1px solid gray"
    )

    checkbox_checked_bg = settings.value(
        "Dark_Light/QCheckBox_checked/background-color",
        "#4d90fe"
    )

    checkbox_checked_border = settings.value(
        "Dark_Light/QCheckBox_checked/border",
        "1px solid #4d90fe"
    )

    self.setStyleSheet(f"""

        /* QWidget */
        QWidget {{
            background-color: {background_color};
        }}

       /* QCheckBox */

        QCheckBox {{
            color: {checkbox_color};
            spacing: 6px;
        }}

        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
        }}

        QCheckBox::indicator:unchecked {{
            background-color: {checkbox_bg};
            border: {checkbox_border};
            border-radius: 3px;
        }}

        QCheckBox::indicator:checked {{
            background-color: {checkbox_checked_bg};
            border: {checkbox_checked_border};
            border-radius: 3px;
        }}

        QCheckBox::indicator:hover {{
            border: 1px solid #6aa2ff;
        }}

        /* QTabWidget */
        QTabWidget::pane {{
            background-color: {tabwidget_pane_bg};
        }}

        /* QTabBar */
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

        /* QSpinBox */
        QSpinBox {{
            color: black;
            background-color: white;
            border: 1px solid gray;
            border-radius: 2px;
            padding: 0px 2px;
        }}
        

        /* QDoubleSpinBox */
        QDoubleSpinBox {{
            background-color: {spinbox_bg};
            color: {spinbox_color};
            border: {spinbox_border};
            border-radius: {spinbox_border_radius};
            padding: 4px;
            min-height: 20px;
        }}

        QDoubleSpinBox:hover {{
            background-color: {spinbox_bg};
        }}

        QDoubleSpinBox:focus {{
            background-color: {spinbox_bg};
            border: {spinbox_border};
        }}

        QDoubleSpinBox::up-button {{
            background-color: {spinbox_bg};
            border: {spinbox_border};
            border-radius: 3px;
            width: 18px;
            min-height: 12px;
        }}

        QDoubleSpinBox::down-button {{
            background-color: {spinbox_bg};
            border: {spinbox_border};
            border-radius: 3px;
            width: 18px;
            min-height: 12px;
        }}

        QDoubleSpinBox::up-button:hover,
        QDoubleSpinBox::down-button:hover {{
            background-color: {pushbutton_hover_bg};
        }}

        QDoubleSpinBox::up-arrow {{
            image: none;
            border-left: 2px solid transparent;
            border-right: 2px solid transparent;
            border-bottom: 3px solid {spinbox_color};
            width: 0px;
            height: 0px;
        }}

        QDoubleSpinBox::down-arrow {{
            image: none;
            border-left: 2px solid transparent;
            border-right: 2px solid transparent;
            border-top: 3px solid {spinbox_color};
            width: 0px;
            height: 0px;
        }}

        /* QComboBox */
        QComboBox {{
            background-color: {combobox_bg};
            color: {combobox_color};
            border: {combobox_border};
            border-radius: {combobox_border_radius};
            padding: 4px 8px;
        }}

        QComboBox:hover {{
            background-color: {combobox_hover_bg};
        }}

        QComboBox:focus {{
            background-color: {combobox_focus_bg};
            border: 1px solid #4d90fe;
        }}

        QComboBox:disabled {{
            color: gray;
            background-color: #1e1e2e;
        }}

        QComboBox {{
            padding-right: 0px;
        }}

        QComboBox::drop-down {{
            border: none;
            width: 0px;
            background: transparent;
        }}

        QComboBox::down-arrow {{
            image: none;
            width: 0px;
            height: 0px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {combobox_bg};
            color: {combobox_color};
            border: {combobox_border};
            selection-background-color: {combobox_hover_bg};
            selection-color: {combobox_color};
        }}

        QComboBox::placeholder {{
            color: {combobox_placeholder_color};
        }}

        /* QGroupBox */
        QGroupBox {{
            border: {groupbox_border};
            border-radius: {groupbox_border_radius};
            margin-top: {groupbox_margin_top};
            padding: {groupbox_padding};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {groupbox_title_color};
        }}

        /* Text widgets */
        QTextEdit {{
            color: {label_color};
        }}

        QLabel {{
            color: {label_color};
        }}

        QProgressBar {{
            color: {label_color};
        }}

        QRadioButton {{
            color: {label_color};
        }}

        /* QFrame */
        QFrame {{
            border-radius: 5px;
        }}

        /* QLineEdit */
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

        /* QPushButton */
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

        QPushButton:disabled {{
            background-color: {pushbutton_disabled_bg};
            color: {pushbutton_disabled_color};
            border: {pushbutton_disabled_border};
        }}

        /* QMenuBar */
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

        /* QMenu */
        QMenu {{
            background-color: {menu_bg};
            color: {menu_color};
            border: {menu_border};
        }}

        QMenu::item:selected {{
            background-color: {menu_item_color};
        }}

        QMenu::separator {{
            height: 1px;
            background: rgba(128, 128, 128, 0.5);
            margin: 3px 8px;
        }}

        /* Lists and trees */
        QListWidget {{
            color: {label_color};
            background-color: transparent;
        }}

        QListView {{
            color: {label_color};
            background-color: transparent;
        }}

        QTreeView {{
            color: {label_color};
            background-color: transparent;
        }}
    """)