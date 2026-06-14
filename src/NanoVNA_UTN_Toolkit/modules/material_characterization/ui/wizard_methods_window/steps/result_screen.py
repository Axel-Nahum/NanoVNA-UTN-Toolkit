"""
Result screen of the characterization wizard.

EN: Runs the calibration + permittivity solver and plots epsilon_r(f): the real
    part (energy storage) and the loss (dissipation), with the other candidate
    root branches drawn faintly. The left column shows a worded summary (using
    the unknown-liquid name), any warnings, and a copyable "intermediate data"
    block: the general 5th-order equation and, for a user-selected frequency,
    the numeric coefficients, the five x-roots and the selected epsilon_r.
    The bottom bar shows an "Export image" button (left of Finish) that saves
    the epsilon_r figure in high quality. Manual per-frequency root override is
    a Stage 2 feature.

ES: Ejecuta la calibracion y el solver de permitividad y grafica epsilon_r(f):
    la parte real (almacenamiento de energia) y la perdida (disipacion), con las
    demas ramas candidatas en tenue. La columna izquierda muestra un resumen en
    palabras (usando el nombre del liquido incognita), los avisos y un bloque de
    "datos intermedios" copiable: la ecuacion general de 5to orden y, para una
    frecuencia elegida, los coeficientes numericos, las cinco raices x y el
    epsilon_r seleccionado. La barra inferior muestra un boton "Exportar imagen"
    (a la izquierda de Finalizar) que guarda la figura de epsilon_r en alta
    calidad. La seleccion manual de raiz por frecuencia es de la Etapa 2.
"""

from __future__ import annotations

import logging

import numpy as np
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget,
)


class _HalfWidthFilter(QObject):
    def __init__(self, target, parent):
        super().__init__(parent)
        self._target = target

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self._target.setFixedWidth(max(300, obj.width() // 2))
        return False

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.charts.epsilon_chart import (
    EpsilonChartManager,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.step_sidebar import (
    build_step_sidebar,
)

logger = logging.getLogger(__name__)

_MAX_FREQ_CHOICES = 200


def build_result_screen(wizard, descriptor, step_def):
    texts = load_text("characterization_wizard.json")
    rtexts = texts.get("result", {})
    wizard.title_label.setText(rtexts.get("title", "Permittivity Result"))

    # Reuse cached result when navigating back/forward without re-measuring.
    # The cache is invalidated (set to None) in _on_measure whenever a new
    # measurement is stored, so revisiting after a re-measurement recomputes.
    result = getattr(wizard, "epsilon_result", None)
    if result is None:
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
        _build_warnings(wizard, mid, result, rtexts)
        _build_intermediate(mid, result, rtexts)
        mid.addStretch(1)
    mid_container = QWidget()
    mid_container.setLayout(mid)
    left_half_layout.addWidget(mid_container, stretch=1)

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
            ax, result.f_hz, result.eps_selected, canvas=canvas,
            candidates=result.eps_candidates,
        )
        wizard.result_epsilon_manager = manager

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

    right_half.setFixedWidth(max(300, (1200 - 40) // 2))
    _chart_filter = _HalfWidthFilter(right_half, container)
    container.installEventFilter(_chart_filter)

    wizard.content_layout.addWidget(container, stretch=1)

    wizard.next_button.setEnabled(True)


def _sample_name(wizard, rtexts):
    return (getattr(wizard, "unknown_liquid_name", "") or "").strip() or rtexts.get(
        "default_sample", "the unknown liquid"
    )


def _build_summary(wizard, layout, result, rtexts):
    eps = result.eps_selected
    valid = np.isfinite(eps)
    sample = _sample_name(wizard, rtexts)
    if np.any(valid):
        with np.errstate(invalid="ignore", divide="ignore"):
            re_mean = float(np.nanmean(np.real(eps[valid])))
            tand = float(np.nanmean(-np.imag(eps[valid]) / np.real(eps[valid])))
        text = rtexts.get(
            "summary_template",
            "Sample: {sample}\nMean ε′ = {er_real:.2f}\nMean loss tangent = {tand:.3f}",
        ).format(sample=sample, er_real=re_mean, tand=tand)
    else:
        text = rtexts.get(
            "all_gap",
            "No physically valid permittivity could be selected on this sweep.",
        )
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("font-size: 15px;")
    layout.addWidget(label)


def _build_warnings(wizard, layout, result, rtexts):
    warns = list(result.warnings) + list(getattr(wizard, "temperature_warnings", []) or [])
    if not warns:
        return
    layout.addSpacing(8)
    title = QLabel(rtexts.get("warnings_title", "Warnings:"))
    title.setStyleSheet("font-weight: bold; color: #b8860b;")
    layout.addWidget(title)
    for w in warns[:8]:
        item = QLabel(f"• {w}")
        item.setWordWrap(True)
        item.setStyleSheet("color: #b8860b; font-size: 12px;")
        layout.addWidget(item)


def _build_intermediate(layout, result, rtexts):
    """Copyable block: general 5th-order equation + per-frequency coefficients."""
    layout.addSpacing(10)
    title = QLabel(rtexts.get("intermediate_title", "Intermediate data (5th-order equation)"))
    title.setStyleSheet("font-weight: bold; font-size: 13px;")
    layout.addWidget(title)

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
    text_box.setMinimumHeight(80)
    text_box.setStyleSheet(
        "font-family: Consolas, monospace; font-size: 12px;"
        " background-color: #ffffff; color: #1a1a1a; border: 1px solid #cccccc;"
    )
    layout.addWidget(text_box)

    def render(idx_in_combo):
        i = selector.itemData(idx_in_combo)
        if i is None:
            return
        content = _format_equation(result, int(i), rtexts)
        text_box.setPlainText(content)
        n_lines = content.count('\n') + 1
        text_box.setFixedHeight(n_lines * 17 + 44.5)

    selector.currentIndexChanged.connect(render)
    render(selector.currentIndex())


def _format_equation(result, i, rtexts):
    coeffs = result.polynomial_coeffs_at(i)
    eps_sel = result.eps_selected[i]
    lines = []
    lines.append(rtexts.get(
        "equation_general",
        "General form:  Gn·x^5 + x^2 + third_term = 0   (x = εr^(1/2),  εr = x^2)",
    ))
    lines.append("")
    lines.append(f"@ f = {_fmt_hz(result.f_hz[i])}")
    lines.append(f"  Gn         = {_fmt_c(result.gn[i])}")
    lines.append(f"  third_term = {_fmt_c(result.third_term[i])}")
    if np.all(np.isfinite(coeffs)):
        x_roots = np.roots(coeffs)
        lines.append("  x roots:")
        for r in x_roots:
            lines.append(f"    {_fmt_c(r)}   ->  εr = {_fmt_c(r**2)}")
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
    return f"{z.real:.4g} {sign} {abs(z.imag):.4g}j"


def _fmt_hz(hz):
    hz = float(hz)
    if hz >= 1e9:
        return f"{hz/1e9:.4f} GHz"
    if hz >= 1e6:
        return f"{hz/1e6:.3f} MHz"
    if hz >= 1e3:
        return f"{hz/1e3:.1f} kHz"
    return f"{hz:.0f} Hz"
