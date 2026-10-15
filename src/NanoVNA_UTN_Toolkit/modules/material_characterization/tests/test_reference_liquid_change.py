"""
Tests for changing the liquid of a reference that is already measured.

EN: The S11 stored for a reference belongs to the liquid it was measured
    with; read under another liquid it gives a wrong permittivity. Changing
    the liquid in the Configuration step must therefore ask, and either
    discard the measurement, keep it (only the selection was wrong) or revert
    the combo. Also covers ``PermittivityProbeCalibration.clear_measurement``,
    which keeps the step's own pre-calibration for its next sweep. The UI tests drive the real reference row with Qt offscreen and a patched
    dialog. Runnable with pytest or directly:
    ``python test_reference_liquid_change.py``.

ES: El S11 guardado de una referencia corresponde al liquido con el que se
    midio; leido como otro liquido da una permitividad incorrecta. Cambiar el
    liquido en el paso de Configuracion tiene que preguntar y descartar la
    medicion, conservarla (solo estaba mal la seleccion) o revertir el combo.
    Tambien cubre ``PermittivityProbeCalibration.clear_measurement``, que
    conserva la pre-calibracion propia del paso para su proximo barrido. Los
    tests de UI usan la fila de referencia real con Qt offscreen y el dialogo
    reemplazado. Ejecutable con pytest o directo:
    ``python test_reference_liquid_change.py``.
"""

import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_probe_calibration import (
    PermittivityProbeCalibration,
)

_DATA = Path(__file__).resolve().parent / "data"
_SWEEPS = {
    "open": "open_air_r60_probe21_2026",
    "short": "short_r60_probe21_2026",
    "ref1": "water_r60_probe21_2026",
    "ref2": "ipa_r60_probe21_2026",
    "dut": "ethanol_r60_probe21_2026",
}


def _load_fixture(name):
    """(freqs, s11) of a real R60 sweep kept in tests/data (not a user preset)."""
    import skrf as rf

    net = rf.Network(str(_DATA / f"{name}.s1p"))
    return np.asarray(net.f, dtype=float), np.asarray(net.s[:, 0, 0], dtype=complex)


def _calibration():
    """Full technique (water / IPA) on the 21 mm sweeps, at 20 C."""
    cal = PermittivityProbeCalibration()
    assert cal.set_reference_liquids("water", "ipa")
    cal.set_temperature(20.0)
    for key, name in _SWEEPS.items():
        assert cal.set_measurement(key, *_load_fixture(name))
    return cal


def _precalibrate_ref2(cal):
    """Give ref2 its own OPEN pre-cal (a cable change of -0.1 dB, 3 deg)."""
    from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.precal import (
        PrecalReference,
    )

    freqs, s_open = cal.get_measurement("open")
    reference = PrecalReference.from_sweep(
        freqs, s_open * 10 ** (-0.1 / 20) * np.exp(1j * np.deg2rad(3.0)))
    cal.set_step_precal("ref2", reference)
    assert cal.is_precal_applied("ref2")
    return reference


def test_clear_measurement_forgets_one_standard():
    cal = _calibration()
    cal.compute_epsilon()
    assert cal.clear_measurement("ref2")
    assert not cal.is_standard_measured("ref2")
    assert cal.get_source("ref2") is None
    assert cal.pattern_constants is None and cal.epsilon_result is None
    assert all(cal.is_standard_measured(k) for k in ("open", "short", "ref1", "dut"))
    assert not cal.get_completion_status()["calibration_complete"]

    cal = _calibration()
    cal.compute_epsilon()
    constants = cal.pattern_constants
    assert cal.clear_measurement("DUT")              # keys are case-insensitive
    assert cal.pattern_constants is constants        # calibration still valid
    assert cal.epsilon_result is None
    assert not cal.clear_measurement("no_such_standard")


def test_clear_measurement_keeps_the_steps_precal_for_the_next_sweep():
    cal = _calibration()
    reference = _precalibrate_ref2(cal)
    assert cal.clear_measurement("ref2")
    assert cal.step_precal("ref2") is reference      # pending, not lost
    assert not cal.is_precal_applied("ref2")

    freqs, s11 = _load_fixture("ethanol_r60_probe21_2026")   # the new liquid
    assert cal.set_measurement("ref2", freqs, s11)
    assert cal.is_precal_applied("ref2")
    np.testing.assert_allclose(cal.get_raw_measurement("ref2")[1], s11)
    assert not np.allclose(cal.get_measurement("ref2")[1], s11)


def test_clearing_the_open_leaves_its_precal_users_pending():
    cal = _calibration()
    _precalibrate_ref2(cal)
    cal.compute_epsilon()
    assert cal.clear_measurement("open")
    assert not cal.is_precal_applied("ref2")         # c0 is gone
    _, raw = cal.get_raw_measurement("ref2")
    np.testing.assert_allclose(cal.get_measurement("ref2")[1], raw)
    assert cal.pattern_constants is None and cal.epsilon_result is None


# --------------------------------------------------------------------------- #
# Configuration step: reference row
# --------------------------------------------------------------------------- #

def _qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _ref2_row(answer):
    """Bind the real ref2 row (IPA, measured, pre-calibrated), dialog patched.

    Returns ``(wizard, liquid_combo, asked, restore)``; ``asked`` collects the
    ``(old, new)`` liquid keys of every dialog shown.
    """
    _qapp()
    from PySide6.QtWidgets import QComboBox, QPushButton

    from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
        list_reference_liquids,
    )
    from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import registry
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps import (
        config_screen,
    )

    cal = _calibration()
    _precalibrate_ref2(cal)
    wizard = SimpleNamespace(
        perm_calibration=cal,
        start_freq_input=SimpleNamespace(value=lambda: 1.0),
        start_freq_unit=SimpleNamespace(currentText=lambda: "MHz"),
        stop_freq_input=SimpleNamespace(value=lambda: 1.5),
        stop_freq_unit=SimpleNamespace(currentText=lambda: "GHz"),
        points_input=SimpleNamespace(currentText=lambda: "101"),
        temperature_input=SimpleNamespace(value=lambda: 20.0),
        unknown_name_input=SimpleNamespace(text=lambda: "ethanol"),
        ref_liquid_keys={"ref1": "water", "ref2": "ipa"},
        epsilon_result=cal.compute_epsilon(),
    )
    descriptor = registry.get("open_coax_liquids")
    standard = next(s for s in descriptor.reference_standards if s.key == "ref2")

    liquid_combo = QComboBox()
    for liq in list_reference_liquids():
        liquid_combo.addItem(liq.display_name, liq.key)
    liquid_combo.setCurrentIndex(liquid_combo.findData("ipa"))

    asked = []

    def _fake_dialog(_wizard, _cfg, old_key, new_key):
        asked.append((old_key, new_key))
        return answer

    original = config_screen._ask_measured_liquid_change
    config_screen._ask_measured_liquid_change = _fake_dialog

    def restore():
        config_screen._ask_measured_liquid_change = original

    config_screen._bind_reference_row(wizard, descriptor, standard, {},
                                      liquid_combo, QComboBox(), QPushButton())
    return wizard, liquid_combo, asked, restore


def test_discarding_drops_the_old_liquids_measurement():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps import (
        config_screen,
    )

    wizard, combo, asked, restore = _ref2_row(config_screen._LIQUID_DISCARD)
    try:
        combo.setCurrentIndex(combo.findData("methanol"))
    finally:
        restore()
    cal = wizard.perm_calibration
    assert asked == [("ipa", "methanol")]
    assert not cal.is_standard_measured("ref2")
    assert cal.get_raw_measurement("ref2") is None   # the IPA sweep is gone
    assert cal.step_precal("ref2") is not None       # its pre-cal waits
    assert cal.ref2_key == "methanol"
    assert wizard.ref_liquid_keys["ref2"] == "methanol"
    assert wizard.epsilon_result is None
    assert all(cal.is_standard_measured(k) for k in ("open", "short", "ref1", "dut"))


def test_keeping_relabels_the_measurement():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps import (
        config_screen,
    )

    wizard, combo, asked, restore = _ref2_row(config_screen._LIQUID_KEEP)
    s11_before = wizard.perm_calibration.get_measurement("ref2")[1]
    try:
        combo.setCurrentIndex(combo.findData("methanol"))
    finally:
        restore()
    cal = wizard.perm_calibration
    assert asked == [("ipa", "methanol")]
    assert cal.get_measurement("ref2")[1] is s11_before
    assert cal.is_precal_applied("ref2")
    assert cal.ref2_key == "methanol"
    assert wizard.epsilon_result is None            # recomputed as methanol


def test_cancelling_reverts_the_combo():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps import (
        config_screen,
    )

    wizard, combo, asked, restore = _ref2_row(config_screen._LIQUID_CANCEL)
    result = wizard.epsilon_result
    try:
        combo.setCurrentIndex(combo.findData("methanol"))
    finally:
        restore()
    cal = wizard.perm_calibration
    assert asked == [("ipa", "methanol")]           # asked once, no re-entry
    assert combo.currentData() == "ipa"
    assert wizard.ref_liquid_keys["ref2"] == "ipa"
    assert cal.ref2_key == "ipa" and cal.is_standard_measured("ref2")
    assert wizard.epsilon_result is result and cal.epsilon_result is result


def test_unmeasured_reference_changes_without_asking():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps import (
        config_screen,
    )

    wizard, combo, asked, restore = _ref2_row(config_screen._LIQUID_CANCEL)
    wizard.perm_calibration.clear_measurement("ref2")
    try:
        combo.setCurrentIndex(combo.findData("methanol"))
    finally:
        restore()
    assert asked == []
    assert wizard.perm_calibration.ref2_key == "methanol"
    assert wizard.ref_liquid_keys["ref2"] == "methanol"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    raise SystemExit(1 if failures else 0)
