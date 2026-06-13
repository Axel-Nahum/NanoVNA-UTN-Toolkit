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
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.base import StepKind, StandardKind
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid,
)

CHECK_DONE = "☑"
CHECK_TODO = "☐"


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
    return False


def build_step_sidebar(wizard, descriptor, texts) -> QWidget:
    """Return a sidebar widget listing every step with status + highlight."""
    liquids = texts.get("liquids", {})

    outer = QWidget()
    outer.setObjectName("sidebar")
    outer.setStyleSheet("""
        QWidget#sidebar {
            background-color: #1a1a1a;
            border: 1px solid #3a3a3a;
            border-radius: 8px;
        }
    """)
    outer.setFixedWidth(220)

    layout = QVBoxLayout(outer)
    layout.setContentsMargins(0, 16, 0, 16)
    layout.setSpacing(2)

    header = QLabel(texts.get("sidebar", {}).get("title", "Steps"))
    header.setStyleSheet(
        "font-weight: bold; font-size: 14px; color: #ffffff;"
        "padding: 0 16px 6px 16px; border: none; background: transparent;"
    )
    layout.addWidget(header)

    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet("border: none; border-top: 1px solid #3a3a3a; margin: 0 10px 6px 10px;")
    layout.addWidget(sep)

    for position, step_def in enumerate(descriptor.steps, start=1):
        name = _step_name(wizard, step_def, texts, liquids)
        done = _step_done(wizard, step_def, position)
        is_current = position == wizard.current_step

        row = QWidget()
        row.setObjectName(f"stepRow{position}")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(14, 7, 14, 7)
        row_layout.setSpacing(8)

        if is_current:
            row.setStyleSheet(
                f"QWidget#stepRow{position} {{"
                "background-color: #1a3a5c;"
                "border-left: 3px solid #4da6ff;"
                "}}"
            )
            icon = QLabel("▶")
            icon.setStyleSheet("color: #4da6ff; font-size: 11px; border: none; background: transparent;")
            lbl = QLabel(f"{position}. {name}")
            lbl.setStyleSheet(
                "color: #4da6ff; font-size: 13px; font-weight: bold;"
                "border: none; background: transparent;"
            )
        elif done:
            row.setStyleSheet(f"QWidget#stepRow{position} {{ background: transparent; }}")
            icon = QLabel("✓")
            icon.setStyleSheet("color: #7ec97e; font-size: 12px; border: none; background: transparent;")
            lbl = QLabel(f"{position}. {name}")
            lbl.setStyleSheet(
                "color: #7ec97e; font-size: 12px;"
                "border: none; background: transparent;"
            )
        else:
            row.setStyleSheet(f"QWidget#stepRow{position} {{ background: transparent; }}")
            icon = QLabel("○")
            icon.setStyleSheet("color: #555555; font-size: 12px; border: none; background: transparent;")
            lbl = QLabel(f"{position}. {name}")
            lbl.setStyleSheet(
                "color: #777777; font-size: 12px;"
                "border: none; background: transparent;"
            )

        icon.setFixedWidth(16)
        lbl.setWordWrap(True)
        row_layout.addWidget(icon, alignment=Qt.AlignTop)
        row_layout.addWidget(lbl, stretch=1)
        layout.addWidget(row)

    layout.addStretch(1)
    return outer
