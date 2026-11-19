"""
EN: Borderless spinbox styling for spinboxes wrapped in a themed
    ``QFrame#spinboxContainer`` with external ▲▼ buttons.

    The native buttons are hidden with zero-width subcontrols instead of
    ``ButtonSymbols.NoButtons``: on Qt 6.12, NoButtons combined with any widget
    stylesheet collapses the inner QLineEdit to 1 px, so typed text is invisible.

ES: Estilo sin borde para spinboxes envueltos en un ``QFrame#spinboxContainer``
    con botones ▲▼ externos.

    Los botones nativos se ocultan con subcontroles de ancho cero en lugar de
    ``ButtonSymbols.NoButtons``: en Qt 6.12, NoButtons junto con cualquier hoja
    de estilo deja el QLineEdit interno en 1 px y el texto escrito no se ve.
"""

from PySide6.QtWidgets import QAbstractSpinBox

_HIDDEN_NATIVE_BUTTONS_CSS = (
    "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,"
    " QSpinBox::up-button, QSpinBox::down-button"
    " { width: 0px; border: none; background: transparent; }"
    "QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow,"
    " QSpinBox::up-arrow, QSpinBox::down-arrow"
    " { image: none; border: none; width: 0px; height: 0px; }"
)


def apply_borderless_spinbox_style(spin: QAbstractSpinBox, padding: str | None = None) -> None:
    """Make ``spin`` borderless/transparent and hide its native buttons.

    ``padding`` is an optional CSS padding value (e.g. ``"0px 2px"``).
    """
    spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
    pad = f" padding: {padding};" if padding else ""
    spin.setStyleSheet(
        f"QDoubleSpinBox, QSpinBox {{ border: none; background: transparent;{pad} }}"
        + _HIDDEN_NATIVE_BUTTONS_CSS
    )
