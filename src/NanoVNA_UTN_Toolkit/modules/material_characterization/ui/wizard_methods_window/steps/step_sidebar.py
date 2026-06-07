"""
Wizard step sidebar (progress indicator).

EN: Builds a vertical list of all wizard steps so the user can see the
    previous and upcoming steps at a glance. The current step is highlighted;
    completed steps are marked with a check box glyph (U+2611), and not-yet-done
    or omitted steps with an empty box (U+2610). This makes it easy to
    anticipate what was done and what comes next.

ES: Construye una lista vertical de todos los pasos del asistente para que el
    usuario vea de un vistazo los pasos anteriores y los proximos. El paso
    actual se resalta; los pasos completados se marcan con una casilla tildada
    (U+2611) y los aun no hechos u omitidos con una casilla vacia (U+2610). Asi
    es facil anticipar lo que se hizo y lo que sigue.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.base import StepKind, StandardKind
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid,
)

CHECK_DONE = "☑"      # ☑
CHECK_TODO = "☐"      # ☐


def _step_name(wizard, step_def, texts, liquids):
    """Human label for a step, used in the sidebar."""
    sidebar = texts.get("sidebar", {})
    std_texts = texts.get("standards", {})

    if step_def.kind is StepKind.CONFIG:
        return sidebar.get("config", "Configuration")
    if step_def.kind is StepKind.RESULT:
        return sidebar.get("result", "Result")
    if step_def.kind is StepKind.DUT_MEASURE:
        name = getattr(wizard, "unknown_liquid_name", "") or ""
        return name.strip() or std_texts.get("dut", {}).get("name", "Unknown liquid")

    standard = step_def.standard
    if standard is not None and standard.kind is StandardKind.REFERENCE_LIQUID:
        key = standard.default_liquid_key
        return liquids.get(key, get_reference_liquid(key).display_name) if key else "Reference"
    if standard is not None:
        return std_texts.get(standard.key, {}).get("name", standard.key.upper())
    return "?"


def _step_done(wizard, step_def, position):
    """Whether a step should show the 'done' check."""
    if step_def.kind in (StepKind.STANDARD_MEASURE, StepKind.DUT_MEASURE):
        return wizard.perm_calibration.is_standard_measured(step_def.standard.key)
    if step_def.kind is StepKind.CONFIG:
        return wizard.current_step > position
    return False  # result has no check


def build_step_sidebar(wizard, descriptor, texts) -> QWidget:
    """Return a sidebar widget listing every step with status + highlight."""
    liquids = texts.get("liquids", {})

    frame = QFrame()
    frame.setFrameShape(QFrame.StyledPanel)
    frame.setStyleSheet("QFrame { border: 1px solid #555; border-radius: 6px; }")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(6)

    header = QLabel(texts.get("sidebar", {}).get("title", "Steps"))
    header.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")
    layout.addWidget(header)

    for position, step_def in enumerate(descriptor.steps, start=1):
        name = _step_name(wizard, step_def, texts, liquids)
        done = _step_done(wizard, step_def, position)
        is_current = position == wizard.current_step

        glyph = CHECK_DONE if done else CHECK_TODO
        label = QLabel(f"{glyph}  {position}. {name}")
        if is_current:
            label.setStyleSheet(
                "border: none; font-size: 13px; font-weight: bold; color: #4da6ff;"
            )
        elif done:
            label.setStyleSheet("border: none; font-size: 12px; color: #7ec97e;")
        else:
            label.setStyleSheet("border: none; font-size: 12px; color: #aaaaaa;")
        layout.addWidget(label)

    layout.addStretch(1)
    frame.setFixedWidth(210)
    return frame
