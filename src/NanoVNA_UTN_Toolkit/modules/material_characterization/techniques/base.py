"""
Data structures describing a characterization technique.

EN: A technique is described as plain data: an ordered list of calibration
    standards and an ordered list of wizard steps. The wizard renders each
    step by dispatching on ``WizardStepDef.kind``; measure steps carry the
    ``StandardDef`` they act on. This keeps the wizard generic and makes new
    techniques additive.

ES: Una tecnica se describe como datos: una lista ordenada de patrones de
    calibracion y una lista ordenada de pasos del asistente. El asistente
    renderiza cada paso despachando segun ``WizardStepDef.kind``; los pasos de
    medicion llevan el ``StandardDef`` sobre el que actuan. Esto mantiene el
    asistente generico y hace que las tecnicas nuevas sean aditivas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class StepKind(str, Enum):
    """Kind of wizard step (drives which screen builder is used)."""

    INTRO = "intro"                  # technique selection (step 0)
    CONFIG = "config"                # sweep + temperature + references
    STANDARD_MEASURE = "standard"    # measure one calibration standard
    DUT_MEASURE = "dut"              # measure the Material-Under-Test
    RESULT = "result"                # compute & display epsilon_r


class StandardKind(str, Enum):
    """Kind of calibration standard."""

    FIXED = "fixed"                      # Open / Short (fixed roles)
    REFERENCE_LIQUID = "reference_liquid"  # a known liquid of given epsilon_r
    DUT = "dut"                          # the unknown material


@dataclass(frozen=True)
class StandardDef:
    """
    One calibration standard within a technique.

    Attributes
    ----------
    key : str
        Manager key for this standard (``open``, ``short``, ``ref1``, ``ref2``,
        ``dut``).
    kind : StandardKind
        Role of the standard.
    label_token : str
        i18n token used to label the step / chart trace.
    chart : str
        Which chart to render while measuring (``"smith"``).
    default_liquid_key : str | None
        For reference-liquid standards, the default liquid key (MVP: fixed).
    """

    key: str
    kind: StandardKind
    label_token: str
    chart: str = "smith"
    default_liquid_key: Optional[str] = None


@dataclass(frozen=True)
class WizardStepDef:
    """One ordered wizard step (steps after the intro)."""

    kind: StepKind
    title_token: str
    standard: Optional[StandardDef] = None


@dataclass(frozen=True)
class TechniqueDescriptor:
    """
    A full characterization technique.

    ``steps`` lists the steps shown AFTER the intro screen; the wizard maps
    ``current_step`` (1-based) to ``steps[current_step - 1]``.
    """

    id: str
    name_token: str
    description_token: str
    material_category: str          # e.g. "liquid"
    instrument: str                 # e.g. "nanovna_s11"
    standards: Tuple[StandardDef, ...]
    steps: Tuple[WizardStepDef, ...]
    # Dotted path "module:function" of the solver entry point (informational).
    solver: str = ""
    result_chart: str = "epsilon_vs_freq"

    @property
    def reference_standards(self) -> Tuple[StandardDef, ...]:
        """The reference-liquid standards (those the user can configure)."""
        return tuple(s for s in self.standards if s.kind is StandardKind.REFERENCE_LIQUID)
