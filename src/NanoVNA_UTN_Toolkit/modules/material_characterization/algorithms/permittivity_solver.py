"""
Fifth-order permittivity solver with continuity tracking of the physical root.

EN: Given the calibration constants (Gn, reference admittances) and the
    measured S11 of an unknown liquid, solves, per frequency, the 5th-order
    equation that relates the corrected reflection coefficient to the complex
    permittivity epsilon_r. Returns every root of that equation plus the
    auto-selected physical branch, followed by continuity across frequency.

ES: Dadas las constantes de calibracion (Gn, admitancias de referencia) y el
    S11 medido de un liquido incognita, resuelve, por frecuencia, la ecuacion
    de quinto orden que relaciona el coeficiente de reflexion corregido con la
    permitividad compleja epsilon_r. Devuelve todas las raices de esa ecuacion
    mas la rama fisica auto-seleccionada, seguida por continuidad en
    frecuencia.

Algorithm source / Fuente del algoritmo:
    "Mediciones de permitividad mediante una sonda coaxial", UTN-FRBA 2024,
    eqs. 15-16, and the MATLAB reference
        medicion_fluidos/App_ME2/src/measurements/get_epsilon_r.m

Equation / Ecuacion (eq. 16):
    epsilon_m + Gn * epsilon_m^(5/2) + third_term = 0
    with epsilon^(5/2) on the PRINCIPAL branch: the one ``pattern_constants``
    calibrates Gn with (``np.power``) and the one MATLAB ``vpasolve`` solves.
    Substituting x = epsilon_m^(1/2) gives the degree-5 polynomial in x:
        Gn * x^5 + x^2 + third_term = 0
    whose roots map back via epsilon_m = x^2.

Branches / Ramas:
    EN: x and -x give the same epsilon, so only roots with Re(x) > 0 solve
        eq. 16; a root with Re(x) < 0 solves epsilon - Gn*epsilon^(5/2) +
        third_term = 0 instead (radiation term with the wrong sign) and is
        extraneous. What remains is the physical root, |Gn*epsilon^(5/2)|
        away from the Gn -> 0 limit epsilon = -third_term, and one or two
        radiation roots at |epsilon| ~ |Gn|^(-2/3), far away while
        |Gn|*|epsilon|^(3/2) << 1. In the probe model Gn = G0/(j*w*C0) with
        G0 ~ w^4 and C0 constant, so |Gn| grows ~w^3: the radiation roots
        approach the physical one at HIGH frequency. With measured standards
        Gn also absorbs calibration residuals, so its low-band value reflects
        noise rather than radiation.
    ES: x y -x dan el mismo epsilon, asi que solo las raices con Re(x) > 0
        resuelven la ec. 16; una raiz con Re(x) < 0 resuelve en cambio
        epsilon - Gn*epsilon^(5/2) + third_term = 0 (termino de radiacion con
        el signo cambiado) y es extrana. Queda la raiz fisica, a
        |Gn*epsilon^(5/2)| del limite Gn -> 0 epsilon = -third_term, y una o
        dos raices de radiacion con |epsilon| ~ |Gn|^(-2/3), lejanas mientras
        |Gn|*|epsilon|^(3/2) << 1. En el modelo de la sonda Gn = G0/(j*w*C0)
        con G0 ~ w^4 y C0 constante, asi que |Gn| crece ~w^3: las raices de
        radiacion se acercan a la fisica a ALTA frecuencia. Con patrones
        medidos Gn ademas absorbe residuos de calibracion, por lo que su valor
        en la banda baja refleja ruido y no radiacion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.pattern_constants import (
    PatternConstants,
)

logger = logging.getLogger(__name__)

_DENOM_FLOOR = 1e-12
_N_ROOTS = 5
# Gap / padding value: NaN in BOTH parts. ``nan+0j`` would read as eps'' = 0
# (a lossless point) to anything that takes -Im(eps).
_NAN_C = complex(np.nan, np.nan)
# A choice is ambiguous when the second-nearest candidate is less than twice
# as far from the reference as the chosen one (margin = d2/d1 < 2).
_AMBIGUITY_MARGIN = 2.0
# Neighbours on each side that must confirm an anchor, and half-width of the
# running median of |Gn| that ranks anchors: a 1-2 point glitch in a standard
# can neither fake a |Gn| minimum nor start the march on its own.
_ANCHOR_NEIGHBOURS = 2
# |Gn| more than this factor away from that running median marks a calibration
# glitch (same 3x rule as the |Gn| quality chart): the root found there keeps
# its value but does not steer the march. Real 2026 sets stay within 1.8x.
_GN_OUTLIER_FACTOR = 3.0
# Same idea for the sample: a Gn = 0 estimate more than this fraction away from
# its running median marks a likely glitch in the DUT sweep; such a point does
# not steer the march when its own continuity step is unclear too. Without it
# a 2-point glitch could drag the rest of the sweep onto another root (573 of
# 2000 points on 21 mm water; none with it). Tuned on the glitch stress set;
# clean real sweeps, coarse grids included, are unchanged.
_TARGET_OUTLIER_FRACTION = 0.25
# No liquid has eps' below vacuum (Debye: eps' >= eps_inf >= 1). A selected
# root under it is a measurement error (e.g. the band edge) and is flagged in
# ``nonpassive_mask``; same threshold as ``simplified_solver``.
_EPS_REAL_MIN_PHYSICAL = 1.0
# Gap causes per frequency (0 = a root was selected).
_GAP_ILL = 1          # reference liquids nearly indistinguishable
_GAP_NO_ROOT = 2      # no principal-branch root at all
_GAP_RE_MIN = 3       # the root followed by continuity has Re(eps) <= re_min
_GAP_AMBIGUOUS = 4    # neither continuity nor the Gn = 0 estimate decides
_GAP_RE_MAX = 5       # the root followed by continuity has Re(eps) >= re_max


@dataclass
class EpsilonResult:
    """
    Result of the permittivity extraction over a frequency grid.

    Attributes
    ----------
    f_hz : np.ndarray
        Frequency grid in Hz (n_freq,).
    eps_candidates : np.ndarray
        Complex (n_freq, 5) roots of eq. 16 per frequency, one slot per root x
        of the degree-5 polynomial (``np.roots`` order). Slots of extraneous
        roots (Re(x) <= 0, see the module docstring) and of a dropped degree
        are NaN, so every finite entry -- the result screen offers them as
        manual branches -- solves eq. 16 as calibrated.
    physical_mask : np.ndarray
        Bool (n_freq, 5) marking the candidates the auto-selection may return:
        finite, Re(eps) > re_min and, if given, Re(eps) < re_max. Passivity
        (Im(eps) <= im_tol) is deliberately NOT required: noise leaves the
        physical root of a near-lossless liquid with eps'' < 0 (see
        ``nonpassive_mask``). True at ``[i, selected_index[i]]``.
    eps_selected : np.ndarray
        Complex (n_freq,) auto-selected root; complex(nan, nan) at gaps.
    selected_index : np.ndarray
        Int (n_freq,) index into ``eps_candidates`` of the selected root
        (-1 at gaps).
    gap_mask : np.ndarray
        Bool (n_freq,) marking frequencies without a selected root (causes in
        ``solve_epsilon_r``; each one is counted in its own warning).
    nonpassive_mask : np.ndarray
        Bool (n_freq,); True where the selected root is non-physical:
        Im(eps) > im_tol (eps'' < 0, non-passive) or Re(eps) < 1 (eps' below
        vacuum). Quality flag only -- the value is kept. A root with
        Re(eps) <= re_min is never selected here (the point is a gap), so only
        re_min < eps' < 1 reaches the flag. ``SimplifiedEpsilonResult`` flags
        the same two conditions on the values it returns.
    gn : np.ndarray
        Complex (n_freq,) normalized conductance used per frequency (the x^5
        coefficient of the degree-5 polynomial).
    third_term : np.ndarray
        Complex (n_freq,) constant term of the degree-5 polynomial.
    warnings : list[str]
        Non-fatal issues collected during the computation.
    eps_crosscheck : np.ndarray | None
        Complex (n_freq,) curve of the SIMPLIFIED (single-reference,
        closed-form) method when it was supplied as ``eps_seed``. Kept for the
        cross-check overlay in the result screen: a large divergence between
        the two methods at low frequency flags a problem with the second
        reference liquid (the only standard that enters solely through Gn).
    quality : measurement_quality.QualityReport | None
        Measurement-quality checks (low-frequency sensitivity, Gn physicality,
        |S11| > 1). Attached by the calibration manager, which has the probe
        and the Open sweep the solver does not see; its warnings are also in
        ``warnings``. None when the solver is called directly.
    processing : dict | None
        Record of what was done to the sweeps before solving (spike removal:
        enabled flag and, per sweep key, the frequencies replaced). Attached by
        the calibration manager; None when the solver is called directly.
    """

    f_hz: np.ndarray
    eps_candidates: np.ndarray
    physical_mask: np.ndarray
    eps_selected: np.ndarray
    selected_index: np.ndarray
    gap_mask: np.ndarray
    nonpassive_mask: np.ndarray
    gn: np.ndarray
    third_term: np.ndarray
    warnings: List[str]
    eps_crosscheck: np.ndarray | None = None
    quality: Any = None
    processing: Dict[str, Any] | None = None

    def polynomial_coeffs_at(self, index: int) -> np.ndarray:
        """Return the degree-5 polynomial coefficients [Gn,0,0,1,0,third] at a frequency."""
        return np.array([self.gn[index], 0.0, 0.0, 1.0, 0.0, self.third_term[index]], dtype=complex)


def compute_third_term(s11_m: np.ndarray, pc: PatternConstants) -> np.ndarray:
    """
    Port of the ``third_term`` computation from ``get_epsilon_r.m``.

    ``third_term = A * Y_ref2 + B * Y_ref1`` (MATLAB ``A*Y_wtr + B*Y_ipa``).
    """
    s11_m = np.asarray(s11_m, dtype=complex)

    d_m1 = s11_m - pc.s11_short
    d_m2 = s11_m - pc.s11_ref1   # MATLAB d_m2 = s11_m - s11_ipa
    d_m3 = s11_m - pc.s11_ref2   # MATLAB d_m3 = s11_m - s11_wtr

    with np.errstate(divide="ignore", invalid="ignore"):
        denom = d_m1 * (pc.s11_ref2 - pc.s11_ref1)
        A = d_m2 * (pc.s11_short - pc.s11_ref2) / denom
        B = d_m3 * (pc.s11_ref1 - pc.s11_short) / denom
        third = A * pc.y_ref2 + B * pc.y_ref1

    bad = np.abs(denom) < _DENOM_FLOOR
    if np.any(bad):
        third[bad] = _NAN_C

    return third


def _roots_at_frequency(gn: complex, third_term: complex) -> np.ndarray:
    """
    Roots of eq. 16 at one frequency, as 5 slots of epsilon candidates.

    Solves ``Gn*x^5 + x^2 + third_term = 0`` and maps back ``epsilon = x^2``
    only the roots with Re(x) > 0 (principal branch); the slots of the
    extraneous roots, and of a degree drop when ``Gn`` is ~0, are NaN.
    """
    out = np.full(_N_ROOTS, _NAN_C, dtype=complex)
    if not (np.isfinite(gn) and np.isfinite(third_term)):
        return out

    # numpy.roots: coefficients highest degree first -> x^5 x^4 x^3 x^2 x^1 x^0
    coeffs = np.array([gn, 0.0, 0.0, 1.0, 0.0, third_term], dtype=complex)
    x_roots = np.roots(coeffs)[:_N_ROOTS]
    out[: x_roots.size] = np.where(np.real(x_roots) > 0.0, np.square(x_roots), _NAN_C)
    return out


def _physical_mask(
    eps_candidates: np.ndarray,
    re_min: float,
    re_max: float | None,
) -> np.ndarray:
    """Mark finite candidates with Re(eps) > re_min (and Re(eps) < re_max if given)."""
    re = np.real(eps_candidates)
    with np.errstate(invalid="ignore"):
        mask = np.isfinite(eps_candidates) & (re > re_min)
        if re_max is not None:
            mask &= re < re_max
    return mask


def _nearest_with_margin(
    cands: np.ndarray,
    ref: np.ndarray,
    usable: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Candidate nearest to ``ref`` per row, and how unambiguous it is.

    ``cands`` is (n, 5) and ``ref`` is (n,); ``usable`` optionally restricts
    the candidates (default: every finite one). The margin is the distance
    to the 2nd-nearest candidate over the distance to the nearest one: inf
    with a single candidate or an exact hit, 1 for two coincident candidates.
    Rows without candidates, or with a non-finite ``ref``, have no choice:
    index -1 and margin NaN (callers must check before indexing with it).
    """
    finite = np.isfinite(cands) if usable is None else (np.isfinite(cands) & usable)
    valid = finite.any(axis=1) & np.isfinite(ref)
    with np.errstate(invalid="ignore"):
        dist = np.where(finite & valid[:, None], np.abs(cands - ref[:, None]), np.inf)
    order = np.argsort(dist, axis=1)
    d1 = np.take_along_axis(dist, order[:, :1], axis=1)[:, 0]
    d2 = np.take_along_axis(dist, order[:, 1:2], axis=1)[:, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        margin = np.where(d1 > 0.0, d2 / d1, np.where(d2 > 0.0, np.inf, 1.0))
    return np.where(valid, order[:, 0], -1), np.where(valid, margin, np.nan)


def _running_median(values: np.ndarray, half_width: int) -> np.ndarray:
    """Median over +-``half_width`` points (edges padded); non-finite counts as +inf."""
    values = np.where(np.isfinite(values), values, np.inf)
    if values.size == 0 or half_width <= 0:
        return values
    padded = np.pad(values, half_width, mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * half_width + 1)
    return np.median(windows, axis=1)


def _choose_anchor(
    cands: np.ndarray,
    gn_abs: np.ndarray,
    choice_target: np.ndarray,
    margin_target: np.ndarray,
    eligible: np.ndarray,
) -> int | None:
    """
    Frequency index where the march starts, or None if no point is eligible.

    Clear points (eligible, target margin >= 2) are tried by increasing
    running-median |Gn|. The first one whose neighbours within
    +-_ANCHOR_NEIGHBOURS are clear too and, by continuity from its root, pick
    the same roots as their own estimate is the anchor: a glitched point
    fails that test. If no point is clear, the one with the largest target
    margin; if no clear point is confirmed, the best-ranked clear one.
    """
    if not np.any(eligible):
        return None
    clear = eligible & (margin_target >= _AMBIGUITY_MARGIN)
    if not np.any(clear):
        return int(np.argmax(np.where(eligible, margin_target, -np.inf)))

    n = cands.shape[0]
    score = np.where(clear, _running_median(gn_abs, _ANCHOR_NEIGHBOURS), np.inf)
    ranked = np.argsort(score, kind="stable")[: int(np.count_nonzero(clear))]
    for a in ranked:
        neighbours = np.r_[max(0, a - _ANCHOR_NEIGHBOURS):a,
                           a + 1:min(n, a + _ANCHOR_NEIGHBOURS + 1)]
        if not np.all(clear[neighbours]):
            continue
        root = np.full(neighbours.size, cands[a, choice_target[a]])
        picks, _ = _nearest_with_margin(cands[neighbours], root)
        if np.array_equal(picks, choice_target[neighbours]):
            return int(a)
    return int(ranked[0])


def _march_from_anchor(
    cands: np.ndarray,
    anchor: int,
    ill_conditioned: np.ndarray,
    choice_target: np.ndarray,
    margin_target: np.ndarray,
    re_min: float,
    re_max: float | None,
    steers: np.ndarray,
    steers_if_clear: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Follow the root chosen at ``anchor`` toward both ends of the grid.

    Each point takes the finite candidate nearest to the reference: the LAST
    VALID selected root that was not held. Gaps do not move the reference,
    nor do HELD points, which keep their root while the next point still
    compares against the previous reference: points with ``steers == False``
    (a glitch in a standard), and points with ``steers_if_clear == False``
    (the sample's estimate jumps there) whose own continuity step is unclear
    -- the step a glitch uses to switch branches. A root with Re(eps) <=
    re_min or >= re_max makes the point a gap, never another root. Returns
    ``(selected_index, gap_cause, ambiguous, held)``. ``ambiguous`` marks
    points kept although the continuity margin is < 2: the Gn = 0 estimate
    either picked the same root, or was itself unambiguous -- in that case
    the continuity root is kept even if the estimate points elsewhere. Only
    when both margins are < 2 and they disagree is the point a gap.
    """
    n = cands.shape[0]
    selected_index = np.full(n, -1, dtype=int)
    gap_cause = np.zeros(n, dtype=np.int8)
    ambiguous = np.zeros(n, dtype=bool)
    held = np.zeros(n, dtype=bool)

    selected_index[anchor] = choice_target[anchor]
    ambiguous[anchor] = margin_target[anchor] < _AMBIGUITY_MARGIN
    for indices in (range(anchor + 1, n), range(anchor - 1, -1, -1)):
        reference = cands[anchor, choice_target[anchor]]
        for i in indices:
            if ill_conditioned[i]:
                gap_cause[i] = _GAP_ILL
                continue
            j, margin = _nearest_with_margin(cands[i:i + 1], np.array([reference]))
            j, margin = int(j[0]), float(margin[0])
            if j < 0:
                gap_cause[i] = _GAP_NO_ROOT
                continue
            unclear = margin < _AMBIGUITY_MARGIN
            if unclear and j != choice_target[i] and not margin_target[i] >= _AMBIGUITY_MARGIN:
                gap_cause[i] = _GAP_AMBIGUOUS
                continue
            re_root = np.real(cands[i, j])
            if re_root <= re_min:
                gap_cause[i] = _GAP_RE_MIN
                continue
            if re_max is not None and re_root >= re_max:
                gap_cause[i] = _GAP_RE_MAX
                continue
            selected_index[i] = j
            ambiguous[i] = unclear
            if steers[i] and (steers_if_clear[i] or not unclear):
                reference = cands[i, j]
            else:
                held[i] = True
    return selected_index, gap_cause, ambiguous, held


def _fmt_mhz(f_hz: float) -> str:
    return f"{f_hz / 1e6:.6g} MHz"


def _ambiguous_span_text(
    ambiguous: np.ndarray, held: np.ndarray, anchor: int, f_hz: np.ndarray,
) -> str:
    """
    Which part of the sweep hangs on an ambiguous step of the march.

    Everything past the first ambiguous step seen from the anchor (in each
    direction) follows the root chosen there, so a wrong pick propagates to
    the end of the sweep: say from where, and how many points. A held step
    (a glitch, see ``_march_from_anchor``) does not move the reference, so it
    opens no span.
    """
    n = f_hz.size
    if ambiguous[anchor]:
        return (f"The whole sweep ({n} points) follows a root chosen at an "
                f"ambiguous anchor; compare with the simplified cross-check.")
    steering = ambiguous & ~held
    spans = []
    up = np.flatnonzero(steering[anchor + 1:])
    if up.size:
        i = anchor + 1 + int(up[0])
        spans.append(f"from f = {_fmt_mhz(f_hz[i])} to the end of the sweep ({n - i} points)")
    down = np.flatnonzero(steering[:anchor])
    if not spans and not down.size:
        return ("None of them steered the branch (each was held as a glitch, "
                "see above), so no other point depends on them.")
    if down.size:
        i = int(down[-1])
        spans.append(f"from f = {_fmt_mhz(f_hz[i])} down to the start of the sweep "
                     f"({i + 1} points)")
    text = " and ".join(spans)
    return (text[:1].upper() + text[1:] + " the branch follows a root chosen at "
            "an ambiguous step; compare with the simplified cross-check.")


def solve_epsilon_r(
    s11_m: np.ndarray,
    pc: PatternConstants,
    *,
    re_min: float = 0.0,
    im_tol: float = 1e-6,
    re_max: float | None = None,
    cond_floor: float = 1e-2,
    eps_seed: np.ndarray | None = None,
) -> EpsilonResult:
    """
    Solve for epsilon_r over the whole frequency grid along one continuous branch.

    EN: Builds the degree-5 polynomial per frequency and keeps its roots that
        solve eq. 16: principal branch, Re(sqrt(eps)) > 0 (see the module
        docstring). Then follows one continuous branch:

        1. Gn = 0 estimate per frequency: ``eps_seed`` (the SIMPLIFIED
           single-reference curve, as in Sonda_2026_py
           ``get_er_DUT_completo``) where finite, else ``-third_term`` (the
           Gn -> 0 limit of this same equation and calibration).
        2. Anchor: among the well-conditioned, non-glitched (see 3) points
           whose root nearest to that estimate is unambiguous (margin >= 2:
           the 2nd-nearest root at least twice as far) and lies in
           (re_min, re_max), the one with the smallest |Gn| -- taken as a
           running median over +-2 points -- whose +-2 neighbours are
           unambiguous too and, by continuity from its root, pick the same
           roots as their own estimate. The estimate misses the physical
           root by about |Gn*eps^(5/2)| and the radiation roots close in as
           |Gn| grows, so that is where it is most reliable; the median and
           the neighbour check keep a 1-2 point glitch in a standard or in
           the sample from taking the anchor. With measured standards |Gn|
           also rises at the lowest frequencies, so the anchor lands in the
           low band just above them (60-75 MHz on the 2026 sets). If no
           point is unambiguous, the one with the largest margin; if none is
           confirmed by its neighbours, the best-ranked.
        3. From the anchor the march goes up and down in frequency: each
           point takes the root nearest to the last valid selected root. A
           point whose |Gn| is more than 3x away from its running median (a
           glitch in a standard, the same 3x rule as the |Gn| quality chart)
           keeps its root but does not become the reference for the next
           point; it is counted in a warning. So does a point whose Gn = 0
           estimate is more than 25 % away from its running median (a glitch
           in the sample sweep) AND whose continuity step is unclear: that
           is the step a 2-point glitch used to hand the rest of the sweep
           to another root. With a clear step it still steers, since on a
           coarse grid the estimate also jumps where the real curve bends.

        Gaps (complex(nan, nan)), each cause counted in its own warning:
        ill-conditioned points, where the two reference liquids are nearly
        indistinguishable (|S11_ref1 - S11_ref2| < cond_floor); points without
        a principal-branch root; points whose selected root has
        Re(eps) <= re_min (noise-dominated, no physical solution there) or
        Re(eps) >= re_max; and points where neither continuity nor the
        estimate singles out a root (both margins < 2 and they disagree). The
        march resumes from the last valid point. Points kept with a continuity
        margin < 2 are counted in a warning that also gives the stretch of
        the sweep hanging on the first of them that steered the march: from
        there to the end of the sweep in the direction of the march (possible
        branch switch). Held points open no stretch.

        Passivity is a QUALITY flag, not a selection filter. Noise leaves the
        physical root of a near-lossless liquid (cyclohexane, acetone) with
        eps'' < 0 at many points; discarding it handed those points to a
        radiation root (|eps| in the hundreds) or to a gap. Such points are
        kept, marked in ``nonpassive_mask`` and counted in a warning. So are
        points kept with 0 < eps' < 1, below vacuum and impossible for a
        liquid (seen at the 1.5 GHz edge of a NanoVNA sweep), in their own
        warning: they are flagged, not turned into gaps, so the selection is
        the same with or without the flag.

    ES: Arma el polinomio de grado 5 por frecuencia y conserva sus raices que
        resuelven la ec. 16: rama principal, Re(sqrt(eps)) > 0 (ver el
        docstring del modulo). Despues sigue una sola rama continua:

        1. Estimacion con Gn = 0 por frecuencia: ``eps_seed`` (la curva
           SIMPLIFICADA de una referencia, como en Sonda_2026_py
           ``get_er_DUT_completo``) donde sea finita, y si no ``-third_term``
           (el limite Gn -> 0 de esta misma ecuacion y calibracion).
        2. Ancla: entre los puntos bien condicionados y sin glitch (ver 3)
           cuya raiz mas cercana a esa estimacion no es ambigua (margen >= 2:
           la 2.a raiz mas cercana esta al menos al doble de distancia) y cae
           en (re_min, re_max), el de menor |Gn| -- tomado como mediana movil
           de +-2 puntos -- cuyos vecinos +-2 tampoco son ambiguos y, por
           continuidad desde su raiz, eligen las mismas raices que su propia
           estimacion. La estimacion se aparta de la raiz fisica en
           |Gn*eps^(5/2)| aproximadamente y las raices de radiacion se acercan
           cuando |Gn| crece, asi que ahi es donde mas se puede confiar en
           ella; la mediana y el control de vecinos evitan que un glitch de
           1-2 puntos en un patron o en la muestra se quede con el ancla. Con
           patrones medidos |Gn| tambien sube en las frecuencias mas bajas,
           por lo que el ancla cae en la banda baja justo por encima de ellas
           (60-75 MHz en los sets 2026). Si ningun punto es inequivoco, el de
           mayor margen; si ninguno queda confirmado por sus vecinos, el mejor
           ubicado.
        3. Desde el ancla se marcha hacia arriba y hacia abajo en frecuencia:
           cada punto toma la raiz mas cercana a la ultima raiz valida
           seleccionada. Un punto cuyo |Gn| se aleja mas de 3x de su mediana
           movil (un glitch en un patron, la misma regla de 3x del grafico de
           calidad de |Gn|) conserva su raiz pero no pasa a ser la referencia
           del punto siguiente; se cuenta en un warning. Lo mismo un punto
           cuya estimacion con Gn = 0 se aleja mas de 25 % de su mediana movil
           (un glitch en el barrido de la muestra) Y cuyo paso de continuidad
           no es claro: ese es el paso con el que un glitch de 2 puntos
           dejaba el resto del barrido en otra raiz. Con un paso claro sigue
           guiando, porque en una grilla gruesa la estimacion tambien salta
           donde la curva real cambia de pendiente.

        Gaps (complex(nan, nan)), cada causa contada en su propio warning:
        puntos mal condicionados, donde los dos liquidos de referencia son
        casi indistinguibles (|S11_ref1 - S11_ref2| < cond_floor); puntos sin
        raiz de rama principal; puntos cuya raiz seleccionada tiene
        Re(eps) <= re_min (dominados por ruido, sin solucion fisica ahi) o
        Re(eps) >= re_max; y puntos donde ni la continuidad ni la estimacion
        distinguen una raiz (ambos margenes < 2 y no coinciden). La marcha se
        retoma desde el ultimo punto valido. Los puntos que se conservan con
        margen de continuidad < 2 se cuentan en un warning que ademas indica
        el tramo del barrido que depende del primero de ellos que guio la
        marcha: desde ahi hasta el extremo del barrido en el sentido de la
        marcha (posible cambio de rama). Los puntos retenidos no abren tramo.

        La pasividad es una marca de CALIDAD, no un filtro de seleccion. El
        ruido deja la raiz fisica de un liquido casi sin perdidas
        (ciclohexano, acetona) con eps'' < 0 en muchos puntos; descartarla
        dejaba esos puntos en una raiz de radiacion (|eps| de cientos) o en un
        gap. Esos puntos se conservan, se marcan en ``nonpassive_mask`` y se
        cuentan en un warning. Lo mismo los puntos que quedan con
        0 < eps' < 1, por debajo del vacio e imposibles en un liquido (se ven
        en el borde de 1.5 GHz de un barrido del NanoVNA), con su propio
        warning: se marcan, no pasan a ser gaps, asi que la seleccion es la
        misma con o sin la marca.

    Parameters
    ----------
    re_min : float
        A point whose selected root has Re(eps) <= re_min becomes a gap
        (default 0). It does not pre-filter the candidates: that would hand
        the point to a radiation root.
    im_tol : float
        Passivity tolerance: a selected root with Im(eps) > im_tol is flagged
        in ``nonpassive_mask`` (default 1e-6, as in ``simplified_solver``).
    re_max : float | None
        Optional upper bound (default None): a point whose selected root has
        Re(eps) >= re_max becomes a gap. Like ``re_min`` it does not
        pre-filter the candidates, so it never swaps in another root.
    cond_floor : float
        Threshold for |S11_ref1 - S11_ref2| below which a frequency point is
        considered ill-conditioned and left as a gap (default 1e-2). It is
        absolute and blind to smoothing: the 3 mm NanoVNA set reads 0.0165 at
        50 kHz, where the probe allows 4e-5. The per-probe sensitivity check
        of ``measurement_quality`` (run by the calibration manager) is what
        flags such points.
    eps_seed : np.ndarray | None
        Optional Gn = 0 estimate on the same grid (the simplified curve);
        non-finite entries fall back to ``-third_term``. Stored in the result
        as ``eps_crosscheck`` for the UI overlay; a large low-band divergence
        between seed and selection raises a ref2-quality warning.
    """
    s11_m = np.asarray(s11_m, dtype=complex)
    n = s11_m.shape[0]
    warnings: List[str] = []

    if eps_seed is not None:
        eps_seed = np.asarray(eps_seed, dtype=complex)
        if eps_seed.shape != s11_m.shape:
            raise ValueError(
                f"eps_seed shape {eps_seed.shape} != measurement shape {s11_m.shape}"
            )

    third = compute_third_term(s11_m, pc)

    eps_candidates = np.empty((n, _N_ROOTS), dtype=complex)
    for i in range(n):
        eps_candidates[i, :] = _roots_at_frequency(pc.gn[i], third[i])

    physical_mask = _physical_mask(eps_candidates, re_min, re_max)

    # Ill-conditioned points: reference liquids nearly indistinguishable.
    ref_sep = np.abs(np.asarray(pc.s11_ref2, dtype=complex) - np.asarray(pc.s11_ref1, dtype=complex))
    ill_conditioned = ref_sep < cond_floor

    # Gn = 0 estimate of the physical root: the simplified curve where it is
    # finite, else the Gn -> 0 limit of eq. 16 with this calibration.
    target = -third
    if eps_seed is not None:
        target = np.where(np.isfinite(eps_seed), eps_seed, target)

    # Candidates outside (re_min, re_max) are not filtered out of the search:
    # dropping the physical root there would hand the point to another root.
    # A root followed by continuity outside the window makes the point a gap.
    choice_target, margin_target = _nearest_with_margin(eps_candidates, target)

    # A glitch in a standard shows up as |Gn| far from its neighbours.
    gn_abs = np.abs(np.asarray(pc.gn, dtype=complex))
    gn_median = _running_median(gn_abs, _ANCHOR_NEIGHBOURS)
    with np.errstate(divide="ignore", invalid="ignore"):
        gn_ratio = gn_abs / gn_median
        gn_outlier = np.isfinite(gn_median) & (
            (gn_ratio > _GN_OUTLIER_FACTOR) | (gn_ratio < 1.0 / _GN_OUTLIER_FACTOR))

    # A glitch in the DUT sweep shows up as the estimate jumping away from its
    # neighbours (|Gn| only sees the standards). On a coarse grid the estimate
    # also jumps where the real curve bends, so such a point is only held when
    # its own continuity step is unclear too (see _march_from_anchor).
    with np.errstate(invalid="ignore"):
        target_median = (_running_median(np.real(target), _ANCHOR_NEIGHBOURS)
                         + 1j * _running_median(np.imag(target), _ANCHOR_NEIGHBOURS))
        target_outlier = (np.abs(target - target_median)
                          > _TARGET_OUTLIER_FRACTION * np.abs(target_median))

    rows = np.arange(n)
    has_choice = choice_target >= 0
    eligible = (has_choice & ~ill_conditioned & ~gn_outlier
                & physical_mask[rows, np.maximum(choice_target, 0)])
    anchor = _choose_anchor(eps_candidates, gn_abs, choice_target, margin_target, eligible)
    if anchor is not None:
        selected_index, gap_cause, ambiguous, held = _march_from_anchor(
            eps_candidates, anchor, ill_conditioned,
            choice_target, margin_target, re_min, re_max,
            steers=~gn_outlier, steers_if_clear=~target_outlier,
        )
    else:
        selected_index = np.full(n, -1, dtype=int)
        ambiguous = np.zeros(n, dtype=bool)
        held = np.zeros(n, dtype=bool)
        with np.errstate(invalid="ignore"):
            re_target = np.real(eps_candidates[rows, np.maximum(choice_target, 0)])
        out_high = (has_choice & (re_target >= re_max) if re_max is not None
                    else np.zeros(n, dtype=bool))
        gap_cause = np.select(
            [ill_conditioned, ~has_choice, out_high], [_GAP_ILL, _GAP_NO_ROOT, _GAP_RE_MAX],
            default=_GAP_RE_MIN,
        ).astype(np.int8)

    selected = selected_index >= 0
    eps_selected = np.where(selected, eps_candidates[rows, np.maximum(selected_index, 0)], _NAN_C)
    gap_mask = ~selected

    with np.errstate(invalid="ignore"):
        gain_mask = selected & (np.imag(eps_selected) > im_tol)
        below_vacuum_mask = selected & (np.real(eps_selected) < _EPS_REAL_MIN_PHYSICAL)
    nonpassive_mask = gain_mask | below_vacuum_mask

    # --- Warnings ----------------------------------------------------------- #

    n_ill = int(np.count_nonzero(ill_conditioned))
    if n_ill > 0:
        msg = (
            f"{n_ill} frequency point(s) excluded: reference liquids nearly "
            f"indistinguishable (|S11_ref1−S11_ref2| < {cond_floor:.0e}). "
            f"Consider starting the sweep above the affected range."
        )
        warnings.append(msg)
        logger.warning("[permittivity_solver] %s", msg)

    gap_texts = [
        (_GAP_NO_ROOT, "without any principal-branch root of the 5th-order equation"),
        (_GAP_RE_MIN, f"whose selected root has ε′ <= {re_min:g} (noise-dominated, "
                      f"no physical solution there)"),
        (_GAP_AMBIGUOUS, "where neither continuity nor the Gn = 0 estimate singles "
                         "out a root (both margins < 2)"),
    ]
    if re_max is not None:
        gap_texts.append((_GAP_RE_MAX, f"whose selected root has ε′ >= re_max = {re_max:g}"))
    for cause, text in gap_texts:
        n_cause = int(np.count_nonzero(gap_cause == cause))
        if n_cause > 0:
            msg = f"{n_cause} frequency point(s) {text}; left as gaps (NaN)."
            warnings.append(msg)
            logger.warning("[permittivity_solver] %s", msg)

    n_outlier = int(np.count_nonzero(gn_outlier & ~gap_mask))
    if n_outlier > 0:
        first = int(np.flatnonzero(gn_outlier & ~gap_mask)[0])
        msg = (
            f"{n_outlier} frequency point(s) with |Gn| more than "
            f"{_GN_OUTLIER_FACTOR:g}x away from its neighbours (first at "
            f"{_fmt_mhz(pc.f_hz[first])}): likely a glitch in a standard. Their "
            f"values are kept but did not steer the branch; check them."
        )
        warnings.append(msg)
        logger.warning("[permittivity_solver] %s", msg)

    sample_jump = held & ~gn_outlier
    n_jump = int(np.count_nonzero(sample_jump))
    if n_jump > 0:
        first = int(np.flatnonzero(sample_jump)[0])
        msg = (
            f"{n_jump} frequency point(s) where the sample's Gn = 0 estimate jumps "
            f"more than {_TARGET_OUTLIER_FRACTION:.0%} away from its neighbours and "
            f"continuity is ambiguous (first at {_fmt_mhz(pc.f_hz[first])}): likely "
            f"a glitch in the sample sweep. Their values are kept but did not "
            f"steer the branch; check them."
        )
        warnings.append(msg)
        logger.warning("[permittivity_solver] %s", msg)

    n_ambiguous = int(np.count_nonzero(ambiguous))
    if n_ambiguous > 0:
        msg = (
            f"{n_ambiguous} frequency point(s) selected with a margin < 2 over the "
            f"second-nearest root (possible branch switch). "
            + _ambiguous_span_text(ambiguous, held, anchor,
                                   np.asarray(pc.f_hz, dtype=float))
        )
        warnings.append(msg)
        logger.warning("[permittivity_solver] %s", msg)

    n_gain = int(np.count_nonzero(gain_mask))
    if n_gain > 0:
        worst = float(np.max(np.imag(eps_selected[gain_mask])))
        msg = (
            f"{n_gain} frequency point(s) with ε″ < 0 (non-passive, worst "
            f"ε″ = {-worst:.3f}), attributable to measurement noise on a "
            f"near-lossless liquid. Values kept and flagged, not replaced by "
            f"another root."
        )
        warnings.append(msg)
        logger.warning("[permittivity_solver] %s", msg)

    n_below_vacuum = int(np.count_nonzero(below_vacuum_mask))
    if n_below_vacuum > 0:
        lowest = int(np.flatnonzero(below_vacuum_mask)[
            np.argmin(np.real(eps_selected[below_vacuum_mask]))])
        msg = (
            f"{n_below_vacuum} frequency point(s) with ε′ < 1, below vacuum and "
            f"impossible for a liquid (lowest ε′ = {np.real(eps_selected[lowest]):.3f} "
            f"at {_fmt_mhz(pc.f_hz[lowest])}): a measurement error, typically at "
            f"the edge of the sweep. Values kept and flagged."
        )
        warnings.append(msg)
        logger.warning("[permittivity_solver] %s", msg)

    # Warn about large jumps in ε′ (>50 % between consecutive valid points).
    re_all = np.real(eps_selected)
    both_valid = selected[:-1] & selected[1:]
    with np.errstate(divide="ignore", invalid="ignore"):
        rel_jump = np.abs(np.diff(re_all)) / np.maximum(np.abs(re_all[:-1]), 1e-6)
    jump_count = int(np.count_nonzero(both_valid & (rel_jump > 0.5)))
    if jump_count > 0:
        msg = (
            f"Large jump (>50 %) in ε′ at {jump_count} consecutive point pair(s) — "
            f"possible branch instability."
        )
        warnings.append(msg)
        logger.warning("[permittivity_solver] %s", msg)

    # Cross-check: the simplified curve must agree with the selection in the
    # LOWER half of the band, where radiation is negligible and both methods
    # solve the same physics. A large divergence there points at ref2 -- the
    # only standard that enters solely through Gn, so an error in it hides
    # from every other consistency check.
    if eps_seed is not None:
        low_band = np.arange(n) < n // 2
        both = low_band & np.isfinite(eps_selected) & np.isfinite(eps_seed)
        if np.count_nonzero(both) >= 5:
            re_sel = np.real(eps_selected[both])
            re_seed = np.real(eps_seed[both])
            with np.errstate(divide="ignore", invalid="ignore"):
                rel = np.abs(re_sel - re_seed) / np.maximum(np.abs(re_seed), 1e-6)
            med = float(np.median(rel))
            if med > 0.25:
                msg = (
                    f"Full-method result diverges {med:.0%} (median) from the "
                    f"simplified cross-check in the lower half-band, where both "
                    f"should agree. Check the second reference liquid (ref2): it "
                    f"only enters through Gn, so an error there is invisible to "
                    f"the other standards."
                )
                warnings.append(msg)
                logger.warning("[permittivity_solver] %s", msg)

    warnings.extend(pc.warnings)

    return EpsilonResult(
        f_hz=np.asarray(pc.f_hz, dtype=float),
        eps_candidates=eps_candidates,
        physical_mask=physical_mask,
        eps_selected=eps_selected,
        selected_index=selected_index,
        gap_mask=gap_mask,
        nonpassive_mask=nonpassive_mask,
        gn=np.asarray(pc.gn, dtype=complex),
        third_term=np.asarray(third, dtype=complex),
        warnings=warnings,
        eps_crosscheck=eps_seed,
    )
