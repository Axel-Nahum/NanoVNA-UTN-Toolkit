"""
INI settings migrator.

On each launch (exe mode only) the migrator runs two passes:

1. OVERWRITE pass — "design" INIs whose visual values are owned by the app,
   not the user.  The bundled default replaces the user's copy entirely,
   except for a small set of per-INI keys that the user is allowed to change
   (e.g. is_dark_mode in dark_light_config).

2. MERGE pass — "config" INIs whose values are user preferences.  Only
   sections/keys that are missing from the user's copy are added; existing
   values are never touched.

Runtime-state INIs (calibration_config, measurement_numbers) are excluded
from both passes — their content is session data, not settings.
"""

import logging
import shutil
import sys
from configparser import RawConfigParser
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Design INIs: overwrite on every launch ───────────────────────────────── #
# Maps relative INI path → set of keys (across ALL sections) that must be
# preserved from the user's current file even during an overwrite.
_DESIGN_INIS: dict[str, set[str]] = {
    "dut_measurement/dark_light_config/dark_light_config.ini": {
        "is_dark_mode",
        "text_light_dark",
    },
}

# ── Config INIs: only add missing keys ───────────────────────────────────── #
_CONFIG_INIS = [
    "dut_measurement/preferences/preferences.ini",
    "dut_measurement/sweep_config/sweep_config.ini",
    "dut_measurement/signal_filters/signal_filters.ini",
    "dut_measurement/auto_scale/auto_scale.ini",
    "dut_measurement/plot_manager/plot_manager.ini",
    "dut_measurement/graphics_config/graphics_config.ini",
    "material_characterization/characterization_chart_config/characterization_chart_config.ini",
    "material_characterization/plot_manager/plot_manager.ini",
]


def _read_ini(path: Path) -> RawConfigParser:
    cfg = RawConfigParser()
    cfg.optionxform = str  # preserve key case
    cfg.read(path, encoding="utf-8")
    return cfg


def _write_ini(cfg: RawConfigParser, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        cfg.write(fh)


def _overwrite_design(default_path: Path, user_path: Path, preserve_keys: set[str]) -> None:
    """Replace user INI with the bundled default, keeping *preserve_keys* intact."""
    if not preserve_keys:
        shutil.copy2(default_path, user_path)
        return

    # Collect the values to preserve from the user's current file.
    user_cfg = _read_ini(user_path) if user_path.exists() else RawConfigParser()
    preserved: dict[tuple[str, str], str] = {}
    for section in user_cfg.sections():
        for key, value in user_cfg.items(section):
            if key in preserve_keys:
                preserved[(section, key)] = value

    # Start from the bundled default and restore preserved values.
    new_cfg = _read_ini(default_path)
    for (section, key), value in preserved.items():
        if new_cfg.has_section(section) and new_cfg.has_option(section, key):
            new_cfg.set(section, key, value)

    _write_ini(new_cfg, user_path)


def _merge_config(default_path: Path, user_path: Path) -> bool:
    """Add missing sections/keys from default into user INI. Returns True if changed."""
    default_cfg = _read_ini(default_path)
    user_cfg = _read_ini(user_path)

    changed = False
    for section in default_cfg.sections():
        if not user_cfg.has_section(section):
            user_cfg.add_section(section)
            changed = True
        for key, value in default_cfg.items(section):
            if not user_cfg.has_option(section, key):
                user_cfg.set(section, key, value)
                changed = True

    if changed:
        _write_ini(user_cfg, user_path)
    return changed


def migrate_settings(defaults_ini_dir: str, user_ini_dir: str) -> None:
    """
    Run the two-pass migration.

    *defaults_ini_dir* — path to the bundled INI folder (sys._MEIPASS/INI).
    *user_ini_dir*     — path to the user's INI folder (AppData/.../INI).

    No-op in dev mode (not frozen).
    """
    if not getattr(sys, "frozen", False):
        return

    defaults_base = Path(defaults_ini_dir)
    user_base = Path(user_ini_dir)

    # Pass 1 — design INIs (overwrite)
    for rel, preserve_keys in _DESIGN_INIS.items():
        default_path = defaults_base / rel
        user_path = user_base / rel
        if not default_path.exists():
            logger.debug("settings_migrator: default not found, skipping: %s", rel)
            continue
        try:
            _overwrite_design(default_path, user_path, preserve_keys)
            logger.info("settings_migrator: refreshed design INI: %s", rel)
        except Exception as exc:  # noqa: BLE001
            logger.warning("settings_migrator: could not overwrite %s: %s", rel, exc)

    # Pass 2 — config INIs (merge only)
    for rel in _CONFIG_INIS:
        default_path = defaults_base / rel
        user_path = user_base / rel
        if not default_path.exists():
            logger.debug("settings_migrator: default not found, skipping: %s", rel)
            continue
        if not user_path.exists():
            logger.debug("settings_migrator: user INI missing, skipping: %s", rel)
            continue
        try:
            if _merge_config(default_path, user_path):
                logger.info("settings_migrator: merged new keys into %s", rel)
        except Exception as exc:  # noqa: BLE001
            logger.warning("settings_migrator: could not merge %s: %s", rel, exc)
