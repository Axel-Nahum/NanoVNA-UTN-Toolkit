"""
Permittivity written as Touchstone, and the guards that keep it out of S11 inputs.

EN: Some users want the computed permittivity as a ``.s1p`` so any Touchstone
    viewer can plot it. That is exactly how the UTN 2021/2024 campaigns lost
    track of their data: eps_r saved with a ``.s1p`` extension was later taken
    for S11. So the export is written with an unmistakable header marker, and
    every S11 import path checks for that marker -- plus a magnitude sanity
    check that also catches the legacy files, which carry no marker.

ES: Algunos usuarios quieren la permitividad calculada como ``.s1p`` para
    graficarla con cualquier visor Touchstone. Asi es justamente como las
    campanas UTN 2021/2024 perdieron el rastro de sus datos: eps_r guardada con
    extension ``.s1p`` se tomo despues por S11. Por eso la exportacion lleva una
    marca inconfundible en el encabezado, y toda importacion de S11 la busca --
    ademas de un control de magnitud que tambien atrapa los archivos viejos, que
    no tienen marca.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

logger = logging.getLogger(__name__)

#: Header text that identifies a permittivity export. Never change it: files
#: already written rely on it to be rejected as S11.
PERMITTIVITY_MARKER = "NanoVNA-UTN-Toolkit permittivity export"

#: A passive one-port reflects at most what it receives (|S11| <= 1). Measured
#: data overshoots slightly (noise, calibration), so only a clear excess flags
#: a file as "not S11". Permittivities are >> 1 almost everywhere.
S11_PLAUSIBLE_MAX = 1.5

# The marker must sit in the leading comment block; no need to read further.
_HEADER_SCAN_LINES = 40


def write_permittivity_touchstone(
    path,
    f_hz,
    eps,
    *,
    sample_name: str = "",
    notes: Iterable[str] = (),
) -> int:
    """
    Write ``eps`` (complex, eps' - j*eps'' convention) as a Touchstone 1-port.

    Columns are frequency (Hz), eps' and eps'' (loss, positive) -- the same
    numbers the CSV export writes. Points without a solution (NaN gaps) are
    skipped, since Touchstone viewers choke on them. Returns the rows written.
    """
    f_hz = np.asarray(f_hz, dtype=float)
    eps = np.asarray(eps, dtype=complex)
    if f_hz.shape != eps.shape:
        raise ValueError(f"frequency grid {f_hz.shape} != permittivity {eps.shape}")

    finite = np.isfinite(f_hz) & np.isfinite(eps)
    n_skipped = int(np.count_nonzero(~finite))

    lines = [
        f"! {PERMITTIVITY_MARKER} -- NOT S-parameters",
        "! ES: Permitividad relativa compleja de la muestra. NO es S11: se guarda en",
        "! ES: formato Touchstone solo para poder graficarla con visores de .s1p.",
        "! EN: Complex relative permittivity of the sample. NOT S11: the Touchstone",
        "! EN: format is used only so that .s1p viewers can plot it.",
        "! Columns / Columnas: f (Hz) | eps' | eps'' (loss >= 0); eps_r = eps' - j*eps''",
    ]
    if sample_name:
        lines.append(f"! Sample / Muestra: {sample_name}")
    lines.extend(f"! {note}" for note in notes)
    if n_skipped:
        lines.append(f"! {n_skipped} point(s) without a solution omitted / "
                     f"{n_skipped} punto(s) sin solucion omitidos")
    lines.append(f"! Exported / Exportado: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("# Hz S RI R 50")

    for f, e in zip(f_hz[finite], eps[finite]):
        lines.append(f"{f:.6f} {e.real:.6f} {-e.imag:.6f}")

    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows = int(np.count_nonzero(finite))
    logger.info("[permittivity_touchstone] wrote %d rows (%d skipped) to %s", rows, n_skipped, path)
    return rows


def is_permittivity_touchstone(path) -> bool:
    """True when ``path`` carries the permittivity-export marker in its header."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i >= _HEADER_SCAN_LINES:
                    break
                stripped = line.strip()
                if stripped.startswith("!") and PERMITTIVITY_MARKER.lower() in stripped.lower():
                    return True
    except OSError:
        return False
    return False


def implausible_s11_peak(s11) -> Optional[float]:
    """Return max |S11| when it is too large for a reflection coefficient, else None."""
    mag = np.abs(np.asarray(s11, dtype=complex))
    mag = mag[np.isfinite(mag)]
    if mag.size == 0:
        return None
    peak = float(mag.max())
    return peak if peak > S11_PLAUSIBLE_MAX else None


def implausible_s11_reason(s11) -> Optional[str]:
    """Plain-text reason to reject ``s11`` as a reflection coefficient, or None."""
    peak = implausible_s11_peak(s11)
    if peak is None:
        return None
    return (f"|S11| reaches {peak:.3g}, but a reflection coefficient stays near or "
            f"below 1: the file does not look like S11 (it may hold permittivity).")
