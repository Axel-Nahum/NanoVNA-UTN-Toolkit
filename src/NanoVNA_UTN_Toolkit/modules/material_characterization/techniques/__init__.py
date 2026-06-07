"""
Characterization technique registry.

EN: A pluggable registry of material-characterization techniques. Each
    technique declares its calibration standards and its ordered wizard steps
    as plain data (no Qt), so the wizard is driven by data instead of
    hard-coded per-method branches. Adding a new technique (a different
    instrument or a non-fluid material) is just adding one descriptor module
    that calls ``register(...)``.

ES: Registro extensible de tecnicas de caracterizacion de materiales. Cada
    tecnica declara sus patrones de calibracion y sus pasos del asistente como
    datos (sin Qt), de modo que el asistente se maneja por datos en lugar de
    ramas fijas por metodo. Agregar una tecnica nueva (otro instrumento o un
    material no liquido) es solo agregar un modulo descriptor que llame a
    ``register(...)``.
"""

from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.base import (
    StandardDef,
    WizardStepDef,
    TechniqueDescriptor,
    StepKind,
    StandardKind,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.registry import (
    register,
    get,
    all_descriptors,
)

# Importing the descriptor module registers the built-in technique(s).
from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import (  # noqa: F401
    open_coax_liquids,
)

__all__ = [
    "StandardDef",
    "WizardStepDef",
    "TechniqueDescriptor",
    "StepKind",
    "StandardKind",
    "register",
    "get",
    "all_descriptors",
]
