"""
Per-standard / DUT measurement screen of the characterization wizard.

EN: Generic three-column measurement screen reused for every calibration
    standard (Open, Short, the two reference liquids) and for the unknown
    liquid (DUT). Columns: step sidebar | instruction + helper photo + Measure
    button + status | live Smith chart. The Smith chart shows an EXPECTED
    reference to guide inexperienced users:
      * Open  -> exact marker at Gamma = +1
      * Short -> exact marker at Gamma = -1
      * reference liquid -> an *indicative* dotted S11 curve (same color as the
        measured trace) from the liquid's known permittivity (nominal probe
        model); a checkbox shows/hides it
      * DUT   -> no reference (it is the unknown)
    Re-entering an already-measured step restores the stored trace.

ES: Pantalla de medicion generica de tres columnas, reutilizada para cada
    patron (Open, Short, los dos liquidos de referencia) y el liquido incognita
    (DUT). Columnas: barra de pasos | instruccion + foto de ayuda + boton Medir
    + estado | carta de Smith en vivo. La carta muestra una referencia ESPERADA
    para guiar al usuario inexperto:
      * Open  -> marcador exacto en Gamma = +1
      * Short -> marcador exacto en Gamma = -1
      * liquido de referencia -> curva S11 *indicativa* punteada (del mismo
        color que la traza medida) a partir de su permitividad conocida (modelo
        de sonda nominal); un checkbox la muestra/oculta
      * DUT   -> sin referencia (es la incognita)
    Al volver a un paso ya medido se restaura la traza guardada.
"""

from __future__ import annotations

import logging

import numpy as np
from matplotlib.lines import Line2D
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget


class _HalfWidthFilter(QObject):
    """Caps a target widget to at most half the observed widget's width."""

    def __init__(self, target: QWidget, parent: QWidget):
        super().__init__(parent)
        self._target = target

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self._target.setFixedWidth(max(300, obj.width() // 2))
        return False

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text, image_path
from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.base import StandardKind
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid, indicative_s11,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.step_sidebar import (
    build_step_sidebar,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.measure_runner import (
    run_s11_sweep, set_status, SMITH_COLOR_MAP,
)

logger = logging.getLogger(__name__)

# Helper photo per standard (None for Open).
_STEP_IMAGE = {
    "short": "short_setup_example.png",
    "ref1": "probe_in_liquid.png",
    "ref2": "probe_in_liquid.png",
    "dut": "probe_in_liquid.png",
}


def build_standard_screen(wizard, descriptor, step_def):
    texts = load_text("characterization_wizard.json")
    std_texts = texts.get("standards", {})
    liquids = texts.get("liquids", {})

    standard = step_def.standard
    is_reference = standard.kind is StandardKind.REFERENCE_LIQUID
    total = len(descriptor.steps)
    name, instruction_html, is_rich = _resolve_strings(wizard, std_texts, liquids, standard)
    color = SMITH_COLOR_MAP.get(standard.key, "blue")

    title_tmpl = std_texts.get("title_template", "Step {index}/{total}: {name}")
    wizard.title_label.setText(title_tmpl.format(index=wizard.current_step, total=total, name=name))

    # Per-screen render state (mutated by the checkbox).
    state = {"show_indicative": True}

    # Left half: sidebar + instructions (occupies exactly the left 50% of the window)
    left_half_layout = QHBoxLayout()
    left_half_layout.setContentsMargins(0, 0, 0, 0)
    left_half_layout.setSpacing(8)
    left_half_layout.addWidget(build_step_sidebar(wizard, descriptor, texts), stretch=0)

    # --- Middle: instructions + photo + control -------------------------- #
    mid = QVBoxLayout()
    mid.setSpacing(0)
    mid.setContentsMargins(8, 8, 8, 8)

    instr = QLabel(instruction_html)
    instr.setWordWrap(True)
    instr.setStyleSheet("font-size: 14px;")
    if is_rich:
        instr.setTextFormat(Qt.RichText)
    mid.addWidget(instr)

    # Temperature reminder (reference liquids depend on it).
    if is_reference:
        mid.addSpacing(10)
        temp_reminder = QLabel(std_texts.get(
            "temperature_reminder", "Configured temperature: {temp:.1f} °C"
        ).format(temp=float(getattr(wizard, "temperature_c", 25.0))))
        temp_reminder.setStyleSheet("font-size: 12px; color: #4da6ff; font-weight: bold;")
        mid.addWidget(temp_reminder)

    # Helper photo.
    img_file = _STEP_IMAGE.get(standard.key)
    if img_file:
        pix = QPixmap(image_path(img_file))
        if not pix.isNull():
            photo = QLabel()
            photo.setAlignment(Qt.AlignCenter)
            photo.setPixmap(pix.scaledToWidth(260, Qt.SmoothTransformation))
            mid.addSpacing(26)
            mid.addWidget(photo)

    mid.addSpacing(20)

    already = wizard.perm_calibration.is_standard_measured(standard.key)
    measure_btn = QPushButton(
        std_texts.get("remeasure_button", "Measure again") if already
        else std_texts.get("measure_button", "Measure")
    )
    measure_btn.setFixedHeight(38)
    measure_btn.setFixedWidth(220)
    mid.addWidget(measure_btn, alignment=Qt.AlignHCenter)

    mid.addSpacing(10)

    wizard.status_label = QLabel(
        _success_text(std_texts, name) if already
        else std_texts.get("status_ready", "Ready to measure")
    )
    wizard.status_label.setAlignment(Qt.AlignCenter)
    wizard.status_label.setWordWrap(True)
    wizard.status_label.setFixedHeight(44)
    wizard.status_label.setStyleSheet(
        f"font-size: 12px; padding: 4px; color: {'lightgreen' if already else 'gray'};"
    )
    mid.addWidget(wizard.status_label)

    # Indicative-curve show/hide (reference steps only).
    indicative_chk = None
    if is_reference:
        mid.addSpacing(12)
        indicative_chk = QCheckBox(std_texts.get("show_indicative", "Show indicative reference"))
        indicative_chk.setChecked(True)
        mid.addWidget(indicative_chk, alignment=Qt.AlignHCenter)

    mid.addStretch(1)
    mid_container = QWidget()
    mid_container.setLayout(mid)
    left_half_layout.addWidget(mid_container, stretch=1)

    left_half = QWidget()
    left_half.setLayout(left_half_layout)

    # Right half: Smith chart — starts exactly at the window midpoint.
    # Equal margins (8 px each side) give symmetric padding around the canvas.
    right = QVBoxLayout()
    right.setContentsMargins(8, 4, 8, 4)
    from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import create_wizard_smith_chart
    fig, ax, canvas = create_wizard_smith_chart(
        start_freq=wizard.get_sweep_start_frequency(),
        stop_freq=wizard.get_sweep_stop_frequency(),
        num_points=wizard.get_sweep_steps(),
        container_layout=right,
        figsize=(6, 6),
    )
    wizard.current_fig, wizard.current_ax, wizard.current_canvas = fig, ax, canvas
    right_half = QWidget()
    right_half.setLayout(right)

    # Two equal halves → chart always occupies the right 50% of the window.
    columns = QHBoxLayout()
    columns.setContentsMargins(0, 0, 0, 0)
    columns.setSpacing(0)
    columns.addWidget(left_half, stretch=1)
    columns.addWidget(right_half, stretch=1)

    container = QWidget()
    container.setLayout(columns)

    # Pin right_half to exactly half the container via setFixedWidth so that
    # canvas.draw() during measure cannot trigger a layout reflow.
    right_half.setFixedWidth(max(300, (1200 - 40) // 2))
    _chart_filter = _HalfWidthFilter(right_half, container)
    container.installEventFilter(_chart_filter)

    wizard.content_layout.addWidget(container, stretch=1)

    stored = wizard.perm_calibration.get_measurement(standard.key) if already else None
    _render(wizard, standard, name, color, std_texts, stored, state["show_indicative"])
    wizard.next_button.setEnabled(already)

    measure_btn.clicked.connect(
        lambda: _on_measure(wizard, standard, name, color, measure_btn, std_texts, state)
    )
    if indicative_chk is not None:
        def _toggle(checked):
            state["show_indicative"] = bool(checked)
            stored_now = wizard.perm_calibration.get_measurement(standard.key)
            _render(wizard, standard, name, color, std_texts, stored_now, state["show_indicative"])
        indicative_chk.toggled.connect(_toggle)


def _success_text(std_texts, name):
    return std_texts.get("status_success", "{name} successfully measured").format(name=name)


def _on_measure(wizard, standard, name, color, button, std_texts, state):
    result = run_s11_sweep(wizard)
    if result is None:
        return
    freqs, s11 = result
    wizard.perm_calibration.set_measurement(standard.key, freqs, s11)
    # A new measurement invalidates the cached epsilon result so that step 7
    # recomputes on the next visit instead of showing stale data.
    wizard.epsilon_result = None
    set_status(wizard, _success_text(std_texts, name), "lightgreen")
    button.setText(std_texts.get("remeasure_button", "Measure again"))
    _render(wizard, standard, name, color, std_texts, (freqs, s11), state["show_indicative"])
    wizard.next_button.setEnabled(True)


def _short_legend_name(standard, name):
    """Return a compact legend label for the S11 trace."""
    if standard.key in ("open", "short"):
        return standard.key.capitalize()
    # Strip "Reference liquid: " prefix (or locale variants)
    short = name
    for prefix in ("Reference liquid: ", "Líquido de referencia: ", "Liquido de referencia: "):
        if short.startswith(prefix):
            short = short[len(prefix):]
            break
    # If name contains an all-caps abbreviation in parentheses (e.g. "Isopropyl Alcohol (IPA)")
    # use that abbreviation directly to keep the legend narrow.
    if "(" in short and short.endswith(")"):
        abbrev = short[short.rfind("(") + 1:-1]
        if abbrev.isupper() and 1 < len(abbrev) <= 6:
            return abbrev
    return short


def _render(wizard, standard, name, color, std_texts, measured, show_indicative):
    """Draw base Smith chart + expected reference + (optional) measured trace."""
    from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import SmithChartManager
    ax = wizard.current_ax
    if ax is None:
        return
    manager = SmithChartManager()
    builder = manager.builder
    builder.ax = ax

    ax.clear()
    ax.get_figure().subplots_adjust(left=0.2, right=0.8, top=0.8, bottom=0.2)
    start = wizard.get_sweep_start_frequency()
    stop = wizard.get_sweep_stop_frequency()
    points = wizard.get_sweep_steps()
    base = builder.create_empty_network(start, stop, points)
    base.plot_s_smith(ax=ax, draw_labels=True, show_legend=False)
    builder._configure_smith_chart_appearance()
    ax.set_title(r"$\mathrm{Smith\ Diagram}$", fontsize=14, pad=30,
                 color=builder.config.text_color)

    handles, labels = [], []

    if standard.key == "open":
        ax.plot([1.0], [0.0], marker="o", markerfacecolor="none", markeredgecolor="gray",
                markeredgewidth=1.5, markersize=12, linestyle="None", zorder=1)
        handles.append(Line2D([0], [0], marker="o", markerfacecolor="none",
                              markeredgecolor="gray", linestyle="None"))
        labels.append(r"$\Gamma = +1$")
    elif standard.key == "short":
        ax.plot([-1.0], [0.0], marker="o", markerfacecolor="none", markeredgecolor="gray",
                markeredgewidth=1.5, markersize=12, linestyle="None", zorder=1)
        handles.append(Line2D([0], [0], marker="o", markerfacecolor="none",
                              markeredgecolor="gray", linestyle="None"))
        labels.append(r"$\Gamma = -1$")
    elif standard.kind is StandardKind.REFERENCE_LIQUID and standard.default_liquid_key and show_indicative:
        try:
            liquid = get_reference_liquid(standard.default_liquid_key)
            f = np.linspace(start, stop, points)
            s_ind = indicative_s11(liquid, f, getattr(wizard, "temperature_c", 25.0))
            ax.plot(np.real(s_ind), np.imag(s_ind), linestyle=":", color=color,
                    linewidth=1.4, zorder=1)
            handles.append(Line2D([0], [0], linestyle=":", color=color))
            labels.append(r"$S_{11}$ — indicative")
        except Exception as exc:  # noqa: BLE001
            logger.error("[standard_screen] indicative curve failed: %s", exc)

    if measured is not None:
        _, s11 = measured
        s11 = np.asarray(s11, dtype=complex)
        ax.plot(np.real(s11), np.imag(s11), "o-", color=color, linewidth=2,
                markersize=3, zorder=3)
        builder.add_start_point_marker(s11, color=color)
        handles.append(Line2D([0], [0], color=color))
        labels.append(rf"$S_{{11}}$ — {_short_legend_name(standard, name)}")

    if handles:
        # Upper-left corner of the axes is diagonally outside the Smith unit circle.
        # transAxes pins the box so it never drifts when the window is resized.
        # Reference-liquid and DUT steps have 2-line legends so we shrink them.
        small = standard.kind is StandardKind.REFERENCE_LIQUID or standard.key == "dut"
        ax.legend(handles, labels,
                  loc="upper left",
                  bbox_to_anchor=(-0.22, 1.14),
                  bbox_transform=ax.transAxes,
                  fontsize=8.0 if small else 9.5,
                  framealpha=0.93,
                  handlelength=1.0 if small else 1.2,
                  borderpad=0.3 if small else 0.4,
                  labelspacing=0.2 if small else 0.25)

    if wizard.current_canvas:
        wizard.current_canvas.draw()


def _resolve_strings(wizard, std_texts, liquids, standard):
    """Return ``(name, instruction, is_rich)`` for the given standard."""
    if standard.kind is StandardKind.REFERENCE_LIQUID:
        key = standard.default_liquid_key
        liquid_name = liquids.get(key, get_reference_liquid(key).display_name) if key else "?"
        block = std_texts.get("reference", {})
        name = block.get("name", "Reference liquid: {liquid}").format(liquid=liquid_name)
        styled = f"<b><i>{liquid_name}</i></b>"
        instruction = block.get(
            "instruction", "Immerse the probe in {liquid} and press Measure."
        ).format(liquid=styled)
        return name, instruction, True

    if standard.kind is StandardKind.DUT:
        unknown = (getattr(wizard, "unknown_liquid_name", "") or "").strip()
        block = std_texts.get("dut", {})
        default_name = block.get("name", "Unknown liquid")
        name = unknown or default_name
        instruction = block.get(
            "instruction", "Immerse the probe in the unknown liquid and press Measure."
        )
        if unknown:
            styled = f"<b><i>{unknown}</i></b>"
            instruction = instruction.replace("the unknown liquid", styled).replace(
                "el líquido incógnita", styled
            )
            return name, instruction, True
        return name, instruction, False

    block = std_texts.get(standard.key, {})
    name = block.get("name", standard.key.upper())
    instruction = block.get("instruction", f"Connect the {standard.key} standard and press Measure.")
    return name, instruction, False
