"""
Fifth-order permittivity solver with cross-frequency root tracking.

EN: Given the calibration constants (Gn, reference admittances) and the
    measured S11 of an unknown liquid, solves, per frequency, the 5th-order
    equation that relates the corrected reflection coefficient to the complex
    permittivity epsilon_r. Returns all candidate roots plus an auto-selected,
    physically plausible and frequency-continuous branch.

ES: Dadas las constantes de calibracion (Gn, admitancias de referencia) y el
    S11 medido de un liquido incognita, resuelve, por frecuencia, la ecuacion
    de quinto orden que relaciona el coeficiente de reflexion corregido con la
    permitividad compleja epsilon_r. Devuelve todas las raices candidatas mas
    una rama auto-seleccionada, fisicamente plausible y continua en frecuencia.

Algorithm source / Fuente del algoritmo:
    "Mediciones de permitividad mediante una sonda coaxial", UTN-FRBA 2024,
    eqs. 15-16, and the MATLAB reference
        medicion_fluidos/App_ME2/src/measurements/get_epsilon_r.m

Equation / Ecuacion (eq. 16):
    epsilon_m + Gn * epsilon_m^(5/2) + third_term = 0
    Substituting x = epsilon_m^(1/2) gives the degree-5 polynomial in x:
        Gn * x^5 + x^2 + third_term = 0
    whose 5 roots map back via epsilon_m = x^2. There is no closed criterion
    for the correct root (it must be physically chosen), so this module
    auto-tracks a continuous physical branch and exposes every candidate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.pattern_constants import (
    PatternConstants,
)

logger = logging.getLogger(__name__)

_DENOM_FLOOR = 1e-12
_N_ROOTS = 5


@dataclass
class EpsilonResult:
    """
    Result of the permittivity extraction over a frequency grid.

    Attributes
    ----------
    f_hz : np.ndarray
        Frequency grid in Hz (n_freq,).
    eps_candidates : np.ndarray
        Complex (n_freq, 5) matrix of ALL candidate roots per frequency
        (NaN-padded when the polynomial degree drops).
    physical_mask : np.ndarray
        Bool (n_freq, 5) marking physically admissible candidates.
    eps_selected : np.ndarray
        Complex (n_freq,) auto-tracked branch.
    selected_index : np.ndarray
        Int (n_freq,) index into ``eps_candidates`` of the selected branch
        (-1 where no admissible candidate was found).
    gap_mask : np.ndarray
        Bool (n_freq,) marking frequencies with no admissible candidate.
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
    """

    f_hz: np.ndarray
    eps_candidates: np.ndarray
    physical_mask: np.ndarray
    eps_selected: np.ndarray
    selected_index: np.ndarray
    gap_mask: np.ndarray
    gn: np.ndarray
    third_term: np.ndarray
    warnings: List[str]
    eps_crosscheck: np.ndarray | None = None

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
        third[bad] = np.nan

    return third


def _roots_at_frequency(gn: complex, third_term: complex) -> np.ndarray:
    """
    Solve ``Gn*x^5 + x^2 + third_term = 0`` and return 5 epsilon candidates.

    Returns a length-5 complex array (NaN-padded if the degree drops because
    ``Gn`` is ~0). ``epsilon = x^2``.
    """
    if not (np.isfinite(gn) and np.isfinite(third_term)):
        return np.full(_N_ROOTS, np.nan + 0j, dtype=complex)

    # numpy.roots: coefficients highest degree first -> x^5 x^4 x^3 x^2 x^1 x^0
    coeffs = np.array([gn, 0.0, 0.0, 1.0, 0.0, third_term], dtype=complex)
    x_roots = np.roots(coeffs)
    eps = np.square(x_roots)

    out = np.full(_N_ROOTS, np.nan + 0j, dtype=complex)
    out[: len(eps)] = eps[:_N_ROOTS]
    return out


def _physical_mask(
    eps_candidates: np.ndarray,
    re_min: float,
    im_tol: float,
    re_max: float | None,
) -> np.ndarray:
    """Mark candidates with Re(eps) > re_min, Im(eps) <= im_tol (and optional re_max)."""
    re = np.real(eps_candidates)
    im = np.imag(eps_candidates)

    mask = np.isfinite(eps_candidates) & (re > re_min) & (im <= im_tol)
    if re_max is not None:
        mask &= re < re_max
    return mask


def solve_epsilon_r(
    s11_m: np.ndarray,
    pc: PatternConstants,
    *,
    re_min: float = 0.0,
    im_tol: float = 1e-6,
    re_max: float | None = None,
    track_window: int = 5,
    track_order: int = 2,
    cond_floor: float = 1e-2,
    eps_seed: np.ndarray | None = None,
) -> EpsilonResult:
    """
    Solve for epsilon_r over the whole frequency grid and track a branch.

    EN: Builds the degree-5 polynomial per frequency, computes all roots,
        filters the physically admissible ones (Re>re_min, Im<=im_tol) and
        tracks a continuous branch across frequency using a short-window
        polynomial prediction (nearest-neighbour matching). Exposes every
        candidate so the UI can override the auto selection.

        Traversal runs from the HIGHEST frequency down to the lowest. At high
        frequencies Gn is small, the inversion is well-conditioned and the seed
        is reliable. At very low frequencies the two reference liquids become
        nearly indistinguishable (|S11_ref1 - S11_ref2| < cond_floor); those
        points are marked as gaps instead of returning a spurious root.

        When ``eps_seed`` is given (the SIMPLIFIED single-reference curve, the
        Gn=0 limit of this same equation), it replaces the per-frequency
        prediction wherever it is finite: the quintic root closest to the seed
        is chosen. This is the strategy of the Sonda_2026_py reference
        (``get_er_DUT_completo``), where the simplified solution seeds the
        quintic. Without a seed the behaviour is unchanged.

    ES: Arma el polinomio de grado 5 por frecuencia, calcula todas las raices,
        filtra las fisicamente admisibles (Re>re_min, Im<=im_tol) y sigue una
        rama continua en frecuencia mediante prediccion polinomica de ventana
        corta (vecino mas cercano). Expone todas las candidatas para que la UI
        pueda sobre-escribir la seleccion automatica.

        El recorrido va de la frecuencia MAS ALTA hacia abajo. A alta frecuencia
        Gn es chico, la inversion esta bien condicionada y la semilla es
        confiable. A muy baja frecuencia los dos liquidos de referencia son casi
        indistinguibles (|S11_ref1 - S11_ref2| < cond_floor); esos puntos se
        marcan como gap en vez de devolver una raiz espuria.

        Si se pasa ``eps_seed`` (la curva SIMPLIFICADA de una referencia, el
        limite Gn=0 de esta misma ecuacion), reemplaza la prediccion por
        frecuencia donde sea finita: se elige la raiz del quintico mas cercana
        a la semilla. Es la estrategia de la referencia Sonda_2026_py
        (``get_er_DUT_completo``), donde la solucion simplificada siembra el
        quintico. Sin semilla el comportamiento no cambia.

    Parameters
    ----------
    cond_floor : float
        Threshold for |S11_ref1 - S11_ref2| below which a frequency point is
        considered ill-conditioned and excluded from the branch (default 1e-2).
    eps_seed : np.ndarray | None
        Optional per-frequency prediction (same grid). Stored in the result as
        ``eps_crosscheck`` for the UI overlay; a large low-band divergence
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

    physical_mask = _physical_mask(eps_candidates, re_min, im_tol, re_max)

    # Ill-conditioned points: reference liquids nearly indistinguishable.
    ref_sep = np.abs(np.asarray(pc.s11_ref2, dtype=complex) - np.asarray(pc.s11_ref1, dtype=complex))
    ill_conditioned = ref_sep < cond_floor

    eps_selected = np.full(n, np.nan + 0j, dtype=complex)
    selected_index = np.full(n, -1, dtype=int)
    gap_mask = np.zeros(n, dtype=bool)

    last_freqs: List[float] = []
    last_eps: List[complex] = []

    # Traverse HIGH → LOW frequency. At high frequencies Gn = G0/(jωC0) is
    # small and the system is well-conditioned; the seed placed there is
    # reliable and the tracker follows a physically correct branch downward.
    for i in range(n - 1, -1, -1):
        if ill_conditioned[i]:
            gap_mask[i] = True
            continue

        admissible = np.where(physical_mask[i])[0]
        if admissible.size == 0:
            gap_mask[i] = True
            continue

        cands = eps_candidates[i, admissible]

        seed_here = (
            eps_seed[i]
            if eps_seed is not None and np.isfinite(eps_seed[i])
            else None
        )

        if seed_here is not None:
            # The simplified (Gn=0) solution IS the physical branch of this
            # equation up to the radiation correction: pick the root nearest it.
            choice = int(np.argmin(np.abs(cands - seed_here)))
        elif not last_eps:
            # Seed at the highest valid frequency: smallest imaginary part
            # (closest to lossless / passive limit).
            choice = int(np.argmin(np.abs(np.imag(cands))))
        else:
            # Predict next epsilon by short-window polynomial extrapolation.
            k = min(track_window, len(last_eps))
            fw = np.asarray(last_freqs[-k:], dtype=float)
            ew = np.asarray(last_eps[-k:], dtype=complex)
            if k == 1:
                pred = ew[-1]
            else:
                deg = min(track_order, k - 1)
                # Fit real and imaginary parts independently vs frequency.
                pr = np.polyfit(fw, np.real(ew), deg)
                pi = np.polyfit(fw, np.imag(ew), deg)
                pred = np.polyval(pr, pc.f_hz[i]) + 1j * np.polyval(pi, pc.f_hz[i])
            choice = int(np.argmin(np.abs(cands - pred)))

        idx = int(admissible[choice])
        selected_index[i] = idx
        eps_selected[i] = eps_candidates[i, idx]
        last_freqs.append(float(pc.f_hz[i]))
        last_eps.append(eps_selected[i])

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

    n_gap_only = int(np.count_nonzero(gap_mask & ~ill_conditioned))
    if n_gap_only > 0:
        msg = (
            f"No physically admissible root at {n_gap_only} frequency point(s); "
            f"those are left as gaps (NaN) in the selected branch."
        )
        warnings.append(msg)
        logger.warning("[permittivity_solver] %s", msg)

    # Warn about large jumps in ε′ (>50 % between consecutive valid points).
    valid_idx = np.where(~np.isnan(eps_selected))[0]
    if len(valid_idx) > 1:
        consecutive_pairs = np.where(np.diff(valid_idx) == 1)[0]
        jump_count = 0
        for j in consecutive_pairs:
            a, b = valid_idx[j], valid_idx[j + 1]
            denom = max(abs(np.real(eps_selected[a])), 1e-6)
            if abs(np.real(eps_selected[b]) - np.real(eps_selected[a])) / denom > 0.5:
                jump_count += 1
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
        gn=np.asarray(pc.gn, dtype=complex),
        third_term=np.asarray(third, dtype=complex),
        warnings=warnings,
        eps_crosscheck=eps_seed,
    )
