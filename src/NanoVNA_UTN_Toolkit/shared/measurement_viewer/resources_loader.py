from __future__ import annotations

from pathlib import Path
from typing import Dict

from NanoVNA_UTN_Toolkit.utils import safe_import

load_resource = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.load_resource", "load_resource"
)
get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)

_MODULE = "measurement_viewer"


def get_current_language() -> str:
    settings = get_settings(
        "INI/dut_measurement/preferences/preferences.ini",
        "shared/utils/preferences/preferences.ini",
        Path(__file__).resolve(),
    )
    return settings.value("Preferences/language", "en")


def load_text(json_resource: str, lang: str | None = None) -> Dict:
    if lang is None:
        lang = get_current_language()
    return load_resource(_MODULE, lang, json_resource) or {}
