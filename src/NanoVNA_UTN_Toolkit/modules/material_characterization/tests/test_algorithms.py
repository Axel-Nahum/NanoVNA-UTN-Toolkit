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
