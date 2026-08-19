"""
Global Debug Mode flag.

EN: Single source of truth for the "Enable Debug Mode" preference. The state
    lives in the same [Preferences] section of preferences.ini used by theme and
    language, so every module can read it without holding a reference to the
    preferences dialog. Debug Mode currently controls the visibility of the
    offline .s1p import actions of the characterization wizard, which let the
    user exercise the whole assistant without a probe or measurement setup.

ES: Fuente unica de verdad para la preferencia "Enable Debug Mode". El estado se
    guarda en la misma seccion [Preferences] de preferences.ini que el tema y el
    idioma, asi cualquier modulo puede leerlo sin depender del dialogo de
    preferencias. Hoy Debug Mode controla la visibilidad de las acciones de
    importacion de .s1p del asistente de caracterizacion, que permiten recorrer
    todo el asistente sin sonda ni setup de medicion.
"""

from __future__ import annotations

import logging
from pathlib import Path

from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings

logger = logging.getLogger(__name__)

_INI_EXE = "INI/dut_measurement/preferences/preferences.ini"
_INI_DEV = "shared/utils/preferences/preferences.ini"
_KEY = "Preferences/debug_mode"


def _settings():
    return get_settings(_INI_EXE, _INI_DEV, Path(__file__).resolve())


def is_debug_enabled() -> bool:
    """Return True when the user enabled Debug Mode in Preferences."""
    try:
        return str(_settings().value(_KEY, "false")).strip().lower() in ("true", "1", "yes")
    except Exception:
        logger.exception("[debug_mode.is_debug_enabled] could not read the preference")
        return False


def set_debug_enabled(enabled: bool) -> None:
    """Persist the Debug Mode preference."""
    _settings().setValue(_KEY, "true" if enabled else "false")
