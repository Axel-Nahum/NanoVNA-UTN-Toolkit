"""
Reference-liquid models checked against their published tables.

EN: The expected values below are transcribed independently of
    ``reference_liquids.py`` from Kaatze (1989) Table III and NPL Report
    MAT 23 (Table 6, Section 7 and the Section 8 "best-fit" tables at 20 C),
    so a slip in the module's tables or in its temperature interpolation
    shows up here. Runnable with pytest or directly:
    ``python test_reference_liquids.py``.

ES: Los valores esperados se transcriben aparte de ``reference_liquids.py``,
    desde la Tabla III de Kaatze (1989) y el NPL Report MAT 23 (Tabla 6,
    seccion 7 y las tablas "best-fit" de la seccion 8 a 20 C), para que un
    error en las tablas del modulo o en su interpolacion en temperatura
    aparezca aca. Ejecutable con pytest o directamente:
    ``python test_reference_liquids.py``.
"""

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    DebyeModelType,
    ReferenceLiquid,
    evaluate_epsilon_r,
    get_reference_liquid,
    list_reference_liquids,
)

# NPL MAT 23 Section 8 frequencies (GHz). Propan-2-ol stops at 3 GHz.
_NPL_F_GHZ = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
              1.2, 1.5, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)

# NPL MAT 23 Section 8, "best-fit" columns at 20 C: (eps', eps'').
_NPL_BEST_FIT_20C = {
    "ethanol": (  # Debye-Gamma
        (24.86, 2.46), (24.03, 4.71), (22.77, 6.62), (21.26, 8.10), (19.66, 9.15),
        (18.07, 9.83), (16.57, 10.21), (15.21, 10.36), (14.00, 10.33), (12.93, 10.19),
        (11.20, 9.72), (9.36, 8.82), (8.14, 7.94), (7.56, 7.42), (6.57, 6.31),
        (5.99, 5.47), (5.63, 4.83), (5.38, 4.34), (5.21, 3.94), (5.08, 3.62)),
    "methanol": (  # single-Debye
        (33.60, 0.99), (33.50, 1.97), (33.33, 2.94), (33.09, 3.89), (32.79, 4.81),
        (32.43, 5.69), (32.02, 6.54), (31.56, 7.34), (31.06, 8.10), (30.52, 8.81),
        (29.35, 10.08), (27.47, 11.60), (25.55, 12.69), (24.28, 13.20), (21.33, 13.89),
        (18.79, 13.97), (16.68, 13.67), (14.95, 13.18), (13.55, 12.60), (12.42, 11.98)),
    "ipa": (  # propan-2-ol, double-Debye
        (18.87, 4.37), (16.05, 7.14), (13.12, 8.20), (10.76, 8.24), (9.02, 7.83),
        (7.77, 7.27), (6.88, 6.69), (6.22, 6.16), (5.73, 5.68), (5.36, 5.26),
        (4.84, 4.56), (4.38, 3.79), (4.12, 3.25), (4.00, 2.97), (3.80, 2.46),
        (3.67, 2.12)),
    "butanol": (  # butan-1-ol, double-Debye
        (16.26, 4.97), (12.65, 7.14), (9.72, 7.29), (7.79, 6.72), (6.57, 6.02),
        (5.78, 5.38), (5.24, 4.82), (4.87, 4.36), (4.60, 3.97), (4.40, 3.64),
        (4.12, 3.13), (3.89, 2.59), (3.75, 2.22), (3.68, 2.04), (3.57, 1.71),
        (3.49, 1.49), (3.42, 1.34), (3.37, 1.22), (3.33, 1.13), (3.29, 1.05)),
}

# Static permittivity at each tabulated temperature: Kaatze Table III (water),
# NPL MAT 23 Table 6 (the rest; for the alcohols it equals the eps_s column of
# Section 7, note 24). Propan-2-ol has no admittance-cell value (note 30).
_STATIC = {
    "water": ((0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60),
              (87.91, 85.83, 83.92, 82.05, 80.21, 78.36, 76.56, 74.87, 73.18, 69.89, 66.70)),
    "ethanol": ((10, 15, 20, 25, 30, 35, 40, 45, 50),
                (26.79, 25.95, 25.16, 24.43, 23.65, 22.88, 22.16, 21.45, 20.78)),
    "methanol": ((10, 15, 20, 25, 30, 35, 40, 45, 50),
                 (35.74, 34.68, 33.64, 32.66, 31.69, 30.78, 29.85, 28.95, 28.19)),
    "butanol": ((10, 15, 20, 25, 30, 35, 40),
                (19.54, 18.86, 18.19, 17.53, 16.89, 16.26, 15.65)),
    "cyclohexane": ((10, 15, 20, 25, 30, 35, 40, 45, 50),
                    (2.040, 2.033, 2.024, 2.015, 2.008, 2.000, 1.992, 1.984, 1.975)),
    "acetone": ((5, 10, 15, 20, 25, 30, 35, 40),
                (22.80, 22.21, 21.65, 21.13, 20.59, 20.10, 19.60, 19.12)),
}


def test_every_registered_liquid_has_a_model():
    keys = {liquid.key for liquid in list_reference_liquids()}
    assert {"water", "ipa", "ethanol", "methanol", "butanol", "cyclohexane", "acetone"} <= keys
    for liquid in list_reference_liquids():
        assert liquid.has_debye_model, liquid.key
        eps, warns = evaluate_epsilon_r(liquid, np.array([1e8, 1e9]), 20.0)
        assert warns == [], (liquid.key, warns)
        assert np.isfinite(eps).all(), liquid.key


def test_water_at_20c_is_kaatze_table_iii():
    """Kaatze 1989 Table III at 20 C: eps_s 80.21, eps_inf 5.6, tau 9.36 ps.
    The old order-2 fit gave tau 9.69 ps and eps'' 6.78 (+3.8 %) at 1.5 GHz."""
    f = np.array([1e6, 1e8, 5e8, 1e9, 1.5e9, 3e9, 6e9])
    eps, _ = evaluate_epsilon_r(get_reference_liquid("water"), f, 20.0)
    expected = 5.6 + (80.21 - 5.6) / (1.0 + 1j * 2.0 * np.pi * f * 9.36e-12)
    assert np.max(np.abs(eps - expected)) < 1e-9
    assert abs(-eps[4].imag - 6.531) < 0.001
    # NPL MAT 23 Table 6 measured 80.29 +/- 0.20 (k=2) at 20 C.
    assert abs(eps[0].real - 80.29) <= 0.20


def test_static_permittivity_at_every_tabulated_temperature():
    f = np.array([1e3])   # far below every relaxation: eps' -> eps_s
    for key, (temps, eps_s) in _STATIC.items():
        liquid = get_reference_liquid(key)
        for temp_c, expected in zip(temps, eps_s):
            eps, warns = evaluate_epsilon_r(liquid, f, float(temp_c))
            assert warns == [], (key, temp_c, warns)
            assert abs(eps[0].real - expected) < 1e-6, (key, temp_c, eps[0], expected)


def test_npl_best_fit_tables_at_20c():
    """The tables are rounded to 0.01. The same tolerance rejects the old
    order-2 polynomial fit, which was off by 0.12 (ethanol), 0.064
    (methanol) and 0.013 (IPA) at 20 C."""
    for key, rows in _NPL_BEST_FIT_20C.items():
        f = np.array(_NPL_F_GHZ[:len(rows)]) * 1e9
        eps, warns = evaluate_epsilon_r(get_reference_liquid(key), f, 20.0)
        assert warns == []
        expected = np.array([re - 1j * im for re, im in rows])
        err_re = np.abs(eps.real - expected.real)
        err_im = np.abs(eps.imag - expected.imag)
        worst = int(np.argmax(np.maximum(err_re, err_im)))
        assert err_re.max() <= 0.01 and err_im.max() <= 0.01, (
            f"{key} @ {_NPL_F_GHZ[worst]} GHz: {eps[worst]:.3f} vs NPL {expected[worst]:.2f}")


def test_npl_section_1_3_interpolation_example():
    """NPL MAT 23 section 1.3: methanol at 2.2 GHz and 22.0 C, linear
    interpolation between 20 C and 25 C gives eps' = 23.33, eps'' = 13.24."""
    eps, warns = evaluate_epsilon_r(get_reference_liquid("methanol"), np.array([2.2e9]), 22.0)
    assert warns == []
    assert abs(eps[0].real - 23.33) <= 0.005, eps[0]
    assert abs(-eps[0].imag - 13.24) <= 0.005, eps[0]


def test_interpolation_is_linear_between_neighbours_and_continuous():
    f = np.array([1e8, 1e9, 3e9])
    for key in ("water", "ipa", "ethanol", "butanol"):
        liquid = get_reference_liquid(key)
        e20, _ = evaluate_epsilon_r(liquid, f, 20.0)
        e25, _ = evaluate_epsilon_r(liquid, f, 25.0)
        e22, _ = evaluate_epsilon_r(liquid, f, 22.0)
        assert np.max(np.abs(e22 - (0.6 * e20 + 0.4 * e25))) < 1e-9, key
        below, _ = evaluate_epsilon_r(liquid, f, 20.0 - 1e-9)
        above, _ = evaluate_epsilon_r(liquid, f, 20.0 + 1e-9)
        assert np.max(np.abs(below - e20)) < 1e-6 and np.max(np.abs(above - e20)) < 1e-6, key


def test_water_follows_temperature_monotonically():
    """eps' at 100 MHz falls and the relaxation speeds up as water warms."""
    liquid = get_reference_liquid("water")
    temps = np.arange(0.0, 60.01, 0.5)
    static = [evaluate_epsilon_r(liquid, np.array([1e8]), t)[0][0].real for t in temps]
    assert np.all(np.diff(static) < 0)


def test_cyclohexane_is_lossless_and_flat():
    f = np.logspace(6, np.log10(6e9), 50)
    eps, _ = evaluate_epsilon_r(get_reference_liquid("cyclohexane"), f, 20.0)
    assert np.all(eps == 2.024 + 0j)
    eps, _ = evaluate_epsilon_r(get_reference_liquid("cyclohexane"), f, 22.5)
    assert np.allclose(eps, 0.5 * (2.024 + 2.015))


def test_acetone_stays_near_its_static_value_in_the_vna_band():
    """NPL note 23: acetone relaxes far above 5 GHz, so below 1.5 GHz eps'
    is its static value; the small loss comes from the assumed Debye term."""
    f = np.linspace(1e6, 1.5e9, 100)
    eps, _ = evaluate_epsilon_r(get_reference_liquid("acetone"), f, 20.0)
    assert np.max(np.abs(eps.real - 21.13)) < 0.02
    assert np.all(eps.imag <= 0) and -eps.imag.min() < 1.0


def test_out_of_range_warns_for_the_new_liquids():
    for key, temp_c in (("acetone", 45.0), ("butanol", 45.0), ("cyclohexane", 5.0)):
        eps, warns = evaluate_epsilon_r(get_reference_liquid(key), np.array([1e9]), temp_c)
        assert warns, key
        assert np.isfinite(eps).all(), key


def test_extrapolation_stays_passive_near_the_table():
    """Outside the table the two outermost rows are extended linearly. That
    stays physical (eps'' >= 0, eps' >= 1) for at least 15 C past every edge
    of every liquid; checked here at 10 C."""
    f = np.logspace(5, np.log10(6e9), 200)
    for liquid in list_reference_liquids():
        for temp_c in (liquid.temp_min_c - 10.0, liquid.temp_max_c + 10.0):
            eps, warns = evaluate_epsilon_r(liquid, f, temp_c)
            assert warns, (liquid.key, temp_c)
            assert np.all(eps.imag <= 1e-12) and np.all(eps.real >= 1.0), (liquid.key, temp_c)


def test_malformed_table_is_rejected():
    try:
        ReferenceLiquid(
            key="broken", display_name="Broken", model_type=DebyeModelType.NONPOLAR,
            temp_axis_c=(10, 15, 20), columns={"eps_s": (2.0, 2.1)},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("a column shorter than the temperature axis must be rejected")


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
