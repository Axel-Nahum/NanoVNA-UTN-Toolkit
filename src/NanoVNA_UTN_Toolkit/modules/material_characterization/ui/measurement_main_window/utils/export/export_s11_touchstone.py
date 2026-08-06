from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QFileDialog, QMessageBox


def export_s11_touchstone(main_window) -> None:
    cal = getattr(main_window.wizard_window, "perm_calibration", None)
    dut = cal.get_measurement("dut") if cal is not None else None
    if dut is None:
        QMessageBox.warning(main_window, "Export S11", "No S11 data available.")
        return

    freqs = np.asarray(dut[0], dtype=float)
    s11 = np.asarray(dut[1], dtype=complex)

    stem = f"s11_{main_window._sample_name()}"
    safe_stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in stem).strip() or "s11"

    path, _ = QFileDialog.getSaveFileName(
        main_window, "Export Touchstone S11", f"{safe_stem}.s1p",
        "Touchstone S1P (*.s1p);;All Files (*)",
    )
    if not path:
        return

    try:
        lines = [
            f"! S11 — {main_window._sample_name()}",
            "# Hz S RI R 50",
        ]
        for f, s in zip(freqs, s11):
            lines.append(f"{f:.6f} {s.real:.10f} {s.imag:.10f}")
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        QMessageBox.information(main_window, "Saved", f"S11 Touchstone saved to:\n{path}")
    except Exception as exc:
        QMessageBox.critical(main_window, "Export Error", f"Failed to save file:\n{exc}")
