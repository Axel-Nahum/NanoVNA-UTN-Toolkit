import os
import sys
import logging

logging.basicConfig(level=logging.INFO)

from pathlib import Path

from PySide6.QtCore import QTimer, QThread, Qt, QSettings

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)


def toggle_menu_dark_mode(self, light_dark_mode):

    logging.info(f"Entressss")   

    # Load configuration for UI colors and styles
    settings = get_settings(
        "INI/dark_light_config/dark_light_config.ini", 
        "ui/utils/settings/dark_light_mode/dark_light_config.ini", 
        Path(__file__).resolve()
    )

    logging.info(f"SETTINGS: {settings.fileName()}")   

    if self.is_dark_mode:
        light_dark_mode.setText("Light Mode 🔆")

        # --- QWidget ---
        settings.setValue("Dark_Light/QWidget/background-color", "#3a3a3a")

        # --- Qframe ---
        settings.setValue("Dark_Light/Qframe/background-color", "white")
        settings.setValue("Dark_Light/Qframe/color", "white")

        # --- QTabWidget pane ---
        settings.setValue("Dark_Light/QTabWidget_pane/background-color", "#343434")

        # --- QTabBar ---
        settings.setValue("Dark_Light/QTabBar/background-color", "#2f2f2f")
        settings.setValue("Dark_Light/QTabBar/color", "white")
        settings.setValue("Dark_Light/QTabBar/padding", "5px 12px")
        settings.setValue("Dark_Light/QTabBar/border", "none")
        settings.setValue("Dark_Light/QTabBar/border-top-left-radius", "6px")
        settings.setValue("Dark_Light/QTabBar/border-top-right-radius", "6px")

        # --- QTabBar selected ---
        settings.setValue("Dark_Light/QTabBar_selected/background-color", "#4a4a4a")
        settings.setValue("Dark_Light/QTabBar_selected/color", "white")

        # --- QSpinBox ---
        settings.setValue("Dark_Light/QSpinBox/color", "white")
        settings.setValue("Dark_Light/QSpinBox/background-color", "#2e2e2e")
        settings.setValue("Dark_Light/QSpinBox/border", "1px solid #4a4a4a")
        settings.setValue("Dark_Light/QSpinBox/border-radius", "8px")

        # --- QGroupBox title ---
        settings.setValue("Dark_Light/QGroupBox_title/color", "white")

        # --- QGroupBox border ---
        settings.setValue("Dark_Light/QGroupBox/border", "1.5px solid white")

        # --- QLabel ---
        settings.setValue("Dark_Light/QLabel/color", "white")

        # --- QLineEdit ---
        settings.setValue("Dark_Light/QLineEdit/background-color", "#2e2e2e")
        settings.setValue("Dark_Light/QLineEdit/color", "white")
        settings.setValue("Dark_Light/QLineEdit/border", "1px solid #4a4a4a")
        settings.setValue("Dark_Light/QLineEdit/border-radius", "6px")
        settings.setValue("Dark_Light/QLineEdit/padding", "4px")

        # --- QLineEdit focus ---
        settings.setValue("Dark_Light/QLineEdit_focus/background-color", "#383838")
        settings.setValue("Dark_Light/QLineEdit_focus/border", "1px solid #6aa2ff")

        # --- QPushButton ---
        settings.setValue("Dark_Light/QPushButton/background-color", "#343434")
        settings.setValue("Dark_Light/QPushButton/color", "white")
        settings.setValue("Dark_Light/QPushButton/border", "1px solid #4a4a4a")
        settings.setValue("Dark_Light/QPushButton/border-radius", "6px")
        settings.setValue("Dark_Light/QPushButton/padding", "4px 10px")

        # --- QPushButton hover/pressed ---
        settings.setValue("Dark_Light/QPushButton_hover/background-color", "#3f3f3f")
        settings.setValue("Dark_Light/QPushButton_pressed/background-color", "#2a2a2a")

        # --- QPushButton disabled ---
        settings.setValue("Dark_Light/QPushButton_disabled/background-color", "#242424")
        settings.setValue("Dark_Light/QPushButton_disabled/color", "#777777")
        settings.setValue("Dark_Light/QPushButton_disabled/border", "1px solid #333333")

        # --- QMenu ---
        settings.setValue("Dark_Light/QMenu/background", "#3a3a3a")
        settings.setValue("Dark_Light/QMenu/color", "white")
        settings.setValue("Dark_Light/QMenu/border", "1px solid #4a4a4a")

        # --- QMenuBar ---
        settings.setValue("Dark_Light/QMenuBar/background-color", "#3a3a3a")
        settings.setValue("Dark_Light/QMenuBar/color", "white")

        # --- QMenuBar items ---
        settings.setValue("Dark_Light/QMenuBar_item/background", "transparent")
        settings.setValue("Dark_Light/QMenuBar_item/color", "white")
        settings.setValue("Dark_Light/QMenuBar_item/padding", "4px 10px")

        # --- QMenuBar selected item ---
        settings.setValue("Dark_Light/QMenuBar_item_selected/background-color", "#4a4a4a")

        # --- QMenu selected item ---
        settings.setValue("Dark_Light/QMenu_item_selected/background-color", "#4a4a4a")

        # --- QComboBox ---
        settings.setValue("Dark_Light/QComboBox/color", "white")
        settings.setValue("Dark_Light/QComboBox/background-color", "#3b3b3b")
        settings.setValue("Dark_Light/QComboBox/border", "2px solid white")
        settings.setValue("Dark_Light/QComboBox/border-radius", "6px")

        # --- QComboBox hover/focus ---
        settings.setValue("Dark_Light/QComboBox:hover/background-color", "#4d4d4d")
        settings.setValue("Dark_Light/QComboBox:focus/background-color", "#4d4d4d")

        # --- QComboBox placeholder ---
        settings.setValue("Dark_Light/QComboBox::placeholder/color", "#cccccc")

        self.setStyleSheet("""
            QWidget {
                background-color: #3a3a3a;
            }

            QTabWidget::pane {
                background-color: #343434;
            }

            QMenu::separator {
                height: 0.5px;           
                background: white;   
                margin: 4px 0px;      
            }

            QTabBar::tab {
                background-color: #2f2f2f;
                color: white;
                padding: 5px 12px;
                border: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }

            QTabBar::tab:selected {
                background-color: #4a4a4a;
                color: white;
            }

            QSpinBox {
                background-color: #2e2e2e;
                color: white;
                border: 1px solid #4a4a4a;
                border-radius: 8px;
            }

            QGroupBox:title,
            QLabel,
            QRadioButton,
            QTextEdit {
                color: white;
            }

            QLineEdit {
                background-color: #2e2e2e;
                color: white;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 4px;
            }

            QLineEdit:focus {
                background-color: #383838;
                border: 1px solid #6aa2ff;
            }

            QPushButton {
                background-color: #343434;
                color: white;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 4px 10px;
            }

            QPushButton:hover {
                background-color: #3f3f3f;
            }

            QPushButton:pressed {
                background-color: #2a2a2a;
            }

            QPushButton:disabled {
                background-color: #242424;
                color: #777777;
                border: 1px solid #333333;
            }

            QMenuBar {
                background-color: #3a3a3a;
                color: white;
            }

            QMenuBar::item {
                background: transparent;
                color: white;
                padding: 4px 10px;
            }

            QMenuBar::item:selected {
                background: #4a4a4a;
            }

            QMenu {
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #4a4a4a;
            }

            QMenu::item:selected {
                background-color: #4a4a4a;
            }

            QComboBox {
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 200px;
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

            QComboBox:focus {
                background-color: #4d4d4d;
            }

            QComboBox::placeholder {
                color: #cccccc;
            }
        """)
        self.is_dark_mode = False

        settings.setValue("Dark_Light/is_dark_mode", self.is_dark_mode)
        settings.setValue("Dark_Light/text_light_dark", "Light Mode 🔆")

    else:
        light_dark_mode.setText("Dark Mode 🌙")

        # --- QWidget ---
        settings.setValue("Dark_Light/QWidget/background-color", "#f0f0f0")

        # --- Qframe ---
        settings.setValue("Dark_Light/Qframe/background-color", "black")
        settings.setValue("Dark_Light/Qframe/color", "black")

        # --- QTabWidget pane ---
        settings.setValue("Dark_Light/QTabWidget_pane/background-color", "#e0e0e0")

        # --- QTabBar ---
        settings.setValue("Dark_Light/QTabBar/background-color", "#c8c8c8")
        settings.setValue("Dark_Light/QTabBar/color", "black")
        settings.setValue("Dark_Light/QTabBar/padding", "5px 12px")
        settings.setValue("Dark_Light/QTabBar/border", "none")
        settings.setValue("Dark_Light/QTabBar/border-top-left-radius", "6px")
        settings.setValue("Dark_Light/QTabBar/border-top-right-radius", "6px")

        # --- QTabBar selected ---
        settings.setValue("Dark_Light/QTabBar_selected/background-color", "#dcdcdc")
        settings.setValue("Dark_Light/QTabBar/color", "black")

        # --- QTabBar alternate background ---
        settings.setValue("Dark_Light/QTabBar/background-color", "#e0e0e0")

        # --- QSpinBox ---
        settings.setValue("Dark_Light/QSpinBox/background-color", "white")
        settings.setValue("Dark_Light/QSpinBox/color", "black")
        settings.setValue("Dark_Light/QSpinBox/border", "1px solid #b0b0b0")
        settings.setValue("Dark_Light/QSpinBox/border-radius", "8px")

        # --- QGroupBox title ---
        settings.setValue("Dark_Light/QGroupBox_title/color", "black")
        
        # --- QGroupBox border ---
        settings.setValue("Dark_Light/QGroupBox/border", "1.5px solid #b0b0b0")

        # --- QLabel ---
        settings.setValue("Dark_Light/QLabel/color", "black")

        # --- QLineEdit ---
        settings.setValue("Dark_Light/QLineEdit/background-color", "#ffffff")
        settings.setValue("Dark_Light/QLineEdit/color", "black")
        settings.setValue("Dark_Light/QLineEdit/border", "1px solid #b0b0b0")
        settings.setValue("Dark_Light/QLineEdit/border-radius", "6px")
        settings.setValue("Dark_Light/QLineEdit/padding", "4px")

        # --- QLineEdit focus ---
        settings.setValue("Dark_Light/QLineEdit_focus/background-color", "#f0f8ff")
        settings.setValue("Dark_Light/QLineEdit_focus/border", "1px solid #4d90fe")

        # --- QPushButton ---
        settings.setValue("Dark_Light/QPushButton/background-color", "#e0e0e0")
        settings.setValue("Dark_Light/QPushButton/color", "black")
        settings.setValue("Dark_Light/QPushButton/border", "1px solid #b0b0b0")
        settings.setValue("Dark_Light/QPushButton/border-radius", "6px")
        settings.setValue("Dark_Light/QPushButton/padding", "4px 10px")

        # --- QPushButton hover/pressed ---
        settings.setValue("Dark_Light/QPushButton_hover/background-color", "#d0d0d0")
        settings.setValue("Dark_Light/QPushButton_pressed/background-color", "#c0c0c0")

        # --- QPushButton disabled ---
        settings.setValue("Dark_Light/QPushButton_disabled/background-color", "#f5f5f5")
        settings.setValue("Dark_Light/QPushButton_disabled/color", "#a0a0a0")
        settings.setValue("Dark_Light/QPushButton_disabled/border", "1px solid #d0d0d0")

        # --- QMenu ---
        settings.setValue("Dark_Light/QMenu/background", "#f0f0f0")
        settings.setValue("Dark_Light/QMenu/color", "black")
        settings.setValue("Dark_Light/QMenu/border", "1px solid #b0b0b0")

        # --- QMenuBar ---
        settings.setValue("Dark_Light/QMenuBar/background-color", "#f0f0f0")
        settings.setValue("Dark_Light/QMenuBar/color", "black")

        # --- QMenuBar items ---
        settings.setValue("Dark_Light/QMenuBar_item/background", "transparent")
        settings.setValue("Dark_Light/QMenuBar_item/color", "black")
        settings.setValue("Dark_Light/QMenuBar_item/padding", "4px 10px")

        # --- QMenuBar selected item ---
        settings.setValue("Dark_Light/QMenuBar_item_selected/background-color", "#dcdcdc")

        # --- QMenu selected item ---
        settings.setValue("Dark_Light/QMenu_item_selected/background-color", "#dcdcdc")

        # --- QComboBox ---
        settings.setValue("Dark_Light/QComboBox/color", "black")
        settings.setValue("Dark_Light/QComboBox/background-color", "white")
        settings.setValue("Dark_Light/QComboBox/border", "2px solid black")
        settings.setValue("Dark_Light/QComboBox/border-radius", "6px")

        # --- QComboBox hover/focus ---
        settings.setValue("Dark_Light/QComboBox:hover/background-color", "#a3a1a1")
        settings.setValue("Dark_Light/QComboBox:focus/background-color", "#a3a1a1")

        # --- QComboBox placeholder ---
        settings.setValue("Dark_Light/QComboBox::placeholder/color", "#cccccc")

        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
            }
            QMenu::separator {
                height: 0.5px;           
                background: black;   
                margin: 4px 0px;      
            }
            QTabWidget::pane {
                background-color: #e0e0e0; 
            }
            QTabBar::tab {
                background-color: #dcdcdc;  
                color: black;             
                padding: 5px 12px;
                border: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #c8c8c8;  
                color: black;
            }
            QRadioButton {
                color: black;
            }
            QSpinBox {
                background-color: white;
                color: black;
                border: 1px solid #b0b0b0;
                border-radius: 8px;
            }
            QGroupBox:title {
                color: black; 
            }
            QLabel {
                color: black;
            }
            QTextEdit {
                color: black;
            }
            QLineEdit {
                background-color: #ffffff;
                color: black;
                border: 1px solid #b0b0b0;
                border-radius: 6px;
                padding: 4px;
            }
            QLineEdit:focus {
                background-color: #f0f8ff;
                border: 1px solid #4d90fe;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: black;
                border: 1px solid #b0b0b0;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QMenuBar {
                background-color: #f0f0f0;
                color: black;
            }
            QMenuBar::item {
                background: transparent;
                color: black;
                padding: 4px 10px;
            }
            QMenuBar::item:selected {
                background: #dcdcdc;
            }
            QMenu {
                background-color: #f0f0f0;
                color: black;
                border: 1px solid #b0b0b0;
            }
            QMenu::item:selected {
                background-color: #dcdcdc;
            }
            QComboBox {{
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 200px;            
            }}
            QComboBox:hover {{
                background-color: #4d4d4d;
            }}
            QComboBox::drop-down {{
                width: 0px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #3b3b3b;
                color: white;             
                selection-background-color: #4d4d4d; 
                selection-color: white;
                border: 1px solid white;
            }}
            QComboBox:focus {{
                background-color: #4d4d4d;
            }}
            QComboBox::placeholder {{
                color: #cccccc;
            }}
        """)

        self.is_dark_mode = True

        settings.setValue("Dark_Light/is_dark_mode", self.is_dark_mode)  
        settings.setValue("Dark_Light/text_light_dark", "Dark Mode 🌙")
    
def dark_light_config(self):

    # Load configuration for UI colors and styles
    settings = get_settings(
        "INI/dark_light_config/dark_light_config.ini",
        "ui/utils/settings/dark_light_mode/dark_light_config.ini",
        Path(__file__).resolve()
    )

    # QWidget
    background_color = settings.value("Dark_Light/QWidget/background-color", "#3a3a3a")

    # QTabWidget
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
    tabbar_selected_color = settings.value("Dark_Light/QTabBar_selected/color", "white")

    # QSpinBox
    spinbox_bg = settings.value("Dark_Light/QSpinBox/background-color", "#3b3b3b")
    spinbox_color = settings.value("Dark_Light/QSpinBox/color", "white")
    spinbox_border = settings.value("Dark_Light/QSpinBox/border", "1px solid white")
    spinbox_border_radius = settings.value("Dark_Light/QSpinBox/border-radius", "8px")

    # QGroupBox
    groupbox_title_color = settings.value("Dark_Light/QGroupBox_title/color", "white")
    groupbox_border = settings.value("Dark_Light/QGroupBox/border", "1.5px solid white")

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

    # QPushButton disabled
    pushbutton_disabled_bg = settings.value("Dark_Light/QPushButton_disabled/background-color", "#242424")
    pushbutton_disabled_color = settings.value("Dark_Light/QPushButton_disabled/color", "#777777")
    pushbutton_disabled_border = settings.value("Dark_Light/QPushButton_disabled/border", "1px solid #333333")

    # QMenu
    menu_bg = settings.value("Dark_Light/QMenu/background", "#3a3a3a")
    menu_color = settings.value("Dark_Light/QMenu/color", "white")
    menu_border = settings.value("Dark_Light/QMenu/border", "1px solid #3b3b3b")
    menu_item_selected_bg = settings.value("Dark_Light/QMenu::item:selected/background-color", "#4d4d4d")

    # QMenuBar
    menu_item_color = settings.value("Dark_Light/QMenu_item_selected/background-color", "#4d4d4d")
    menubar_bg = settings.value("Dark_Light/QMenuBar/background-color", "#3a3a3a")
    menubar_color = settings.value("Dark_Light/QMenuBar/color", "white")
    menubar_item_bg = settings.value("Dark_Light/QMenuBar_item/background", "transparent")
    menubar_item_color = settings.value("Dark_Light/QMenuBar_item/color", "white")
    menubar_item_padding = settings.value("Dark_Light/QMenuBar_item/padding", "4px 10px")
    menubar_item_selected_bg = settings.value("Dark_Light/QMenuBar_item_selected/background-color", "#4d4d4d")

    # QComboBox
    combobox_color = settings.value("Dark_Light/QComboBox/color", "white")
    combobox_bg = settings.value("Dark_Light/QComboBox/background-color", "#3b3b3b")
    combobox_border = settings.value("Dark_Light/QComboBox/border", "2px solid white")
    combobox_border_radius = settings.value("Dark_Light/QComboBox/border-radius", "6px")
    combobox_hover_bg = settings.value("Dark_Light/QComboBox:hover/background-color", "#4d4d4d")
    combobox_focus_bg = settings.value("Dark_Light/QComboBox:focus/background-color", "#4d4d4d")
    combobox_placeholder_color = settings.value("Dark_Light/QComboBox::placeholder/color", "#cccccc")

    self.setStyleSheet(f"""

        /* QWidget */
        QWidget {{
            background-color: {background_color};
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
            min-height: 20px;
            min-width: 60px;
        }}

        QComboBox:hover {{
            background-color: {combobox_hover_bg};
        }}

        QComboBox:focus {{
            background-color: {combobox_focus_bg};
            border: 1px solid #4d90fe;
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
        QGroupBox:title {{
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