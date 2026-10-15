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
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_touchstone import (
    implausible_s11_reason,
    is_permittivity_touchstone,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.precal import (
    REFERENCE_STANDARD,
    PrecalReference,
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

# Default of set_measurement(precal=...): the step keeps its pre-calibration.
KEEP_PRECAL = object()


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
        # evaluated at THAT temperature, not at the session one. ``s11_raw`` is
        # the sweep as acquired; ``precal`` is the step's own pre-calibration
        # reference c(f) (calibration.precal); ``s11`` is what the solvers use:
        # s11_raw * c0 / c when that pre-calibration is applied, else s11_raw.
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

        # Computed results.
        self.pattern_constants: Optional[PatternConstants] = None
        self.epsilon_result: Optional[EpsilonResult] = None
        self.last_error: Optional[str] = None

        logger.info("[PermittivityProbeCalibration] Initialized at %s", self.results_path)

    @staticmethod
    def _empty_measurement() -> Dict:
        return {"freqs": None, "s11": None, "s11_raw": None, "measured": False,
                "source": None, "temperature_c": None, "precal": None,
                "precal_applied": False}

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
        Set the session temperature; returns extrapolation warnings (if any)
        for the currently-selected reference liquids, each checked at the
        temperature its known eps_r is actually evaluated at.
        """
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
                        temperature_c: Optional[float] = None, precal=KEEP_PRECAL) -> bool:
        """Store a RAW measurement and persist it as a Touchstone .s1p file.

        EN: ``s11`` is the sweep as acquired. ``precal`` is the pre-calibration
            of THIS step (calibration.precal): left out, the step keeps the one
            it has -- a live re-measurement shares the probe state its
            reference was taken in --; a ``PrecalReference`` or ``None``
            replaces it (a preset or kit brings its own reference, or none).
            A kept reference on another grid than the new sweep is dropped.
            ``temperature_c`` is the temperature the S11 was recorded at when
            it does NOT come from this session (preset / kit); leave it None
            for a live measurement so the session temperature applies.
        ES: ``s11`` es el barrido tal como se adquirio. ``precal`` es la
            pre-calibracion de ESTE paso (calibration.precal): si se omite, el
            paso conserva la que tiene -- una re-medicion en vivo comparte el
            estado de la sonda en que se tomo su referencia --; un
            ``PrecalReference`` o ``None`` la reemplaza (un preset o kit trae
            su propia referencia, o ninguna). Una referencia conservada en otra
            grilla que el barrido nuevo se descarta. ``temperature_c`` es la
            temperatura a la que se registro el S11 cuando NO viene de esta
            sesion (preset / kit); dejarlo en None para una medicion en vivo.
        """
        key = standard_key.lower()
        if key not in self.measurements:
            logger.error("[PermittivityProbeCalibration] Unknown standard: %s", key)
            return False
        try:
            freqs = np.asarray(freqs, dtype=float)
            s11_raw = np.asarray(s11, dtype=complex)
            meas = self.measurements[key]
            if precal is not KEEP_PRECAL:
                if precal is not None:
                    self._check_precal(key, precal, freqs)
                meas["precal"] = precal
            elif meas["precal"] is not None and not meas["precal"].matches(freqs):
                logger.warning("[PermittivityProbeCalibration] %s: pre-calibration on another "
                               "grid than the new sweep, dropped", key)
                meas["precal"] = None
            meas["freqs"] = freqs
            meas["s11_raw"] = s11_raw
            meas["measured"] = True
            meas["source"] = source
            meas["temperature_c"] = float(temperature_c) if temperature_c is not None else None
            self._refresh(key)
            logger.info("[PermittivityProbeCalibration] Stored %s (%d points, source=%s)", key, len(freqs), source)
            return True
        except Exception as exc:  # noqa: BLE001 - report and signal failure
            logger.error("[PermittivityProbeCalibration] Error storing %s: %s", key, exc)
            return False

    def _invalidate_results(self, key: Optional[str] = None) -> None:
        """Forget results computed from the previous sweeps (``key=None``: all)."""
        if key is None or key in STANDARD_KEYS:
            self.pattern_constants = None
        self.epsilon_result = None

    def _persist(self, key: str) -> None:
        """Write the stored (solver-facing) S11 of ``key`` to ``<key>.s1p``."""
        meas = self.measurements[key]
        path = os.path.join(self.results_path, f"{key}.s1p")
        self._save_as_touchstone(meas["freqs"], meas["s11"], path)

    # --------------------------------------------------------------------- #
    # Per-step pre-calibration (s11 * c0 / c, see calibration.precal)
    # --------------------------------------------------------------------- #

    @staticmethod
    def precal_allowed(standard_key: str, kind: str) -> bool:
        """False for the step that defines the reference state of ``kind``.

        The Open is the reference of the session, so it never takes a
        pre-calibration; the Short only takes an OPEN one (a SHORT one would
        be referred to itself).
        """
        key = standard_key.lower()
        return key != "open" and key != REFERENCE_STANDARD.get(kind)

    def _check_precal(self, key: str, reference: PrecalReference, freqs=None) -> None:
        if not self.precal_allowed(key, reference.kind):
            raise ValueError(f"'{key}' cannot take a {reference.kind.upper()} pre-calibration: "
                             f"it is the reference of the session.")
        if freqs is not None and not reference.matches(freqs):
            raise ValueError(f"The pre-calibration of '{key}' is not on the frequency grid "
                             f"of its measurement.")

    def set_step_precal(self, standard_key: str, reference: PrecalReference) -> None:
        """
        Pre-calibrate ONE step: its sweep becomes s11_raw * c0 / c.

        EN: Recomputed from the step's current RAW sweep, so a new reference
            replaces the previous one instead of stacking on it; source and
            preset temperature are kept and no other step changes. Set before
            the step is measured, it waits for the measurement. Raises
            ``ValueError`` (changing nothing) for the reference step of the
            kind or a reference on another grid than the stored sweep.
        ES: Se recalcula desde el barrido CRUDO actual del paso, asi una
            referencia nueva reemplaza a la anterior en vez de apilarse; se
            conservan la fuente y la temperatura de preset y ningun otro paso
            cambia. Si se fija antes de medir el paso, espera a la medicion.
            Lanza ``ValueError`` (sin cambiar nada) para el paso de referencia
            de ese tipo o una referencia en otra grilla que el barrido guardado.
        """
        key = standard_key.lower()
        meas = self.measurements[key]
        self._check_precal(key, reference, meas["freqs"] if meas["measured"] else None)
        meas["precal"] = reference
        self._refresh(key)
        logger.info("[PermittivityProbeCalibration] %s pre-calibration set on %s",
                    reference.kind.upper(), key)

    def clear_step_precal(self, standard_key: str) -> None:
        """Remove the pre-calibration of one step: it goes back to its raw sweep."""
        key = standard_key.lower()
        if self.measurements[key]["precal"] is None:
            return
        self.measurements[key]["precal"] = None
        self._refresh(key)
        logger.info("[PermittivityProbeCalibration] pre-calibration removed from %s", key)

    def step_precal(self, standard_key: str) -> Optional[PrecalReference]:
        """The pre-calibration reference of a step (applied or pending), or None."""
        data = self.measurements.get(standard_key.lower())
        return data.get("precal") if data else None

    def is_precal_applied(self, standard_key: str) -> bool:
        """True when the stored sweep of the step is actually s11_raw * c0 / c.

        A pre-calibration stays pending (sweep stored raw) while its reference
        standard is not measured on the same grid.
        """
        data = self.measurements.get(standard_key.lower())
        return bool(data and data.get("precal_applied"))

    def precal_reference_sweep(self, kind: str) -> Optional[PrecalReference]:
        """c0 for ``kind``: the stored OPEN (or -SHORT) of the session, or None."""
        meas = self.measurements[REFERENCE_STANDARD[kind]]
        if not meas["measured"]:
            return None
        return PrecalReference.from_sweep(meas["freqs"], meas["s11"], kind)

    def _refresh(self, key: str) -> None:
        """Recompute what depends on ``key`` after its sweep or reference changed."""
        if key in REFERENCE_STANDARD.values():
            # c0 of every pre-calibrated step may have moved. Open first, then
            # Short (its own OPEN pre-cal feeds the SHORT c0), then the rest.
            order = ["open", "short"] + [k for k in self.measurements if k not in ("open", "short")]
            for k in order:
                self._apply_step_precal(k)
            self._invalidate_results()
        else:
            self._apply_step_precal(key)
            self._invalidate_results(key)

    def _apply_step_precal(self, key: str) -> None:
        meas = self.measurements[key]
        if not meas["measured"]:
            return
        raw, reference = meas["s11_raw"], meas["precal"]
        s11, applied = raw, False
        if reference is not None:
            c0 = self.precal_reference_sweep(reference.kind)
            if c0 is not None and c0.matches(meas["freqs"]) and reference.matches(meas["freqs"]):
                s11, applied = reference.correct(raw, c0.divisor), True
            else:
                logger.info("[PermittivityProbeCalibration] %s: pre-calibration pending until "
                            "the %s is measured on the same grid", key, reference.reference_standard)
        meas["s11"] = s11
        meas["precal_applied"] = applied
        try:
            self._persist(key)
        except Exception as exc:  # noqa: BLE001 - the in-memory data is what counts
            logger.error("[PermittivityProbeCalibration] Could not persist %s: %s", key, exc)

    def get_raw_measurement(self, standard_key: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Return ``(freqs, s11_raw)`` -- the sweep before its pre-cal -- or ``None``."""
        data = self.measurements.get(standard_key.lower())
        if not data or not data["measured"]:
            return None
        return data["freqs"], data["s11_raw"]

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
                temp_ref1_c=self.reference_temperature("ref1"),
                temp_ref2_c=self.reference_temperature("ref2"),
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

        self.epsilon_result = solve_epsilon_r(
            s11, self.pattern_constants, eps_seed=self._simplified_seed(cal_f, s11)
        )
        return self.epsilon_result

    def _simplified_seed(self, cal_f, s11_dut) -> Optional[np.ndarray]:
        """Simplified (Gn=0) curve used to seed the quintic and as cross-check.

        The full technique already measured everything the simplified formula
        needs (open/short/ref1), so the seed comes for free. Best-effort: on
        any failure the solver falls back to its own Gn -> 0 estimate
        (-third_term) to pick the root.
        """
        try:
            simplified = solve_epsilon_simplified(
                cal_f,
                s11_dut,
                self.measurements["open"]["s11"],
                self.measurements["short"]["s11"],
                self.measurements["ref1"]["s11"],
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
            self.reference_temperature("ref1"),
        )
        return self.epsilon_result

    def clear_all_measurements(self) -> None:
        """Forget every sweep, each step's pre-calibration included."""
        for key in self.measurements:
            self.measurements[key] = self._empty_measurement()
        self.pattern_constants = None
        self.epsilon_result = None
