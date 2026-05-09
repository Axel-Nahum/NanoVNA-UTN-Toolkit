import os
import sys
from PySide6.QtCore import QTimer, QThread, Qt, QSettings

def toggle_menu_dark_mode(self, light_dark_mode):
    # Load configuration for UI colors and styles
    if getattr(sys, 'frozen', False):
        appdata = os.getenv("APPDATA")
        ruta_colors = os.path.join(
            appdata,
            "NanoVNA-UTN-Toolkit",
            "INI",
            "colors_config",
            "config.ini"
        )
        ruta_colors = os.path.normpath(ruta_colors)
    else:
        ui_dir = os.path.dirname(os.path.dirname(__file__))
        ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

    settings = QSettings(ruta_colors, QSettings.IniFormat)

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