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

    The full solver flags eps'' < 0; the simplified one eps'' < 0 or
    eps' <= 0. User-facing texts word it so it holds for both.

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
