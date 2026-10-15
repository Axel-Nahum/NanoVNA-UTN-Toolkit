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
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.measurement_quality import (
    SPIKE_K,
    QualityReport,
    assess_quality,
    despike_sweeps,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.probe_models import (
    get_probe,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    evaluate_epsilon_r,
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
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_touchstone import (
    implausible_s11_reason,
    is_permittivity_touchstone,
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

        # Per-standard measurement storage. ``temperature_c`` is only set when
        # the S11 was NOT taken in this session (a preset or kit recorded at a
        # known temperature): the reference liquid's known eps_r must then be
        # evaluated at THAT temperature, not at the session one.
        self.measurements: Dict[str, Dict] = {
            key: self._empty_measurement() for key in STANDARD_KEYS + (MUT_KEY,)
        }

        # Configuration / reference selection.
        self.ref1_key: Optional[str] = None
        self.ref2_key: Optional[str] = None
        self.temperature_c: Optional[float] = None
        self.device_name: Optional[str] = None
        # Probe in use (algorithms.probe_models key). Metadata only: it picks
        # the indicative model and which presets apply, never the solver math.
        self.probe_key: Optional[str] = None

        # Noise-based spike removal (``measurement_quality.despike_sweeps``).
        # Stored sweeps always stay as measured / imported: the removal runs
        # on copies when computing, jointly over the sweeps, and what it did is
        # recorded in each measurement's ``processing`` and in the result.
        self.despike_enabled: bool = True
        # Standards as fed to the calibration (despiked copies or the stored
        # arrays); None until computed, reset whenever a standard changes.
        self._calibration_sweeps: Optional[Dict[str, np.ndarray]] = None

        # Computed results.
        self.pattern_constants: Optional[PatternConstants] = None
        self.epsilon_result: Optional[EpsilonResult] = None
        self.last_error: Optional[str] = None

        logger.info("[PermittivityProbeCalibration] Initialized at %s", self.results_path)

    @staticmethod
    def _empty_measurement() -> Dict:
        return {"freqs": None, "s11": None, "measured": False, "source": None,
                "temperature_c": None, "processing": None}

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
        if (ref1_key, ref2_key) != (self.ref1_key, self.ref2_key):
            self._invalidate(standards_changed=True)
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
        Set the session temperature; returns extrapolation warnings (if any)
        for the currently-selected reference liquids, each checked at the
        temperature its known eps_r is actually evaluated at.
        """
        if self.temperature_c != float(temp_c):
            self._invalidate(standards_changed=True)  # the reference eps_r move
        self.temperature_c = float(temp_c)
        warnings: List[str] = []
        for std_key, liq_key in (("ref1", self.ref1_key), ("ref2", self.ref2_key)):
            if liq_key is None:
                continue
            liquid = get_reference_liquid(liq_key)
            if not liquid.has_debye_model:
                continue
            t = self.reference_temperature(std_key)
            if t < liquid.temp_min_c or t > liquid.temp_max_c:
                warnings.append(
                    f"{liquid.display_name}: {t:.1f} C outside "
                    f"[{liquid.temp_min_c:.0f}, {liquid.temp_max_c:.0f}] C (extrapolated)."
                )
        return warnings

    def standard_temperature(self, standard_key: str) -> Optional[float]:
        """Temperature recorded WITH a standard's S11 (preset / kit), or None."""
        data = self.measurements.get(standard_key.lower())
        return data.get("temperature_c") if data else None

    def reference_temperature(self, standard_key: str) -> Optional[float]:
        """
        Temperature at which ``standard_key``'s reference eps_r is evaluated.

        EN: The S11 and the known eps_r of a reference liquid must describe the
            liquid at the SAME temperature. A standard loaded from a preset
            measured at 18 C keeps 18 C even if this session runs at 25 C;
            anything measured now uses the session temperature.
        ES: El S11 y el eps_r conocido de un liquido de referencia tienen que
            corresponder a la MISMA temperatura. Un patron cargado de un preset
            medido a 18 C conserva 18 C aunque la sesion este a 25 C; lo que se
            mide ahora usa la temperatura de la sesion.
        """
        own = self.standard_temperature(standard_key)
        return float(own) if own is not None else self.temperature_c

    # --------------------------------------------------------------------- #
    # Measurement storage
    # --------------------------------------------------------------------- #

    def set_measurement(self, standard_key: str, freqs, s11, source: str = "measured",
                        temperature_c: Optional[float] = None) -> bool:
        """Store a measurement and persist it as a Touchstone .s1p file.

        ``temperature_c`` is the temperature the S11 was recorded at when it
        does NOT come from this session (preset / kit); leave it None for a
        live measurement so the session temperature applies.
        """
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
            self.measurements[key]["temperature_c"] = (
                float(temperature_c) if temperature_c is not None else None)
            self.measurements[key]["processing"] = None
            self._invalidate(standards_changed=key in STANDARD_KEYS)

            path = os.path.join(self.results_path, f"{key}.s1p")
            self._save_as_touchstone(freqs, s11, path)
            logger.info("[PermittivityProbeCalibration] Stored %s (%d points, source=%s)", key, len(freqs), source)
            return True
        except Exception as exc:  # noqa: BLE001 - report and signal failure
            logger.error("[PermittivityProbeCalibration] Error storing %s: %s", key, exc)
            return False

    def _invalidate(self, standards_changed: bool) -> None:
        """Drop computed results that depend on a sweep that just changed.

        A new standard used to leave the old pattern constants in place:
        ``compute_epsilon`` only recalibrates when they are None, so a
        re-measured standard was silently ignored until the session restarted.
        """
        self.epsilon_result = None
        if standards_changed:
            self.pattern_constants = None
            self._calibration_sweeps = None

    def set_despike_enabled(self, enabled: bool) -> None:
        """Turn the noise-based spike removal on or off (results are recomputed)."""
        enabled = bool(enabled)
        if enabled != self.despike_enabled:
            self.despike_enabled = enabled
            self._invalidate(standards_changed=True)

    def get_source(self, standard_key: str) -> Optional[str]:
        """Return the data source tag for a standard, or None if not measured."""
        data = self.measurements.get(standard_key.lower())
        return data.get("source") if data else None

    def get_processing(self, standard_key: str) -> Optional[Dict]:
        """What the last computation did to a stored sweep (None: not processed).

        EN: ``{"despike": {"replaced_hz": [...], "changes": [...],
            "kept_common_hz": [...]}}`` once a computation ran with spike
            removal enabled; ``{"despike": None}`` when it ran with it off.
        ES: ``{"despike": {...}}`` cuando un calculo corrio con la remocion de
            picos activada; ``{"despike": None}`` cuando corrio desactivada.
        """
        data = self.measurements.get(standard_key.lower())
        return data.get("processing") if data else None

    def import_standard_from_touchstone(self, standard_key: str, filepath: str) -> bool:
        """
        Offline path: load a standard's S11 from a Touchstone .s1p file.

        EN: Lets the wizard run without a connected device (e.g. SIMCAL files).
        ES: Permite ejecutar el asistente sin instrumento conectado (p. ej.
            archivos SIMCAL).
        """
        try:
            if is_permittivity_touchstone(filepath):
                raise ValueError("the file holds an exported permittivity, not S11")
            net = rf.Network(filepath)
            freqs = np.asarray(net.f, dtype=float)        # skrf normalizes to Hz
            s11 = np.asarray(net.s[:, 0, 0], dtype=complex)
            reason = implausible_s11_reason(s11)
            if reason:
                raise ValueError(reason)
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

    def _prepare_standards(self, f_hz: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Sweeps of the required standards as the calibration consumes them.

        EN: With spike removal on, copies despiked jointly (an outlier shared
            by several standards is an instrument artefact the calibration
            cancels, so it stays); each measurement's ``processing`` records
            what was done. The stored sweeps are never modified.
        ES: Con la remocion de picos activada, copias procesadas en conjunto
            (un outlier que comparten varios patrones es un artefacto del
            instrumento que la calibracion cancela, asi que se conserva); el
            ``processing`` de cada medicion registra lo que se hizo. Los
            barridos guardados nunca se modifican.
        """
        raw = {key: np.asarray(self.measurements[key]["s11"], dtype=complex)
               for key in self.required_standards}
        if self.despike_enabled:
            records = despike_sweeps(raw)
            sweeps = {key: rec.s11 for key, rec in records.items()}
            for key, rec in records.items():
                self.measurements[key]["processing"] = {"despike": rec.to_metadata(f_hz)}
                if rec.replaced.size:
                    logger.info("[PermittivityProbeCalibration] spike removal: %s at %s MHz",
                                key, ", ".join(f"{f_hz[i] / 1e6:.4g}" for i in rec.replaced))
        else:
            sweeps = raw
            for key in raw:
                self.measurements[key]["processing"] = {"despike": None}
        self._calibration_sweeps = sweeps
        return sweeps

    def _prepare_dut(self, f_hz: np.ndarray, s11: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Sample sweep as solved, plus its processing record (see ``_prepare_standards``).

        The stored (raw) standards are the context: a sample spike that sits
        where a standard has one too is shared, not removed.
        """
        if not self.despike_enabled:
            return s11, {"despike": None}
        context = {key: self.measurements[key]["s11"] for key in self.required_standards}
        rec = despike_sweeps({MUT_KEY: s11}, context=context)[MUT_KEY]
        return rec.s11, {"despike": rec.to_metadata(f_hz)}

    def compute_calibration(self) -> bool:
        """Compute the pattern constants (Gn, reference admittances).

        The simplified technique has no pattern constants (its closed formula
        needs none): there it only validates the shared frequency grid and
        prepares the standards.
        """
        if self.ref1_key is None:
            logger.error("[PermittivityProbeCalibration] Reference liquid not set")
            return False
        if self.temperature_c is None:
            logger.error("[PermittivityProbeCalibration] Temperature not set")
            return False

        if self.is_simplified:
            try:
                f_hz = self._common_frequency_grid(self.required_standards)
                self._prepare_standards(f_hz)
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
            sweeps = self._prepare_standards(f_hz)
            self.pattern_constants = compute_pattern_constants(
                f_hz=f_hz,
                temp_c=self.temperature_c,
                temp_ref1_c=self.reference_temperature("ref1"),
                temp_ref2_c=self.reference_temperature("ref2"),
                s11_short=sweeps["short"],
                s11_ref1=sweeps["ref1"],
                s11_ref2=sweeps["ref2"],
                s11_open=sweeps["open"],
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
        which is all the downstream UI consumes, plus ``quality`` (the
        measurement-quality checks, whose warnings lead ``warnings``) and
        ``processing`` (what spike removal did to each sweep).
        """
        stored_dut = s11 is None
        if stored_dut:
            dut = self.get_measurement(MUT_KEY)
            if dut is None:
                logger.error("[PermittivityProbeCalibration] No DUT measurement")
                return None
            freqs, s11 = dut
        freqs = np.asarray(freqs, dtype=float)
        s11 = np.asarray(s11, dtype=complex)

        stale = self._calibration_sweeps is None or (
            not self.is_simplified and self.pattern_constants is None)
        if stale and not self.compute_calibration():
            return None

        cal_f = self._common_frequency_grid(self.required_standards)
        if freqs.shape != cal_f.shape or not np.allclose(freqs, cal_f, rtol=0, atol=_FREQ_ATOL_HZ):
            logger.error("[PermittivityProbeCalibration] DUT grid != calibration grid")
            return None

        s11, dut_processing = self._prepare_dut(cal_f, s11)
        if stored_dut:
            self.measurements[MUT_KEY]["processing"] = dut_processing

        if self.is_simplified:
            result = self._compute_epsilon_simplified(cal_f, s11)
        else:
            result = solve_epsilon_r(
                s11, self.pattern_constants, eps_seed=self._simplified_seed(cal_f, s11)
            )
        self.epsilon_result = self._attach_quality(result, cal_f, s11, dut_processing)
        return self.epsilon_result

    def _simplified_seed(self, cal_f, s11_dut) -> Optional[np.ndarray]:
        """Simplified (Gn=0) curve used to seed the quintic and as cross-check.

        The full technique already measured everything the simplified formula
        needs (open/short/ref1), so the seed comes for free. Best-effort: on
        any failure the solver falls back to its own Gn -> 0 estimate
        (-third_term) to pick the root.
        """
        try:
            sweeps = self._calibration_sweeps
            simplified = solve_epsilon_simplified(
                cal_f,
                s11_dut,
                sweeps["open"],
                sweeps["short"],
                sweeps["ref1"],
                get_reference_liquid(self.ref1_key),
                self.reference_temperature("ref1"),
            )
            return simplified.eps
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[PermittivityProbeCalibration] simplified seed unavailable (%s); "
                "falling back to the solver's own Gn -> 0 estimate", exc
            )
            return None

    def _compute_epsilon_simplified(self, cal_f, s11) -> SimplifiedEpsilonResult:
        """Closed-form path: Short + Open(air) + one reference liquid."""
        sweeps = self._calibration_sweeps
        return solve_epsilon_simplified(
            cal_f,
            s11,
            sweeps["open"],
            sweeps["short"],
            sweeps["ref1"],
            get_reference_liquid(self.ref1_key),
            self.reference_temperature("ref1"),
        )

    # --------------------------------------------------------------------- #
    # Quality checks and processing record
    # --------------------------------------------------------------------- #

    def sweep_labels(self) -> Dict[str, str]:
        """Names of the sweeps in quality messages ("Ref 1 (Water)", ...)."""
        labels = {"open": "Open", "short": "Short", MUT_KEY: "sample"}
        for std_key, liq_key, tag in (("ref1", self.ref1_key, "Ref 1"),
                                      ("ref2", self.ref2_key, "Ref 2")):
            if liq_key is None:
                continue
            try:
                labels[std_key] = f"{tag} ({get_reference_liquid(liq_key).display_name})"
            except KeyError:
                labels[std_key] = tag
        return labels

    def assess_quality(self, f_hz: np.ndarray, s11_dut: Optional[np.ndarray],
                       gn: Optional[np.ndarray] = None) -> QualityReport:
        """
        Measurement-quality checks of the current calibration (+ sample).

        EN: Runs ``measurement_quality.assess_quality`` on the standards as
            the calibration uses them. The probe's C0 caps the reference
            separation only for a KNOWN probe (the generic C0 is an order of
            magnitude). Call after ``compute_calibration``.
        ES: Corre ``measurement_quality.assess_quality`` sobre los patrones tal
            como los usa la calibracion. El C0 de la sonda acota la separacion
            de referencias solo con una sonda CONOCIDA (el C0 generico es un
            orden de magnitud). Llamar despues de ``compute_calibration``.
        """
        sweeps = self._calibration_sweeps
        probe = get_probe(self.probe_key)
        known_probe = bool(probe.preset_probe)
        eps1, _ = evaluate_epsilon_r(get_reference_liquid(self.ref1_key), f_hz,
                                     self.reference_temperature("ref1"))
        eps2 = None
        if not self.is_simplified:
            eps2, _ = evaluate_epsilon_r(get_reference_liquid(self.ref2_key), f_hz,
                                         self.reference_temperature("ref2"))
        return assess_quality(
            f_hz,
            s11_open=sweeps["open"],
            s11_short=sweeps["short"],
            s11_ref1=sweeps["ref1"],
            eps_ref1=eps1,
            s11_ref2=sweeps.get("ref2"),
            eps_ref2=eps2,
            s11_dut=s11_dut,
            gn=gn,
            c0_f=probe.c0_f if known_probe else None,
            probe_label=probe.display_name if known_probe else "",
            labels=self.sweep_labels(),
        )

    def processing_record(self, dut_processing: Optional[Dict] = None) -> Dict:
        """
        JSON-friendly record of the sweep processing of the last computation.

        ``{"despike": {"enabled": bool, "criterion": str, "sweeps": {key:
        {"replaced_hz": [...], "changes": [...], "kept_common_hz": [...]}}}}``;
        ``sweeps`` is empty when spike removal is off.
        """
        sweeps = {}
        for key in self.required_standards:
            proc = (self.get_processing(key) or {}).get("despike")
            if proc:
                sweeps[key] = proc
        dut = (dut_processing or self.get_processing(MUT_KEY) or {}).get("despike")
        if dut:
            sweeps[MUT_KEY] = dut
        return {"despike": {
            "enabled": bool(self.despike_enabled),
            "criterion": (f"isolated point, 2nd difference > {SPIKE_K:g} x local noise "
                          f"and > S11 error budget, not shared with another sweep"),
            "sweeps": sweeps,
        }}

    def _despike_warning(self, record: Dict) -> List[str]:
        """Warning naming every point spike removal replaced (empty if none)."""
        labels = self.sweep_labels()
        items = []
        for key, proc in record["despike"]["sweeps"].items():
            for f, change in zip(proc.get("replaced_hz", []), proc.get("changes", [])):
                items.append(f"{labels.get(key, key)} at {f / 1e6:.4g} MHz "
                             f"(|ΔS11| = {change:.1e})")
        if not items:
            return []
        return [f"Spike removal (noise-based) replaced {len(items)} isolated point(s) "
                f"with the mean of their neighbours: " + "; ".join(items)
                + ". The stored sweeps are unchanged; turn spike removal off in the "
                  "result screen to compute with them as measured."]

    def _attach_quality(self, result, f_hz, s11_dut, dut_processing):
        """Attach ``processing`` and ``quality`` to ``result``; quality warnings go first.

        Best-effort: a failing check is logged and never breaks the result.
        """
        if result is None:
            return None
        record = self.processing_record(dut_processing)
        result.processing = record
        extra = []
        try:
            quality = self.assess_quality(f_hz, s11_dut, gn=getattr(result, "gn", None))
            result.quality = quality
            extra += quality.warnings
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PermittivityProbeCalibration] quality checks failed: %s", exc)
        extra += self._despike_warning(record)
        result.warnings[:0] = extra
        return result

    def clear_all_measurements(self) -> None:
        for key in self.measurements:
            self.measurements[key] = self._empty_measurement()
        self._invalidate(standards_changed=True)
