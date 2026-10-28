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
        self._callback = None
        self.completed.connect(self._deliver)

    def on_completed(self, callback):
        """Register the GUI-thread handler for ``completed(success, error)``.

        EN: ``completed`` is emitted from the worker thread. A closure connected
            to it directly would run THERE (no receiver object to queue against)
            and touch widgets off the GUI thread. This QThread object lives in
            the GUI thread, so its bound ``_deliver`` slot is queued to the GUI
            thread and calls ``callback`` from it.
        ES: ``completed`` se emite desde el hilo del worker; un closure conectado
            directo correria ahi. El slot ligado ``_deliver`` de este objeto (que
            vive en el hilo de UI) se encola al hilo de UI y llama al callback.
        """
        self._callback = callback

    def _deliver(self, success, error_message):  # runs on the GUI thread
        if self._callback is not None:
            self._callback(success, error_message)

    def run(self):
        try:
            self._work()
        except Exception as exc:
            logger.exception("[PdfCompileTask] PDF compilation failed")
            self.completed.emit(False, str(exc))
            return
        self.completed.emit(True, "")


# Checker threads whose dialog closed while the (1-30 s) LaTeX test compile was
# still running. Terminating them kills a thread inside subprocess/logging and can
# leave locks held; letting the Python wrapper go would destroy a running QThread.
# They finish on their own and delete themselves; the list keeps them referenced.
_orphan_checkers: list = []


def detach_checker_thread(thread, signal, slot):
    """Let a running checker finish unattended.

    EN: Disconnects ``signal`` (the thread's result signal) from ``slot`` so the
        closed dialog is never called back, keeps the thread referenced and lets
        it delete itself once finished. No ``terminate()``, no ``wait()``.
    ES: Desconecta la senal de resultado del slot del dialogo cerrado, mantiene
        la referencia al hilo y deja que se borre solo al terminar. Nunca
        ``terminate()`` ni ``wait()``.
    """
    if thread is None:
        return
    try:
        running = thread.isRunning()
    except RuntimeError:  # C++ object already gone
        return
    if not running:
        return
    try:
        signal.disconnect(slot)
    except (RuntimeError, TypeError):
        pass
    _orphan_checkers.append(thread)
    thread.finished.connect(thread.deleteLater)
    logger.info("[detach_checker_thread] checker thread detached, finishing unattended")


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
