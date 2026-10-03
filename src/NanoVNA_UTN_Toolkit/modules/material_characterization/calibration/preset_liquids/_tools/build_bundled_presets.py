"""
One-shot builder for the bundled presets shipped with the toolkit.

EN: Converts the reference-liquid sweeps handed over by the course teacher
    (2026-10-02) into the preset format (``.s1p`` + ``.json`` sidecar) used by
    ``calibration/preset_store``. Committed for traceability: it documents
    exactly which source file became which preset, so the library can be
    rebuilt or audited later.

ES: Convierte los barridos de liquidos de referencia que entrego el docente
    del curso (2026-10-02) al formato de presets (``.s1p`` + sidecar ``.json``)
    que usa ``calibration/preset_store``. Se commitea por trazabilidad:
    documenta exactamente que archivo de origen dio lugar a cada preset, para
    poder reconstruir o auditar la biblioteca mas adelante.

Sources / Fuentes
-----------------
Four workbooks "Interpolacion medicion S11 {agua,IPA} sonda {3mm,21mm}.xlsx",
one sheet per frequency band. Per row: frequency (Hz), the MEASURED S11 (real
part in column B, imaginary in column F) and a polynomial fit of each.

  * The columns are labelled Er' / Er'' but hold Re / Im of S11, not
    permittivity (values ~1 at low frequency; checked against the archive).
  * Only the MEASURED columns are used. The polynomial fits were evaluated
    against them and rejected: they reach |S11| > 1 at low frequency, jump at
    the band boundary, and shift the computed ethanol eps' by ~37 % at 10 MHz
    with the 21 mm probe. The wizard already interpolates presets
    linearly onto the configured sweep, which reproduces the data exactly.
  * Temperature ~18 C, as stated by the teacher (measured in winter); it was
    not recorded with the sweeps.

Provenance checked against the probe archive (Google Drive,
https://drive.google.com/drive/folders/1vWChEqFr98Cv9aOmgLwDoIE1WwvhoSyR):
  * 3 mm water / IPA  == sonda3-agua.s1p / sonda3-alc-isoprop.s1p (2026-06-24)
  * 21 mm water       == sonda 21-agua 35mm prof base plastico ancha 06-08.s1p
  * 21 mm IPA         -- not in the archive (closest: sonda21-alcisoprop25-06,
                         median |dS11| 0.027); measurement date not given.

The previous library (2026 R60 open/short/ethanol sweeps and the CST 2020
simulations) was removed on 2026-10-02; see git history for its builder. The
2026 probe-21mm open/short/water/IPA/ethanol set the golden tests rely on now
lives in ``tests/data/``.

Usage
-----
    python build_bundled_presets.py [--source DIR] [--dry-run]

Requires ``openpyxl`` (dev-only; not a runtime dependency of the toolkit).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# Allow running the script straight from its directory.
_SRC = Path(__file__).resolve().parents[6]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import preset_store as ps

DEFAULT_SOURCE = Path.home() / "Downloads"

_R60 = "Copper Mountain R60 (S/N 23103002)"
_TEMP_C = 18.0
_RECEIVED = "Planilla entregada por el docente el 2026-10-02"
_LABEL_NOTE = ("En la planilla las columnas se rotulan Er'/Er'' pero son Re/Im de S11. "
               "Se usan los puntos medidos, no los polinomios de ajuste. "
               "Temperatura ~18 C informada por el docente (no registrada con el barrido)")

# (workbook, preset name, liquid_key, probe, acquired, display name, provenance)
_PRESETS = [
    ("Interpolacion medicion S11 agua sonda 3mm.xlsx", "water_r60_probe3mm_18C", "water",
     "open-ended coax 3 mm", "2026-06-24T00:00:00",
     "Agua destilada - sonda 3 mm (R60, 18 °C)",
     "Coincide con sonda3-agua.s1p del archivo de antecedentes"),
    ("Interpolacion medicion S11 IPA sonda 3mm.xlsx", "ipa_r60_probe3mm_18C", "ipa",
     "open-ended coax 3 mm", "2026-06-24T00:00:00",
     "Alcohol isopropílico - sonda 3 mm (R60, 18 °C)",
     "Coincide con sonda3-alc-isoprop.s1p del archivo de antecedentes"),
    ("Interpolacion medicion S11 agua sonda 21mm.xlsx", "water_r60_probe21mm_18C", "water",
     "open-ended coax 21 mm", "2026-08-06T17:08:00",
     "Agua destilada - sonda 21 mm (R60, 18 °C)",
     "Coincide con 'sonda 21-agua 35mm prof base plastico ancha 06-08.s1p' "
     "(35 mm de profundidad, base plastica ancha)"),
    ("Interpolacion medicion S11 IPA sonda 21mm.xlsx", "ipa_r60_probe21mm_18C", "ipa",
     "open-ended coax 21 mm", "unknown",
     "Alcohol isopropílico - sonda 21 mm (R60, 18 °C)",
     "No figura en el archivo de antecedentes (el mas parecido, "
     "sonda21-alcisoprop25-06.s1p, difiere en mediana 0.027 de |S11|); "
     "fecha de medicion no informada"),
]


def _read_measured(path: Path):
    """Return (freqs, s11) from the MEASURED columns of every sheet, deduplicated."""
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover - dev tool
        raise SystemExit("openpyxl is required: pip install openpyxl") from exc

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = {}
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_row=3, values_only=True):
            f, re_, im_ = row[0], row[1], row[5]
            if not isinstance(f, (int, float)):
                continue
            s = complex(float(re_), float(im_))
            # Adjacent sheets share their boundary frequency: it must agree.
            if f in rows and abs(rows[f] - s) > 1e-9:
                raise ValueError(f"{path.name}: conflicting values at {f} Hz")
            rows[f] = s
    freqs = np.array(sorted(rows), dtype=float)
    s11 = np.array([rows[f] for f in sorted(rows)], dtype=complex)
    return freqs, s11


def build(source: Path, dry_run: bool) -> int:
    count = 0
    for workbook, name, liquid, probe, acquired, display, provenance in _PRESETS:
        src = source / workbook
        if not src.exists():
            print("  [skip] falta {}".format(src))
            continue
        freqs, s11 = _read_measured(src)
        meta = ps.PresetMeta(
            name=name,
            display_name=display,
            liquid_key=liquid,
            role=ps.ROLE_REFERENCE,
            source=ps.SOURCE_MEASURED,
            instrument=_R60,
            probe=probe,
            temperature_c=_TEMP_C,
            acquired=acquired,
            technique="open_coax_liquids",
            origin_note="{}. {}: '{}'. {}".format(provenance, _RECEIVED, workbook, _LABEL_NOTE),
            bundled=True,
        )
        print("  {:26s} {:5d} pts  {:.0f}-{:.0f} Hz  max|S11|={:.4f}".format(
            name, len(freqs), freqs[0], freqs[-1], float(np.abs(s11).max())))
        if not dry_run:
            ps.save_preset(name, freqs, s11, meta, overwrite_bundled=True)
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="carpeta con las cuatro planillas .xlsx")
    parser.add_argument("--dry-run", action="store_true",
                        help="listar lo que se importaria sin escribir nada")
    args = parser.parse_args()

    print("Destino: {}".format(ps.get_preset_dir()))
    n = build(args.source, args.dry_run)
    if not args.dry_run:
        ps.refresh_presets_md()
    print("\n{} presets {}.".format(n, "listados" if args.dry_run else "escritos"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
