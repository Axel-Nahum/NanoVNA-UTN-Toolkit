"""
Probe + VNA calibration constants (normalized conductance Gn and admittances).

EN: Computes the calibration constants needed to turn a measured reflection
    coefficient (S11) into the complex permittivity of an unknown liquid.
    From the four reference standards (Open, Short, and two reference liquids)
    it derives the normalized conductance ``Gn`` and the linearly-transformed
    admittances of the two reference liquids.

ES: Calcula las constantes de calibracion necesarias para convertir un
    coeficiente de reflexion medido (S11) en la permitividad compleja de un
    liquido incognita. A partir de los cuatro patrones de referencia (Open,
    Short y dos liquidos de referencia) obtiene la conductancia normalizada
    ``Gn`` y las admitancias linealmente transformadas de los dos liquidos.

Algorithm source / Fuente del algoritmo:
    "Mediciones de permitividad mediante una sonda coaxial", UTN-FRBA 2024,
    eqs. 15-17, and the MATLAB reference
        medicion_fluidos/App_ME2/src/measurements/get_pattern_constants.m

Role mapping / Mapeo de roles (pinned for internal consistency):
    Standard index   MATLAB name   This module
        1 (Short)      s11_sht       s11_short      Y1 -> inf  (not used)
        2 (Liquid)     s11_ipa       s11_ref1       Y2
        3 (Liquid)     s11_wtr       s11_ref2       Y3
        4 (Open)       s11_opn       s11_open       Y4 -> 0    (not used)
    ``ref1`` always plays the MATLAB "ipa" slot and ``ref2`` the "wtr" slot.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    ReferenceLiquid,
    evaluate_epsilon_r,
)

logger = logging.getLogger(__name__)

# Below this magnitude a complex denominator is treated as zero (degenerate
# standards) and the affected frequency point is masked with NaN.
_DENOM_FLOOR = 1e-12


@dataclass
class PatternConstants:
    """
    Calibration constants for one frequency grid + temperature + liquid pair.

    All complex arrays are aligned with ``f_hz``.
    """

    f_hz: np.ndarray
    temp_c: float
    gn: np.ndarray            # normalized conductance Gn
    y_ref1: np.ndarray        # transformed admittance of ref1 (MATLAB Y_ipa / Y2)
    y_ref2: np.ndarray        # transformed admittance of ref2 (MATLAB Y_wtr / Y3)
    s11_short: np.ndarray
    s11_ref1: np.ndarray
    s11_ref2: np.ndarray
    ref1_key: str
    ref2_key: str
    warnings: List[str]


def compute_pattern_constants(
    f_hz: np.ndarray,
    temp_c: float,
    s11_short: np.ndarray,
    s11_ref1: np.ndarray,
    s11_ref2: np.ndarray,
    s11_open: np.ndarray,
    ref1: ReferenceLiquid,
    ref2: ReferenceLiquid,
) -> PatternConstants:
    """
    Port of ``get_pattern_constants.m`` generalized to two reference liquids.

    Parameters
    ----------
    f_hz : np.ndarray
        Frequency grid in Hz (shared by all standards).
    temp_c : float
        Temperature at which the references are evaluated, in Celsius.
    s11_short, s11_ref1, s11_ref2, s11_open : np.ndarray
        Complex S11 of each standard, aligned with ``f_hz``.
    ref1, ref2 : ReferenceLiquid
        Reference liquids for the ref1 (ipa slot) and ref2 (wtr slot).
    """
    f_hz = np.asarray(f_hz, dtype=float)
    s11_short = np.asarray(s11_short, dtype=complex)
    s11_ref1 = np.asarray(s11_ref1, dtype=complex)
    s11_ref2 = np.asarray(s11_ref2, dtype=complex)
    s11_open = np.asarray(s11_open, dtype=complex)

    warnings: List[str] = []

    eps_r1, w1 = evaluate_epsilon_r(ref1, f_hz, temp_c)   # MATLAB epsilon_ipa
    eps_r2, w2 = evaluate_epsilon_r(ref2, f_hz, temp_c)   # MATLAB epsilon_wtr
    warnings.extend(w1)
    warnings.extend(w2)

    # get_pattern_constants.m, lines 31-39 (Gn). Names A..F mirror the MATLAB.
    with np.errstate(divide="ignore", invalid="ignore"):
        A = (s11_open - s11_short) * (s11_ref2 - s11_ref1)
        B = (s11_open - s11_ref1) * (s11_short - s11_ref2) * eps_r2
        C = (s11_open - s11_ref2) * (s11_ref1 - s11_short) * eps_r1

        D = (s11_open - s11_short) * (s11_ref2 - s11_ref1)
        E = (s11_open - s11_ref1) * (s11_short - s11_ref2) * np.power(eps_r2, 2.5)
        F = (s11_open - s11_ref2) * (s11_ref1 - s11_short) * np.power(eps_r1, 2.5)

        denom = D + E + F
        gn = -(A + B + C) / denom

        # get_pattern_constants.m, lines 43-44 (linearly transformed admittances)
        y_ref1 = eps_r1 + gn * np.power(eps_r1, 2.5)   # Y2 (MATLAB Y_ipa)
        y_ref2 = eps_r2 + gn * np.power(eps_r2, 2.5)   # Y3 (MATLAB Y_wtr)

    bad = np.abs(denom) < _DENOM_FLOOR
    if np.any(bad):
        n_bad = int(np.count_nonzero(bad))
        msg = (
            f"Gn denominator near zero at {n_bad} frequency point(s) "
            f"(coincident standards?); those points are masked as NaN."
        )
        warnings.append(msg)
        logger.warning("[pattern_constants] %s", msg)
        gn[bad] = np.nan
        y_ref1[bad] = np.nan
        y_ref2[bad] = np.nan

    return PatternConstants(
        f_hz=f_hz,
        temp_c=float(temp_c),
        gn=gn,
        y_ref1=y_ref1,
        y_ref2=y_ref2,
        s11_short=s11_short,
        s11_ref1=s11_ref1,
        s11_ref2=s11_ref2,
        ref1_key=ref1.key,
        ref2_key=ref2.key,
        warnings=warnings,
    )
