"""
Cached Touchstone loading for calibration error terms and imported DUT files.

EN: The error-term files (``.s1p`` / ``.s2p``) were re-parsed with scikit-rf on
every one-shot sweep (GUI thread) and every real-time tick (worker thread),
although they only change when the user recalibrates. The cache keys each file
on its path plus modification time and size, so a rewritten file is picked up
on the next read without any explicit invalidation, and a hit costs one
``os.stat``.

ES: Los archivos de términos de error se parseaban con scikit-rf en cada barrido
y en cada tick de tiempo real, aunque solo cambian al recalibrar. La caché usa
ruta + mtime + tamaño como clave, así un archivo reescrito se vuelve a leer solo.
"""

import logging
import os
import threading

import skrf as rf

_lock = threading.Lock()
_cache: dict = {}   # path -> ((mtime_ns, size), rf.Network)


def _parse(path):
    return rf.Network(path)


def load_network(path):
    """Parsed ``rf.Network`` for ``path``, shared read-only between callers.

    Raises the same errors as ``rf.Network`` would for a missing/invalid file
    (``FileNotFoundError`` comes from the stat before any parsing).
    """
    key = os.fspath(path)
    st = os.stat(key)
    stamp = (st.st_mtime_ns, st.st_size)
    with _lock:
        hit = _cache.get(key)
        if hit is not None and hit[0] == stamp:
            return hit[1]
    net = _parse(key)
    with _lock:
        _cache[key] = (stamp, net)
    logging.info("[touchstone_cache] parsed %s (%d points)", key, len(net.f))
    return net


def load_s(path, i, j):
    """One S-parameter column ``s[:, i, j]`` of the cached network.

    The view is marked read-only: calibration maths must build new arrays, never
    write into the shared error terms.
    """
    s = load_network(path).s[:, i, j]
    s.flags.writeable = False
    return s


def clear():
    """Drop every cached network (tests, or after deleting calibration files)."""
    with _lock:
        _cache.clear()
