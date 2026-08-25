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
from pathlib import Path

import numpy as np
from matplotlib.lines import Line2D
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame,
    QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, QRadioButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from NanoVNA_UTN_Toolkit.shared.utils.preferences.debug_mode import is_debug_enabled

def _refresh_preset_combo(combo: QComboBox, liquid_key=None) -> None:
    """Fill ``combo`` with the presets of ``liquid_key`` (all of them if None).

    The preset NAME travels as userData, because the visible label is the
    human-readable ``display_name`` from the sidecar, not the file stem.
    """
    current = combo.currentData()
    combo.clear()
    try:
        metas = preset_store.list_presets(liquid_key=liquid_key)
    except Exception:
        logger.exception("[standard_screen] could not list presets")
        metas = []
    for meta in metas:
        combo.addItem(meta.label(), meta.name)
    idx = combo.findData(current)
    if idx >= 0:
        combo.setCurrentIndex(idx)


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
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import preset_store
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.session_liquids import (
    preset_preload, selected_liquid_key, set_preset_preload,
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

    # Clear any hook left over from a previous reference-liquid screen so that
    # non-reference steps (DUT) don't call into already-destroyed widgets.
    wizard._on_measurement_stored_hook = None
    wizard._on_precal_applied_hook = None

    standard = step_def.standard
    is_reference = standard.kind is StandardKind.REFERENCE_LIQUID
    total = len(descriptor.steps)
    name, instruction_html, is_rich = _resolve_strings(wizard, std_texts, liquids, standard)
    color = SMITH_COLOR_MAP.get(standard.key, "blue")

    # Offline .s1p import is a Debug Mode feature: it lets the whole assistant be
    # exercised without a probe. Read once per screen build; screens are rebuilt
    # on every navigation, so toggling the preference takes effect immediately.
    debug_mode = is_debug_enabled()

    title_tmpl = std_texts.get("title_template", "Step {index}/{total}: {name}")
    wizard.title_label.setText(title_tmpl.format(index=wizard.current_step, total=total, name=name))

    # Per-screen render state (mutated by the checkboxes).
    state = {"show_indicative": True, "show_raw": False}

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
        precal_hint = QLabel(std_texts.get(
            "pre_calibrate_hint",
            "Normalización con OPEN — corrige cable y conectores"
        ))
        precal_hint.setStyleSheet("font-size: 11px; color: #606080; font-style: italic;")
        precal_row.addWidget(precal_hint, stretch=1)

        btn_precal = QPushButton(std_texts.get("pre_calibrate", "⚙  Pre-calibrar (OPEN)"))
        btn_precal.setFixedHeight(24)
        btn_precal.setStyleSheet(
            "QPushButton { font-size: 11px; color: #888888; border: 1px solid #484858;"
            " border-radius: 4px; padding: 0 10px; }"
            " QPushButton:hover { color: #cccccc; border-color: #7070a0; }"
        )
        precal_row.addWidget(btn_precal)

        btn_delete_precal_top = QPushButton(std_texts.get("delete_precal", "✕ Quitar pre-cal"))
        btn_delete_precal_top.setFixedHeight(24)
        btn_delete_precal_top.setStyleSheet(
            "QPushButton { font-size: 11px; color: #ff6b6b; border: 1px solid #ff6b6b;"
            " border-radius: 4px; padding: 0 10px; }"
            " QPushButton:hover { background: #3a1a1a; }"
        )
        _has_precal = standard.key in getattr(wizard, "_precal_originals", {})
        btn_delete_precal_top.setVisible(_has_precal)
        precal_row.addWidget(btn_delete_precal_top)

        def _on_precal_clicked():
            if not wizard.perm_calibration.is_standard_measured(standard.key):
                QMessageBox.information(
                    wizard,
                    std_texts.get("precal_no_liquid_title", "Sin datos"),
                    std_texts.get(
                        "precal_no_liquid_msg",
                        "Primero medí, importá o seleccioná un preset del líquido "
                        "antes de aplicar la normalización con OPEN.",
                    ),
                )
                return
            _open_precal_dialog(wizard, standard, name, color, std_texts, state, btn_delete_precal_top)

        btn_precal.clicked.connect(_on_precal_clicked)

        def _delete_precal():
            originals = getattr(wizard, "_precal_originals", {})
            if standard.key not in originals:
                return
            freqs, s11_orig = originals.pop(standard.key)
            getattr(wizard, "_precal_open", {}).pop(standard.key, None)
            wizard.perm_calibration.set_measurement(standard.key, freqs, s11_orig)
            wizard.epsilon_result = None
            state["show_raw"] = False
            if state.get("raw_chk_artist") is not None:
                state["raw_chk_artist"].set_text(state.get("raw_chk_off", "☐  Show without pre-cal"))
                state["raw_chk_artist"].set_visible(False)
                if wizard.current_canvas:
                    wizard.current_canvas.draw()
            _render(wizard, standard, name, color, std_texts, (freqs, s11_orig), state["show_indicative"], False)
            btn_delete_precal_top.setVisible(False)

        btn_delete_precal_top.clicked.connect(_delete_precal)

        # Register a hook so _store_measurement can hide this button if a new
        # measurement arrives with a grid that no longer matches the stored OPEN.
        if not hasattr(wizard, "_precal_discard_hooks"):
            wizard._precal_discard_hooks = {}
        wizard._precal_discard_hooks[standard.key] = btn_delete_precal_top.hide
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
        # Without the Save/Delete action row the box is two rows shorter; one
        # more when the import option is hidden (Debug Mode off).
        src_frame.setMinimumHeight(126 if debug_mode else 100)
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

        if debug_mode:
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

        # Preset deletion now lives in Step 1, next to the liquid selection:
        # this screen only consumes presets, it no longer manages the library.
        _refresh_preset_combo(preset_combo, selected_liquid_key(wizard, standard))

        # [rb_preset] [combo ────────] — misma fila, Qt los alinea vertical automáticamente
        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(0, 0, 0, 0)
        preset_row.setSpacing(8)
        preset_row.addWidget(rb_preset)
        preset_row.addWidget(preset_combo, stretch=1)
        src_layout.addLayout(preset_row)

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

    # Saving belongs next to Measure: what it stores is exactly what this step
    # just captured. Available on every step, not only the reference liquids.
    btn_save_preset = QPushButton(std_texts.get("save_preset", "Save as preset…"))
    btn_save_preset.setFixedHeight(38)
    btn_save_preset.setEnabled(already)
    btn_save_preset.setStyleSheet(
        "QPushButton { color: #7ab3f5; border: 1px solid #7ab3f5;"
        " border-radius: 4px; padding: 0 12px; font-size: 11px; }"
        " QPushButton:hover { background: #0f1e30; }"
        " QPushButton:disabled { color: #3a4a5a; border-color: #3a4a5a; }"
    )
    btn_save_preset.clicked.connect(
        lambda: _do_save_measurement(wizard, descriptor, standard, std_texts))

    measure_row = QHBoxLayout()
    measure_row.setSpacing(10)
    measure_row.addStretch(1)
    measure_row.addWidget(measure_btn)
    measure_row.addWidget(btn_save_preset)
    measure_row.addStretch(1)
    mid.addLayout(measure_row)

    # Every path that stores a measurement re-enables saving.
    wizard._on_measurement_stored_hook = lambda: btn_save_preset.setEnabled(True)

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
        _lbl_no_preset = std_texts.get("status_no_preset",    "No preset selected")
        _btn_measure   = std_texts.get("measure_button",      "Measure")
        _btn_remeasure = std_texts.get("remeasure_button",    "Measure again")
        _btn_import    = std_texts.get("import_button",       "Import Liquid")

        # Trace color per source mode: 0=measure, 1=import, 2=preset
        _trace_colors = {0: color, 1: "#ff9f43", 2: "#2ecc71"}

        def _on_source_changed(btn_id):
            preset_combo.setEnabled(btn_id == 2)
            measure_btn.setEnabled(btn_id != 2)
            if btn_id == 0:
                measure_btn.setText(_btn_remeasure if already else _btn_measure)
                if not already:
                    wizard.status_label.setText(_lbl_ready)
                    wizard.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: gray;")
            elif btn_id == 1:
                measure_btn.setText(_btn_import)
                wizard.status_label.setText(_lbl_import)
                wizard.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: gray;")
            else:
                measure_btn.setText(_btn_measure)
                current_preset = preset_combo.currentData()
                if current_preset:
                    _load_preset(current_preset)
                else:
                    wizard.status_label.setText(_lbl_no_preset)
                    wizard.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: gray;")

        def _load_preset(preset_name):
            if not preset_name or btn_grp.checkedId() != 2:
                return
            loaded = _load_preset_into_step(wizard, standard, name, std_texts, preset_name)
            if loaded is None:
                return
            freqs, s11 = loaded
            _render(wizard, standard, name, _trace_colors[2], std_texts,
                    (freqs, s11), state["show_indicative"], state.get("show_raw", False))

        btn_grp.idClicked.connect(_on_source_changed)
        preset_combo.currentIndexChanged.connect(
            lambda *_: _load_preset(preset_combo.currentData()))

    mid.addStretch(1)

    if not is_reference and debug_mode:
        dev_import_btn = QPushButton(std_texts.get("import_file_button", "Import .s1p file"))
        dev_import_btn.setFixedHeight(26)
        dev_import_btn.setStyleSheet(
            "QPushButton { font-size: 11px; color: #666677; border: 1px dashed #444455;"
            " border-radius: 4px; padding: 0 12px; }"
            " QPushButton:hover { color: #aaaacc; border-color: #6666aa; }"
        )
        mid.addWidget(dev_import_btn, alignment=Qt.AlignHCenter)
        mid.addSpacing(4)
        dev_import_btn.clicked.connect(
            lambda: _on_import(wizard, standard, name, color, measure_btn, std_texts, state)
        )

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

    # Checkboxes dentro del canvas (fig.text) — en el espacio blanco inferior del figure
    if is_reference:
        _chk_on  = '☑  ' + std_texts.get("show_indicative", "Show indicative reference")
        _chk_off = '☐  ' + std_texts.get("show_indicative", "Show indicative reference")
        _chk_text = fig.text(
            0.5, 0.08, _chk_on,
            ha='center', va='center',
            fontsize=9, color='#888888',
            picker=True,
        )

        _raw_on  = '☑  ' + std_texts.get("show_raw", "Show without pre-cal")
        _raw_off = '☐  ' + std_texts.get("show_raw", "Show without pre-cal")
        _chk_raw = fig.text(
            0.5, 0.02, _raw_off,
            ha='center', va='center',
            fontsize=9, color='#888888',
            picker=True,
            visible=False,  # shown only when pre-cal is active
        )
        state["raw_chk_artist"] = _chk_raw
        state["raw_chk_on"]  = _raw_on
        state["raw_chk_off"] = _raw_off

        # Make raw checkbox visible immediately if pre-cal already active (screen revisit).
        if standard.key in getattr(wizard, "_precal_originals", {}):
            _chk_raw.set_visible(True)

        def _on_pick(event):
            stored_now = wizard.perm_calibration.get_measurement(standard.key)
            if event.artist is _chk_text:
                state["show_indicative"] = not state["show_indicative"]
                _chk_text.set_text(_chk_on if state["show_indicative"] else _chk_off)
                _render(wizard, standard, name, color, std_texts, stored_now,
                        state["show_indicative"], state.get("show_raw", False))
            elif event.artist is _chk_raw:
                if standard.key not in getattr(wizard, "_precal_originals", {}):
                    return
                state["show_raw"] = not state["show_raw"]
                _chk_raw.set_text(_raw_on if state["show_raw"] else _raw_off)
                _render(wizard, standard, name, color, std_texts, stored_now,
                        state["show_indicative"], state["show_raw"])

        fig.canvas.mpl_connect('pick_event', _on_pick)

        # Hook called by _open_precal_dialog after Apply to make the raw checkbox visible.
        def _on_precal_applied():
            _chk_raw.set_visible(True)
            if wizard.current_canvas:
                wizard.current_canvas.draw()

        wizard._on_precal_applied_hook = _on_precal_applied

        # Register hook so _precal_discard_hooks can also hide the raw checkbox.
        _orig_discard = wizard._precal_discard_hooks.get(standard.key)
        def _on_precal_discard_full():
            if callable(_orig_discard):
                _orig_discard()
            state["show_raw"] = False
            _chk_raw.set_text(_raw_off)
            _chk_raw.set_visible(False)
            if wizard.current_canvas:
                wizard.current_canvas.draw()
        wizard._precal_discard_hooks[standard.key] = _on_precal_discard_full

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

    # A preset picked in Step 1 pre-loads this step the first time it is shown;
    # the user can still measure over it.
    pending_preset = preset_preload(wizard).get(standard.key)
    if pending_preset and not already:
        loaded = _load_preset_into_step(wizard, standard, name, std_texts, pending_preset)
        if loaded is not None:
            already = True
            if btn_grp is not None:
                # Reflect the preset source WITHOUT re-triggering a load: the
                # data is already in, and going through _on_source_changed here
                # would reload whatever the combo happens to be showing.
                rb_preset.setChecked(True)
                preset_combo.blockSignals(True)
                idx = preset_combo.findData(pending_preset)
                if idx >= 0:
                    preset_combo.setCurrentIndex(idx)
                preset_combo.blockSignals(False)
                preset_combo.setEnabled(True)
                measure_btn.setEnabled(False)
            btn_save_preset.setEnabled(True)
        else:
            # It could not be applied (bad grid, missing file): forget it so the
            # step does not retry on every visit.
            set_preset_preload(wizard, standard.key, None)

    stored = wizard.perm_calibration.get_measurement(standard.key) if already else None
    _render(wizard, standard, name,
            _trace_colors[2] if (btn_grp is not None and pending_preset) else color,
            std_texts, stored, state["show_indicative"], state.get("show_raw", False))
    wizard.next_button.setEnabled(already)

    def _btn_clicked():
        mode = btn_grp.checkedId() if btn_grp is not None else 0
        trace_color = _trace_colors.get(mode, color) if btn_grp is not None else color
        if mode == 0:
            _on_measure(wizard, standard, name, trace_color, measure_btn, std_texts, state)
        elif mode == 1:
            _on_import(wizard, standard, name, trace_color, measure_btn, std_texts, state)

    measure_btn.clicked.connect(_btn_clicked)


def _success_text(std_texts, name):
    return std_texts.get("status_success", "{name} successfully measured").format(name=name)


def _ask_s1p_matching_sweep(wizard, std_texts, dialog_title=None):
    """Prompt for a .s1p file and return (freqs, s11) validated against the sweep.

    Returns None when the user cancels or the file is rejected (the corresponding
    message box has already been shown). Shared by every import action of the
    wizard so that they all enforce the same frequency-grid contract.
    """
    filepath, _ = QFileDialog.getOpenFileName(
        wizard,
        dialog_title or std_texts.get("import_dialog_title", "Import S11 (.s1p)"),
        "",
        "Touchstone 1-port (*.s1p);;All files (*)",
    )
    if not filepath:
        return None  # user cancelled

    # Validate extension
    if not filepath.lower().endswith(".s1p"):
        QMessageBox.warning(
            wizard,
            std_texts.get("import_error_title", "Import Error"),
            std_texts.get("import_error_not_s1p", "The selected file is not a .s1p Touchstone file."),
        )
        return None

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
        return None

    # Validate frequency grid against configured sweep
    sw_n     = wizard.get_sweep_steps()
    sw_start = float(wizard.get_sweep_start_frequency())
    sw_stop  = float(wizard.get_sweep_stop_frequency())
    f_tol    = 1e-3  # Hz

    if len(freqs) != sw_n or abs(freqs[0] - sw_start) > f_tol or abs(freqs[-1] - sw_stop) > f_tol:
        message = std_texts.get(
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
        )

        box = QMessageBox(wizard)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(std_texts.get("import_error_title", "Import Error"))
        box.setText(message)
        # Debug Mode can adopt the file's own sweep instead of forcing the user
        # to retype it in Configuration (and mistype one of the endpoints).
        adopt_btn = None
        if is_debug_enabled():
            adopt_btn = box.addButton(
                std_texts.get("import_adopt_sweep", "Use the file's sweep"),
                QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()

        if adopt_btn is None or box.clickedButton() is not adopt_btn:
            return None
        if not _adopt_sweep_from_file(wizard, freqs, std_texts):
            return None

    return freqs, s11


def _adopt_sweep_from_file(wizard, freqs, std_texts) -> bool:
    """Point the session sweep at ``freqs``. Returns False if the user backs out.

    Every standard must end up on the SAME grid: ``compute_calibration`` does
    not interpolate. So if something was already measured on the old sweep,
    changing it means dropping those measurements -- ask first.
    """
    already = [k for k, done in wizard.perm_calibration.get_completion_status().items()
               if done and k != "calibration_complete"]
    if already:
        answer = QMessageBox.question(
            wizard,
            std_texts.get("adopt_sweep_title", "Change the configured sweep?"),
            std_texts.get(
                "adopt_sweep_msg",
                "The sweep will change to {n} points, {fs} – {fe}.\n\n"
                "These steps were already measured on the previous sweep and will be "
                "discarded, because every standard must share one frequency grid:\n  {steps}\n\n"
                "Continue?"
            ).format(n=len(freqs), fs=_fmt_freq(freqs[0]), fe=_fmt_freq(freqs[-1]),
                     steps=", ".join(sorted(already))),
            QMessageBox.Yes | QMessageBox.No)
        if answer != QMessageBox.Yes:
            return False
        wizard.perm_calibration.clear_all_measurements()
        wizard._precal_originals = {}
        wizard._precal_open = {}

    wizard.sweep_start_freq = int(round(float(freqs[0])))
    wizard.sweep_stop_freq = int(round(float(freqs[-1])))
    wizard.sweep_steps = int(len(freqs))
    wizard.epsilon_result = None
    logger.info("[standard_screen] sweep adopted from file: %d pts, %s - %s",
                len(freqs), _fmt_freq(freqs[0]), _fmt_freq(freqs[-1]))
    return True


def _on_import(wizard, standard, name, color, button, std_texts, state):
    """Open a .s1p file, validate frequencies, store and render."""
    imported = _ask_s1p_matching_sweep(wizard, std_texts)
    if imported is None:
        return
    freqs, s11 = _store_measurement(wizard, standard.key, imported[0], imported[1])
    set_status(wizard, _success_text(std_texts, name), "lightgreen")
    button.setText(std_texts.get("reimport_button", "Import again"))
    _render(wizard, standard, name, color, std_texts, (freqs, s11),
            state["show_indicative"], state.get("show_raw", False))
    wizard.next_button.setEnabled(True)
    hook = getattr(wizard, "_on_measurement_stored_hook", None)
    if callable(hook):
        hook()


def _fmt_freq(hz: float) -> str:
    """Format Hz as kHz / MHz / GHz string."""
    if hz >= 1e9:
        return f"{hz/1e9:.4g} GHz"
    if hz >= 1e6:
        return f"{hz/1e6:.4g} MHz"
    return f"{hz/1e3:.4g} kHz"


def _resample_to_grid(freqs_src, s11_src, grid):
    """Linear interpolation of Re/Im onto ``grid``.

    Real and imaginary parts are interpolated SEPARATELY (interpolating
    magnitude/phase would wrap); same approach as Touchstone.resamplear in the
    Sonda_2026_py reference (https://github.com/pguzmanUTN/Sonda_2026_py).
    """
    grid = np.asarray(grid, dtype=float)
    freqs_src = np.asarray(freqs_src, dtype=float)
    s11_src = np.asarray(s11_src, dtype=complex)
    re = np.interp(grid, freqs_src, s11_src.real)
    im = np.interp(grid, freqs_src, s11_src.imag)
    return grid, re + 1j * im


def _load_preset_into_step(wizard, standard, name, std_texts, preset_name):
    """Load a stored preset into ``standard``, validating the frequency grid.

    Returns ``(freqs, s11)`` on success, ``None`` if it could not be applied.
    Unlike the previous version, a preset recorded on a different sweep no
    longer slips in silently to blow up later in ``_common_frequency_grid``:
    the user is offered a resample (or adopting the preset's own sweep).
    """
    try:
        freqs, s11, meta = preset_store.load_preset(preset_name)
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(
            wizard,
            std_texts.get("preset_save_error_title", "Preset error"),
            str(exc))
        return None

    sw_n = wizard.get_sweep_steps()
    sw_start = float(wizard.get_sweep_start_frequency())
    sw_stop = float(wizard.get_sweep_stop_frequency())
    f_tol = 1e-3

    mismatch = (len(freqs) != sw_n
                or abs(freqs[0] - sw_start) > f_tol
                or abs(freqs[-1] - sw_stop) > f_tol)

    if mismatch:
        covers = freqs[0] <= sw_start + f_tol and freqs[-1] >= sw_stop - f_tol
        box = QMessageBox(wizard)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(std_texts.get("preset_grid_title", "Preset sweep mismatch"))
        box.setText(std_texts.get(
            "preset_grid_msg",
            "\"{name}\" was recorded on a different sweep.\n\n"
            "Preset: {pn} pts  {ps} – {pe}\n"
            "Sweep:  {sn} pts  {ss} – {se}"
        ).format(name=meta.display_name or preset_name,
                 pn=len(freqs), ps=_fmt_freq(freqs[0]), pe=_fmt_freq(freqs[-1]),
                 sn=sw_n, ss=_fmt_freq(sw_start), se=_fmt_freq(sw_stop)))

        resample_btn = None
        adopt_btn = None
        if covers:
            resample_btn = box.addButton(
                std_texts.get("preset_grid_resample", "Resample onto the configured sweep"),
                QMessageBox.AcceptRole)
        else:
            box.setInformativeText(std_texts.get(
                "preset_grid_no_cover",
                "It cannot be resampled: the preset does not span the whole configured range."))
        if is_debug_enabled():
            adopt_btn = box.addButton(
                std_texts.get("import_adopt_sweep", "Use the file's sweep"),
                QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.exec()

        clicked = box.clickedButton()
        if resample_btn is not None and clicked is resample_btn:
            grid = np.linspace(sw_start, sw_stop, sw_n)
            freqs, s11 = _resample_to_grid(freqs, s11, grid)
            logger.info("[standard_screen] preset '%s' resampled to %d pts", preset_name, sw_n)
        elif adopt_btn is not None and clicked is adopt_btn:
            if not _adopt_sweep_from_file(wizard, freqs, std_texts):
                return None
        else:
            return None

    freqs, s11 = _store_measurement(wizard, standard.key, freqs, s11)
    set_status(wizard, _success_text(std_texts, name), "lightgreen")
    wizard.next_button.setEnabled(True)
    hook = getattr(wizard, "_on_measurement_stored_hook", None)
    if callable(hook):
        hook()
    return freqs, s11


def _do_save_measurement(wizard, descriptor, standard, std_texts):
    """Store what this step currently holds as a preset (.s1p + JSON sidecar)."""
    data = wizard.perm_calibration.get_measurement(standard.key)
    if data is None:
        QMessageBox.warning(
            wizard,
            std_texts.get("preset_save_error_title", "Save preset"),
            std_texts.get("preset_save_no_data",
                          "No measurement to save. Measure or import first."))
        return

    preset_name, ok = QInputDialog.getText(
        wizard,
        std_texts.get("preset_save_title", "Save preset"),
        std_texts.get("preset_save_prompt", "Preset name:"),
        text=_suggested_preset_name(wizard, descriptor, standard))
    if not ok or not preset_name.strip():
        return
    preset_name = preset_name.strip()

    if preset_store.preset_exists(preset_name):
        answer = QMessageBox.question(
            wizard,
            std_texts.get("preset_overwrite_title", "Overwrite?"),
            std_texts.get("preset_overwrite_msg",
                          '"{n}" already exists. Overwrite?').format(n=preset_name),
            QMessageBox.Yes | QMessageBox.No)
        if answer != QMessageBox.Yes:
            return

    freqs, s11 = data
    meta = preset_store.PresetMeta(
        name=preset_name,
        display_name=preset_name,
        liquid_key=_preset_liquid_key(wizard, standard),
        role=_preset_role(standard),
        source=preset_store.SOURCE_MEASURED,
        instrument=getattr(getattr(wizard, "vna_device", None), "name", "") or "",
        temperature_c=float(getattr(wizard, "temperature_c", 25.0)),
        technique=getattr(descriptor, "id", ""),
        precal_open_applied=standard.key in getattr(wizard, "_precal_originals", {}),
        origin_note=std_texts.get("preset_saved_from_wizard",
                                  "Guardado desde el asistente de caracterizacion."),
    )
    try:
        preset_store.save_preset(preset_name, freqs, s11, meta)
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(
            wizard, std_texts.get("preset_save_error_title", "Save preset"), str(exc))
        return

    QMessageBox.information(
        wizard,
        std_texts.get("preset_saved_title", "Saved"),
        std_texts.get("preset_saved_msg", 'Preset "{n}" saved.').format(n=preset_name))


def _preset_role(standard) -> str:
    if standard.kind is StandardKind.REFERENCE_LIQUID:
        return preset_store.ROLE_REFERENCE
    if standard.kind is StandardKind.DUT:
        return preset_store.ROLE_DUT
    return standard.key if standard.key in (preset_store.ROLE_OPEN, preset_store.ROLE_SHORT) \
        else preset_store.ROLE_REFERENCE


def _preset_liquid_key(wizard, standard) -> str:
    """Liquid a saved sweep belongs to (Open/Short are standards, not liquids)."""
    if standard.kind is StandardKind.REFERENCE_LIQUID:
        return selected_liquid_key(wizard, standard) or standard.key
    if standard.key == "open":
        return "air"
    if standard.key == "short":
        return "short"
    # The unknown liquid has no known key: use its user-given name, slugged.
    unknown = (getattr(wizard, "unknown_liquid_name", "") or "").strip().lower()
    return unknown.replace(" ", "_") or "unknown"


def _suggested_preset_name(wizard, descriptor, standard) -> str:
    """Build the pre-filled name offered by the "Save as preset…" dialog.

    Packs everything needed to tell two presets apart later: liquid, technique,
    temperature, sweep, point count, whether OPEN normalization was applied and
    when it was captured. Long on purpose — the file name is the only metadata a
    .s1p carries today.
    """
    from datetime import datetime

    parts = [selected_liquid_key(wizard, standard) or standard.key]

    technique_id = getattr(descriptor, "id", "")
    if technique_id:
        parts.append(technique_id)

    try:
        parts.append(f"{float(getattr(wizard, 'temperature_c', 25.0)):.1f}C")
    except (TypeError, ValueError):
        pass

    try:
        start = _fmt_freq(float(wizard.get_sweep_start_frequency())).replace(" ", "")
        stop = _fmt_freq(float(wizard.get_sweep_stop_frequency())).replace(" ", "")
        parts.append(f"{start}-{stop}")
        parts.append(f"{int(wizard.get_sweep_steps())}pts")
    except Exception:
        logger.debug("[standard_screen] sweep unavailable for the suggested preset name")

    if standard.key in getattr(wizard, "_precal_originals", {}):
        parts.append("precal")

    parts.append(datetime.now().strftime("%Y%m%d-%H%M%S"))

    name = "_".join(str(p) for p in parts if p)
    for bad in '<>:"/\\|?*':
        name = name.replace(bad, "-")
    return name


def _store_measurement(wizard, std_key, freqs_raw, s11_raw):
    """Store a raw S11, applying pre-cal normalization if active for this step.

    If wizard._precal_open[std_key] exists and the OPEN grid matches, the raw
    value is saved to _precal_originals and the normalized one is written to
    perm_calibration. On a grid mismatch the pre-cal is discarded (logged) and
    any registered _precal_discard_hooks[std_key] is called so the UI can hide
    the "Quitar pre-cal" button.

    Returns (freqs, s11_stored) — whatever was actually written.
    """
    freqs_raw = np.asarray(freqs_raw, dtype=float)
    s11_raw = np.asarray(s11_raw, dtype=complex)

    if not hasattr(wizard, "_precal_open"):
        wizard._precal_open = {}
    if not hasattr(wizard, "_precal_originals"):
        wizard._precal_originals = {}

    s11_to_store = s11_raw
    if std_key in wizard._precal_open:
        freqs_open, s11_open = wizard._precal_open[std_key]
        f_tol = 1e-3
        grid_ok = (
            len(freqs_open) == len(freqs_raw)
            and abs(float(freqs_open[0]) - float(freqs_raw[0])) < f_tol
            and abs(float(freqs_open[-1]) - float(freqs_raw[-1])) < f_tol
        )
        if grid_ok:
            wizard._precal_originals[std_key] = (freqs_raw.copy(), s11_raw.copy())
            s11_to_store = s11_raw / np.asarray(s11_open, dtype=complex)
        else:
            logger.warning(
                "[standard_screen] pre-cal OPEN grid mismatch for %s — discarding", std_key
            )
            wizard._precal_open.pop(std_key)
            wizard._precal_originals.pop(std_key, None)
            hook = getattr(wizard, "_precal_discard_hooks", {}).get(std_key)
            if callable(hook):
                try:
                    hook()
                except Exception:
                    pass

    wizard.perm_calibration.set_measurement(std_key, freqs_raw, s11_to_store)
    wizard.epsilon_result = None
    return freqs_raw, s11_to_store


def _on_measure(wizard, standard, name, color, button, std_texts, state):
    result = run_s11_sweep(wizard)
    if result is None:
        return
    freqs, s11 = _store_measurement(wizard, standard.key, result[0], result[1])
    set_status(wizard, _success_text(std_texts, name), "lightgreen")
    button.setText(std_texts.get("remeasure_button", "Measure again"))
    _render(wizard, standard, name, color, std_texts, (freqs, s11),
            state["show_indicative"], state.get("show_raw", False))
    wizard.next_button.setEnabled(True)
    hook = getattr(wizard, "_on_measurement_stored_hook", None)
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


def _render(wizard, standard, name, color, std_texts, measured, show_indicative, show_raw=False):
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
    elif standard.kind is StandardKind.REFERENCE_LIQUID and show_indicative and \
            selected_liquid_key(wizard, standard):
        try:
            liquid = get_reference_liquid(selected_liquid_key(wizard, standard))
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

    if show_raw and standard.kind is StandardKind.REFERENCE_LIQUID:
        raw_data = getattr(wizard, "_precal_originals", {}).get(standard.key)
        if raw_data is not None:
            _, s11_raw = raw_data
            s11_raw = np.asarray(s11_raw, dtype=complex)
            ax.plot(np.real(s11_raw), np.imag(s11_raw), "--", color="#999999",
                    linewidth=1.3, zorder=2, alpha=0.75)
            handles.append(Line2D([0], [0], color="#999999", linestyle="--", alpha=0.75))
            labels.append(r"$S_{11}$ — raw")

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
        key = selected_liquid_key(wizard, standard)
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


def _open_precal_dialog(wizard, standard, name, color, std_texts, state, btn_delete_precal):
    """Open-normalization pre-calibration dialog (vertical single-column layout).

    Measures an OPEN (probe in air) and normalizes the stored liquid S11 by
    dividing element-wise: s11_norm = s11_liquid / s11_open.
    The original S11 is saved in wizard._precal_originals so it can be restored.
    """
    from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import create_wizard_smith_chart, SmithChartManager

    dlg = QDialog(wizard)
    dlg.setWindowTitle(std_texts.get("precal_dialog_title", "Pre-calibración — Normalización con OPEN"))
    dlg.setMinimumSize(460, 620)
    dlg.resize(500, 700)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(6)

    # Title
    title_lbl = QLabel(std_texts.get("precal_title", "Normalización con OPEN"))
    title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #4da6ff;")
    layout.addWidget(title_lbl)

    # Description
    desc_lbl = QLabel(std_texts.get(
        "precal_description",
        "Colocá la sonda en el aire (OPEN) y medí. La normalización divide "
        "el S₁₁ del líquido por el S₁₁ del OPEN, corrigiendo los efectos "
        "del cable y los conectores.\n\ns₁₁_norm = s₁₁_líquido / s₁₁_OPEN"
    ))
    desc_lbl.setWordWrap(True)
    desc_lbl.setStyleSheet("font-size: 11px; color: #aaaaaa;")
    layout.addWidget(desc_lbl)

    # Measure button
    _measure_open_btn = QPushButton(std_texts.get("precal_measure_button", "Medir OPEN"))
    _measure_open_btn.setFixedHeight(34)
    _measure_open_btn.setFixedWidth(200)
    layout.addWidget(_measure_open_btn, alignment=Qt.AlignHCenter)

    # Import the OPEN from a file (Debug Mode): without it the pre-calibration
    # cannot be exercised at all when there is no probe available.
    _import_open_btn = None
    if is_debug_enabled():
        _import_open_btn = QPushButton(std_texts.get("precal_import_button", "Import OPEN .s1p"))
        _import_open_btn.setFixedHeight(26)
        _import_open_btn.setFixedWidth(200)
        _import_open_btn.setStyleSheet(
            "QPushButton { font-size: 11px; color: #666677; border: 1px dashed #444455;"
            " border-radius: 4px; padding: 0 12px; }"
            " QPushButton:hover { color: #aaaacc; border-color: #6666aa; }"
        )
        layout.addSpacing(4)
        layout.addWidget(_import_open_btn, alignment=Qt.AlignHCenter)

    # Status label
    _status_lbl = QLabel(std_texts.get("precal_status_ready", "Sin medición del OPEN"))
    _status_lbl.setAlignment(Qt.AlignCenter)
    _status_lbl.setStyleSheet("font-size: 11px; padding: 2px; color: gray;")
    layout.addWidget(_status_lbl)

    # Smith chart in a container widget that stretches to fill remaining space
    chart_widget = QWidget()
    chart_layout = QVBoxLayout(chart_widget)
    chart_layout.setContentsMargins(0, 0, 0, 0)
    chart_layout.setSpacing(0)
    fig, ax, canvas = create_wizard_smith_chart(
        start_freq=wizard.get_sweep_start_frequency(),
        stop_freq=wizard.get_sweep_stop_frequency(),
        num_points=wizard.get_sweep_steps(),
        container_layout=chart_layout,
        figsize=(4.4, 4.4),
    )
    layout.addWidget(chart_widget, stretch=1)

    # Apply / Cancel
    bottom_row = QHBoxLayout()
    bottom_row.addStretch(1)
    apply_btn = QPushButton(std_texts.get("precal_apply", "Aplicar"))
    apply_btn.setFixedHeight(30)
    apply_btn.setEnabled(False)
    apply_btn.setStyleSheet(
        "QPushButton { color: #4da6ff; border: 1px solid #4da6ff;"
        " border-radius: 4px; padding: 0 20px; font-size: 12px; }"
        " QPushButton:disabled { color: #2a4a6a; border-color: #2a4a6a; }"
        " QPushButton:hover { background: #0a1828; }"
    )
    cancel_btn = QPushButton(std_texts.get("precal_cancel", "Cancelar"))
    cancel_btn.setFixedHeight(30)
    cancel_btn.setStyleSheet(
        "QPushButton { color: #888888; border: 1px solid #484858;"
        " border-radius: 4px; padding: 0 20px; font-size: 12px; }"
        " QPushButton:hover { color: #cccccc; border-color: #707080; }"
    )
    bottom_row.addWidget(apply_btn)
    bottom_row.addWidget(cancel_btn)
    layout.addLayout(bottom_row)

    _open_data = [None]  # [(freqs, s11_open)]

    def _accept_open(freqs_open, s11_open, trace_color="red"):
        """Store the OPEN sweep, plot it and enable Apply."""
        s11_arr = np.asarray(s11_open, dtype=complex)
        _open_data[0] = (np.asarray(freqs_open, dtype=float), s11_arr)

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
        ax.set_title(r"$S_{11}$ — OPEN", fontsize=13, pad=20, color=builder.config.text_color)
        ax.plot(np.real(s11_arr), np.imag(s11_arr), "o-", color=trace_color,
                linewidth=2, markersize=3, zorder=3)
        builder.add_start_point_marker(s11_arr, color=trace_color)
        ax.legend(
            [Line2D([0], [0], color=trace_color)], [r"$S_{11}$ — OPEN"],
            loc="upper left", bbox_to_anchor=(-0.22, 1.14),
            bbox_transform=ax.transAxes, fontsize=8.5, framealpha=0.93,
        )
        canvas.draw()

        _status_lbl.setText(std_texts.get("precal_status_done", "OPEN medido ✓"))
        _status_lbl.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")
        apply_btn.setEnabled(True)

    def _do_measure_open():
        from PySide6.QtWidgets import QApplication
        _status_lbl.setText(std_texts.get("precal_status_measuring", "Measuring…"))
        _status_lbl.setStyleSheet("font-size: 11px; padding: 2px; color: orange;")
        QApplication.processEvents()
        result = run_s11_sweep(wizard)
        if result is None:
            _status_lbl.setText(std_texts.get("precal_status_ready", "Sin medición del OPEN"))
            _status_lbl.setStyleSheet("font-size: 11px; padding: 2px; color: gray;")
            return
        _accept_open(result[0], result[1], trace_color="red")

    def _do_import_open():
        imported = _ask_s1p_matching_sweep(
            wizard, std_texts,
            std_texts.get("precal_import_dialog_title", "Import OPEN S11 (.s1p)"),
        )
        if imported is None:
            return
        _accept_open(imported[0], imported[1], trace_color="#ff9f43")

    def _do_apply():
        freqs_open, s11_open = _open_data[0]
        freqs_liq, s11_liq = wizard.perm_calibration.get_measurement(standard.key)
        if not hasattr(wizard, "_precal_open"):
            wizard._precal_open = {}
        if not hasattr(wizard, "_precal_originals"):
            wizard._precal_originals = {}
        # Persist the OPEN so future measure/import/preset re-applies normalization.
        wizard._precal_open[standard.key] = (
            np.asarray(freqs_open, dtype=float).copy(),
            np.asarray(s11_open, dtype=complex).copy(),
        )
        wizard._precal_originals[standard.key] = (
            np.asarray(freqs_liq, dtype=float).copy(),
            np.asarray(s11_liq, dtype=complex).copy(),
        )
        s11_norm = np.asarray(s11_liq, dtype=complex) / np.asarray(s11_open, dtype=complex)
        wizard.perm_calibration.set_measurement(standard.key, freqs_liq, s11_norm)
        wizard.epsilon_result = None
        state["show_raw"] = False
        _render(wizard, standard, name, color, std_texts, (freqs_liq, s11_norm), state["show_indicative"], False)
        btn_delete_precal.setVisible(True)
        hook = getattr(wizard, "_on_precal_applied_hook", None)
        if callable(hook):
            hook()
        dlg.accept()

    _measure_open_btn.clicked.connect(_do_measure_open)
    if _import_open_btn is not None:
        _import_open_btn.clicked.connect(_do_import_open)
    apply_btn.clicked.connect(_do_apply)
    cancel_btn.clicked.connect(dlg.reject)

    dlg.exec()
