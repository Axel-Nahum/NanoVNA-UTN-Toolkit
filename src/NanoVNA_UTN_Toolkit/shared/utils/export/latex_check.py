"""
Process-wide memory of LaTeX compilers that already passed the test compile.

EN: Both PDF exporters verify a compiler by compiling a trivial document
(1-5 s; 10-30 s the first time MiKTeX installs packages). The setup dialog
does that in a thread, and the preview dialog repeated it on the GUI thread
right before every export. A compiler that compiled once in this process keeps
working: remember its path and skip the test. Failures are not remembered, so
installing LaTeX mid-session is picked up by the next check.

ES: Los dos exportadores verifican el compilador compilando un documento
trivial; el que ya compilo una vez en este proceso no se vuelve a probar.
"""

import threading

_lock = threading.Lock()
_working: set = set()


def known_working(compiler_path) -> bool:
    with _lock:
        return str(compiler_path) in _working


def remember_working(compiler_path) -> None:
    with _lock:
        _working.add(str(compiler_path))


def forget_all() -> None:
    """Tests / troubleshooting: force the next check to compile again."""
    with _lock:
        _working.clear()
