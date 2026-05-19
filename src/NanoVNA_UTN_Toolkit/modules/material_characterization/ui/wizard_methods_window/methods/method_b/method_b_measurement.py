import logging

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel
)

def build_method_b_measurement(self):

    from PySide6.QtWidgets import QLabel

    label = QLabel(
        "Measurement Window - Method B"
    )

    label.setStyleSheet("""
        font-size: 24px;
        font-weight: bold;
    """)

    self.content_layout.addWidget(label)