"""
Signal filters dialog for the characterization measurement window.

Same Smoothing + Kalman options as the DUT module, applied to ε′ and ε″.
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QStyledItemDelegate,
    QGroupBox, QRadioButton, QButtonGroup,
    QSpinBox, QFrame,
)
from PySide6.QtCore import Qt

from NanoVNA_UTN_Toolkit.utils import safe_import

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils",
    "get_settings",
)
ComplexKalman = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.real_time.kalman_filter.kalman_filter",
    "ComplexKalman",
)

_INI_EXE = "INI/char_measurement/signal_filters/signal_filters_char.ini"
_INI_DEV = "modules/material_characterization/ui/measurement_main_window/utils/menu/signal_filters/signal_filters_char.ini"

KALMAN_PRESETS = {
    "Light":  {"Q": 0.1,   "R": 0.01},
    "Medium": {"Q": 0.01,  "R": 0.1},
    "Strong": {"Q": 0.001, "R": 1.0},
}

_FRAME_ACTIVE   = "QFrame {{ border: 1px solid #3a7bd5; border-radius: 6px; background: transparent; }}"
_FRAME_INACTIVE = "QFrame {{ border: 1px solid #2a3050; border-radius: 6px; background: transparent; }}"
_TITLE_ACTIVE   = "font-weight: bold; font-size: 13px; color: #e0e0e0; border: none;"
_TITLE_INACTIVE = "font-weight: bold; font-size: 13px; color: #5a6a8a; border: none;"
_LABEL_ACTIVE   = "font-weight: normal; border: none;"
_LABEL_INACTIVE = "font-weight: normal; color: #5a6a8a; border: none;"
_DESC_ACTIVE    = "font-weight: normal; font-size: 11px; color: #8899bb; border: none;"
_DESC_INACTIVE  = "font-weight: normal; font-size: 11px; color: #3a4a6a; border: none;"


class _CenterDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter


def open_signal_filters_char(window):
    dlg = QDialog(window)
    dlg.setWindowTitle("Signal Filters")
    dlg.setFixedSize(460, 430)
    dlg.setStyleSheet(window.styleSheet())
    dlg.setWindowFlags(
        Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint
    )

    sf_settings = get_settings(_INI_EXE, _INI_DEV, Path(__file__).resolve())
    active = getattr(window, "_active_filter", "Off")

    main = QVBoxLayout(dlg)
    main.setContentsMargins(20, 16, 20, 0)
    main.setSpacing(6)

    # ── Title ──────────────────────────────────────────────────────────── #
    title_lbl = QLabel("Signal Filters")
    title_lbl.setAlignment(Qt.AlignCenter)
    title_lbl.setStyleSheet("font-size: 22px; font-weight: bold;")
    main.addWidget(title_lbl)

    subtitle = QLabel("Reduce measurement noise while preserving signal characteristics.")
    subtitle.setAlignment(Qt.AlignCenter)
    subtitle.setWordWrap(True)
    subtitle.setStyleSheet("font-size: 11px; color: #8899bb;")
    main.addWidget(subtitle)

    # ── Filter mode ────────────────────────────────────────────────────── #
    type_group = QGroupBox("Filter mode")
    type_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; }")
    tg_layout = QHBoxLayout(type_group)
    tg_layout.setSpacing(0)

    rb_off    = QRadioButton("Off")
    rb_smooth = QRadioButton("Smoothing")
    rb_kalman = QRadioButton("Kalman")

    rb_group = QButtonGroup(dlg)
    rb_group.addButton(rb_off)
    rb_group.addButton(rb_smooth)
    rb_group.addButton(rb_kalman)

    if active == "Smoothing":
        rb_smooth.setChecked(True)
    elif active == "Kalman":
        rb_kalman.setChecked(True)
    else:
        rb_off.setChecked(True)

    tg_layout.addStretch()
    tg_layout.addWidget(rb_off)
    tg_layout.addStretch()
    tg_layout.addWidget(rb_smooth)
    tg_layout.addStretch()
    tg_layout.addWidget(rb_kalman)
    tg_layout.addStretch()
    main.addWidget(type_group)
    main.addSpacing(12)

    # ── Smoothing frame ────────────────────────────────────────────────── #
    smooth_frame = QFrame()
    smooth_frame.setObjectName("smoothFrame")
    sf_v = QVBoxLayout(smooth_frame)
    sf_v.setContentsMargins(14, 10, 14, 12)
    sf_v.setSpacing(8)

    smooth_title = QLabel("Smoothing")
    smooth_title.setStyleSheet(_TITLE_ACTIVE + " background: transparent;")
    sf_v.addWidget(smooth_title)

    pct_row = QHBoxLayout()
    smooth_pct_lbl = QLabel("Window size:")
    pct_row.addWidget(smooth_pct_lbl)
    pct_row.addStretch()

    spin_container = QFrame()
    spin_container.setObjectName("spinboxContainer")
    spin_cl = QHBoxLayout(spin_container)
    spin_cl.setContentsMargins(4, 0, 0, 0)
    spin_cl.setSpacing(0)

    smooth_spin = QSpinBox()
    smooth_spin.setRange(1, 100)
    smooth_spin.setSuffix(" %")
    smooth_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
    smooth_spin.setStyleSheet("QSpinBox { border: none; background: transparent; }")
    smooth_spin.setValue(sf_settings.value("smoothing/window_pct", 5, type=int))

    btn_up = QPushButton("▲")
    btn_up.setObjectName("spinboxUpBtn")
    btn_up.setFixedSize(18, 12)
    btn_up.clicked.connect(smooth_spin.stepUp)
    btn_dn = QPushButton("▼")
    btn_dn.setObjectName("spinboxDownBtn")
    btn_dn.setFixedSize(18, 12)
    btn_dn.clicked.connect(smooth_spin.stepDown)

    btn_col = QVBoxLayout()
    btn_col.setSpacing(1)
    btn_col.setContentsMargins(3, 0, 0, 0)
    btn_col.addWidget(btn_up)
    btn_col.addWidget(btn_dn)
    spin_cl.addWidget(smooth_spin, 1)
    spin_cl.addLayout(btn_col)
    pct_row.addWidget(spin_container)
    sf_v.addLayout(pct_row)

    smooth_desc = QLabel("Moving average window as a percentage of sweep points.")
    smooth_desc.setWordWrap(True)
    sf_v.addWidget(smooth_desc)
    main.addWidget(smooth_frame)
    main.addSpacing(12)

    # ── Kalman frame ───────────────────────────────────────────────────── #
    kalman_frame = QFrame()
    kalman_frame.setObjectName("kalmanFrame")
    kf_v = QVBoxLayout(kalman_frame)
    kf_v.setContentsMargins(14, 10, 14, 12)
    kf_v.setSpacing(8)

    kalman_title = QLabel("Kalman Filter")
    kalman_title.setStyleSheet(_TITLE_INACTIVE + " background: transparent;")
    kf_v.addWidget(kalman_title)

    preset_row = QHBoxLayout()
    kalman_preset_lbl = QLabel("Preset:")
    kalman_preset_lbl.setStyleSheet("background: transparent;")
    preset_row.addWidget(kalman_preset_lbl)
    preset_row.addStretch()

    kalman_combo = QComboBox()
    kalman_combo.setItemDelegate(_CenterDelegate())
    kalman_combo.setFixedWidth(120)
    kalman_combo.addItems(list(KALMAN_PRESETS.keys()))

    saved_preset = sf_settings.value("kalman/preset", "Medium")
    if saved_preset == "Custom":
        kalman_combo.addItem("Custom")
    idx = kalman_combo.findText(saved_preset)
    if idx >= 0:
        kalman_combo.setCurrentIndex(idx)

    preset_row.addWidget(kalman_combo)
    kf_v.addLayout(preset_row)

    kalman_info = QLabel()
    kalman_info.setAlignment(Qt.AlignLeft)
    kalman_info.setStyleSheet(
        "font-size: 13px; font-weight: normal; border: none; padding-left: 8px; background: transparent;"
    )
    kf_v.addWidget(kalman_info)
    main.addWidget(kalman_frame)

    # ── Helpers ────────────────────────────────────────────────────────── #
    widgets = {
        "smooth_frame": smooth_frame, "smooth_title": smooth_title,
        "smooth_pct_lbl": smooth_pct_lbl, "smooth_desc": smooth_desc,
        "smooth_spin": smooth_spin, "btn_up": btn_up, "btn_dn": btn_dn,
        "kalman_frame": kalman_frame, "kalman_title": kalman_title,
        "kalman_preset_lbl": kalman_preset_lbl, "kalman_combo": kalman_combo,
        "kalman_info": kalman_info,
        "rb_off": rb_off, "rb_smooth": rb_smooth, "rb_kalman": rb_kalman,
    }

    def _update_ui():
        smooth_on = rb_smooth.isChecked()
        kalman_on = rb_kalman.isChecked()
        smooth_frame.setStyleSheet(
            "QFrame#smoothFrame { border: 1px solid #3a7bd5; border-radius: 6px; background: transparent; }"
            if smooth_on else
            "QFrame#smoothFrame { border: 1px solid #2a3050; border-radius: 6px; background: transparent; }"
        )
        smooth_title.setStyleSheet(_TITLE_ACTIVE if smooth_on else _TITLE_INACTIVE)
        smooth_pct_lbl.setStyleSheet(_LABEL_ACTIVE if smooth_on else _LABEL_INACTIVE)
        smooth_desc.setStyleSheet(_DESC_ACTIVE if smooth_on else _DESC_INACTIVE)
        smooth_spin.setEnabled(smooth_on)
        btn_up.setEnabled(smooth_on)
        btn_dn.setEnabled(smooth_on)
        kalman_frame.setStyleSheet(
            "QFrame#kalmanFrame { border: 1px solid #3a7bd5; border-radius: 6px; background: transparent; }"
            if kalman_on else
            "QFrame#kalmanFrame { border: 1px solid #2a3050; border-radius: 6px; background: transparent; }"
        )
        kalman_title.setStyleSheet(
            (_TITLE_ACTIVE if kalman_on else _TITLE_INACTIVE) + " background: transparent;"
        )
        _k_dim = "color: #3a4a6a;" if not kalman_on else "color: #8899bb;"
        kalman_info.setStyleSheet(
            f"font-size: 13px; font-weight: normal; border: none; padding-left: 8px; background: transparent; {_k_dim}"
        )
        kalman_combo.setEnabled(kalman_on)

    def _update_kalman_info():
        preset = kalman_combo.currentText()
        if preset in KALMAN_PRESETS:
            q = KALMAN_PRESETS[preset]["Q"]
            r = KALMAN_PRESETS[preset]["R"]
        else:
            q = sf_settings.value("kalman/custom_Q", "-")
            r = sf_settings.value("kalman/custom_R", "-")
        kalman_info.setText(f"Q = {q}  ·  R = {r}")

    rb_group.buttonToggled.connect(lambda *_: _update_ui())
    kalman_combo.currentTextChanged.connect(lambda _: _update_kalman_info())
    _update_ui()
    _update_kalman_info()

    # ── Separator + actions ────────────────────────────────────────────── #
    main.addSpacing(8)
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFixedHeight(1)
    sep.setStyleSheet("background-color: #2a3050; border: none;")
    main.addWidget(sep)

    actions = QHBoxLayout()
    actions.setContentsMargins(0, 10, 0, 14)
    cancel_btn = QPushButton("Cancel")
    apply_btn  = QPushButton("Apply")
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
    cancel_btn.clicked.connect(dlg.reject)

    def _apply():
        if rb_smooth.isChecked():
            new_active = "Smoothing"
        elif rb_kalman.isChecked():
            new_active = "Kalman"
        else:
            new_active = "Off"

        pct = smooth_spin.value()
        sf_settings.setValue("smoothing/window_pct", pct)
        preset = kalman_combo.currentText()
        sf_settings.setValue("kalman/preset", preset)

        if preset in KALMAN_PRESETS:
            q = KALMAN_PRESETS[preset]["Q"]
            r = KALMAN_PRESETS[preset]["R"]
            sf_settings.setValue("kalman/Q", q)
            sf_settings.setValue("kalman/R", r)
        else:
            q = float(sf_settings.value("kalman/custom_Q", 0.01))
            r = float(sf_settings.value("kalman/custom_R", 0.1))
        sf_settings.sync()

        window._active_filter      = new_active
        window._filter_smooth_pct  = pct
        # Reset Kalman filter so it starts fresh with new params
        process_noise     = q if new_active == "Kalman" else 0.01
        measurement_noise = r if new_active == "Kalman" else 1.0
        window._kf_eps = ComplexKalman(
            process_noise=process_noise,
            measurement_noise=measurement_noise,
        )
        dlg.accept()
        # Re-apply filter to current result and redraw
        window._on_filter_settings_changed()

    apply_btn.clicked.connect(_apply)
    actions.addStretch()
    actions.addWidget(cancel_btn)
    actions.addSpacing(15)
    actions.addWidget(apply_btn)
    actions.addStretch()
    main.addLayout(actions)

    dlg.exec()
