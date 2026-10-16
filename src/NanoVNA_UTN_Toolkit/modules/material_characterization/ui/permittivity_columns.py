"""
Columns of the selected permittivity, shared by every chart, table and export.

EN: Convention eps_r = eps' - j*eps'', stored as complex with Im(eps) = -eps''.
    Every consumer shows eps' and eps'' = -Im(eps), so a passive point has
    eps'' >= 0 and a non-passive one (eps'' < 0, attributable to noise) keeps
    its sign instead of being hidden by abs(). A point without a solution (a
    gap) is NaN in BOTH columns, whatever the solver stored there
    (``nan+0j`` or ``complex(nan, nan)``): it must never show up as 0.000 in
    eps'' nor be filled in by interpolation.

ES: Convencion eps_r = eps' - j*eps'', guardada como complejo con
    Im(eps) = -eps''. Todos los consumidores muestran eps' y eps'' = -Im(eps),
    asi un punto pasivo tiene eps'' >= 0 y uno no pasivo (eps'' < 0, atribuible
    al ruido) conserva su signo en vez de quedar oculto por abs(). Un punto sin
    solucion (gap) es NaN en AMBAS columnas, sea cual sea lo que guardo el
    solver (``nan+0j`` o ``complex(nan, nan)``): nunca debe aparecer como 0.000
    en eps'' ni rellenarse por interpolacion.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

#: Header of the permittivity CSV. "Epsilon_imag" holds eps'' = -Im(eps) (the
#: loss, >= 0 for a passive point); the name is kept for existing readers.
CSV_HEADER = ("Frequency (Hz)", "Epsilon_real", "Epsilon_imag")


def permittivity_columns(eps) -> Tuple[np.ndarray, np.ndarray]:
    """
    Split ``eps`` into ``(eps', eps'')`` with ``eps'' = -Im(eps)``.

    Both arrays are float (n_freq,) and NaN together wherever ``eps`` is not
    finite (a gap), so the two columns can never disagree about a gap.
    """
    eps = np.asarray(eps, dtype=complex)
    gap = ~np.isfinite(eps)  # complex isfinite: False when either part is nan/inf
    eps_real = np.real(eps).copy()
    eps_loss = -np.imag(eps)
    eps_real[gap] = np.nan
    eps_loss[gap] = np.nan
    return eps_real, eps_loss


def loss_tangent(eps_real: np.ndarray, eps_loss: np.ndarray) -> np.ndarray:
    """Signed ``tan(delta) = eps''/eps'``; NaN at gaps or where eps' is 0.

    Negative values flag non-passive points: they are reported, not hidden.
    """
    eps_real = np.asarray(eps_real, dtype=float)
    eps_loss = np.asarray(eps_loss, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        tand = np.where(eps_real != 0.0, eps_loss / eps_real, np.nan)
    tand[~np.isfinite(tand)] = np.nan
    return tand


def nonpassive_mask_of(result) -> Optional[np.ndarray]:
    """
    The solver's non-physical flag (bool per frequency), or None.

    Both solvers flag eps'' < 0 (non-passive) or eps' < 1 (below vacuum);
    user-facing texts say so.

    Read with ``getattr`` so results without the field keep working. A mask
    whose shape does not match ``eps_selected`` is ignored (logged), never
    applied to the wrong points.
    """
    mask = getattr(result, "nonpassive_mask", None)
    if mask is None:
        return None
    mask = np.asarray(mask, dtype=bool)
    eps = getattr(result, "eps_selected", None)
    if eps is not None and mask.shape != np.shape(eps):
        logger.warning(
            "[permittivity_columns] nonpassive_mask shape %s != eps_selected %s; ignored",
            mask.shape, np.shape(eps),
        )
        return None
    return mask


def usable_band_of(result) -> Tuple[Optional[np.ndarray], Optional[float]]:
    """
    ``(usable_mask, f_min_hz)`` from the result's measurement-quality checks.

    EN: ``usable_mask`` is True where the point passed the sensitivity check
        (None without checks or on a shape mismatch); ``f_min_hz`` is the
        start of the usable band, or None when it is the first point (nothing
        to shade). Read with ``getattr`` so older results keep working.
    ES: ``usable_mask`` es True donde el punto paso el control de
        sensibilidad (None sin controles o si la forma no coincide);
        ``f_min_hz`` es el comienzo de la banda util, o None cuando es el
        primer punto (no hay nada que sombrear).
    """
    sens = getattr(getattr(result, "quality", None), "sensitivity", None)
    if sens is None:
        return None, None
    mask = np.asarray(sens.usable, dtype=bool)
    f_hz = np.asarray(getattr(result, "f_hz", sens.f_hz), dtype=float)
    if mask.shape != f_hz.shape:
        logger.warning("[permittivity_columns] usable mask shape %s != f_hz %s; ignored",
                       mask.shape, f_hz.shape)
        return None, None
    f_min = sens.f_min_hz
    if f_min is None or f_min <= float(f_hz[0]):
        f_min = None
    return mask, (None if f_min is None else float(f_min))


def scale_limits(eps, usable: Optional[np.ndarray] = None,
                 margin: float = 0.06) -> Optional[Tuple[float, float]]:
    """
    y-limits that fit eps' and eps'' of the usable points only.

    EN: Points that failed the quality checks stay on the chart (they may run
        off it) but never set its scale: one diverging value at 50 kHz must
        not flatten the rest of the curve. None when no usable point is
        finite (the caller then keeps its own limits).
    ES: Los puntos que no pasaron los controles quedan en el grafico (pueden
        salirse) pero nunca fijan su escala: un valor divergente a 50 kHz no
        tiene que aplastar el resto de la curva. None cuando ningun punto
        utilizable es finito (el llamador conserva sus propios limites).
    """
    eps_real, eps_loss = permittivity_columns(eps)
    values = np.concatenate([eps_real, eps_loss])
    values = values[np.isfinite(values)]
    if values.size == 0:
        return None
    lo, hi = float(values.min()), float(values.max())
    pad = (hi - lo) * margin if hi > lo else max(1.0, abs(hi) * margin)
    return lo - pad, hi + pad


def shade_unusable_band(ax, x_start: float, x_end: float, label: str = "_nolegend_"):
    """Grey band over ``[x_start, x_end]`` (chart units) behind the curves."""
    return ax.axvspan(x_start, x_end, color="#9a9a9a", alpha=0.18, zorder=0, label=label)


def isolated_points(y: np.ndarray) -> np.ndarray:
    """Bool mask of finite samples whose two neighbours are both NaN/missing.

    A line plot draws nothing for such a sample (a one-point segment has no
    length), so charts mark them explicitly to keep real data visible next
    to the gaps.
    """
    finite = np.isfinite(np.asarray(y, dtype=float))
    prev_ok = np.concatenate(([False], finite[:-1]))
    next_ok = np.concatenate((finite[1:], [False]))
    return finite & ~prev_ok & ~next_ok


def plot_with_gaps(ax, x, y, **line_kwargs):
    """``ax.plot`` that leaves gaps (NaN) as breaks and marks isolated points.

    Returns the main Line2D. The isolated-point markers reuse the line color
    and stay out of the legend.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    line, = ax.plot(x, y, **line_kwargs)
    lonely = isolated_points(y)
    if np.any(lonely):
        ax.plot(
            x[lonely], y[lonely], linestyle="none", marker="o",
            markersize=max(2.5, float(line.get_linewidth()) * 1.6),
            color=line.get_color(), alpha=line.get_alpha(),
            zorder=line.get_zorder(), label="_nolegend_",
        )
    return line


def write_permittivity_csv(path, f_hz, eps) -> int:
    """
    Write ``Frequency (Hz) | eps' | eps''`` rows (``eps'' = -Im(eps)``).

    Every frequency gets a row so the grid stays intact; a gap is written as
    ``nan`` in both permittivity columns (parsed as NaN by numpy, pandas and
    spreadsheet imports). Returns the number of rows with a solution.
    """
    f_hz = np.asarray(f_hz, dtype=float)
    eps_real, eps_loss = permittivity_columns(eps)
    if f_hz.shape != eps_real.shape:
        raise ValueError(f"frequency grid {f_hz.shape} != permittivity {eps_real.shape}")

    with open(Path(path), "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_HEADER)
        for freq, er, el in zip(f_hz, eps_real, eps_loss):
            writer.writerow([f"{freq:.4f}", f"{er:.6f}", f"{el:.6f}"])

    n_valid = int(np.count_nonzero(np.isfinite(eps_real)))
    logger.info("[permittivity_columns] wrote CSV %s (%d rows, %d gaps)",
                path, f_hz.size, f_hz.size - n_valid)
    return n_valid
