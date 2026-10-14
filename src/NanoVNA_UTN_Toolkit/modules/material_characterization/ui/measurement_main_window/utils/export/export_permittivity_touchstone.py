"""
Export the computed permittivity as a Touchstone ``.s1p`` (for viewers only).

EN: Shared by the File menu, the results table and the chart export dialog.
    The file is written by ``calibration.permittivity_touchstone``, which tags
    it so it can never be re-imported as an S11 measurement.

ES: Lo comparten el menu Archivo, la tabla de resultados y el dialogo de
    exportacion del grafico. El archivo lo escribe
    ``calibration.permittivity_touchstone``, que lo marca para que nunca pueda
    volver a importarse como una medicion de S11.
"""

from __future__ import annotations

import logging

import numpy as np
from PySide6.QtWidgets import QFileDialog, QMessageBox

from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_touchstone import (
    write_permittivity_touchstone,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.permittivity_columns import (
    nonpassive_mask_of,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text

logger = logging.getLogger(__name__)


def _safe_stem(sample_name: str) -> str:
    stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in (sample_name or "")).strip()
    return stem or "sample"


def _nonpassive_note(result) -> list[str]:
    """Header line counting the flagged non-physical points kept in the file.

    The writer's column legend says eps'' >= 0; points the solver flags carry
    eps'' < 0 (full and simplified methods) or eps' <= 0 (simplified only)
    and are written as such, so say so.
    """
    mask = nonpassive_mask_of(result)
    if mask is None:
        return []
    eps = np.asarray(result.eps_selected, dtype=complex)
    n_flag = int(np.count_nonzero(mask & np.isfinite(eps)))
    if n_flag == 0:
        return []
    return [f"{n_flag} non-physical point(s) (eps'' < 0 or eps' <= 0) kept and flagged / "
            f"{n_flag} punto(s) no fisico(s) (eps'' < 0 o eps' <= 0) conservados y marcados"]


def export_permittivity_touchstone(parent, result, sample_name: str = "", notes=()) -> None:
    """Ask for a path and write ``result`` (eps_selected over f_hz) as ``<sample>_er.s1p``."""
    t = load_text("characterization_measurement_main.json").get("export", {})

    if result is None:
        QMessageBox.warning(parent, t.get("error_title", "Error"),
                            t.get("eps_s1p_no_data", "No permittivity data available."))
        return

    path, _ = QFileDialog.getSaveFileName(
        parent,
        t.get("eps_s1p_dialog_title", "Export permittivity as Touchstone"),
        f"{_safe_stem(sample_name)}_er.s1p",
        t.get("eps_s1p_filter", "Touchstone S1P (*.s1p);;All Files (*)"),
    )
    if not path:
        return

    try:
        write_permittivity_touchstone(
            path,
            np.asarray(result.f_hz, dtype=float),
            np.asarray(result.eps_selected, dtype=complex),
            sample_name=sample_name,
            notes=list(notes) + _nonpassive_note(result),
        )
    except Exception as exc:  # noqa: BLE001 - report to the user
        logger.error("[export_permittivity_touchstone] %s", exc)
        QMessageBox.critical(parent, t.get("error_title", "Error"),
                             t.get("eps_s1p_failed", "Failed to save the file:\n{error}").format(error=exc))
        return

    QMessageBox.information(
        parent, t.get("ok_title", "Saved"),
        t.get("eps_s1p_saved", "Permittivity saved to:\n{path}").format(path=path))
