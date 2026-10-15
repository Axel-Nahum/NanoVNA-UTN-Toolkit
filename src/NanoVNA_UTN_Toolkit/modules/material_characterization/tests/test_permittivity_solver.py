"""
Root-selection tests for the full (two-liquid, degree-5) permittivity solver.

EN: Guards the branch choice of ``solve_epsilon_r``: (1) a SYNTHETIC
    near-lossless liquid whose noisy S11 pushes the physical root to
    eps'' < 0 must keep that root (flagged as non-passive) instead of jumping
    to a radiation root or a gap; (2) every selected root, and every candidate
    offered to the UI, must solve eq. 16 with the PRINCIPAL power eps**2.5 --
    the one ``pattern_constants`` calibrates with -- never the extraneous
    roots of the x = sqrt(eps) substitution; (3) REGRESSION on real NanoVNA
    sweeps with the 3 mm probe (cyclohexane, acetone; raw, without the UI
    despike); (4) the selection does not depend on having the simplified
    seed, and high-eps liquids pushed through the real 21 mm calibration land
    on the true root; (5) gaps are NaN in both parts, so they never read as
    lossless, and each gap cause is reported on its own; (6) robustness: a
    glitch in a standard or in the sample cannot take the anchor or steer
    the march, so a 2-point glitch in the sample no longer drags the rest of
    the sweep onto another root; an ambiguous step that does steer is
    reported with the stretch of the sweep that depends on it.
    Runnable with pytest or directly.

ES: Protege la eleccion de rama de ``solve_epsilon_r``: (1) un liquido
    SINTETICO casi sin perdidas cuyo S11 con ruido deja la raiz fisica con
    eps'' < 0 tiene que conservar esa raiz (marcada como no pasiva) en vez de
    saltar a una raiz de radiacion o a un gap; (2) toda raiz seleccionada, y
    toda candidata que se le ofrece a la UI, tiene que cumplir la ec. 16 con la
    potencia PRINCIPAL eps**2.5 -- la misma con la que calibra
    ``pattern_constants`` --, nunca las raices extranas de la sustitucion
    x = sqrt(eps); (3) REGRESION con barridos reales de NanoVNA y sonda de
    3 mm (ciclohexano, acetona; crudos, sin el despike de la UI); (4) la
    seleccion no depende de tener la semilla simplificada, y liquidos de eps
    alta propagados con la calibracion real de 21 mm caen en la raiz
    verdadera; (5) los gaps son NaN en ambas partes, para que nunca se lean
    como sin perdidas, y cada causa de gap se informa por separado; (6)
    robustez: un glitch en un patron o en la muestra no puede quedarse con
    el ancla ni guiar la marcha, asi que un glitch de 2 puntos en la muestra
    ya no arrastra el resto del barrido a otra raiz; un paso ambiguo que si
    guia la marcha se informa con el tramo del barrido que depende de el.
    Ejecutable con pytest o directo.
"""

from pathlib import Path

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.pattern_constants import (
    PatternConstants,
    compute_pattern_constants,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.permittivity_solver import (
    _ambiguous_span_text,
    solve_epsilon_r,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.probe_models import (
    get_probe,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    evaluate_epsilon_r,
    get_reference_liquid,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.simplified_solver import (
    solve_epsilon_simplified,
)

_DATA = Path(__file__).resolve().parent / "data"
_Z0_OHM = 50.0
# Relative residual of eq. 16 accepted as "solves it": rounding sits ~1e-15,
# an extraneous root misses by 2*|Gn*eps**2.5| (up to ~1e-1 on the 21 mm set).
_RESIDUAL_TOL = 1e-9


def _load_fixture(name):
    """(freqs, s11) of a real sweep kept in tests/data (not a user preset)."""
    import skrf as rf

    net = rf.Network(str(_DATA / f"{name}.s1p"))
    return np.asarray(net.f, dtype=float), np.asarray(net.s[:, 0, 0], dtype=complex)


def _calibration(suffix, temp_c):
    """Water (ref1) + IPA (ref2) calibration from tests/data, as the wizard builds it."""
    from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_probe_calibration import (
        PermittivityProbeCalibration,
    )

    cal = PermittivityProbeCalibration()
    assert cal.set_reference_liquids("water", "ipa")
    cal.set_temperature(temp_c)
    for key, liquid in (("open", "open_air"), ("short", "short"),
                        ("ref1", "water"), ("ref2", "ipa")):
        freqs, s11 = _load_fixture(f"{liquid}_{suffix}")
        assert cal.set_measurement(key, freqs, s11)
    assert cal.compute_calibration()
    return cal


def _eq16_relative_residual(eps, gn, third):
    """|eps + Gn*eps**2.5 + third| over the largest term, principal power."""
    eps = np.asarray(eps, dtype=complex)
    rad = gn * np.power(eps, 2.5)     # numpy power = principal branch
    scale = np.maximum(np.maximum(np.abs(eps), np.abs(rad)), np.abs(third))
    return np.abs(eps + rad + third) / scale


def _probe_s11(eps, f_hz, gn, c0_f):
    """S11 of the eq.-16 probe model (Y = jwC0*(eps + Gn*eps**2.5)) behind a fixed error box."""
    y = 1j * 2.0 * np.pi * f_hz * c0_f * _Z0_OHM * (eps + gn * np.power(eps, 2.5))
    gamma = (1.0 - y) / (1.0 + y)
    return _error_box(gamma, f_hz)


def _error_box(gamma, f_hz):
    """Arbitrary 1-port error box (directivity, source match, tracking with delay)."""
    e00, e11 = 0.02 + 0.01j, 0.05 - 0.03j
    e10e01 = 0.97 * np.exp(-2j * np.pi * f_hz * 0.15e-9)
    return e00 + e10e01 * gamma / (1.0 - e11 * gamma)


def _physical_root_newton(gn, third, eps_start, n_iter=60):
    """Root of Gn*x^5 + x^2 + third = 0 reached by Newton from sqrt(eps_start), as eps = x^2."""
    x = np.sqrt(np.broadcast_to(np.asarray(eps_start, dtype=complex), np.shape(gn)))
    for _ in range(n_iter):
        x = x - (gn * x**5 + x**2 + third) / (5.0 * gn * x**4 + 2.0 * x)
    assert np.all(np.real(x) > 0)
    return x**2


def _ref2_s11_giving_gn(gn, eps_ref1, eps_ref2, s_open, s_short, s_ref1):
    """S11 of ref2 that makes ``compute_pattern_constants`` return ``gn``.

    Gn = -(A + B + C)/(D + E + F) is a Moebius map of s11_ref2 (see
    pattern_constants), so it inverts in closed form.
    """
    p1, p2 = np.power(eps_ref1, 2.5), np.power(eps_ref2, 2.5)
    a1 = (s_open - s_short) - (s_open - s_ref1) * eps_ref2 - (s_ref1 - s_short) * eps_ref1
    a0 = (-(s_open - s_short) * s_ref1 + (s_open - s_ref1) * s_short * eps_ref2
          + s_open * (s_ref1 - s_short) * eps_ref1)
    b1 = (s_open - s_short) - (s_open - s_ref1) * p2 - (s_ref1 - s_short) * p1
    b0 = (-(s_open - s_short) * s_ref1 + (s_open - s_ref1) * s_short * p2
          + s_open * (s_ref1 - s_short) * p1)
    return -(a0 + gn * b0) / (a1 + gn * b1)


def _s11_through_calibration(eps, pc):
    """S11 that a liquid of permittivity ``eps`` gives under calibration ``pc``.

    Inverse of ``compute_third_term``: third_term is a Moebius map of S11, so
    third*(s - sS)*K = s*P - Q with K = s2 - s1 solves for s in closed form.
    """
    third = -(eps + pc.gn * np.power(eps, 2.5))
    s_sh, s_1, s_2 = pc.s11_short, pc.s11_ref1, pc.s11_ref2
    k = s_2 - s_1
    p = (s_sh - s_2) * pc.y_ref2 + (s_1 - s_sh) * pc.y_ref1
    q = s_1 * (s_sh - s_2) * pc.y_ref2 + s_2 * (s_1 - s_sh) * pc.y_ref1
    return (third * k * s_sh - q) / (third * k - p)


def test_low_loss_liquid_keeps_physical_root_and_flags_noise():
    """Cyclohexane-like eps = 2.02 - j0 with S11 noise: noise leaves the physical
    root with eps'' < 0 at many points. It must still be selected (no NaN, no
    radiation root at |eps| ~ |Gn|**(-2/3)) and be flagged in nonpassive_mask."""
    f = np.linspace(100e6, 1.5e9, 57)
    temp_c = 20.0
    c0_f = get_probe("probe3mm").c0_f
    # Gn = G0/(jwC0) with G0 ~ w**4: grows ~f**3 (|Gn| = 2e-4 at 1.5 GHz).
    gn = -1j * 2e-4 * (f / 1.5e9) ** 3

    water, ipa = get_reference_liquid("water"), get_reference_liquid("ipa")
    eps_water, _ = evaluate_epsilon_r(water, f, temp_c)
    eps_ipa, _ = evaluate_epsilon_r(ipa, f, temp_c)
    s11_short = _error_box(np.full(f.shape, -1.0 + 0j), f)
    s11_open = _probe_s11(np.ones(f.shape, dtype=complex), f, gn, c0_f)
    s11_water = _probe_s11(eps_water, f, gn, c0_f)
    s11_ipa = _probe_s11(eps_ipa, f, gn, c0_f)

    eps_true = 2.02 - 0.0j
    rng = np.random.default_rng(seed=2026)
    noise = 1e-4 * (rng.standard_normal(f.size) + 1j * rng.standard_normal(f.size))
    s11_dut = _probe_s11(np.full(f.shape, eps_true), f, gn, c0_f) + noise

    pc = compute_pattern_constants(f, temp_c, s11_short, s11_water, s11_ipa,
                                   s11_open, water, ipa)
    seed = solve_epsilon_simplified(f, s11_dut, s11_open, s11_short, s11_water,
                                    water, temp_c).eps

    for eps_seed in (seed, None):          # wizard path, then the -third fallback
        res = solve_epsilon_r(s11_dut, pc, eps_seed=eps_seed)
        assert not res.gap_mask.any()
        assert np.max(np.abs(res.eps_selected - eps_true)) < 0.5
        # Oracle independent of the selection: Newton on eq. 16 from the true
        # eps gives the physical root of the NOISY data at each frequency.
        eps_phys = _physical_root_newton(res.gn, res.third_term, eps_true)
        np.testing.assert_allclose(res.eps_selected, eps_phys, rtol=1e-9)
        # Exactly the points the noise pushed to eps'' < 0 are flagged (and kept).
        np.testing.assert_array_equal(res.nonpassive_mask, np.imag(eps_phys) > 1e-6)
        assert np.count_nonzero(res.nonpassive_mask) >= 5
        assert any("non-passive" in w for w in res.warnings)

    # im_tol only moves the flag, never the values (same seeded run, default im_tol).
    strict = solve_epsilon_r(s11_dut, pc, eps_seed=seed)
    loose = solve_epsilon_r(s11_dut, pc, eps_seed=seed, im_tol=1.0)
    assert strict.nonpassive_mask.any() and not loose.nonpassive_mask.any()
    np.testing.assert_array_equal(loose.eps_selected, strict.eps_selected)


def test_selected_roots_solve_eq16_on_principal_branch():
    """Roots with Re(sqrt(eps)) <= 0 solve eps - Gn*eps**2.5 + third = 0, not
    eq. 16 as calibrated: none may be selected (21 mm R60 set, seeded and
    unseeded, plus the 3 mm NanoVNA set)."""
    cases = []
    cal21 = _calibration("r60_probe21_2026", 22.0)
    f, s11 = _load_fixture("ethanol_r60_probe21_2026")
    cases.append(("21mm ethanol seeded", cal21.compute_epsilon(f, s11)))
    cases.append(("21mm ethanol unseeded", solve_epsilon_r(s11, cal21.pattern_constants)))
    cal3 = _calibration("nanovna_probe3_2026", 20.0)
    for dut in ("cyclohexane", "acetone"):
        f, s11 = _load_fixture(f"{dut}_nanovna_probe3_2026")
        cases.append((f"3mm {dut}", cal3.compute_epsilon(f, s11)))

    for label, res in cases:
        ok = np.isfinite(res.eps_selected)
        assert np.count_nonzero(ok) > 0.9 * ok.size, label
        rel = _eq16_relative_residual(res.eps_selected[ok], res.gn[ok], res.third_term[ok])
        n_bad = int(np.count_nonzero(rel > _RESIDUAL_TOL))
        assert n_bad == 0, f"{label}: {n_bad} selected root(s) off the principal branch"


def test_candidates_offered_to_the_ui_are_roots_of_eq16():
    """The result screen lets the user pick any finite candidate by hand, so
    eps_candidates must only hold roots of eq. 16 (extraneous ones are NaN),
    and physical_mask must contain the auto-selection."""
    cal = _calibration("nanovna_probe3_2026", 20.0)
    f, s11 = _load_fixture("cyclohexane_nanovna_probe3_2026")
    res = cal.compute_epsilon(f, s11)

    cand = res.eps_candidates
    finite = np.isfinite(cand)
    rel = _eq16_relative_residual(np.where(finite, cand, 1.0),
                                  res.gn[:, None], res.third_term[:, None])
    assert not np.any(finite & (rel > _RESIDUAL_TOL))
    assert np.all(finite.sum(axis=1)[~res.gap_mask] >= 1)

    rows = np.flatnonzero(res.selected_index >= 0)
    assert np.all(res.physical_mask[rows, res.selected_index[rows]])
    assert not np.any(res.physical_mask & ~finite)


def test_nanovna_probe3_cyclohexane_raw_no_spurious_roots():
    """Regression, real NanoVNA-H + 3 mm probe, water + IPA at 20 C, raw S11.
    Before the fix ~half of the points lost the physical root (eps'' < 0 from
    noise) and got a radiation root (|eps| 250-580) or NaN."""
    cal = _calibration("nanovna_probe3_2026", 20.0)
    f, s11 = _load_fixture("cyclohexane_nanovna_probe3_2026")
    res = cal.compute_epsilon(f, s11)

    band = (f >= 100e6) & (f <= 1.2e9)
    eps = res.eps_selected[band]
    assert np.isfinite(eps).all()
    assert np.max(np.abs(eps)) < 5.0
    assert abs(np.median(np.real(eps)) - 2.0) <= 0.2   # cyclohexane ~2.02 at 20 C
    assert res.nonpassive_mask[band].any()            # noise is flagged, not hidden


def test_nanovna_probe3_cyclohexane_below_vacuum_edge_is_flagged():
    """Same set: at the 1.5 GHz edge eps' drops to 0.99 and 0.73 (1485, 1500 MHz)
    with eps'' > 0, impossible for a liquid. They are kept and flagged (eps' < 1),
    like eps'' < 0, and get their own warning naming the lowest point."""
    cal = _calibration("nanovna_probe3_2026", 20.0)
    f, s11 = _load_fixture("cyclohexane_nanovna_probe3_2026")
    res = cal.compute_epsilon(f, s11)
    eps = res.eps_selected

    edge = np.isin(f, [1485e6, 1500e6])
    assert edge.sum() == 2
    assert np.all((np.real(eps[edge]) > 0.0) & (np.real(eps[edge]) < 1.0))
    assert np.all(np.imag(eps[edge]) < 0.0)           # passive: only eps' flags them
    assert res.nonpassive_mask[edge].all()

    finite = np.isfinite(eps)
    expected = finite & ((np.imag(eps) > 1e-6) | (np.real(eps) < 1.0))
    np.testing.assert_array_equal(res.nonpassive_mask, expected)
    below = [w for w in res.warnings if "ε′ < 1" in w]
    assert len(below) == 1 and below[0].startswith("2 ") and "1500 MHz" in below[0], below


def test_nanovna_probe3_acetone_raw_stays_on_physical_branch():
    """Same set, acetone (eps' ~21, nearly flat below 1.5 GHz). Before the fix
    the 1.26-1.5 GHz tail had gaps and radiation-root spikes (1.29-1.34 GHz)."""
    cal = _calibration("nanovna_probe3_2026", 20.0)
    f, s11 = _load_fixture("acetone_nanovna_probe3_2026")
    res = cal.compute_epsilon(f, s11)

    band = (f >= 100e6) & (f <= 1.2e9)
    eps = res.eps_selected[band]
    assert np.isfinite(eps).all()
    assert np.all((np.real(eps) >= 18.0) & (np.real(eps) <= 23.5))

    upper = f >= 100e6                                  # up to the 1.5 GHz stop
    assert np.isfinite(res.eps_selected[upper]).all()
    assert np.max(np.abs(res.eps_selected[upper])) < 30.0


def test_unseeded_path_matches_seeded_on_21mm_water():
    """Without the simplified seed (a NaN seed point, or _simplified_seed
    failing) the root must not change. Water on the 21 mm probe is the hard
    case: |Gn|*|eps|**1.5 ~ 0.2-6, so -third_term sits far from the physical
    root and nearest-to-(-third) picked other roots from ~690 MHz up."""
    cal = _calibration("r60_probe21_2026", 22.0)
    f, s11 = _load_fixture("water_r60_probe21_2026")
    seeded = cal.compute_epsilon(f, s11)
    unseeded = solve_epsilon_r(s11, cal.pattern_constants)

    assert not seeded.gap_mask.any()
    np.testing.assert_array_equal(unseeded.gap_mask, seeded.gap_mask)
    np.testing.assert_array_equal(unseeded.selected_index, seeded.selected_index)


def test_high_eps_liquids_through_real_21mm_calibration():
    """Synthetic eps pushed through the REAL R60 21 mm calibration (exact eq. 16,
    no noise): every point must land on the true root, seeded and unseeded.
    Nearest-to-seed alone picked radiation roots (40-30j: 0.7-1.24 GHz;
    75-40j: 523 wrong + 158 gaps) and anchoring the march on the largest
    target margin sent 75-40j unseeded onto a wrong branch end to end."""
    cal = _calibration("r60_probe21_2026", 22.0)
    pc = cal.pattern_constants
    for eps_value in (40 - 30j, 75 - 40j):
        eps_true = np.full(pc.f_hz.shape, eps_value)
        s11 = _s11_through_calibration(eps_true, pc)
        for label, res in (("seeded", cal.compute_epsilon(pc.f_hz, s11)),
                           ("unseeded", solve_epsilon_r(s11, pc))):
            assert not res.gap_mask.any(), f"{eps_value} {label}: gaps"
            rel = np.abs(res.eps_selected - eps_true) / abs(eps_value)
            n_bad = int(np.count_nonzero(rel > 1e-6))
            assert n_bad == 0, f"{eps_value} {label}: {n_bad} wrong root(s)"


def test_gap_causes_are_reported_separately():
    """A point without any principal-branch root and a point whose root has
    eps' <= re_min are both gaps, each reported with its own cause (the old
    single message blamed 'the physical one' even when it did not apply)."""
    n = 9
    f = np.linspace(1e8, 1e9, n)
    eps_true = np.full(n, 3.0 - 0.2j)
    eps_true[3] = -0.5 - 0.1j                 # physical root with eps' < 0
    gn = np.full(n, 1e-4 - 1e-4j)
    third = -(eps_true + gn * np.power(eps_true, 2.5))
    gn[6] = np.nan                            # no polynomial -> no candidate
    # Toy standards (short=-1, ref1=0, ref2=1, Y1=0, Y2=1): third = -2s/(s+1).
    pc = PatternConstants(
        f_hz=f, temp_c=25.0, gn=gn,
        y_ref1=np.zeros(n, complex), y_ref2=np.ones(n, complex),
        s11_short=np.full(n, -1 + 0j), s11_ref1=np.zeros(n, complex),
        s11_ref2=np.ones(n, complex), ref1_key="water", ref2_key="ipa", warnings=[],
    )
    res = solve_epsilon_r(-third / (2 + third), pc)

    np.testing.assert_array_equal(np.flatnonzero(res.gap_mask), [3, 6])
    ok = ~res.gap_mask
    np.testing.assert_allclose(res.eps_selected[ok], eps_true[ok], rtol=1e-9)
    assert any(w.startswith("1 ") and "without any principal-branch root" in w
               for w in res.warnings), res.warnings
    assert any(w.startswith("1 ") and "selected root has ε′ <= 0" in w
               for w in res.warnings), res.warnings
    assert not any("physical one" in w for w in res.warnings)


def test_ambiguous_gap_on_real_21mm_ethanol_noise_floor():
    """Real data, 21 mm R60 ethanol at 1-2 MHz (noise floor: the simplified
    seed reads ~2.6-7j there for an eps ~24 liquid). 2 MHz: the root followed
    by continuity has eps' < 0. 1 MHz: neither continuity (margin 1.08) nor
    the seed (margin 1.23) singles out a root and they disagree -> gap, not
    an arbitrary root."""
    cal = _calibration("r60_probe21_2026", 22.0)
    f, s11 = _load_fixture("ethanol_r60_probe21_2026")
    res = cal.compute_epsilon(f, s11)

    np.testing.assert_array_equal(np.flatnonzero(res.gap_mask), [0, 1])
    assert any(w.startswith("1 ") and "neither continuity nor the Gn = 0 estimate" in w
               for w in res.warnings), res.warnings
    assert any(w.startswith("1 ") and "selected root has ε′ <= 0" in w
               for w in res.warnings), res.warnings


def test_dut_glitch_does_not_drag_the_rest_of_the_sweep():
    """A 2-point glitch (|dS11| = 0.3) in the 21 mm water sweep at 1426 MHz
    forces ambiguous steps. Before, the march then followed another root up
    to the end of the sweep (573 points changed); now the glitch points keep
    their roots but do not steer, so nothing outside them changes, and a
    warning names the jump. Clean data raises neither warning."""
    cal = _calibration("r60_probe21_2026", 22.0)
    f, s11 = _load_fixture("water_r60_probe21_2026")
    clean = cal.compute_epsilon(f, s11)
    assert not any("margin < 2" in w or "jumps more than" in w for w in clean.warnings)

    glitch = [1425, 1426]
    s11_glitch = s11.copy()
    s11_glitch[glitch] += 0.3 * np.exp(2j * np.pi / 8)
    res = cal.compute_epsilon(f, s11_glitch)

    same = ((np.isnan(clean.eps_selected) & np.isnan(res.eps_selected))
            | (clean.eps_selected == res.eps_selected))
    same[glitch] = True
    assert same.all(), np.flatnonzero(~same)
    jumps = [w for w in res.warnings if "jumps more than 25%" in w]
    assert len(jumps) == 1 and "first at 1426 MHz" in jumps[0], res.warnings
    margin = [w for w in res.warnings if "margin < 2" in w]
    assert len(margin) == 1 and "None of them steered" in margin[0], res.warnings


def test_ambiguous_span_counts_only_steps_that_steer():
    """The span warning starts at the first ambiguous step that steers the
    march; a held one (a glitch) leaves the rest of the sweep alone, even
    when it comes before a steering one."""
    f = (np.arange(10) + 1) * 1e6
    amb = np.zeros(10, dtype=bool)
    held = np.zeros(10, dtype=bool)
    amb[5] = True
    assert "From f = 6 MHz to the end of the sweep (5 points)" in _ambiguous_span_text(
        amb, held, 2, f)
    held[5] = True
    assert _ambiguous_span_text(amb, held, 2, f).startswith("None of them steered")
    amb[[4, 6]] = True
    held[4] = True                       # held 5 MHz, steering 7 MHz
    assert "From f = 7 MHz to the end of the sweep (4 points)" in _ambiguous_span_text(
        amb, held, 2, f)
    amb[0] = True
    assert "and from f = 1 MHz down to the start of the sweep (1 points)" in (
        _ambiguous_span_text(amb, held, 2, f))
    amb[2] = True
    assert _ambiguous_span_text(amb, held, 2, f).startswith("The whole sweep (10 points)")


def test_anchor_resists_a_glitch_in_a_standard():
    """A 2-point glitch in ref2 that drives |Gn| to 0.3x its minimum used to
    take the anchor (|Gn| minimum) and, for 75-40j on the 21 mm set, flipped
    1997 of 2000 points; with a robust anchor alone the march still followed
    the glitched root and lost the last 98 points. The anchor ranks a running
    median of |Gn| and needs its neighbours' confirmation, and a |Gn| outlier
    does not steer the march, so nothing outside the glitch may change."""
    cal = _calibration("r60_probe21_2026", 22.0)
    pc = cal.pattern_constants
    f = pc.f_hz
    _, s_open = _load_fixture("open_air_r60_probe21_2026")
    _, s_short = _load_fixture("short_r60_probe21_2026")
    _, s_water = _load_fixture("water_r60_probe21_2026")
    _, s_ipa = _load_fixture("ipa_r60_probe21_2026")

    glitch = np.array([1900, 1901])
    gn_glitch = 0.3 * np.min(np.abs(pc.gn)) * pc.gn[glitch] / np.abs(pc.gn[glitch])
    eps_w, _ = evaluate_epsilon_r(get_reference_liquid("water"), f[glitch], 22.0)
    eps_i, _ = evaluate_epsilon_r(get_reference_liquid("ipa"), f[glitch], 22.0)
    s_ipa_glitch = s_ipa.copy()
    s_ipa_glitch[glitch] = _ref2_s11_giving_gn(
        gn_glitch, eps_w, eps_i, s_open[glitch], s_short[glitch], s_water[glitch])

    glitched = _calibration("r60_probe21_2026", 22.0)
    assert glitched.set_measurement("ref2", f, s_ipa_glitch)
    assert glitched.compute_calibration()
    np.testing.assert_allclose(glitched.pattern_constants.gn[glitch], gn_glitch, rtol=1e-6)

    s11 = _s11_through_calibration(np.full(f.shape, 75 - 40j), pc)
    clean_sel = cal.compute_epsilon(f, s11).selected_index
    glitch_sel = glitched.compute_epsilon(f, s11).selected_index
    outside = np.ones(f.size, dtype=bool)
    outside[glitch] = False
    np.testing.assert_array_equal(glitch_sel[outside], clean_sel[outside])


def test_re_max_gap_is_labelled_with_its_cause():
    """re_max does not swap in another root: where the root followed by
    continuity has eps' >= re_max the point is a gap, reported as such (not
    as a noise-dominated eps' <= 0 point)."""
    n = 12
    f = np.linspace(1e8, 1e9, n)
    eps_true = np.linspace(30, 10, n) - 2j
    gn = np.full(n, 1e-3 + 0j)
    third = -(eps_true + gn * np.power(eps_true, 2.5))
    pc = PatternConstants(
        f_hz=f, temp_c=25.0, gn=gn,
        y_ref1=np.zeros(n, complex), y_ref2=np.ones(n, complex),
        s11_short=np.full(n, -1 + 0j), s11_ref1=np.zeros(n, complex),
        s11_ref2=np.ones(n, complex), ref1_key="water", ref2_key="ipa", warnings=[],
    )
    res = solve_epsilon_r(-third / (2 + third), pc, re_max=20.0)

    above = eps_true.real >= 20.0
    np.testing.assert_array_equal(res.gap_mask, above)
    np.testing.assert_allclose(res.eps_selected[~above], eps_true[~above], rtol=1e-9)
    assert any(w.startswith(f"{int(above.sum())} ") and "ε′ >= re_max = 20" in w
               for w in res.warnings), res.warnings
    assert not any("ε′ <= 0" in w for w in res.warnings)


def test_gaps_are_nan_in_both_parts():
    """A gap stored as nan+0j reads as eps'' = 0 (lossless) downstream; both
    solvers must store complex(nan, nan)."""
    n = 6
    f = np.linspace(1e8, 1e9, n)
    s_ref2 = np.ones(n, complex)
    s_ref2[2] = 0.0                       # ref2 == ref1 there -> ill-conditioned
    pc = PatternConstants(
        f_hz=f, temp_c=25.0, gn=np.full(n, 1e-4 - 1e-4j),
        y_ref1=np.zeros(n, complex), y_ref2=np.ones(n, complex),
        s11_short=np.full(n, -1 + 0j), s11_ref1=np.zeros(n, complex),
        s11_ref2=s_ref2, ref1_key="water", ref2_key="ipa", warnings=[],
    )
    res = solve_epsilon_r(np.full(n, 0.3 + 0.1j), pc)
    assert res.gap_mask[2]
    assert np.isnan(res.eps_selected[2].real) and np.isnan(res.eps_selected[2].imag)

    water = get_reference_liquid("water")
    s_open, s_short, s_ref = (np.full(n, v, complex) for v in (0.9, -1.0, 0.2))
    simp = solve_epsilon_simplified(f, s_short.copy(), s_open, s_short, s_ref, water, 25.0)
    assert simp.gap_mask.all()
    assert np.isnan(simp.eps.real).all() and np.isnan(simp.eps.imag).all()


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
