"""
Built-in technique: open-ended coaxial probe for liquid permittivity.

EN: Declares the standards and wizard steps for measuring the complex
    relative permittivity of a liquid with an open-ended coaxial probe on a
    NanoVNA. Calibration uses four standards (Open, Short, and two reference
    liquids); the result step solves and plots epsilon_r(f) of the unknown
    liquid. In the MVP the two reference liquids are fixed to Water and IPA.

ES: Declara los patrones y pasos del asistente para medir la permitividad
    relativa compleja de un liquido con una sonda coaxial open-ended en un
    NanoVNA. La calibracion usa cuatro patrones (Open, Short y dos liquidos de
    referencia); el paso de resultado resuelve y grafica epsilon_r(f) del
    liquido incognita. En el MVP los dos liquidos de referencia son fijos:
    Agua e IPA.

Algorithm source / Fuente del algoritmo:
    "Mediciones de permitividad mediante una sonda coaxial", UTN-FRBA 2024.
"""

from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.base import (
    StandardDef,
    WizardStepDef,
    TechniqueDescriptor,
    StepKind,
    StandardKind,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.registry import register

TECHNIQUE_ID = "open_coax_liquids"

# --- Calibration standards (ordered) -------------------------------------- #
_OPEN = StandardDef(key="open", kind=StandardKind.FIXED, label_token="open")
_SHORT = StandardDef(key="short", kind=StandardKind.FIXED, label_token="short")
_REF1 = StandardDef(
    key="ref1",
    kind=StandardKind.REFERENCE_LIQUID,
    label_token="reference",
    default_liquid_key="water",
)
_REF2 = StandardDef(
    key="ref2",
    kind=StandardKind.REFERENCE_LIQUID,
    label_token="reference",
    default_liquid_key="ipa",
)
_DUT = StandardDef(key="dut", kind=StandardKind.DUT, label_token="dut")

_STANDARDS = (_OPEN, _SHORT, _REF1, _REF2)

# --- Wizard steps after the intro (current_step 1..N) --------------------- #
_STEPS = (
    WizardStepDef(StepKind.CONFIG, title_token="config"),
    WizardStepDef(StepKind.STANDARD_MEASURE, title_token="open", standard=_OPEN),
    WizardStepDef(StepKind.STANDARD_MEASURE, title_token="short", standard=_SHORT),
    WizardStepDef(StepKind.STANDARD_MEASURE, title_token="reference", standard=_REF1),
    WizardStepDef(StepKind.STANDARD_MEASURE, title_token="reference", standard=_REF2),
    WizardStepDef(StepKind.DUT_MEASURE, title_token="dut", standard=_DUT),
    WizardStepDef(StepKind.RESULT, title_token="result"),
)

DESCRIPTOR = TechniqueDescriptor(
    id=TECHNIQUE_ID,
    name_token=TECHNIQUE_ID,            # resolved against methods.<id>.title
    description_token=TECHNIQUE_ID,     # resolved against methods.<id>.description
    material_category="liquid",
    instrument="nanovna_s11",
    standards=_STANDARDS,
    steps=_STEPS,
    solver=(
        "NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms."
        "permittivity_solver:solve_epsilon_r"
    ),
    result_chart="epsilon_vs_freq",
)

register(DESCRIPTOR)
