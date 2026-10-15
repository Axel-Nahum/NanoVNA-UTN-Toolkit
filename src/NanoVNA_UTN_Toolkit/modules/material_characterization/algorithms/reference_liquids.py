"""
Reference-liquid library and temperature-dependent Debye permittivity models.

EN: Provides the complex relative permittivity epsilon_r(f, T) of the
    reference liquids used as calibration standards for the open-ended
    coaxial probe. Each liquid carries a table of relaxation parameters at
    discrete temperatures (single-Debye, double-Debye, Debye-Gamma, or a
    lossless constant for non-polar liquids), taken from Kaatze (water) and
    NPL Report MAT 23 (the rest).

ES: Provee la permitividad relativa compleja epsilon_r(f, T) de los liquidos
    de referencia usados como patrones de calibracion para la sonda coaxial
    open-ended. Cada liquido tiene una tabla de parametros de relajacion a
    temperaturas discretas (Debye simple, Debye doble, Debye-Gamma, o una
    constante sin perdidas para liquidos no polares), tomada de Kaatze (agua)
    y del NPL Report MAT 23 (el resto).

Sources / Fuentes:
    - U. Kaatze, "Complex permittivity of water as a function of frequency
      and temperature", J. Chem. Eng. Data 34 (1989) 371-374, Table III.
    - A. P. Gregory and R. N. Clarke, "Tables of the complex permittivity of
      dielectric reference liquids at frequencies up to 5 GHz", NPL Report
      MAT 23 (2012): Table 6 (static permittivity), Section 7 (relaxation
      parameters), Section 8 (best-fit permittivity, used by the tests).
    - Water and IPA tables were first ported from the MATLAB reference
        medicion_fluidos/App_ME2/src/measurements/get_pattern_wtr.m
        medicion_fluidos/App_ME2/src/measurements/get_pattern_ipa.m

Temperature interpolation / Interpolacion en temperatura:
    EN: Follows NPL MAT 23 section 1.3: the permittivity is computed at the
        two nearest tabulated temperatures with their OWN parameters, and the
        complex result is interpolated linearly in temperature. Tabulated
        temperatures are therefore reproduced exactly. The MATLAB code instead
        fitted an order-2 polynomial to each parameter column over the whole
        range; that fit does not pass through the table (water at 20 C:
        tau 9.69 ps instead of 9.36 ps, eps'' +3.8 % at 1.5 GHz; ethanol
        eps' off by 0.12) and was dropped.
    ES: Sigue la seccion 1.3 del NPL MAT 23: la permitividad se calcula en
        las dos temperaturas tabuladas mas cercanas con SUS parametros, y el
        resultado complejo se interpola linealmente en temperatura. Asi las
        temperaturas tabuladas se reproducen exactamente. El MATLAB ajustaba
        un polinomio de orden 2 a cada columna en todo el rango; ese ajuste no
        pasa por la tabla (agua a 20 C: tau 9,69 ps en vez de 9,36 ps, eps''
        +3,8 % a 1,5 GHz; etanol eps' corrido 0,12) y se descarto.

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


class DebyeModelType(str, Enum):
    """Type of Debye model backing a reference liquid."""

    SINGLE_DEBYE = "single_debye"
    DOUBLE_DEBYE = "double_debye"
    DEBYE_GAMMA = "debye_gamma"
    # Non-polar liquid: eps = eps_s, real and frequency-independent.
    NONPOLAR = "nonpolar"


# Parameter columns each model type reads from ``ReferenceLiquid.columns``.
_MODEL_COLUMNS: Dict[DebyeModelType, Tuple[str, ...]] = {
    DebyeModelType.SINGLE_DEBYE: ("eps_s", "eps_inf", "tau_r"),
    DebyeModelType.DOUBLE_DEBYE: ("eps_s", "eps_h", "eps_inf", "f_r1", "f_r2"),
    DebyeModelType.DEBYE_GAMMA: ("eps_s", "eps_h", "f_r", "gamma"),
    DebyeModelType.NONPOLAR: ("eps_s",),
}


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
        Relaxation equation used at every tabulated temperature.
    temp_axis_c : tuple[float, ...]
        Tabulated temperature axis, in degrees Celsius, strictly increasing.
    columns : dict[str, tuple[float, ...]]
        Tabulated coefficient columns aligned with ``temp_axis_c``.
        Single-Debye expects: ``eps_s``, ``eps_inf``, ``tau_r`` (seconds).
        Double-Debye expects: ``eps_s``, ``eps_h``, ``eps_inf``,
        ``f_r1`` (Hz), ``f_r2`` (Hz).
        Debye-Gamma expects: ``eps_s``, ``eps_h``, ``f_r`` (Hz), ``gamma``
        (dimensionless, multiplies frequency expressed in GHz).
        Non-polar expects: ``eps_s``.
    validated : bool
        ``True`` when the coefficient table was validated against the
        reference MATLAB implementation; ``False`` for literature-sourced
        entries. (The temperature interpolation no longer follows MATLAB:
        see the module docstring.)
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
    has_debye_model: bool = True

    def __post_init__(self) -> None:
        # Catch transcription slips (a missing value shifts a whole column).
        if not self.has_debye_model:
            return
        temps = np.asarray(self.temp_axis_c, dtype=float)
        if temps.size > 1 and np.any(np.diff(temps) <= 0):
            raise ValueError(f"{self.key}: temp_axis_c must be strictly increasing")
        for name in _MODEL_COLUMNS[self.model_type]:
            if len(self.columns.get(name, ())) != temps.size:
                raise ValueError(
                    f"{self.key}: column '{name}' must have {temps.size} values "
                    f"(one per tabulated temperature)"
                )

    @property
    def temp_min_c(self) -> float:
        return float(min(self.temp_axis_c))

    @property
    def temp_max_c(self) -> float:
        return float(max(self.temp_axis_c))


def _evaluate_row(liquid: ReferenceLiquid, row: int, f_hz: np.ndarray) -> np.ndarray:
    """Permittivity with the parameters of ONE tabulated temperature."""
    p = {name: float(liquid.columns[name][row]) for name in _MODEL_COLUMNS[liquid.model_type]}

    if liquid.model_type is DebyeModelType.SINGLE_DEBYE:
        f_r = 1.0 / (2.0 * np.pi * p["tau_r"])
        # get_pattern_wtr.m, eq. 1 (single-Debye)
        return p["eps_inf"] + (p["eps_s"] - p["eps_inf"]) / (1.0 + 1j * f_hz / f_r)

    if liquid.model_type is DebyeModelType.DOUBLE_DEBYE:
        # get_pattern_ipa.m, eq. 2 (double-Debye)
        return (
            p["eps_inf"]
            + (p["eps_s"] - p["eps_h"]) / (1.0 + 1j * f_hz / p["f_r1"])
            + (p["eps_h"] - p["eps_inf"]) / (1.0 + 1j * f_hz / p["f_r2"])
        )

    if liquid.model_type is DebyeModelType.DEBYE_GAMMA:
        # NPL MAT 23 eq. 3: single relaxation plus a linear "tail" standing in
        # for a second relaxation that sits above the tabulated band. The tail
        # is defined with the frequency expressed in GHz, hence the 1e9 scale.
        # It is subtracted as -1j*gamma*f_GHz, i.e. it ADDS loss under the
        # eps' - j*eps'' convention pinned in the module docstring.
        return (
            p["eps_h"]
            + (p["eps_s"] - p["eps_h"]) / (1.0 + 1j * f_hz / p["f_r"])
            - 1j * p["gamma"] * (f_hz / 1e9)
        )

    if liquid.model_type is DebyeModelType.NONPOLAR:
        return np.full(f_hz.shape, p["eps_s"], dtype=complex)

    raise ValueError(f"Unsupported Debye model: {liquid.model_type}")  # pragma: no cover


def _bracketing_rows(liquid: ReferenceLiquid, temp_c: float) -> Tuple[int, int, float]:
    """``(lo, hi, w)`` with ``eps(T) = (1 - w)*eps[lo] + w*eps[hi]``.

    Inside the table, lo/hi are the two nearest tabulated temperatures and
    0 <= w <= 1 (w is exactly 0 or 1 on a tabulated temperature). Outside it,
    the two outermost rows are extended linearly (w < 0 or w > 1).
    """
    temps = np.asarray(liquid.temp_axis_c, dtype=float)
    if temps.size == 1:
        return 0, 0, 0.0
    hi = int(np.clip(np.searchsorted(temps, temp_c), 1, temps.size - 1))
    lo = hi - 1
    return lo, hi, float((temp_c - temps[lo]) / (temps[hi] - temps[lo]))


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
        tabulated range -> extrapolation). Between tabulated temperatures the
        permittivity is interpolated linearly (NPL MAT 23 section 1.3); on a
        tabulated temperature it is exactly the tabulated model. Unlike the
        MATLAB reference, this does NOT raise on out-of-range temperature: it
        warns and extends the two outermost rows linearly.

    ES: Devuelve ``(epsilon_r, warnings)`` donde ``epsilon_r`` es un arreglo
        complejo alineado con ``f_hz`` (convencion eps' - j*eps'') y
        ``warnings`` lista avisos no fatales (p. ej. temperatura fuera del
        rango tabulado -> extrapolacion). Entre temperaturas tabuladas la
        permitividad se interpola linealmente (NPL MAT 23 seccion 1.3); en una
        temperatura tabulada es exactamente el modelo tabulado. A diferencia
        del MATLAB original, NO lanza error si la temperatura esta fuera de
        rango: avisa y prolonga linealmente las dos filas extremas.
    """
    if not liquid.has_debye_model:
        raise NotImplementedError(
            f"No Debye model is available yet for '{liquid.display_name}'. "
            "It can be listed as a reference but cannot be used for calibration "
            "until its model coefficients are added."
        )

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

    lo, hi, w = _bracketing_rows(liquid, temp_c)
    epsilon = _evaluate_row(liquid, lo, f_hz)
    if w != 0.0:
        # NPL MAT 23 section 1.3: linear interpolation of the permittivity
        # between the two nearest tabulated temperatures.
        epsilon = (1.0 - w) * epsilon + w * _evaluate_row(liquid, hi, f_hz)

    return np.asarray(epsilon, dtype=complex), warnings


# --------------------------------------------------------------------------- #
# Bundled reference liquids (validated against the MATLAB reference)
# --------------------------------------------------------------------------- #

# EN: Kaatze 1989, Table III (the same table get_pattern_wtr.m carries). At
#     20 C it gives eps_s 80.21, eps_inf 5.6, tau 9.36 ps; NPL MAT 23 Table 6
#     measured eps_s = 80.29 +/- 0.20 there, consistent within uncertainty.
# ES: Kaatze 1989, Tabla III (la misma que trae get_pattern_wtr.m). A 20 C da
#     eps_s 80,21, eps_inf 5,6, tau 9,36 ps; la Tabla 6 del NPL MAT 23 midio
#     eps_s = 80,29 +/- 0,20 ahi, consistente dentro de la incertidumbre.
_WATER = ReferenceLiquid(
    key="water",
    display_name="Distilled Water",
    model_type=DebyeModelType.SINGLE_DEBYE,
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
    source=("U. Kaatze, J. Chem. Eng. Data 34 (1989) 371-374, Table III "
            "(single-Debye, 0-60 C); via MATLAB get_pattern_wtr.m (UTN 2024)."),
)

# EN: NPL MAT 23, propan-2-ol double-Debye table (eqn. 2, eps_s fitted: no
#     admittance-cell value exists, note 30). Recommended range 10-25 C.
# ES: NPL MAT 23, tabla Debye doble del propan-2-ol (ec. 2, eps_s ajustado:
#     no hay valor de celda de admitancia, nota 30). Rango recomendado 10-25 C.
_IPA = ReferenceLiquid(
    key="ipa",
    display_name="Isopropyl Alcohol (IPA)",
    model_type=DebyeModelType.DOUBLE_DEBYE,
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
    source=("NPL Report MAT 23 (Gregory & Clarke 2012), propan-2-ol double-Debye "
            "table; via MATLAB get_pattern_ipa.m (UTN 2024)."),
)


# --------------------------------------------------------------------------- #
# Additional liquids from the NPL tables (not covered by the MATLAB reference)
# --------------------------------------------------------------------------- #
#
# Ethanol and methanol are the other two liquids the group has actually used
# across the years (ethanol is the unknown of the 2026 probe-21mm campaign), so
# they are the natural additions to the reference dropdowns. Their coefficients
# come from NPL Report MAT 23 (Gregory & Clarke, 2012), the same source behind
# the water and IPA tables above -- but unlike those two they were NOT validated
# against the MATLAB implementation (it only ships water and IPA), hence
# ``validated=False``.
#
# Each liquid has ONE relaxation equation for all its rows. Several NPL liquids
# switch equation with temperature (butan-1-ol: double-Debye up to 40 C,
# Debye-Gamma above); for those only the rows of one equation are carried.

# EN: Debye-Gamma (eqn. 3). NPL note 27: a second relaxation makes eps'
#     diverge from this equation above ~4 GHz.
# ES: Debye-Gamma (ec. 3). Nota 27 del NPL: una segunda relajacion hace que
#     eps' se aparte de esta ecuacion por encima de ~4 GHz.
_ETHANOL = ReferenceLiquid(
    key="ethanol",
    display_name="Ethanol",
    model_type=DebyeModelType.DEBYE_GAMMA,
    temp_axis_c=(10, 15, 20, 25, 30, 35, 40, 45, 50),
    columns={
        "eps_s": (26.79, 25.95, 25.16, 24.43, 23.65, 22.88, 22.16, 21.45, 20.78),
        "eps_h": (4.624, 4.590, 4.531, 4.505, 4.471, 4.439, 4.410, 4.394, 4.378),
        "f_r": tuple(v * 1e9 for v in
                     (0.596, 0.700, 0.829, 0.964, 1.124, 1.303, 1.511, 1.745, 2.010)),
        "gamma": (0.075, 0.071, 0.059, 0.056, 0.054, 0.053, 0.050, 0.049, 0.044),
    },
    validated=False,
    source=("NPL Report MAT 23 (Gregory & Clarke 2012), eq. 3 Debye-Gamma table. "
            "Transcribed via Sonda_2026_py/Patrones.py "
            "(https://github.com/pguzmanUTN/Sonda_2026_py)."),
)

_METHANOL = ReferenceLiquid(
    key="methanol",
    display_name="Methanol",
    model_type=DebyeModelType.SINGLE_DEBYE,
    temp_axis_c=(10, 15, 20, 25, 30, 35, 40, 45, 50),
    columns={
        "eps_s": (35.74, 34.68, 33.64, 32.66, 31.69, 30.78, 29.85, 28.95, 28.19),
        "eps_inf": (5.818, 5.698, 5.654, 5.563, 5.450, 5.388, 5.251, 5.107, 5.224),
        # NPL tabulates the relaxation FREQUENCY in GHz; this library stores the
        # relaxation TIME in seconds for single-Debye liquids (see water above).
        "tau_r": tuple(1.0 / (2.0 * np.pi * v * 1e9) for v in
                       (2.262, 2.532, 2.822, 3.141, 3.490, 3.862, 4.283, 4.738, 5.175)),
    },
    validated=False,
    source=("NPL Report MAT 23 (Gregory & Clarke 2012), eq. 1 single-Debye table. "
            "Transcribed via Sonda_2026_py/Patrones.py "
            "(https://github.com/pguzmanUTN/Sonda_2026_py)."),
)


# EN: Double-Debye (eqn. 2), the NPL table recommended for 10-40 C. The 45 and
#     50 C rows exist only for the Debye-Gamma equation (note 26) and are not
#     carried: above 40 C the 35/40 C rows are extended with a warning.
# ES: Debye doble (ec. 2), la tabla que el NPL recomienda para 10-40 C. Las
#     filas de 45 y 50 C solo existen para la ecuacion Debye-Gamma (nota 26) y
#     no se incluyen: arriba de 40 C se prolongan las filas de 35/40 C con aviso.
_BUTANOL = ReferenceLiquid(
    key="butanol",
    display_name="1-Butanol",
    model_type=DebyeModelType.DOUBLE_DEBYE,
    temp_axis_c=(10, 15, 20, 25, 30, 35, 40),
    columns={
        "eps_s": (19.54, 18.86, 18.19, 17.53, 16.89, 16.26, 15.65),
        "eps_h": (3.528, 3.527, 3.505, 3.506, 3.501, 3.493, 3.484),
        "eps_inf": (2.914, 2.914, 2.900, 2.921, 2.923, 2.902, 2.883),
        "f_r1": tuple(v * 1e9 for v in (0.167, 0.207, 0.257, 0.318, 0.393, 0.483, 0.592)),
        "f_r2": tuple(v * 1e9 for v in (4.878, 5.259, 5.865, 5.979, 6.433, 7.234, 8.139)),
    },
    validated=False,
    source=("NPL Report MAT 23 (Gregory & Clarke 2012), butan-1-ol double-Debye "
            "table (eqn. 2), recommended range 10-40 C."),
)


# --------------------------------------------------------------------------- #
# Liquids NPL MAT 23 measured only at low frequency (Table 6, static values)
# --------------------------------------------------------------------------- #

# EN: Non-polar and practically lossless (NPL note 19: tan(delta) < 1e-4, so
#     eps'' < 2e-4), hence eps = eps_s at every frequency. Static values from
#     the admittance cell (+/-0.002 at k=2), consistent with the IUPAC
#     reference values of Kienitz & Marsh (1981).
# ES: No polar y practicamente sin perdidas (nota 19 del NPL: tan(delta) <
#     1e-4, o sea eps'' < 2e-4), por eso eps = eps_s a toda frecuencia. Valores
#     estaticos de la celda de admitancia (+/-0,002 con k=2), consistentes con
#     los valores de referencia IUPAC de Kienitz y Marsh (1981).
_CYCLOHEXANE = ReferenceLiquid(
    key="cyclohexane",
    display_name="Cyclohexane",
    model_type=DebyeModelType.NONPOLAR,
    temp_axis_c=(10, 15, 20, 25, 30, 35, 40, 45, 50),
    columns={
        "eps_s": (2.040, 2.033, 2.024, 2.015, 2.008, 2.000, 1.992, 1.984, 1.975),
    },
    validated=False,
    source=("NPL Report MAT 23 (Gregory & Clarke 2012), Table 6 static permittivity "
            "(also Meas. Sci. Technol. 16 (2005) 1506-1516); lossless, note 19."),
)

# EN: eps_s(T) is NPL MAT 23 Table 6 (+/-0.04 at k=2). NPL gives no
#     relaxation parameters: acetone relaxes far above its 5 GHz band
#     (note 23). The 45 and 50 C values are omitted (bubbling in the cell,
#     note 18; boiling point 56 C). The loss term is a single Debye with
#     tau = 3.2 ps (f_r ~ 50 GHz) and eps_inf = 2.0 at every temperature,
#     attributed to Vij, Grochulski, Kocot & Hufnagel, Mol. Phys. 72 (1991)
#     353-361 (acetone at 293 K, 50-310 GHz). That paper fits Budo /
#     confined-rotator models; the single-Debye equivalent was NOT checked
#     against its full text, and its temperature dependence is ignored. With
#     these values eps' stays within 0.02 of eps_s below 1.5 GHz, while eps''
#     (about 0.58 at 1.5 GHz, 20 C) scales with tau.
# ES: eps_s(T) es la Tabla 6 del NPL MAT 23 (+/-0,04 con k=2). El NPL no da
#     parametros de relajacion: la acetona relaja muy por encima de su banda
#     de 5 GHz (nota 23). Se omiten 45 y 50 C (burbujas en la celda, nota 18;
#     ebulle a 56 C). La perdida es un Debye simple con tau = 3,2 ps
#     (f_r ~ 50 GHz) y eps_inf = 2,0 a toda temperatura, atribuido a Vij,
#     Grochulski, Kocot y Hufnagel, Mol. Phys. 72 (1991) 353-361 (acetona a
#     293 K, 50-310 GHz). Ese trabajo ajusta modelos de Budo / rotor confinado;
#     el Debye simple equivalente NO se verifico contra el texto completo, y se
#     ignora su dependencia con la temperatura. Con estos valores eps' queda a
#     menos de 0,02 de eps_s por debajo de 1,5 GHz, mientras que eps'' (unos
#     0,58 a 1,5 GHz, 20 C) escala con tau.
_ACETONE = ReferenceLiquid(
    key="acetone",
    display_name="Acetone",
    model_type=DebyeModelType.SINGLE_DEBYE,
    temp_axis_c=(5, 10, 15, 20, 25, 30, 35, 40),
    columns={
        "eps_s": (22.80, 22.21, 21.65, 21.13, 20.59, 20.10, 19.60, 19.12),
        "eps_inf": (2.0,) * 8,
        "tau_r": (3.2e-12,) * 8,
    },
    validated=False,
    source=("eps_s: NPL Report MAT 23 (Gregory & Clarke 2012), Table 6. "
            "tau 3.2 ps / eps_inf 2.0: Vij et al., Mol. Phys. 72 (1991) 353 "
            "(approximate, not verified against the paper)."),
)

_BUTANOL = ReferenceLiquid(
    key="butanol",
    display_name="1-Butanol",
    model_type=DebyeModelType.SINGLE_DEBYE,  # placeholder — not used
    temp_axis_c=(20,),                        # placeholder
    columns={},                               # placeholder
    validated=False,
    source="No Debye model available yet — listed for future use.",
    has_debye_model=False,
)


REFERENCE_LIQUIDS: Dict[str, ReferenceLiquid] = {
    _WATER.key: _WATER,
    _IPA.key: _IPA,
    _ETHANOL.key: _ETHANOL,
    _METHANOL.key: _METHANOL,
    _BUTANOL.key: _BUTANOL,
    _CYCLOHEXANE.key: _CYCLOHEXANE,
    _ACETONE.key: _ACETONE,
    _BUTANOL.key: _BUTANOL,
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
