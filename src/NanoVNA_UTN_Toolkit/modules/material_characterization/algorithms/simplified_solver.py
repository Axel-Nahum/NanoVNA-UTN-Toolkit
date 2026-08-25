"""
Simplified (single-reference-liquid) permittivity solver.

EN: Computes the complex relative permittivity of an unknown liquid from FOUR
    S11 sweeps -- Short, Open (air) and ONE known reference liquid, plus the
    unknown -- via a closed-form barycentric formula. No quintic, no root
    tracking, no branch ambiguity.

ES: Calcula la permitividad relativa compleja de un liquido incognita a partir
    de CUATRO barridos de S11 -- Short, Open (aire) y UN liquido de referencia
    conocido, mas la incognita -- mediante una formula baricentrica cerrada.
    Sin quintico, sin tracking de raices, sin ambiguedad de ramas.

Why it works / Por que funciona:
    Neglecting the radiation term (Gn = 0), the probe admittance is LINEAR in
    epsilon (Y = j*w*C0*eps), so the measured reflection coefficient is a
    Moebius (bilinear) transform of epsilon -- and any 1-port error box
    composed with it is still Moebius. The cross-ratio of four points is
    invariant under Moebius maps, and with the Short at eps -> infinity the
    identity collapses to a barycentric interpolation:

        eps_m = -coef_ref * eps_ref(f,T) - coef_air * eps_air

    where coef_ref + coef_air = -1 identically (Ptolemy identity) and both
    coefficients come only from the four measured S11. C0, G0, Z0 and the
    probe geometry cancel out; no prior VNA SOL calibration is required (the
    three standards absorb the whole 1-port error box).

    The price: neglecting radiation makes the model degrade where G0*eps^2.5
    matters -- higher frequency, larger probe. The full 2-liquid method (see
    ``permittivity_solver``) corrects that via Gn at the cost of solving a
    degree-5 polynomial per frequency.

Algorithm source / Fuente del algoritmo:
    Eq. (18) of Higa/Cismondi/Grass (2016); "Desarrollo de un sistema de
    medicion de la permitividad compleja en alimentos para frecuencias de
    microondas mediante parametros S", A. Henze et al., IEEE ARGENCON 2024.
    Reference implementation: ``funciones.get_er_DUTm`` in
    https://github.com/pguzmanUTN/Sonda_2026_py (generalized here: the
    reference liquid is a parameter instead of being hard-wired to water; the
    tautological "water self-check" of that repo is intentionally NOT ported).

Sign convention: eps = eps' - j*eps'' with eps'' > 0 for a passive liquid,
same as ``reference_liquids`` (see its module docstring).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    ReferenceLiquid,
    evaluate_epsilon_r,
)

logger = logging.getLogger(__name__)

# Relative permittivity of air at 20 C, 1013.2 mb, 50 % RH (Medley, NPL 1991).
# Kept explicit instead of assuming exactly 1: it is one of the two anchors of
# the barycentric interpolation.
EPS_AIR = 1.0006

_DENOM_FLOOR = 1e-12
# Passivity tolerance for the QUALITY mask (not a selection filter: the closed
# formula has no branches to choose from). Small positive Im(eps) can appear
# from measurement noise on nearly lossless points.
_IM_TOL = 1e-6


@dataclass
class SimplifiedEpsilonResult:
    """
    Result of the single-reference (simplified) permittivity extraction.

    Attributes
    ----------
    f_hz : np.ndarray
        Frequency grid in Hz (n_freq,).
    eps : np.ndarray
        Complex (n_freq,) permittivity of the unknown liquid. NaN where the
        formula is numerically degenerate (see ``gap_mask``).
    eps_ref : np.ndarray
        Complex (n_freq,) model permittivity used for the reference liquid.
    coef_ref, coef_air : np.ndarray
        Complex (n_freq,) barycentric coefficients (diagnostic; they satisfy
        ``coef_ref + coef_air = -1`` wherever the data is consistent).
    gap_mask : np.ndarray
        Bool (n_freq,); True where a denominator collapsed and eps is NaN.
    nonpassive_mask : np.ndarray
        Bool (n_freq,); True where the result violates passivity
        (Re(eps) <= 0 or Im(eps) > tolerance). Quality flag only -- the values
        are still returned.
    ref_liquid_key : str
        Key of the reference liquid used.
    temperature_c : float
        Temperature the reference model was evaluated at.
    warnings : list[str]
        Non-fatal issues collected during the computation.
    """

    f_hz: np.ndarray
    eps: np.ndarray
    eps_ref: np.ndarray
    coef_ref: np.ndarray
    coef_air: np.ndarray
    gap_mask: np.ndarray
    nonpassive_mask: np.ndarray
    ref_liquid_key: str
    temperature_c: float
    warnings: List[str]

    @property
    def eps_selected(self) -> np.ndarray:
        """Alias so downstream consumers of ``EpsilonResult`` (results window,
        PDF exporters, epsilon chart) work unchanged. Here nothing is
        "selected" -- the closed formula yields a single curve."""
        return self.eps


def solve_epsilon_simplified(
    f_hz: np.ndarray,
    s11_dut: np.ndarray,
    s11_open: np.ndarray,
    s11_short: np.ndarray,
    s11_ref: np.ndarray,
    ref_liquid: ReferenceLiquid,
    temp_c: float,
    *,
    eps_air: complex = EPS_AIR,
    denom_floor: float = _DENOM_FLOOR,
    im_tol: float = _IM_TOL,
) -> SimplifiedEpsilonResult:
    """
    Closed-form permittivity from Short + Open(air) + one reference liquid.

    EN: All S11 arrays must share the frequency grid ``f_hz`` (the caller
        validates that; this function only checks shapes). ``s11_open`` is the
        probe in air -- it acts as the eps = 1.0006 standard, NOT as an ideal
        Gamma = 1 open.

    ES: Todos los S11 deben compartir la grilla ``f_hz`` (eso lo valida el
        llamador; aca solo se verifican las formas). ``s11_open`` es la sonda
        al aire -- actua como el patron de eps = 1.0006, NO como un open ideal
        de Gamma = 1.
    """
    f_hz = np.asarray(f_hz, dtype=float)
    s11_dut = np.asarray(s11_dut, dtype=complex)
    s11_open = np.asarray(s11_open, dtype=complex)
    s11_short = np.asarray(s11_short, dtype=complex)
    s11_ref = np.asarray(s11_ref, dtype=complex)

    for name, arr in (("s11_dut", s11_dut), ("s11_open", s11_open),
                      ("s11_short", s11_short), ("s11_ref", s11_ref)):
        if arr.shape != f_hz.shape:
            raise ValueError(f"{name} shape {arr.shape} != frequency grid {f_hz.shape}")

    warnings: List[str] = []

    eps_ref, ref_warnings = evaluate_epsilon_r(ref_liquid, f_hz, temp_c)
    warnings.extend(ref_warnings)

    # Eq. (18), Higa 2016 / funciones.get_er_DUTm: cross-ratio coefficients.
    # Shared denominator of both coefficients; if it collapses the point is
    # degenerate (probe barely distinguishes the standards there).
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = (s11_dut - s11_short) * (s11_ref - s11_open)
        coef_ref = (s11_dut - s11_open) * (s11_short - s11_ref) / denom
        coef_air = (s11_dut - s11_ref) * (s11_open - s11_short) / denom
        eps = -coef_ref * eps_ref - coef_air * eps_air

    gap_mask = (np.abs(denom) < denom_floor) | ~np.isfinite(eps)
    if np.any(gap_mask):
        eps = eps.copy()
        eps[gap_mask] = np.nan + 0j
        n_gap = int(np.count_nonzero(gap_mask))
        msg = (
            f"{n_gap} frequency point(s) are numerically degenerate "
            f"(cross-ratio denominator < {denom_floor:.0e}); left as gaps (NaN)."
        )
        warnings.append(msg)
        logger.warning("[simplified_solver] %s", msg)

    # Passivity QUALITY check (never alters the values: there is no branch to
    # pick -- a violation means noisy data or the capacitive model breaking).
    with np.errstate(invalid="ignore"):
        nonpassive_mask = (~gap_mask) & (
            (np.real(eps) <= 0.0) | (np.imag(eps) > im_tol)
        )
    if np.any(nonpassive_mask):
        n_bad = int(np.count_nonzero(nonpassive_mask))
        msg = (
            f"{n_bad} frequency point(s) violate passivity (Re<=0 or Im>0): "
            f"noisy standards or the capacitive (Gn=0) model degrading. "
            f"Consider the full two-liquid method for those frequencies."
        )
        warnings.append(msg)
        logger.warning("[simplified_solver] %s", msg)

    return SimplifiedEpsilonResult(
        f_hz=f_hz,
        eps=eps,
        eps_ref=eps_ref,
        coef_ref=coef_ref,
        coef_air=coef_air,
        gap_mask=gap_mask,
        nonpassive_mask=nonpassive_mask,
        ref_liquid_key=ref_liquid.key,
        temperature_c=float(temp_c),
        warnings=warnings,
    )
