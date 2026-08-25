"""
Permittivity probe calibration manager.

EN: Stores the four calibration standards (Open, Short, and two reference
    liquids) plus the Material-Under-Test (MUT) S11, persists each as a
    Touchstone .s1p file, validates the frequency grid, and computes the
    complex permittivity of the MUT. Modeled on
    ``modules/dut_measurement/calibration/calibration_manager.OSMCalibrationManager``.

ES: Almacena los cuatro patrones de calibracion (Open, Short y dos liquidos de
    referencia) mas el S11 del material bajo prueba (MUT), persiste cada uno
    como archivo Touchstone .s1p, valida la grilla de frecuencias y calcula la
    permitividad compleja del MUT. Modelado a partir de ``OSMCalibrationManager``.

Algorithm source / Fuente del algoritmo:
    "Mediciones de permitividad mediante una sonda coaxial", UTN-FRBA 2024,
    and the MATLAB reference in medicion_fluidos/App_ME2/src/measurements.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import skrf as rf

from NanoVNA_UTN_Toolkit.utils import safe_import
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.pattern_constants import (
    PatternConstants,
    compute_pattern_constants,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.permittivity_solver import (
    EpsilonResult,
    solve_epsilon_r,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.simplified_solver import (
    SimplifiedEpsilonResult,
    solve_epsilon_simplified,
)

logger = logging.getLogger(__name__)

get_calibration_path = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils",
    "get_calibration_path",
)

# Calibration standards in measurement order. Open/Short are fixed roles;
# ref1/ref2 are user-selected reference liquids; dut is the unknown liquid.
STANDARD_KEYS = ("open", "short", "ref1", "ref2")
MUT_KEY = "dut"

# Frequency-grid comparison tolerance, in Hz.
_FREQ_ATOL_HZ = 1000.0


class PermittivityProbeCalibration:
    """Manager for the open-ended coaxial probe permittivity calibration."""

    def __init__(self, base_path: Optional[str] = None):
        self.results_path = get_calibration_path(
            "modules/material_characterization/calibration/probe_results",
            "modules/material_characterization/calibration/probe_results",
            Path(__file__).resolve(),
        )
        os.makedirs(self.results_path, exist_ok=True)

        # Per-standard measurement storage.
        self.measurements: Dict[str, Dict] = {
            key: {"freqs": None, "s11": None, "measured": False, "source": None}
            for key in STANDARD_KEYS + (MUT_KEY,)
        }

        # Configuration / reference selection.
        self.ref1_key: Optional[str] = None
        self.ref2_key: Optional[str] = None
        self.temperature_c: Optional[float] = None
        self.device_name: Optional[str] = None

        # Computed results.
        self.pattern_constants: Optional[PatternConstants] = None
        self.epsilon_result: Optional[EpsilonResult] = None
        self.last_error: Optional[str] = None

        logger.info("[PermittivityProbeCalibration] Initialized at %s", self.results_path)

    # --------------------------------------------------------------------- #
    # Configuration
    # --------------------------------------------------------------------- #

    def set_reference_liquids(self, ref1_key: str, ref2_key: Optional[str] = None) -> bool:
        """
        Select the reference liquid(s), validated against the library.

        EN: ``ref2_key=None`` selects the SIMPLIFIED single-reference technique:
            the permittivity comes from the closed-form barycentric formula
            (``simplified_solver``) instead of the degree-5 solver, and ``ref2``
            stops being a required standard.

        ES: ``ref2_key=None`` selecciona la tecnica SIMPLIFICADA de una sola
            referencia: la permitividad sale de la formula baricentrica cerrada
            (``simplified_solver``) en vez del solver de grado 5, y ``ref2``
            deja de ser un patron requerido.
        """
        if ref2_key is not None and ref1_key == ref2_key:
            logger.error("[PermittivityProbeCalibration] Reference liquids must differ")
            return False
        try:
            get_reference_liquid(ref1_key)
            if ref2_key is not None:
                get_reference_liquid(ref2_key)
        except KeyError as exc:
            logger.error("[PermittivityProbeCalibration] %s", exc)
            return False
        self.ref1_key = ref1_key
        self.ref2_key = ref2_key
        return True

    @property
    def is_simplified(self) -> bool:
        """True when running the single-reference (closed-form) technique."""
        return self.ref2_key is None

    @property
    def required_standards(self) -> Tuple[str, ...]:
        """Calibration standards this technique actually needs."""
        return ("open", "short", "ref1") if self.is_simplified else STANDARD_KEYS

    def set_temperature(self, temp_c: float) -> List[str]:
        """
        Set the reference temperature; returns extrapolation warnings (if any)
        for the currently-selected reference liquids.
        """
        self.temperature_c = float(temp_c)
        warnings: List[str] = []
        for key in (self.ref1_key, self.ref2_key):
            if key is None:
                continue
            liquid = get_reference_liquid(key)
            if temp_c < liquid.temp_min_c or temp_c > liquid.temp_max_c:
                warnings.append(
                    f"{liquid.display_name}: {temp_c:.1f} C outside "
                    f"[{liquid.temp_min_c:.0f}, {liquid.temp_max_c:.0f}] C (extrapolated)."
                )
        return warnings

    # --------------------------------------------------------------------- #
    # Measurement storage
    # --------------------------------------------------------------------- #

    def set_measurement(self, standard_key: str, freqs, s11, source: str = "measured") -> bool:
        """Store a measurement and persist it as a Touchstone .s1p file."""
        key = standard_key.lower()
        if key not in self.measurements:
            logger.error("[PermittivityProbeCalibration] Unknown standard: %s", key)
            return False
        try:
            freqs = np.asarray(freqs, dtype=float)
            s11 = np.asarray(s11, dtype=complex)
            self.measurements[key]["freqs"] = freqs
            self.measurements[key]["s11"] = s11
            self.measurements[key]["measured"] = True
            self.measurements[key]["source"] = source

            path = os.path.join(self.results_path, f"{key}.s1p")
            self._save_as_touchstone(freqs, s11, path)
            logger.info("[PermittivityProbeCalibration] Stored %s (%d points, source=%s)", key, len(freqs), source)
            return True
        except Exception as exc:  # noqa: BLE001 - report and signal failure
            logger.error("[PermittivityProbeCalibration] Error storing %s: %s", key, exc)
            return False

    def get_source(self, standard_key: str) -> Optional[str]:
        """Return the data source tag for a standard, or None if not measured."""
        data = self.measurements.get(standard_key.lower())
        return data.get("source") if data else None

    def import_standard_from_touchstone(self, standard_key: str, filepath: str) -> bool:
        """
        Offline path: load a standard's S11 from a Touchstone .s1p file.

        EN: Lets the wizard run without a connected device (e.g. SIMCAL files).
        ES: Permite ejecutar el asistente sin instrumento conectado (p. ej.
            archivos SIMCAL).
        """
        try:
            net = rf.Network(filepath)
            freqs = np.asarray(net.f, dtype=float)        # skrf normalizes to Hz
            s11 = np.asarray(net.s[:, 0, 0], dtype=complex)
            return self.set_measurement(standard_key, freqs, s11, source="imported")
        except Exception as exc:  # noqa: BLE001
            logger.error("[PermittivityProbeCalibration] Import failed (%s): %s", filepath, exc)
            return False

    def _save_as_touchstone(self, freqs: np.ndarray, s11: np.ndarray, filepath: str) -> None:
        """Save a 1-port measurement as a Touchstone .s1p file (Z0 = 50)."""
        s_data = s11.reshape(-1, 1, 1)
        network = rf.Network(frequency=freqs, s=s_data, z0=50)
        network.write_touchstone(filepath)
        logger.info("[PermittivityProbeCalibration] Touchstone saved: %s", filepath)

    def get_measurement(self, standard_key: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Return ``(freqs, s11)`` for a standard, or ``None`` if not measured."""
        data = self.measurements.get(standard_key.lower())
        if not data or not data["measured"]:
            return None
        return data["freqs"], data["s11"]

    def is_standard_measured(self, standard_key: str) -> bool:
        data = self.measurements.get(standard_key.lower())
        return bool(data and data["measured"])

    def get_completion_status(self) -> Dict[str, bool]:
        """Return per-standard completion flags plus a ``calibration_complete``.

        ``calibration_complete`` only counts the standards the ACTIVE technique
        requires (the simplified one has no ``ref2``).
        """
        status = {key: self.measurements[key]["measured"] for key in self.measurements}
        status["calibration_complete"] = all(
            self.measurements[key]["measured"] for key in self.required_standards
        )
        return status

    # --------------------------------------------------------------------- #
    # Computation
    # --------------------------------------------------------------------- #

    def _common_frequency_grid(self, keys) -> np.ndarray:
        """Validate that all given standards share one frequency grid; return it."""
        grids = []
        for key in keys:
            data = self.measurements[key]
            if not data["measured"]:
                raise ValueError(f"Standard '{key}' has not been measured.")
            grids.append(data["freqs"])
        ref = grids[0]
        for key, grid in zip(keys, grids):
            if grid.shape != ref.shape or not np.allclose(grid, ref, rtol=0, atol=_FREQ_ATOL_HZ):
                raise ValueError(
                    f"Frequency grid mismatch for '{key}'. All standards must be "
                    f"measured on the same sweep (interpolation is not allowed)."
                )
        return ref

    def compute_calibration(self) -> bool:
        """Compute the pattern constants (Gn, reference admittances).

        The simplified technique has no pattern constants (its closed formula
        needs none): there it only validates the shared frequency grid.
        """
        if self.ref1_key is None:
            logger.error("[PermittivityProbeCalibration] Reference liquid not set")
            return False
        if self.temperature_c is None:
            logger.error("[PermittivityProbeCalibration] Temperature not set")
            return False

        if self.is_simplified:
            try:
                self._common_frequency_grid(self.required_standards)
                self.last_error = None
                logger.info(
                    "[PermittivityProbeCalibration] Simplified technique: grid "
                    "validated; no pattern constants required"
                )
                return True
            except Exception as exc:  # noqa: BLE001
                self.last_error = str(exc)
                logger.error("[PermittivityProbeCalibration] compute_calibration failed: %s", exc)
                return False

        try:
            f_hz = self._common_frequency_grid(STANDARD_KEYS)
            self.pattern_constants = compute_pattern_constants(
                f_hz=f_hz,
                temp_c=self.temperature_c,
                s11_short=self.measurements["short"]["s11"],
                s11_ref1=self.measurements["ref1"]["s11"],
                s11_ref2=self.measurements["ref2"]["s11"],
                s11_open=self.measurements["open"]["s11"],
                ref1=get_reference_liquid(self.ref1_key),
                ref2=get_reference_liquid(self.ref2_key),
            )
            self.last_error = None
            logger.info("[PermittivityProbeCalibration] Calibration constants computed")
            return True
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            logger.error("[PermittivityProbeCalibration] compute_calibration failed: %s", exc)
            return False

    def compute_epsilon(self, freqs=None, s11=None):
        """
        Compute the MUT permittivity. Uses the stored DUT measurement unless
        ``(freqs, s11)`` are provided.

        Returns an ``EpsilonResult`` (full two-liquid technique, degree-5
        solver) or a ``SimplifiedEpsilonResult`` (single-reference technique,
        closed formula). Both expose ``f_hz`` / ``eps_selected`` / ``warnings``,
        which is all the downstream UI consumes.
        """
        if s11 is None:
            dut = self.get_measurement(MUT_KEY)
            if dut is None:
                logger.error("[PermittivityProbeCalibration] No DUT measurement")
                return None
            freqs, s11 = dut
        freqs = np.asarray(freqs, dtype=float)
        s11 = np.asarray(s11, dtype=complex)

        if self.is_simplified:
            return self._compute_epsilon_simplified(freqs, s11)

        if self.pattern_constants is None and not self.compute_calibration():
            return None

        cal_f = self.pattern_constants.f_hz
        if freqs.shape != cal_f.shape or not np.allclose(freqs, cal_f, rtol=0, atol=_FREQ_ATOL_HZ):
            logger.error("[PermittivityProbeCalibration] DUT grid != calibration grid")
            return None

        self.epsilon_result = solve_epsilon_r(s11, self.pattern_constants)
        return self.epsilon_result

    def _compute_epsilon_simplified(self, freqs, s11) -> Optional[SimplifiedEpsilonResult]:
        """Closed-form path: Short + Open(air) + one reference liquid."""
        if self.temperature_c is None:
            logger.error("[PermittivityProbeCalibration] Temperature not set")
            return None
        try:
            cal_f = self._common_frequency_grid(self.required_standards)
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            logger.error("[PermittivityProbeCalibration] %s", exc)
            return None

        if freqs.shape != cal_f.shape or not np.allclose(freqs, cal_f, rtol=0, atol=_FREQ_ATOL_HZ):
            logger.error("[PermittivityProbeCalibration] DUT grid != calibration grid")
            return None

        self.epsilon_result = solve_epsilon_simplified(
            cal_f,
            s11,
            self.measurements["open"]["s11"],
            self.measurements["short"]["s11"],
            self.measurements["ref1"]["s11"],
            get_reference_liquid(self.ref1_key),
            self.temperature_c,
        )
        return self.epsilon_result

    def clear_all_measurements(self) -> None:
        for key in self.measurements:
            self.measurements[key] = {"freqs": None, "s11": None, "measured": False}
        self.pattern_constants = None
        self.epsilon_result = None
