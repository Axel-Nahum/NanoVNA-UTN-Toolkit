"""
Unit tests for the simplified (single-reference-liquid) permittivity solver.

EN: Three layers: (1) a SYNTHETIC exactness test -- the barycentric formula
    must recover a known epsilon exactly through an arbitrary Moebius error
    box, which is the mathematical claim the method rests on; (2) a GOLDEN
    test against the bundled 2026 probe-21mm presets (real Copper Mountain R60
    sweeps shipped with the toolkit), checking the result against the NPL
    ethanol model inside the band where the capacitive (Gn = 0) approximation
    holds; (3) guard-rail tests (degenerate denominators, shape mismatch,
    Ptolemy identity). Runnable with pytest or directly.

ES: Tres capas: (1) test SINTETICO de exactitud -- la formula baricentrica
    debe recuperar un epsilon conocido exactamente a traves de una caja de
    error de Moebius arbitraria, que es el argumento matematico del metodo;
    (2) test GOLDEN contra los presets 2026 sonda 21 mm incluidos en el
    toolkit (barridos reales del Copper Mountain R60), contrastando contra el
    modelo NPL del etanol dentro de la banda donde vale la aproximacion
    capacitiva (Gn = 0); (3) tests de guardas (denominadores degenerados,
    formas incompatibles, identidad de Ptolomeo). Ejecutable con pytest o
    directo.
"""

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    evaluate_epsilon_r,
    get_reference_liquid,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.simplified_solver import (
    EPS_AIR,
    solve_epsilon_simplified,
)


def _moebius(eps, a, b, c, d):
    """Arbitrary bilinear (Moebius) map of epsilon -> measured Gamma."""
    return (a * eps + b) / (c * eps + d)


def _synthetic_standards(f_hz, temp_c, a, b, c, d):
    """Gammas of Short (eps->inf), Open (air) and water through the error box."""
    water = get_reference_liquid("water")
    eps_ref, _ = evaluate_epsilon_r(water, f_hz, temp_c)
    s11_short = np.full_like(f_hz, a / c, dtype=complex)   # lim eps->inf of Moebius
    s11_open = _moebius(np.full(f_hz.shape, EPS_AIR, dtype=complex), a, b, c, d)
    s11_ref = _moebius(eps_ref, a, b, c, d)
    return water, eps_ref, s11_open, s11_short, s11_ref


def test_synthetic_moebius_exact_recovery():
    """The formula must invert ANY Moebius error box exactly (its core claim)."""
    f = np.linspace(10e6, 2e9, 64)
    temp_c = 25.0
    # Arbitrary invertible error box: nothing special about these numbers.
    a, b, c, d = 0.7 - 0.2j, 1.3 + 0.4j, 0.05 + 0.01j, 1.0 - 0.3j

    water, _, s11_open, s11_short, s11_ref = _synthetic_standards(f, temp_c, a, b, c, d)

    # Frequency-dependent "unknown" with losses (eps'' > 0 -> Im < 0).
    eps_true = (30.0 - 5.0j) - f / f[-1] * (10.0 - 2.0j)
    s11_dut = _moebius(eps_true, a, b, c, d)

    res = solve_epsilon_simplified(f, s11_dut, s11_open, s11_short, s11_ref, water, temp_c)

    assert not res.gap_mask.any()
    np.testing.assert_allclose(res.eps, eps_true, rtol=1e-9)
    # Ptolemy identity: barycentric weights sum to -1 identically.
    np.testing.assert_allclose(res.coef_ref + res.coef_air, -1.0, atol=1e-9)


def test_synthetic_recovery_with_nonwater_reference():
    """The reference liquid is a parameter, not hard-wired water (unlike the repo)."""
    f = np.linspace(50e6, 1.5e9, 32)
    temp_c = 25.0
    a, b, c, d = 1.1 + 0.1j, -0.4 + 0.9j, 0.02 - 0.03j, 0.8 + 0.2j

    ipa = get_reference_liquid("ipa")
    eps_ref, _ = evaluate_epsilon_r(ipa, f, temp_c)
    s11_short = np.full_like(f, a / c, dtype=complex)
    s11_open = _moebius(np.full(f.shape, EPS_AIR, dtype=complex), a, b, c, d)
    s11_ref = _moebius(eps_ref, a, b, c, d)

    eps_true = np.full(f.shape, 42.0 - 7.0j, dtype=complex)
    s11_dut = _moebius(eps_true, a, b, c, d)

    res = solve_epsilon_simplified(f, s11_dut, s11_open, s11_short, s11_ref, ipa, temp_c)
    np.testing.assert_allclose(res.eps, eps_true, rtol=1e-9)
    assert res.ref_liquid_key == "ipa"


def test_golden_ethanol_2026_probe21():
    """
    Real data: bundled 2026 R60 probe-21mm presets, ethanol as the unknown.

    Inside 50 MHz - 1.5 GHz the capacitive model holds for the 21 mm probe and
    eps' must track the NPL ethanol model within 10 % (measured: 2-6 %).
    Outside that band the deviation is EXPECTED (noise floor below, neglected
    radiation above) -- that is the documented trade-off of this method.
    """
    try:
        from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import (
            preset_store,
        )
        f, s_open, _ = None, None, None
        f, s_open = preset_store.load_preset("open_air_r60_probe21_2026")[:2]
        _, s_short = preset_store.load_preset("short_r60_probe21_2026")[:2]
        _, s_ref = preset_store.load_preset("water_r60_probe21_2026")[:2]
        _, s_dut = preset_store.load_preset("ethanol_r60_probe21_2026")[:2]
    except Exception:
        import pytest
        pytest.skip("bundled 2026 presets not available")

    water = get_reference_liquid("water")
    temp_c = 22.0
    res = solve_epsilon_simplified(f, s_dut, s_open, s_short, s_ref, water, temp_c)

    model, _ = evaluate_epsilon_r(get_reference_liquid("ethanol"), f, temp_c)
    band = (f >= 50e6) & (f <= 1.5e9)

    rel_err = np.abs(np.real(res.eps[band]) - np.real(model[band])) / np.real(model[band])
    assert np.median(rel_err) < 0.10, f"median eps' error {np.median(rel_err):.1%}"

    # Losses must be present (Im < 0) through the relaxation region. Real data:
    # a narrow glitch near 690 MHz flips ~14/1001 points slightly positive, so
    # require the bulk of the band rather than every single point.
    relax = (f >= 200e6) & (f <= 1.2e9)
    assert np.mean(np.imag(res.eps[relax]) < 0) > 0.95
    assert np.median(np.imag(res.eps[relax])) < -3.0

    # Spot values recorded when this test was written (regression anchors).
    for f_tgt, er_expected in ((0.1e9, 26.0), (0.5e9, 20.4), (1.0e9, 13.0)):
        i = int(np.argmin(np.abs(f - f_tgt)))
        assert abs(np.real(res.eps[i]) - er_expected) / er_expected < 0.05


def test_degenerate_denominator_yields_nan_and_warning():
    """DUT identical to Short collapses the cross-ratio -> NaN + warning, no crash."""
    f = np.linspace(10e6, 1e9, 8)
    water = get_reference_liquid("water")
    _, _, s11_open, s11_short, s11_ref = _synthetic_standards(
        f, 25.0, 0.9 - 0.1j, 1.1 + 0.2j, 0.03 + 0.02j, 1.0
    )
    res = solve_epsilon_simplified(
        f, s11_short.copy(), s11_open, s11_short, s11_ref, water, 25.0
    )
    assert res.gap_mask.all()
    assert np.isnan(res.eps).all()
    assert any("degenerate" in w for w in res.warnings)


def test_shape_mismatch_raises():
    f = np.linspace(10e6, 1e9, 8)
    water = get_reference_liquid("water")
    ok = np.zeros(8, dtype=complex)
    bad = np.zeros(7, dtype=complex)
    try:
        solve_epsilon_simplified(f, bad, ok, ok, ok, water, 25.0)
    except ValueError:
        pass
    else:
        raise AssertionError("shape mismatch should raise ValueError")


def test_out_of_range_temperature_propagates_warning():
    f = np.linspace(10e6, 1e9, 8)
    ipa = get_reference_liquid("ipa")  # tabulated 10-30 C
    _, _, s11_open, s11_short, s11_ref = _synthetic_standards(
        f, 25.0, 1.0, 0.5 + 0.5j, 0.02j, 1.0
    )
    res = solve_epsilon_simplified(
        f, s11_ref.copy(), s11_open, s11_short, s11_ref, ipa, 80.0
    )
    assert any("outside" in w for w in res.warnings)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
