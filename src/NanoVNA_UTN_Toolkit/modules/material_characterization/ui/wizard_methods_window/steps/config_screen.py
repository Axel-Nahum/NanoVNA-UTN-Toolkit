"""
Configuration screen of the characterization wizard.

EN: Lets the user set the frequency sweep (start/stop/points) and the
    MEASUREMENT temperature, name the unknown liquid, and CHOOSE the reference
    liquids. Each reference row is: liquid combo + a combo of stored
    measurements of that liquid (default None) + a delete button for the
    selected preset. The sweep is constrained to the CONNECTED nanoVNA's
    capabilities, EXCEPT in Debug Mode, where arbitrary values are allowed so
    that .s1p files from other campaigns can be imported. Committing updates
    the wizard session and the permittivity calibration manager.

ES: Permite configurar el barrido de frecuencia (inicio/fin/puntos) y la
    temperatura de MEDICION, nombrar el liquido incognita y ELEGIR los liquidos
    de referencia. Cada fila de referencia es: combo de liquido + combo de
    mediciones guardadas de ese liquido (por defecto None) + boton para
    eliminar el preset seleccionado. El barrido se limita segun el nanoVNA
    CONECTADO, SALVO en modo Debug, donde se admiten valores arbitrarios para
    poder importar .s1p de otras campanas. Al confirmar se actualiza la sesion
    del asistente y el administrador de calibracion.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QFormLayout, QGroupBox, QPushButton, QVBoxLayout, QWidget,
)

from NanoVNA_UTN_Toolkit.shared.utils.preferences.debug_mode import is_debug_enabled
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid, list_reference_liquids,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import preset_store
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.session_liquids import (
    ensure_defaults, preset_preload, selected_liquid_key, set_liquid_key, set_preset_preload,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.step_sidebar import (
    build_step_sidebar,
)

logger = logging.getLogger(__name__)

_UNIT_MULT = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
_DEFAULT_POINTS = [11, 51, 101, 201, 301, 401, 501, 1023]
_UNKNOWN_NAME_MAXLEN = 80

# Debug Mode lifts the device limits so that a sweep can be made to match ANY
# .s1p on disk. These bounds only keep the spin boxes sane; they are not a
# claim about what the instrument can do (see _sweep_exceeds_device).
_DEBUG_MIN_HZ = 1.0
_DEBUG_MAX_HZ = 1e12
_DEBUG_MAX_POINTS = 20000


def _device_caps(wizard):
    """Return (name, valid_points list, min_hz, max_hz) for the connected device."""
    device = getattr(wizard, "vna_device", None)
    if device is None:
        return None, _DEFAULT_POINTS, 50_000, 1_500_000_000
    name = getattr(device, "name", type(device).__name__)
    points = list(getattr(device, "valid_datapoints", None) or _DEFAULT_POINTS)
    points = sorted(set(int(p) for p in points))
    min_hz = int(getattr(device, "sweep_min_freq_hz", 50_000) or 50_000)
    max_hz = int(getattr(device, "sweep_max_freq_hz", 0) or 0) or 1_500_000_000
    return name, points, min_hz, max_hz


def build_config_screen(wizard, descriptor, step_def):
    texts = load_text("characterization_wizard.json")
    cfg = texts.get("config", {})
    liquids = texts.get("liquids", {})

    wizard.title_label.setText(cfg.get("title", "Measurement Configuration"))

    dev_name, valid_points, min_hz, max_hz = _device_caps(wizard)

    # Debug Mode: the sweep stops being bounded by the instrument so that files
    # recorded elsewhere (e.g. 2000 pts / 1 MHz-2 GHz on a Copper Mountain R60)
    # can be described exactly and therefore imported. The device limits are
    # still remembered, to warn when the configured sweep is not measurable.
    debug_mode = is_debug_enabled()
    wizard._debug_sweep = debug_mode
    wizard._device_limits = (min_hz, max_hz, tuple(valid_points))
    lim_min_hz = _DEBUG_MIN_HZ if debug_mode else min_hz
    lim_max_hz = _DEBUG_MAX_HZ if debug_mode else max_hz

    left_half_layout = QHBoxLayout()
    left_half_layout.setContentsMargins(0, 0, 0, 0)
    left_half_layout.setSpacing(8)
    left_half_layout.addWidget(build_step_sidebar(wizard, descriptor, texts), stretch=0)

    root = QVBoxLayout()
    root.setSpacing(14)

    # --- Connected device info ------------------------------------------- #
    if dev_name:
        dev_str = cfg.get("device_template",
                          "Connected device: {name}  |  Range: {fmin}–{fmax}  |  Valid points: {points}")
        dev_label = QLabel(dev_str.format(
            name=dev_name,
            fmin=_fmt_hz(min_hz), fmax=_fmt_hz(max_hz),
            points=", ".join(str(p) for p in valid_points),
        ))
    else:
        dev_label = QLabel(cfg.get("no_device", "No nanoVNA connected (using default limits)."))
    dev_label.setWordWrap(True)
    dev_label.setStyleSheet("font-size: 12px; color: #5ab3ff; border: none; background: transparent;")

    info_card = QWidget()
    info_card.setObjectName("infoCard")
    info_card.setStyleSheet(
        "QWidget#infoCard { background-color: #12263d; border: 1px solid #2d5a8e; border-radius: 6px; }"
    )
    info_card_layout = QHBoxLayout(info_card)
    info_card_layout.setContentsMargins(12, 8, 12, 8)
    info_card_layout.addWidget(dev_label)
    root.addWidget(info_card)

    # --- Sweep configuration --------------------------------------------- #
    sweep_group = QGroupBox(cfg.get("sweep_title", "Sweep Configuration"))
    sweep_form = QFormLayout(sweep_group)
    sweep_form.setVerticalSpacing(10)
    sweep_form.setHorizontalSpacing(16)

    wizard.start_freq_input = QDoubleSpinBox()
    wizard.start_freq_input.setDecimals(4)
    wizard.start_freq_input.setRange(0.0001, 1e12)
    wizard.start_freq_unit = QComboBox()
    wizard.start_freq_unit.addItems(list(_UNIT_MULT))

    wizard.stop_freq_input = QDoubleSpinBox()
    wizard.stop_freq_input.setDecimals(4)
    wizard.stop_freq_input.setRange(0.0001, 1e12)
    wizard.stop_freq_unit = QComboBox()
    wizard.stop_freq_unit.addItems(list(_UNIT_MULT))

    wizard.points_input = QComboBox()
    wizard.points_input.addItems([str(p) for p in valid_points])
    if debug_mode:
        # Editable so any point count can be typed, not just the device list.
        wizard.points_input.setEditable(True)
        wizard.points_input.setValidator(QIntValidator(2, _DEBUG_MAX_POINTS))
        wizard.points_input.setInsertPolicy(QComboBox.NoInsert)

    sweep_form.addRow(cfg.get("start_freq", "Start Frequency:"),
                      _freq_row(wizard.start_freq_input, wizard.start_freq_unit))
    sweep_form.addRow(cfg.get("stop_freq", "Stop Frequency:"),
                      _freq_row(wizard.stop_freq_input, wizard.stop_freq_unit))
    sweep_form.addRow(cfg.get("points", "Number of Points:"), wizard.points_input)

    # Shown only when the configured sweep is outside what the device supports.
    wizard.sweep_warning_label = QLabel("")
    wizard.sweep_warning_label.setWordWrap(True)
    wizard.sweep_warning_label.setStyleSheet(
        "color: #ffa94d; font-size: 11px; font-weight: bold; border: none;")
    wizard.sweep_warning_label.setVisible(False)
    sweep_form.addRow(wizard.sweep_warning_label)
    root.addWidget(sweep_group)

    # --- Unknown liquid + temperature ------------------------------------ #
    sample_group = QGroupBox(cfg.get("sample_title", "Sample"))
    sample_form = QFormLayout(sample_group)
    sample_form.setVerticalSpacing(10)
    sample_form.setHorizontalSpacing(16)

    wizard.unknown_name_input = QLineEdit()
    wizard.unknown_name_input.setMaxLength(_UNKNOWN_NAME_MAXLEN)
    wizard.unknown_name_input.setPlaceholderText(
        cfg.get("unknown_placeholder", "e.g. tap water, glycerin solution…")
    )
    sample_form.addRow(cfg.get("unknown_name", "Unknown liquid name:"), wizard.unknown_name_input)

    wizard.temperature_input = QDoubleSpinBox()
    wizard.temperature_input.setDecimals(1)
    wizard.temperature_input.setRange(-50.0, 200.0)
    wizard.temperature_input.setSuffix(" °C")
    sample_form.addRow(cfg.get("temperature", "Measurement temperature:"), wizard.temperature_input)

    temp_help = QLabel(cfg.get(
        "temperature_help",
        "All liquids (the reference liquids and the sample) must be at this same, "
        "stable temperature. It sets the reference liquids' known permittivity.",
    ))
    temp_help.setWordWrap(True)
    temp_help.setStyleSheet("color: gray; font-style: italic; font-size: 11px;")
    sample_form.addRow(temp_help)
    root.addWidget(sample_group)

    # --- Reference liquids: selectable + optional stored measurement ------ #
    ensure_defaults(wizard, descriptor)

    ref_group = QGroupBox(cfg.get("references_title", "Reference Liquids"))
    ref_form = QFormLayout(ref_group)
    ref_form.setVerticalSpacing(10)
    ref_form.setHorizontalSpacing(16)

    all_liquids = list_reference_liquids()
    wizard.ref_liquid_combos = {}
    wizard.ref_preset_combos = {}

    for i, std in enumerate(descriptor.reference_standards, start=1):
        liquid_combo = QComboBox()
        for liq in all_liquids:
            liquid_combo.addItem(liquids.get(liq.key, liq.display_name), liq.key)
        current = selected_liquid_key(wizard, std)
        idx = liquid_combo.findData(current)
        liquid_combo.setCurrentIndex(idx if idx >= 0 else 0)
        liquid_combo.setMinimumWidth(150)

        preset_combo = QComboBox()
        preset_combo.setMinimumWidth(190)
        preset_combo.setToolTip(cfg.get(
            "preset_tooltip",
            "Optional: load a stored measurement of this liquid instead of measuring it."))

        del_btn = QPushButton("🗑")
        del_btn.setFixedWidth(32)
        del_btn.setToolTip(cfg.get("preset_delete_tooltip", "Delete the selected stored measurement"))
        del_btn.setStyleSheet(
            "QPushButton { color: #ff6b6b; border: 1px solid #ff6b6b; border-radius: 4px; }"
            " QPushButton:hover { background: #3a1a1a; }"
            " QPushButton:disabled { color: #5a2a2a; border-color: #5a2a2a; }")

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        row_layout.addWidget(liquid_combo)
        row_layout.addWidget(preset_combo, stretch=1)
        row_layout.addWidget(del_btn)
        ref_form.addRow(cfg.get(f"reference_{i}", f"Reference {i}:"), row)

        wizard.ref_liquid_combos[std.key] = liquid_combo
        wizard.ref_preset_combos[std.key] = preset_combo

        _bind_reference_row(wizard, descriptor, std, cfg, liquid_combo, preset_combo, del_btn)

    wizard.reference_warning_label = QLabel("")
    wizard.reference_warning_label.setWordWrap(True)
    wizard.reference_warning_label.setStyleSheet(
        "color: #ffa94d; font-size: 11px; font-weight: bold; border: none;")
    wizard.reference_warning_label.setVisible(False)
    ref_form.addRow(wizard.reference_warning_label)

    note = QLabel(cfg.get(
        "references_note",
        "Pick the liquid used as each standard. Optionally load a stored measurement "
        "instead of measuring it in its step."))
    note.setWordWrap(True)
    note.setStyleSheet("color: gray; font-style: italic; font-size: 11px;")
    ref_form.addRow(note)
    root.addWidget(ref_group)
    root.addStretch(1)

    # --- Initialize from session, then wire commits ----------------------- #

    _init_widgets(wizard, valid_points, lim_min_hz, lim_max_hz, debug_mode)
    _commit(wizard, descriptor)

    def on_unit_changed(spin, combo):
        """Keep the same physical frequency when the unit changes, then clamp to device."""
        new_unit = combo.currentText()
        old_unit = getattr(combo, "_prev_unit", new_unit)
        hz = spin.value() * _UNIT_MULT[old_unit]
        _apply_freq_range(spin, new_unit, lim_min_hz, lim_max_hz)
        spin.setValue(hz / _UNIT_MULT[new_unit])   # QDoubleSpinBox clamps to range
        combo._prev_unit = new_unit
        _commit(wizard, descriptor)

    wizard.start_freq_unit.currentIndexChanged.connect(
        lambda *_: on_unit_changed(wizard.start_freq_input, wizard.start_freq_unit))
    wizard.stop_freq_unit.currentIndexChanged.connect(
        lambda *_: on_unit_changed(wizard.stop_freq_input, wizard.stop_freq_unit))

    for w in (wizard.start_freq_input, wizard.stop_freq_input, wizard.temperature_input):
        w.valueChanged.connect(lambda *_: _commit(wizard, descriptor))
    wizard.points_input.currentIndexChanged.connect(lambda *_: _commit(wizard, descriptor))
    if debug_mode:
        wizard.points_input.currentTextChanged.connect(lambda *_: _commit(wizard, descriptor))
    wizard.unknown_name_input.textChanged.connect(lambda *_: _commit(wizard, descriptor))

    wizard.next_button.setEnabled(True)

    form_container = QWidget()
    form_container.setLayout(root)
    left_half_layout.addWidget(form_container, stretch=1)

    left_half = QWidget()
    left_half.setLayout(left_half_layout)

    columns = QHBoxLayout()
    columns.setContentsMargins(0, 0, 0, 0)
    columns.setSpacing(0)
    columns.addWidget(left_half, stretch=1)

    container = QWidget()
    container.setLayout(columns)
    wizard.content_layout.addWidget(container, stretch=1)


def _refresh_preset_combo(wizard, standard, combo, cfg):
    """Repopulate ``combo`` with the stored measurements of the current liquid."""
    liquid_key = selected_liquid_key(wizard, standard)
    previous = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    combo.addItem(cfg.get("preset_none", "None (measure in its step)"), None)
    try:
        presets = preset_store.list_presets(liquid_key=liquid_key)
    except Exception:
        logger.exception("[config_screen] could not list presets")
        presets = []
    for meta in presets:
        combo.addItem(meta.label(), meta.name)
    idx = combo.findData(previous)
    combo.setCurrentIndex(idx if idx >= 0 else 0)
    combo.blockSignals(False)
    return combo.currentData()


def _bind_reference_row(wizard, descriptor, standard, cfg,
                        liquid_combo, preset_combo, del_btn):
    """Wire one reference row: liquid choice, preset choice and preset deletion."""

    def _sync_delete_enabled():
        del_btn.setEnabled(preset_combo.currentData() is not None)

    def _on_liquid_changed():
        key = liquid_combo.currentData()
        if not key:
            return
        set_liquid_key(wizard, standard.key, key)
        # The previous preset belonged to the previous liquid.
        set_preset_preload(wizard, standard.key, None)
        _refresh_preset_combo(wizard, standard, preset_combo, cfg)
        _sync_delete_enabled()
        _commit(wizard, descriptor)

    def _on_preset_changed():
        set_preset_preload(wizard, standard.key, preset_combo.currentData())
        _sync_delete_enabled()

    def _on_delete():
        name = preset_combo.currentData()
        if not name:
            return
        answer = QMessageBox.question(
            wizard,
            cfg.get("preset_delete_title", "Delete stored measurement"),
            cfg.get("preset_delete_msg", 'Delete "{n}" permanently?').format(n=name),
            QMessageBox.Yes | QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            preset_store.delete_preset(name)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(wizard, cfg.get("preset_delete_title", "Delete"), str(exc))
            return
        set_preset_preload(wizard, standard.key, None)
        _refresh_preset_combo(wizard, standard, preset_combo, cfg)
        _sync_delete_enabled()

    liquid_combo.currentIndexChanged.connect(lambda *_: _on_liquid_changed())
    preset_combo.currentIndexChanged.connect(lambda *_: _on_preset_changed())
    del_btn.clicked.connect(_on_delete)

    _refresh_preset_combo(wizard, standard, preset_combo, cfg)
    # Restore a selection made earlier in this session.
    pending = preset_preload(wizard).get(standard.key)
    if pending:
        idx = preset_combo.findData(pending)
        if idx >= 0:
            preset_combo.setCurrentIndex(idx)
    _sync_delete_enabled()


def _sweep_exceeds_device(wizard):
    """Return a human description of how the sweep exceeds the device, or ''."""
    limits = getattr(wizard, "_device_limits", None)
    if not limits:
        return ""
    min_hz, max_hz, valid_points = limits
    problems = []
    if wizard.sweep_start_freq < min_hz or wizard.sweep_stop_freq > max_hz:
        problems.append(f"{_fmt_hz(min_hz)}–{_fmt_hz(max_hz)}")
    if valid_points and wizard.sweep_steps not in valid_points:
        problems.append(f"{', '.join(str(p) for p in valid_points)} pts")
    return " / ".join(problems)


def _update_sweep_warning(wizard, cfg):
    label = getattr(wizard, "sweep_warning_label", None)
    if label is None:
        return
    exceeded = _sweep_exceeds_device(wizard) if getattr(wizard, "_debug_sweep", False) else ""
    if exceeded:
        label.setText(cfg.get(
            "debug_sweep_warning",
            "⚠ Debug Mode: this sweep is outside the connected device's capabilities "
            "({caps}). It is valid for IMPORTING .s1p files, but the instrument "
            "cannot measure it."
        ).format(caps=exceeded))
    label.setVisible(bool(exceeded))


def _update_reference_warning(wizard, descriptor, cfg):
    """Flag duplicated reference liquids and out-of-range temperatures."""
    label = getattr(wizard, "reference_warning_label", None)
    if label is None:
        return
    refs = descriptor.reference_standards
    keys = [selected_liquid_key(wizard, std) for std in refs]
    messages = []

    if len(keys) >= 2 and len(set(k for k in keys if k)) < len([k for k in keys if k]):
        messages.append(cfg.get(
            "references_duplicated",
            "The two reference liquids must be different: two identical standards "
            "carry no extra information and the calibration cannot be solved."))

    temp = float(getattr(wizard, "temperature_c", 25.0))
    for key in keys:
        if not key:
            continue
        try:
            liq = get_reference_liquid(key)
        except KeyError:
            continue
        if temp < liq.temp_min_c or temp > liq.temp_max_c:
            messages.append(cfg.get(
                "temperature_out_of_range",
                "{liquid}: {temp:.1f} °C is outside its tabulated range "
                "[{tmin:.0f}, {tmax:.0f}] °C; its permittivity is extrapolated."
            ).format(liquid=liq.display_name, temp=temp,
                     tmin=liq.temp_min_c, tmax=liq.temp_max_c))

    label.setText("\n".join(messages))
    label.setVisible(bool(messages))
    # A duplicated pair is a hard error: block Next until it is fixed.
    duplicated = len(keys) >= 2 and len(set(k for k in keys if k)) < len([k for k in keys if k])
    wizard.next_button.setEnabled(not duplicated)


def _fmt_hz(hz):
    if hz >= 1e9:
        return f"{hz/1e9:.3g} GHz"
    if hz >= 1e6:
        return f"{hz/1e6:.3g} MHz"
    if hz >= 1e3:
        return f"{hz/1e3:.3g} kHz"
    return f"{hz:.0f} Hz"


def _freq_row(spin, unit_combo):
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(spin)
    h.addWidget(unit_combo)
    return row


def _apply_freq_range(spin, unit, min_hz, max_hz):
    """Constrain a frequency spinbox to the device limits, expressed in ``unit``."""
    mult = _UNIT_MULT[unit]
    spin.setRange(min_hz / mult, max_hz / mult)


def _clamp_hz(hz, min_hz, max_hz):
    return max(min_hz, min(max_hz, hz))


def _best_unit(hz: float) -> str:
    """Return the most readable unit for a frequency value in Hz."""
    if hz >= 1e9:
        return "GHz"
    if hz >= 1e6:
        return "MHz"
    if hz >= 1e3:
        return "kHz"
    return "Hz"


def _init_widgets(wizard, valid_points, min_hz, max_hz, debug_mode=False):
    start_hz = _clamp_hz(getattr(wizard, "sweep_start_freq", 50_000), min_hz, max_hz)
    stop_hz = _clamp_hz(getattr(wizard, "sweep_stop_freq", 1_500_000_000), min_hz, max_hz)
    steps = getattr(wizard, "sweep_steps", 101)
    temp = getattr(wizard, "temperature_c", 25.0)

    start_unit = _best_unit(start_hz)
    wizard.start_freq_unit.setCurrentText(start_unit)
    wizard.start_freq_unit._prev_unit = start_unit
    _apply_freq_range(wizard.start_freq_input, start_unit, min_hz, max_hz)
    wizard.start_freq_input.setValue(start_hz / _UNIT_MULT[start_unit])

    stop_unit = _best_unit(stop_hz)
    wizard.stop_freq_unit.setCurrentText(stop_unit)
    wizard.stop_freq_unit._prev_unit = stop_unit
    _apply_freq_range(wizard.stop_freq_input, stop_unit, min_hz, max_hz)
    wizard.stop_freq_input.setValue(stop_hz / _UNIT_MULT[stop_unit])

    # Choose stored points if valid, else nearest default. In Debug Mode a
    # value the device does not offer is still honoured (typed into the combo).
    if debug_mode and steps not in valid_points:
        wizard.points_input.setEditText(str(steps))
    else:
        target = str(steps) if steps in valid_points else str(valid_points[min(2, len(valid_points) - 1)])
        idx = wizard.points_input.findText(target)
        wizard.points_input.setCurrentIndex(idx if idx >= 0 else 0)

    wizard.temperature_input.setValue(float(temp))
    wizard.unknown_name_input.setText(getattr(wizard, "unknown_liquid_name", "") or "")


def _commit(wizard, descriptor):
    try:
        start = wizard.start_freq_input.value() * _UNIT_MULT[wizard.start_freq_unit.currentText()]
        stop = wizard.stop_freq_input.value() * _UNIT_MULT[wizard.stop_freq_unit.currentText()]
        wizard.sweep_start_freq = int(start)
        wizard.sweep_stop_freq = int(stop)
        # In Debug Mode the combo is editable, so it can hold a half-typed
        # number: keep the previous value instead of crashing the commit.
        try:
            wizard.sweep_steps = int(wizard.points_input.currentText())
        except (TypeError, ValueError):
            wizard.sweep_steps = int(getattr(wizard, "sweep_steps", 101))
        wizard.temperature_c = float(wizard.temperature_input.value())
        wizard.unknown_liquid_name = wizard.unknown_name_input.text().strip()

        refs = descriptor.reference_standards
        if len(refs) >= 2:
            wizard.perm_calibration.set_reference_liquids(
                selected_liquid_key(wizard, refs[0]), selected_liquid_key(wizard, refs[1])
            )
        elif len(refs) == 1:
            wizard.perm_calibration.set_reference_liquids(
                selected_liquid_key(wizard, refs[0]), None
            )
        wizard.temperature_warnings = wizard.perm_calibration.set_temperature(wizard.temperature_c)

        cfg = load_text("characterization_wizard.json").get("config", {})
        _update_sweep_warning(wizard, cfg)
        _update_reference_warning(wizard, descriptor, cfg)
    except Exception as exc:  # noqa: BLE001
        logger.error("[config_screen] commit failed: %s", exc)
