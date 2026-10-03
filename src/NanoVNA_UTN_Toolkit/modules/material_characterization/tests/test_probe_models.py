"""
Tests for the probe registry: fitted C0, preset filtering and kit persistence.

EN: The C0 of each known probe must match a fresh least-squares fit to the
    bundled presets of that probe (so rebuilding the presets cannot silently
    leave a stale constant behind), must actually bring the indicative curve
    closer to the measurement than the generic value, and must select only the
    presets of its probe. Runnable with pytest or directly.

ES: El C0 de cada sonda conocida tiene que coincidir con un ajuste nuevo por
    minimos cuadrados a los presets incluidos de esa sonda (asi reconstruir los
    presets no deja una constante vieja sin aviso), tiene que acercar de verdad
    la curva indicativa a la medicion respecto del valor generico, y tiene que
    seleccionar solo los presets de su sonda. Ejecutable con pytest o directo.
"""

import tempfile
from pathlib import Path

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.probe_models import (
    GENERIC_PROBE_KEY,
    fit_c0,
    get_probe,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    NOMINAL_PROBE_C0_F,
    evaluate_epsilon_r,
    get_reference_liquid,
    indicative_s11,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import calibration_store
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import preset_store as ps
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_probe_calibration import (
    PermittivityProbeCalibration,
)

_BUNDLED = {
    "probe3mm": ("water_r60_probe3mm_18C", "ipa_r60_probe3mm_18C"),
    "probe21mm": ("water_r60_probe21mm_18C", "ipa_r60_probe21mm_18C"),
}


def _refs_in_band(probe):
    lo, hi = probe.fit_band_hz
    refs = []
    for name in _BUNDLED[probe.key]:
        f, s11, meta = ps.load_preset(name)
        band = (f >= lo) & (f <= hi)
        eps, _ = evaluate_epsilon_r(get_reference_liquid(meta.liquid_key), f[band], meta.temperature_c)
        refs.append((f[band], s11[band], eps))
    return refs


def test_stored_c0_matches_a_fresh_fit_to_the_bundled_presets():
    for key in _BUNDLED:
        probe = get_probe(key)
        fitted = fit_c0(_refs_in_band(probe))
        assert abs(fitted - probe.c0_f) / probe.c0_f < 0.01, (key, fitted, probe.c0_f)


def test_probe_c0_brings_the_indicative_curve_closer_to_the_measurement():
    for key, (water, _ipa) in _BUNDLED.items():
        probe = get_probe(key)
        f, s11, meta = ps.load_preset(water)
        liquid = get_reference_liquid("water")
        err_generic = np.median(np.abs(indicative_s11(liquid, f, meta.temperature_c) - s11))
        err_probe = np.median(np.abs(
            indicative_s11(liquid, f, meta.temperature_c, c0_f=probe.c0_f) - s11))
        assert err_probe < err_generic / 3, (key, err_probe, err_generic)


def test_unknown_or_missing_probe_falls_back_to_generic():
    assert get_probe(None).key == GENERIC_PROBE_KEY
    assert get_probe("no-such-probe").key == GENERIC_PROBE_KEY
    assert get_probe(None).c0_f == NOMINAL_PROBE_C0_F


def test_presets_are_listed_only_for_their_probe():
    for key, names in _BUNDLED.items():
        listed = {m.name for m in ps.list_presets(probe=get_probe(key).preset_probe)}
        assert set(names) <= listed
        other = [n for k, ns in _BUNDLED.items() if k != key for n in ns]
        assert not listed & set(other)
    generic = {m.name for m in ps.list_presets(probe=get_probe(None).preset_probe)}
    assert not generic & {n for ns in _BUNDLED.values() for n in ns}


def test_kit_keeps_the_probe():
    cal = PermittivityProbeCalibration()
    cal.set_reference_liquids("water", None)
    cal.set_temperature(25.0)
    cal.probe_key = "probe21mm"
    f = np.linspace(1e6, 1e8, 5)
    for key in ("open", "short", "ref1"):
        cal.set_measurement(key, f, np.full(5, 0.5 + 0j))
    original = calibration_store.get_calibration_dir
    with tempfile.TemporaryDirectory() as tmp:
        calibration_store.get_calibration_dir = lambda: Path(tmp)
        try:
            calibration_store.save_calibration("kit_p", "kit_p", cal, "open_coax_liquids", 25.0)
            _, meta = calibration_store.load_calibration("kit_p")
        finally:
            calibration_store.get_calibration_dir = original
    assert meta.probe_key == "probe21mm"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
