import os
import sys

from PySide6.QtCore import QSettings

def get_settings(path_inside_base):
    if getattr(sys, 'frozen', False):
        appdata = os.getenv("APPDATA")
        base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

        ruta = os.path.join(base, *path_inside_base.split("/"))

    else:
        ui_dir = os.path.dirname(os.path.dirname(__file__))

        ruta = os.path.join(ui_dir, *path_inside_base.split("/"))

    return QSettings(ruta, QSettings.Format.IniFormat)