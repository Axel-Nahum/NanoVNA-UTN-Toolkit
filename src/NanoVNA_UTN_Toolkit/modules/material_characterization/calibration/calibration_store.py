"""
Characterization calibration store.

EN: A characterization calibration bundles the calibration standards (Open, Short,
    Ref1 and optionally Ref2) measured in one session so that the same probe
    setup can be reused for multiple unknown liquids without repeating all the
    calibration steps. Each calibration is a sub-directory inside the kits folder:
        <calibration_name>/
            manifest.json   -- CalibrationMeta fields as JSON
            open.s1p        -- Touchstone 1-port
            short.s1p
            ref1.s1p
            ref2.s1p        -- only for the full two-liquid technique
            <key>.precal.s1p -- only for a pre-calibrated standard: the
                               reference c(f) of its step (calibration.precal)
    Every standard is stored RAW; a pre-calibrated one is corrected again on
    load (s11 * c0 / c, c0 = the kit's own Open), exactly as in its session.

ES: Una calibracion agrupa los patrones de calibracion (Open, Short,
    Ref1 y opcionalmente Ref2) medidos en una sesion para poder reutilizar el
    mismo setup de sonda con multiples liquidos incognita sin repetir todos los
    pasos de calibracion. Cada calibracion es un subdirectorio dentro de la carpeta de
    kits:
        <nombre_calibracion>/
            manifest.json   -- campos de CalibrationMeta en JSON
            open.s1p        -- Touchstone 1 puerto
            short.s1p
            ref1.s1p
            ref2.s1p        -- solo para la tecnica completa (dos liquidos)
            <clave>.precal.s1p -- solo para un patron pre-calibrado: la
                               referencia c(f) de su paso (calibration.precal)
    Cada patron se guarda CRUDO; uno pre-calibrado se vuelve a corregir al
    cargarse (s11 * c0 / c, c0 = el Open del propio kit), igual que en su sesion.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import skrf

from NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils import get_calibration_path
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.precal import (
    KINDS as PRECAL_KINDS,
    PrecalReference,
)

logger = logging.getLogger(__name__)

_KIT_DEV_PATH = "modules/material_characterization/calibration/kits"
_KIT_EXE_PATH = "modules/material_characterization/calibration/kits"

# 2: standards stored raw; precal_kinds + <key>.precal.s1p per pre-calibrated standard.
SCHEMA_VERSION = 2

_PRECAL_SUFFIX = ".precal"

_CALLER = Path(__file__).resolve()


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass
class CalibrationMeta:
    """Provenance and configuration of one characterization calibration."""

    name: str                           # directory name (slug, no spaces)
    display_name: str                   # human-readable label shown in the UI
    technique_id: str                   # e.g. "open_coax_liquids"
    ref1_key: str                       # e.g. "water"
    ref2_key: Optional[str]            # None for simplified technique
    temperature_c: float
    device_name: str
    saved: str                          # ISO-8601 timestamp
    standards: List[str]                # keys present in the calibration, e.g. ["open","short","ref1","ref2"]
    sources: Dict[str, str]             # source tag per standard key
    f_start_hz: Optional[float] = None
    f_stop_hz: Optional[float] = None
    points: Optional[int] = None
    schema_version: int = SCHEMA_VERSION
    # Temperature recorded with a standard's S11 when it differs from the
    # session one (it came from a preset). Absent in older manifests.
    standard_temperatures: Dict[str, float] = field(default_factory=dict)
    # Probe the standards were taken with (algorithms.probe_models key).
    probe_key: Optional[str] = None
    # Pre-calibrated standards: key -> "open" | "short", with the reference
    # in <key>.precal.s1p. Absent in older manifests (no pre-cal restored).
    precal_kinds: Dict[str, str] = field(default_factory=dict)
    # Spike removal of the session that saved the kit, and what it did to each
    # standard in its last computation ({"despike": {...} | None} per key).
    # The .s1p files are always the sweeps as stored (never despiked): the
    # removal runs again on them when a computation uses the kit.
    despike_enabled: Optional[bool] = None
    processing: Dict[str, Dict] = field(default_factory=dict)

    @property
    def is_simplified(self) -> bool:
        return self.ref2_key is None

    def summary_lines(self) -> List[str]:
        """Short human-readable summary shown in the welcome info label."""
        lines = []
        tech = "Simplified (1 ref)" if self.is_simplified else "Full (2 refs)"
        lines.append(f"Technique: {tech}")
        ref = self.ref1_key
        if self.ref2_key:
            ref += f" + {self.ref2_key}"
        lines.append(f"References: {ref}")
        if self.probe_key:
            lines.append(f"Probe: {self.probe_key}")
        lines.append(f"Temperature: {self.temperature_c:.1f} °C")
        for key, temp in sorted((self.standard_temperatures or {}).items()):
            lines.append(f"  {key} (preset): {temp:.1f} °C")
        for key, kind in sorted((self.precal_kinds or {}).items()):
            lines.append(f"  {key}: pre-cal ({kind.upper()})")
        if self.f_start_hz is not None and self.f_stop_hz is not None:
            start = f"{self.f_start_hz / 1e6:.3g} MHz"
            stop = f"{self.f_stop_hz / 1e9:.4g} GHz"
            pts = f"{self.points} pts" if self.points else ""
            lines.append(f"Sweep: {start} – {stop}" + (f"  ({pts})" if pts else ""))
        lines.append(f"Saved: {self.saved[:10]}")
        return lines


# Backwards-compatible alias so old pickles / external code using KitMeta still works.
KitMeta = CalibrationMeta


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

def get_calibration_dir() -> Path:
    path = get_calibration_path(_KIT_EXE_PATH, _KIT_DEV_PATH, _CALLER)
    path.mkdir(parents=True, exist_ok=True)
    return path


# Keep old name as alias for internal helpers that still use it.
def get_kit_dir() -> Path:
    return get_calibration_dir()


def _cal_path(name: str) -> Path:
    return get_calibration_dir() / name


def _manifest_path(name: str) -> Path:
    return _cal_path(name) / "manifest.json"


def _s1p_path(name: str, key: str) -> Path:
    return _cal_path(name) / f"{key}.s1p"


def _precal_file(key: str) -> str:
    return f"{key}{_PRECAL_SUFFIX}.s1p"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _write_s1p(path: Path, freqs: np.ndarray, s11: np.ndarray) -> None:
    net = skrf.Network()
    net.frequency = skrf.Frequency.from_f(freqs, unit="hz")
    net.s = s11[:, np.newaxis, np.newaxis]
    net.write_touchstone(str(path))


def _read_s1p(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    net = skrf.Network(str(path))
    return net.f, net.s[:, 0, 0]


def _write_calibration_files(
    dest: Path,
    name: str,
    display_name: str,
    cal,
    technique_id: str,
    temperature_c: float,
    device_name: str,
    action: str,
) -> CalibrationMeta:
    """
    Write the standards of *cal* (raw, plus each one's pre-cal c(f)) into *dest*.

    Shared by ``save_calibration`` and ``export_calibration`` so both formats
    carry exactly the same content. Raises ``ValueError`` if a required
    standard is not measured (*action* names the operation in the message).
    """
    required = ["open", "short", "ref1"]
    if cal.ref2_key is not None:
        required.append("ref2")

    for key in required:
        if not cal.measurements.get(key, {}).get("measured"):
            raise ValueError(f"Standard '{key}' is not measured — cannot {action} calibration.")

    dest.mkdir(parents=True, exist_ok=True)
    standards: List[str] = []
    sources: Dict[str, str] = {}
    temps: Dict[str, float] = {}
    precal_kinds: Dict[str, str] = {}
    processing: Dict[str, Dict] = {}
    f_start = f_stop = points = None

    for key in required:
        meas = cal.measurements[key]
        freqs: np.ndarray = meas["freqs"]
        raw = meas.get("s11_raw")
        s11: np.ndarray = raw if raw is not None else meas["s11"]
        _write_s1p(dest / f"{key}.s1p", freqs, s11)
        standards.append(key)
        sources[key] = meas.get("source") or "measured"
        if meas.get("temperature_c") is not None:
            temps[key] = float(meas["temperature_c"])
        if meas.get("processing"):
            processing[key] = meas["processing"]
        precal: Optional[PrecalReference] = meas.get("precal")
        precal_path = dest / _precal_file(key)
        if precal is not None:
            _write_s1p(precal_path, precal.freqs, precal.divisor)
            precal_kinds[key] = precal.kind
        elif precal_path.exists():
            precal_path.unlink()               # overwriting a pre-calibrated kit
        if f_start is None:
            f_start = float(freqs[0])
            f_stop = float(freqs[-1])
            points = len(freqs)

    return CalibrationMeta(
        name=name,
        display_name=display_name,
        technique_id=technique_id,
        ref1_key=cal.ref1_key,
        ref2_key=cal.ref2_key,
        temperature_c=float(temperature_c),
        device_name=device_name,
        saved=datetime.now().isoformat(timespec="seconds"),
        standards=standards,
        sources=sources,
        f_start_hz=f_start,
        f_stop_hz=f_stop,
        points=points,
        standard_temperatures=temps,
        probe_key=getattr(cal, "probe_key", None),
        precal_kinds=precal_kinds,
        despike_enabled=getattr(cal, "despike_enabled", None),
        processing=processing,
    )


def _write_manifest(path: Path, meta: CalibrationMeta) -> None:
    path.write_text(json.dumps(asdict(meta), indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def save_calibration(
    name: str,
    display_name: str,
    cal,
    technique_id: str,
    temperature_c: float,
    device_name: str = "",
) -> Path:
    """
    Save the calibration standards from *cal* as a new calibration named *name*.

    Only the non-DUT standards are saved (Open, Short, Ref1, optionally Ref2),
    each raw and, when its step was pre-calibrated, with its reference c(f).
    Raises ``ValueError`` if the required standards are not all measured.
    Returns the calibration directory path.
    """
    cal_dir = _cal_path(name)
    meta = _write_calibration_files(cal_dir, name, display_name, cal, technique_id,
                                    temperature_c, device_name, action="save")
    _write_manifest(_manifest_path(name), meta)

    logger.info("[calibration_store] saved calibration '%s' to %s", name, cal_dir)
    return cal_dir


def read_calibration_meta(name: str) -> CalibrationMeta:
    """Load the manifest for an existing calibration. Raises FileNotFoundError if missing."""
    path = _manifest_path(name)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return CalibrationMeta(**{k: v for k, v in raw.items() if k in CalibrationMeta.__dataclass_fields__})


def _load_calibration_parts(name: str):
    """Read and validate every file of calibration *name*: ``(data, meta, precals)``."""
    meta = read_calibration_meta(name)
    data: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
    for key in meta.standards:
        path = _s1p_path(name, key)
        if not path.exists():
            raise FileNotFoundError(f"Calibration '{name}': missing file {path.name}")
        data[key] = _read_s1p(path)
    return data, meta, _load_precals(name, meta, data)


def _load_precals(name: str, meta: CalibrationMeta, data) -> Dict[str, PrecalReference]:
    """
    The pre-calibration reference of each pre-calibrated standard, validated.

    EN: A standard listed in ``precal_kinds`` was corrected in its session
        with that c(f): without it, it would come back uncorrected and out of
        step with the others, so a missing, malformed or off-grid
        ``<key>.precal.s1p`` is an error, never a silent "no pre-cal".
    ES: Un patron listado en ``precal_kinds`` se corrigio en su sesion con esa
        c(f): sin ella volveria sin corregir y desfasado de los demas, asi que
        un ``<clave>.precal.s1p`` faltante, invalido o en otra grilla es un
        error, nunca un "sin pre-cal" silencioso.
    """
    label = meta.display_name or name
    precals: Dict[str, PrecalReference] = {}
    for key, kind in (meta.precal_kinds or {}).items():
        if key not in data:
            raise ValueError(f"Calibration '{label}': pre-calibration listed for '{key}', "
                             f"which is not one of its standards.")
        if kind not in PRECAL_KINDS:
            raise ValueError(f"Calibration '{label}': unknown pre-calibration kind "
                             f"'{kind}' for '{key}'.")
        path = _cal_path(name) / _precal_file(key)
        if not path.exists():
            raise ValueError(
                f"Calibration '{label}': '{key}' was pre-calibrated ({kind.upper()}) but "
                f"{path.name} is missing.\nWithout that reference the standard cannot be "
                "corrected as it was. Restore the file or redo the calibration.")
        freqs, divisor = _read_s1p(path)
        try:
            precal = PrecalReference(freqs=freqs, divisor=divisor, kind=kind)
        except ValueError as exc:
            raise ValueError(f"Calibration '{label}': invalid {path.name}: {exc}") from exc
        if not precal.matches(data[key][0]):
            raise ValueError(f"Calibration '{label}': {path.name} is not on the frequency "
                             f"grid of '{key}'.")
        precals[key] = precal
    return precals


def load_calibration(name: str) -> Tuple[Dict[str, Tuple[np.ndarray, np.ndarray]], CalibrationMeta]:
    """
    Load a calibration by name.

    Returns ``(data, meta)`` where *data* maps standard key → (freqs, s11),
    the raw S11 as stored (manifests before schema 2 may hold an already
    divided one: nothing recorded it). Raises ``ValueError`` when a
    pre-calibrated standard's reference is unusable.
    """
    data, meta, _ = _load_calibration_parts(name)
    return data, meta


def load_calibration_precals(name: str) -> Dict[str, PrecalReference]:
    """Validated pre-calibration reference of each pre-calibrated standard of *name*."""
    return _load_calibration_parts(name)[2]


def apply_calibration(cal, name: str) -> Tuple[CalibrationMeta, List[str]]:
    """
    Load calibration *name* into the calibration manager *cal*.

    EN: The single path every "open a saved kit" action goes through. All
        files are read and validated BEFORE *cal* is touched. Then: reference
        liquids, probe, spike-removal setting, each standard with its source
        tag, preset temperature and own pre-calibration, and finally the session
        temperature, whose extrapolation warnings are returned with the
        manifest. The kit's Open becomes c0, so a DUT pre-calibrated now is
        referred to the state the kit was measured in.
    ES: El unico camino por el que pasa toda accion de "abrir un kit guardado".
        Todos los archivos se leen y validan ANTES de tocar *cal*. Despues:
        liquidos de referencia, sonda, remocion de picos, cada patron con su
        fuente, temperatura de preset y pre-calibracion propia, y al final la
        temperatura de la
        sesion, cuyas advertencias de extrapolacion se devuelven con el
        manifiesto. El Open del kit pasa a ser c0, asi un DUT pre-calibrado
        ahora queda referido al estado en que se midio el kit.
    """
    data, meta, precals = _load_calibration_parts(name)
    label = meta.display_name or name

    cal.clear_all_measurements()
    if not cal.set_reference_liquids(meta.ref1_key, meta.ref2_key):
        raise ValueError(f"Calibration '{label}' references unknown liquids "
                         f"'{meta.ref1_key}' / '{meta.ref2_key}'.")
    cal.probe_key = meta.probe_key
    # Spike removal as the kit was saved with (older manifests: keep the session's).
    if meta.despike_enabled is not None and hasattr(cal, "set_despike_enabled"):
        cal.set_despike_enabled(meta.despike_enabled)

    temps = meta.standard_temperatures or {}
    for key, (freqs, s11) in data.items():
        if not cal.set_measurement(key, freqs, s11, source=f"kit:{meta.name}",
                                   temperature_c=temps.get(key), precal=precals.get(key)):
            raise ValueError(f"Calibration '{label}': could not load '{key}'.")

    # After the standards: the warnings check each reference at the
    # temperature its eps_r is really evaluated at.
    warnings = cal.set_temperature(meta.temperature_c)
    return meta, warnings


def list_calibrations() -> List[CalibrationMeta]:
    """Return all valid calibrations sorted by save date (newest first)."""
    calibrations: List[CalibrationMeta] = []
    for cal_dir in sorted(get_calibration_dir().iterdir()):
        if not cal_dir.is_dir():
            continue
        manifest = cal_dir / "manifest.json"
        if not manifest.exists():
            continue
        try:
            calibrations.append(read_calibration_meta(cal_dir.name))
        except Exception:
            logger.warning("[calibration_store] could not read calibration '%s'", cal_dir.name)
    calibrations.sort(key=lambda m: m.saved, reverse=True)
    return calibrations


def delete_calibration(name: str) -> None:
    """Delete a calibration directory and all its contents."""
    import shutil
    cal_dir = _cal_path(name)
    if cal_dir.exists():
        shutil.rmtree(cal_dir)
        logger.info("[calibration_store] deleted calibration '%s'", name)


def export_calibration(
    dest_dir: Path,
    slug: str,
    display_name: str,
    cal,
    technique_id: str,
    temperature_c: float,
    device_name: str = "",
) -> Path:
    """
    Export a calibration to *dest_dir/<slug>/* containing both a ``.charpkg`` and a
    ``.zip`` file (identical content, different extension) so the recipient can
    open either with any archive tool.

    Does not create an internal calibration folder — use ``save_calibration`` for that.
    Returns the created folder path.
    """
    import tempfile
    import zipfile

    dest_dir = Path(dest_dir)
    out_folder = dest_dir / slug

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        meta = _write_calibration_files(tmp_path, slug, display_name, cal, technique_id,
                                        temperature_c, device_name, action="export")
        _write_manifest(tmp_path / "manifest.json", meta)

        out_folder.mkdir(parents=True, exist_ok=True)
        archive_files = list(tmp_path.iterdir())
        for ext in (".charpkg", ".zip"):
            out_file = out_folder / f"{slug}{ext}"
            with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in archive_files:
                    zf.write(f, f.name)

    logger.info("[calibration_store] exported calibration package to %s", out_folder)
    return out_folder


def import_calibration(zip_path: Path) -> str:
    """
    Extract a ``.charpkg`` ZIP into the calibrations directory.

    Returns the imported calibration name (slug). Raises ``FileExistsError`` if a
    calibration with the same name already exists locally.
    """
    import zipfile

    zip_path = Path(zip_path)
    with zipfile.ZipFile(zip_path, "r") as zf:
        if "manifest.json" not in zf.namelist():
            raise ValueError("Invalid calibration: manifest.json not found in the archive.")
        manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))

    cal_name = manifest_data.get("name") or zip_path.stem
    dest = _cal_path(cal_name)
    if dest.exists():
        import shutil
        shutil.rmtree(dest)

    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(str(dest))

    logger.info("[calibration_store] imported calibration '%s' from ZIP %s", cal_name, zip_path)
    return cal_name


# --------------------------------------------------------------------------- #
# Backwards-compatible aliases (old kit_store names)
# --------------------------------------------------------------------------- #

save_kit = save_calibration
save_kit_to_zip = export_calibration
import_kit_from_zip = import_calibration
read_kit_meta = read_calibration_meta
load_kit = load_calibration
list_kits = list_calibrations
delete_kit = delete_calibration
