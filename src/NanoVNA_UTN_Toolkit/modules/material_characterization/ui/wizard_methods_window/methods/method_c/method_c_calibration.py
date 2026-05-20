import logging

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel
)

def build_method_c_calibration(self):

    from PySide6.QtWidgets import QLabel

    label = QLabel(
        "Calibration Wizard - Method C"
    )

    label.setStyleSheet("""
        font-size: 24px;
        font-weight: bold;
    """)

    self.content_layout.addWidget(label)