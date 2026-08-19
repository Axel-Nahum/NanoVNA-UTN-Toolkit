"""
Preset measurement store (Touchstone + JSON sidecar + PRESETS.md).

EN: A ``.s1p`` carries no provenance: until now the only metadata a saved
    preset had was its file name, so nothing could tell a water reference from
    a short, or a 2026 R60 sweep from something measured this morning. This
    module pairs every ``<name>.s1p`` with a ``<name>.json`` sidecar and keeps
    ``PRESETS.md`` in sync, so presets can be filtered by liquid in the wizard
    and their origin stays auditable.

ES: Un ``.s1p`` no lleva procedencia: hasta ahora la unica metadata de un
    preset guardado era su nombre de archivo, asi que nada distinguia una
    referencia de agua de un short, ni un barrido del R60 2026 de algo medido
    esta manana. Este modulo acompana cada ``<name>.s1p`` con un sidecar
    ``<name>.json`` y mantiene ``PRESETS.md`` al dia, para poder filtrar los
    presets por liquido en el asistente y que su origen quede auditable.

Legacy presets (a ``.s1p`` with no sidecar) are still listed, with
``liquid_key=None``, so nothing saved before this module disappears.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils import get_calibration_path

logger = logging.getLogger(__name__)

_PRESET_DEV_PATH = "modules/material_characterization/calibration/preset_liquids"
_PRESET_EXE_PATH = "modules/material_characterization/calibration/preset_liquids"

SCHEMA_VERSION = 1

#: Roles a stored sweep can play in a characterization run.
ROLE_OPEN = "open"
ROLE_SHORT = "short"
ROLE_REFERENCE = "reference"
ROLE_DUT = "dut"

#: How the sweep was obtained.
SOURCE_MEASURED = "measured"
SOURCE_IMPORTED = "imported"
SOURCE_SIMULATED = "simulated"

_MD_NAME = "PRESETS.md"
_AUTO_BEGIN = "<!-- BEGIN AUTO-GENERATED TABLE - do not edit by hand -->"
_AUTO_END = "<!-- END AUTO-GENERATED TABLE -->"
_LOG_HEADER = "## Presets eliminados"

_MD_HEADER = """# Presets de medicion - origen y procedencia

Cada preset son dos archivos: `<nombre>.s1p` (Touchstone 1 puerto) y
`<nombre>.json` (metadata). La tabla de abajo se **regenera automaticamente**
desde los sidecars cada vez que se guarda o elimina un preset desde el
asistente: no la edites a mano, edita el `.json` correspondiente.

**Origen del material historico:** los presets de las campanas previas salen de
la carpeta de antecedentes de la sonda,
<https://drive.google.com/drive/folders/1vWChEqFr98Cv9aOmgLwDoIE1WwvhoSyR?usp=drive_link>.

> **Advertencia.** En esa carpeta, la mayoria de los `.s1p` de las campanas
> **UTN 2021 y UTN 2024** NO contienen S11: contienen la **permitividad ya
> calculada** guardada con extension `.s1p`. Nunca importarlos como mediciones.
> Los unicos S11 validos verificados son los de 2026 (Copper Mountain R60), las
> simulaciones CST 2020 y los sets NanoVNA de App_ME2 / Kupce 2024.

{begin}
{end}

{log_header}

Registro de presets borrados desde el asistente (append-only).
""".format(begin=_AUTO_BEGIN, end=_AUTO_END, log_header=_LOG_HEADER)


@dataclass
class PresetMeta:
    """Provenance of one stored sweep."""

    name: str
    display_name: str = ""
    liquid_key: Optional[str] = None      # water | ipa | ethanol | methanol | air | ...
    role: str = ROLE_REFERENCE            # open | short | reference | dut
    source: str = SOURCE_MEASURED         # measured | imported | simulated
    instrument: str = ""
    probe: str = ""
    temperature_c: Optional[float] = None
    acquired: str = ""                    # ISO-8601, when the sweep was taken
    saved: str = ""                       # ISO-8601, when it entered the library
    technique: str = ""
    points: Optional[int] = None
    f_start_hz: Optional[float] = None
    f_stop_hz: Optional[float] = None
    precal_open_applied: bool = False
    origin_note: str = ""
    schema_version: int = SCHEMA_VERSION

    @property
    def has_metadata(self) -> bool:
        """False for legacy presets recovered from a bare .s1p."""
        return self.liquid_key is not None

    def label(self) -> str:
        """Text shown in the preset combo boxes."""
        if not self.has_metadata:
            return self.name + "  (sin metadata)"
        return self.display_name or self.name


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

def get_preset_dir() -> Path:
    path = get_calibration_path(_PRESET_EXE_PATH, _PRESET_DEV_PATH, Path(__file__).resolve())
    path.mkdir(parents=True, exist_ok=True)
    return path


def _s1p_path(name: str) -> Path:
    return get_preset_dir() / (name + ".s1p")


def _json_path(name: str) -> Path:
    return get_preset_dir() / (name + ".json")


# --------------------------------------------------------------------------- #
# Read
# --------------------------------------------------------------------------- #

def read_meta(name: str) -> PresetMeta:
    """Return the sidecar metadata, or a legacy placeholder when there is none."""
    path = _json_path(name)
    if not path.exists():
        return PresetMeta(name=name, display_name=name, liquid_key=None, role="")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("[preset_store] unreadable sidecar for '%s'; treating as legacy", name)
        return PresetMeta(name=name, display_name=name, liquid_key=None, role="")
    known = set(PresetMeta.__dataclass_fields__)
    fields = {k: v for k, v in raw.items() if k in known}
    fields["name"] = name
    return PresetMeta(**fields)


def list_presets(liquid_key: Optional[str] = None,
                 role: Optional[str] = None,
                 include_legacy: bool = True) -> List[PresetMeta]:
    """List presets, optionally filtered by liquid and/or role.

    Legacy presets (no sidecar) match every filter by default: their liquid is
    unknown, so hiding them would silently drop data the user saved earlier.
    """
    out: List[PresetMeta] = []
    try:
        names = sorted(p.stem for p in get_preset_dir().glob("*.s1p"))
    except Exception:
        logger.exception("[preset_store] could not list the preset directory")
        return out

    for name in names:
        meta = read_meta(name)
        if not meta.has_metadata:
            if include_legacy:
                out.append(meta)
            continue
        if liquid_key is not None and meta.liquid_key != liquid_key:
            continue
        if role is not None and meta.role != role:
            continue
        out.append(meta)
    return out


def load_preset(name: str) -> Tuple[np.ndarray, np.ndarray, PresetMeta]:
    """Read a preset sweep. Raises if the Touchstone cannot be parsed."""
    import skrf as rf

    net = rf.Network(str(_s1p_path(name)))
    freqs = np.asarray(net.f, dtype=float)
    s11 = np.asarray(net.s[:, 0, 0], dtype=complex)
    return freqs, s11, read_meta(name)


def preset_exists(name: str) -> bool:
    return _s1p_path(name).exists()


# --------------------------------------------------------------------------- #
# Write
# --------------------------------------------------------------------------- #

def save_preset(name: str, freqs, s11, meta: PresetMeta) -> Path:
    """Write ``<name>.s1p`` + ``<name>.json`` and refresh PRESETS.md."""
    import skrf as rf

    freqs = np.asarray(freqs, dtype=float)
    s11 = np.asarray(s11, dtype=complex)

    meta.name = name
    meta.points = int(len(freqs))
    meta.f_start_hz = float(freqs[0])
    meta.f_stop_hz = float(freqs[-1])
    meta.saved = meta.saved or datetime.now().isoformat(timespec="seconds")
    meta.acquired = meta.acquired or meta.saved
    meta.display_name = meta.display_name or name
    meta.schema_version = SCHEMA_VERSION

    dest = _s1p_path(name)
    net = rf.Network(frequency=freqs, s=s11.reshape(-1, 1, 1), z0=50)
    net.write_touchstone(str(dest))
    _json_path(name).write_text(
        json.dumps(asdict(meta), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    refresh_presets_md()
    logger.info("[preset_store] saved preset '%s' (%d pts)", name, meta.points)
    return dest


def delete_preset(name: str) -> bool:
    """Remove both files and log the deletion in PRESETS.md."""
    meta = read_meta(name)
    removed = False
    for path in (_s1p_path(name), _json_path(name)):
        try:
            if path.exists():
                path.unlink()
                removed = True
        except Exception:
            logger.exception("[preset_store] could not delete %s", path)
    if removed:
        refresh_presets_md()
        _log_deletion(meta)
        logger.info("[preset_store] deleted preset '%s'", name)
    return removed


# --------------------------------------------------------------------------- #
# PRESETS.md
# --------------------------------------------------------------------------- #

def _fmt_hz(hz) -> str:
    if hz is None:
        return "-"
    hz = float(hz)
    if hz >= 1e9:
        return "{:.4g} GHz".format(hz / 1e9)
    if hz >= 1e6:
        return "{:.4g} MHz".format(hz / 1e6)
    return "{:.4g} kHz".format(hz / 1e3)


def _md_row(m: PresetMeta) -> str:
    if not m.has_metadata:
        return ("| `" + m.name + "` | - | - | - | - | - | "
                "sin sidecar JSON (preset previo a la metadata) |")
    span = _fmt_hz(m.f_start_hz) + " - " + _fmt_hz(m.f_stop_hz)
    temp = "{:.1f} C".format(m.temperature_c) if m.temperature_c is not None else "-"
    origin = " ".join(x for x in (m.instrument, m.probe) if x) or "-"
    notes = m.origin_note or ""
    if m.precal_open_applied:
        notes = (notes + " - normalizado con OPEN").strip(" -")
    detail = (origin + ". " + notes).strip().rstrip(".")
    return ("| `" + m.name + "` | " + (m.liquid_key or "-") + " | " + (m.role or "-")
            + " | " + m.source + " | " + span + " / " + str(m.points) + " pts | "
            + temp + " | " + detail + " |")


def refresh_presets_md() -> Path:
    """Regenerate the auto table from the sidecars, preserving the rest of the file."""
    md_path = get_preset_dir() / _MD_NAME
    text = md_path.read_text(encoding="utf-8") if md_path.exists() else _MD_HEADER
    if _AUTO_BEGIN not in text or _AUTO_END not in text:
        text = _MD_HEADER

    presets = list_presets()
    lines = [_AUTO_BEGIN, "", "## Presets disponibles ({})".format(len(presets)), ""]
    if presets:
        lines += [
            "| Preset | Liquido | Rol | Fuente | Barrido | Temp. | Origen |",
            "|---|---|---|---|---|---|---|",
        ] + [_md_row(m) for m in presets]
    else:
        lines.append("*(no hay presets guardados)*")
    lines += ["", _AUTO_END]

    head, _, rest = text.partition(_AUTO_BEGIN)
    _, _, tail = rest.partition(_AUTO_END)
    md_path.write_text(head + "\n".join(lines) + tail, encoding="utf-8")
    return md_path


def _log_deletion(meta: PresetMeta) -> None:
    md_path = get_preset_dir() / _MD_NAME
    if not md_path.exists():
        return
    stamp = datetime.now().isoformat(timespec="seconds")
    detail = " ({}, {})".format(meta.liquid_key, meta.role) if meta.has_metadata else ""
    entry = "- **" + stamp + "** - eliminado `" + meta.name + "`" + detail + "\n"
    text = md_path.read_text(encoding="utf-8")
    if _LOG_HEADER in text:
        text = text.rstrip("\n") + "\n" + entry
    else:
        text = text.rstrip("\n") + "\n\n" + _LOG_HEADER + "\n\n" + entry
    md_path.write_text(text, encoding="utf-8")
