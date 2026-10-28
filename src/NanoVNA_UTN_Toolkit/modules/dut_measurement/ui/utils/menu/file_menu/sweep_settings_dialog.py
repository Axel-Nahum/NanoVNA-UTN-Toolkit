"""
Sweep Settings dialog for the DUT measurement module.

Lets the user change the real-time sweep interval and re-open the
calibration wizard (only available when a wizard calibration exists).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QDoubleSpinBox, QPushButton, QLabel, QDialogButtonBox,
    QFrame,
)

from NanoVNA_UTN_Toolkit.utils import safe_import

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")


def _restore_calibration_data(wizard) -> None:
    """After show_first_screen cleared all managers, reload the saved .s1p data."""
    try:
        import skrf as rf
        import numpy as np

        settings = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve(),
        )
        settings.sync()
        method = settings.value("Calibration/Method", "", type=str)
        if not method:
            return

        # Pre-select method in the dropdown (the signal enables next_button and sets selected_method)
        idx = wizard.freq_dropdown.findText(method)
        if idx > 0:
            wizard.freq_dropdown.setCurrentIndex(idx)

        # Load OSM standards (used by OSM, 1-Port+N and Enhanced-Response)
        if method in ("OSM (Open - Short - Match)", "1-Port+N", "Enhanced-Response"):
            osm_path = wizard.osm_calibration.osm_results_path
            for std in ("open", "short", "match"):
                fp = os.path.join(osm_path, f"{std}.s1p")
                if not os.path.exists(fp):
                    continue
                try:
                    net = rf.Network(fp)
                    wizard.osm_calibration.measurements[std]["freqs"] = net.f
                    wizard.osm_calibration.measurements[std]["s11"]   = net.s[:, 0, 0]
                    wizard.osm_calibration.measurements[std]["measured"] = True
                except Exception as e:
                    logging.warning("[restore_cal] Could not load %s: %s", std, e)
            wizard.osm_calibration._check_completion()

        # Load Open/Short standard (Open/Short Normalization — one combined measurement)
        elif method == "Open/Short Normalization":
            if hasattr(wizard, "os_calibration") and wizard.os_calibration is not None:
                os_path = wizard.os_calibration.open_short_results_path
                fp = os.path.join(os_path, "open_short.s1p")
                if os.path.exists(fp):
                    try:
                        net = rf.Network(fp)
                        wizard.os_calibration.measurements["open_short"]["freqs"]   = net.f
                        wizard.os_calibration.measurements["open_short"]["s11"]     = net.s[:, 0, 0]
                        wizard.os_calibration.measurements["open_short"]["measured"] = True
                        wizard.os_calibration.is_complete = True
                    except Exception as e:
                        logging.warning("[restore_cal] Could not load open_short: %s", e)

        # Load Thru standard (Thru Normalization)
        elif method == "Thru Normalization":
            if hasattr(wizard, "thru_calibration") and wizard.thru_calibration is not None:
                thru_path = wizard.thru_calibration.thru_results_path
                fp = os.path.join(thru_path, "thru.s2p")
                if os.path.exists(fp):
                    try:
                        net = rf.Network(fp)
                        wizard.thru_calibration.measurements["thru"]["freqs"]   = net.f
                        wizard.thru_calibration.measurements["thru"]["s11"]     = net.s[:, 0, 0]
                        wizard.thru_calibration.measurements["thru"]["s21"]     = net.s[:, 1, 0]
                        wizard.thru_calibration.measurements["thru"]["measured"] = True
                        wizard.thru_calibration.is_complete = True
                    except Exception as e:
                        logging.warning("[restore_cal] Could not load thru: %s", e)

        # Advance to step 1 (first measurement step)
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.wizard_cal_windows.wizard_cal_utils.screens import next_step
        next_step(wizard)
        # next_step always disables next_button at entry; re-enable it since
        # all measurements are already loaded from disk.
        wizard.next_button.setEnabled(True)

    except Exception as e:
        logging.warning("[restore_cal] Unexpected error: %s", e)


def _has_wizard_calibration() -> bool:
    """Return True if a wizard-based calibration was previously done."""
    try:
        settings = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve(),
        )
        settings.sync()
        kits_ok       = settings.value("Calibration/Kits",             False, type=bool)
        no_cal        = settings.value("Calibration/NoCalibration",     False, type=bool)
        wizard_done   = settings.value("Calibration/CalibrationWizard", False, type=bool)
        return wizard_done and not kits_ok and not no_cal
    except Exception:
        return False


def open_sweep_settings_dialog(window):
    """Open the Sweep Settings dialog from the DUT measurement window."""

    dlg = QDialog(window)
    dlg.setWindowTitle("Sweep Settings")
    dlg.setMinimumWidth(340)
    dlg.setModal(True)

    root = QVBoxLayout(dlg)
    root.setSpacing(12)
    root.setContentsMargins(16, 16, 16, 12)

    # ── Real-time interval ──────────────────────────────────────────────── #
    rt_group = QGroupBox("Real-time sweep")
    rt_form = QFormLayout(rt_group)
    rt_form.setVerticalSpacing(6)
    rt_form.setHorizontalSpacing(12)

    interval_spin = QDoubleSpinBox()
    interval_spin.setDecimals(1)
    interval_spin.setRange(0.1, 60.0)
    interval_spin.setSingleStep(0.1)
    interval_spin.setSuffix(" s")
    interval_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
    interval_spin.setMinimumHeight(26)
    interval_spin.setStyleSheet(
        "QDoubleSpinBox { border: none; background: transparent; }"
    )

    current_ms = getattr(window, "realtime_interval_ms", 100)
    interval_spin.setValue(current_ms / 1000.0)

    # External ▲▼ buttons (same pattern as the rest of the project)
    spin_container = QFrame()
    spin_container.setObjectName("spinboxContainer")
    spin_container.setMinimumHeight(30)
    spin_cl = QHBoxLayout(spin_container)
    spin_cl.setContentsMargins(4, 1, 0, 1)
    spin_cl.setSpacing(0)
    btn_h = 14
    up_btn = QPushButton("▲")
    up_btn.setObjectName("spinboxUpBtn")
    up_btn.setFixedSize(18, btn_h)
    up_btn.clicked.connect(interval_spin.stepUp)
    dn_btn = QPushButton("▼")
    dn_btn.setObjectName("spinboxDownBtn")
    dn_btn.setFixedSize(18, btn_h)
    dn_btn.clicked.connect(interval_spin.stepDown)
    btn_col = QVBoxLayout()
    btn_col.setSpacing(1)
    btn_col.setContentsMargins(3, 0, 0, 0)
    btn_col.addWidget(up_btn)
    btn_col.addWidget(dn_btn)
    spin_cl.addWidget(interval_spin, 1)
    spin_cl.addLayout(btn_col)

    rt_form.addRow("Interval:", spin_container)
    root.addWidget(rt_group)

    # ── Calibration ─────────────────────────────────────────────────────── #
    cal_group = QGroupBox("Calibration")
    cal_v = QVBoxLayout(cal_group)
    cal_v.setSpacing(6)

    wizard_btn = QPushButton("🧙  Re-open Calibration Wizard…")
    wizard_btn.setMinimumHeight(30)
    wizard_has_data = _has_wizard_calibration()
    wizard_btn.setEnabled(wizard_has_data)
    if not wizard_has_data:
        wizard_btn.setToolTip(
            "No wizard calibration found. Use Calibration → Calibration Wizard to calibrate first."
        )

    cal_v.addWidget(wizard_btn)
    root.addWidget(cal_group)

    # ── Buttons ─────────────────────────────────────────────────────────── #
    btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    root.addWidget(btn_box)

    # ── Signals ─────────────────────────────────────────────────────────── #

    def _open_wizard():
        dlg.accept()
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.calibration_menu.calibration_menu import (
            open_calibration_wizard,
        )
        open_calibration_wizard(window)
        wizard = getattr(window, "welcome_windows", None)
        if wizard is not None:
            QTimer.singleShot(0, lambda: _restore_calibration_data(wizard))

    wizard_btn.clicked.connect(_open_wizard)

    def _apply():
        from NanoVNA_UTN_Toolkit.shared.utils.real_time.real_time import RT_MIN_INTERVAL_MS
        new_ms = max(RT_MIN_INTERVAL_MS, int(interval_spin.value() * 1000))
        window.realtime_interval_ms = new_ms
        timer = getattr(window, "_rt_timer", None)
        if timer is not None:
            try:
                timer.setInterval(new_ms)
            except RuntimeError:
                pass
        dlg.accept()

    btn_box.accepted.connect(_apply)
    btn_box.rejected.connect(dlg.reject)

    dlg.exec()
