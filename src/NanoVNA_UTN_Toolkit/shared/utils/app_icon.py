from pathlib import Path
import sys
import logging

from PySide6.QtGui import QIcon


def resource_path(relative_path):

    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parents[4]

    # intenta directo
    path = base_path / relative_path
    if path.exists():
        return path

    # intenta dentro de src (caso típico pyinstaller)
    path = base_path / "src" / relative_path
    return path


def apply_window_icon(self):

    icon_path = resource_path("icon.ico")

    logging.info(f"Trying icon path: {icon_path}")

    if icon_path.exists():
        self.setWindowIcon(QIcon(str(icon_path)))

    else:
        logging.warning(f"icon.ico not found: {icon_path}")