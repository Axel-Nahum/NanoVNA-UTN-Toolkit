"""
Result screen of the characterization wizard.

EN: Runs the calibration + permittivity solver and plots epsilon_r(f): the real
    part (energy storage) and the loss (dissipation), with the other candidate
    root branches drawn faintly. The left column shows a worded summary (using
    the unknown-liquid name), any warnings, and a copyable "intermediate data"
    block: the general 5th-order equation and, for a user-selected frequency,
    the numeric coefficients, the five x-roots (the extraneous ones, Re x <= 0,
    marked as such; the selected one tagged) and the selected epsilon_r.
    The bottom bar shows an "Export image" button (left of Finish) that saves
    the epsilon_r figure in high quality. Manual per-frequency root override is
    a Stage 2 feature.

ES: Ejecuta la calibracion y el solver de permitividad y grafica epsilon_r(f):
    la parte real (almacenamiento de energia) y la perdida (disipacion), con las
    demas ramas candidatas en tenue. La columna izquierda muestra un resumen en
    palabras (usando el nombre del liquido incognita), los avisos y un bloque de
    "datos intermedios" copiable: la ecuacion general de 5to orden y, para una
    frecuencia elegida, los coeficientes numericos, las cinco raices x (las
    extranas, Re x <= 0, marcadas como tales; la elegida senalada) y el
    epsilon_r seleccionado. La barra inferior muestra un boton "Exportar imagen"
    (a la izquierda de Finalizar) que guarda la figura de epsilon_r en alta
    calidad. La seleccion manual de raiz por frecuencia es de la Etapa 2.
"""

from __future__ import annotations

import html
import logging
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from NanoVNA_UTN_Toolkit.utils import safe_import

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)


class _HalfWidthFilter(QObject):
    def __init__(self, target, parent):
        super().__init__(parent)
        self._target = target

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self._target.setFixedWidth(max(300, obj.width() // 2))
        return False

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.simplified_solver import (
    SimplifiedEpsilonResult,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.permittivity_columns import (
    loss_tangent,
    nonpassive_mask_of,
    permittivity_columns,
    scale_limits,
    shade_unusable_band,
    usable_band_of,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.charts.epsilon_chart import (
    EpsilonChartManager,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.step_sidebar import (
    build_step_sidebar,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import calibration_store

logger = logging.getLogger(__name__)

_MAX_FREQ_CHOICES = 200


def build_result_screen(wizard, descriptor, step_def):
    texts = load_text("characterization_wizard.json")
    rtexts = texts.get("result", {})
    wizard.title_label.setText(rtexts.get("title", "Permittivity Result"))

    # Reuse cached result when navigating back/forward without changes. It is
    # only valid while the calibration still holds it: any input change (a
    # standard, the DUT, T, a reference liquid, a loaded kit) makes
    # perm_calibration drop its epsilon_result, and then this one is stale.
    result = getattr(wizard, "epsilon_result", None)
    if result is None or result is not wizard.perm_calibration.epsilon_result:
        result = None
        try:
            result = wizard.perm_calibration.compute_epsilon()
        except Exception as exc:  # noqa: BLE001
            logger.error("[result_screen] compute_epsilon failed: %s", exc)
        wizard.epsilon_result = result

    # Left half: sidebar + summary (same structure as standard_screen)
    left_half_layout = QHBoxLayout()
    left_half_layout.setContentsMargins(0, 0, 0, 0)
    left_half_layout.setSpacing(8)
    left_half_layout.addWidget(build_step_sidebar(wizard, descriptor, texts), stretch=0)

    # --- Middle: summary + warnings + intermediate data ------------------ #
    mid = QVBoxLayout()
    mid.setContentsMargins(8, 8, 8, 8)
    if result is None:
        msg = QLabel(rtexts.get(
            "compute_failed",
            "Could not compute permittivity. Check the calibration measurements.",
        ))
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #d62728; font-size: 14px;")
        mid.addWidget(msg)
        mid.addStretch(1)
    else:
        _build_summary(wizard, mid, result, rtexts)
        _build_sources(wizard, mid, rtexts)
        _build_warnings(wizard, mid, result, rtexts)
        _build_processing(wizard, mid, result, rtexts)
        # _build_intermediate is called after right half so it gets manager/ax/canvas

    mid_container = QWidget()
    mid_container.setLayout(mid)
    # The wizard has a fixed size: the column scrolls vertically instead of
    # squeezing its widgets, so long texts or a small screen never overlap.
    mid_scroll = QScrollArea()
    mid_scroll.setWidgetResizable(True)
    mid_scroll.setFrameShape(QFrame.Shape.NoFrame)
    mid_scroll.setWidget(mid_container)
    left_half_layout.addWidget(mid_scroll, stretch=1)

    left_half = QWidget()
    left_half.setLayout(left_half_layout)

    # Right half: epsilon chart — same position/size as Smith chart in other steps
    right = QVBoxLayout()
    right.setContentsMargins(8, 4, 8, 4)
    if result is not None:
        manager = EpsilonChartManager()
        real_label = rtexts.get("real_label", r"$\varepsilon_r'$")
        loss_label = rtexts.get("loss_label", r"$\varepsilon_r''$")
        title = rtexts.get("chart_title", r"$\varepsilon_r$" + " — {sample}").format(
            sample=_sample_name(wizard, rtexts))
        fig, ax, canvas = manager.create_wizard_epsilon_chart(
            result.f_hz, figsize=(6.5, 5), container_layout=right,
            title=title, real_label=real_label, loss_label=loss_label,
        )
        manager.update_epsilon_curves(
            ax, result.f_hz, result.eps_selected, canvas=None,
            autoscale=False,
        )
        _mark_low_sensitivity(ax, result, rtexts)
        # Unreliable points stay drawn but never set the scale.
        limits = scale_limits(result.eps_selected, usable_band_of(result)[0])
        if limits is not None:
            ax.set_ylim(limits)
        canvas.draw()
        fixed_ylim = ax.get_ylim()
        wizard.result_epsilon_manager = manager

        # The intermediate block (degree-5 equation, roots, branch override)
        # only makes sense for the full technique: the simplified one is a
        # closed formula with a single curve and nothing to override.
        if isinstance(result, SimplifiedEpsilonResult):
            _build_simplified_note(mid, result, rtexts)
            _build_extend_to_full(wizard, mid, rtexts)
        else:
            _build_intermediate(mid, result, rtexts, manager, ax, canvas, fixed_ylim)
        mid.addStretch(1)

    right_half = QWidget()
    right_half.setLayout(right)

    # Two equal halves — sidebar stays in the same position as every other step
    columns = QHBoxLayout()
    columns.setContentsMargins(0, 0, 0, 0)
    columns.setSpacing(0)
    columns.addWidget(left_half, stretch=1)
    columns.addWidget(right_half, stretch=1)

    container = QWidget()
    container.setLayout(columns)

    right_half.setFixedWidth(max(300, (getattr(wizard, "_wiz_w", 1300) - 40) // 2))
    _chart_filter = _HalfWidthFilter(right_half, container)
    container.installEventFilter(_chart_filter)

    wizard.content_layout.addWidget(container, stretch=1)

    wizard.next_button.setEnabled(True)
    _setup_save_calibration_button(wizard, rtexts)


def _setup_save_calibration_button(wizard, rtexts):
    """Show the bottom-bar save-calibration button and wire it up for this result session."""
    from PySide6.QtWidgets import QMessageBox

    btn = getattr(wizard, "save_calibration_button", None)
    cal = getattr(wizard, "perm_calibration", None)
    if btn is None or cal is None:
        return

    btn.setText(rtexts.get("save_kit_button", "💾  Save calibration"))
    btn.setStyleSheet(
        "QPushButton { font-size: 13px; background-color: #4CAF50; color: white;"
        " font-weight: bold; border-radius: 4px; padding: 0 14px; }"
        " QPushButton:hover { background-color: #388E3C; }"
        " QPushButton:pressed { background-color: #2E7D32; }"
    )

    try:
        btn.clicked.disconnect()
    except RuntimeError:
        pass

    def _on_save():
        dlg = _SaveCalibrationDialog(wizard, rtexts, cal)
        dlg.exec()

    btn.clicked.connect(_on_save)
    btn.setVisible(True)


class _SaveCalibrationDialog:
    """Dialog that lets the user choose internal save or ZIP export."""

    def __init__(self, wizard, rtexts, cal, ui_parent=None):
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
            QCheckBox, QDialogButtonBox, QLabel,
        )
        from datetime import datetime as _dt

        self._wizard = wizard
        self._rtexts = rtexts
        self._cal = cal
        self._ui_parent = ui_parent if ui_parent is not None else wizard

        default_name = (
            f"cal_{getattr(wizard, 'selected_technique_id', 'cal')}"
            f"_{_dt.now().strftime('%Y%m%d_%H%M%S')}"
        )

        self._dlg = QDialog(self._ui_parent)
        self._dlg.setWindowTitle(rtexts.get("save_kit_dialog_title", "Save calibration kit"))
        self._dlg.setMinimumWidth(420)

        layout = QVBoxLayout(self._dlg)
        layout.setSpacing(10)

        layout.addWidget(QLabel(rtexts.get("save_kit_name_label", "Kit name:")))
        self._name_edit = QLineEdit(default_name)
        layout.addWidget(self._name_edit)

        self._chk_internal = QCheckBox(
            rtexts.get("save_kit_internal_radio", "Save internally (appears in the welcome dropdown)")
        )
        self._chk_internal.setChecked(True)
        self._chk_zip = QCheckBox(
            rtexts.get("save_kit_zip_radio", "Export as .charpkg file (for sharing)")
        )
        layout.addWidget(self._chk_internal)
        layout.addWidget(self._chk_zip)

        zip_hint = QLabel(rtexts.get(
            "save_kit_zip_hint",
            "Creates a folder with a .charpkg (importable in the app) and a .zip (openable with any archive tool)."
        ))
        zip_hint.setWordWrap(True)
        zip_hint.setStyleSheet("font-size: 11px; color: #888888; font-style: italic; margin-left: 20px;")
        layout.addWidget(zip_hint)

        self._btn_ok = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._btn_ok.button(QDialogButtonBox.StandardButton.Ok).setText(rtexts.get("save_kit_ok", "Save"))
        self._btn_ok.button(QDialogButtonBox.StandardButton.Cancel).setText(rtexts.get("save_kit_cancel", "Cancel"))
        self._btn_ok.accepted.connect(self._on_accepted)
        self._btn_ok.rejected.connect(self._dlg.reject)
        layout.addWidget(self._btn_ok)

        def _update_ok():
            self._btn_ok.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                self._chk_internal.isChecked() or self._chk_zip.isChecked()
            )
        self._chk_internal.toggled.connect(_update_ok)
        self._chk_zip.toggled.connect(_update_ok)

    def exec(self):
        self._dlg.exec()

    def _on_accepted(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        display_name = self._name_edit.text().strip()
        if not display_name:
            self._dlg.reject()
            return

        slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in display_name)
        wizard = self._wizard
        rtexts = self._rtexts
        cal = self._cal
        tech_id = getattr(wizard, "selected_technique_id", None) or ""
        temp_c = getattr(wizard, "temperature_c", 25.0)
        device = str(getattr(wizard, "vna_device", "") or "")

        if not tech_id:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                wizard,
                "Cannot save",
                "The active session has no technique selected. "
                "Return to the wizard and complete a full measurement first.",
            )
            return

        p = self._ui_parent
        any_ok = False

        if self._chk_internal.isChecked():
            try:
                calibration_store.save_calibration(
                    name=slug, display_name=display_name, cal=cal,
                    technique_id=tech_id, temperature_c=temp_c, device_name=device,
                )
                any_ok = True
                QMessageBox.information(
                    p,
                    rtexts.get("save_kit_success_title", "Calibration saved"),
                    rtexts.get("save_kit_success_internal", "Calibration '{name}' saved to the local library.").format(name=display_name),
                )
            except Exception as exc:
                QMessageBox.critical(p, rtexts.get("save_kit_fail_title", "Save failed"), str(exc))

        if self._chk_zip.isChecked():
            dest_dir = QFileDialog.getExistingDirectory(
                p, rtexts.get("save_kit_dialog_title", "Export calibration — choose folder"),
                str(__import__("pathlib").Path.home()),
            )
            if dest_dir:
                try:
                    out_folder = calibration_store.export_calibration(
                        dest_dir=dest_dir, slug=slug, display_name=display_name, cal=cal,
                        technique_id=tech_id, temperature_c=temp_c, device_name=device,
                    )
                    any_ok = True
                    QMessageBox.information(
                        p,
                        rtexts.get("save_kit_success_title", "Calibration saved"),
                        rtexts.get("save_kit_success_zip", "Calibration exported to:\n{path}").format(path=out_folder),
                    )
                except Exception as exc:
                    QMessageBox.critical(p, rtexts.get("save_kit_fail_title", "Save failed"), str(exc))

        if any_ok:
            self._dlg.accept()


def _sample_name(wizard, rtexts):
    return (getattr(wizard, "unknown_liquid_name", "") or "").strip() or rtexts.get(
        "default_sample", "the unknown liquid"
    )


def _usable_f_min(result):
    """Start of the usable band from the sensitivity check, or None (whole sweep)."""
    return usable_band_of(result)[1]


def _build_summary(wizard, layout, result, rtexts):
    # eps'' = -Im(eps); gaps are NaN in both columns and ignored below.
    eps_real, eps_loss = permittivity_columns(result.eps_selected)
    sample = _sample_name(wizard, rtexts)
    # Unreliable points stay out of the medians (they stay on the chart,
    # shaded, and in every export).
    usable, f_min = usable_band_of(result)
    in_band = usable if usable is not None else np.ones(eps_real.shape, bool)
    if not np.any(np.isfinite(eps_real[in_band])):
        in_band = np.ones(eps_real.shape, bool)
        f_min = None
    if np.any(np.isfinite(eps_real)):
        # Median, not mean: robust to a few outlier points (a root on the
        # wrong branch, a noisy band edge) that would drag a mean away from
        # the bulk of the sweep.
        re_median = float(np.nanmedian(eps_real[in_band]))
        tand_all = loss_tangent(eps_real, eps_loss)[in_band]
        tand_ok = tand_all[np.isfinite(tand_all)]
        tand = float(np.median(tand_ok)) if tand_ok.size else float("nan")
        text = rtexts.get(
            "summary_template",
            "Sample: {sample}\nMedian ε′ = {er_real:.2f}\nMedian loss tangent = {tand:.3f}",
        ).format(sample=sample, er_real=re_median, tand=tand)

        # Both solvers flag eps'' < 0 or eps' < 1 (below vacuum).
        mask = nonpassive_mask_of(result)
        n_flagged = (int(np.count_nonzero(mask & np.isfinite(eps_real)))
                     if mask is not None else 0)
    else:
        text = rtexts.get(
            "all_gap",
            "No physically valid permittivity could be selected on this sweep.",
        )
        n_flagged = 0
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("font-size: 15px;")
    layout.addWidget(label)

    if f_min is not None:
        band_lbl = QLabel(rtexts.get(
            "summary_usable_band",
            "Medians over the reliable points (≥ {fmin}); the unreliable ones are "
            "left out: see warnings",
        ).format(fmin=_fmt_hz(f_min)))
        band_lbl.setWordWrap(True)
        band_lbl.setStyleSheet("font-size: 12px;")
        layout.addWidget(band_lbl)

    if n_flagged:
        # Own, smaller line: it must fit in one row of the narrow column.
        flag_lbl = QLabel(rtexts.get(
            "summary_nonpassive",
            "Non-physical (ε″ < 0 or ε′ < 1): {n} of {total}, flagged",
        ).format(n=n_flagged, total=eps_real.size))
        flag_lbl.setWordWrap(True)
        flag_lbl.setStyleSheet("font-size: 12px;")
        layout.addWidget(flag_lbl)


def _build_sources(wizard, layout, rtexts):
    """Compact popup button showing data source per standard."""
    cal = getattr(wizard, "perm_calibration", None)
    if cal is None:
        return

    _DISPLAY = {
        "open":  "Open",
        "short": "Short",
        "ref1":  "Ref 1",
        "ref2":  "Ref 2",
        "dut":   "DUT",
    }
    prefix = rtexts.get("source_preset_prefix", "preset:")
    src_measured = rtexts.get("source_measured", "measured")
    src_imported = rtexts.get("source_imported", "imported")

    rows = []
    for key, label in _DISPLAY.items():
        src = cal.get_source(key)
        if src is None:
            continue
        if src == "measured":
            tag = src_measured
        elif src == "imported":
            tag = src_imported
        elif src.startswith("preset:"):
            tag = prefix + src[len("preset:"):]
        else:
            tag = src
        replaced = _despike_replaced_hz(cal, key)
        if replaced:
            tag += " · " + rtexts.get(
                "source_despiked", "{n} spike(s) replaced in the computation ({freqs})"
            ).format(n=len(replaced), freqs=", ".join(_fmt_hz(f) for f in replaced[:3])
                     + (" …" if len(replaced) > 3 else ""))
        rows.append((label, tag))

    if not rows:
        return

    title = rtexts.get("sources_title", "Data sources")

    def _show_popup():
        dlg = QDialog(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        dlg.setStyleSheet(
            "QDialog { background: #f0f4ff; border: 1px solid #7aa0e0; border-radius: 6px; }"
        )
        v = QVBoxLayout(dlg)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(4)
        hdr = QLabel(f"<b>{title}</b>")
        hdr.setStyleSheet("font-size: 12px; color: #2a4a8a;")
        v.addWidget(hdr)
        for label, tag in rows:
            item = QLabel(f"• {label}: {tag}")
            item.setStyleSheet("font-size: 11px; color: #1a3060;")
            v.addWidget(item)
        dlg.adjustSize()
        dlg.move(btn.mapToGlobal(btn.rect().bottomLeft()))
        dlg.exec()

    btn = QPushButton(f"📋  {title}")
    btn.setStyleSheet(
        "QPushButton { background: transparent; color: #4a6fa5; border: none;"
        " font-size: 12px; padding: 2px 0px; text-align: left; }"
        "QPushButton:hover { color: #2a4a8a; text-decoration: underline; }"
    )
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.clicked.connect(_show_popup)
    layout.addSpacing(4)
    layout.addWidget(btn)


def _detect_branch_jumps(result, threshold=0.50):
    """Return warning strings for relative jumps > threshold in Re(εr) between adjacent points."""
    try:
        eps = result.eps_selected
        f_hz = result.f_hz
        re = np.real(eps)
        valid = np.isfinite(re) & (re > 0)
        if valid.sum() < 2:
            return []
        idx = np.where(valid)[0]
        re_v = re[idx]
        jumps = np.abs(np.diff(re_v)) / np.maximum(np.abs(re_v[:-1]), 1e-12)
        bad = np.where(jumps > threshold)[0]
        if len(bad) == 0:
            return []
        msgs = []
        for i in bad[:3]:
            f_mhz = f_hz[idx[i]] / 1e6
            msgs.append(
                f"Branch jump >{int(threshold*100)}% at {f_mhz:.1f} MHz "
                f"(Re εr: {re_v[i]:.2f} → {re_v[i+1]:.2f}) — possible wrong branch"
            )
        if len(bad) > 3:
            msgs.append(f"…and {len(bad)-3} more branch jumps")
        return msgs
    except Exception:
        return []


def _despike_replaced_hz(cal, key):
    """Frequencies spike removal replaced in ``key`` in the last computation."""
    getter = getattr(cal, "get_processing", None)
    proc = (getter(key) or {}).get("despike") if callable(getter) else None
    return list((proc or {}).get("replaced_hz") or [])


def _build_warnings(wizard, layout, result, rtexts):
    warns = list(result.warnings) + list(getattr(wizard, "temperature_warnings", []) or [])
    warns += _detect_branch_jumps(result)
    if not warns:
        return

    def _show_popup():
        dlg = QDialog(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        dlg.setStyleSheet(
            "QDialog { background: #fffbf0; border: 1px solid #e8c84a; border-radius: 6px; }"
        )
        v = QVBoxLayout(dlg)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(4)
        hdr = QLabel(rtexts.get("warnings_title", "Warnings:"))
        hdr.setStyleSheet("font-weight: bold; color: #b8860b; font-size: 12px;")
        v.addWidget(hdr)
        # Every warning, scrolled: the quality checks come first and their
        # messages are long, so a fixed cut used to hide the solver's ones.
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 4, 0)
        body_layout.setSpacing(6)
        for w in warns:
            item = QLabel(f"• {w}")
            item.setWordWrap(True)
            item.setStyleSheet("color: #7a5800; font-size: 11px;")
            item.setFixedWidth(420)
            body_layout.addWidget(item)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        scroll.setWidget(body)
        body.adjustSize()
        scroll.setFixedWidth(440)
        scroll.setFixedHeight(min(420, body.sizeHint().height() + 4))
        v.addWidget(scroll)
        dlg.adjustSize()
        dlg.move(btn.mapToGlobal(btn.rect().bottomLeft()))
        dlg.exec()

    n = len(warns)
    btn = QPushButton(f"⚠  {n} warning{'s' if n > 1 else ''}")
    btn.setStyleSheet(
        "QPushButton { background: transparent; color: #b8860b; border: none;"
        " font-size: 12px; padding: 2px 0px; text-align: left; }"
        "QPushButton:hover { color: #7a5800; text-decoration: underline; }"
    )
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.clicked.connect(_show_popup)
    layout.addSpacing(4)
    layout.addWidget(btn)


def _build_processing(wizard, layout, result, rtexts):
    """
    Spike-removal toggle plus what it did in this computation.

    EN: Spike removal runs on copies when computing (the stored sweeps stay
        as measured/imported). Unticking it recomputes with the sweeps as
        they are; the line under the box lists every replaced point and the
        outliers left alone because several sweeps share them.
    ES: La remocion de picos corre sobre copias al calcular (los barridos
        guardados quedan como se midieron/importaron). Destildarla recalcula
        con los barridos tal cual; la linea bajo la casilla lista cada punto
        reemplazado y los outliers que se dejan porque los comparten varios
        barridos.
    """
    cal = getattr(wizard, "perm_calibration", None)
    if cal is None or not hasattr(cal, "set_despike_enabled"):
        return
    record = (getattr(result, "processing", None) or {}).get("despike") or {}
    enabled = bool(getattr(cal, "despike_enabled", True))

    chk = QCheckBox(rtexts.get("despike_label", "Remove isolated spikes (noise-based)"))
    chk.setChecked(enabled)
    chk.setToolTip(rtexts.get(
        "despike_tooltip",
        "A point is replaced by the mean of its neighbours only if its second "
        "difference is more than 6× the local noise, larger than the S11 error "
        "budget (0.001) and isolated. An outlier shared by several sweeps at the "
        "same frequency is an instrument artefact that the calibration cancels, so "
        "it is left alone. The stored sweeps are never modified.",
    ))
    chk.setStyleSheet("font-size: 12px;")

    names = {"open": "Open", "short": "Short", "ref1": "Ref 1", "ref2": "Ref 2", "dut": "DUT"}
    replaced, shared = [], set()
    for key, proc in (record.get("sweeps") or {}).items():
        for f in proc.get("replaced_hz") or []:
            replaced.append(f"{names.get(key, key)} @ {_fmt_hz(f)}")
        shared.update(proc.get("kept_common_hz") or [])
    if not enabled:
        detail = rtexts.get("despike_off", "Off: the sweeps are used as measured.")
    elif replaced:
        detail = rtexts.get("despike_replaced", "Replaced: {items}").format(items="; ".join(replaced))
    else:
        detail = rtexts.get("despike_none", "No isolated spike found.")
    if enabled and shared:
        detail += "  " + rtexts.get(
            "despike_shared", "Left alone (shared by several sweeps): {freqs}"
        ).format(freqs=", ".join(_fmt_hz(f) for f in sorted(shared)))
    detail_lbl = QLabel(detail)
    detail_lbl.setWordWrap(True)
    detail_lbl.setStyleSheet(f"font-size: 11px; color: {_secondary_text_color()};")

    def _on_toggled(checked):
        from PySide6.QtCore import QTimer
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.steps_manager import (
            update_step_screen,
        )
        cal.set_despike_enabled(checked)
        wizard.epsilon_result = None
        # Rebuild after this slot returns: the rebuild destroys this checkbox.
        QTimer.singleShot(0, lambda: update_step_screen(wizard))

    chk.toggled.connect(_on_toggled)
    layout.addSpacing(4)
    layout.addWidget(chk)
    layout.addWidget(detail_lbl)


def _mark_low_sensitivity(ax, result, rtexts):
    """Shade the band below the usable start (sensitivity check) on ``ax``."""
    f_min = _usable_f_min(result)
    if f_min is None:
        return
    shade_unusable_band(ax, float(result.f_hz[0]), f_min,
                        label=rtexts.get("low_sensitivity_label", "unreliable"))
    ax.legend(loc="upper right")


_NAN_C = complex(np.nan, np.nan)


def _greedy_assign(prev_vals: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    """
    One-to-one assignment of the finite ``candidates`` to branch slots.

    Slots with a finite previous value are continued first, closest pairs
    first. Candidates left over (a root that appears mid-sweep, or more roots
    than continued slots) go to the free slots, highest Re(eps) first and
    preferring slots that never held a value -- so no finite candidate is
    ever dropped while there is a free slot.
    """
    n = len(prev_vals)
    assigned = np.full(n, _NAN_C, dtype=complex)
    cands = [complex(c) for c in candidates if np.isfinite(c)]

    pairs = sorted(
        (abs(c - prev_vals[s]), s, k)
        for s in range(n) if np.isfinite(prev_vals[s])
        for k, c in enumerate(cands)
    )
    slot_used = [False] * n
    cand_used = [False] * len(cands)
    for _, s, k in pairs:
        if not slot_used[s] and not cand_used[k]:
            assigned[s] = cands[k]
            slot_used[s] = cand_used[k] = True

    leftovers = sorted((c for k, c in enumerate(cands) if not cand_used[k]),
                       key=lambda c: -c.real)
    # Never-used slots first (stable sort keeps index order within each group).
    free = sorted((s for s in range(n) if not slot_used[s]),
                  key=lambda s: bool(np.isfinite(prev_vals[s])))
    if len(leftovers) > len(free):
        logger.warning("[result_screen] %d candidate(s) without a free branch slot",
                       len(leftovers) - len(free))
    for s, c in zip(free, leftovers):
        assigned[s] = c
    return assigned


def _track_all_branches(result) -> np.ndarray:
    """
    Arrange every root into 5 branch columns for the manual override.

    Column 0 = eps_selected (algorithm auto). Columns 1-4 = the other finite
    candidates, continued by nearest neighbour against the LAST value each
    branch had (so a branch survives a frequency where its root is missing)
    and with new roots placed in free columns: at every solved frequency each
    finite candidate appears in exactly one column. Gap frequencies (the
    solver declined the point) stay blank in every column. Returns shape
    (n_freq, 5), complex(nan, nan) where a column has no value.
    """
    n_freq = len(result.f_hz)
    tracked = np.full((n_freq, 5), _NAN_C, dtype=complex)
    tracked[:, 0] = result.eps_selected
    last_seen = np.full(4, _NAN_C, dtype=complex)

    for i in range(n_freq):
        sel_idx = int(result.selected_index[i])
        if sel_idx < 0:
            continue  # gap: no auto value and no override offered either

        remaining = np.delete(np.asarray(result.eps_candidates[i], dtype=complex), sel_idx)
        tracked[i, 1:] = _greedy_assign(last_seen, remaining)
        hit = np.isfinite(tracked[i, 1:])
        last_seen[hit] = tracked[i, 1:][hit]

    return tracked


def _build_simplified_note(layout, result, rtexts):
    """Method note shown instead of the quintic block for the simplified technique."""
    layout.addSpacing(10)
    title = QLabel(rtexts.get("simplified_title", "Simplified method (single reference)"))
    title.setStyleSheet("font-weight: bold; font-size: 13px;")
    layout.addWidget(title)

    note = QLabel(rtexts.get(
        "simplified_note",
        "ε_r comes from the closed-form cross-ratio formula (Higa 2016, eq. 18) using "
        "Short, Open (air, ε=1.0006) and one reference liquid — there are no candidate "
        "roots and nothing to override. The probe's radiation term is neglected, so "
        "accuracy degrades toward high frequency; for best accuracy use the full "
        "two-liquid method.",
    ))
    note.setWordWrap(True)
    note.setStyleSheet("font-size: 11px; color: #555555; padding: 4px 0px 6px 0px;")
    layout.addWidget(note)

    ref_line = QLabel(rtexts.get(
        "simplified_reference", "Reference liquid: {ref}  ·  T = {temp:.1f} °C"
    ).format(ref=result.ref_liquid_key, temp=result.temperature_c))
    ref_line.setStyleSheet("font-size: 11px; color: #555555;")
    layout.addWidget(ref_line)


_FULL_TECHNIQUE_ID = "open_coax_liquids"


def _build_extend_to_full(wizard, layout, rtexts):
    """Button that upgrades a simplified session to the full two-liquid method.

    EN: The simplified technique shares its standard keys (open/short/ref1/dut)
        with the full one, so everything already measured carries over: the
        wizard only needs the SECOND reference liquid. Clicking switches the
        active technique and lands on the ref2 step; the result then recomputes
        with the degree-5 solver, seeded by the simplified curve just shown.

    ES: La tecnica simplificada comparte las claves de patrones
        (open/short/ref1/dut) con la completa, asi que todo lo ya medido se
        conserva: al asistente solo le falta el SEGUNDO liquido de referencia.
        El click cambia la tecnica activa y cae en el paso de ref2; el
        resultado se recalcula con el solver de grado 5, sembrado por la curva
        simplificada recien mostrada.
    """
    from PySide6.QtWidgets import QMessageBox

    layout.addSpacing(12)
    btn = QPushButton(rtexts.get("extend_button", "Extend to full method (2nd liquid)…"))
    btn.setFixedHeight(30)
    btn.setStyleSheet(
        "QPushButton { color: #4da6ff; border: 1px solid #4da6ff;"
        " border-radius: 4px; padding: 0 14px; font-size: 12px; }"
        " QPushButton:hover { background: #0a1828; }"
    )
    layout.addWidget(btn, alignment=Qt.AlignLeft)

    def _on_extend():
        from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import (
            get as get_technique,
        )
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.session_liquids import (
            liquid_keys, set_liquid_key,
        )

        try:
            full = get_technique(_FULL_TECHNIQUE_ID)
        except KeyError:
            logger.error("[result_screen] full technique '%s' not registered", _FULL_TECHNIQUE_ID)
            return

        # ref2 default: IPA, unless ref1 already is IPA (they must differ).
        ref1_liquid = liquid_keys(wizard).get("ref1") or "water"
        ref2_liquid = "ipa" if ref1_liquid != "ipa" else "water"

        ref2_index = next(
            (i + 1 for i, s in enumerate(full.steps)
             if s.standard is not None and s.standard.key == "ref2"),
            None,
        )
        if ref2_index is None:
            logger.error("[result_screen] full technique has no ref2 step")
            return

        answer = QMessageBox.question(
            wizard,
            rtexts.get("extend_title", "Extend to full method?"),
            rtexts.get(
                "extend_msg",
                "Everything measured so far (Open, Short, {ref1} and the unknown) is "
                "kept. The wizard switches to the full two-liquid technique and only "
                "the second reference liquid ({ref2}) remains to be measured or "
                "imported — you can change it in the Configuration step.\n\n"
                "The result will be recomputed with the degree-5 solver, seeded by "
                "the simplified curve shown here.\n\nContinue?",
            ).format(ref1=ref1_liquid, ref2=ref2_liquid),
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        # A ref2 left over from an earlier full-technique run in this session
        # belongs to whatever liquid ref2 had then; read as ref2_liquid it
        # would give a wrong result, so it is measured again.
        if (wizard.perm_calibration.is_standard_measured("ref2")
                and liquid_keys(wizard).get("ref2") != ref2_liquid):
            wizard.perm_calibration.clear_measurement("ref2")
        set_liquid_key(wizard, "ref2", ref2_liquid)
        if not wizard.perm_calibration.set_reference_liquids(ref1_liquid, ref2_liquid):
            logger.error("[result_screen] could not set reference liquids %s/%s",
                         ref1_liquid, ref2_liquid)
            return

        # Switch the active technique; measurements live in perm_calibration
        # (shared standard keys), so nothing is lost. The stale simplified
        # result must not be reused by the full technique's result screen
        # (set_reference_liquids already dropped the calibration's copy).
        wizard.selected_technique_id = _FULL_TECHNIQUE_ID
        methods = load_text("characterization_methods.json").get("methods", {})
        wizard.selected_method = methods.get(_FULL_TECHNIQUE_ID, {}).get(
            "title", _FULL_TECHNIQUE_ID)
        wizard.epsilon_result = None

        logger.info("[result_screen] extended to '%s'; jumping to ref2 (step %d)",
                    _FULL_TECHNIQUE_ID, ref2_index)
        wizard.current_step = ref2_index
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.steps_manager import (
            update_step_screen,
        )
        update_step_screen(wizard)

    btn.clicked.connect(_on_extend)


# Marks at the start of each root line of the intermediate block (both glyphs
# are in Consolas, the box font, with the same advance as any other char).
_MARK_SELECTED = "►"
_MARK_EXTRANEOUS = "×"


def _secondary_text_color() -> str:
    """Muted text colour readable on the current theme's background."""
    try:
        theme = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve(),
        )
        is_dark = not theme.value("Dark_Light/is_dark_mode", False, type=bool)
    except Exception:  # noqa: BLE001 - styling only, never block the screen
        is_dark = True
    # Dark: the theme's placeholder grey; light: the previous #555555.
    return "#8888aa" if is_dark else "#555555"


def _bulleted_tooltip(title: str, text: str) -> str:
    """Rich-text tooltip: bold title and one bullet per " · "-separated item."""
    items = [part.strip() for part in text.split("·") if part.strip()]
    body = "<br>".join("• " + html.escape(item) for item in items)
    return f"<b>{html.escape(title)}</b><br>{body}"


def _fit_height_to_text(box: QPlainTextEdit) -> None:
    """Make ``box`` exactly as tall as its text, measured from its own font.

    With NoWrap every block is one visual line; room is kept for the
    horizontal scrollbar a long line may need. The column around it scrolls,
    so a tall box can never cover the widgets below.
    """
    box.ensurePolished()  # the stylesheet font must be in effect before measuring
    n_lines = max(1, box.document().blockCount())
    height = (n_lines * box.fontMetrics().lineSpacing()
              + 2 * int(box.document().documentMargin())
              + 2 * box.frameWidth()
              + box.horizontalScrollBar().sizeHint().height()
              + 2)
    box.setFixedHeight(height)


def _build_intermediate(layout, result, rtexts, manager=None, ax=None, canvas=None, fixed_ylim=None):
    """Copyable block: general 5th-order equation + per-frequency coefficients."""
    layout.addSpacing(10)
    title = QLabel(rtexts.get("intermediate_title", "Intermediate data (5th-order equation)"))
    title.setStyleSheet("font-weight: bold; font-size: 13px;")
    layout.addWidget(title)

    # Short criterion on screen; the full description goes in the tooltip.
    crit_title = rtexts.get("criterion_title", "Branch selection criterion")
    crit_text  = rtexts.get(
        "criterion_text",
        "Principal-branch roots, Re(√ε) > 0  ·  Anchor: smallest-|Gn| point"
        " unambiguously matched to the simplified curve  ·  then continuity in"
        " frequency  ·  ε″ < 0 or ε′ < 1 kept and flagged  ·  Gaps: indistinguishable"
        " references, no valid root, ε′ ≤ 0 or ambiguous step",
    )
    crit_tip = rtexts.get(
        "criterion_tooltip",
        "Candidates: principal-branch roots only, Re(√ε) > 0"
        "  ·  Anchor: among the frequencies where the root closest to the"
        " simplified-method curve (available as the cross-check overlay) is"
        " unambiguous, the one with the smallest |Gn| (running median, confirmed by"
        " its neighbours, so a glitch cannot take it), where that estimate is most"
        " reliable; only where that curve has no value is the cruder Gn → 0 limit"
        " used instead"
        "  ·  From the anchor the sweep is followed in frequency, each point taking"
        " the root closest to the last selected one; a point that jumps away from"
        " its neighbours (|Gn| over 3× its running median, or the estimate over"
        " 25 % with an ambiguous step: a glitch) keeps its root but does not steer"
        "  ·  Points with ε″ < 0 (non-passive, attributable to noise) or 0 < ε′ < 1"
        " (below vacuum, a measurement error) are kept and flagged, not discarded"
        "  ·  Gaps: reference liquids indistinguishable (|S₁₁ʳ¹ − S₁₁ʳ²| < 0.01),"
        " no principal-branch root, a selected root with ε′ ≤ 0, or no root singled"
        " out by either continuity or the estimate",
    )
    # Rich text (for the bold title): escape the body, or Qt cuts it at "ε″ < 0".
    crit_lbl = QLabel(f"<b>{html.escape(crit_title)}:</b> {html.escape(crit_text)}")
    crit_lbl.setWordWrap(True)
    crit_lbl.setToolTip(_bulleted_tooltip(crit_title, crit_tip))
    crit_lbl.setStyleSheet(
        f"font-size: 11px; color: {_secondary_text_color()}; padding: 4px 0px 6px 0px;"
    )
    layout.addWidget(crit_lbl)

    # Frequency selector (decimated).
    n = len(result.f_hz)
    stride = max(1, n // _MAX_FREQ_CHOICES)
    indices = list(range(0, n, stride))
    selector = QComboBox()
    for i in indices:
        selector.addItem(_fmt_hz(result.f_hz[i]), i)
    # Default to a representative (middle) frequency.
    selector.setCurrentIndex(len(indices) // 2)
    row = QHBoxLayout()
    row.addWidget(QLabel(rtexts.get("frequency_label", "Frequency:")))
    row.addWidget(selector, stretch=1)
    row_w = QWidget()
    row_w.setLayout(row)
    layout.addWidget(row_w)

    text_box = QPlainTextEdit()
    text_box.setReadOnly(True)
    # No wrap: a wrapped root line pushed its tag onto the next line, next to
    # another root. Long lines scroll horizontally instead.
    text_box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    text_box.setStyleSheet(
        "font-family: Consolas, monospace; font-size: 12px;"
        " background-color: #ffffff; color: #1a1a1a; border: 1px solid #cccccc;"
    )
    layout.addWidget(text_box)

    def render(idx_in_combo):
        i = selector.itemData(idx_in_combo)
        if i is None:
            return
        text_box.setPlainText(_format_equation(result, int(i), rtexts))
        _fit_height_to_text(text_box)

    selector.currentIndexChanged.connect(render)
    render(selector.currentIndex())

    # --- Branch override + Gn popup ---
    if manager is None or ax is None or canvas is None:
        return

    tracked = _track_all_branches(result)  # shape (n_freq, 5)

    layout.addSpacing(10)

    cc_label = rtexts.get("crosscheck_tag", "simplified")
    _cc_state = [False]  # shared state for the cross-check checkbox across popup openings

    chk = QCheckBox(rtexts.get("branch_override_label", "Override automatic branch selection"))
    chk.setVisible(False)
    layout.addWidget(chk)

    combo_container = QWidget()
    combo_container.setVisible(False)
    combo_row = QHBoxLayout(combo_container)
    combo_row.setContentsMargins(4, 4, 0, 0)
    combo_row.addWidget(QLabel(rtexts.get("branch_label", "Branch:")))
    branch_combo = QComboBox()
    n_listed = 0
    for b in range(5):
        branch_data = tracked[:, b]
        finite = np.isfinite(branch_data)
        if b > 0 and not np.any(finite):
            continue  # no candidate ever landed in this column: nothing to offer
        n_listed += 1
        if np.any(finite):
            median_real = float(np.median(np.real(branch_data[finite])))
            suffix = f"ε′ ≈ {median_real:.2f}"
        else:
            suffix = "no valid data"
        label = f"Branch 1 (Auto) — {suffix}" if b == 0 else f"Branch {n_listed} — {suffix}"
        branch_combo.addItem(label, b)  # item data = column in ``tracked``
    branch_combo.setCurrentIndex(0)
    combo_row.addWidget(branch_combo, stretch=1)
    layout.addWidget(combo_container)

    def _redraw():
        """Single redraw path honouring BOTH toggles (branch override + cross-check)."""
        cc = result.eps_crosscheck if _cc_state[0] else None
        if chk.isChecked():
            b = branch_combo.itemData(branch_combo.currentIndex())
            b = 0 if b is None else int(b)
            eps_curve = tracked[:, b]
            gray = np.column_stack([tracked[:, j] for j in range(5) if j != b])
            manager.update_epsilon_curves(
                ax, result.f_hz, eps_curve, canvas=None, candidates=gray,
                autoscale=False, crosscheck=cc, crosscheck_label=cc_label,
            )
        else:
            manager.update_epsilon_curves(
                ax, result.f_hz, result.eps_selected, canvas=None,
                autoscale=False, crosscheck=cc, crosscheck_label=cc_label,
            )
        _mark_low_sensitivity(ax, result, rtexts)
        if fixed_ylim is not None:
            ax.set_ylim(fixed_ylim)
        canvas.draw()

    # ── Gn(f) quality chart: popup button (like "Data sources" / "Warnings") ─ #
    def _show_gn_popup():
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

        dlg = QDialog(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        dlg.setStyleSheet(
            "QDialog { background: #1a1a2e; border: 1.5px solid #606070; border-radius: 8px; }"
        )
        v = QVBoxLayout(dlg)
        v.setContentsMargins(14, 12, 14, 14)
        v.setSpacing(6)

        hdr = QLabel(rtexts.get("gn_title", "Calibration quality — |Gn(f)|"))
        hdr.setStyleSheet("font-weight: bold; font-size: 12px; color: #7ab3f5;")
        v.addWidget(hdr)

        hint = QLabel(rtexts.get(
            "gn_hint",
            "Smooth curve → good calibration.  Peaks → suspect standard (typically ref2).",
        ))
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 10px; color: #888888;")
        hint.setMaximumWidth(420)
        v.addWidget(hint)

        gn = result.gn
        f_mhz = result.f_hz / 1e6
        gn_abs = np.abs(gn)

        fig, ax_gn = plt.subplots(figsize=(4.4, 1.8))
        fig.patch.set_facecolor("#1a1a2e")
        ax_gn.set_facecolor("#12122a")

        valid = np.isfinite(gn_abs)
        if np.any(valid):
            ax_gn.plot(f_mhz[valid], gn_abs[valid], color="#7ab3f5", linewidth=1.2)
            median_gn = float(np.nanmedian(gn_abs[valid]))
            threshold = 3.0 * median_gn
            peaks = valid & (gn_abs > threshold)
            if np.any(peaks):
                ax_gn.scatter(f_mhz[peaks], gn_abs[peaks], color="#e05050",
                              s=12, zorder=5, label=rtexts.get("gn_peak_label", "peak"))
                ax_gn.axhline(threshold, color="#e05050", linewidth=0.7,
                              linestyle="--", alpha=0.6)

        ax_gn.set_xlabel("f (MHz)", fontsize=6, color="#aaaaaa")
        ax_gn.set_ylabel("|Gn|", fontsize=6, color="#aaaaaa")
        ax_gn.tick_params(colors="#888888", labelsize=5)
        for spine in ax_gn.spines.values():
            spine.set_edgecolor("#333355")
        fig.tight_layout(pad=0.2)
        fig.subplots_adjust(left=0.10, right=0.98, top=0.95, bottom=0.22)

        canvas_gn = FigureCanvas(fig)
        canvas_gn.setFixedHeight(180)
        canvas_gn.setFixedWidth(430)
        v.addWidget(canvas_gn)
        plt.close(fig)

        if getattr(result, "eps_crosscheck", None) is not None:
            cc_chk_popup = QCheckBox(rtexts.get(
                "crosscheck_label", "Show cross-check (simplified method)"))
            cc_chk_popup.setChecked(_cc_state[0])
            cc_chk_popup.setStyleSheet("color: #cccccc; font-size: 11px;")

            def _on_cc(checked):
                _cc_state[0] = checked
                _redraw()

            cc_chk_popup.toggled.connect(_on_cc)
            v.addWidget(cc_chk_popup)

        dlg.adjustSize()
        _pos = btn_gn.mapToGlobal(btn_gn.rect().topLeft())
        _pos.setY(_pos.y() - dlg.height())
        dlg.move(_pos)
        dlg.exec()

    layout.addSpacing(6)
    btn_gn = QPushButton("📊  " + rtexts.get("gn_title", "Calibration quality — |Gn(f)|"))
    btn_gn.setStyleSheet(
        "QPushButton { background: transparent; color: #7ab3f5; border: none;"
        " font-size: 12px; padding: 2px 0px; text-align: left; }"
        "QPushButton:hover { color: #4da6ff; text-decoration: underline; }"
    )
    btn_gn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_gn.clicked.connect(_show_gn_popup)
    layout.addWidget(btn_gn)

    def _on_check(checked):
        combo_container.setVisible(bool(checked))
        _redraw()

    chk.toggled.connect(_on_check)
    branch_combo.currentIndexChanged.connect(
        lambda _idx: _redraw() if chk.isChecked() else None
    )



def _principal_roots(result, i, x_roots) -> np.ndarray:
    """
    Bool per x root: True for the principal-branch roots the solver offers.

    ``eps_candidates[i]`` keeps the ``np.roots`` order with NaN in the slots
    of the extraneous roots (Re x <= 0, they solve eq. 16 with the radiation
    term's sign flipped). That layout is used when it matches ``x_roots``;
    otherwise the same Re(x) > 0 test is applied to the roots directly.
    """
    by_x = np.real(x_roots) > 0.0
    cands = getattr(result, "eps_candidates", None)
    if cands is None or np.shape(cands)[-1] < x_roots.size:
        return by_x
    slots = np.asarray(cands[i], dtype=complex)[: x_roots.size]
    finite = np.isfinite(slots)
    if np.allclose(slots[finite], np.square(x_roots)[finite], rtol=1e-9, atol=1e-12):
        return finite
    logger.warning("[result_screen] eps_candidates order differs from np.roots at %d; "
                   "using Re(x) > 0", i)
    return by_x


def _format_equation(result, i, rtexts):
    """Text of the intermediate block at frequency index ``i``.

    One line per x root, never wrapped (the box scrolls horizontally), with
    the mark at the START of the line: ``_MARK_SELECTED`` on the selected
    root, ``_MARK_EXTRANEOUS`` on the extraneous ones (Re x <= 0), followed by
    a one-line legend.
    """
    coeffs = result.polynomial_coeffs_at(i)
    eps_sel = result.eps_selected[i]
    lines = []
    lines.extend(rtexts.get(
        "equation_general",
        "General form:  Gn·x^5 + x^2 + third_term = 0\n(x = εr^(1/2),  εr = x^2)",
    ).splitlines())
    lines.append("")
    lines.append(f"@ f = {_fmt_hz(result.f_hz[i])}")
    # Gn is ~1e-5..1e-2: fixed 2 decimals printed it as "-0.00 - 0.00j".
    lines.append(f"  Gn         = {_fmt_c_sci(result.gn[i])}")
    lines.append(f"  third_term = {_fmt_c(result.third_term[i])}")
    if np.all(np.isfinite(coeffs)):
        x_roots = np.roots(coeffs)
        eps_roots = np.square(x_roots)
        principal = _principal_roots(result, i, x_roots)
        with np.errstate(invalid="ignore"):
            is_sel = np.isfinite(eps_sel) & np.isclose(eps_roots, eps_sel, rtol=1e-9, atol=1e-12)
        root_strs = [_fmt_c(r) for r in x_roots]
        col_w = max(len(s) for s in root_strs)
        lines.append("  x roots:")
        for rs, e, ok, sel in zip(root_strs, eps_roots, principal, is_sel):
            mark = _MARK_EXTRANEOUS if not ok else (_MARK_SELECTED if sel else " ")
            lines.append(f"  {mark} {rs.ljust(col_w)} -> εr = {_fmt_c(e)}")
        lines.append("  " + rtexts.get(
            "roots_legend", "{sel} selected   {ext} extraneous (Re x ≤ 0)",
        ).format(sel=_MARK_SELECTED, ext=_MARK_EXTRANEOUS))
    else:
        lines.append("  x roots: " + rtexts.get("no_root", "no physical root")
                     + " (non-finite coefficients at this frequency)")
    lines.append("")
    if np.isfinite(eps_sel):
        lines.append(f"  εr (selected) = {_fmt_c(eps_sel)}")
    else:
        lines.append(f"  εr (selected) = {rtexts.get('no_root', 'no physical root')}")
    return "\n".join(lines)


def _fmt_c(z):
    z = complex(z)
    if not np.isfinite(z.real) or not np.isfinite(z.imag):
        return "nan"
    sign = "+" if z.imag >= 0 else "-"
    return f"{z.real:.2f} {sign} {abs(z.imag):.2f}j"


def _fmt_c_sci(z):
    """Like ``_fmt_c`` in scientific notation, for small values such as Gn."""
    z = complex(z)
    if not np.isfinite(z.real) or not np.isfinite(z.imag):
        return "nan"
    sign = "+" if z.imag >= 0 else "-"
    return f"{z.real:.2e} {sign} {abs(z.imag):.2e}j"


def _fmt_hz(hz):
    hz = float(hz)
    if hz >= 1e9:
        return f"{hz/1e9:.4f} GHz"
    if hz >= 1e6:
        return f"{hz/1e6:.3f} MHz"
    if hz >= 1e3:
        return f"{hz/1e3:.1f} kHz"
    return f"{hz:.0f} Hz"
