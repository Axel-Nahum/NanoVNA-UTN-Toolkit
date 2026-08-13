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
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget,
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
        # _build_intermediate is called after right half so it gets manager/ax/canvas

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
            autoscale=False,
        )
        fixed_ylim = ax.get_ylim()
        wizard.result_epsilon_manager = manager

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


def _greedy_assign(prev_vals: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    """One-to-one nearest-neighbour assignment of candidates to previous track values."""
    n = len(prev_vals)
    m = len(candidates)
    assigned = np.full(n, np.nan + 0j, dtype=complex)
    used_cand = [False] * m

    pairs = []
    for pi in range(n):
        if not np.isfinite(prev_vals[pi]):
            continue
        for ci in range(m):
            if np.isfinite(candidates[ci]):
                pairs.append((abs(candidates[ci] - prev_vals[pi]), pi, ci))
    pairs.sort(key=lambda x: x[0])

    used_prev = [False] * n
    for _, pi, ci in pairs:
        if not used_prev[pi] and not used_cand[ci]:
            assigned[pi] = candidates[ci]
            used_prev[pi] = True
            used_cand[ci] = True

    return assigned


def _track_all_branches(result) -> np.ndarray:
    """
    Track 5 continuous branches.
    Column 0 = eps_selected (algorithm auto).
    Columns 1-4 = remaining roots tracked by continuity.
    Returns shape (n_freq, 5).
    """
    n_freq = len(result.f_hz)
    tracked = np.full((n_freq, 5), np.nan + 0j, dtype=complex)
    tracked[:, 0] = result.eps_selected

    for i in range(n_freq):
        sel_idx = int(result.selected_index[i])
        if sel_idx < 0:
            continue  # gap frequency — leave branches 1-4 as NaN

        remaining = np.array(
            [result.eps_candidates[i, j] for j in range(5) if j != sel_idx],
            dtype=complex,
        )  # shape (4,)

        prev = tracked[i - 1, 1:] if i > 0 else np.full(4, np.nan + 0j, dtype=complex)

        if i == 0 or not np.any(np.isfinite(prev)):
            # Seed: order by real part descending (physically valid first)
            valid_mask = np.isfinite(remaining) & (np.real(remaining) > 0)
            valid = remaining[valid_mask]
            invalid = remaining[~valid_mask]
            if len(valid) > 1:
                valid = valid[np.argsort(-np.real(valid))]
            ordered = np.concatenate([valid, invalid])
            for b in range(min(4, len(ordered))):
                tracked[i, b + 1] = ordered[b]
        else:
            tracked[i, 1:] = _greedy_assign(prev, remaining)

    return tracked


def _build_intermediate(layout, result, rtexts, manager=None, ax=None, canvas=None, fixed_ylim=None):
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
        text_box.setFixedHeight(n_lines * 14 + 30)

    selector.currentIndexChanged.connect(render)
    render(selector.currentIndex())

    # --- Branch override ---
    if manager is None or ax is None or canvas is None:
        return

    tracked = _track_all_branches(result)  # shape (n_freq, 5)

    layout.addSpacing(10)

    chk = QCheckBox(rtexts.get("branch_override_label", "Override automatic branch selection"))
    layout.addWidget(chk)

    combo_container = QWidget()
    combo_container.setVisible(False)
    combo_row = QHBoxLayout(combo_container)
    combo_row.setContentsMargins(4, 4, 0, 0)
    combo_row.addWidget(QLabel(rtexts.get("branch_label", "Branch:")))
    branch_combo = QComboBox()
    for b in range(5):
        branch_data = tracked[:, b]
        valid = np.isfinite(branch_data) & (np.real(branch_data) > 0)
        if np.any(valid):
            mean_real = float(np.nanmean(np.real(branch_data[valid])))
            suffix = f"ε′ ≈ {mean_real:.2f}"
        else:
            suffix = "no valid data"
        label = f"Branch 1 (Auto) — {suffix}" if b == 0 else f"Branch {b + 1} — {suffix}"
        branch_combo.addItem(label, b)
    branch_combo.setCurrentIndex(0)
    combo_row.addWidget(branch_combo, stretch=1)
    layout.addWidget(combo_container)

    def _draw_branch(b: int):
        eps_curve = tracked[:, b]
        gray = np.column_stack([tracked[:, j] for j in range(5) if j != b])
        manager.update_epsilon_curves(ax, result.f_hz, eps_curve, canvas=None, candidates=gray, autoscale=False)
        if fixed_ylim is not None:
            ax.set_ylim(fixed_ylim)
        canvas.draw()

    def _apply_branch(branch_idx):
        b = branch_combo.itemData(branch_idx)
        if b is not None:
            _draw_branch(b)

    def _on_check(checked):
        combo_container.setVisible(bool(checked))
        if checked:
            _draw_branch(branch_combo.currentIndex())
        else:
            manager.update_epsilon_curves(
                ax, result.f_hz, result.eps_selected, canvas=None,
                autoscale=False,
            )
            if fixed_ylim is not None:
                ax.set_ylim(fixed_ylim)
            canvas.draw()

    chk.toggled.connect(_on_check)
    branch_combo.currentIndexChanged.connect(
        lambda idx: _apply_branch(idx) if chk.isChecked() else None
    )


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
        root_strs = [_fmt_c(r) for r in x_roots]
        eps_strs  = [_fmt_c(r ** 2) for r in x_roots]
        col_w = max(len(s) for s in root_strs)
        lines.append("  x roots:")
        for rs, es in zip(root_strs, eps_strs):
            lines.append(f"    {rs.ljust(col_w)}   ->  εr = {es}")
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


def _fmt_hz(hz):
    hz = float(hz)
    if hz >= 1e9:
        return f"{hz/1e9:.4f} GHz"
    if hz >= 1e6:
        return f"{hz/1e6:.3f} MHz"
    if hz >= 1e3:
        return f"{hz/1e3:.1f} kHz"
    return f"{hz:.0f} Hz"
