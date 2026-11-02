"""
Consistency checks behind chapter 6 of report R6051 (open-ended coaxial probe).

EN: The identities the report states about the two-liquid (full) and the
    single-liquid (simplified) methods, checked on the real NanoVNA-H + 3 mm
    probe sweeps kept in ``tests/data`` (water + IPA calibration). Measured
    when the chapter was reviewed: Gn symmetric to 4e-15, standards recovered
    to 1e-14 with no gaps, eq. 16 residual 3e-13, Ptolemy identity 5e-16,
    ethanol eps' median error 1.9 % (full) and 13 % (simplified) against the
    NPL model. Runnable with pytest or directly.

ES: Las identidades que el informe afirma sobre el metodo de dos liquidos
    (completo) y el de un liquido (simplificado), verificadas con los barridos
    reales de NanoVNA-H y sonda de 3 mm de ``tests/data`` (calibracion agua +
    IPA). Medido al revisar el capitulo: Gn simetrico a 4e-15, patrones
    recuperados a 1e-14 sin gaps, residuo de la ec. 16 de 3e-13, identidad de
    Ptolomeo a 5e-16, error mediano de eps' del etanol de 1,9 % (completo) y
    13 % (simplificado) frente al modelo NPL. Ejecutable con pytest o directo.

The sweeps were recorded on 2026-10-13. The temperature was not logged; 20 C
is the one in the name of the original water file ("agua20C") and is the one
used here for every liquid.
"""

from pathlib import Path

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.pattern_constants import (
    compute_pattern_constants,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.permittivity_solver import (
    solve_epsilon_r,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    evaluate_epsilon_r,
    get_reference_liquid,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.simplified_solver import (
    solve_epsilon_simplified,
)

_DATA = Path(__file__).resolve().parent / "data"
_SET = "nanovna_probe3_2026"
_TEMP_C = 20.0


def _load_fixture(name):
    """(freqs, s11) of a real sweep kept in tests/data (not a user preset)."""
    import skrf as rf

    net = rf.Network(str(_DATA / f"{name}_{_SET}.s1p"))
    return np.asarray(net.f, dtype=float), np.asarray(net.s[:, 0, 0], dtype=complex)


def _standards():
    """Frequency grid and S11 of open (air), short, water and IPA."""
    f, s_open = _load_fixture("open_air")
    sweeps = {"open": s_open}
    for key, name in (("short", "short"), ("water", "water"), ("ipa", "ipa")):
        f_k, s11 = _load_fixture(name)
        assert np.array_equal(f_k, f), name
        sweeps[key] = s11
    return f, sweeps


def _water_ipa_constants(f, s):
    water, ipa = get_reference_liquid("water"), get_reference_liquid("ipa")
    return compute_pattern_constants(f, _TEMP_C, s["short"], s["water"], s["ipa"],
                                     s["open"], water, ipa)


def test_pattern_constants_symmetric_in_reference_order():
    """Swapping the roles of the two liquids flips the sign of every term of
    Gn = -(A + B + C)/(D + E + F), so Gn must not change."""
    f, s = _standards()
    water, ipa = get_reference_liquid("water"), get_reference_liquid("ipa")
    pc_wi = compute_pattern_constants(f, _TEMP_C, s["short"], s["water"], s["ipa"],
                                      s["open"], water, ipa)
    pc_iw = compute_pattern_constants(f, _TEMP_C, s["short"], s["ipa"], s["water"],
                                      s["open"], ipa, water)
    np.testing.assert_allclose(pc_iw.gn, pc_wi.gn, rtol=1e-12)


def test_reference_as_dut_recovers_its_model():
    """Measuring a calibration standard as the unknown must return its own
    model: IPA and water through the full method, and air (eps = 1, the open
    of the full method), seeded and unseeded, with no gaps."""
    f, s = _standards()
    pc = _water_ipa_constants(f, s)
    water = get_reference_liquid("water")
    cases = (
        ("ipa", s["ipa"], evaluate_epsilon_r(get_reference_liquid("ipa"), f, _TEMP_C)[0]),
        ("water", s["water"], evaluate_epsilon_r(water, f, _TEMP_C)[0]),
        ("air", s["open"], np.ones(f.shape, dtype=complex)),
    )
    for label, s_dut, eps_model in cases:
        seed = solve_epsilon_simplified(f, s_dut, s["open"], s["short"], s["water"],
                                        water, _TEMP_C).eps
        for eps_seed in (seed, None):
            res = solve_epsilon_r(s_dut, pc, eps_seed=eps_seed)
            assert res.gap_mask.sum() == 0, (label, res.warnings)
            rel = np.abs(res.eps_selected - eps_model) / np.abs(eps_model)
            assert rel.max() < 1e-10, (label, float(rel.max()))


def test_quintic_residual_of_selected_root():
    """The selected root solves eq. 16, eps + Gn*eps**2.5 + third = 0, with the
    principal power the calibration uses."""
    f, s = _standards()
    pc = _water_ipa_constants(f, s)
    water = get_reference_liquid("water")
    for dut in ("ethanol", "acetone", "cyclohexane"):
        _, s_dut = _load_fixture(dut)
        seed = solve_epsilon_simplified(f, s_dut, s["open"], s["short"], s["water"],
                                        water, _TEMP_C).eps
        res = solve_epsilon_r(s_dut, pc, eps_seed=seed)
        ok = ~res.gap_mask
        eps = res.eps_selected[ok]
        residual = np.abs(eps + res.gn[ok] * np.power(eps, 2.5) + res.third_term[ok])
        assert residual.max() < 1e-9, (dut, float(residual.max()))


def test_simplified_ptolemy_identity():
    """The barycentric coefficients of the simplified method add up to -1
    (Ptolemy identity of the four S11), whatever the unknown is."""
    f, s = _standards()
    water = get_reference_liquid("water")
    for dut in ("ethanol", "acetone", "cyclohexane"):
        _, s_dut = _load_fixture(dut)
        res = solve_epsilon_simplified(f, s_dut, s["open"], s["short"], s["water"],
                                       water, _TEMP_C)
        ok = ~res.gap_mask
        assert ok.all(), dut
        err = np.abs(res.coef_ref[ok] + res.coef_air[ok] + 1.0)
        assert err.max() < 1e-12, (dut, float(err.max()))


def test_ethanol_probe3_full_vs_npl_20c():
    """Ethanol against the NPL Debye-Gamma model at 20 C, 0.1-1.2 GHz: the
    full method within 5 % (median eps', measured 1.9 %), the simplified one
    within 20 % (measured 13 %: it neglects radiation)."""
    f, s = _standards()
    pc = _water_ipa_constants(f, s)
    water = get_reference_liquid("water")
    _, s_eth = _load_fixture("ethanol")
    eps_npl, _ = evaluate_epsilon_r(get_reference_liquid("ethanol"), f, _TEMP_C)
    simplified = solve_epsilon_simplified(f, s_eth, s["open"], s["short"], s["water"],
                                          water, _TEMP_C)
    full = solve_epsilon_r(s_eth, pc, eps_seed=simplified.eps)

    band = (f >= 0.1e9) & (f <= 1.2e9)
    for label, eps, limit in (("full", full.eps_selected, 0.05),
                              ("simplified", simplified.eps, 0.20)):
        err = np.abs(eps.real[band] - eps_npl.real[band]) / eps_npl.real[band]
        assert np.all(np.isfinite(err)), label
        assert np.median(err) < limit, (label, float(np.median(err)))


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
