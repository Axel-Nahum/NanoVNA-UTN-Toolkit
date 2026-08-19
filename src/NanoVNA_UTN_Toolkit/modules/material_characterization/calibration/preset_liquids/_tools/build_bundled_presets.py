"""
One-shot builder for the bundled presets shipped with the toolkit.

EN: Converts the reference material of the probe archive into the preset
    format (``.s1p`` + ``.json`` sidecar) used by ``calibration/preset_store``.
    Committed for traceability: it documents exactly which source file became
    which preset, so the library can be rebuilt or audited later.

ES: Convierte el material de referencia del archivo historico de la sonda al
    formato de presets (``.s1p`` + sidecar ``.json``) que usa
    ``calibration/preset_store``. Se commitea por trazabilidad: documenta
    exactamente que archivo de origen dio lugar a cada preset, para poder
    reconstruir o auditar la biblioteca mas adelante.

Sources / Fuentes
-----------------
Probe archive (Google Drive):
    https://drive.google.com/drive/folders/1vWChEqFr98Cv9aOmgLwDoIE1WwvhoSyR?usp=drive_link
    Local copy assumed at ``D:\\temp\\Sonda Open Ended - Antecedentes``.

  * ``Mediciones 2026 con sonda 21 mm y 3 mm\\`` -- real S11, Copper Mountain
    R60 (S/N 23103002), Touchstone ``# HZ S MA R 50``. Verified good: air is
    ~1 angle 0 and short ~1 angle 180 across the whole band.
  * ``UTN 2020 - Simulacion  sonda CST para medicion materiales\\MATLAB\\
    Calculo Er\\ws_patrones_2020.mat`` -- CST simulation, magnitude and phase
    (degrees) stored in separate variables over ``100e6:100e6:10e9``.

NOT imported on purpose: the ``.s1p`` files of the UTN 2021 and UTN 2024
campaigns hold ALREADY-COMPUTED permittivity, not S11, despite the extension.

Usage
-----
    python build_bundled_presets.py [--archive PATH] [--dry-run]
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

DEFAULT_ARCHIVE = Path(r"D:\temp\Sonda Open Ended - Antecedentes")

_R60 = "Copper Mountain R60 (S/N 23103002)"
_DRIVE_NOTE = "Antecedentes de la sonda (Drive UTN)"

# --------------------------------------------------------------------------- #
# 2026 campaign -- real measurements
# --------------------------------------------------------------------------- #
# (source file, preset name, liquid_key, role, probe, acquired, note)
_MEAS_2026 = [
    ("sonda21-aire.s1p", "open_air_r60_probe21_2026", "air", ps.ROLE_OPEN,
     "open-ended coax 21 mm", "2026-06-24T12:16:30", "Sonda al aire (patron OPEN)"),
    ("sonda21-short.s1p", "short_r60_probe21_2026", "short", ps.ROLE_SHORT,
     "open-ended coax 21 mm", "2026-06-24T12:15:00", "Sonda cortocircuitada"),
    ("sonda21-agua25-06.s1p", "water_r60_probe21_2026", "water", ps.ROLE_REFERENCE,
     "open-ended coax 21 mm", "2026-06-25T14:44:00", "Agua destilada"),
    ("sonda21-alcisoprop25-06.s1p", "ipa_r60_probe21_2026", "ipa", ps.ROLE_REFERENCE,
     "open-ended coax 21 mm", "2026-06-25T14:38:00", "Alcohol isopropilico (propan-2-ol)"),
    ("sonda21-alc-etilico25-06.s1p", "ethanol_r60_probe21_2026", "ethanol", ps.ROLE_REFERENCE,
     "open-ended coax 21 mm", "2026-06-25T15:06:00", "Alcohol etilico"),
    ("sonda 21-agua 35mm prof base plastico ancha 06-08.s1p",
     "water_deep35mm_r60_probe21_2026", "water", ps.ROLE_REFERENCE,
     "open-ended coax 21 mm", "2026-08-06T17:08:00",
     "Agua a 35 mm de profundidad, base plastica ancha"),

    ("sonda3-aire.s1p", "open_air_r60_probe3_2026", "air", ps.ROLE_OPEN,
     "open-ended coax 3 mm", "2026-06-24T00:00:00", "Sonda al aire (patron OPEN)"),
    ("sonda3-short.s1p", "short_r60_probe3_2026", "short", ps.ROLE_SHORT,
     "open-ended coax 3 mm", "2026-06-24T00:00:00", "Sonda cortocircuitada"),
    ("sonda3-agua.s1p", "water_r60_probe3_2026", "water", ps.ROLE_REFERENCE,
     "open-ended coax 3 mm", "2026-06-24T00:00:00", "Agua destilada"),
    ("sonda3-alc-isoprop.s1p", "ipa_r60_probe3_2026", "ipa", ps.ROLE_REFERENCE,
     "open-ended coax 3 mm", "2026-06-24T00:00:00", "Alcohol isopropilico (propan-2-ol)"),
    ("sonda3-alc-etilico.s1p", "ethanol_r60_probe3_2026", "ethanol", ps.ROLE_REFERENCE,
     "open-ended coax 3 mm", "2026-06-24T00:00:00", "Alcohol etilico"),
]

# --------------------------------------------------------------------------- #
# CST 2020 -- simulation
# --------------------------------------------------------------------------- #
# (mat variable stem, preset name, liquid_key, role, note)
_SIM_CST = [
    ("open", "sim_cst2020_open_air", "air", ps.ROLE_OPEN, "Patron OPEN simulado"),
    ("short", "sim_cst2020_short", "short", ps.ROLE_SHORT, "Patron SHORT simulado"),
    ("agua", "sim_cst2020_water", "water", ps.ROLE_REFERENCE, "Agua simulada"),
    ("alcohol", "sim_cst2020_alcohol", "ipa", ps.ROLE_REFERENCE, "Alcohol simulado"),
    ("musculoaceite000", "sim_cst2020_muscle_dut", "muscle", ps.ROLE_DUT,
     "Musculo sin capa de aceite; el .mat trae Er_musculo_real / Er_musculo_tgD "
     "como valor teorico esperado"),
]
_CST_MAT = (r"UTN 2020 - Simulacion  sonda CST para medicion materiales"
            r"\MATLAB\Calculo Er\ws_patrones_2020.mat")
# Frequency grid declared in Calculo_Er.m: frec = 100e6:100e6:10e9
_CST_FREQS = np.arange(1, 101, dtype=float) * 100e6


def _import_2026(archive: Path, dry_run: bool) -> int:
    import skrf as rf

    folder = archive / "Mediciones 2026 con sonda 21 mm y 3 mm"
    if not folder.is_dir():
        print("  [skip] no existe {}".format(folder))
        return 0

    count = 0
    for filename, name, liquid, role, probe, acquired, note in _MEAS_2026:
        src = folder / filename
        if not src.exists():
            print("  [skip] falta {}".format(src.name))
            continue
        net = rf.Network(str(src))
        freqs = np.asarray(net.f, dtype=float)
        s11 = np.asarray(net.s[:, 0, 0], dtype=complex)
        meta = ps.PresetMeta(
            name=name,
            display_name="{} - R60 {} ({})".format(
                note.split("(")[0].strip(), probe.split()[-2] + " " + probe.split()[-1],
                acquired[:10]),
            liquid_key=liquid, role=role, source=ps.SOURCE_MEASURED,
            instrument=_R60, probe=probe, temperature_c=None, acquired=acquired,
            technique="open_coax_liquids",
            origin_note="{}. {}. Archivo original: {}".format(note, _DRIVE_NOTE, filename),
        )
        print("  {:34s} {:5d} pts  {:.0f}-{:.0f} Hz".format(name, len(freqs), freqs[0], freqs[-1]))
        if not dry_run:
            ps.save_preset(name, freqs, s11, meta)
        count += 1
    return count


def _import_cst(archive: Path, dry_run: bool) -> int:
    try:
        from scipy.io import loadmat
    except ImportError:
        print("  [skip] scipy no disponible; no se pueden leer las simulaciones CST")
        return 0

    mat_path = archive / _CST_MAT
    if not mat_path.exists():
        print("  [skip] no existe {}".format(mat_path))
        return 0

    data = loadmat(str(mat_path))
    count = 0
    for stem, name, liquid, role, note in _SIM_CST:
        mod_key, ph_key = "modS11" + stem, "phaseS11" + stem
        if mod_key not in data or ph_key not in data:
            print("  [skip] faltan {} / {} en el .mat".format(mod_key, ph_key))
            continue
        mod = np.asarray(data[mod_key], dtype=float).ravel()
        # CST exports the phase in degrees in a separate variable.
        phase_deg = np.asarray(data[ph_key], dtype=float).ravel()
        s11 = mod * np.exp(1j * np.deg2rad(phase_deg))
        freqs = _CST_FREQS[: len(s11)]
        meta = ps.PresetMeta(
            name=name,
            display_name="{} - simulacion CST 2020".format(note.split(";")[0].strip()),
            liquid_key=liquid, role=role, source=ps.SOURCE_SIMULATED,
            instrument="CST Studio Suite (simulacion)", probe="open-ended coax (modelo CST)",
            temperature_c=None, acquired="2020-01-01T00:00:00",
            technique="open_coax_liquids",
            origin_note=("{}. Reconstruido de {} / {} en ws_patrones_2020.mat "
                         "(magnitud lineal + fase en grados, igual que pol2complex.m). "
                         "El |S11| de origen supera levemente 1 en algunos puntos: es un "
                         "artefacto del post-proceso de CST, no un error de conversion. "
                         "{}. NO es una medicion.").format(note, mod_key, ph_key, _DRIVE_NOTE),
        )
        print("  {:34s} {:5d} pts  {:.0f}-{:.0f} Hz".format(name, len(freqs), freqs[0], freqs[-1]))
        if not dry_run:
            ps.save_preset(name, freqs, s11, meta)
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE,
                        help="carpeta local de antecedentes de la sonda")
    parser.add_argument("--dry-run", action="store_true",
                        help="listar lo que se importaria sin escribir nada")
    args = parser.parse_args()

    print("Destino: {}".format(ps.get_preset_dir()))
    print("Mediciones 2026 (Copper Mountain R60):")
    n1 = _import_2026(args.archive, args.dry_run)
    print("Simulaciones CST 2020:")
    n2 = _import_cst(args.archive, args.dry_run)

    if not args.dry_run:
        ps.refresh_presets_md()
    print("\n{} presets {}.".format(n1 + n2, "listados" if args.dry_run else "escritos"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
