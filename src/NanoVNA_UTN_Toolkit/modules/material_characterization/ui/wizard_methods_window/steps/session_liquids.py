"""
Per-session reference-liquid selection.

EN: The technique descriptor declares a DEFAULT liquid per reference standard
    (``StandardDef.default_liquid_key``). Since Step 1 lets the user change it,
    the descriptor default is no longer the answer: the session choice wins.
    Every place that used to read ``standard.default_liquid_key`` directly
    (config screen, measure screen, step sidebar) must go through here instead,
    otherwise the wizard shows "Water" while measuring ethanol.

ES: El descriptor de la tecnica declara un liquido POR DEFECTO para cada patron
    de referencia (``StandardDef.default_liquid_key``). Como el Step 1 ahora
    permite cambiarlo, ese default ya no es la respuesta: gana la eleccion de la
    sesion. Todos los lugares que antes leian ``standard.default_liquid_key``
    directamente (pantalla de config, de medicion y barra de pasos) tienen que
    pasar por aca, si no el asistente muestra "Agua" mientras se mide etanol.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.probe_models import (
    ProbeModel,
    get_probe,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid,
)

logger = logging.getLogger(__name__)


def liquid_keys(wizard) -> Dict[str, str]:
    """Return (creating if needed) the session map ``standard key -> liquid key``."""
    keys = getattr(wizard, "ref_liquid_keys", None)
    if keys is None:
        keys = {}
        wizard.ref_liquid_keys = keys
    return keys


def selected_liquid_key(wizard, standard) -> Optional[str]:
    """Liquid chosen for ``standard``, falling back to the descriptor default."""
    if standard is None:
        return None
    return liquid_keys(wizard).get(standard.key) or standard.default_liquid_key


def set_liquid_key(wizard, standard_key: str, liquid_key: str) -> None:
    liquid_keys(wizard)[standard_key] = liquid_key


def discard_reference_measurement(wizard, standard_key: str) -> None:
    """
    Forget a reference's stored S11 and the raw copy kept to undo its pre-cal.

    EN: For when the liquid assigned to the standard changes and the stored S11
        belongs to the previous one. The pre-cal OPEN (``_precal_open``) stays:
        it is a probe measurement, valid for the liquid measured next.
    ES: Para cuando cambia el liquido asignado al patron y el S11 guardado es
        del anterior. El OPEN de la pre-calibracion (``_precal_open``) se
        conserva: es una medicion de la sonda, valida para el liquido que se
        mida despues.
    """
    wizard.perm_calibration.clear_measurement(standard_key)
    getattr(wizard, "_precal_originals", {}).pop(standard_key, None)


def ensure_defaults(wizard, descriptor) -> None:
    """Seed the session map from the descriptor for any standard not set yet."""
    keys = liquid_keys(wizard)
    for std in descriptor.reference_standards:
        if not keys.get(std.key) and std.default_liquid_key:
            keys[std.key] = std.default_liquid_key


def liquid_display_name(wizard, standard, liquids_texts) -> str:
    """Localized name of the liquid currently assigned to ``standard``."""
    key = selected_liquid_key(wizard, standard)
    if not key:
        return "-"
    try:
        fallback = get_reference_liquid(key).display_name
    except KeyError:
        logger.warning("[session_liquids] unknown liquid key '%s'", key)
        fallback = key
    return liquids_texts.get(key, fallback)


# --------------------------------------------------------------------------- #
# Probe chosen in Step 1
# --------------------------------------------------------------------------- #

def selected_probe(wizard) -> ProbeModel:
    """Probe of this session (the generic one until the user picks a probe)."""
    return get_probe(getattr(wizard.perm_calibration, "probe_key", None))


def set_probe_key(wizard, probe_key: str) -> None:
    wizard.perm_calibration.probe_key = probe_key


# --------------------------------------------------------------------------- #
# Preset pre-loading chosen in Step 1
# --------------------------------------------------------------------------- #

def preset_preload(wizard) -> Dict[str, str]:
    """Session map ``standard key -> preset name`` picked in Step 1 (may be empty)."""
    preload = getattr(wizard, "preset_preload", None)
    if preload is None:
        preload = {}
        wizard.preset_preload = preload
    return preload


def set_preset_preload(wizard, standard_key: str, preset_name: Optional[str]) -> None:
    preload = preset_preload(wizard)
    if preset_name:
        preload[standard_key] = preset_name
    else:
        preload.pop(standard_key, None)
