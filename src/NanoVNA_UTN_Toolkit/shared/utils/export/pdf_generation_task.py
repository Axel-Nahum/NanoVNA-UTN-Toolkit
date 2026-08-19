"""
Background LaTeX compilation with visible button feedback.

EN: Compiling a report takes several seconds. Run inline it froze the window
    with no sign the click had been registered. These two helpers give every PDF
    export the same behaviour: the button announces that it is working, and the
    blocking part runs off the UI thread.

    Matplotlib is not thread-safe, so figures must be rasterized to PNG on the
    UI thread BEFORE the task starts; only the LaTeX compilation belongs here.

ES: Compilar un reporte lleva varios segundos. Hecho en linea congelaba la
    ventana sin ninguna senal de que el click se hubiera registrado. Estos dos
    helpers le dan a cada exportacion a PDF el mismo comportamiento: el boton
    avisa que esta trabajando, y la parte bloqueante corre fuera del hilo de UI.

    Matplotlib no es thread-safe, asi que las figuras deben rasterizarse a PNG
    en el hilo de UI ANTES de arrancar la tarea; aca solo va la compilacion.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

_BUSY_STYLE = """
    QPushButton {
        background-color: #d68910; color: white; font-weight: bold;
        padding: 6px 16px; border-radius: 5px; font-size: 12px;
    }
    QPushButton:disabled { background-color: #d68910; color: white; }
"""


class PdfCompileTask(QThread):
    """Runs a blocking callable off the UI thread.

    Emits ``completed(success, error_message)``. The callable must not touch any
    Qt widget: report outcomes through the signal instead.
    """

    completed = Signal(bool, str)

    def __init__(self, work, parent=None):
        super().__init__(parent)
        self._work = work

    def run(self):
        try:
            self._work()
        except Exception as exc:
            logger.exception("[PdfCompileTask] PDF compilation failed")
            self.completed.emit(False, str(exc))
            return
        self.completed.emit(True, "")


class GeneratingButton:
    """Puts a button into a visible "working" state and restores it afterwards.

    Text and stylesheet are captured on ``begin`` so the original look comes back
    on ``end`` regardless of how the button was styled.
    """

    def __init__(self, button, busy_text="Generating report…"):
        self._button = button
        self._busy_text = busy_text
        self._text = None
        self._style = None
        self._enabled = True

    def begin(self):
        self._text = self._button.text()
        self._style = self._button.styleSheet()
        self._enabled = self._button.isEnabled()
        self._button.setText(self._busy_text)
        self._button.setStyleSheet(_BUSY_STYLE)
        self._button.setEnabled(False)
        # Repaint now: the click handler keeps running before returning to the
        # event loop, and without this the new state would not be shown.
        self._button.repaint()

    def end(self):
        if self._text is None:
            return
        self._button.setText(self._text)
        self._button.setStyleSheet(self._style)
        self._button.setEnabled(self._enabled)
        self._text = None
