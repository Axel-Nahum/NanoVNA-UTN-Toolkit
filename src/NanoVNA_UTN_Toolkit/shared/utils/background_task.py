"""
Run a plain function on a QThread and deliver its result on the GUI thread.

EN: ``run_in_background(fn, args, on_done, registry)`` moves a ``BackgroundWorker``
to a parent-less ``QThread`` and connects its ``finished`` signal to
``on_done``. ``on_done`` must be a bound method of a QObject that lives on the
GUI thread (a window): Qt then queues the call to that thread. A closure or
lambda would run on the worker thread instead (see shared/utils/real_time).

The owner keeps the ``(thread, worker, slot)`` records in ``registry`` so the
QThread is never garbage-collected while running. When the owner closes,
``detach_background_threads(registry)`` drops the result slot and parks the
running threads in a module list until they exit: never ``terminate()``, never
a QThread destroyed while running.

ES: Ejecuta ``fn`` en un QThread y entrega el resultado en el hilo de UI a
traves de un metodo ligado de la ventana; al cerrar, los hilos en curso se
desconectan y se dejan terminar solos.
"""

from PySide6.QtCore import QObject, QThread, Signal


class BackgroundWorker(QObject):
    """``finished`` carries ``fn(*args)``'s return value, or the exception it raised."""

    finished = Signal(object)

    def __init__(self, fn, args=()):
        super().__init__()
        self._fn = fn
        self._args = tuple(args)

    def run(self):
        try:
            self.finished.emit(self._fn(*self._args))
        except Exception as exc:   # noqa: BLE001 - delivered to the GUI thread, never raised here
            self.finished.emit(exc)


# Records of owners that closed while their work was still running.
_detached: list = []


def run_in_background(fn, args, on_done, registry: list) -> QThread:
    """Start ``fn(*args)`` on a new QThread; ``on_done(result_or_exception)``
    runs on the GUI thread. The record is kept in ``registry`` until the
    thread exits."""
    thread = QThread()
    worker = BackgroundWorker(fn, args)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(on_done)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    record = (thread, worker, on_done)
    registry.append(record)

    def _forget():
        try:
            registry.remove(record)
        except ValueError:
            pass

    thread.finished.connect(_forget)
    thread.start()
    return thread


def detach_background_threads(registry: list) -> None:
    """The owner is closing: disconnect its result slots and keep the running
    threads alive (in ``_detached``) until they finish on their own."""
    for record in list(registry):
        thread, worker, on_done = record
        try:
            worker.finished.disconnect(on_done)
        except (RuntimeError, TypeError):
            pass
        try:
            running = thread.isRunning()
        except RuntimeError:
            running = False
        if running:
            _detached.append(record)
            thread.finished.connect(
                lambda r=record: _detached.remove(r) if r in _detached else None)
    registry.clear()
