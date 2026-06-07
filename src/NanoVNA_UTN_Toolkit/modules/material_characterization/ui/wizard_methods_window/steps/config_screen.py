"""
Configuration screen of the characterization wizard.

EN: Lets the user set the frequency sweep (start/stop/points) and the
    MEASUREMENT temperature, name the unknown liquid, and shows the two
    reference liquids. The sweep points and frequency ranges are constrained to
    the CONNECTED nanoVNA's capabilities, which are displayed. In the MVP the
    reference liquids are fixed (Water + IPA). Committing updates the wizard
    session and the permittivity calibration manager.

ES: Permite configurar el barrido de frecuencia (inicio/fin/puntos) y la
    temperatura de MEDICION, nombrar el liquido incognita, y muestra los dos
    liquidos de referencia. Los puntos y rangos de frecuencia se limitan segun
    el nanoVNA CONECTADO, cuyas caracteristicas se muestran. En el MVP los
    liquidos de referencia son fijos (Agua + IPA). Al confirmar se actualiza la
    sesion del asistente y el administrador de calibracion.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit,
    QFormLayout, QGroupBox, QVBoxLayout, QWidget,
)

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.step_sidebar import (
    build_step_sidebar,
)

logger = logging.getLogger(__name__)

_UNIT_MULT = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
_DEFAULT_POINTS = [11, 51, 101, 201, 301, 401, 501, 1023]
_UNKNOWN_NAME_MAXLEN = 80


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

    columns = QHBoxLayout()
    columns.addWidget(build_step_sidebar(wizard, descriptor, texts), stretch=0)

    root = QVBoxLayout()
    root.setSpacing(12)

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
    dev_label.setStyleSheet("font-size: 12px; color: #4da6ff; padding: 2px;")
    root.addWidget(dev_label)

    # --- Sweep configuration --------------------------------------------- #
    sweep_group = QGroupBox(cfg.get("sweep_title", "Sweep Configuration"))
    sweep_form = QFormLayout(sweep_group)

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

    sweep_form.addRow(cfg.get("start_freq", "Start Frequency:"),
                      _freq_row(wizard.start_freq_input, wizard.start_freq_unit))
    sweep_form.addRow(cfg.get("stop_freq", "Stop Frequency:"),
                      _freq_row(wizard.stop_freq_input, wizard.stop_freq_unit))
    sweep_form.addRow(cfg.get("points", "Number of Points:"), wizard.points_input)
    root.addWidget(sweep_group)

    # --- Unknown liquid + temperature ------------------------------------ #
    sample_group = QGroupBox(cfg.get("sample_title", "Sample"))
    sample_form = QFormLayout(sample_group)

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

    # --- Reference liquids (fixed in MVP) -------------------------------- #
    ref_group = QGroupBox(cfg.get("references_title", "Reference Liquids"))
    ref_form = QFormLayout(ref_group)
    for i, std in enumerate(descriptor.reference_standards, start=1):
        key = std.default_liquid_key
        name = liquids.get(key, get_reference_liquid(key).display_name) if key else "-"
        ref_form.addRow(cfg.get(f"reference_{i}", f"Reference {i}:"), QLabel(name))
    note = QLabel(cfg.get("fixed_note",
                          "In this version the reference liquids are fixed (configurable in a future version)."))
    note.setWordWrap(True)
    note.setStyleSheet("color: gray; font-style: italic; font-size: 11px;")
    ref_form.addRow(note)
    root.addWidget(ref_group)
    root.addStretch(1)

    # --- Initialize from session, then wire commits ----------------------- #
    _init_widgets(wizard, valid_points, min_hz, max_hz)
    _commit(wizard, descriptor)

    def on_unit_changed(spin, combo):
        """Keep the same physical frequency when the unit changes, then clamp to device."""
        new_unit = combo.currentText()
        old_unit = getattr(combo, "_prev_unit", new_unit)
        hz = spin.value() * _UNIT_MULT[old_unit]
        _apply_freq_range(spin, new_unit, min_hz, max_hz)
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
    wizard.unknown_name_input.textChanged.connect(lambda *_: _commit(wizard, descriptor))

    wizard.next_button.setEnabled(True)

    form_container = QWidget()
    form_container.setLayout(root)
    columns.addWidget(form_container, stretch=1)

    container = QWidget()
    container.setLayout(columns)
    wizard.content_layout.addWidget(container, alignment=Qt.AlignTop)


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


def _init_widgets(wizard, valid_points, min_hz, max_hz):
    start_hz = _clamp_hz(getattr(wizard, "sweep_start_freq", 50_000), min_hz, max_hz)
    stop_hz = _clamp_hz(getattr(wizard, "sweep_stop_freq", 1_500_000_000), min_hz, max_hz)
    steps = getattr(wizard, "sweep_steps", 101)
    temp = getattr(wizard, "temperature_c", 25.0)

    wizard.start_freq_unit.setCurrentText("kHz")
    wizard.start_freq_unit._prev_unit = "kHz"
    _apply_freq_range(wizard.start_freq_input, "kHz", min_hz, max_hz)
    wizard.start_freq_input.setValue(start_hz / _UNIT_MULT["kHz"])

    wizard.stop_freq_unit.setCurrentText("MHz")
    wizard.stop_freq_unit._prev_unit = "MHz"
    _apply_freq_range(wizard.stop_freq_input, "MHz", min_hz, max_hz)
    wizard.stop_freq_input.setValue(stop_hz / _UNIT_MULT["MHz"])

    # Choose stored points if valid, else nearest default.
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
        wizard.sweep_steps = int(wizard.points_input.currentText())
        wizard.temperature_c = float(wizard.temperature_input.value())
        wizard.unknown_liquid_name = wizard.unknown_name_input.text().strip()

        refs = descriptor.reference_standards
        if len(refs) >= 2:
            wizard.perm_calibration.set_reference_liquids(
                refs[0].default_liquid_key, refs[1].default_liquid_key
            )
        wizard.temperature_warnings = wizard.perm_calibration.set_temperature(wizard.temperature_c)
    except Exception as exc:  # noqa: BLE001
        logger.error("[config_screen] commit failed: %s", exc)
