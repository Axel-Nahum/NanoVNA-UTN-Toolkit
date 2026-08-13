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

from NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils import get_calibration_path

_PRESET_DEV_PATH = "modules/material_characterization/calibration/preset_liquids"
_PRESET_EXE_PATH = "modules/material_characterization/calibration/preset_liquids"

# Set to False to hide the dev import button on Open / Short / DUT screens.
_DEV_IMPORT_VISIBLE = True


def _get_preset_path() -> Path:
    path = get_calibration_path(_PRESET_EXE_PATH, _PRESET_DEV_PATH, Path(__file__).resolve())
    path.mkdir(parents=True, exist_ok=True)
    return path


def _refresh_preset_combo(combo: QComboBox) -> None:
    current = combo.currentText()
    combo.clear()
    try:
        names = sorted(p.stem for p in _get_preset_path().glob("*.s1p"))
    except Exception:
        names = []
    for name in names:
        combo.addItem(name)
    idx = combo.findText(current)
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
    wizard._on_ref_measured_hook = None

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
            wizard.perm_calibration.set_measurement(standard.key, freqs, s11_orig)
            wizard.epsilon_result = None
            _render(wizard, standard, name, color, std_texts, (freqs, s11_orig), state["show_indicative"])
            btn_delete_precal_top.setVisible(False)

        btn_delete_precal_top.clicked.connect(_delete_precal)
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

        # Poblar combo con presets existentes
        _refresh_preset_combo(preset_combo)

        # [rb_preset] [combo ────────] — misma fila, Qt los alinea vertical automáticamente
        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(0, 0, 0, 0)
        preset_row.setSpacing(8)
        preset_row.addWidget(rb_preset)
        preset_row.addWidget(preset_combo, stretch=1)
        src_layout.addLayout(preset_row)

        src_layout.addSpacing(8)

        # Botones centrados bajo el ancho del combo
        _rb_offset = rb_preset.sizeHint().width() + 8
        action_row = QHBoxLayout()
        action_row.setSpacing(14)
        action_row.setContentsMargins(_rb_offset, 0, 0, 0)
        action_row.addStretch(1)
        action_row.addWidget(btn_save_preset)
        action_row.addWidget(btn_delete_preset)
        action_row.addStretch(1)
        src_layout.addLayout(action_row)

        def _do_save_preset():
            data = wizard.perm_calibration.get_measurement(standard.key)
            if data is None:
                QMessageBox.warning(wizard,
                    std_texts.get("preset_save_error_title", "Save preset"),
                    std_texts.get("preset_save_no_data", "No measurement to save. Measure or import first."))
                return
            name, ok = QInputDialog.getText(wizard,
                std_texts.get("preset_save_title", "Save preset"),
                std_texts.get("preset_save_prompt", "Preset name:"))
            if not ok or not name.strip():
                return
            name = name.strip()
            dest = _get_preset_path() / f"{name}.s1p"
            if dest.exists():
                ans = QMessageBox.question(wizard,
                    std_texts.get("preset_overwrite_title", "Overwrite?"),
                    std_texts.get("preset_overwrite_msg", '"{n}" already exists. Overwrite?').format(n=name),
                    QMessageBox.Yes | QMessageBox.No)
                if ans != QMessageBox.Yes:
                    return
            try:
                import skrf as rf
                freqs, s11 = data
                net = rf.Network(frequency=freqs, s=s11.reshape(-1, 1, 1), z0=50)
                net.write_touchstone(str(dest))
                _refresh_preset_combo(preset_combo)
                QMessageBox.information(wizard,
                    std_texts.get("preset_saved_title", "Saved"),
                    std_texts.get("preset_saved_msg", 'Preset "{n}" saved.').format(n=name))
            except Exception as exc:
                QMessageBox.critical(wizard,
                    std_texts.get("preset_save_error_title", "Save preset"),
                    str(exc))

        def _do_delete_preset():
            name = preset_combo.currentText()
            if not name:
                return
            ans = QMessageBox.question(wizard,
                std_texts.get("preset_delete_title", "Delete preset"),
                std_texts.get("preset_delete_msg", 'Delete "{n}"?').format(n=name),
                QMessageBox.Yes | QMessageBox.No)
            if ans != QMessageBox.Yes:
                return
            try:
                (_get_preset_path() / f"{name}.s1p").unlink(missing_ok=True)
                _refresh_preset_combo(preset_combo)
            except Exception as exc:
                QMessageBox.critical(wizard,
                    std_texts.get("preset_save_error_title", "Delete preset"), str(exc))

        btn_save_preset.clicked.connect(_do_save_preset)
        btn_delete_preset.clicked.connect(_do_delete_preset)

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
        _lbl_no_preset = std_texts.get("status_no_preset",    "No preset selected")
        _btn_measure   = std_texts.get("measure_button",      "Measure")
        _btn_remeasure = std_texts.get("remeasure_button",    "Measure again")
        _btn_import    = std_texts.get("import_button",       "Import Liquid")

        # Trace color per source mode: 0=measure, 1=import, 2=preset
        _trace_colors = {0: color, 1: "#ff9f43", 2: "#2ecc71"}

        def _on_source_changed(btn_id):
            preset_combo.setEnabled(btn_id == 2)
            btn_delete_preset.setEnabled(btn_id == 2)
            measure_btn.setEnabled(btn_id != 2)
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
                current_preset = preset_combo.currentText()
                if current_preset:
                    _load_preset(current_preset)
                else:
                    wizard.status_label.setText(_lbl_no_preset)
                    wizard.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: gray;")

        def _load_preset(preset_name):
            if not preset_name or btn_grp.checkedId() != 2:
                return
            path = _get_preset_path() / f"{preset_name}.s1p"
            try:
                import skrf as rf
                net = rf.Network(str(path))
                freqs = np.asarray(net.f, dtype=float)
                s11 = np.asarray(net.s[:, 0, 0], dtype=complex)
            except Exception as exc:
                QMessageBox.critical(
                    wizard,
                    std_texts.get("preset_save_error_title", "Preset error"),
                    str(exc),
                )
                return
            wizard.perm_calibration.set_measurement(standard.key, freqs, s11)
            wizard.epsilon_result = None
            set_status(wizard, _success_text(std_texts, name), "lightgreen")
            _render(wizard, standard, name, _trace_colors[2], std_texts, (freqs, s11), state["show_indicative"])
            wizard.next_button.setEnabled(True)

        btn_grp.idClicked.connect(_on_source_changed)
        preset_combo.currentTextChanged.connect(_load_preset)

        def _show_save_after_measure():
            btn_save_preset.setEnabled(True)

        wizard._on_ref_measured_hook = _show_save_after_measure

    mid.addStretch(1)

    if not is_reference and _DEV_IMPORT_VISIBLE:
        dev_import_btn = QPushButton("Import")
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
        trace_color = _trace_colors.get(mode, color) if btn_grp is not None else color
        if mode == 0:
            _on_measure(wizard, standard, name, trace_color, measure_btn, std_texts, state)
        elif mode == 1:
            _on_import(wizard, standard, name, trace_color, measure_btn, std_texts, state)

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
        freqs_open, s11_open = result
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
        ax.plot(np.real(s11_arr), np.imag(s11_arr), "o-", color="red",
                linewidth=2, markersize=3, zorder=3)
        builder.add_start_point_marker(s11_arr, color="red")
        ax.legend(
            [Line2D([0], [0], color="red")], [r"$S_{11}$ — OPEN"],
            loc="upper left", bbox_to_anchor=(-0.22, 1.14),
            bbox_transform=ax.transAxes, fontsize=8.5, framealpha=0.93,
        )
        canvas.draw()

        _status_lbl.setText(std_texts.get("precal_status_done", "OPEN medido ✓"))
        _status_lbl.setStyleSheet("font-size: 12px; padding: 4px; color: lightgreen;")
        apply_btn.setEnabled(True)

    def _do_apply():
        freqs_open, s11_open = _open_data[0]
        freqs_liq, s11_liq = wizard.perm_calibration.get_measurement(standard.key)
        if not hasattr(wizard, "_precal_originals"):
            wizard._precal_originals = {}
        wizard._precal_originals[standard.key] = (freqs_liq.copy(), np.asarray(s11_liq, dtype=complex).copy())
        s11_norm = np.asarray(s11_liq, dtype=complex) / np.asarray(s11_open, dtype=complex)
        wizard.perm_calibration.set_measurement(standard.key, freqs_liq, s11_norm)
        wizard.epsilon_result = None
        _render(wizard, standard, name, color, std_texts, (freqs_liq, s11_norm), state["show_indicative"])
        btn_delete_precal.setVisible(True)
        dlg.accept()

    _measure_open_btn.clicked.connect(_do_measure_open)
    apply_btn.clicked.connect(_do_apply)
    cancel_btn.clicked.connect(dlg.reject)

    dlg.exec()
