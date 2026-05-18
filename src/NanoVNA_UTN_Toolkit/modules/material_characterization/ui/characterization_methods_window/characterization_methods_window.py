import logging
import sys
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QTextEdit
)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------- #

class CharacterizationWizard(QMainWindow):

    def __init__(self, vna_device=None):
        super().__init__()

        self.vna = vna_device

        self.setWindowTitle("NanoVNA UTN Toolkit - Characterization Wizard")
        self.setGeometry(200, 200, 950, 620)

# ------------------------------------------------------------------------------------------------------------------------------------------ #

        # Dark-Light mode settings

        dark_light_config(self)

# ------------------------------------------------------------------------------------------------------------------------------------------ #

        # === Store VNA device reference ===

        self.vna_device = vna_device

        logging.info(
            "[material_characterization_welcome.__init__] Initializing material characterization welcome window"
        )

        # =========================
        # Window icon
        # =========================

        if getattr(sys, 'frozen', False):

            # ---- EXE MODE ----

            base_path = sys._MEIPASS

            icon_path = os.path.join(base_path, 'icon.ico')

            if os.path.exists(icon_path):

                self.setWindowIcon(QIcon(icon_path))

            else:

                logging.getLogger(__name__).warning(
                    f"icon.ico not found in exe: {icon_path}"
                )

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

                logging.getLogger(__name__).warning(
                    "icon.ico not found in dev mode"
                )

        # =========================
        # Central widget
        # =========================

        self.central_widget = QWidget()

        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # =========================
        # Top header
        # =========================

        self.header_layout = QHBoxLayout()

        self.title_label = QLabel("Characterization Methods")
        self.title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
        """)

        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()

        self.back_button = QPushButton("Back")
        self.back_button.setFixedSize(120, 35)
        self.back_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
            }
        """)

        self.back_button.clicked.connect(
            lambda: self.return_to_previous_window()
        )

        self.header_layout.addWidget(self.back_button)

        self.main_layout.addLayout(self.header_layout)

        # =========================
        # Content layout
        # =========================

        self.content_layout = QVBoxLayout()

        self.main_layout.addLayout(self.content_layout)

        # =========================
        # Internal state
        # =========================

        self.selected_method = None

        self.current_step = 0

        # =========================
        # Show first screen
        # =========================

        self.show_first_screen()

# ------------------------------------------------------------------------------------------------------------------- #

    def clear_content(self):

        while self.content_layout.count():

            item = self.content_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:

                widget.deleteLater()

            elif item.layout() is not None:

                self.clear_layout(item.layout())

# ------------------------------------------------------------------------------------------------------------------- #

    def clear_layout(self, layout):

        while layout.count():

            item = layout.takeAt(0)

            widget = item.widget()

            if widget is not None:

                widget.deleteLater()

            elif item.layout() is not None:

                self.clear_layout(item.layout())

# ------------------------------------------------------------------------------------------------------------------- #

    def return_to_previous_window(self):

        """
        Back button callback.
        Add your navigation logic here.
        """

        logging.info(
            "[CharacterizationWizard.return_to_previous_window] Returning to previous window"
        )

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

# ------------------------------------------------------------------------------------------------------------------- #

    def show_first_screen(self):

        """
        Initial screen:
        Characterization method selector + dynamic information.
        """

        self.clear_content()

        # =========================
        # Reset state
        # =========================

        self.selected_method = None

        # =========================
        # Main container
        # =========================

        top_container = QVBoxLayout()

        top_container.setAlignment(Qt.AlignTop)

        top_container.setSpacing(15)

        # =========================
        # Label
        # =========================

        method_label = QLabel("Select Characterization Method:")

        method_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
        """)

        top_container.addWidget(method_label)

        # =========================
        # Dropdown
        # =========================

        self.method_dropdown = QComboBox()

        self.method_dropdown.setEditable(False)

        self.method_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 380px;
                max-width: 450px;
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

        # =========================
        # Placeholder
        # =========================

        self.method_dropdown.addItem(
            "Select Characterization Method"
        )

        item = self.method_dropdown.model().item(0)

        item.setEnabled(False)

        placeholder_color = QColor(120, 120, 120)

        item.setForeground(placeholder_color)

        # =========================
        # Methods
        # =========================

        methods = [
            "Method A",
            "Method B",
            "Method C"
        ]

        self.method_dropdown.addItems(methods)

        top_container.addWidget(self.method_dropdown)

        # =========================
        # Description title
        # =========================

        description_title = QLabel("Method Description")

        description_title.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-top: 10px;
        """)

        top_container.addWidget(description_title)

        # =========================
        # Description box
        # =========================

        self.method_info = QTextEdit()

        self.method_info.setReadOnly(True)

        self.method_info.setMinimumHeight(260)

        self.method_info.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #dddddd;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
        """)

        self.method_info.setText(
            "Select a characterization method to display information."
        )

        top_container.addWidget(self.method_info)

        # =========================
        # Method descriptions
        # =========================

        method_descriptions = {

            "Method A": (

                "Method A is optimized for fast broadband "
                "characterization of passive RF devices.\n\n"

                "This workflow prioritizes acquisition speed while "
                "maintaining stable amplitude tracking across the "
                "entire frequency range.\n\n"

                "Typical applications include rapid verification "
                "of filters, attenuators, and matching networks."
            ),

            "Method B": (

                "Method B focuses on enhanced phase stability and "
                "long-term repeatability.\n\n"

                "The method applies adaptive correction algorithms "
                "to reduce drift and connector mismatch effects "
                "during extended measurement sessions.\n\n"

                "This approach is recommended for precision "
                "laboratory analysis and validation tasks."
            ),

            "Method C": (

                "Method C is an advanced characterization technique "
                "designed for complex multi-frequency analysis.\n\n"

                "It combines dynamic response compensation with "
                "frequency-dependent error correction models to "
                "improve overall measurement accuracy.\n\n"

                "This method is intended for high accuracy DUT "
                "evaluation and detailed network response analysis."
            )
        }

        # =========================
        # Dropdown callback
        # =========================

        def on_method_changed(index):

            if index == 0:

                self.selected_method = None

                self.method_info.setText(
                    "Select a characterization method to display information."
                )

                return

            selected_text = self.method_dropdown.itemText(index)

            self.selected_method = selected_text

            logging.info(
                f"[CharacterizationWizard] Selected method: {selected_text}"
            )

            self.method_info.setText(
                method_descriptions.get(
                    selected_text,
                    "No information available."
                )
            )

        self.method_dropdown.activated.connect(on_method_changed)

        # =========================
        # Add layout
        # =========================

        self.content_layout.addLayout(top_container)

        self.current_step = 0

# ------------------------------------------------------------------------------------------------------------------- #

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = CharacterizationWizard()

    window.show()

    sys.exit(app.exec())