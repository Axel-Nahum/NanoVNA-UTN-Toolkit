"""
Measurement-quality checks and noise-based spike removal for open-coax sweeps.

EN: Non-blocking diagnostics computed next to the permittivity. None of them
    changes a value the solvers return: each adds a warning that says where
    the data cannot support the result, and why.

    * Sensitivity (low-frequency limit of the probe). At low frequency every
      liquid looks like an open: S11 moves about 2*w*C0*Z0 per unit of eps,
      so an S11 error sigma becomes an eps error sigma / (2*w*C0*Z0) -- with
      the 3 mm probe (C0 = 19 fF) and sigma = 0.001: +-1675 at 50 kHz, +-5.6
      at 15 MHz, +-0.84 at 100 MHz. Two measured quantities are compared with
      sigma: the separation of the two calibration liquids (ref1 - ref2, or
      ref1 - air in the simplified method), turned into the eps resolution it
      gives, and the contrast of the sample against air, |S_dut - S_open|.
      With a known probe the separation is capped by the probe model's: a
      larger measured separation is not information (a smoothed sweep spreads
      the contrast of higher frequencies down to its first points -- the 3 mm
      NanoVNA set reads |S_water - S_IPA| = 0.0165 at 50 kHz, where the probe
      allows 4e-5). The same comparison tells where the values actually
      diverge: below the band where the probe is well resolved, the measured
      separation must keep the probe model's frequency shape (their ratio
      stays constant, whatever the true C0); where it departs by more than
      10 % the S11 there is not the probe's, and the sample's eps drifts by
      about as much (21 mm R60 set: +18 % at 10 MHz, ethanol 17 % low). The
      thresholds are loose on purpose (+-2 per sigma, sample >= 1 sigma from
      air): only points whose value cannot be trusted are flagged, and the
      charts and medians leave them out so they never set the scale.
    * Gn physicality. Gn = G0/(j*w*C0) models radiation: arg(Gn) = -90 deg and
      |Gn| ~ f^3. Radiation is largest at the top of the sweep, so if even the
      upper octave shows neither signature, Gn holds noise and the
      inconsistency between the reference liquids over the whole sweep.
    * Passivity of the sweeps: |S11| > 1 + tol cannot come from a passive
      load; the VNA calibration is off there.
    * Spike removal: a point is replaced by the mean of its neighbours only
      when its second difference is k times the LOCAL noise (robust median of
      the nearby second differences), exceeds the S11 error budget and is
      isolated. An outlier shared by several sweeps at the same frequency is
      an instrument artefact (the 3 mm NanoVNA set has one at 825 MHz in all
      six sweeps) that the calibration cancels: it is left alone, because
      removing it from some sweeps only would break that cancellation.

ES: Diagnosticos no bloqueantes que se calculan junto con la permitividad.
    Ninguno cambia un valor que devuelvan los solvers: cada uno agrega un
    warning que dice donde los datos no pueden sostener el resultado, y por que.

    * Sensibilidad (limite de baja frecuencia de la sonda). En baja frecuencia
      todo liquido se parece a un open: el S11 se mueve unos 2*w*C0*Z0 por
      unidad de eps, asi que un error sigma en S11 se vuelve un error
      sigma / (2*w*C0*Z0) en eps -- con la sonda de 3 mm (C0 = 19 fF) y
      sigma = 0.001: +-1675 a 50 kHz, +-5.6 a 15 MHz, +-0.84 a 100 MHz. Se
      comparan con sigma dos magnitudes medidas: la separacion de los dos
      liquidos de calibracion (ref1 - ref2, o ref1 - aire en el metodo
      simplificado), convertida en la resolucion en eps que da, y el contraste
      de la muestra contra el aire, |S_dut - S_open|. Con una sonda conocida la
      separacion se acota con la del modelo de la sonda: una separacion medida
      mayor no es informacion (un barrido suavizado arrastra el contraste de
      frecuencias mas altas hasta sus primeros puntos -- el set NanoVNA de
      3 mm da |S_agua - S_IPA| = 0.0165 a 50 kHz, donde la sonda permite 4e-5).
      La misma comparacion dice donde los valores divergen de verdad: por
      debajo de la banda donde la sonda resuelve bien, la separacion medida
      tiene que conservar la forma en frecuencia del modelo de la sonda (su
      cociente se mantiene constante, sea cual sea el C0 real); donde se
      aparta mas de un 10 % el S11 ya no es el de la sonda, y el eps de la
      muestra se corre mas o menos lo mismo (set R60 de 21 mm: +18 % a 10 MHz,
      etanol 17 % bajo). Los umbrales son holgados a proposito (+-2 por sigma,
      muestra >= 1 sigma del aire): solo se marcan los puntos cuyo valor no es
      confiable, y los graficos y las medianas los dejan afuera para que nunca
      definan la escala.
    * Fisica de Gn. Gn = G0/(j*w*C0) modela la radiacion: arg(Gn) = -90 grados
      y |Gn| ~ f^3. La radiacion es maxima en el extremo alto del barrido, asi
      que si ni la octava superior muestra ninguna de las dos firmas, Gn
      contiene ruido y la inconsistencia entre los liquidos de referencia en
      todo el barrido.
    * Pasividad de los barridos: |S11| > 1 + tol no puede venir de una carga
      pasiva; ahi la calibracion del VNA esta corrida.
    * Remocion de picos: un punto se reemplaza por el promedio de sus vecinos
      solo cuando su segunda diferencia es k veces el ruido LOCAL (mediana
      robusta de las segundas diferencias cercanas), supera el presupuesto de
      error de S11 y esta aislado. Un outlier que comparten varios barridos en
      la misma frecuencia es un artefacto del instrumento (el set NanoVNA de
      3 mm tiene uno en 825 MHz en los seis barridos) que la calibracion
      cancela: se deja, porque sacarlo solo de algunos barridos romperia esa
      cancelacion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.probe_models import (
    Z0_OHM,
)

logger = logging.getLogger(__name__)

#: S11 error budget of a NanoVNA after SOL (drift, connector repeatability,
#: calibration residual). Trace noise alone underestimates it, and a smoothed
#: sweep hides even that: a noise estimate from the data only raises it.
S11_ERROR_FLOOR = 1e-3
#: Largest eps error per S11 error sigma that still counts as information.
#: +-1 flagged points whose values were still right (3 mm acetone 45-75 MHz);
#: +-2 starts where they go wrong (30 MHz and below).
EPS_RESOLUTION_MAX = 2.0
#: Resolution of the band trusted to fix the probe model's scale for the
#: consistency check below (the well-resolved part of the sweep).
EPS_RESOLUTION_TRUSTED = 1.0
#: The sample must differ from air by at least this many sigma.
DUT_CONTRAST_MIN = 1.0
#: Below the trusted band, |S_ref1 - S_ref2| may depart from the probe
#: model's frequency shape by at most this (relative) before the point is
#: flagged: the sample's eps drifts by about as much.
REF_CONSISTENCY_TOL = 0.10
#: The capacitive model holds while w*C0*Z0*|eps| stays below this.
_MODEL_REGIME_MAX = 0.5
#: Consecutive usable points that mark the start of the usable band (a lone
#: point that happens to pass inside the noise does not).
MIN_USABLE_RUN = 3
#: |S11| above 1 + this is flagged as non-passive.
S11_PASSIVE_TOL = 0.02
#: Gn is radiation-like when its phase is within this of -90 deg ...
GN_PHASE_TOL_DEG = 45.0
#: ... and |Gn| grows at least as f^GN_SLOPE_MIN (radiation: f^3).
GN_SLOPE_MIN = 1.0
#: Points needed to judge Gn on the upper octave.
_GN_MIN_POINTS = 5
#: Spike: second difference above SPIKE_K times the local noise ...
SPIKE_K = 6.0
#: ... and above SPIKE_ISOLATION times its neighbours' (a pure spike d gives
#: d at the point and d/2 at each neighbour; a step gives d/2 at both sides).
SPIKE_ISOLATION = 1.5
#: Half-width, in points, of the window the local noise is taken from.
SPIKE_HALF_WINDOW = 6
#: A spike is common to several sweeps when another sweep is at least this
#: many local-noise units off at the same point.
SPIKE_COMMON_K = 3.0
# Relative permittivity of air, the second point of the simplified method
# (same value as simplified_solver.EPS_AIR; not imported to avoid a cycle).
_EPS_AIR = 1.0006


def _fmt_hz(f_hz: float) -> str:
    f_hz = float(f_hz)
    if f_hz >= 1e9:
        return f"{f_hz / 1e9:.4g} GHz"
    if f_hz >= 1e6:
        return f"{f_hz / 1e6:.4g} MHz"
    return f"{f_hz / 1e3:.4g} kHz"


# --------------------------------------------------------------------------- #
# Noise and spikes
# --------------------------------------------------------------------------- #

def second_difference(s11: np.ndarray) -> np.ndarray:
    """``s[i] - (s[i-1] + s[i+1]) / 2`` per point (0 at both ends)."""
    s11 = np.asarray(s11, dtype=complex)
    r = np.zeros_like(s11)
    if s11.size >= 3:
        r[1:-1] = s11[1:-1] - 0.5 * (s11[:-2] + s11[2:])
    return r


def estimate_s11_noise(*sweeps: np.ndarray) -> float:
    """
    Typical S11 trace noise: median |second difference| over all ``sweeps``.

    For complex white noise of RMS magnitude sigma the second difference has
    median magnitude ~0.98*sigma, so this reads directly as sigma. Smooth
    curvature of the trace adds to it (an upper bound, never an
    underestimate); smoothing removes noise from it (hence ``S11_ERROR_FLOOR``).
    """
    meds = []
    for s in sweeps:
        if s is None:
            continue
        r = np.abs(second_difference(s))[1:-1]
        r = r[np.isfinite(r)]
        if r.size:
            meds.append(float(np.median(r)))
    return float(np.median(meds)) if meds else 0.0


def _local_noise(abs_r: np.ndarray, half_window: int) -> np.ndarray:
    """Median of |r| around each point, skipping the point and its two neighbours."""
    n = abs_r.size
    scale = np.full(n, np.nan)
    for i in range(1, n - 1):
        lo, hi = max(1, i - half_window), min(n - 1, i + half_window + 1)
        window = np.concatenate([abs_r[lo:max(lo, i - 1)], abs_r[min(hi, i + 2):hi]])
        window = window[np.isfinite(window)]
        if window.size:
            scale[i] = float(np.median(window))
    return scale


def spike_ratio(s11: np.ndarray, half_window: int = SPIKE_HALF_WINDOW) -> np.ndarray:
    """|second difference| over the local noise, per point (NaN at the ends)."""
    abs_r = np.abs(second_difference(s11))
    with np.errstate(divide="ignore", invalid="ignore"):
        return abs_r / _local_noise(abs_r, half_window)


def find_spikes(
    s11: np.ndarray,
    *,
    k: float = SPIKE_K,
    isolation: float = SPIKE_ISOLATION,
    min_abs: float = S11_ERROR_FLOOR,
    half_window: int = SPIKE_HALF_WINDOW,
) -> np.ndarray:
    """
    Indices of isolated single-point spikes of one sweep.

    A point is a spike when its second difference is above ``k`` times the
    local noise, above ``min_abs`` (smaller deviations are inside the S11
    error budget and cannot matter) and above ``isolation`` times both
    neighbours' second differences (a step or a 2-point glitch fails this).
    """
    s11 = np.asarray(s11, dtype=complex)
    if s11.size < 5:
        return np.zeros(0, dtype=int)
    abs_r = np.abs(second_difference(s11))
    noise = _local_noise(abs_r, half_window)
    neighbours = np.zeros_like(abs_r)
    neighbours[1:-1] = np.maximum(abs_r[:-2], abs_r[2:])
    with np.errstate(invalid="ignore"):
        hit = ((abs_r > k * noise) & (abs_r > min_abs)
               & (abs_r > isolation * neighbours))
    hit[[0, -1]] = False
    return np.flatnonzero(hit)


@dataclass
class DespikeRecord:
    """
    What spike removal did to one sweep.

    Attributes
    ----------
    s11 : np.ndarray
        The processed sweep (a copy; equal to the input when nothing changed).
    replaced : np.ndarray
        Int indices replaced by the mean of their neighbours.
    changes : np.ndarray
        |Delta S11| applied at each replaced index.
    kept_common : np.ndarray
        Int indices that looked like spikes but are shared with other sweeps
        (instrument artefacts the calibration cancels); left untouched.
    """

    s11: np.ndarray
    replaced: np.ndarray
    changes: np.ndarray
    kept_common: np.ndarray

    def to_metadata(self, f_hz: np.ndarray) -> Dict:
        """JSON-friendly summary (frequencies in Hz) for kits, reports and the UI."""
        f_hz = np.asarray(f_hz, dtype=float)
        return {
            "replaced_hz": [float(f_hz[i]) for i in self.replaced],
            "changes": [float(c) for c in self.changes],
            "kept_common_hz": [float(f_hz[i]) for i in self.kept_common],
        }


def despike_sweeps(
    sweeps: Mapping[str, np.ndarray],
    *,
    context: Optional[Mapping[str, np.ndarray]] = None,
    k: float = SPIKE_K,
    isolation: float = SPIKE_ISOLATION,
    min_abs: float = S11_ERROR_FLOOR,
    common_k: float = SPIKE_COMMON_K,
    half_window: int = SPIKE_HALF_WINDOW,
) -> Dict[str, DespikeRecord]:
    """
    Joint noise-based spike removal over sweeps that share a frequency grid.

    EN: Each sweep in ``sweeps`` is searched with ``find_spikes``. A spike
        is replaced by the mean of its two neighbours unless another sweep
        -- of ``sweeps`` or of ``context`` (sweeps that are compared but not
        processed, e.g. the standards when despiking the sample) -- is also
        at least ``common_k`` local-noise units off at that point: then it is
        an instrument artefact shared by the sweeps, which the calibration
        cancels, and it is kept.
    ES: Cada barrido de ``sweeps`` se revisa con ``find_spikes``. Un pico se
        reemplaza por el promedio de sus dos vecinos salvo que otro barrido
        -- de ``sweeps`` o de ``context`` (barridos que se comparan pero no se
        procesan, p. ej. los patrones al procesar la muestra) -- tambien este
        al menos ``common_k`` unidades de ruido local corrido en ese punto:
        entonces es un artefacto del instrumento que comparten los barridos,
        que la calibracion cancela, y se conserva.
    """
    arrays = {key: np.asarray(s, dtype=complex) for key, s in sweeps.items()}
    others = dict(arrays)
    for key, s in (context or {}).items():
        others.setdefault(f"context:{key}", np.asarray(s, dtype=complex))
    ratios = {key: spike_ratio(s, half_window) for key, s in others.items()}

    records: Dict[str, DespikeRecord] = {}
    for key, s in arrays.items():
        out = s.copy()
        replaced, changes, kept = [], [], []
        for i in find_spikes(s, k=k, isolation=isolation, min_abs=min_abs,
                             half_window=half_window):
            shared = any(
                other != key and ratio.size == s.size and ratio[i] >= common_k
                for other, ratio in ratios.items()
            )
            if shared:
                kept.append(i)
                continue
            out[i] = 0.5 * (s[i - 1] + s[i + 1])
            replaced.append(i)
            changes.append(abs(out[i] - s[i]))
        records[key] = DespikeRecord(
            s11=out,
            replaced=np.asarray(replaced, dtype=int),
            changes=np.asarray(changes, dtype=float),
            kept_common=np.asarray(kept, dtype=int),
        )
    return records


# --------------------------------------------------------------------------- #
# Sensitivity
# --------------------------------------------------------------------------- #

def _model_gamma(eps: np.ndarray, f_hz: np.ndarray, c0_f: float) -> np.ndarray:
    """S11 of the capacitive probe model, Y = j*w*C0*eps."""
    y = 1j * 2.0 * np.pi * f_hz * c0_f * Z0_OHM * eps
    return (1.0 - y) / (1.0 + y)


def _first_run_start(ok: np.ndarray, run: int) -> Optional[int]:
    """First index starting ``run`` consecutive True (or a True tail to the end)."""
    n = ok.size
    for i in range(n):
        if ok[i:min(n, i + run)].all():
            return i
    return None


@dataclass
class SensitivityCheck:
    """
    Per-frequency information content of the sweep (see the module docstring).

    Attributes
    ----------
    f_hz : np.ndarray
        Frequency grid.
    s11_error : float
        S11 error sigma the checks are made against.
    eps_resolution : np.ndarray
        eps error per sigma that the reference separation allows (inf where
        the references coincide).
    ref_inconsistency : np.ndarray | None
        Relative departure of |S_a - S_b| from the probe model's frequency
        shape, (measured/model) / (its median over the trusted band) - 1,
        evaluated below the trusted band (NaN elsewhere); None without a
        known probe or a trusted band.
    dut_contrast : np.ndarray | None
        |S_dut - S_open| / sigma (None without a sample).
    resolution_ok, consistent : np.ndarray
        Bool per point: eps_resolution <= EPS_RESOLUTION_MAX; reference
        separation within REF_CONSISTENCY_TOL of the model shape (True where
        not evaluated).
    ref_ok, dut_ok, usable : np.ndarray
        Bool per point: reference checks passed (both above), sample check
        passed, everything.
    f_min_hz : float | None
        Start of the usable band: first point of MIN_USABLE_RUN consecutive
        usable points (None if there is none).
    f_min_ref_hz : float | None
        The same from the reference checks only (a calibration property).
    model_capped : bool
        True when the separation was capped by the probe model (known C0).
    reference_pair : str
        "ref1-ref2" (full method) or "ref1-air" (simplified method).
    """

    f_hz: np.ndarray
    s11_error: float
    eps_resolution: np.ndarray
    dut_contrast: Optional[np.ndarray]
    ref_ok: np.ndarray
    dut_ok: np.ndarray
    usable: np.ndarray
    f_min_hz: Optional[float]
    f_min_ref_hz: Optional[float]
    model_capped: bool
    reference_pair: str = "ref1-ref2"
    resolution_ok: Optional[np.ndarray] = None
    consistent: Optional[np.ndarray] = None
    ref_inconsistency: Optional[np.ndarray] = None

    @property
    def low_mask(self) -> np.ndarray:
        """Bool per point: True where the point fails the check."""
        return ~self.usable


def _reference_inconsistency(
    f_hz: np.ndarray,
    separation: np.ndarray,
    model_separation: np.ndarray,
    eps_resolution: np.ndarray,
    eps_a: np.ndarray,
    eps_b: np.ndarray,
    c0_f: float,
) -> Optional[np.ndarray]:
    """
    Departure of the measured reference separation from the probe model's shape.

    EN: Inside the trusted band (eps_resolution <= EPS_RESOLUTION_TRUSTED and
        the capacitive regime w*C0*Z0*|eps| < 0.5) the ratio measured/model is
        nearly constant -- its level only says how far the true C0 is from
        the stored one (1.26 on the 3 mm NanoVNA set). Below that band the
        ratio is compared with its median there; NaN elsewhere. None if the
        band has fewer than 3 points.
    ES: Dentro de la banda confiable (eps_resolution <= EPS_RESOLUTION_TRUSTED
        y el regimen capacitivo w*C0*Z0*|eps| < 0.5) el cociente medido/modelo
        es casi constante -- su nivel solo dice cuanto se aparta el C0 real del
        guardado (1.26 en el set NanoVNA de 3 mm). Por debajo de esa banda el
        cociente se compara con su mediana ahi; NaN en el resto. None si la
        banda tiene menos de 3 puntos.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = separation / model_separation
    regime = (2.0 * np.pi * f_hz * c0_f * Z0_OHM
              * np.maximum(np.abs(eps_a), np.abs(eps_b))) < _MODEL_REGIME_MAX
    trusted = regime & (eps_resolution <= EPS_RESOLUTION_TRUSTED) & np.isfinite(ratio)
    if np.count_nonzero(trusted) < 3:
        return None
    ratio_ref = float(np.median(ratio[trusted]))
    below = f_hz < f_hz[np.flatnonzero(trusted)[0]]
    return np.where(below, ratio / ratio_ref - 1.0, np.nan)


def check_sensitivity(
    f_hz: np.ndarray,
    s11_open: np.ndarray,
    s11_ref1: np.ndarray,
    eps_ref1: np.ndarray,
    *,
    s11_ref2: Optional[np.ndarray] = None,
    eps_ref2: Optional[np.ndarray] = None,
    s11_dut: Optional[np.ndarray] = None,
    c0_f: Optional[float] = None,
    s11_error: float = S11_ERROR_FLOOR,
    eps_resolution_max: float = EPS_RESOLUTION_MAX,
    dut_contrast_min: float = DUT_CONTRAST_MIN,
    consistency_tol: float = REF_CONSISTENCY_TOL,
) -> SensitivityCheck:
    """
    Where the sweep carries usable information (see the module docstring).

    EN: The reference pair is ref1/ref2, or ref1/air (``s11_open``,
        eps = 1.0006) when ``s11_ref2`` is None (simplified method).
        ``eps_resolution = sigma * |eps_a - eps_b| / separation``; with
        ``c0_f`` the separation is min(measured, probe model) and the
        separation must also keep the model's frequency shape below the
        trusted band (``_reference_inconsistency``). A point is usable when
        the resolution is within ``eps_resolution_max``, the separation is
        consistent and the sample is at least ``dut_contrast_min`` sigma from
        air.
    ES: El par de referencia es ref1/ref2, o ref1/aire (``s11_open``,
        eps = 1.0006) cuando ``s11_ref2`` es None (metodo simplificado).
        ``eps_resolution = sigma * |eps_a - eps_b| / separacion``; con
        ``c0_f`` la separacion es min(medida, modelo de la sonda) y ademas
        tiene que conservar la forma en frecuencia del modelo por debajo de la
        banda confiable (``_reference_inconsistency``). Un punto es utilizable
        cuando la resolucion no supera ``eps_resolution_max``, la separacion es
        consistente y la muestra esta al menos ``dut_contrast_min`` sigma del
        aire.
    """
    f_hz = np.asarray(f_hz, dtype=float)
    s_open = np.asarray(s11_open, dtype=complex)
    s_a = np.asarray(s11_ref1, dtype=complex)
    eps_a = np.asarray(eps_ref1, dtype=complex)
    if s11_ref2 is None:
        s_b, eps_b = s_open, np.full(f_hz.shape, _EPS_AIR, dtype=complex)
    else:
        s_b = np.asarray(s11_ref2, dtype=complex)
        eps_b = np.asarray(eps_ref2, dtype=complex)

    measured = np.abs(s_a - s_b)
    separation = measured
    model_capped = c0_f is not None and c0_f > 0
    inconsistency = None
    if model_capped:
        model = np.abs(_model_gamma(eps_a, f_hz, c0_f) - _model_gamma(eps_b, f_hz, c0_f))
        separation = np.minimum(measured, model)
    with np.errstate(divide="ignore", invalid="ignore"):
        eps_resolution = np.where(separation > 0.0,
                                  s11_error * np.abs(eps_a - eps_b) / separation, np.inf)
    eps_resolution = np.where(np.isfinite(eps_resolution), eps_resolution, np.inf)
    resolution_ok = eps_resolution <= eps_resolution_max
    if model_capped:
        inconsistency = _reference_inconsistency(
            f_hz, measured, model, eps_resolution, eps_a, eps_b, c0_f)
    with np.errstate(invalid="ignore"):
        consistent = (np.ones(f_hz.shape, dtype=bool) if inconsistency is None
                      else ~(np.abs(inconsistency) > consistency_tol))
    ref_ok = resolution_ok & consistent

    if s11_dut is None:
        dut_contrast = None
        dut_ok = np.ones(f_hz.shape, dtype=bool)
    else:
        dut_contrast = np.abs(np.asarray(s11_dut, dtype=complex) - s_open) / s11_error
        with np.errstate(invalid="ignore"):
            dut_ok = dut_contrast >= dut_contrast_min

    usable = ref_ok & dut_ok
    i_min = _first_run_start(usable, MIN_USABLE_RUN)
    i_ref = _first_run_start(ref_ok, MIN_USABLE_RUN)
    return SensitivityCheck(
        f_hz=f_hz,
        s11_error=float(s11_error),
        eps_resolution=eps_resolution,
        dut_contrast=dut_contrast,
        ref_ok=ref_ok,
        dut_ok=dut_ok,
        usable=usable,
        f_min_hz=None if i_min is None else float(f_hz[i_min]),
        f_min_ref_hz=None if i_ref is None else float(f_hz[i_ref]),
        model_capped=bool(model_capped),
        reference_pair="ref1-air" if s11_ref2 is None else "ref1-ref2",
        resolution_ok=resolution_ok,
        consistent=consistent,
        ref_inconsistency=inconsistency,
    )


def _fmt_resolution(value: float) -> str:
    if not np.isfinite(value):
        return "∞"
    return f"{value:.0f}" if value >= 100 else f"{value:.3g}"


def _fmt_deg(value: float) -> str:
    return f"{value:.0f}°".replace("-", "−")


def _fmt_pct(value: float) -> str:
    if not np.isfinite(value):
        return "∞"
    return (f"{value:+.0%}" if abs(value) < 10 else f"×{value + 1:.0f}").replace("-", "−")


def _pair_text(chk: SensitivityCheck) -> str:
    return ("the reference liquid and air" if chk.reference_pair == "ref1-air"
            else "the reference liquids")


def _span(f, values, idx, fmt, pick_worst) -> str:
    """"<worst> at <f> … <last> at <f>" over the points ``idx``."""
    worst = int(idx[pick_worst(values[idx])])
    last = int(idx[-1])
    text = f"{fmt(values[worst])} at {_fmt_hz(f[worst])}"
    if last != worst:
        text += f" … {fmt(values[last])} at {_fmt_hz(f[last])}"
    return text


def sensitivity_warnings(
    chk: SensitivityCheck,
    probe_label: str = "",
    eps_resolution_max: float = EPS_RESOLUTION_MAX,
    dut_contrast_min: float = DUT_CONTRAST_MIN,
    consistency_tol: float = REF_CONSISTENCY_TOL,
) -> List[str]:
    """Plain-text warnings for a ``SensitivityCheck`` (empty when every point passes)."""
    f = chk.f_hz
    fail = chk.low_mask
    if not np.any(fail):
        return []
    context = f"{probe_label}, " if probe_label else ""
    context += f"S11 error σ = {chk.s11_error:.1e}"
    resolution_ok = chk.resolution_ok if chk.resolution_ok is not None else chk.ref_ok
    consistent = (chk.consistent if chk.consistent is not None
                  else np.ones(f.shape, dtype=bool))

    if chk.f_min_hz is None:
        below = fail
        head = (f"Unreliable over the whole sweep ({context}): no stretch of "
                f"{MIN_USABLE_RUN} consecutive points passes the check.")
    elif not np.any(fail & (f < chk.f_min_hz)):
        above = np.flatnonzero(fail)
        return [f"{above.size} isolated point(s) are unreliable ({context}; first at "
                f"{_fmt_hz(f[above[0]])}): there {_pair_text(chk)} resolve εr worse than "
                f"±{eps_resolution_max:g} per σ, separate unlike the probe model or the "
                f"sample differs from air by less than {dut_contrast_min:g}σ. Values kept, "
                f"left out of the chart scale and of the summary medians."]
    else:
        below = fail & (f < chk.f_min_hz)
        head = (f"Unreliable below {_fmt_hz(chk.f_min_hz)}: "
                f"{int(np.count_nonzero(below))} point(s) ({context}).")

    parts = []
    res_bad = below & ~resolution_ok
    if np.any(res_bad):
        span = _span(f, chk.eps_resolution, np.flatnonzero(res_bad),
                     lambda v: f"±{_fmt_resolution(v)}", np.argmax)
        parts.append(f"{_pair_text(chk)} resolve εr only to {span} per σ "
                     f"(usable: ≤ ±{eps_resolution_max:g})")
    cons_bad = below & ~consistent
    if np.any(cons_bad) and chk.ref_inconsistency is not None:
        span = _span(f, chk.ref_inconsistency, np.flatnonzero(cons_bad),
                     _fmt_pct, lambda v: np.argmax(np.abs(v)))
        parts.append(f"{_pair_text(chk)} separate {span} unlike the probe model "
                     f"(tolerance ±{consistency_tol:.0%}): the S11 there is not the "
                     f"probe's (smoothing, drift or calibration error) and the sample's "
                     f"εr drifts by about as much")
    dut_bad = below & ~chk.dut_ok
    if np.any(dut_bad):
        parts.append(f"the sample differs from air by less than {dut_contrast_min:g}σ "
                     f"(|S11_dut − S11_open|) at {int(np.count_nonzero(dut_bad))} of them")
    msg = head
    if parts:
        msg += " There " + "; ".join(parts) + "."
    msg += " Values kept, but left out of the chart scale and of the summary medians"
    if chk.f_min_hz is not None:
        msg += f"; start the sweep at ≥ {_fmt_hz(chk.f_min_hz)}."
        above = fail & (f >= chk.f_min_hz)
        if np.any(above):
            first = int(np.flatnonzero(above)[0])
            msg += (f" {int(np.count_nonzero(above))} isolated point(s) above it fail "
                    f"the same check (first at {_fmt_hz(f[first])}).")
    else:
        msg += "."
    return [msg]
# --------------------------------------------------------------------------- #
# Gn
# --------------------------------------------------------------------------- #

@dataclass
class GnCheck:
    """
    Whether Gn behaves like radiation on the upper octave of the sweep.

    Attributes
    ----------
    band_hz : tuple(float, float)
        Frequency band judged (the upper octave of the usable sweep).
    median_arg_deg : float
        Circular mean of arg(Gn) over the band, degrees (radiation: -90).
    phase_dev_deg : float
        Median |arg(Gn) + 90 deg| over the band.
    slope : float
        Exponent k of |Gn| ~ f^k fitted over the band (radiation: 3); NaN if
        the band spans less than a factor 1.5 in frequency.
    radiation_like : bool
        phase_dev_deg <= GN_PHASE_TOL_DEG and slope >= GN_SLOPE_MIN.
    ref_weight : float
        Median |Gn * eps_ref^1.5| over the usable sweep for the reference of
        largest |eps|: the relative weight of the Gn term in its admittance.
    ref_index : int
        Which reference ``ref_weight`` refers to (0 = ref1, 1 = ref2).
    """

    band_hz: tuple
    median_arg_deg: float
    phase_dev_deg: float
    slope: float
    radiation_like: bool
    ref_weight: float
    ref_index: int


def check_gn(
    f_hz: np.ndarray,
    gn: np.ndarray,
    eps_refs: Sequence[np.ndarray],
    *,
    f_min_hz: Optional[float] = None,
    phase_tol_deg: float = GN_PHASE_TOL_DEG,
    slope_min: float = GN_SLOPE_MIN,
) -> Optional[GnCheck]:
    """
    Phase/scaling check of Gn on the upper octave (None if too few points).

    EN: Radiation grows ~f^3, so the top of the sweep is where it is most
        visible; the band is [f_top/2, f_top] of the points above
        ``f_min_hz`` with a finite Gn (the top ``_GN_MIN_POINTS`` points if
        that octave holds fewer).
    ES: La radiacion crece ~f^3, asi que el extremo alto del barrido es donde
        mas se ve; la banda es [f_top/2, f_top] de los puntos por encima de
        ``f_min_hz`` con Gn finito (los ``_GN_MIN_POINTS`` puntos superiores
        si esa octava tiene menos).
    """
    f_hz = np.asarray(f_hz, dtype=float)
    gn = np.asarray(gn, dtype=complex)
    ok = np.isfinite(gn) & (np.abs(gn) > 0.0) & (f_hz > 0.0)
    if f_min_hz is not None:
        ok &= f_hz >= f_min_hz
    idx = np.flatnonzero(ok)
    if idx.size < _GN_MIN_POINTS:
        return None
    f_top = float(f_hz[idx[-1]])
    band = idx[f_hz[idx] >= f_top / 2.0]
    if band.size < _GN_MIN_POINTS:
        band = idx[-_GN_MIN_POINTS:]

    g = gn[band]
    phase_dev = float(np.median(np.abs(np.degrees(np.angle(g * 1j)))))
    median_arg = float(np.degrees(np.angle(np.sum(g / np.abs(g)))))
    f_band = f_hz[band]
    if f_band[-1] / f_band[0] >= 1.5:
        slope = float(np.polyfit(np.log(f_band), np.log(np.abs(g)), 1)[0])
    else:
        slope = float("nan")
    radiation_like = phase_dev <= phase_tol_deg and not (slope < slope_min)

    weights = []
    for eps in eps_refs:
        if eps is None:
            weights.append(-np.inf)
            continue
        eps = np.asarray(eps, dtype=complex)[idx]
        w = np.abs(gn[idx]) * np.abs(eps) ** 1.5
        w = w[np.isfinite(w)]
        weights.append(float(np.median(w)) if w.size else -np.inf)
    ref_index = int(np.argmax(weights))

    return GnCheck(
        band_hz=(float(f_band[0]), float(f_band[-1])),
        median_arg_deg=median_arg,
        phase_dev_deg=phase_dev,
        slope=slope,
        radiation_like=bool(radiation_like),
        ref_weight=max(float(weights[ref_index]), 0.0),
        ref_index=ref_index,
    )


def gn_warnings(chk: Optional[GnCheck], ref_labels: Sequence[str] = ("ref1", "ref2")) -> List[str]:
    """Plain-text warning when Gn is not radiation-like (empty otherwise)."""
    if chk is None or chk.radiation_like:
        return []
    lo, hi = chk.band_hz
    slope = "?" if not np.isfinite(chk.slope) else f"{chk.slope:.1f}"
    label = ref_labels[chk.ref_index] if chk.ref_index < len(ref_labels) else "reference"
    return [
        f"Gn shows no radiation signature even at the top of the sweep "
        f"({_fmt_hz(lo)} – {_fmt_hz(hi)}): mean arg(Gn) = {_fmt_deg(chk.median_arg_deg)} "
        f"(radiation: −90°, median deviation {_fmt_deg(chk.phase_dev_deg)}) and |Gn| ∝ "
        f"f^{slope.replace('-', '−')} (radiation: f^3). Over the whole sweep it holds noise and the "
        f"inconsistency between the reference liquids instead (its term is "
        f"≈{chk.ref_weight:.0%} of the {label} admittance), so the full method's "
        f"radiation correction is empirical here: compare with the simplified "
        f"cross-check, especially for samples whose εr lies outside the range of "
        f"the reference liquids."
    ]


# --------------------------------------------------------------------------- #
# Passivity
# --------------------------------------------------------------------------- #

@dataclass
class PassivityCheck:
    """
    Sweeps with |S11| > 1 + tol.

    ``offenders`` maps each offending sweep key to a dict with ``n`` (points),
    ``peak`` (max |S11|), ``f_peak_hz`` and ``f_first_hz``; ``mask`` is True
    where any sweep is non-passive.
    """

    tol: float
    offenders: Dict[str, Dict] = field(default_factory=dict)
    mask: Optional[np.ndarray] = None


def check_passivity(
    f_hz: np.ndarray,
    sweeps: Mapping[str, Optional[np.ndarray]],
    *,
    tol: float = S11_PASSIVE_TOL,
) -> PassivityCheck:
    """Find the sweeps whose |S11| exceeds 1 + ``tol`` (a passive load cannot)."""
    f_hz = np.asarray(f_hz, dtype=float)
    mask = np.zeros(f_hz.shape, dtype=bool)
    offenders: Dict[str, Dict] = {}
    for key, s in sweeps.items():
        if s is None:
            continue
        mag = np.abs(np.asarray(s, dtype=complex))
        with np.errstate(invalid="ignore"):
            over = mag > 1.0 + tol
        if mag.shape != f_hz.shape or not np.any(over):
            continue
        mask |= over
        i_peak = int(np.nanargmax(mag))
        offenders[key] = {
            "n": int(np.count_nonzero(over)),
            "peak": float(mag[i_peak]),
            "f_peak_hz": float(f_hz[i_peak]),
            "f_first_hz": float(f_hz[np.flatnonzero(over)[0]]),
        }
    return PassivityCheck(tol=float(tol), offenders=offenders, mask=mask)


def passivity_warnings(chk: PassivityCheck, labels: Optional[Mapping[str, str]] = None) -> List[str]:
    """One plain-text warning listing every non-passive sweep (empty if none)."""
    if not chk.offenders:
        return []
    labels = labels or {}
    items = [
        f"{labels.get(key, key)} up to {o['peak']:.3f} at {_fmt_hz(o['f_peak_hz'])} "
        f"({o['n']} point(s) from {_fmt_hz(o['f_first_hz'])})"
        for key, o in chk.offenders.items()
    ]
    return [
        f"|S11| above {1.0 + chk.tol:g}, impossible for a passive load: "
        + "; ".join(items)
        + ". The VNA calibration (SOL) is off there and the results at those "
          "frequencies inherit that error; recalibrate the VNA over the band."
    ]


# --------------------------------------------------------------------------- #
# All checks together
# --------------------------------------------------------------------------- #

@dataclass
class QualityReport:
    """
    Every measurement-quality check of one computation.

    ``warnings`` holds the plain-text messages in display order (sensitivity,
    passivity, Gn); the rest keeps the numbers behind them.
    """

    s11_error: float
    sensitivity: Optional[SensitivityCheck]
    gn: Optional[GnCheck]
    passivity: PassivityCheck
    warnings: List[str]

    @property
    def low_sensitivity_mask(self) -> Optional[np.ndarray]:
        return None if self.sensitivity is None else self.sensitivity.low_mask

    @property
    def f_min_hz(self) -> Optional[float]:
        return None if self.sensitivity is None else self.sensitivity.f_min_hz


def assess_quality(
    f_hz: np.ndarray,
    *,
    s11_open: np.ndarray,
    s11_short: np.ndarray,
    s11_ref1: np.ndarray,
    eps_ref1: np.ndarray,
    s11_ref2: Optional[np.ndarray] = None,
    eps_ref2: Optional[np.ndarray] = None,
    s11_dut: Optional[np.ndarray] = None,
    gn: Optional[np.ndarray] = None,
    c0_f: Optional[float] = None,
    probe_label: str = "",
    labels: Optional[Mapping[str, str]] = None,
    s11_error: Optional[float] = None,
) -> QualityReport:
    """
    Run every check on one calibration (+ sample) and collect the warnings.

    EN: ``s11_error`` defaults to max(S11_ERROR_FLOOR, trace noise estimated
        from all sweeps). ``c0_f`` is the C0 of a KNOWN probe (None for the
        generic one, whose C0 is only an order of magnitude). ``gn`` is
        None for the simplified method (no Gn). ``labels`` names each sweep
        key (open, short, ref1, ref2, dut) in the messages.
    ES: ``s11_error`` vale por defecto max(S11_ERROR_FLOOR, ruido de traza
        estimado de todos los barridos). ``c0_f`` es el C0 de una sonda
        CONOCIDA (None para la generica, cuyo C0 es solo un orden de
        magnitud). ``gn`` es None en el metodo simplificado (sin Gn).
        ``labels`` nombra cada clave de barrido (open, short, ref1, ref2,
        dut) en los mensajes.
    """
    labels = dict(labels or {})
    sweeps = {"open": s11_open, "short": s11_short, "ref1": s11_ref1,
              "ref2": s11_ref2, "dut": s11_dut}
    if s11_error is None:
        s11_error = max(S11_ERROR_FLOOR, estimate_s11_noise(*sweeps.values()))

    sensitivity = check_sensitivity(
        f_hz, s11_open, s11_ref1, eps_ref1,
        s11_ref2=s11_ref2, eps_ref2=eps_ref2, s11_dut=s11_dut,
        c0_f=c0_f, s11_error=s11_error,
    )
    passivity = check_passivity(f_hz, sweeps)
    gn_check = None
    if gn is not None:
        gn_check = check_gn(f_hz, gn, [eps_ref1, eps_ref2],
                            f_min_hz=sensitivity.f_min_ref_hz)

    warnings: List[str] = []
    warnings += sensitivity_warnings(sensitivity, probe_label)
    warnings += passivity_warnings(passivity, labels)
    warnings += gn_warnings(gn_check, (labels.get("ref1", "ref1"), labels.get("ref2", "ref2")))
    for msg in warnings:
        logger.warning("[measurement_quality] %s", msg)

    return QualityReport(
        s11_error=float(s11_error),
        sensitivity=sensitivity,
        gn=gn_check,
        passivity=passivity,
        warnings=warnings,
    )
