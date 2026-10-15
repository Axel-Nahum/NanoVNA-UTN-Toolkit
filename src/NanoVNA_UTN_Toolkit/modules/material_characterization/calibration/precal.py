"""
Per-step pre-calibration: correcting what handling the probe changes.

EN: Handling the probe between steps (moving the cable, reconnecting, cleaning
    it) changes the cable and connectors, so a step measured afterwards no
    longer shares the state the other standards were measured in. The
    pre-calibration of a step measures a reference right after that handling,
    c = S11 of the probe in air (OPEN), or c = -S11 of the SHORT, and refers
    the step back to the reference state:

        s11_corr = s11 * c0 / c

    where c0 is the same reference in the state of the session: the OPEN of
    step 1 (or the SHORT of step 2). It corrects the change that acts as a
    factor (cable phase and loss); a change of match is not visible to a
    single reference. Each pre-calibration belongs to its step only: the
    other steps keep their own measurement. Dividing only by c (s11 / c, as
    the wizard used to) leaves the step on another scale than the steps
    without pre-cal: with the 2026 21 mm sweeps and a -0.3 dB / 0.1 ns cable
    change, eps' of ethanol was off by up to 0.48, against ~1e-13 with c0.

ES: Manipular la sonda entre pasos (mover el cable, reconectar, limpiarla)
    cambia el cable y los conectores, asi que un paso medido despues ya no
    comparte el estado en que se midieron los demas patrones. La
    pre-calibracion de un paso mide una referencia justo despues de esa
    manipulacion, c = S11 de la sonda en el aire (OPEN), o c = -S11 del
    SHORT, y refiere el paso al estado de referencia:

        s11_corr = s11 * c0 / c

    donde c0 es la misma referencia en el estado de la sesion: el OPEN del
    paso 1 (o el SHORT del paso 2). Corrige el cambio que actua como un
    factor (fase y perdida del cable); un cambio de adaptacion no se ve con
    una sola referencia. Cada pre-calibracion es solo de su paso: los demas
    pasos conservan su propia medicion. Dividir solo por c (s11 / c, como
    hacia el asistente) deja el paso en otra escala que los pasos sin
    pre-cal: con los barridos 2026 de la sonda de 21 mm y un cambio de cable
    de -0.3 dB / 0.1 ns, el eps' del etanol erraba hasta 0.48, contra ~1e-13
    con c0.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

KIND_OPEN = "open"
KIND_SHORT = "short"
KINDS = (KIND_OPEN, KIND_SHORT)

# Standard whose sweep is c0 for each kind. That step defines the reference
# state, so it cannot be pre-calibrated with its own kind.
REFERENCE_STANDARD = {KIND_OPEN: "open", KIND_SHORT: "short"}

# Same frequency tolerance the calibration uses to compare standards' grids:
# a grid read back from a Touchstone file is not bit-identical to the original.
FREQ_ATOL_HZ = 1000.0


@dataclass(frozen=True, eq=False)
class PrecalReference:
    """The c(f) of one step: its reference measured right after handling the probe."""

    freqs: np.ndarray
    divisor: np.ndarray
    kind: str = KIND_OPEN

    def __post_init__(self):
        freqs = np.asarray(self.freqs, dtype=float).copy()
        divisor = np.asarray(self.divisor, dtype=complex).copy()
        if self.kind not in KINDS:
            raise ValueError(f"Unknown pre-calibration kind '{self.kind}' (expected one of {KINDS}).")
        if freqs.ndim != 1 or freqs.shape != divisor.shape or freqs.size == 0:
            raise ValueError("Pre-calibration reference: frequencies and c(f) must be "
                             "1-D arrays of the same, non-zero length.")
        if not np.all(np.isfinite(divisor)) or np.any(divisor == 0):
            raise ValueError("Pre-calibration reference: c(f) must be finite and non-zero.")
        object.__setattr__(self, "freqs", freqs)
        object.__setattr__(self, "divisor", divisor)

    @classmethod
    def from_sweep(cls, freqs, s11_reference, kind: str = KIND_OPEN) -> "PrecalReference":
        """Build c(f) from the measured OPEN (c = S11) or SHORT (c = -S11)."""
        s11_reference = np.asarray(s11_reference, dtype=complex)
        divisor = -s11_reference if kind == KIND_SHORT else s11_reference
        return cls(freqs=freqs, divisor=divisor, kind=kind)

    @property
    def reference_standard(self) -> str:
        """Standard whose sweep gives c0 for this kind ("open" or "short")."""
        return REFERENCE_STANDARD[self.kind]

    def matches(self, freqs) -> bool:
        """True when ``freqs`` is the grid c(f) was taken on."""
        freqs = np.asarray(freqs, dtype=float)
        return (freqs.shape == self.freqs.shape
                and bool(np.allclose(freqs, self.freqs, rtol=0, atol=FREQ_ATOL_HZ)))

    def correct(self, s11_raw, c0) -> np.ndarray:
        """s11 * c0 / c: the step's sweep referred back to the session state."""
        return np.asarray(s11_raw, dtype=complex) * np.asarray(c0, dtype=complex) / self.divisor
