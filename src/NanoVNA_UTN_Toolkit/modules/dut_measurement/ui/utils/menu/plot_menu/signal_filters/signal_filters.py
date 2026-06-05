from pathlib import Path
from NanoVNA_UTN_Toolkit.utils import safe_import

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QComboBox, QStyledItemDelegate,
    QLineEdit, QFrame, QGridLayout, QSizePolicy, QMessageBox,
    QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils",
    "get_settings"
)

ComplexKalman = safe_import("NanoVNA_UTN_Toolkit.shared.utils.real_time.kalman_filter.kalman_filter", "ComplexKalman")

KALMAN_PRESETS = {
    "Light":  {"Q": 0.1,   "R": 0.01},
    "Medium": {"Q": 0.01,  "R": 0.1},
    "Strong": {"Q": 0.001, "R": 1.0},
}


class CenterDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter


def open_signal_filters(self):

    settings_dark = get_settings(
        "INI/dut_measurement/dark_light_config/dark_light_config.ini",
        "shared/utils/dark_light_mode/dark_light_config.ini",
        Path(__file__).resolve()
    )

    border = settings_dark.value("Dark_Light/QGroupBox/color", "1px solid #999")

    frame_style = f"""
        QFrame {{
            border: {border};
            border-radius: 8px;
            padding: 12px;
        }}
    """

    self.sf_dialog = QDialog(self)
    self.sf_dialog.setWindowTitle(f"{self.signal_filters_title}")
    self.sf_dialog.setFixedSize(420, 380)
    self.sf_dialog.setStyleSheet(self.styleSheet())
    self.sf_dialog.setWindowFlags(
        Qt.WindowType.Dialog |
        Qt.WindowType.MSWindowsFixedSizeDialogHint
    )

    self.sf_settings = get_settings(
        "INI/dut_measurement/signal_filters/signal_filters.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/signal_filters/signal_filters.ini",
        Path(__file__).resolve()
    )

    main = QVBoxLayout(self.sf_dialog)
    main.setContentsMargins(15, 15, 15, 15)

    frame = QFrame()
    frame.setStyleSheet(frame_style)

    layout = QVBoxLayout(frame)
    layout.setSpacing(10)

    # =====================================================
    # TITLE
    # =====================================================

    title = QLabel(f"{self.signal_filters_title}")
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet("font-size: 22px; font-weight: bold; border: none;")
    layout.addWidget(title)

    layout.addSpacing(6)

    # =====================================================
    # KALMAN CONTROLS
    # =====================================================

    # ENABLED

    self.sf_dialog.kalman_check = QCheckBox()

    kalman_enabled = self.sf_settings.value(
        "kalman/enabled",
        "false",
        type=bool
    )

    self.sf_dialog.kalman_check.setChecked(kalman_enabled)

    # PRESET
    self.sf_dialog.kalman_combo = QComboBox()
    self.sf_dialog.kalman_combo.setItemDelegate(CenterDelegate())
    self.sf_dialog.kalman_combo.setFixedWidth(120)

    self.sf_dialog.kalman_check.setFixedHeight(
        self.sf_dialog.kalman_combo.sizeHint().height()
    )

    self.sf_dialog.kalman_combo.addItems(list(KALMAN_PRESETS.keys()))

    self.sf_dialog.kalman_combo.currentTextChanged.connect(
        lambda _: (
            handle_kalman_combo_change(self),
            update_kalman_info(self)
        )
    )

    saved_preset = self.sf_settings.value(
        "kalman/preset",
        "Medium"
    )

    if saved_preset == "Custom":
        self.sf_dialog.kalman_combo.addItem("Custom")

    idx = self.sf_dialog.kalman_combo.findText(saved_preset)

    if idx >= 0:
        self.sf_dialog.kalman_combo.setCurrentIndex(idx)

    self.sf_dialog.kalman_combo.setEnabled(kalman_enabled)

    self.sf_dialog.kalman_check.toggled.connect(
        lambda _: (
            update_kalman_ui(self),
            update_kalman_info(self)
        )
    )

    enabled_label = QLabel(f"{self.kalman_filter_title}")
    enabled_label.setStyleSheet(
        "font-weight: bold; font-size: 15px; border: none;"
    )

    preset_label = QLabel(f"{self.kalman_preset_label}")
    preset_label.setStyleSheet(
        "font-weight: bold; font-size: 15px; border: none;"
    )

    kalman_grid = QGridLayout()
    kalman_grid.setColumnStretch(0, 2)
    kalman_grid.setColumnStretch(1, 1)

    kalman_grid.addWidget(
        enabled_label,
        0,
        0,
        alignment=Qt.AlignLeft
    )

    check_widget = QWidget()
    check_widget.setFixedWidth(120)

    check_layout = QHBoxLayout(check_widget)
    check_layout.setContentsMargins(0, 0, 0, 0)
    check_layout.addStretch()
    check_layout.addWidget(self.sf_dialog.kalman_check)
    check_layout.addStretch()

    kalman_grid.addWidget(
        check_widget,
        0,
        1,
        alignment=Qt.AlignCenter
    )

    kalman_grid.addWidget(
        preset_label,
        1,
        0,
        alignment=Qt.AlignLeft
    )

    kalman_grid.addWidget(
        self.sf_dialog.kalman_combo,
        1,
        1,
        alignment=Qt.AlignCenter
    )
    
    layout.addLayout(kalman_grid)

    # ADVANCED
    self.sf_dialog.kalman_adv_btn = QPushButton(f"{self.kalman_advanced_title}")
    self.sf_dialog.kalman_adv_btn.setFlat(True)
    self.sf_dialog.kalman_adv_btn.setStyleSheet("""
        QPushButton {
            border: none;
            background: transparent;
            color: white;
            font-size: 12px;
        }
        QPushButton:hover {
            text-decoration: underline;
        }
        QPushButton:disabled {
            color: gray;
        }
    """)
    self.sf_dialog.kalman_adv_btn.setCursor(Qt.PointingHandCursor)
    self.sf_dialog.kalman_adv_btn.clicked.connect(lambda: open_kalman_advanced(self))

    layout.addSpacing(15) 

    adv_layout = QHBoxLayout()
    adv_layout.addStretch()
    adv_layout.addWidget(self.sf_dialog.kalman_adv_btn)
    adv_layout.addStretch()
    layout.addLayout(adv_layout)

    self.sf_dialog.kalman_info = QLabel()
    self.sf_dialog.kalman_info.setAlignment(Qt.AlignCenter)
    self.sf_dialog.kalman_info.setStyleSheet("""
        QLabel {
            border: none;
            font-size: 11px;
            color: gray;
        }
    """)

    layout.addWidget(self.sf_dialog.kalman_info)

    update_kalman_ui(self)
    update_kalman_info(self)

    layout.addSpacing(10)

    # =====================================================
    # ACTIONS
    # =====================================================

    actions = QHBoxLayout()

    apply_btn = QPushButton(f"{self.kalman_advanced_apply_button_label}")
    cancel_btn = QPushButton(f"{self.kalman_advanced_cancel_button_label}")

    apply_btn.setMinimumSize(100, 30)
    cancel_btn.setMinimumSize(100, 30)

    apply_btn.clicked.connect(lambda: apply_signal_filters(self))
    cancel_btn.clicked.connect(self.sf_dialog.reject)

    actions.addStretch()
    actions.addWidget(apply_btn)
    actions.addSpacing(15)
    actions.addWidget(cancel_btn)
    actions.addStretch()

    layout.addLayout(actions)

    main.addWidget(frame)

    self.sf_dialog.exec()


# =========================================================
# KALMAN ADVANCED DIALOG
# =========================================================

def open_kalman_advanced(self):

    adv = QDialog(self.sf_dialog)
    adv.setWindowTitle(f"{self.kalman_advanced_title}")
    adv.setStyleSheet(self.styleSheet())
    adv.setWindowFlags(
        Qt.WindowType.Dialog |
        Qt.WindowType.MSWindowsFixedSizeDialogHint
    )
    adv.setFixedSize(420, 380)

    layout = QVBoxLayout(adv)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(12)

    title = QLabel(f"{self.kalman_custom_parameters_title}")
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet("font-size: 16px; font-weight: bold;")
    layout.addWidget(title)

    # =====================================================
    # Q
    # =====================================================

    q_label = QLabel(f"{self.kalman_process_noise_label}")
    q_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(q_label)

    q_edit = QLineEdit()
    q_edit.setAlignment(Qt.AlignCenter)

    saved_q = self.sf_settings.value("kalman/custom_Q", "")
    if saved_q:
        q_edit.setText(saved_q)

    layout.addWidget(q_edit)

    q_help = QLabel(
        f"{self.kalman_process_noise_description}"
    )
    q_help.setAlignment(Qt.AlignCenter)
    q_help.setWordWrap(True)
    q_help.setStyleSheet("""
        QLabel {
            border: none;
            color: gray;
            font-size: 11px;
        }
    """)
    layout.addWidget(q_help)

    # =====================================================
    # R
    # =====================================================

    r_label = QLabel(f"{self.kalman_measurement_noise_label}")
    r_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(r_label)

    r_edit = QLineEdit()
    r_edit.setAlignment(Qt.AlignCenter)

    saved_r = self.sf_settings.value("kalman/custom_R", "")
    if saved_r:
        r_edit.setText(saved_r)

    layout.addWidget(r_edit)

    r_help = QLabel(
        f"{self.kalman_measurement_noise_description}"
    )
    r_help.setAlignment(Qt.AlignCenter)
    r_help.setWordWrap(True)
    r_help.setStyleSheet("""
        QLabel {
            border: none;
            color: gray;
            font-size: 11px;
        }
    """)
    layout.addWidget(r_help)

    # =====================================================
    # BUTTONS
    # =====================================================

    btn_row = QHBoxLayout()

    ok_btn = QPushButton(f"{self.kalman_advanced_apply_button_label}")
    cancel_btn = QPushButton(f"{self.kalman_advanced_cancel_button_label}")

    btn_row.addStretch()
    btn_row.addWidget(ok_btn)
    btn_row.addWidget(cancel_btn)
    btn_row.addStretch()

    layout.addLayout(btn_row)

    def apply_advanced():

        q_text = q_edit.text().strip()
        r_text = r_edit.text().strip()

        if not q_text or not r_text:
            QMessageBox.warning(
                adv,
                f"{self.kalman_advanced_missing_values_title}",
                f"{self.kalman_advanced_missing_values_message}"
            )
            return

        try:
            q = float(q_text)
            r = float(r_text)

            if q <= 0 or r <= 0:
                raise ValueError

        except ValueError:
            QMessageBox.warning(
                adv,
                f"{self.kalman_advanced_invalid_values_title}",
                f"{self.kalman_advanced_invalid_values_message}"
            )
            return

        self.sf_settings.setValue("kalman/custom_Q", str(q))
        self.sf_settings.setValue("kalman/custom_R", str(r))

        if self.sf_dialog.kalman_combo.findText("Custom") < 0:
            self.sf_dialog.kalman_combo.addItem("Custom")

        self.sf_dialog.kalman_combo.setCurrentText("Custom")

        update_kalman_info(self)

        adv.accept()

    ok_btn.clicked.connect(apply_advanced)
    cancel_btn.clicked.connect(adv.reject)

    adv.exec()

# =========================================================
# KALMAN UI UPDATE
# =========================================================
def update_kalman_info(self):

    if not hasattr(self, "sf_dialog"):
        return

    if not hasattr(self.sf_dialog, "kalman_info"):
        return

    preset = self.sf_dialog.kalman_combo.currentText()

    if preset == "Off":
        self.sf_dialog.kalman_info.setText(
            "Kalman filter is disabled."
        )
        return

    if preset in KALMAN_PRESETS:
        q = KALMAN_PRESETS[preset]["Q"]
        r = KALMAN_PRESETS[preset]["R"]
    else:
        q = self.sf_settings.value("kalman/custom_Q", "-")
        r = self.sf_settings.value("kalman/custom_R", "-")

    self.sf_dialog.kalman_info.setText(
        f"Q = {q}   |   R = {r}"
    )
    
def update_kalman_ui(self):

    enabled = self.sf_dialog.kalman_check.isChecked()
    self.sf_dialog.kalman_combo.setEnabled(enabled)

    if not enabled:
        if self.sf_dialog.kalman_combo.findText("Off") < 0:
            self.sf_dialog.kalman_combo.insertItem(0, "Off")
        self.sf_dialog.kalman_combo.setCurrentText("Off")
    else:
        idx = self.sf_dialog.kalman_combo.findText("Off")
        if idx >= 0:
            self.sf_dialog.kalman_combo.removeItem(idx)
        if self.sf_dialog.kalman_combo.currentText() == "":
            self.sf_dialog.kalman_combo.setCurrentText("Medium")

    self.sf_dialog.kalman_adv_btn.setEnabled(enabled)

def handle_kalman_combo_change(self):

    if self.sf_dialog.kalman_combo.currentText() == "Custom":
        return

    idx = self.sf_dialog.kalman_combo.findText("Custom")
    if idx >= 0:
        self.sf_dialog.kalman_combo.removeItem(idx)

# =========================================================
# APPLY
# =========================================================

def apply_signal_filters(self):

    enabled = self.sf_dialog.kalman_check.isChecked()
    self.sf_settings.setValue("kalman/enabled", enabled)

    preset = self.sf_dialog.kalman_combo.currentText()
    self.sf_settings.setValue("kalman/preset", preset)

    if preset == "Custom":
        self.sf_settings.setValue("kalman/preset", preset)

        q = self.sf_settings.value("kalman/custom_Q", None)
        r = self.sf_settings.value("kalman/custom_R", None)

        if q is None or r is None:
            QMessageBox.warning(
                self.sf_dialog,
                "Missing Kalman values",
                "Custom preset selected but no Q/R values were entered."
            )
            return

        q = float(q)
        r = float(r)

    else:
        params = KALMAN_PRESETS.get(preset, KALMAN_PRESETS["Medium"])
        q = params["Q"]
        r = params["R"]

        self.sf_settings.setValue("kalman/preset", preset)
        self.sf_settings.setValue("kalman/Q", q)
        self.sf_settings.setValue("kalman/R", r)

    self.kalman_enabled = enabled
    self.kalman_Q = q if enabled else None
    self.kalman_R = r if enabled else None

    process_noise = self.kalman_Q
    measurement_noise = r

    # kalman filters for real-time data smoothing
    
    self.kf_s11 = ComplexKalman(process_noise=process_noise, measurement_noise=measurement_noise)
    self.kf_s21 = ComplexKalman(process_noise=process_noise, measurement_noise=measurement_noise)

    sf_settings = get_settings(
        "INI/dut_measurement/signal_filters/signal_filters.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/signal_filters/signal_filters.ini",
        Path(__file__).resolve()
    )

    preset = sf_settings.value("kalman/preset", "Default")

    if preset == "Custom":
        q = sf_settings.value("kalman/custom_Q", 0.01, type=float)
        r = sf_settings.value("kalman/custom_R", 1.0, type=float)
    else:
        q = sf_settings.value("kalman/Q", 0.01, type=float)
        r = sf_settings.value("kalman/R", 1.0, type=float)

    if preset == "Off":
        self.kalman_label.setText(
            "Kalman filter is disabled"
        )
    else:
        self.kalman_label.setText(
            f"Kalman Filter: {preset} - Q = {q:.3f} · R = {r:.3f}"
        )

    self.sf_dialog.accept()