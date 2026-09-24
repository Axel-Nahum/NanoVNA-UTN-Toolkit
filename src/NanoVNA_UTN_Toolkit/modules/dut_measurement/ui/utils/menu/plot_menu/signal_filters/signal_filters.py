from pathlib import Path
from NanoVNA_UTN_Toolkit.utils import safe_import

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QStyledItemDelegate,
    QLineEdit, QGroupBox, QRadioButton, QButtonGroup,
    QSpinBox, QFrame, QSizePolicy, QMessageBox, QWidget
)
from PySide6.QtCore import Qt

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


_FRAME_ACTIVE   = "QFrame {{ border: 1px solid #3a7bd5; border-radius: 6px; background: transparent; }}"
_FRAME_INACTIVE = "QFrame {{ border: 1px solid #2a3050; border-radius: 6px; background: transparent; }}"
_TITLE_ACTIVE   = "font-weight: bold; font-size: 13px; color: #e0e0e0; border: none;"
_TITLE_INACTIVE = "font-weight: bold; font-size: 13px; color: #5a6a8a; border: none;"
_LABEL_ACTIVE   = "font-weight: normal; border: none;"
_LABEL_INACTIVE = "font-weight: normal; color: #5a6a8a; border: none;"
_DESC_ACTIVE    = "font-weight: normal; font-size: 11px; color: #8899bb; border: none;"
_DESC_INACTIVE  = "font-weight: normal; font-size: 11px; color: #3a4a6a; border: none;"


def open_signal_filters(self):

    self.sf_dialog = QDialog(self)
    self.sf_dialog.setWindowTitle(f"{self.signal_filters_title}")
    self.sf_dialog.setFixedSize(460, 492)
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

    active = getattr(self, '_active_filter', 'Off')

    main = QVBoxLayout(self.sf_dialog)
    main.setContentsMargins(20, 16, 20, 0)
    main.setSpacing(6)

    # ── Title ──────────────────────────────────────────────
    title_lbl = QLabel(f"{self.signal_filters_title}")
    title_lbl.setAlignment(Qt.AlignCenter)
    title_lbl.setStyleSheet("font-size: 22px; font-weight: bold;")
    main.addWidget(title_lbl)

    subtitle = QLabel("Reduce measurement noise while preserving signal characteristics.")
    subtitle.setAlignment(Qt.AlignCenter)
    subtitle.setWordWrap(True)
    subtitle.setStyleSheet("font-size: 11px; color: #8899bb;")
    main.addWidget(subtitle)

    # ── Filter mode (GroupBox keeps the native title-in-border look) ──
    type_group = QGroupBox("Filter mode")
    type_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; }")
    tg_layout = QHBoxLayout(type_group)
    tg_layout.setSpacing(0)

    self.sf_dialog.rb_off    = QRadioButton("Off")
    self.sf_dialog.rb_smooth = QRadioButton("Smoothing")
    self.sf_dialog.rb_kalman = QRadioButton("Kalman")

    rb_group = QButtonGroup(self.sf_dialog)
    rb_group.addButton(self.sf_dialog.rb_off)
    rb_group.addButton(self.sf_dialog.rb_smooth)
    rb_group.addButton(self.sf_dialog.rb_kalman)

    if active == "Smoothing":
        self.sf_dialog.rb_smooth.setChecked(True)
    elif active == "Kalman":
        self.sf_dialog.rb_kalman.setChecked(True)
    else:
        self.sf_dialog.rb_off.setChecked(True)

    tg_layout.addStretch()
    tg_layout.addWidget(self.sf_dialog.rb_off)
    tg_layout.addStretch()
    tg_layout.addWidget(self.sf_dialog.rb_smooth)
    tg_layout.addStretch()
    tg_layout.addWidget(self.sf_dialog.rb_kalman)
    tg_layout.addStretch()
    main.addWidget(type_group)
    main.addSpacing(12)

    # ── Smoothing — QFrame with title inside ───────────────
    smooth_frame = QFrame()
    smooth_frame.setObjectName("smoothFrame")
    self.sf_dialog.smooth_frame = smooth_frame

    sf_v = QVBoxLayout(smooth_frame)
    sf_v.setContentsMargins(14, 10, 14, 12)
    sf_v.setSpacing(8)

    self.sf_dialog.smooth_title = QLabel("Smoothing")
    sf_v.addWidget(self.sf_dialog.smooth_title)

    pct_row = QHBoxLayout()
    self.sf_dialog.smooth_pct_lbl = QLabel("Window size:")
    pct_row.addWidget(self.sf_dialog.smooth_pct_lbl)
    pct_row.addStretch()

    # Spinbox with custom ▲▼ buttons (app standard pattern)
    spin_container = QFrame()
    spin_container.setObjectName("spinboxContainer")
    spin_c_layout = QHBoxLayout(spin_container)
    spin_c_layout.setContentsMargins(4, 0, 0, 0)
    spin_c_layout.setSpacing(0)

    self.sf_dialog.smooth_spin = QSpinBox()
    self.sf_dialog.smooth_spin.setRange(1, 100)
    self.sf_dialog.smooth_spin.setSuffix(" %")
    self.sf_dialog.smooth_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
    self.sf_dialog.smooth_spin.setStyleSheet("QSpinBox { border: none; background: transparent; }")
    saved_pct = self.sf_settings.value("smoothing/window_pct", 5, type=int)
    self.sf_dialog.smooth_spin.setValue(saved_pct)

    self.sf_dialog.smooth_btn_up = QPushButton("▲")
    self.sf_dialog.smooth_btn_up.setObjectName("spinboxUpBtn")
    self.sf_dialog.smooth_btn_up.setFixedSize(18, 12)
    self.sf_dialog.smooth_btn_up.clicked.connect(self.sf_dialog.smooth_spin.stepUp)

    self.sf_dialog.smooth_btn_down = QPushButton("▼")
    self.sf_dialog.smooth_btn_down.setObjectName("spinboxDownBtn")
    self.sf_dialog.smooth_btn_down.setFixedSize(18, 12)
    self.sf_dialog.smooth_btn_down.clicked.connect(self.sf_dialog.smooth_spin.stepDown)

    btn_col = QVBoxLayout()
    btn_col.setSpacing(1)
    btn_col.setContentsMargins(3, 0, 0, 0)
    btn_col.addWidget(self.sf_dialog.smooth_btn_up)
    btn_col.addWidget(self.sf_dialog.smooth_btn_down)

    spin_c_layout.addWidget(self.sf_dialog.smooth_spin, 1)
    spin_c_layout.addLayout(btn_col)

    pct_row.addWidget(spin_container)
    sf_v.addLayout(pct_row)

    self.sf_dialog.smooth_desc = QLabel("Moving average window as a percentage of sweep points.")
    self.sf_dialog.smooth_desc.setWordWrap(True)
    sf_v.addWidget(self.sf_dialog.smooth_desc)

    main.addWidget(smooth_frame)
    main.addSpacing(12)

    # ── Kalman Filter — QFrame with title inside ───────────
    kalman_frame = QFrame()
    kalman_frame.setObjectName("kalmanFrame")
    self.sf_dialog.kalman_frame = kalman_frame

    kf_v = QVBoxLayout(kalman_frame)
    kf_v.setContentsMargins(14, 10, 14, 12)
    kf_v.setSpacing(8)

    self.sf_dialog.kalman_title = QLabel("Kalman Filter")
    kf_v.addWidget(self.sf_dialog.kalman_title)

    preset_row = QHBoxLayout()
    self.sf_dialog.kalman_preset_lbl = QLabel(f"{self.kalman_preset_label}")
    preset_row.addWidget(self.sf_dialog.kalman_preset_lbl)
    preset_row.addStretch()

    self.sf_dialog.kalman_combo = QComboBox()
    self.sf_dialog.kalman_combo.setItemDelegate(CenterDelegate())
    self.sf_dialog.kalman_combo.setFixedWidth(120)
    self.sf_dialog.kalman_combo.addItems(list(KALMAN_PRESETS.keys()))

    saved_preset = self.sf_settings.value("kalman/preset", "Medium")
    if saved_preset == "Custom":
        self.sf_dialog.kalman_combo.addItem("Custom")
    idx = self.sf_dialog.kalman_combo.findText(saved_preset)
    if idx >= 0:
        self.sf_dialog.kalman_combo.setCurrentIndex(idx)

    self.sf_dialog.kalman_combo.currentTextChanged.connect(
        lambda _: (handle_kalman_combo_change(self), update_kalman_info(self))
    )

    preset_row.addWidget(self.sf_dialog.kalman_combo)
    kf_v.addLayout(preset_row)

    self.sf_dialog.kalman_params_lbl = QLabel("Preset parameters:")
    self.sf_dialog.kalman_params_lbl.setStyleSheet(
        "font-weight: normal; font-size: 11px; font-style: italic; border: none;"
    )
    kf_v.addWidget(self.sf_dialog.kalman_params_lbl)

    self.sf_dialog.kalman_info = QLabel()
    self.sf_dialog.kalman_info.setAlignment(Qt.AlignLeft)
    self.sf_dialog.kalman_info.setStyleSheet("font-size: 13px; font-weight: normal; border: none; padding-left: 8px;")
    kf_v.addWidget(self.sf_dialog.kalman_info)

    main.addWidget(kalman_frame)

    # ── Connect radios ─────────────────────────────────────
    rb_group.buttonToggled.connect(lambda *_: update_filter_ui(self))
    update_filter_ui(self)
    update_kalman_info(self)

    main.addSpacing(8)

    # ── Separator ──────────────────────────────────────────
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFixedHeight(1)
    sep.setStyleSheet("background-color: #2a3050; border: none;")
    main.addWidget(sep)

    # ── Actions ────────────────────────────────────────────
    actions = QHBoxLayout()
    actions.setContentsMargins(0, 10, 0, 14)
    cancel_btn = QPushButton(f"{self.kalman_advanced_cancel_button_label}")
    apply_btn  = QPushButton(f"{self.kalman_advanced_apply_button_label}")
    cancel_btn.setMinimumSize(120, 36)
    apply_btn.setMinimumSize(120, 36)
    cancel_btn.setStyleSheet("""
        QPushButton { background-color: #2a2d3e; color: #c0c8d8; border: 1px solid #3a3f5a;
                      border-radius: 8px; font-size: 13px; }
        QPushButton:hover { background-color: #333754; }
        QPushButton:pressed { background-color: #1e2030; }
    """)
    apply_btn.setStyleSheet("""
        QPushButton { background-color: #2563eb; color: white; border: none;
                      border-radius: 8px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #1d4fd8; }
        QPushButton:pressed { background-color: #1a44c2; }
    """)
    cancel_btn.clicked.connect(self.sf_dialog.reject)
    apply_btn.clicked.connect(lambda: apply_signal_filters(self))
    actions.addStretch()
    actions.addWidget(cancel_btn)
    actions.addSpacing(15)
    actions.addWidget(apply_btn)
    actions.addStretch()
    main.addLayout(actions)

    self.sf_dialog.exec()


# =========================================================
# FILTER UI UPDATE
# =========================================================

def update_filter_ui(self):
    if not hasattr(self, "sf_dialog"):
        return
    smooth_on = self.sf_dialog.rb_smooth.isChecked()
    kalman_on = self.sf_dialog.rb_kalman.isChecked()

    # Smoothing frame
    self.sf_dialog.smooth_frame.setStyleSheet(
        "QFrame#smoothFrame { border: 1px solid #3a7bd5; border-radius: 6px; background: transparent; }"
        if smooth_on else
        "QFrame#smoothFrame { border: 1px solid #2a3050; border-radius: 6px; background: transparent; }"
    )
    self.sf_dialog.smooth_title.setStyleSheet(_TITLE_ACTIVE if smooth_on else _TITLE_INACTIVE)
    self.sf_dialog.smooth_pct_lbl.setStyleSheet(_LABEL_ACTIVE if smooth_on else _LABEL_INACTIVE)
    self.sf_dialog.smooth_desc.setStyleSheet(_DESC_ACTIVE if smooth_on else _DESC_INACTIVE)
    self.sf_dialog.smooth_spin.setEnabled(smooth_on)
    self.sf_dialog.smooth_btn_up.setEnabled(smooth_on)
    self.sf_dialog.smooth_btn_down.setEnabled(smooth_on)

    # Kalman frame
    self.sf_dialog.kalman_frame.setStyleSheet(
        "QFrame#kalmanFrame { border: 1px solid #3a7bd5; border-radius: 6px; background: transparent; }"
        if kalman_on else
        "QFrame#kalmanFrame { border: 1px solid #2a3050; border-radius: 6px; background: transparent; }"
    )
    self.sf_dialog.kalman_title.setStyleSheet(_TITLE_ACTIVE if kalman_on else _TITLE_INACTIVE)
    self.sf_dialog.kalman_preset_lbl.setStyleSheet(_LABEL_ACTIVE if kalman_on else _LABEL_INACTIVE)
    self.sf_dialog.kalman_combo.setEnabled(kalman_on)
    self.sf_dialog.kalman_info.setEnabled(kalman_on)


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

    q_label = QLabel(f"{self.kalman_process_noise_label}")
    q_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(q_label)

    q_edit = QLineEdit()
    q_edit.setAlignment(Qt.AlignCenter)
    saved_q = self.sf_settings.value("kalman/custom_Q", "")
    if saved_q:
        q_edit.setText(saved_q)
    layout.addWidget(q_edit)

    q_help = QLabel(f"{self.kalman_process_noise_description}")
    q_help.setAlignment(Qt.AlignCenter)
    q_help.setWordWrap(True)
    q_help.setStyleSheet("border: none; color: gray; font-size: 11px;")
    layout.addWidget(q_help)

    r_label = QLabel(f"{self.kalman_measurement_noise_label}")
    r_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(r_label)

    r_edit = QLineEdit()
    r_edit.setAlignment(Qt.AlignCenter)
    saved_r = self.sf_settings.value("kalman/custom_R", "")
    if saved_r:
        r_edit.setText(saved_r)
    layout.addWidget(r_edit)

    r_help = QLabel(f"{self.kalman_measurement_noise_description}")
    r_help.setAlignment(Qt.AlignCenter)
    r_help.setWordWrap(True)
    r_help.setStyleSheet("border: none; color: gray; font-size: 11px;")
    layout.addWidget(r_help)

    btn_row = QHBoxLayout()
    ok_btn     = QPushButton(f"{self.kalman_advanced_apply_button_label}")
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
            QMessageBox.warning(adv, f"{self.kalman_advanced_missing_values_title}",
                                f"{self.kalman_advanced_missing_values_message}")
            return
        try:
            q = float(q_text)
            r = float(r_text)
            if q <= 0 or r <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(adv, f"{self.kalman_advanced_invalid_values_title}",
                                f"{self.kalman_advanced_invalid_values_message}")
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
# KALMAN HELPERS
# =========================================================

def update_kalman_info(self):
    if not hasattr(self, "sf_dialog") or not hasattr(self.sf_dialog, "kalman_info"):
        return
    preset = self.sf_dialog.kalman_combo.currentText()
    if preset in KALMAN_PRESETS:
        q = KALMAN_PRESETS[preset]["Q"]
        r = KALMAN_PRESETS[preset]["R"]
    else:
        q = self.sf_settings.value("kalman/custom_Q", "-")
        r = self.sf_settings.value("kalman/custom_R", "-")
    self.sf_dialog.kalman_info.setText(f"Q = {q}  ·  R = {r}")


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

    if self.sf_dialog.rb_smooth.isChecked():
        active = "Smoothing"
    elif self.sf_dialog.rb_kalman.isChecked():
        active = "Kalman"
    else:
        active = "Off"

    self._active_filter = active

    pct = self.sf_dialog.smooth_spin.value()
    self.sf_settings.setValue("smoothing/window_pct", pct)

    preset = self.sf_dialog.kalman_combo.currentText()
    self.sf_settings.setValue("kalman/preset", preset)

    if preset == "Custom":
        q = self.sf_settings.value("kalman/custom_Q", None)
        r = self.sf_settings.value("kalman/custom_R", None)
        if q is None or r is None:
            QMessageBox.warning(self.sf_dialog, "Missing Kalman values",
                                "Custom preset selected but no Q/R values were entered.")
            return
        q = float(q)
        r = float(r)
    else:
        params = KALMAN_PRESETS.get(preset, KALMAN_PRESETS["Medium"])
        q = params["Q"]
        r = params["R"]
        self.sf_settings.setValue("kalman/Q", q)
        self.sf_settings.setValue("kalman/R", r)

    self.sf_settings.sync()

    # Reset Kalman filters
    process_noise      = q if active == "Kalman" else 0.01
    measurement_noise  = r if active == "Kalman" else 1.0
    self.kf_s11 = ComplexKalman(process_noise=process_noise, measurement_noise=measurement_noise)
    self.kf_s21 = ComplexKalman(process_noise=process_noise, measurement_noise=measurement_noise)

    # Update label
    if active == "Smoothing":
        self.kalman_label.setText(f"Smoothing: {pct}%")
        self.sweep_button.setEnabled(True)
    elif active == "Kalman":
        self.kalman_label.setText(f"Kalman: {preset} — Q = {q:.3f} · R = {r:.3f}")
        self.sweep_button.setEnabled(True)
    else:
        self.kalman_label.setText("No filter active")
        self.sweep_button.setEnabled(True)

    self.sf_dialog.accept()
