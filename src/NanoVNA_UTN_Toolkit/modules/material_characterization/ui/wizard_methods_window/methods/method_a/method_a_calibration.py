import logging

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel
)

def build_method_a_calibration(window):

    from PySide6.QtWidgets import QLabel

    label = QLabel(
        "Calibration Wizard - Method A"
    )

    label.setStyleSheet("""
        font-size: 24px;
        font-weight: bold;
    """)

    window.content_layout.addWidget(label)