"""
Regression tests for the invalidation of the cached calibration results.

EN: ``compute_epsilon`` reuses ``pattern_constants`` (and the wizard reuses
    ``epsilon_result``) while they exist. Before the fix no setter dropped
    them, so after viewing a result, changing T, replacing a reference liquid
    or re-measuring a standard returned the OLD epsilon (delta = 0). Each test
    changes one input and checks that the result equals a fresh calibration
    with the new input, that an unchanged input keeps the cache, and that a
    failed .s1p write leaves the standard as it was. Runnable with pytest or
    directly: ``python test_calibration_cache_invalidation.py``.

ES: ``compute_epsilon`` reutiliza ``pattern_constants`` (y el asistente
    reutiliza ``epsilon_result``) mientras existan. Antes del arreglo ningun
    setter los descartaba, asi que despues de ver un resultado, cambiar T,
    reemplazar un liquido de referencia o volver a medir un patron devolvia el
    epsilon VIEJO (delta = 0). Cada test cambia una entrada y verifica que el
    resultado sea igual al de una calibracion nueva con esa entrada, que una
    entrada sin cambios conserve el cache y que una escritura fallida del .s1p
    deje el patron como estaba. Ejecutable con pytest o directo:
    ``python test_calibration_cache_invalidation.py``.
"""

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


def _calibration(temp_c, ref2="ipa", replace=None):
    """Calibration on the 21 mm sweeps; ``replace`` swaps in other (f, s11)."""
    replace = replace or {}
    cal = PermittivityProbeCalibration()
    assert cal.set_reference_liquids("water", ref2)
    cal.set_temperature(temp_c)
    for key, name in _SWEEPS.items():
        if ref2 is None and key == "ref2":
            continue
        freqs, s11 = replace.get(key) or _load_fixture(name)
        assert cal.set_measurement(key, freqs, s11)
    return cal


def _same(a, b):
    a, b = np.asarray(a), np.asarray(b)
    both = np.isfinite(a) & np.isfinite(b)
    assert np.array_equal(np.isfinite(a), np.isfinite(b))
    assert np.allclose(a[both], b[both], rtol=0, atol=1e-9)


def _delta(a, b):
    return float(np.nanmax(np.abs(a.eps_selected - b.eps_selected)))


def _assert_invalidated(cal):
    assert cal.pattern_constants is None
    assert cal.epsilon_result is None


def test_temperature_change_recomputes_epsilon():
    cal = _calibration(20.0)
    first = cal.compute_epsilon()
    cal.set_temperature(30.0)
    _assert_invalidated(cal)

    res = cal.compute_epsilon()
    assert cal.pattern_constants.temp_c == 30.0
    _same(res.eps_selected, _calibration(30.0).compute_epsilon().eps_selected)
    assert _delta(res, first) > 1.0               # the stale cache gave 0


def test_reference_liquid_change_recomputes_epsilon():
    cal = _calibration(20.0)
    first = cal.compute_epsilon()
    assert cal.set_reference_liquids("water", "methanol")
    _assert_invalidated(cal)

    res = cal.compute_epsilon()
    assert cal.pattern_constants.ref2_key == "methanol"
    _same(res.eps_selected,
          _calibration(20.0, ref2="methanol").compute_epsilon().eps_selected)
    assert _delta(res, first) > 1.0


def test_remeasured_standard_recomputes_epsilon():
    cal = _calibration(20.0)
    first = cal.compute_epsilon()
    freqs, s11 = cal.get_measurement("ref2")
    remeasured = (freqs, s11 * 0.98)
    assert cal.set_measurement("ref2", *remeasured)
    _assert_invalidated(cal)

    res = cal.compute_epsilon()
    _same(res.eps_selected,
          _calibration(20.0, replace={"ref2": remeasured}).compute_epsilon().eps_selected)
    assert _delta(res, first) > 1.0

    # Same S11 but now tagged with the temperature it was recorded at (kit /
    # preset): the reference eps_r changes, so the constants must too.
    assert cal.set_measurement("ref2", *remeasured, temperature_c=18.0)
    _assert_invalidated(cal)
    cal.compute_epsilon()
    assert cal.pattern_constants.temp_ref2_c == 18.0


def test_new_dut_sweep_keeps_the_pattern_constants():
    cal = _calibration(20.0)
    first = cal.compute_epsilon()
    constants = cal.pattern_constants
    assert cal.set_measurement("dut", *_load_fixture(_SWEEPS["ref2"]))
    assert cal.pattern_constants is constants     # calibration still valid
    assert cal.epsilon_result is None             # but the old eps is not
    assert _delta(cal.compute_epsilon(), first) > 1.0


def test_unchanged_or_rejected_settings_keep_the_cache():
    cal = _calibration(20.0)
    res = cal.compute_epsilon()
    constants = cal.pattern_constants
    cal.set_temperature(20.0)
    assert cal.set_reference_liquids("water", "ipa")
    assert not cal.set_reference_liquids("water", "water")
    assert not cal.set_reference_liquids("water", "no_such_liquid")
    assert cal.pattern_constants is constants
    assert cal.epsilon_result is res


def test_simplified_result_is_dropped_on_temperature_change():
    cal = _calibration(20.0, ref2=None)
    res = cal.compute_epsilon()
    assert cal.epsilon_result is res
    cal.set_temperature(30.0)
    assert cal.epsilon_result is None


def test_failed_persistence_leaves_the_standard_untouched():
    def _disk_full(*_args):
        raise OSError("disk full")

    cal = _calibration(20.0)
    res = cal.compute_epsilon()
    constants = cal.pattern_constants
    freqs, s11 = cal.get_measurement("ref2")
    cal._save_as_touchstone = _disk_full
    assert cal.set_measurement("ref2", freqs, s11 * 0.98, temperature_c=18.0) is False
    stored_f, stored_s11 = cal.get_measurement("ref2")
    assert stored_f is freqs and stored_s11 is s11
    assert cal.standard_temperature("ref2") is None
    assert cal.pattern_constants is constants and cal.epsilon_result is res

    fresh = PermittivityProbeCalibration()
    fresh._save_as_touchstone = _disk_full
    assert fresh.set_measurement("open", freqs, s11) is False
    assert not fresh.is_standard_measured("open")
    assert fresh.get_source("open") is None


def test_config_commit_drops_the_wizards_stale_result():
    """The config step must not leave the wizard showing the old epsilon."""
    from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import registry
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.config_screen import (
        _commit,
    )

    cal = _calibration(20.0)
    temp = {"c": 20.0}
    wizard = SimpleNamespace(
        perm_calibration=cal,
        start_freq_input=SimpleNamespace(value=lambda: 1.0),
        start_freq_unit=SimpleNamespace(currentText=lambda: "MHz"),
        stop_freq_input=SimpleNamespace(value=lambda: 1.5),
        stop_freq_unit=SimpleNamespace(currentText=lambda: "GHz"),
        points_input=SimpleNamespace(currentText=lambda: "101"),
        temperature_input=SimpleNamespace(value=lambda: temp["c"]),
        unknown_name_input=SimpleNamespace(text=lambda: "ethanol"),
        ref_liquid_keys={"ref1": "water", "ref2": "ipa"},
        epsilon_result=cal.compute_epsilon(),
    )
    descriptor = registry.get("open_coax_liquids")

    _commit(wizard, descriptor)                   # nothing changed
    assert wizard.epsilon_result is not None
    assert wizard.epsilon_result is cal.epsilon_result

    temp["c"] = 30.0
    _commit(wizard, descriptor)
    assert cal.temperature_c == 30.0              # the commit went through
    assert wizard.epsilon_result is None

    wizard.epsilon_result = cal.compute_epsilon()
    wizard.ref_liquid_keys["ref2"] = "methanol"
    _commit(wizard, descriptor)
    assert cal.ref2_key == "methanol"
    assert wizard.epsilon_result is None


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
