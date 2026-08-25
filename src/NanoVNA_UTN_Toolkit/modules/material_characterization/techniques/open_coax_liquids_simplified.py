"""
Built-in technique: open-ended coaxial probe, simplified (single reference).

EN: Declares the standards and wizard steps for the SIMPLIFIED permittivity
    method: Short, Open (air) and ONE known reference liquid (default water),
    plus the unknown. The result comes from a closed-form barycentric formula
    (see ``algorithms/simplified_solver``) -- no quintic, no root ambiguity --
    at the cost of neglecting the probe's radiation term, so accuracy degrades
    toward high frequency / large probes. One liquid less to prepare and clean
    makes it the quick-look counterpart of ``open_coax_liquids``.

ES: Declara los patrones y pasos del asistente para el metodo SIMPLIFICADO de
    permitividad: Short, Open (aire) y UN liquido de referencia conocido (agua
    por defecto), mas la incognita. El resultado sale de una formula
    baricentrica cerrada (ver ``algorithms/simplified_solver``) -- sin quintico
    ni ambiguedad de raices -- al costo de despreciar el termino de radiacion
    de la sonda, por lo que la exactitud degrada hacia alta frecuencia / sondas
    grandes. Un liquido menos que preparar y limpiar lo vuelve la variante
    rapida de ``open_coax_liquids``.

The standard keys (open/short/ref1/dut) deliberately MATCH the full
technique's keys so measurements carry over between the two (the "extend to
full method" flow re-uses everything already measured and only adds ref2).

Algorithm source / Fuente del algoritmo:
    Eq. (18) of Higa/Cismondi/Grass (2016); A. Henze et al., IEEE ARGENCON
    2024. Reference implementation ``funciones.get_er_DUTm`` in
    https://github.com/pguzmanUTN/Sonda_2026_py
"""

from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.base import (
    StandardDef,
    WizardStepDef,
    TechniqueDescriptor,
    StepKind,
    StandardKind,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.registry import register

TECHNIQUE_ID = "open_coax_liquids_simplified"

# --- Calibration standards (ordered) -------------------------------------- #
# Same keys as open_coax_liquids so a session can be extended to the full
# method without re-measuring anything.
_OPEN = StandardDef(key="open", kind=StandardKind.FIXED, label_token="open")
_SHORT = StandardDef(key="short", kind=StandardKind.FIXED, label_token="short")
_REF1 = StandardDef(
    key="ref1",
    kind=StandardKind.REFERENCE_LIQUID,
    label_token="reference",
    default_liquid_key="water",
)
_DUT = StandardDef(key="dut", kind=StandardKind.DUT, label_token="dut")

_STANDARDS = (_OPEN, _SHORT, _REF1)

# --- Wizard steps after the intro (current_step 1..N) --------------------- #
_STEPS = (
    WizardStepDef(StepKind.CONFIG, title_token="config"),
    WizardStepDef(StepKind.STANDARD_MEASURE, title_token="open", standard=_OPEN),
    WizardStepDef(StepKind.STANDARD_MEASURE, title_token="short", standard=_SHORT),
    WizardStepDef(StepKind.STANDARD_MEASURE, title_token="reference", standard=_REF1),
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
        "simplified_solver:solve_epsilon_simplified"
    ),
    result_chart="epsilon_vs_freq",
)

register(DESCRIPTOR)
