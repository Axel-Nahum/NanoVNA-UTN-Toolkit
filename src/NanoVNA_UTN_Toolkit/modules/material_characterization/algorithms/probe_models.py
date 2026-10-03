"""
Open-ended coaxial probes known to the toolkit and their capacitive model.

EN: The indicative (dotted) S11 of a reference liquid uses the low-frequency
    capacitive model of the probe, ``Y = j*w*C0*eps_r``. C0 depends on the
    probe geometry: a single generic value (0.05 pF) misses both probes of the
    course by a factor of 2.5-6. Each known probe therefore carries its own C0,
    least-squares fitted to the bundled water and IPA presets of that probe
    (see ``fit_c0``). The probe also tags which presets belong to it, so a
    session never mixes sweeps from different probes.

ES: El S11 indicativo (punteado) de un liquido de referencia usa el modelo
    capacitivo de baja frecuencia de la sonda, ``Y = j*w*C0*eps_r``. C0 depende
    de la geometria de la sonda: un unico valor generico (0.05 pF) le erra a las
    dos sondas del curso por un factor de 2.5-6. Por eso cada sonda conocida
    lleva su propio C0, ajustado por minimos cuadrados a los presets de agua e
    IPA incluidos para esa sonda (ver ``fit_c0``). La sonda ademas identifica
    que presets le pertenecen, para que una sesion nunca mezcle barridos de
    sondas distintas.

The model is ORIENTATIVE only: it ignores the fringing field outside the
liquid, radiation (which grows with frequency) and the connector. The real
probe constants are what the 4-standard calibration determines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    NOMINAL_PROBE_C0_F,
)

#: Reference impedance of the capacitive model, in ohms.
Z0_OHM = 50.0


@dataclass(frozen=True)
class ProbeModel:
    """
    One open-ended coaxial probe.

    Attributes
    ----------
    key : str
        Stable identifier, stored in sessions and calibration kits.
    display_name : str
        Default label (localized labels live in the i18n resources).
    c0_f : float
        Capacitance C0 of ``Y = j*w*C0*eps_r``, in farads.
    preset_probe : str
        Value of ``PresetMeta.probe`` for sweeps taken with this probe. Empty
        for the generic entry, which matches presets of unknown probe.
    c0_source : str
        Where C0 comes from (shown next to the indicative curve).
    fit_band_hz : tuple(float, float) or None
        Band used to fit C0, where the capacitive model holds for this probe.
    """

    key: str
    display_name: str
    c0_f: float
    preset_probe: str
    c0_source: str
    fit_band_hz: Optional[Tuple[float, float]] = None


GENERIC_PROBE_KEY = "generic"

# C0 values: ``fit_c0`` on the bundled 18 C water + IPA presets of each probe
# (tests/test_probe_models.py re-fits them, so a rebuilt preset set cannot
# silently drift away from these numbers).
_PROBES: List[ProbeModel] = [
    ProbeModel(
        key="probe3mm",
        display_name="3 mm probe",
        c0_f=0.0190e-12,
        preset_probe="open-ended coax 3 mm",
        c0_source="fitted to the bundled water/IPA presets (R60, 18 C), 100 MHz - 1 GHz",
        fit_band_hz=(100e6, 1e9),
    ),
    ProbeModel(
        key="probe21mm",
        display_name="21 mm probe",
        c0_f=0.1166e-12,
        preset_probe="open-ended coax 21 mm",
        c0_source="fitted to the bundled water/IPA presets (R60, 18 C), 1 - 200 MHz",
        fit_band_hz=(1e6, 200e6),
    ),
    ProbeModel(
        key=GENERIC_PROBE_KEY,
        display_name="Other probe (generic C0)",
        c0_f=NOMINAL_PROBE_C0_F,
        preset_probe="",
        c0_source="generic order-of-magnitude value, not fitted to any probe",
    ),
]

PROBES: Dict[str, ProbeModel] = {p.key: p for p in _PROBES}


def get_probe(key: Optional[str]) -> ProbeModel:
    """Probe registered under ``key``; the generic one for None / unknown keys."""
    return PROBES.get(key or GENERIC_PROBE_KEY, PROBES[GENERIC_PROBE_KEY])


def list_probes() -> List[ProbeModel]:
    """All probes, in display order (known probes first, generic last)."""
    return list(_PROBES)


def fit_c0(references) -> float:
    """
    Least-squares C0 of ``Y = j*w*C0*eps_r`` from measured references.

    ``references`` is an iterable of ``(f_hz, s11, eps_r)`` arrays (one tuple
    per liquid, restricted by the caller to the band where the capacitive
    model holds). Returns C0 in farads.
    """
    num = 0.0
    den = 0.0
    for f_hz, s11, eps in references:
        f_hz = np.asarray(f_hz, dtype=float)
        s11 = np.asarray(s11, dtype=complex)
        eps = np.asarray(eps, dtype=complex)
        y = (1.0 - s11) / (1.0 + s11)                 # normalized admittance
        a = 1j * 2.0 * np.pi * f_hz * Z0_OHM * eps     # y = a * C0
        ok = np.isfinite(y) & np.isfinite(a)
        num += float(np.real(np.sum(np.conj(a[ok]) * y[ok])))
        den += float(np.sum(np.abs(a[ok]) ** 2))
    if den == 0.0:
        raise ValueError("no usable reference points to fit C0")
    return num / den
