from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QButtonGroup, QRadioButton

def show_touchstone_format_dialog(self):
    """
    Show a simple dialog to choose between S1P and S2P export formats.

    Returns:
        str: "s1p" or "s2p" if user selects, None if cancelled
    """

    dialog = QDialog(self)
    dialog.setWindowTitle("Select Touchstone Format")
    dialog.setFixedSize(350, 200)
    dialog.setModal(True)

    # Main layout
    layout = QVBoxLayout(dialog)
    layout.setSpacing(15)
    layout.setContentsMargins(20, 20, 20, 20)

    # Title label
    title_label = QLabel("Choose Touchstone export format:")
    title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
    layout.addWidget(title_label)

    # Radio button group
    button_group = QButtonGroup(dialog)

    # S1P option
    s1p_radio = QRadioButton("S1P Format - Single Port (S11 only)")
    s1p_radio.setChecked(True)  # Default selection
    button_group.addButton(s1p_radio, 1)
    layout.addWidget(s1p_radio)

    # S2P option  
    s2p_radio = QRadioButton("S2P Format - Two Port (S11 and S21)")
    button_group.addButton(s2p_radio, 2)
    layout.addWidget(s2p_radio)

    # Info label
    info_label = QLabel("S1P files contain only S11 reflection data.\nS2P files contain both S11 and S21 transmission data.")
    info_label.setStyleSheet("font-size: 11px; color: #D0D0D0;")
    info_label.setWordWrap(True)
    layout.addWidget(info_label)

    # Button layout
    button_layout = QHBoxLayout()
    button_layout.addStretch()

    # Cancel button
    cancel_button = QPushButton("Cancel")
    cancel_button.setMinimumWidth(80)
    cancel_button.clicked.connect(dialog.reject)
    button_layout.addWidget(cancel_button)

    # Export button
    export_button = QPushButton("Export")
    export_button.setMinimumWidth(80)
    export_button.setDefault(True)
    export_button.clicked.connect(dialog.accept)
    button_layout.addWidget(export_button)

    layout.addStretch()
    layout.addLayout(button_layout)

    # Show dialog and get result
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted:
        if s1p_radio.isChecked():
            return "s1p"
        else:
            return "s2p"
    else:
        return None