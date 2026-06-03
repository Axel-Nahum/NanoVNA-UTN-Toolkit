"""
Centralized helper for importing required project/third-party modules.

with a single call::
    thing = safe_import("some.module", "thing")
"""

import sys
import logging
import importlib

# Shown whenever a required import fails so the user knows how to fix it.
DEPENDENCY_HINT = (
    "Please make sure you're running from the correct directory and install all "
    "dependencies with: pip install -r requirements.txt"
)


def safe_import(module, *names):
    """Import ``names`` from ``module``, exiting with a friendly hint on failure.

    Args:
        module: Dotted path of the module to import (e.g. ``"pkg.sub.mod"``).
        *names: Names to pull out of the module.

    Returns:
        - The module itself when no ``names`` are given.
        - The single object when exactly one name is requested.
        - A tuple of objects when several names are requested (ready to unpack).

    On ``ImportError``/``AttributeError`` it logs the error plus a reminder to
    install the dependencies from ``requirements.txt`` and exits the process,
    mirroring the previous per-file behavior.
    """
    try:
        mod = importlib.import_module(module)
        if not names:
            return mod
        attrs = tuple(getattr(mod, name) for name in names)
        return attrs[0] if len(attrs) == 1 else attrs
    except (ImportError, AttributeError) as e:
        logging.error("Failed to import required modules: %s", e)
        logging.info(DEPENDENCY_HINT)
        sys.exit(1)
