"""
Reference-liquid library and temperature-dependent Debye permittivity models.

EN: Provides the complex relative permittivity epsilon_r(f, T) of the
    reference liquids used as calibration standards for the open-ended
    coaxial probe. Water uses a single-Debye model and Isopropyl Alcohol
    (IPA / propan-2-ol) uses a double-Debye model, both with Andrew
    Gregory's tabulated coefficients interpolated over temperature.

ES: Provee la permitividad relativa compleja epsilon_r(f, T) de los liquidos
    de referencia usados como patrones de calibracion para la sonda coaxial
    open-ended. El agua usa un modelo Debye simple y el alcohol isopropilico
    (IPA / propan-2-ol) un modelo Debye doble, ambos con los coeficientes
    tabulados de Andrew Gregory interpolados en temperatura.

Algorithm source / Fuente del algoritmo:
    Literal port of the MATLAB reference functions
        medicion_fluidos/App_ME2/src/measurements/get_pattern_wtr.m
        medicion_fluidos/App_ME2/src/measurements/get_pattern_ipa.m
    (A. Gregory, "Tables of the Complex Permittivity of Dielectric
    Reference Liquids ...", NPL Report MAT 23).

Sign convention / Convencion de signo (LOAD-BEARING):
    The Debye term denominator is kept EXACTLY as ``1 + 1j*f/f_r`` (as in
    the MATLAB code). This yields a permittivity with NEGATIVE imaginary
    part for a lossy/passive medium (epsilon_r = eps' - j*eps''). Do NOT
    "fix" this sign: the calibration math and the physical root filter in
    ``permittivity_solver`` depend on it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Polynomial order used to interpolate the tabulated coefficients vs.
# temperature. Gregory notes the standards' uncertainty dominates the error
# of a higher-order interpolation, so order 2 is used (matches MATLAB).
_POLY_ORDER = 2


class DebyeModelType(str, Enum):
    """Type of Debye model backing a reference liquid."""

    SINGLE_DEBYE = "single_debye"
    DOUBLE_DEBYE = "double_debye"


@dataclass(frozen=True)
class ReferenceLiquid:
    """
    Descriptor of a reference liquid with a temperature-dependent Debye model.

    Attributes
    ----------
    key : str
        Stable identifier (e.g. ``"water"``, ``"ipa"``).
    display_name : str
        Default human-readable name (localized names live in i18n resources).
    model_type : DebyeModelType
        Single- or double-Debye.
    temp_axis_c : tuple[float, ...]
        Tabulated temperature axis, in degrees Celsius.
    columns : dict[str, tuple[float, ...]]
        Tabulated coefficient columns aligned with ``temp_axis_c``.
        Single-Debye expects: ``eps_s``, ``eps_inf``, ``tau_r`` (seconds).
        Double-Debye expects: ``eps_s``, ``eps_h``, ``eps_inf``,
        ``f_r1`` (Hz), ``f_r2`` (Hz).
    validated : bool
        ``True`` when the coefficients were validated against the reference
        MATLAB implementation; ``False`` for literature-sourced entries.
    source : str
        Citation / provenance of the coefficients.
    """

    key: str
    display_name: str
    model_type: DebyeModelType
    temp_axis_c: Tuple[float, ...]
    columns: Dict[str, Tuple[float, ...]]
    validated: bool = False
    source: str = ""
    poly_order: int = _POLY_ORDER

    @property
    def temp_min_c(self) -> float:
        return float(min(self.temp_axis_c))

    @property
    def temp_max_c(self) -> float:
        return float(max(self.temp_axis_c))


def _interp_column(liquid: ReferenceLiquid, name: str, temp_c: float) -> float:
    """Polynomial-interpolate one tabulated column at ``temp_c``."""
    temp_axis = np.asarray(liquid.temp_axis_c, dtype=float)
    values = np.asarray(liquid.columns[name], dtype=float)
    coeffs = np.polyfit(temp_axis, values, liquid.poly_order)
    return float(np.polyval(coeffs, temp_c))


def evaluate_epsilon_r(
    liquid: ReferenceLiquid,
    f_hz: np.ndarray,
    temp_c: float,
) -> Tuple[np.ndarray, List[str]]:
    """
    Evaluate the complex relative permittivity of ``liquid`` over ``f_hz``.

    EN: Returns ``(epsilon_r, warnings)`` where ``epsilon_r`` is a complex
        array aligned with ``f_hz`` (using the eps' - j*eps'' convention),
        and ``warnings`` lists non-fatal issues (e.g. temperature outside the
        tabulated range -> extrapolation). Unlike the MATLAB reference, this
        does NOT raise on out-of-range temperature; it warns and extrapolates.

    ES: Devuelve ``(epsilon_r, warnings)`` donde ``epsilon_r`` es un arreglo
        complejo alineado con ``f_hz`` (convencion eps' - j*eps'') y
        ``warnings`` lista avisos no fatales (p. ej. temperatura fuera del
        rango tabulado -> extrapolacion). A diferencia del MATLAB original,
        NO lanza error si la temperatura esta fuera de rango: avisa y extrapola.
    """
    warnings: List[str] = []
    f_hz = np.asarray(f_hz, dtype=float)

    if temp_c < liquid.temp_min_c or temp_c > liquid.temp_max_c:
        msg = (
            f"Temperature {temp_c:.1f} C is outside the tabulated range "
            f"[{liquid.temp_min_c:.0f}, {liquid.temp_max_c:.0f}] C for "
            f"'{liquid.display_name}'; values are extrapolated."
        )
        warnings.append(msg)
        logger.warning("[reference_liquids] %s", msg)

    if liquid.model_type is DebyeModelType.SINGLE_DEBYE:
        eps_s = _interp_column(liquid, "eps_s", temp_c)
        eps_inf = _interp_column(liquid, "eps_inf", temp_c)
        tau_r = _interp_column(liquid, "tau_r", temp_c)
        f_r = 1.0 / (2.0 * np.pi * tau_r)
        # get_pattern_wtr.m, eq. 1 (single-Debye)
        epsilon = eps_inf + (eps_s - eps_inf) / (1.0 + 1j * f_hz / f_r)

    elif liquid.model_type is DebyeModelType.DOUBLE_DEBYE:
        eps_s = _interp_column(liquid, "eps_s", temp_c)
        eps_h = _interp_column(liquid, "eps_h", temp_c)
        eps_inf = _interp_column(liquid, "eps_inf", temp_c)
        f_r1 = _interp_column(liquid, "f_r1", temp_c)
        f_r2 = _interp_column(liquid, "f_r2", temp_c)
        # get_pattern_ipa.m, eq. 2 (double-Debye)
        epsilon = (
            eps_inf
            + (eps_s - eps_h) / (1.0 + 1j * f_hz / f_r1)
            + (eps_h - eps_inf) / (1.0 + 1j * f_hz / f_r2)
        )
    else:  # pragma: no cover - guarded by the enum
        raise ValueError(f"Unsupported Debye model: {liquid.model_type}")

    return np.asarray(epsilon, dtype=complex), warnings


# --------------------------------------------------------------------------- #
# Bundled reference liquids (validated against the MATLAB reference)
# --------------------------------------------------------------------------- #

_WATER = ReferenceLiquid(
    key="water",
    display_name="Distilled Water",
    model_type=DebyeModelType.SINGLE_DEBYE,
    # get_pattern_wtr.m tabulated values (T in [0, 60] C)
    temp_axis_c=(0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60),
    columns={
        "eps_s": (87.91, 85.83, 83.92, 82.05, 80.21, 78.36, 76.56, 74.87, 73.18, 69.89, 66.7),
        # MATLAB column tab.eps_i plays the role of eps_inf here.
        "eps_inf": (5.7, 5.7, 5.5, 6.0, 5.6, 5.2, 5.2, 5.1, 3.9, 4.0, 4.2),
        # Relaxation time in seconds (MATLAB stores ps * 1e-12).
        "tau_r": tuple(v * 1e-12 for v in
                       (17.67, 14.91, 12.68, 10.83, 9.36, 8.27, 7.28, 6.5, 5.82, 4.75, 4.01)),
    },
    validated=True,
    source="A. Gregory NPL tables, via MATLAB get_pattern_wtr.m (UTN 2024).",
)

_IPA = ReferenceLiquid(
    key="ipa",
    display_name="Isopropyl Alcohol (IPA)",
    model_type=DebyeModelType.DOUBLE_DEBYE,
    # get_pattern_ipa.m tabulated values (T in [10, 30] C)
    temp_axis_c=(10, 15, 20, 25, 30),
    columns={
        "eps_s": (21.73, 20.89, 20.11, 19.30, 18.50),
        "eps_h": (3.573, 3.566, 3.557, 3.551, 3.538),
        # MATLAB column tab.eps_i plays the role of eps_inf here.
        "eps_inf": (3.045, 3.035, 3.057, 3.065, 3.056),
        "f_r1": tuple(v * 1e9 for v in (0.217, 0.277, 0.351, 0.443, 0.557)),
        "f_r2": tuple(v * 1e9 for v in (5.037, 5.545, 5.721, 5.999, 6.655)),
    },
    validated=True,
    source="A. Gregory NPL tables, via MATLAB get_pattern_ipa.m (UTN 2024).",
)


REFERENCE_LIQUIDS: Dict[str, ReferenceLiquid] = {
    _WATER.key: _WATER,
    _IPA.key: _IPA,
}


def get_reference_liquid(key: str) -> ReferenceLiquid:
    """Return the reference liquid registered under ``key``."""
    try:
        return REFERENCE_LIQUIDS[key]
    except KeyError as exc:
        raise KeyError(
            f"Unknown reference liquid '{key}'. "
            f"Available: {sorted(REFERENCE_LIQUIDS)}"
        ) from exc


def list_reference_liquids() -> List[ReferenceLiquid]:
    """Return all registered reference liquids (for UI population)."""
    return list(REFERENCE_LIQUIDS.values())


# --------------------------------------------------------------------------- #
# Indicative S11 (nominal capacitive probe model) -- for UI guidance only
# --------------------------------------------------------------------------- #

# NOMINAL fringing capacitance of an open-ended coaxial probe (order 0.05 pF).
# This is a ROUGH, generic value: the true C0/G0 are what the 4-standard
# calibration determines. It is used ONLY to draw an *indicative* dotted S11
# reference curve for a known reference liquid, so an inexperienced user has a
# visual target shape. It must never be treated as the calibrated probe model.
NOMINAL_PROBE_C0_F = 5.0e-14  # 0.05 pF


def indicative_s11(
    liquid: ReferenceLiquid,
    f_hz: np.ndarray,
    temp_c: float,
    c0_f: float = NOMINAL_PROBE_C0_F,
    z0: float = 50.0,
) -> np.ndarray:
    """
    Indicative (NOT calibrated) S11 of the probe immersed in ``liquid``.

    EN: Uses the low-frequency capacitive-probe approximation
        ``Y = j*w*eps_r*C0`` with the liquid's KNOWN eps_r(f,T) and a NOMINAL
        C0, then ``S11 = (1 - Y*Z0)/(1 + Y*Z0)``. Loss comes only from the
        imaginary part of the known eps_r. Intended purely as a dotted visual
        reference; the real S11 depends on the calibrated probe constants.

    ES: Usa la aproximacion capacitiva de baja frecuencia ``Y = j*w*eps_r*C0``
        con el eps_r(f,T) CONOCIDO del liquido y un C0 NOMINAL, y luego
        ``S11 = (1 - Y*Z0)/(1 + Y*Z0)``. La perdida proviene solo de la parte
        imaginaria del eps_r conocido. Es solo una referencia visual punteada;
        el S11 real depende de las constantes calibradas de la sonda.
    """
    eps, _ = evaluate_epsilon_r(liquid, f_hz, temp_c)
    omega = 2.0 * np.pi * np.asarray(f_hz, dtype=float)
    y = 1j * omega * eps * c0_f
    return (1.0 - y * z0) / (1.0 + y * z0)
