"""Route Qt's internal C++ messages through Python's ``logging``.

Qt emits messages such as ``QThread::wait: Thread tried to wait on itself``
directly to ``stderr`` through its *default* message handler. Those lines bypass
the ``logging`` module entirely: no timestamp, no logger name, no level and — most
importantly — no indication of *where* in the Python code they originated. That is
exactly why warnings of this kind are so hard to track down from the console.

:func:`install_qt_message_handler` registers a ``qInstallMessageHandler`` callback
that:

* forwards every Qt message to the ``"qt"`` logger at the matching level, so they
  share the same formatter/handlers as the rest of the application, and
* for warnings and above, attaches the current Python call stack, so a Qt-internal
  warning emitted synchronously from one of our own calls (e.g. ``QThread.wait()``)
  points straight at the offending Python line.

Install it once, *before* the ``QApplication`` is created, so even early Qt
start-up messages are captured.
"""

import logging
import traceback

from PySide6.QtCore import QtMsgType, qInstallMessageHandler, QThread, QCoreApplication

# Map each Qt message type to a Python logging level.
_LEVEL_BY_TYPE = {
    QtMsgType.QtDebugMsg:    logging.DEBUG,
    QtMsgType.QtInfoMsg:     logging.INFO,
    QtMsgType.QtWarningMsg:  logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg:    logging.CRITICAL,
}

_qt_logger = logging.getLogger("qt")

# Attach a Python stack trace for messages at or above this level.
_STACK_LEVEL = logging.WARNING


def _format_context(context):
    """Build a short ``file:line | function`` string from a QMessageLogContext."""
    parts = []
    if getattr(context, "file", None):
        location = context.file
        if context.line:
            location += f":{context.line}"
        parts.append(location)
    if getattr(context, "function", None):
        parts.append(context.function)
    return " | ".join(parts)


def _handler(msg_type, context, message):
    level = _LEVEL_BY_TYPE.get(msg_type, logging.INFO)

    ctx = _format_context(context)
    text = message if not ctx else f"{message}  [{ctx}]"

    if level >= _STACK_LEVEL:
        # The current Python stack at the point Qt emitted the message. When the
        # warning is raised synchronously from one of our calls, this is the real
        # culprit. The last frame is this handler itself, so drop it.
        stack = traceback.extract_stack()[:-1]
        text += "\nPython stack at Qt message:\n" + "".join(traceback.format_list(stack))

    _qt_logger.log(level, text)


def install_qt_message_handler():
    """Install the Qt -> logging bridge. Call once before ``QApplication``."""
    qInstallMessageHandler(_handler)
    _qt_logger.debug("Qt message handler installed")


# ------------------------------------------------------------------------------ #
# THREAD-LIFECYCLE CHECKPOINTS
# ------------------------------------------------------------------------------ #
#
# These mark the spots where a worker QThread is torn down (quit/wait/delete) —
# i.e. the places where "QThread::wait: Thread tried to wait on itself" can be
# emitted. They are deliberately DEBUG-level so they stay silent during normal
# operation (real-time mode reaches some of them ~10x/second); enable them with:
#
#     logging.getLogger("qt.threads").setLevel(logging.DEBUG)
#
# When `target_thread` is the thread we are *currently running on*, that is the
# exact self-wait condition, so we log an ERROR with a Python stack regardless of
# level — the loud, attributable signal you want if the bug ever returns.

_thread_logger = logging.getLogger("qt.threads")


def log_thread_checkpoint(label, target_thread=None):
    """Record that execution reached ``label``, noting the current thread.

    :param label: short description of the code location.
    :param target_thread: the QThread about to be quit()/wait()'d, if any. If it is
        the current thread, a self-wait would occur and this logs ERROR + stack.
    """
    try:
        current = QThread.currentThread()
        app = QCoreApplication.instance()
        gui_thread = app.thread() if app is not None else None
        on_gui = gui_thread is not None and current is gui_thread
        current_name = current.objectName() or hex(id(current))
        is_self_wait = target_thread is not None and current is target_thread
    except Exception:
        # Diagnostics must never break the teardown they are observing.
        _thread_logger.debug("[thread-checkpoint] %s (introspection failed)", label)
        return

    if is_self_wait:
        _thread_logger.error(
            "[thread-checkpoint] %s | running ON the target thread (%s) -> "
            "QThread.wait() here would self-wait "
            "('QThread::wait: Thread tried to wait on itself')",
            label, current_name, stack_info=True,
        )
    else:
        _thread_logger.debug(
            "[thread-checkpoint] %s | on %s thread (%s)",
            label, "GUI" if on_gui else "non-GUI", current_name,
        )
