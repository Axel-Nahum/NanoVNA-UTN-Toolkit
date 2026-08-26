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
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import skrf

from NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils import get_calibration_path

logger = logging.getLogger(__name__)

_KIT_DEV_PATH = "modules/material_characterization/calibration/kits"
_KIT_EXE_PATH = "modules/material_characterization/calibration/kits"

SCHEMA_VERSION = 1

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
        lines.append(f"Temperature: {self.temperature_c:.1f} °C")
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

    Only the non-DUT standards are saved (Open, Short, Ref1, optionally Ref2).
    Raises ``ValueError`` if the required standards are not all measured.
    Returns the calibration directory path.
    """
    required = ["open", "short", "ref1"]
    if cal.ref2_key is not None:
        required.append("ref2")

    for key in required:
        meas = cal.measurements.get(key, {})
        if not meas.get("measured"):
            raise ValueError(f"Standard '{key}' is not measured — cannot save calibration.")

    cal_dir = _cal_path(name)
    cal_dir.mkdir(parents=True, exist_ok=True)

    standards = []
    sources: Dict[str, str] = {}
    f_start = f_stop = points = None

    for key in required:
        meas = cal.measurements[key]
        freqs: np.ndarray = meas["freqs"]
        s11: np.ndarray = meas["s11"]
        _write_s1p(_s1p_path(name, key), freqs, s11)
        standards.append(key)
        sources[key] = meas.get("source") or "measured"
        if f_start is None:
            f_start = float(freqs[0])
            f_stop = float(freqs[-1])
            points = len(freqs)

    meta = CalibrationMeta(
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
    )

    _manifest_path(name).write_text(
        json.dumps(asdict(meta), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("[calibration_store] saved calibration '%s' to %s", name, cal_dir)
    return cal_dir


def read_calibration_meta(name: str) -> CalibrationMeta:
    """Load the manifest for an existing calibration. Raises FileNotFoundError if missing."""
    path = _manifest_path(name)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return CalibrationMeta(**{k: v for k, v in raw.items() if k in CalibrationMeta.__dataclass_fields__})


def load_calibration(name: str) -> Tuple[Dict[str, Tuple[np.ndarray, np.ndarray]], CalibrationMeta]:
    """
    Load a calibration by name.

    Returns ``(data, meta)`` where *data* maps standard key → (freqs, s11).
    """
    meta = read_calibration_meta(name)
    data: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
    for key in meta.standards:
        path = _s1p_path(name, key)
        if not path.exists():
            raise FileNotFoundError(f"Calibration '{name}': missing file {path.name}")
        data[key] = _read_s1p(path)
    return data, meta


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
    out_folder.mkdir(parents=True, exist_ok=True)

    required = ["open", "short", "ref1"]
    if cal.ref2_key is not None:
        required.append("ref2")

    for key in required:
        if not cal.measurements.get(key, {}).get("measured"):
            raise ValueError(f"Standard '{key}' is not measured — cannot export calibration.")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        standards: List[str] = []
        sources: Dict[str, str] = {}
        f_start = f_stop = points = None

        for key in required:
            meas = cal.measurements[key]
            freqs: np.ndarray = meas["freqs"]
            s11: np.ndarray = meas["s11"]
            _write_s1p(tmp_path / f"{key}.s1p", freqs, s11)
            standards.append(key)
            sources[key] = meas.get("source") or "measured"
            if f_start is None:
                f_start = float(freqs[0])
                f_stop = float(freqs[-1])
                points = len(freqs)

        meta = CalibrationMeta(
            name=slug,
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
        )
        (tmp_path / "manifest.json").write_text(
            json.dumps(asdict(meta), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

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
