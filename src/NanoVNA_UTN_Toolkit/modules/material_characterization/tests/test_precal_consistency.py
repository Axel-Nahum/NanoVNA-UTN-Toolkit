"""
Tests for the per-step pre-calibration (s11 * c0 / c, calibration.precal).

EN: Handling the probe before a step is simulated as a cable change k(f) on
    that step and the later ones (-0.3 dB, 0.1 ns). (1) Referring each handled
    step to the session with its own reference, s11 * c0 / c, gives back the
    eps of the unhandled session (full and simplified technique, OPEN and
    SHORT references), while dividing only by c does not; (2) the model keeps
    each pre-cal in its step, recomputes from the CURRENT raw sweep, keeps
    source and preset temperature and follows c0 when the Open changes; (3)
    kits and presets store the raw sweep plus each step's reference, are
    validated on load and never apply a reference twice; (4) one kit loader
    configures the wizard. Runnable with pytest or directly.

ES: Manipular la sonda antes de un paso se simula como un cambio de cable
    k(f) en ese paso y los siguientes (-0.3 dB, 0.1 ns). (1) Referir cada paso
    manipulado a la sesion con su propia referencia, s11 * c0 / c, devuelve el
    eps de la sesion sin manipular (tecnica completa y simplificada,
    referencias OPEN y SHORT), mientras que dividir solo por c no; (2) el
    modelo mantiene cada pre-cal en su paso, recalcula desde el barrido CRUDO
    actual, conserva fuente y temperatura de preset y sigue a c0 cuando cambia
    el Open; (3) kits y presets guardan el barrido crudo mas la referencia de
    cada paso, se validan al cargarse y nunca aplican una referencia dos
    veces; (4) un unico cargador de kits configura el asistente. Ejecutable con
    pytest o directo.
"""

import json
import tempfile
import types
import zipfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import calibration_store
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import preset_store as ps
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_probe_calibration import (
    PermittivityProbeCalibration,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.precal import (
    KIND_OPEN,
    KIND_SHORT,
    PrecalReference,
)

_DATA = Path(__file__).resolve().parent / "data"
_SWEEPS = {
    "open": "open_air_r60_probe21_2026",
    "short": "short_r60_probe21_2026",
    "ref1": "water_r60_probe21_2026",
    "ref2": "ipa_r60_probe21_2026",
    "dut": "ethanol_r60_probe21_2026",
}
_STANDARDS = ("open", "short", "ref1", "ref2")
_HANDLED = ("ref2", "dut")          # probe handled right before step 4 (ref2)


@lru_cache(maxsize=None)
def _raw(key):
    """(freqs, s11) of the real 2026 R60 sweep of ``key`` kept in tests/data."""
    import skrf as rf

    net = rf.Network(str(_DATA / f"{_SWEEPS[key]}.s1p"))
    return np.asarray(net.f, dtype=float), np.asarray(net.s[:, 0, 0], dtype=complex)


@lru_cache(maxsize=None)
def _k():
    """Cable change caused by handling the probe: -0.3 dB and a 0.1 ns delay."""
    freqs = _raw("open")[0]
    return 10 ** (-0.3 / 20) * np.exp(-2j * np.pi * freqs * 0.1e-9)


def _handled(key):
    """Sweep of ``key`` as measured after the handling."""
    freqs, s11 = _raw(key)
    return freqs, s11 * _k()


def _reference_now(kind):
    """The step's pre-cal: OPEN (or SHORT) measured right after the handling."""
    freqs, s11 = _handled("open" if kind == KIND_OPEN else "short")
    return PrecalReference.from_sweep(freqs, s11, kind)


def _cal(simplified=False, handled=(), precal_kind=None, temps=None, keys=None):
    """Session on the 21 mm sweeps; ``handled`` steps get the cable change k(f)."""
    temps = temps or {}
    cal = PermittivityProbeCalibration()
    assert cal.set_reference_liquids("water", None if simplified else "ipa")
    cal.set_temperature(25.0)
    for key in keys or _SWEEPS:
        if simplified and key == "ref2":
            continue
        freqs, s11 = _handled(key) if key in handled else _raw(key)
        precal = _reference_now(precal_kind) if (precal_kind and key in handled) else None
        assert cal.set_measurement(key, freqs, s11, temperature_c=temps.get(key), precal=precal)
    return cal


def _eps(cal):
    """eps of the stored DUT (both techniques expose ``eps_selected``)."""
    result = cal.compute_epsilon()
    assert result is not None, cal.last_error
    return np.asarray(result.eps_selected)


def _max_diff(a, b):
    """Largest |a - b| where both are finite; both must have the same gaps."""
    a, b = np.asarray(a), np.asarray(b)
    assert np.array_equal(np.isfinite(a), np.isfinite(b))
    both = np.isfinite(a)
    return float(np.max(np.abs(a[both] - b[both])))


def _max_real_diff(a, b):
    both = np.isfinite(a) & np.isfinite(b)
    return float(np.max(np.abs(a.real[both] - b.real[both])))


@contextmanager
def _tmp_kits():
    original = calibration_store.get_calibration_dir
    with tempfile.TemporaryDirectory() as tmp:
        calibration_store.get_calibration_dir = lambda: Path(tmp)
        try:
            yield Path(tmp)
        finally:
            calibration_store.get_calibration_dir = original


@contextmanager
def _tmp_presets():
    original = ps.get_preset_dir
    with tempfile.TemporaryDirectory() as tmp:
        ps.get_preset_dir = lambda: Path(tmp)
        try:
            yield Path(tmp)
        finally:
            ps.get_preset_dir = original


# --------------------------------------------------------------------------- #
# (1) Why s11 * c0 / c
# --------------------------------------------------------------------------- #

def test_step_precal_removes_the_handling_change_full_technique():
    truth = _eps(_cal())
    assert _max_real_diff(_eps(_cal(handled=_HANDLED)), truth) > 1.0   # it does matter
    for kind in (KIND_OPEN, KIND_SHORT):
        assert _max_diff(_eps(_cal(handled=_HANDLED, precal_kind=kind)), truth) < 1e-9, kind


def test_step_precal_removes_the_handling_change_simplified_technique():
    truth = _eps(_cal(simplified=True))
    corrected = _cal(simplified=True, handled=("dut",), precal_kind=KIND_OPEN)
    assert _max_diff(_eps(corrected), truth) < 1e-9


def test_dividing_only_by_the_new_open_is_not_enough():
    """What the wizard used to do (s11 / c) leaves the step on another scale."""
    truth = _eps(_cal())
    cal = PermittivityProbeCalibration()
    cal.set_reference_liquids("water", "ipa")
    cal.set_temperature(25.0)
    c = _reference_now(KIND_OPEN).divisor
    for key in _SWEEPS:
        freqs, s11 = _handled(key) if key in _HANDLED else _raw(key)
        cal.set_measurement(key, freqs, s11 / c if key in _HANDLED else s11)
    assert _max_real_diff(_eps(cal), truth) > 0.25


# --------------------------------------------------------------------------- #
# (2) Model behaviour
# --------------------------------------------------------------------------- #

def test_a_step_precal_changes_only_its_own_step():
    cal = _cal(handled=("ref2",))
    reference = _reference_now(KIND_OPEN)
    cal.set_step_precal("ref2", reference)
    assert np.allclose(cal.get_measurement("ref2")[1],
                       _handled("ref2")[1] * _raw("open")[1] / reference.divisor)
    assert np.allclose(cal.get_measurement("ref2")[1], _raw("ref2")[1])   # k(f) removed
    for key in ("open", "short", "ref1", "dut"):
        assert cal.step_precal(key) is None
        assert np.array_equal(cal.get_measurement(key)[1], _raw(key)[1]), key


def test_the_open_and_the_short_by_itself_cannot_be_precalibrated():
    cal = _cal(keys=("open", "short"))
    for key, kind in (("open", KIND_OPEN), ("open", KIND_SHORT), ("short", KIND_SHORT)):
        assert not cal.precal_allowed(key, kind)
        try:
            cal.set_step_precal(key, _reference_now(kind))
        except ValueError:
            pass
        else:
            raise AssertionError(f"{key} must refuse a {kind} pre-cal")
    assert cal.precal_allowed("short", KIND_OPEN)
    cal.set_step_precal("short", _reference_now(KIND_OPEN))
    assert cal.is_precal_applied("short")


def test_precal_set_before_measuring_waits_for_the_sweep():
    cal = _cal(keys=("open", "short", "ref1", "ref2"))
    reference = _reference_now(KIND_OPEN)
    cal.set_step_precal("dut", reference)
    assert not cal.is_standard_measured("dut")
    freqs, s11 = _handled("dut")
    cal.set_measurement("dut", freqs, s11)          # live: keeps the step's pre-cal
    assert cal.is_precal_applied("dut")
    assert np.allclose(cal.get_measurement("dut")[1], _raw("dut")[1])


def test_precal_waits_for_its_reference_standard():
    cal = PermittivityProbeCalibration()
    cal.set_measurement("ref1", *_handled("ref1"), precal=_reference_now(KIND_OPEN))
    assert cal.step_precal("ref1") is not None and not cal.is_precal_applied("ref1")
    assert np.array_equal(cal.get_measurement("ref1")[1], _handled("ref1")[1])
    cal.set_measurement("open", *_raw("open"))      # c0 arrives
    assert cal.is_precal_applied("ref1")
    assert np.allclose(cal.get_measurement("ref1")[1], _raw("ref1")[1])


def test_a_new_open_rereferences_the_precalibrated_steps():
    cal = _cal(handled=("ref1",), precal_kind=KIND_OPEN, keys=("open", "ref1"))
    reference = cal.step_precal("ref1")
    new_open = _raw("open")[1] * (1 + 0.02j)
    cal.set_measurement("open", _raw("open")[0], new_open)
    assert np.allclose(cal.get_measurement("ref1")[1],
                       _handled("ref1")[1] * new_open / reference.divisor)


def test_short_reference_follows_the_corrected_short():
    """A SHORT pre-cal uses c0 = the Short of step 2 as the solver sees it."""
    cal = _cal(handled=("short", "dut"), keys=("open", "short", "dut"))
    cal.set_step_precal("short", _reference_now(KIND_OPEN))   # Short handled too
    cal.set_step_precal("dut", _reference_now(KIND_SHORT))
    assert np.allclose(cal.get_measurement("short")[1], _raw("short")[1])
    assert np.allclose(cal.get_measurement("dut")[1], _raw("dut")[1])


def test_precal_is_rebuilt_from_the_current_raw_sweep():
    """Old UI: a stale ``_precal_originals`` entry was re-normalized instead."""
    freqs, first = _handled("ref1")
    remeasured = first * (1 + 0.05j)
    cal = _cal(keys=("open", "short"))
    cal.set_measurement("ref1", freqs, first, precal=_reference_now(KIND_OPEN))
    cal.set_measurement("ref1", freqs, remeasured)            # measured again, same state
    c = _reference_now(KIND_SHORT)
    cal.set_step_precal("ref1", c)                             # re-calibrated
    c0 = cal.precal_reference_sweep(KIND_SHORT).divisor
    assert np.allclose(cal.get_measurement("ref1")[1], remeasured * c0 / c.divisor)
    assert np.array_equal(cal.get_raw_measurement("ref1")[1], remeasured)

    cal.clear_step_precal("ref1")
    assert np.array_equal(cal.get_measurement("ref1")[1], remeasured)
    assert not cal.is_precal_applied("ref1")


def test_precal_keeps_source_and_preset_temperature():
    """Old UI: applying/removing the pre-cal re-stored the sweep without its 18 C."""
    cal = _cal(keys=("open", "short", "ref2", "dut"))
    freqs, s11 = _raw("ref1")
    cal.set_measurement("ref1", freqs, s11, source="preset:water_18C", temperature_c=18.0)
    for change in (lambda: cal.set_step_precal("ref1", _reference_now(KIND_OPEN)),
                   lambda: cal.clear_step_precal("ref1"),
                   lambda: cal.set_step_precal("ref1", _reference_now(KIND_SHORT))):
        change()
        assert cal.standard_temperature("ref1") == 18.0
        assert cal.get_source("ref1") == "preset:water_18C"
    _eps(cal)
    assert cal.pattern_constants.temp_ref1_c == 18.0


def test_explicit_precal_none_replaces_the_step_precal():
    cal = _cal(handled=("ref1",), precal_kind=KIND_OPEN, keys=("open", "ref1"))
    cal.set_measurement("ref1", *_raw("ref1"), source="preset:x", precal=None)
    assert cal.step_precal("ref1") is None
    assert np.array_equal(cal.get_measurement("ref1")[1], _raw("ref1")[1])


def test_precal_on_another_grid_is_refused_without_changes():
    cal = _cal(keys=("open", "ref1"))
    freqs, s11 = _raw("open")
    try:
        cal.set_step_precal("ref1", PrecalReference(freqs=freqs[:-1], divisor=s11[:-1]))
    except ValueError:
        pass
    else:
        raise AssertionError("an off-grid pre-cal must be refused")
    assert cal.step_precal("ref1") is None
    assert np.array_equal(cal.get_measurement("ref1")[1], _raw("ref1")[1])


def test_sweep_on_another_grid_drops_only_that_steps_precal():
    cal = _cal(handled=("ref1", "ref2"), precal_kind=KIND_OPEN, keys=("open", "ref1", "ref2"))
    freqs, s11 = _raw("ref1")
    cal.set_measurement("ref1", freqs[::2], s11[::2])
    assert cal.step_precal("ref1") is None
    assert cal.is_precal_applied("ref2")


def test_changes_to_the_standards_invalidate_the_pattern_constants():
    cal = _cal()
    assert cal.compute_calibration()
    cal.set_step_precal("ref2", _reference_now(KIND_OPEN))
    assert cal.pattern_constants is None
    assert cal.compute_calibration()
    cal.set_measurement("ref1", *_raw("ref1"))       # a re-measured standard
    assert cal.pattern_constants is None
    assert cal.compute_calibration()
    cal.set_measurement("dut", *_raw("dut"))         # the DUT is not a standard
    assert cal.pattern_constants is not None


def test_clear_all_measurements_drops_every_precal():
    cal = _cal(handled=_HANDLED, precal_kind=KIND_OPEN)
    cal.clear_all_measurements()
    assert all(cal.step_precal(k) is None for k in _SWEEPS)


# --------------------------------------------------------------------------- #
# (3) Kits
# --------------------------------------------------------------------------- #

def test_precalibrated_kit_round_trip():
    session = _cal(handled=("ref2",), precal_kind=KIND_SHORT, temps={"ref1": 18.0})
    session.probe_key = "probe21mm"
    expected = _eps(session)

    with _tmp_kits() as kits:
        calibration_store.save_calibration("kit_pc", "kit_pc", session, "open_coax_liquids", 25.0)
        folder = kits / "kit_pc"
        assert (folder / "ref2.precal.s1p").exists()
        assert not any((folder / f"{k}.precal.s1p").exists() for k in ("open", "short", "ref1"))
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["precal_kinds"] == {"ref2": KIND_SHORT}

        fresh = PermittivityProbeCalibration()
        meta, warnings = calibration_store.apply_calibration(fresh, "kit_pc")

    assert meta.precal_kinds == {"ref2": KIND_SHORT} and isinstance(warnings, list)
    for key in _STANDARDS:                           # stored raw, as acquired
        expected_raw = (_handled if key == "ref2" else _raw)(key)[1]
        assert np.allclose(fresh.get_raw_measurement(key)[1], expected_raw, rtol=0, atol=1e-12)
        assert fresh.get_source(key) == "kit:kit_pc"
    assert fresh.is_precal_applied("ref2") and fresh.step_precal("ref2").kind == KIND_SHORT
    assert fresh.standard_temperature("ref1") == 18.0
    assert fresh.probe_key == "probe21mm"
    assert not fresh.is_standard_measured("dut")

    fresh.set_measurement("dut", *_raw("dut"))
    assert _max_diff(_eps(fresh), expected) < 1e-6


def test_dut_measured_later_with_a_kit_is_referred_to_the_kits_state():
    """The plus of the design: the kit's Open is c0 for a DUT pre-calibrated now."""
    session = _cal()
    expected = _eps(session)
    with _tmp_kits():
        calibration_store.save_calibration("kit_raw", "kit_raw", session, "open_coax_liquids", 25.0)
        fresh = PermittivityProbeCalibration()
        calibration_store.apply_calibration(fresh, "kit_raw")
    # Days later: the probe was certainly handled; OPEN measured before the DUT.
    fresh.set_measurement("dut", *_handled("dut"), precal=_reference_now(KIND_OPEN))
    assert _max_diff(_eps(fresh), expected) < 1e-6


def test_kit_without_precal_has_no_precal_files():
    with _tmp_kits() as kits:
        calibration_store.save_calibration("kit_raw", "kit_raw", _cal(), "open_coax_liquids", 25.0)
        assert not list((kits / "kit_raw").glob("*.precal.s1p"))
        fresh = PermittivityProbeCalibration()
        meta, _ = calibration_store.apply_calibration(fresh, "kit_raw")
    assert meta.precal_kinds == {}
    assert all(fresh.step_precal(k) is None for k in _STANDARDS)


def test_resaving_a_kit_without_precal_removes_the_stale_reference():
    session = _cal(handled=("ref1",), precal_kind=KIND_OPEN)
    with _tmp_kits() as kits:
        calibration_store.save_calibration("kit_x", "kit_x", session, "open_coax_liquids", 25.0)
        session.clear_step_precal("ref1")
        calibration_store.save_calibration("kit_x", "kit_x", session, "open_coax_liquids", 25.0)
        assert not (kits / "kit_x" / "ref1.precal.s1p").exists()
        assert calibration_store.load_calibration_precals("kit_x") == {}


def test_kit_with_a_missing_or_off_grid_reference_is_refused():
    session = _cal(handled=("ref1",), precal_kind=KIND_OPEN)
    with _tmp_kits() as kits:
        calibration_store.save_calibration("kit_bad", "kit_bad", session, "open_coax_liquids", 25.0)
        precal_file = kits / "kit_bad" / "ref1.precal.s1p"
        freqs, divisor = _raw("open")

        def _refused():
            fresh = _cal(keys=("dut",))             # must stay untouched on failure
            for load in (lambda: calibration_store.load_calibration("kit_bad"),
                         lambda: calibration_store.apply_calibration(fresh, "kit_bad")):
                try:
                    load()
                except ValueError:
                    pass
                else:
                    raise AssertionError("a kit without a usable reference must be refused")
            assert fresh.is_standard_measured("dut") and fresh.ref2_key == "ipa"

        precal_file.unlink()
        _refused()
        calibration_store._write_s1p(precal_file, freqs[::2], divisor[::2])
        _refused()


def test_legacy_kit_manifest_without_precal_fields_loads():
    with _tmp_kits() as kits:
        calibration_store.save_calibration("kit_old", "kit_old", _cal(), "open_coax_liquids", 25.0)
        manifest_path = kits / "kit_old" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        del manifest["precal_kinds"]
        manifest["schema_version"] = 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        fresh = PermittivityProbeCalibration()
        meta, _ = calibration_store.apply_calibration(fresh, "kit_old")
    assert meta.precal_kinds == {}
    assert np.allclose(fresh.get_measurement("ref1")[1], _raw("ref1")[1], rtol=0, atol=1e-12)


def test_exported_package_carries_each_precal():
    session = _cal(handled=_HANDLED, precal_kind=KIND_OPEN)
    with _tmp_kits(), tempfile.TemporaryDirectory() as out:
        folder = calibration_store.export_calibration(Path(out), "pkg", "pkg", session,
                                                      "open_coax_liquids", 25.0)
        with zipfile.ZipFile(folder / "pkg.charpkg") as zf:
            assert "ref2.precal.s1p" in zf.namelist()
            assert json.loads(zf.read("manifest.json"))["precal_kinds"] == {"ref2": KIND_OPEN}
        name = calibration_store.import_calibration(folder / "pkg.charpkg")
        fresh = PermittivityProbeCalibration()
        calibration_store.apply_calibration(fresh, name)
    assert fresh.is_precal_applied("ref2")


# --------------------------------------------------------------------------- #
# (3) Presets
# --------------------------------------------------------------------------- #

def test_preset_round_trip_keeps_the_raw_sweep_and_its_reference():
    reference = _reference_now(KIND_OPEN)
    freqs, raw = _handled("ref1")
    with _tmp_presets() as presets:
        ps.save_preset("w_pc", freqs, raw, ps.PresetMeta(name="w_pc", liquid_key="water"),
                       precal=reference)
        meta = ps.read_meta("w_pc")
        assert meta.precal_kind == KIND_OPEN and not meta.precal_open_applied
        assert (presets / "w_pc.precal.s1p").exists()
        assert [m.name for m in ps.list_presets()] == ["w_pc"]   # the reference is not a preset

        f2, s2, _, ref2 = ps.load_preset_with_precal("w_pc")
        assert np.allclose(s2, raw, rtol=0, atol=1e-12)
        assert np.allclose(ref2.divisor, reference.divisor, rtol=0, atol=1e-12)

        # Overwritten by a sweep without pre-cal: the reference file goes away.
        ps.save_preset("w_pc", freqs, raw, ps.PresetMeta(name="w_pc", liquid_key="water"))
        assert not (presets / "w_pc.precal.s1p").exists()
        assert ps.load_preset_with_precal("w_pc")[3] is None

        ps.save_preset("w_pc", freqs, raw, ps.PresetMeta(name="w_pc", liquid_key="water"),
                       precal=reference)
        assert ps.delete_preset("w_pc")
        assert not any(presets.glob("w_pc*"))


def test_legacy_normalized_preset_is_refused():
    freqs, raw = _raw("ref1")
    with _tmp_presets() as presets:
        # What the old wizard wrote: S11 / c(f) flagged, but no c(f).
        ps.save_preset("old_pc", freqs, raw, ps.PresetMeta(name="old_pc", liquid_key="water"))
        sidecar = presets / "old_pc.json"
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        data["precal_open_applied"] = True
        sidecar.write_text(json.dumps(data), encoding="utf-8")
        try:
            ps.load_preset_with_precal("old_pc")
        except ps.PresetPrecalError:
            pass
        else:
            raise AssertionError("a legacy normalized preset must be refused")

        try:
            ps.save_preset("new_pc", freqs, raw, ps.PresetMeta(
                name="new_pc", liquid_key="water", precal_open_applied=True))
        except ValueError:
            pass
        else:
            raise AssertionError("presets are stored raw: the legacy flag cannot be written")


# --------------------------------------------------------------------------- #
# Wizard UI paths (no widgets are created)
# --------------------------------------------------------------------------- #

def _fake_wizard(cal):
    freqs = _raw("open")[0]
    return types.SimpleNamespace(
        perm_calibration=cal,
        epsilon_result=None,
        status_label=None,
        next_button=types.SimpleNamespace(setEnabled=lambda *_: None),
        get_sweep_steps=lambda: len(freqs),
        get_sweep_start_frequency=lambda: float(freqs[0]),
        get_sweep_stop_frequency=lambda: float(freqs[-1]),
    )


def _screen():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps import (
        standard_screen,
    )
    return standard_screen


def test_preset_brings_its_own_precal_instead_of_the_steps():
    """Old UI: a normalized preset loaded with the step's pre-cal became S/c^2."""
    ss = _screen()
    preset_ref = _reference_now(KIND_OPEN)
    freqs, raw = _handled("ref1")
    cal = _cal(keys=("open", "short"))
    cal.set_step_precal("ref1", _reference_now(KIND_SHORT))   # the step's own, from now
    wizard = _fake_wizard(cal)
    changes = []
    wizard._on_precal_changed_hook = lambda: changes.append("changed")
    with _tmp_presets():
        ps.save_preset("w_pc", freqs, raw, ps.PresetMeta(name="w_pc", liquid_key="water",
                                                         temperature_c=18.0), precal=preset_ref)
        loaded = ss._load_preset_into_step(wizard, types.SimpleNamespace(key="ref1"),
                                           "water", {}, "w_pc")
    assert loaded is not None
    assert cal.step_precal("ref1").kind == KIND_OPEN and changes == ["changed"]
    expected = raw * _raw("open")[1] / preset_ref.divisor
    assert np.allclose(cal.get_measurement("ref1")[1], expected, rtol=0, atol=1e-9)
    assert cal.standard_temperature("ref1") == 18.0


def test_store_measurement_keeps_the_step_precal_and_reports_a_drop():
    ss = _screen()
    cal = _cal(keys=("open",))
    cal.set_step_precal("dut", _reference_now(KIND_OPEN))
    wizard = _fake_wizard(cal)
    changes = []
    wizard._on_precal_changed_hook = lambda: changes.append("changed")

    freqs, s11 = _handled("dut")
    _, stored = ss._store_measurement(wizard, "dut", freqs, s11)
    assert np.allclose(stored, s11 * _raw("open")[1] / _reference_now(KIND_OPEN).divisor)
    assert changes == []

    ss._store_measurement(wizard, "dut", freqs[::2], s11[::2])
    assert cal.step_precal("dut") is None and changes == ["changed"]


def test_importing_a_measurement_keeps_the_imported_precal():
    """Pre-cal imported in the dialog, then the step's sweep imported: it stays."""
    ss = _screen()
    cal = _cal(keys=("open", "short"))
    reference = _reference_now(KIND_OPEN)
    cal.set_step_precal("ref1", reference)
    wizard = _fake_wizard(cal)
    changes = []
    wizard._on_precal_changed_hook = lambda: changes.append("changed")
    freqs, s11 = _handled("ref1")
    originals = ss._ask_s1p_matching_sweep, ss._render
    ss._ask_s1p_matching_sweep = lambda *_: (freqs, s11)      # the file dialog
    ss._render = lambda *_, **__: None
    try:
        ss._on_import(wizard, types.SimpleNamespace(key="ref1"), "water", "blue",
                      types.SimpleNamespace(setText=lambda *_: None), {},
                      {"show_indicative": False})
    finally:
        ss._ask_s1p_matching_sweep, ss._render = originals
    assert cal.step_precal("ref1") is reference and changes == []
    assert cal.get_source("ref1") == "imported"
    assert np.allclose(cal.get_measurement("ref1")[1],
                       s11 * _raw("open")[1] / reference.divisor)


def test_kit_loader_configures_the_whole_session():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.kit_loader import (
        configure_wizard_from_kit,
    )

    session = _cal(handled=("ref2",), precal_kind=KIND_OPEN, temps={"ref1": 18.0})
    session.set_reference_liquids("ethanol", "ipa")   # not the descriptor default
    session.probe_key = "probe21mm"
    wizard = types.SimpleNamespace(perm_calibration=PermittivityProbeCalibration())
    with _tmp_kits():
        calibration_store.save_calibration("kit_ui", "kit_ui", session, "open_coax_liquids", 22.0)
        descriptor = configure_wizard_from_kit(wizard, "kit_ui")

    cal = wizard.perm_calibration
    assert descriptor.id == "open_coax_liquids"
    assert wizard.selected_technique_id == "open_coax_liquids"
    assert wizard.selected_method and wizard.selected_method != descriptor.name_token
    assert wizard.temperature_c == 22.0 and cal.temperature_c == 22.0
    freqs = _raw("open")[0]
    assert wizard.sweep_steps == len(freqs)
    assert wizard.sweep_start_freq == freqs[0] and wizard.sweep_stop_freq == freqs[-1]
    assert wizard.ref_liquid_keys == {"ref1": "ethanol", "ref2": "ipa"}
    assert (cal.ref1_key, cal.ref2_key) == ("ethanol", "ipa")
    assert cal.probe_key == "probe21mm"
    assert cal.standard_temperature("ref1") == 18.0      # the menu path used to drop it
    assert cal.is_precal_applied("ref2")                  # neither path kept it
    assert isinstance(wizard.temperature_warnings, list)


def test_kit_loader_refuses_an_unknown_technique_without_changes():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.kit_loader import (
        configure_wizard_from_kit,
    )

    wizard = types.SimpleNamespace(perm_calibration=_cal(keys=("dut",)))
    with _tmp_kits():
        calibration_store.save_calibration("kit_t", "kit_t", _cal(), "no_such_technique", 25.0)
        try:
            configure_wizard_from_kit(wizard, "kit_t")
        except ValueError:
            pass
        else:
            raise AssertionError("an unknown technique must be refused")
    assert wizard.perm_calibration.is_standard_measured("dut")
    assert not hasattr(wizard, "selected_technique_id")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
