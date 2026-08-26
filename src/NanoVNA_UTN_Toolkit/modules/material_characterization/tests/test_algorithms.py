"""
Sanity unit tests for the material-characterization algorithm layer.

EN: Stage-1 sanity checks (not the authoritative MATLAB golden-value suite,
    which is Stage 2). They verify the Debye sign convention, the degree-5
    solver round-trip, the frequency-grid guard, and the reference-liquid
    registry. Runnable with pytest or directly: ``python test_algorithms.py``.

ES: Verificaciones de cordura de la Etapa 1 (no es la suite autoritativa de
    valores de referencia MATLAB, que es de la Etapa 2). Verifican la
    convención de signo Debye, el round-trip del solver de grado 5, la
    validación de grilla de frecuencia y el registro de líquidos de referencia.
    Ejecutable con pytest o directamente: ``python test_algorithms.py``.
"""

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid,
    list_reference_liquids,
    evaluate_epsilon_r,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.pattern_constants import (
    PatternConstants,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.permittivity_solver import (
    solve_epsilon_r,
)


def test_reference_registry_has_water_and_ipa():
    keys = {liquid.key for liquid in list_reference_liquids()}
    assert {"water", "ipa"} <= keys
    assert get_reference_liquid("water").validated
    assert get_reference_liquid("ipa").validated


def test_water_debye_sign_convention():
    f = np.array([1e8, 1e9, 2e9])
    eps, warns = evaluate_epsilon_r(get_reference_liquid("water"), f, 25.0)
    assert warns == []
    assert np.all(eps.real > 0)
    assert np.all(eps.imag <= 1e-9)             # eps = eps' - j*eps'' (passive)
    assert 70.0 < eps.real[1] < 82.0            # water ~78 at 25 C, 1 GHz


def test_ipa_debye_sign_convention():
    f = np.array([1e8, 1e9, 2e9])
    eps, warns = evaluate_epsilon_r(get_reference_liquid("ipa"), f, 25.0)
    assert warns == []
    assert np.all(eps.real > 0)
    assert np.all(eps.imag <= 1e-9)


def test_temperature_out_of_range_warns_not_raises():
    f = np.array([1e9])
    eps, warns = evaluate_epsilon_r(get_reference_liquid("ipa"), f, 80.0)
    assert warns                                 # extrapolation warning present
    assert np.isfinite(eps).all()                # still returns finite values


def test_solver_roundtrips_known_epsilon():
    """Craft a synthetic case whose third_term encodes a known epsilon(f)."""
    n = 21
    f = np.linspace(1e8, 2e9, n)
    eps_true = np.linspace(20, 25, n) - 1j * np.linspace(3, 6, n)
    gn = np.full(n, 0.01 - 0.002j)
    third_req = -(eps_true + gn * np.power(eps_true, 2.5))

    # With s_short=-1, s_ref1=0, s_ref2=+1, y_ref1=0, y_ref2=1:
    #   third = -2*s_m/(s_m+1)  ->  solve s_m for the required third_term.
    s_short = np.full(n, -1 + 0j)
    s_ref1 = np.full(n, 0 + 0j)
    s_ref2 = np.full(n, 1 + 0j)
    s_m = -third_req / (2 + third_req)

    pc = PatternConstants(
        f_hz=f, temp_c=25.0, gn=gn,
        y_ref1=np.zeros(n, complex), y_ref2=np.ones(n, complex),
        s11_short=s_short, s11_ref1=s_ref1, s11_ref2=s_ref2,
        ref1_key="water", ref2_key="ipa", warnings=[],
    )
    res = solve_epsilon_r(s_m, pc)
    assert res.gap_mask.sum() == 0
    assert np.nanmax(np.abs(res.eps_selected - eps_true)) < 1e-9
    assert res.eps_candidates.shape == (n, 5)


def test_grid_mismatch_blocks_calibration():
    from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_probe_calibration import (
        PermittivityProbeCalibration,
    )
    m = PermittivityProbeCalibration()
    assert m.set_reference_liquids("water", "ipa")
    m.set_temperature(25.0)
    f1 = np.linspace(1e8, 1e9, 11)
    f2 = np.linspace(1e8, 1e9, 21)               # different grid
    z = np.zeros_like
    m.set_measurement("open", f1, z(f1) + 0.5)
    m.set_measurement("short", f1, z(f1) - 0.9)
    m.set_measurement("ref1", f1, z(f1) + 0.1j)
    m.set_measurement("ref2", f2, z(f2) + 0.2j)  # mismatched
    assert m.compute_calibration() is False


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


def _synthetic_pattern_case(n=21):
    """Same synthetic construction as the roundtrip test, shared by seed tests."""
    f = np.linspace(1e8, 2e9, n)
    eps_true = np.linspace(20, 25, n) - 1j * np.linspace(3, 6, n)
    gn = np.full(n, 0.01 - 0.002j)
    third_req = -(eps_true + gn * np.power(eps_true, 2.5))
    s_m = -third_req / (2 + third_req)
    pc = PatternConstants(
        f_hz=f, temp_c=25.0, gn=gn,
        y_ref1=np.zeros(n, complex), y_ref2=np.ones(n, complex),
        s11_short=np.full(n, -1 + 0j), s11_ref1=np.zeros(n, complex),
        s11_ref2=np.ones(n, complex),
        ref1_key="water", ref2_key="ipa", warnings=[],
    )
    return f, eps_true, s_m, pc


def test_seeded_solver_follows_seed_and_attaches_crosscheck():
    """With eps_seed given, the nearest root to the seed is selected and the
    seed travels in the result as eps_crosscheck (for the UI overlay)."""
    _f, eps_true, s_m, pc = _synthetic_pattern_case()

    seed = eps_true + (0.3 - 0.1j)          # slightly-off seed, as in real use
    res = solve_epsilon_r(s_m, pc, eps_seed=seed)
    assert np.nanmax(np.abs(res.eps_selected - eps_true)) < 1e-9
    assert res.eps_crosscheck is not None
    np.testing.assert_allclose(res.eps_crosscheck, seed)

    # NaN gaps in the seed fall back to the unseeded tracker (no crash, no gap).
    seed_gappy = seed.copy()
    seed_gappy[5:9] = np.nan + 0j
    res2 = solve_epsilon_r(s_m, pc, eps_seed=seed_gappy)
    assert np.nanmax(np.abs(res2.eps_selected - eps_true)) < 1e-9

    # Unseeded behaviour unchanged: no crosscheck attached.
    res3 = solve_epsilon_r(s_m, pc)
    assert res3.eps_crosscheck is None


def test_golden_full_method_seeded_2026():
    """Regression (H13 / task 5.3): full method on the bundled 2026 probe-21mm
    presets, swept from 1 MHz, must land on the canonical ethanol branch."""
    try:
        from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import (
            preset_store,
        )
        from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_probe_calibration import (
            PermittivityProbeCalibration,
        )
        data = {
            key: preset_store.load_preset(name)[:2]
            for key, name in (
                ("open", "open_air_r60_probe21_2026"),
                ("short", "short_r60_probe21_2026"),
                ("ref1", "water_r60_probe21_2026"),
                ("ref2", "ipa_r60_probe21_2026"),
                ("dut", "ethanol_r60_probe21_2026"),
            )
        }
    except Exception:
        import pytest
        pytest.skip("bundled 2026 presets not available")

    cal = PermittivityProbeCalibration()
    assert cal.set_reference_liquids("water", "ipa")
    cal.set_temperature(22.0)
    for key, (freqs, s11) in data.items():
        cal.set_measurement(key, freqs, s11)

    res = cal.compute_epsilon()
    assert res is not None
    assert res.eps_crosscheck is not None     # the simplified seed was used

    for f_tgt, expected in ((0.1e9, 23.36 - 3.59j),
                            (0.5e9, 15.59 - 9.64j),
                            (1.0e9, 9.55 - 8.95j)):
        i = int(np.argmin(np.abs(res.f_hz - f_tgt)))
        got = res.eps_selected[i]
        assert abs(got - expected) < 0.05 * abs(expected), (
            f"@{f_tgt/1e9:.1f} GHz: {got:.3f} vs expected {expected:.3f}"
        )
