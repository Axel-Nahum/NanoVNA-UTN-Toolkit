import os
import sys
from pathlib import Path
from PySide6.QtCore import QSettings


def get_base_dir(is_exe, caller_path=None):
    
    if is_exe:
        return Path(os.getenv("APPDATA")) / "NanoVNA-UTN-Toolkit"

    current = caller_path

    for parent in current.parents:
        if parent.name == "NanoVNA_UTN_Toolkit":
            return parent

    raise RuntimeError("Project root not found")


def get_settings(exe_path_inside_base, dev_path_inside_base, caller_path):
    is_exe = getattr(sys, 'frozen', False)

    base = get_base_dir(is_exe, caller_path)

    selected_path = exe_path_inside_base if is_exe else dev_path_inside_base

    final_path = base.joinpath(*selected_path.split("/"))
    final_path.parent.mkdir(parents=True, exist_ok=True)

    return QSettings(str(final_path), QSettings.IniFormat)