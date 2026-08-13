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
import sys
import os

import numpy as np
from matplotlib.lines import Line2D
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QRadioButton, QSizePolicy, QVBoxLayout, QWidget,
)


class _HalfWidthFilter(QObject):
    """Caps a target widget to at most half the observed widget's width."""

    def __init__(self, target: QWidget, parent: QWidget):
        super().__init__(parent)
        self._target = target

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self._target.setFixedWidth(max(260, int(obj.width() * 0.38)))
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

    # Left half: sidebar + mid (occupies ~62% of the window, chart gets 38%)
    left_half_layout = QHBoxLayout()
    left_half_layout.setContentsMargins(0, 0, 0, 0)
    left_half_layout.setSpacing(8)
    left_half_layout.addWidget(build_step_sidebar(wizard, descriptor, texts), stretch=0)

    # --- Middle column ---------------------------------------------------- #
    import os, sys
    mid = QVBoxLayout()
    mid.setSpacing(0)
    mid.setContentsMargins(10, 8, 10, 6)

    # ── Pre-calibrate bar — solo en pasos de líquido de referencia ──────── #
    if is_reference:
        precal_row = QHBoxLayout()
        precal_row.setContentsMargins(0, 0, 0, 0)
        precal_row.setSpacing(8)
        precal_hint = QLabel(std_texts.get("pre_calibrate_hint", "Optional — calibrate this reference before measuring"))
        precal_hint.setStyleSheet("font-size: 11px; color: #606080; font-style: italic;")
        precal_row.addWidget(precal_hint, stretch=1)
        btn_precal = QPushButton(std_texts.get("pre_calibrate", "⚙  Pre-calibrate"))
        btn_precal.setFixedHeight(24)
        btn_precal.setStyleSheet(
            "QPushButton { font-size: 11px; color: #888888; border: 1px solid #484858;"
            " border-radius: 4px; padding: 0 10px; }"
            " QPushButton:hover { color: #cccccc; border-color: #7070a0; }"
        )
        btn_precal.clicked.connect(lambda: _open_precal_dialog(wizard))
        precal_row.addWidget(btn_precal)
        mid.addLayout(precal_row)
        mid.addSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("border: none; background: #2e2e42; max-height: 1px;")
        mid.addWidget(sep)
        mid.addSpacing(10)

    # ── Instruction text ─────────────────────────────────────────────────── #
    instr = QLabel(instruction_html)
    instr.setWordWrap(True)
    instr.setStyleSheet("font-size: 13px;")
    if is_rich:
        instr.setTextFormat(Qt.RichText)
    mid.addWidget(instr)

    # Temperature reminder (reference liquids only)
    if is_reference:
        mid.addSpacing(3)
        temp_reminder = QLabel(std_texts.get(
            "temperature_reminder", "Configured temperature: {temp:.1f} °C"
        ).format(temp=float(getattr(wizard, "temperature_c", 25.0))))
        temp_reminder.setStyleSheet("font-size: 11px; color: #4da6ff; font-weight: bold;")
        mid.addWidget(temp_reminder)

    # ── Helper photo centrada debajo de la instrucción ───────────────────── #
    # En pasos sin pre-calibrate (Open, Short, DUT) la foto puede ser más grande
    _has_photo = False
    img_file = _STEP_IMAGE.get(standard.key)
    if img_file:
        base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.abspath("src/NanoVNA_UTN_Toolkit")
        img_path = os.path.join(base, "modules", "material_characterization", "assets", "images", img_file)
        _p = QPixmap(img_path)
        if not _p.isNull():
            photo = QLabel()
            photo.setAlignment(Qt.AlignHCenter)
            _pw, _ph = (245, 184) if is_reference else (330, 245)
            _scaled = _p.scaled(_pw, _ph, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            photo.setPixmap(_scaled)
            photo.setFixedHeight(_scaled.height())
            mid.addSpacing(18 if not is_reference else 10)
            mid.addWidget(photo)
            _has_photo = True

    mid.addSpacing(20 if is_reference else 20)

    already = wizard.perm_calibration.is_standard_measured(standard.key)

    # ── Source selector (reference liquids only) ──────────────────────── #
    btn_grp = None
    if is_reference:
        src_frame = QFrame()
        src_frame.setStyleSheet(
            "QFrame { border: 1.5px solid #606070; border-radius: 6px; }"
        )
        src_frame.setMinimumHeight(178)
        src_layout = QVBoxLayout(src_frame)
        src_layout.setContentsMargins(14, 12, 14, 14)
        src_layout.setSpacing(8)

        src_title = QLabel(std_texts.get("source_title", "Data source"))
        src_title.setStyleSheet("font-size: 11px; color: #888888; font-weight: bold; border: none;")
        src_layout.addWidget(src_title)

        btn_grp = QButtonGroup(src_frame)

        rb_measure = QRadioButton(std_texts.get("source_measure", "Measure with VNA"))
        rb_measure.setChecked(True)
        btn_grp.addButton(rb_measure, 0)
        src_layout.addWidget(rb_measure)

        rb_import = QRadioButton(std_texts.get("source_import", "Import .s1p file"))
        btn_grp.addButton(rb_import, 1)
        src_layout.addWidget(rb_import)

        # Fila: [rb_preset] [combo ─────────────]
        rb_preset = QRadioButton(std_texts.get("source_preset", "Use saved preset"))
        btn_grp.addButton(rb_preset, 2)

        preset_combo = QComboBox()
        preset_combo.setEnabled(False)
        preset_combo.setMinimumHeight(26)
        preset_combo.setPlaceholderText(std_texts.get("preset_empty", "No presets saved"))

        btn_save_preset = QPushButton(std_texts.get("save_preset", "Save as preset…"))
        btn_save_preset.setFixedHeight(24)
        btn_save_preset.setEnabled(already)
        btn_save_preset.setStyleSheet(
            "QPushButton { color: #7ab3f5; border: 1px solid #7ab3f5;"
            " border-radius: 4px; padding: 0 8px; font-size: 11px; }"
            " QPushButton:hover { background: #0f1e30; }"
            " QPushButton:disabled { color: #3a4a5a; border-color: #3a4a5a; }"
        )

        btn_delete_preset = QPushButton(std_texts.get("delete_preset", "Delete preset"))
        btn_delete_preset.setFixedHeight(24)
        btn_delete_preset.setEnabled(False)
        btn_delete_preset.setStyleSheet(
            "QPushButton { color: #ff6b6b; border: 1px solid #ff6b6b;"
            " border-radius: 4px; padding: 0 8px; font-size: 11px; }"
            " QPushButton:hover { background: #3a1a1a; }"
            " QPushButton:disabled { color: #5a2a2a; border-color: #5a2a2a; }"
        )

        # [rb_preset] [combo ────────] — misma fila, Qt los alinea vertical automáticamente
        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(0, 0, 0, 0)
        preset_row.setSpacing(8)
        preset_row.addWidget(rb_preset)
        preset_row.addWidget(preset_combo, stretch=1)
        src_layout.addLayout(preset_row)

        src_layout.addSpacing(8)

        # Botones centrados bajo el ancho del combo:
        # spacer izquierdo = ancho del rb_preset + spacing de preset_row
        _rb_offset = rb_preset.sizeHint().width() + 8
        action_row = QHBoxLayout()
        action_row.setSpacing(14)
        action_row.setContentsMargins(_rb_offset, 0, 0, 0)
        action_row.addStretch(1)
        action_row.addWidget(btn_save_preset)
        action_row.addWidget(btn_delete_preset)
        action_row.addStretch(1)
        src_layout.addLayout(action_row)

        mid.addSpacing(14)
        mid.addWidget(src_frame)
        mid.addSpacing(34)
    # ──────────────────────────────────────────────────────────────────── #

    measure_btn = QPushButton(
        std_texts.get("remeasure_button", "Measure again") if already
        else std_texts.get("measure_button", "Measure")
    )
    measure_btn.setFixedHeight(38)
    measure_btn.setFixedWidth(220)
    mid.addWidget(measure_btn, alignment=Qt.AlignHCenter)

    mid.addSpacing(6)

    wizard.status_label = QLabel(
        _success_text(std_texts, name) if already
        else std_texts.get("status_ready", "Ready to measure")
    )
    wizard.status_label.setAlignment(Qt.AlignCenter)
    wizard.status_label.setWordWrap(True)
    wizard.status_label.setStyleSheet(
        f"font-size: 12px; padding: 4px; color: {'lightgreen' if already else 'gray'};"
    )
    mid.addWidget(wizard.status_label)

    if is_reference:
        _lbl_ready     = std_texts.get("status_ready",        "Ready to measure")
        _lbl_import    = std_texts.get("status_import_ready", "No file imported yet")
        _btn_measure   = std_texts.get("measure_button",      "Measure")
        _btn_remeasure = std_texts.get("remeasure_button",    "Measure again")
        _btn_import    = std_texts.get("import_button",       "Import Liquid")

        def _on_source_changed(btn_id):
            preset_combo.setEnabled(btn_id == 2)
            btn_delete_preset.setEnabled(btn_id == 2)
            if btn_id == 0:
                measure_btn.setText(_btn_remeasure if already else _btn_measure)
                btn_save_preset.setEnabled(already)
                if not already:
                    wizard.status_label.setText(_lbl_ready)
                    wizard.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: gray;")
            elif btn_id == 1:
                measure_btn.setText(_btn_import)
                btn_save_preset.setEnabled(False)
                wizard.status_label.setText(_lbl_import)
                wizard.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: gray;")
            else:
                measure_btn.setText(_btn_measure)
                btn_save_preset.setEnabled(False)
                if not already:
                    wizard.status_label.setText(_lbl_ready)
                    wizard.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: gray;")

        btn_grp.idClicked.connect(_on_source_changed)

        def _show_save_after_measure():
            btn_save_preset.setEnabled(True)

        wizard._on_ref_measured_hook = _show_save_after_measure

    mid.addStretch(1)
    mid_container = QWidget()
    mid_container.setLayout(mid)
    left_half_layout.addWidget(mid_container, stretch=1)

    left_half = QWidget()
    left_half.setLayout(left_half_layout)

    # Right half: Smith chart
    right = QVBoxLayout()
    right.setContentsMargins(8, 4, 8, 4)
    right.setSpacing(4)
    from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import create_wizard_smith_chart
    fig, ax, canvas = create_wizard_smith_chart(
        start_freq=wizard.get_sweep_start_frequency(),
        stop_freq=wizard.get_sweep_stop_frequency(),
        num_points=wizard.get_sweep_steps(),
        container_layout=right,
        figsize=(6, 6),
    )
    wizard.current_fig, wizard.current_ax, wizard.current_canvas = fig, ax, canvas

    # Checkbox dentro del canvas (fig.text) — en el espacio blanco inferior del figure
    indicative_chk = None
    if is_reference:
        _chk_on  = '☑  ' + std_texts.get("show_indicative", "Show indicative reference")
        _chk_off = '☐  ' + std_texts.get("show_indicative", "Show indicative reference")
        _chk_text = fig.text(
            0.5, 0.06, _chk_on,
            ha='center', va='center',
            fontsize=9, color='#888888',
            picker=True,
        )

        def _on_pick(event):
            if event.artist is not _chk_text:
                return
            state["show_indicative"] = not state["show_indicative"]
            _chk_text.set_text(_chk_on if state["show_indicative"] else _chk_off)
            stored_now = wizard.perm_calibration.get_measurement(standard.key)
            _render(wizard, standard, name, color, std_texts, stored_now, state["show_indicative"])

        fig.canvas.mpl_connect('pick_event', _on_pick)

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
    right_half.setFixedWidth(max(260, int((getattr(wizard, "_wiz_w", 1300) - 40) * 0.38)))
    _chart_filter = _HalfWidthFilter(right_half, container)
    container.installEventFilter(_chart_filter)

    wizard.content_layout.addWidget(container, stretch=1)

    stored = wizard.perm_calibration.get_measurement(standard.key) if already else None
    _render(wizard, standard, name, color, std_texts, stored, state["show_indicative"])
    wizard.next_button.setEnabled(already)

    def _btn_clicked():
        mode = btn_grp.checkedId() if btn_grp is not None else 0
        if mode == 0:
            _on_measure(wizard, standard, name, color, measure_btn, std_texts, state)
        elif mode == 1:
            _on_import(wizard, standard, name, color, measure_btn, std_texts, state)
        # mode == 2 (preset) — no action yet

    measure_btn.clicked.connect(_btn_clicked)


def _success_text(std_texts, name):
    return std_texts.get("status_success", "{name} successfully measured").format(name=name)


def _on_import(wizard, standard, name, color, button, std_texts, state):
    """Open a .s1p file, validate frequencies, store and render."""
    import numpy as np
    filepath, _ = QFileDialog.getOpenFileName(
        wizard,
        std_texts.get("import_dialog_title", "Import S11 (.s1p)"),
        "",
        "Touchstone 1-port (*.s1p);;All files (*)",
    )
    if not filepath:
        return  # user cancelled

    # Validate extension
    if not filepath.lower().endswith(".s1p"):
        QMessageBox.warning(
            wizard,
            std_texts.get("import_error_title", "Import Error"),
            std_texts.get("import_error_not_s1p", "The selected file is not a .s1p Touchstone file."),
        )
        return

    # Parse with skrf
    try:
        import skrf as rf
        net = rf.Network(filepath)
        freqs = np.asarray(net.f, dtype=float)
        s11   = np.asarray(net.s[:, 0, 0], dtype=complex)
    except Exception as exc:
        QMessageBox.critical(
            wizard,
            std_texts.get("import_error_title", "Import Error"),
            std_texts.get("import_error_parse", "Could not read the file:\n{err}").format(err=exc),
        )
        return

    # Validate frequency grid against configured sweep
    sw_n     = wizard.get_sweep_steps()
    sw_start = float(wizard.get_sweep_start_frequency())
    sw_stop  = float(wizard.get_sweep_stop_frequency())
    f_tol    = 1e-3  # Hz

    if len(freqs) != sw_n or abs(freqs[0] - sw_start) > f_tol or abs(freqs[-1] - sw_stop) > f_tol:
        QMessageBox.warning(
            wizard,
            std_texts.get("import_error_title", "Import Error"),
            std_texts.get(
                "import_error_freq_mismatch",
                "Frequency mismatch.\n\n"
                "File:  {fn} pts  {fs} – {fe}\n"
                "Sweep: {sn} pts  {ss} – {se}\n\n"
                "The file must match the configured sweep exactly.\n"
                "Import a matching file or change the sweep in Configuration."
            ).format(
                fn=len(freqs),
                fs=_fmt_freq(freqs[0]),
                fe=_fmt_freq(freqs[-1]),
                sn=sw_n,
                ss=_fmt_freq(sw_start),
                se=_fmt_freq(sw_stop),
            ),
        )
        return

    wizard.perm_calibration.set_measurement(standard.key, freqs, s11)
    wizard.epsilon_result = None
    set_status(wizard, _success_text(std_texts, name), "lightgreen")
    button.setText(std_texts.get("reimport_button", "Import again"))
    _render(wizard, standard, name, color, std_texts, (freqs, s11), state["show_indicative"])
    wizard.next_button.setEnabled(True)
    hook = getattr(wizard, "_on_ref_measured_hook", None)
    if callable(hook):
        hook()


def _fmt_freq(hz: float) -> str:
    """Format Hz as kHz / MHz / GHz string."""
    if hz >= 1e9:
        return f"{hz/1e9:.4g} GHz"
    if hz >= 1e6:
        return f"{hz/1e6:.4g} MHz"
    return f"{hz/1e3:.4g} kHz"


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
    hook = getattr(wizard, "_on_ref_measured_hook", None)
    if callable(hook):
        hook()


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


def _open_precal_dialog(wizard):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox
    dlg = QDialog(wizard)
    dlg.setWindowTitle("Pre-calibration")
    dlg.setMinimumWidth(400)
    layout = QVBoxLayout(dlg)
    layout.setSpacing(12)
    layout.setContentsMargins(20, 16, 20, 16)

    title = QLabel("Pre-calibration")
    title.setStyleSheet("font-size: 15px; font-weight: bold;")
    layout.addWidget(title)

    desc = QLabel(
        "Pre-calibration compensates for cable and connector imperfections "
        "before running the characterization procedure.\n\n"
        "Connect the calibration standards (Open, Short, Load) to the port "
        "and follow the on-screen instructions."
    )
    desc.setWordWrap(True)
    desc.setStyleSheet("font-size: 12px; color: #cccccc;")
    layout.addWidget(desc)

    layout.addSpacing(4)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok)
    buttons.accepted.connect(dlg.accept)
    layout.addWidget(buttons)

    dlg.exec()
