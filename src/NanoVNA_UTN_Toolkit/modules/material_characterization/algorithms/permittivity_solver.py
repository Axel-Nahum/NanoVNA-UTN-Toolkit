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
) -> EpsilonResult:
    """
    Solve for epsilon_r over the whole frequency grid and track a branch.

    EN: Builds the degree-5 polynomial per frequency, computes all roots,
        filters the physically admissible ones (Re>re_min, Im<=im_tol) and
        tracks a continuous branch across frequency using a short-window
        polynomial prediction (nearest-neighbour matching). Exposes every
        candidate so the UI can override the auto selection.

    ES: Arma el polinomio de grado 5 por frecuencia, calcula todas las raices,
        filtra las fisicamente admisibles (Re>re_min, Im<=im_tol) y sigue una
        rama continua en frecuencia mediante prediccion polinomica de ventana
        corta (vecino mas cercano). Expone todas las candidatas para que la UI
        pueda sobre-escribir la seleccion automatica.
    """
    s11_m = np.asarray(s11_m, dtype=complex)
    n = s11_m.shape[0]
    warnings: List[str] = []

    third = compute_third_term(s11_m, pc)

    eps_candidates = np.empty((n, _N_ROOTS), dtype=complex)
    for i in range(n):
        eps_candidates[i, :] = _roots_at_frequency(pc.gn[i], third[i])

    physical_mask = _physical_mask(eps_candidates, re_min, im_tol, re_max)

    eps_selected = np.full(n, np.nan + 0j, dtype=complex)
    selected_index = np.full(n, -1, dtype=int)
    gap_mask = np.zeros(n, dtype=bool)

    last_freqs: List[float] = []
    last_eps: List[complex] = []

    for i in range(n):
        admissible = np.where(physical_mask[i])[0]
        if admissible.size == 0:
            gap_mask[i] = True
            continue

        cands = eps_candidates[i, admissible]

        if not last_eps:
            # Seed: smallest loss (closest to lossless / passive limit).
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

    if np.any(gap_mask):
        n_gap = int(np.count_nonzero(gap_mask))
        msg = (
            f"No physically admissible root at {n_gap} frequency point(s); "
            f"those are left as gaps (NaN) in the selected branch."
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
    )
