"""
Introduction screen builder.
"""

import logging
import sys

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QLabel, QVBoxLayout, QComboBox, 
    QTextEdit, QWidget
)

# ------------------------------------------------------------------------------------------------------------------- #

def build_introduction_screen(self):

    self.title_label.setText("Characterization Methods")

    self.next_button.setEnabled(False)

    self.clear_content()

# ------------------------------------------------------------------------------------------------------------------- #
    # Main layout
# ------------------------------------------------------------------------------------------------------------------- #

    top_container = QVBoxLayout()
    top_container.setSpacing(15)
    top_container.setContentsMargins(0, 0, 0, 0)

# ------------------------------------------------------------------------------------------------------------------- #
    # Method label
# ------------------------------------------------------------------------------------------------------------------- #

    method_label = QLabel(
        "Select Characterization Method:"
    )

    method_label.setStyleSheet("""
        font-size: 16px;
        font-weight: bold;
    """)

    top_container.addWidget(method_label)

# ------------------------------------------------------------------------------------------------------------------- #
    # Dropdown
# ------------------------------------------------------------------------------------------------------------------- #

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
    """)

    self.method_dropdown.addItem(
        "Select Characterization Method"
    )

    item = self.method_dropdown.model().item(0)

    item.setEnabled(False)

    item.setForeground(QColor(120, 120, 120))

    methods = [
        "Method A",
        "Method B",
        "Method C"
    ]

    self.method_dropdown.addItems(methods)

    top_container.addWidget(self.method_dropdown)

# ------------------------------------------------------------------------------------------------------------------- #
    # Description title
# ------------------------------------------------------------------------------------------------------------------- #

    description_title = QLabel("Method Description")

    description_title.setStyleSheet("""
        font-size: 15px;
        font-weight: bold;
        margin-top: 10px;
    """)

    top_container.addWidget(description_title)

# ------------------------------------------------------------------------------------------------------------------- #
    # Description box
# ------------------------------------------------------------------------------------------------------------------- #

    self.method_info = QTextEdit()

    self.method_info.setReadOnly(True)

    self.method_info.setMinimumHeight(350)

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

# ------------------------------------------------------------------------------------------------------------------- #
    # Descriptions
# ------------------------------------------------------------------------------------------------------------------- #

    def resource_path(relative_path):

        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)

        else:
            base_path = Path(__file__).resolve().parents[6] / "NanoVNA_UTN_Toolkit"

        return base_path / relative_path


    def load_method_descriptions():

        path = resource_path(
            "modules/material_characterization/ui/wizard_methods_window/steps/method_descriptions.json"
        )

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

# ------------------------------------------------------------------------------------------------------------------- #
    # Callback
# ------------------------------------------------------------------------------------------------------------------- #

    def on_method_changed(index):

        if index == 0:
            self.selected_method = None
            self.method_info.setText("")
            self.next_button.setEnabled(False)
            return

        selected_text = self.method_dropdown.itemText(index)
        self.selected_method = selected_text

        self.next_button.setEnabled(True)

        logging.info(
            f"[CharacterizationWizard] Selected method: {selected_text}"
        )

        description = method_descriptions.get(selected_text, "")
        self.method_info.setText(description)

    method_descriptions = load_method_descriptions()

    self.method_dropdown.activated.connect(
        on_method_changed
    )

# ------------------------------------------------------------------------------------------------------------------- #

    container = QWidget()
    container.setLayout(top_container)

    self.content_layout.addWidget(container, alignment=Qt.AlignTop)
