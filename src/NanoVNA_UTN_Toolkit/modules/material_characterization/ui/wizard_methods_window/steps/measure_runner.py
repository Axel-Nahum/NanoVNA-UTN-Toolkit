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

        if hasattr(device, "sweep_max_freq_hz") and device.sweep_max_freq_hz and stop_freq > device.sweep_max_freq_hz:
            stop_freq = int(device.sweep_max_freq_hz)
        device_max_points = None
        if getattr(device, "valid_datapoints", None):
            device_max_points = max(device.valid_datapoints)
        elif hasattr(device, "sweep_points_max"):
            device_max_points = device.sweep_points_max
        if device_max_points and num_points > device_max_points:
            num_points = device_max_points

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
