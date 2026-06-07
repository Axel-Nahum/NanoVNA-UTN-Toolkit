"""
Module-local i18n loader for the material characterization feature.

EN: Reads the feature's JSON resource files (English / Spanish kept in separate
    files under ``shared/resources/material_characterization/<lang>/``) and
    returns plain dicts. This is intentionally module-local so the feature does
    NOT modify the shared ``json_resource_loader.py`` that other modules use; it
    only re-uses the low-level, read-only ``load_resource`` reader and the
    ``get_settings`` helper.

ES: Lee los archivos JSON de recursos de la funcionalidad (ingles / espanol en
    archivos separados bajo ``shared/resources/material_characterization/<lang>/``)
    y devuelve diccionarios. Es deliberadamente local al modulo para NO modificar
    el ``json_resource_loader.py`` compartido que usan otros modulos; solo reusa
    el lector de bajo nivel ``load_resource`` (solo lectura) y el ayudante
    ``get_settings``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

from NanoVNA_UTN_Toolkit.utils import safe_import

load_resource = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.load_resource", "load_resource"
)
get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)

_MODULE = "material_characterization"


def get_current_language() -> str:
    """Return the configured UI language code (defaults to ``"en"``)."""
    settings = get_settings(
        "INI/dut_measurement/preferences/preferences.ini",
        "shared/utils/preferences/preferences.ini",
        Path(__file__).resolve(),
    )
    return settings.value("Preferences/language", "en")


def load_text(json_resource: str, lang: str | None = None) -> Dict:
    """
    Load a characterization JSON resource as a dict.

    Parameters
    ----------
    json_resource : str
        File name, e.g. ``"characterization_wizard.json"``.
    lang : str | None
        Language code; if ``None`` the configured language is used.
    """
    if lang is None:
        lang = get_current_language()
    return load_resource(_MODULE, lang, json_resource) or {}


def image_path(name: str) -> str:
    """
    Absolute path to a bundled module image (under assets/images).

    EN: Resolves both in development and in a frozen (PyInstaller) build.
    ES: Resuelve tanto en desarrollo como en un build congelado (PyInstaller).
    """
    rel = Path("modules") / _MODULE / "assets" / "images" / name
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return str(base / rel)
    # ui/resources_loader.py -> parents[0]=ui, [1]=material_characterization
    module_dir = Path(__file__).resolve().parents[1]
    return str(module_dir / "assets" / "images" / name)
