"""
Tests for the measurement-quality checks and the noise-based spike removal.

EN: Guards the non-blocking diagnostics of ``measurement_quality`` on the
    real NanoVNA-H + 3 mm probe set (101 pts, 50 kHz-1.5 GHz, smoothed) and
    the R60 + 21 mm set: (1) only the points whose values go wrong are
    flagged (3 mm: 50 kHz-30 MHz; 21 mm: below 14 MHz, where water and IPA
    separate unlike the probe model), a smoothed reference separation cannot
    fake information at 50 kHz, and flagged points never set the chart
    scale; (2) the 3 mm Gn
    is flagged as non-radiation (phase -166 deg, flat), the 21 mm one is not;
    (3) standards with |S11| > 1.02 are named; (4) spike removal leaves clean
    and shared outliers alone (the 825 MHz artefact of the 3 mm set), replaces
    isolated ones, never touches the stored sweeps, is optional and recorded
    (measurement, result, kit); (5) a re-measured standard invalidates the
    cached calibration; (6) the report escapes the messages for LaTeX.
    Runnable with pytest or directly.

ES: Protege los diagnosticos no bloqueantes de ``measurement_quality`` con el
    set real NanoVNA-H + sonda de 3 mm (101 pts, 50 kHz-1.5 GHz, suavizado) y
    el set R60 + sonda de 21 mm: (1) solo se marcan los puntos cuyos valores
    se van (3 mm: 50 kHz-30 MHz; 21 mm: debajo de 14 MHz, donde agua e IPA se
    separan distinto del modelo de la sonda), una separacion de referencias
    suavizada no puede fingir informacion a 50 kHz y los puntos marcados
    nunca fijan la escala del grafico; (2) el Gn de 3 mm se marca como no radiativo (fase
    -166 grados, plano) y el de 21 mm no; (3) se nombran los patrones con
    |S11| > 1.02; (4) la remocion de picos deja los barridos limpios y los
    outliers compartidos (el artefacto de 825 MHz del set de 3 mm), reemplaza
    los aislados, nunca toca los barridos guardados, es opcional y queda
    registrada (medicion, resultado, kit); (5) un patron medido de nuevo
    invalida la calibracion en cache; (6) el informe escapa los mensajes para
    LaTeX. Ejecutable con pytest o directo.
"""

import tempfile
from pathlib import Path

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms import measurement_quality as mq
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.probe_models import get_probe
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import calibration_store
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_probe_calibration import (
    PermittivityProbeCalibration,
)

_DATA = Path(__file__).resolve().parent / "data"
_SET3 = "nanovna_probe3_2026"
_SET21 = "r60_probe21_2026"


def _load_fixture(name):
    """(freqs, s11) of a real sweep kept in tests/data (not a user preset)."""
    import skrf as rf

    net = rf.Network(str(_DATA / f"{name}.s1p"))
    return np.asarray(net.f, dtype=float), np.asarray(net.s[:, 0, 0], dtype=complex)


def _calibration(suffix, temp_c, probe_key=None, simplified=False, dut=None):
    """Water (+ IPA) calibration from tests/data, as the wizard builds it."""
    cal = PermittivityProbeCalibration()
    assert cal.set_reference_liquids("water", None if simplified else "ipa")
    cal.set_temperature(temp_c)
    cal.probe_key = probe_key
    keys = [("open", "open_air"), ("short", "short"), ("ref1", "water")]
    if not simplified:
        keys.append(("ref2", "ipa"))
    if dut:
        keys.append(("dut", dut))
    for key, liquid in keys:
        freqs, s11 = _load_fixture(f"{liquid}_{suffix}")
        assert cal.set_measurement(key, freqs, s11, source="imported")
    return cal


def _index(f, f_hz):
    return int(np.argmin(np.abs(np.asarray(f) - f_hz)))


# --------------------------------------------------------------------------- #
# (1) Sensitivity
# --------------------------------------------------------------------------- #

def test_probe_min_usable_frequency_follows_c0():
    """sigma/(2*w*C0*Z0) with sigma = 0.001 and C0 = 19 fF: +-1675 at 50 kHz,
    +-5.6 at 15 MHz, +-0.84 at 100 MHz; +-2 (the usable limit) is reached at
    ~42 MHz for the 3 mm probe and ~7 MHz for the 21 mm one."""
    p3, p21 = get_probe("probe3mm"), get_probe("probe21mm")
    for f, expected in ((50e3, 1675.0), (15e6, 5.6), (100e6, 0.84)):
        eps_err = 1e-3 / (4 * np.pi * f * p3.c0_f * 50.0)
        assert abs(eps_err / expected - 1.0) < 0.01, (f, eps_err)
    assert mq.EPS_RESOLUTION_MAX == 2.0
    assert 40e6 < p3.min_usable_hz(eps_resolution=mq.EPS_RESOLUTION_MAX) < 44e6
    assert 6.5e6 < p21.min_usable_hz(eps_resolution=mq.EPS_RESOLUTION_MAX) < 7.2e6
    assert p3.min_usable_hz(eps_resolution=0.5) == 2 * p3.min_usable_hz()


def test_smoothed_reference_separation_cannot_fake_information():
    """At 50 kHz the smoothed 3 mm set reads |S_water - S_IPA| = 0.0165, above
    the solver's absolute cond_floor (0.01), where the probe allows ~4e-5.
    Capped by the probe model the point resolves eps only to ~+-1675 per
    0.001 (without the cap it would look almost usable, ~+-3.7), and the
    separation is ~365x the probe model's shape (smoothing)."""
    f, s_open = _load_fixture(f"open_air_{_SET3}")
    _, s_water = _load_fixture(f"water_{_SET3}")
    _, s_ipa = _load_fixture(f"ipa_{_SET3}")
    assert 0.015 < abs(s_water[0] - s_ipa[0]) < 0.018

    from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
        evaluate_epsilon_r, get_reference_liquid,
    )
    eps_w, _ = evaluate_epsilon_r(get_reference_liquid("water"), f, 20.0)
    eps_i, _ = evaluate_epsilon_r(get_reference_liquid("ipa"), f, 20.0)
    capped = mq.check_sensitivity(f, s_open, s_water, eps_w, s11_ref2=s_ipa, eps_ref2=eps_i,
                                  c0_f=get_probe("probe3mm").c0_f)
    free = mq.check_sensitivity(f, s_open, s_water, eps_w, s11_ref2=s_ipa, eps_ref2=eps_i)
    assert capped.model_capped and not free.model_capped
    assert 1500 < capped.eps_resolution[0] < 1850
    assert free.eps_resolution[0] < 5
    assert capped.ref_inconsistency[0] > 100 and not capped.consistent[0]
    assert free.ref_inconsistency is None                 # no probe, no model shape
    assert not capped.ref_ok[0]


def test_reference_consistency_flags_only_where_the_shape_breaks():
    """Synthetic references from the capacitive model with the true C0 1.3x
    the stored one (as on the 3 mm NanoVNA set): the ratio is constant, so
    only the resolution limit flags points. Adding 20 % extra separation
    below 20 MHz (smoothing, drift) flags exactly those points."""
    from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
        evaluate_epsilon_r, get_reference_liquid,
    )
    f = np.linspace(1e6, 1e9, 400)
    c0 = get_probe("probe3mm").c0_f
    eps_w, _ = evaluate_epsilon_r(get_reference_liquid("water"), f, 20.0)
    eps_i, _ = evaluate_epsilon_r(get_reference_liquid("ipa"), f, 20.0)
    s_open = mq._model_gamma(np.ones(f.shape, complex), f, 1.3 * c0)
    s_w = mq._model_gamma(eps_w, f, 1.3 * c0)
    s_i = mq._model_gamma(eps_i, f, 1.3 * c0)
    clean = mq.check_sensitivity(f, s_open, s_w, eps_w, s11_ref2=s_i, eps_ref2=eps_i, c0_f=c0)
    assert clean.consistent.all()
    # The model is not exactly linear in the trusted band: ~3 % baseline.
    assert np.nanmax(np.abs(clean.ref_inconsistency)) < 0.04
    np.testing.assert_array_equal(clean.usable, clean.resolution_ok)

    low = f < 20e6
    s_i_bad = s_i.copy()
    s_i_bad[low] = s_w[low] + 1.2 * (s_i[low] - s_w[low])
    bad = mq.check_sensitivity(f, s_open, s_w, eps_w, s11_ref2=s_i_bad, eps_ref2=eps_i, c0_f=c0)
    np.testing.assert_array_equal(~bad.consistent, low)
    np.testing.assert_allclose(bad.ref_inconsistency[low],
                               1.2 * (1.0 + clean.ref_inconsistency[low]) - 1.0, rtol=1e-9)
    assert bad.f_min_hz >= 20e6


def test_unreliable_band_on_real_3mm_set():
    """Full method, water + IPA at 20 C, 3 mm probe: only the points whose
    values go wrong are flagged -- 50 kHz, 15 and 30 MHz (acetone eps''
    3.9/3.5/2.8 instead of ~0.4; cyclohexane eps' 3.2 instead of ~2.1).
    45-75 MHz stay usable (acetone 21.76, as from 90 MHz on). The values are
    kept (non-blocking) and the warning leads the result's warnings."""
    cal = _calibration(_SET3, 20.0, probe_key="probe3mm", dut="acetone")
    res = cal.compute_epsilon()
    q = res.quality
    assert q is not None and q.s11_error == mq.S11_ERROR_FLOOR
    assert abs(q.f_min_hz - 45.0485e6) < 1e3
    np.testing.assert_array_equal(np.flatnonzero(q.low_sensitivity_mask), np.arange(3))
    assert np.isfinite(res.eps_selected[:3]).all()          # flagged, not removed
    assert np.all(np.abs(res.eps_selected[3:6].real - 21.76) < 0.1)
    msg = res.warnings[0]
    assert msg.startswith("Unreliable below 45.05 MHz: 3 point(s)"), msg
    assert "3 mm probe" in msg and "±1675 at 50 kHz" in msg and "+42% at 15.05 MHz" in msg
    assert "left out of the chart scale and of the summary medians" in msg

    _, s_cyc = _load_fixture(f"cyclohexane_{_SET3}")
    cyc = cal.compute_epsilon(res.f_hz, s_cyc)
    assert abs(cyc.quality.f_min_hz - 45.0485e6) < 1e3
    assert "differs from air by less than 1σ" in cyc.warnings[0]


def test_21mm_low_band_limit_and_simplified_method():
    """21 mm probe: water and IPA separate +12 % unlike the probe model at
    13 MHz (+544 % at 1 MHz) and ethanol reads 10-17 % low there, so the
    reliable band starts at 14 MHz. The simplified method gets the check
    too, with ref1 vs air as the reference pair, and no Gn check (no Gn)."""
    cal = _calibration(_SET21, 22.0, probe_key="probe21mm", dut="ethanol")
    res = cal.compute_epsilon()
    assert res.quality.f_min_hz == 14e6
    assert "+12% at 13 MHz unlike the probe model" in res.warnings[0]
    assert res.quality.gn is not None and res.quality.gn.radiation_like
    assert not any("radiation signature" in w for w in res.warnings)

    simp = _calibration(_SET21, 22.0, probe_key="probe21mm", simplified=True, dut="ethanol")
    sres = simp.compute_epsilon()
    assert sres.quality is not None and sres.quality.gn is None
    assert sres.quality.sensitivity.reference_pair == "ref1-air"
    assert 8e6 <= sres.quality.f_min_hz <= 16e6
    assert any("the reference liquid and air resolve" in w for w in sres.warnings)


def test_unreliable_points_never_set_the_chart_scale():
    """A diverging value at the bottom of the sweep (here 500 - 300j) stays
    in the data but the y-limits come from the usable points only; without
    checks every finite point counts."""
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.permittivity_columns import (
        scale_limits, usable_band_of,
    )
    eps = np.full(20, 21.0 - 0.5j)
    eps[0] = 500.0 - 300.0j
    eps[5] = complex(np.nan, np.nan)                       # a gap is ignored too
    usable = np.ones(20, dtype=bool)
    usable[:2] = False
    lo, hi = scale_limits(eps, usable)
    assert -1.0 < lo < 0.5 and 21.0 < hi < 23.0
    assert scale_limits(eps)[1] > 300                      # no mask: every point
    assert scale_limits(eps, np.zeros(20, bool)) is None   # nothing usable

    cal = _calibration(_SET3, 20.0, probe_key="probe3mm", dut="acetone")
    res = cal.compute_epsilon()
    mask, f_min = usable_band_of(res)
    np.testing.assert_array_equal(mask, res.quality.sensitivity.usable)
    assert f_min == res.quality.f_min_hz
    assert usable_band_of(object()) == (None, None)        # older results


# --------------------------------------------------------------------------- #
# (2) Gn
# --------------------------------------------------------------------------- #

def test_gn_of_3mm_set_is_not_radiation():
    """Upper octave of the 3 mm calibration: arg(Gn) ~ -166 deg (radiation:
    -90) and |Gn| flat (radiation: f^3). Its term still weighs ~13 % of the
    water admittance, so the warning says the correction is empirical."""
    cal = _calibration(_SET3, 20.0, probe_key="probe3mm", dut="acetone")
    res = cal.compute_epsilon()
    gn = res.quality.gn
    assert gn is not None and not gn.radiation_like
    assert gn.phase_dev_deg > 60 and gn.slope < 0.5
    assert gn.ref_index == 0 and 0.10 < gn.ref_weight < 0.16       # ref1 = water
    msg = next(w for w in res.warnings if "radiation signature" in w)
    assert "Ref 1 (Distilled Water) admittance" in msg and "simplified cross-check" in msg


def test_gn_check_on_synthetic_radiation_and_noise():
    """Gn = -j*a*f^3 is radiation; a constant |Gn| at -150 deg is not; a sweep
    too short to judge returns None."""
    f = np.linspace(100e6, 1.5e9, 57)
    eps = np.full(f.shape, 80.0 - 5j)
    rng = np.random.default_rng(7)
    radiation = -1j * 2e-4 * (f / 1.5e9) ** 3 * (1 + 0.05 * rng.standard_normal(f.size))
    good = mq.check_gn(f, radiation, [eps])
    assert good.radiation_like and abs(good.slope - 3.0) < 0.3 and good.phase_dev_deg < 5

    noise = np.full(f.shape, 1.5e-4 * np.exp(-1j * np.radians(150.0)))
    bad = mq.check_gn(f, noise, [eps])
    assert not bad.radiation_like and abs(bad.median_arg_deg + 150.0) < 1e-6
    assert mq.gn_warnings(bad, ("Water",)) and not mq.gn_warnings(good)
    assert mq.check_gn(f[:4], radiation[:4], [eps[:4]]) is None


# --------------------------------------------------------------------------- #
# (3) Passivity
# --------------------------------------------------------------------------- #

def test_nonpassive_standards_are_named():
    """3 mm set: Short reaches 1.356 (1395 MHz) and water 1.405 (1485 MHz);
    the import guard (1.5) let both through silently. Open (1.004) and IPA
    (1.0005) are inside the 0.02 tolerance."""
    cal = _calibration(_SET3, 20.0, probe_key="probe3mm", dut="cyclohexane")
    res = cal.compute_epsilon()
    off = res.quality.passivity.offenders
    assert set(off) == {"short", "ref1"}
    assert abs(off["short"]["peak"] - 1.356) < 2e-3 and abs(off["short"]["f_peak_hz"] - 1395e6) < 0.1e6
    assert abs(off["ref1"]["peak"] - 1.405) < 2e-3
    msg = next(w for w in res.warnings if w.startswith("|S11| above 1.02"))
    assert "Short up to 1.356" in msg and "Ref 1 (Distilled Water) up to 1.40" in msg

    f = np.linspace(1e6, 1e9, 11)
    chk = mq.check_passivity(f, {"open": np.full(f.shape, 1.01 + 0j)})
    assert not chk.offenders and not mq.passivity_warnings(chk)


# --------------------------------------------------------------------------- #
# (4) Spike removal
# --------------------------------------------------------------------------- #

def test_despike_leaves_clean_sweeps_alone():
    """The 21 mm R60 sweeps are clean: nothing is replaced (the old
    neighbour-spread rule altered 226 points of OPEN and 237 of SHORT, whose
    static traces make that spread pure noise)."""
    sweeps = {key: _load_fixture(f"{name}_{_SET21}")[1]
              for key, name in (("open", "open_air"), ("short", "short"),
                                ("ref1", "water"), ("ref2", "ipa"))}
    for key, rec in mq.despike_sweeps(sweeps).items():
        assert rec.replaced.size == 0, key
        np.testing.assert_array_equal(rec.s11, sweeps[key])


def test_despike_replaces_an_isolated_spike_and_keeps_shared_ones():
    """A 0.01 spike injected in one 21 mm standard is replaced (only there);
    the same spike injected in all four is an instrument artefact the
    calibration cancels and stays in every one of them."""
    f, _ = _load_fixture(f"water_{_SET21}")
    sweeps = {key: _load_fixture(f"{name}_{_SET21}")[1]
              for key, name in (("open", "open_air"), ("short", "short"),
                                ("ref1", "water"), ("ref2", "ipa"))}
    i = 700
    spike = 0.01 * np.exp(1j * 0.7)
    one = dict(sweeps)
    one["ref1"] = sweeps["ref1"].copy()
    one["ref1"][i] += spike
    recs = mq.despike_sweeps(one)
    np.testing.assert_array_equal(recs["ref1"].replaced, [i])
    assert abs(recs["ref1"].changes[0] - 0.01) < 1e-3
    assert abs(recs["ref1"].s11[i] - sweeps["ref1"][i]) < 1e-3
    assert all(recs[k].replaced.size == 0 for k in ("open", "short", "ref2"))
    assert recs["ref1"].to_metadata(f)["replaced_hz"] == [float(f[i])]

    shared = {key: s.copy() for key, s in sweeps.items()}
    for s in shared.values():
        s[i] += spike
    recs = mq.despike_sweeps(shared)
    for key, rec in recs.items():
        assert rec.replaced.size == 0 and list(rec.kept_common) == [i], key


def test_despike_on_3mm_set_keeps_the_825mhz_artefact():
    """All six 3 mm sweeps are off at 825 MHz (an instrument artefact); Short
    and water trip the spike test there but share it, so both keep it. Water
    at 1410 MHz (|dS11| 0.046, in its |S11| > 1 tail) is the only point
    replaced. Per-sweep removal would have broken the calibration's
    cancellation of the 825 MHz artefact."""
    cal = _calibration(_SET3, 20.0, probe_key="probe3mm", dut="cyclohexane")
    res = cal.compute_epsilon()
    sweeps = res.processing["despike"]["sweeps"]
    assert res.processing["despike"]["enabled"]
    assert sweeps["ref1"]["replaced_hz"] == [1410.003e6]
    assert 0.04 < sweeps["ref1"]["changes"][0] < 0.05
    assert 825.0225e6 in sweeps["ref1"]["kept_common_hz"]
    assert 825.0225e6 in sweeps["short"]["kept_common_hz"]
    replaced = [f for key, p in sweeps.items() if key != "ref1" for f in p["replaced_hz"]]
    assert replaced == []
    assert any(w.startswith("Spike removal (noise-based) replaced 1 isolated point(s)")
               and "Ref 1 (Distilled Water) at 1410 MHz" in w for w in res.warnings)


def test_despike_is_optional_and_never_touches_stored_sweeps():
    """Stored sweeps stay as imported (source still 'imported'); turning spike
    removal off recomputes with them as they are, changes the result only
    near the replaced point, records 'off' and drops the warning."""
    cal = _calibration(_SET3, 20.0, probe_key="probe3mm", dut="cyclohexane")
    on = cal.compute_epsilon()
    f, s_water = _load_fixture(f"water_{_SET3}")
    np.testing.assert_array_equal(cal.get_measurement("ref1")[1], s_water)
    assert cal.get_source("ref1") == "imported"
    assert cal.get_processing("ref1")["despike"]["replaced_hz"] == [1410.003e6]
    eps_on = on.eps_selected.copy()

    cal.set_despike_enabled(False)
    assert cal.pattern_constants is None and cal.epsilon_result is None
    off = cal.compute_epsilon()
    assert cal.get_processing("ref1") == {"despike": None}
    assert off.processing["despike"] == {
        "enabled": False, "criterion": on.processing["despike"]["criterion"], "sweeps": {}}
    assert not any(w.startswith("Spike removal") for w in off.warnings)
    i = _index(f, 1410.003e6)
    changed = np.flatnonzero(~np.isclose(off.eps_selected, eps_on, rtol=1e-12, equal_nan=True))
    assert i in changed and np.all(np.abs(changed - i) <= 2), changed


def test_kit_records_processing_and_keeps_raw_sweeps():
    """A saved kit stores the sweeps as measured plus the despike setting and
    what it did; loading it back gives the raw data."""
    cal = _calibration(_SET3, 20.0, probe_key="probe3mm", dut="cyclohexane")
    cal.compute_epsilon()
    original = calibration_store.get_calibration_dir
    with tempfile.TemporaryDirectory() as tmp:
        calibration_store.get_calibration_dir = lambda: Path(tmp)
        try:
            calibration_store.save_calibration("kit_q", "kit_q", cal, "open_coax_liquids", 20.0)
            data, meta = calibration_store.load_calibration("kit_q")
        finally:
            calibration_store.get_calibration_dir = original
    assert meta.despike_enabled is True
    assert meta.processing["ref1"]["despike"]["replaced_hz"] == [1410.003e6]
    _, s_water = _load_fixture(f"water_{_SET3}")
    np.testing.assert_allclose(data["ref1"][1], s_water, atol=1e-9)


# --------------------------------------------------------------------------- #
# (5) Cache invalidation
# --------------------------------------------------------------------------- #

def test_remeasured_standard_invalidates_the_calibration():
    """Re-measuring ref2 used to leave the old pattern constants in place
    (compute_epsilon only recalibrates when they are None)."""
    cal = _calibration(_SET21, 22.0, dut="ethanol")
    first = cal.compute_epsilon()
    gn_before = cal.pattern_constants.gn.copy()
    f, s_ipa = _load_fixture(f"ipa_{_SET21}")
    assert cal.set_measurement("ref2", f, s_ipa * np.exp(1j * 0.01))
    assert cal.pattern_constants is None and cal.epsilon_result is None
    second = cal.compute_epsilon()
    assert not np.allclose(cal.pattern_constants.gn, gn_before)
    assert not np.allclose(second.eps_selected, first.eps_selected, equal_nan=True)


# --------------------------------------------------------------------------- #
# (6) Report
# --------------------------------------------------------------------------- #

def test_report_escapes_quality_messages_for_latex():
    """Every message of the 3 mm result becomes pdflatex-safe text: no raw
    Greek/math symbols, '%' escaped, balanced math shifts."""
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.export.permittivity_exporter import (
        _despike_summary,
        _plain_to_latex,
    )
    cal = _calibration(_SET3, 20.0, probe_key="probe3mm", dut="acetone")
    res = cal.compute_epsilon()
    lines = res.warnings + _despike_summary(res.processing, cal.sweep_labels())
    assert any("Ref 1 (Distilled Water) at 1410 MHz" in line for line in lines)
    for line in lines:
        tex = _plain_to_latex(line)
        assert not any(ch in tex for ch in "εσ∝≥≤±−′″°…≈Δ∞⚠"), tex
        assert tex.replace(r"\$", "").count("$") % 2 == 0, tex
        assert "%" not in tex.replace(r"\%", ""), tex


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
