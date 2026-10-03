"""
Tests for per-standard reference temperatures and the eps_r Touchstone export.

EN: (1) a reference loaded from a preset keeps the temperature it was recorded
    at: the result must equal a session run AT that temperature, for both the
    full and the simplified technique, and a saved kit must keep it; (2) the
    permittivity .s1p export is readable by Touchstone tools, carries its
    marker, and is refused as S11 (as are marker-less legacy eps_r files).
    Runnable with pytest or directly.

ES: (1) una referencia cargada de un preset conserva la temperatura a la que se
    midio: el resultado tiene que ser igual al de una sesion A esa temperatura,
    en la tecnica completa y en la simplificada, y un kit guardado la conserva;
    (2) la exportacion .s1p de la permitividad la leen las herramientas
    Touchstone, lleva su marca y se rechaza como S11 (igual que los archivos
    eps_r viejos sin marca). Ejecutable con pytest o directo.
"""

import tempfile
from pathlib import Path

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import calibration_store
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_probe_calibration import (
    PermittivityProbeCalibration,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_touchstone import (
    PERMITTIVITY_MARKER,
    implausible_s11_peak,
    is_permittivity_touchstone,
    write_permittivity_touchstone,
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


def _calibration(session_c, ref_temps=None, simplified=False):
    """Calibration on the 21 mm sweeps; ``ref_temps`` mimics preset-loaded refs."""
    ref_temps = ref_temps or {}
    cal = PermittivityProbeCalibration()
    assert cal.set_reference_liquids("water", None if simplified else "ipa")
    cal.set_temperature(session_c)
    for key, name in _SWEEPS.items():
        if simplified and key == "ref2":
            continue
        freqs, s11 = _load_fixture(name)
        cal.set_measurement(key, freqs, s11, temperature_c=ref_temps.get(key))
    return cal


def _same(a, b):
    a, b = np.asarray(a), np.asarray(b)
    both = np.isfinite(a) & np.isfinite(b)
    assert np.array_equal(np.isfinite(a), np.isfinite(b))
    assert np.allclose(a[both], b[both], rtol=0, atol=1e-9)


def test_preset_temperature_drives_full_technique():
    at_18 = _calibration(18.0).compute_epsilon()
    preset_18 = _calibration(25.0, {"ref1": 18.0, "ref2": 18.0})
    res = preset_18.compute_epsilon()
    assert preset_18.pattern_constants.temp_ref1_c == 18.0
    assert preset_18.pattern_constants.temp_ref2_c == 18.0
    _same(res.eps_selected, at_18.eps_selected)

    # ...and it really matters: the session temperature alone gives another eps.
    at_25 = _calibration(25.0).compute_epsilon()
    assert np.nanmax(np.abs(at_25.eps_selected - res.eps_selected)) > 0.1


def test_only_the_preset_reference_keeps_its_temperature():
    cal = _calibration(25.0, {"ref1": 18.0})      # ref2 measured "live"
    cal.compute_epsilon()
    assert cal.pattern_constants.temp_ref1_c == 18.0
    assert cal.pattern_constants.temp_ref2_c == 25.0
    assert cal.reference_temperature("ref2") == 25.0


def test_preset_temperature_drives_simplified_technique():
    at_18 = _calibration(18.0, simplified=True).compute_epsilon()
    res = _calibration(25.0, {"ref1": 18.0}, simplified=True).compute_epsilon()
    assert res.temperature_c == 18.0
    _same(res.eps, at_18.eps)


def test_live_measurement_clears_a_previous_preset_temperature():
    cal = _calibration(25.0, {"ref1": 18.0})
    freqs, s11 = _load_fixture(_SWEEPS["ref1"])
    cal.set_measurement("ref1", freqs, s11)           # re-measured now
    assert cal.standard_temperature("ref1") is None
    assert cal.reference_temperature("ref1") == 25.0


def test_kit_round_trip_keeps_standard_temperatures():
    cal = _calibration(25.0, {"ref1": 18.0, "ref2": 18.0})
    original = calibration_store.get_calibration_dir
    with tempfile.TemporaryDirectory() as tmp:
        calibration_store.get_calibration_dir = lambda: Path(tmp)
        try:
            calibration_store.save_calibration("kit_t", "kit_t", cal, "open_coax_liquids", 25.0)
            _, meta = calibration_store.load_calibration("kit_t")
        finally:
            calibration_store.get_calibration_dir = original
    assert meta.temperature_c == 25.0
    assert meta.standard_temperatures == {"ref1": 18.0, "ref2": 18.0}


def test_old_kit_manifest_without_temperatures_still_loads():
    meta = calibration_store.CalibrationMeta(
        name="old", display_name="old", technique_id="open_coax_liquids",
        ref1_key="water", ref2_key="ipa", temperature_c=25.0, device_name="",
        saved="2026-09-03T20:01:07", standards=["open"], sources={"open": "measured"},
    )
    assert meta.standard_temperatures == {}


def test_bundled_presets_cannot_be_deleted_or_overwritten():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import preset_store as ps

    f, s11 = _load_fixture(_SWEEPS["ref1"])
    original = ps.get_preset_dir
    with tempfile.TemporaryDirectory() as tmp:
        ps.get_preset_dir = lambda: Path(tmp)
        try:
            ps.save_preset("shipped", f, s11, ps.PresetMeta(name="shipped", liquid_key="water",
                                                            bundled=True), overwrite_bundled=True)
            ps.save_preset("mine", f, s11, ps.PresetMeta(name="mine", liquid_key="water"))
            assert ps.is_bundled("shipped") and not ps.is_bundled("mine")
            for attempt in (lambda: ps.delete_preset("shipped"),
                            lambda: ps.save_preset("shipped", f, s11,
                                                   ps.PresetMeta(name="shipped", liquid_key="ipa"))):
                try:
                    attempt()
                except ps.PresetProtectedError:
                    pass
                else:
                    raise AssertionError("a bundled preset must be protected")
            assert ps.read_meta("shipped").liquid_key == "water"   # untouched
            assert ps.delete_preset("mine")                          # user presets still go
        finally:
            ps.get_preset_dir = original


def test_shipped_presets_are_marked_bundled():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import preset_store as ps

    shipped = [m for m in ps.list_presets() if m.bundled]
    assert {m.name for m in shipped} >= {
        "water_r60_probe3mm_18C", "ipa_r60_probe3mm_18C",
        "water_r60_probe21mm_18C", "ipa_r60_probe21mm_18C",
    }
    assert all(m.temperature_c == 18.0 for m in shipped)


def test_permittivity_touchstone_round_trip():
    import skrf as rf

    f = np.array([1e6, 2e6, 3e6, 4e6])
    eps = np.array([80 - 1j, 79 - 2j, np.nan + 0j, 77 - 4j])
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "water_er.s1p"
        rows = write_permittivity_touchstone(path, f, eps, sample_name="agua",
                                             notes=["References / Referencias: water + ipa"])
        text = path.read_text(encoding="utf-8")
        assert rows == 3                                  # the NaN gap is omitted
        assert PERMITTIVITY_MARKER in text
        assert is_permittivity_touchstone(path)

        net = rf.Network(str(path))                       # viewers can read it
        assert np.allclose(net.f, [1e6, 2e6, 4e6])
        # Same numbers as the CSV export: eps' and eps'' (positive loss).
        assert np.allclose(net.s[:, 0, 0], [80 + 1j, 79 + 2j, 77 + 4j])

        # It must never pass as S11.
        cal = PermittivityProbeCalibration()
        assert not cal.import_standard_from_touchstone("dut", str(path))
        assert not cal.is_standard_measured("dut")


def test_s11_plausibility_guard():
    _, s11 = _load_fixture(_SWEEPS["ref1"])
    assert implausible_s11_peak(s11) is None              # real S11 passes
    assert not is_permittivity_touchstone(_DATA / f"{_SWEEPS['ref1']}.s1p")

    legacy_eps = np.array([80.1 - 0.5j, 79.9 - 4.5j, 77.8 - 13.2j])   # no marker
    assert implausible_s11_peak(legacy_eps) > 70


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
