"""
S11 sweep runner for the characterization wizard.

EN: Self-contained device-and-read helper that performs one S11 sweep on the
    connected NanoVNA. The device interaction (guard, connect, setSweep, read)
    is replicated here on purpose so the material-characterization module does
    NOT import code from ``dut_measurement`` (where other people work). Chart
    rendering lives in the screen builders, not here.

ES: Ayudante autocontenido que realiza un barrido de S11 en el NanoVNA
    conectado. La interaccion con el dispositivo (chequeo, conexion, setSweep,
    lectura) se replica aqui a proposito para que el modulo de caracterizacion
    NO importe codigo de ``dut_measurement``. El dibujado de graficos vive en
    los constructores de pantalla, no aqui.
"""

from __future__ import annotations

import logging

import numpy as np
from PySide6.QtWidgets import QApplication, QMessageBox

logger = logging.getLogger(__name__)

# Smith-chart trace colors per standard.
SMITH_COLOR_MAP = {
    "open": "red",
    "short": "green",
    "ref1": "blue",
    "ref2": "purple",
    "dut": "orange",
}


def _fmt_hz(hz):
    """Format Hz as kHz / MHz / GHz for user-facing messages."""
    hz = float(hz)
    if hz >= 1e9:
        return f"{hz/1e9:.4g} GHz"
    if hz >= 1e6:
        return f"{hz/1e6:.4g} MHz"
    return f"{hz/1e3:.4g} kHz"


def set_status(wizard, text, color):
    """Update the wizard's status label, if present."""
    if getattr(wizard, "status_label", None) is not None:
        wizard.status_label.setText(text)
        wizard.status_label.setStyleSheet(f"font-size: 12px; padding: 4px; color: {color};")


def run_s11_sweep(wizard):
    """
    Perform one S11 sweep and return ``(freqs, s11)`` or ``None`` on failure.

    Shows a blocking dialog (no simulation) when no device is connected, to
    match the behavior of the existing calibration wizard.
    """
    device = getattr(wizard, "vna_device", None)
    device_available = device is not None and hasattr(device, "connected")

    if not device_available:
        msg = (
            "No VNA device detected. Please connect a NanoVNA device before "
            "performing characterization measurements."
        )
        logger.error("[CharacterizationWizard] %s", msg)
        set_status(wizard, "No VNA device connected!", "red")
        QMessageBox.critical(wizard, "VNA Device Required", msg)
        return None

    try:
        if not device.connected():
            logger.warning("[CharacterizationWizard] Device not connected, connecting...")
            device.connect()
            if not device.connected():
                QMessageBox.warning(wizard, "Connection Failed", "Could not connect to VNA device.")
                return None
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(wizard, "Connection Error", f"Failed to connect: {exc}")
        return None

    try:
        set_status(wizard, "Measuring...", "orange")
        QApplication.processEvents()

        start_freq = wizard.get_sweep_start_frequency()
        stop_freq = wizard.get_sweep_stop_frequency()
        num_points = wizard.get_sweep_steps()

        # Debug Mode lets Step 1 configure a sweep beyond the instrument so that
        # foreign .s1p files can be imported. Measuring such a sweep is a
        # different matter: silently clamping it would return a grid that does
        # not match the other standards and break compute_calibration far from
        # the cause, so refuse here with an explicit message.
        problems = []
        dev_min = getattr(device, "sweep_min_freq_hz", None)
        dev_max = getattr(device, "sweep_max_freq_hz", None)
        if dev_min and start_freq < dev_min:
            problems.append(f"start {_fmt_hz(start_freq)} < {_fmt_hz(dev_min)}")
        if dev_max and stop_freq > dev_max:
            problems.append(f"stop {_fmt_hz(stop_freq)} > {_fmt_hz(dev_max)}")

        valid_points = getattr(device, "valid_datapoints", None)
        if valid_points and num_points not in valid_points:
            problems.append(
                f"{num_points} points is not one of "
                f"{', '.join(str(p) for p in sorted(valid_points))}")

        if problems:
            device_name = getattr(device, "name", type(device).__name__)
            logger.error("[CharacterizationWizard] sweep not measurable: %s", "; ".join(problems))
            set_status(wizard, "Sweep not supported by the device!", "red")
            QMessageBox.critical(
                wizard,
                "Sweep Not Supported",
                f"The configured sweep cannot be measured with {device_name}:\n\n"
                + "\n".join("  - " + p for p in problems)
                + "\n\nThis sweep is only usable for IMPORTING .s1p files.\n"
                  "Change it in Configuration to measure with the instrument.",
            )
            return None

        device.datapoints = num_points
        device.setSweep(start_freq, stop_freq)

        freqs = np.array(device.read_frequencies())
        s11 = np.array(device.readValues("data 0"))

        if len(freqs) != len(s11):
            logger.error("[CharacterizationWizard] freq/S11 length mismatch (%d/%d)",
                         len(freqs), len(s11))
            QMessageBox.critical(wizard, "Measurement Error",
                                 "Frequency and S11 sample counts differ.")
            set_status(wizard, "Measurement failed!", "red")
            return None

        return freqs, s11
    except Exception as exc:  # noqa: BLE001
        logger.error("[CharacterizationWizard] Measurement error: %s", exc)
        QMessageBox.critical(wizard, "Measurement Error", f"Error during measurement: {exc}")
        set_status(wizard, "Measurement failed!", "red")
        return None
