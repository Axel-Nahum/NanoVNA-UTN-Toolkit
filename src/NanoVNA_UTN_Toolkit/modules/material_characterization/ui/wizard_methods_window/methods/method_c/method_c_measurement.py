import logging

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel
)

def build_method_c_measurement(self):

    from PySide6.QtWidgets import QLabel

    label = QLabel(
        "Measurement Window - Method C"
    )

    label.setStyleSheet("""
        font-size: 24px;
        font-weight: bold;
    """)

    self.content_layout.addWidget(label)