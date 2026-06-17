#!/usr/bin/env python3
import sys
import os
import multiprocessing
multiprocessing.freeze_support()
import shutil
import logging
from PySide6.QtWidgets import QApplication

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    sys.path.insert(0, base_path)
else:
    base_path = os.path.dirname(__file__)
    sys.path.insert(0, os.path.join(base_path, 'src'))

from NanoVNA_UTN_Toolkit.compat import apply_patches
apply_patches()

from NanoVNA_UTN_Toolkit.utils import check_required_packages, cleanup_routine    
from NanoVNA_UTN_Toolkit.shared.ui.connection_window.connection_window import NanoVNAStatusApp

# ----------------------------
# LOGGING
# ----------------------------
class ShortNameFormatter(logging.Formatter):
    def format(self, record):
        if record.name.startswith('NanoVNA_UTN_Toolkit.'):
            record.name = record.name[len('NanoVNA_UTN_Toolkit.'):]
        return super().format(record)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(ShortNameFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)


# ----------------------------
# COPY ONLY FIRST TIME
# ----------------------------
def copy_contents(src, dst):
    """
    Copia archivos sueltos o carpetas completas sin sobreescribir 
    si ya existen.
    """
    if not os.path.exists(src):
        return

    os.makedirs(dst, exist_ok=True)

    if os.path.isdir(src):
        # Copiar recursivamente pero sin reemplazar
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            target_root = os.path.join(dst, rel) if rel != "." else dst
            os.makedirs(target_root, exist_ok=True)

            for f in files:
                src_f = os.path.join(root, f)
                dst_f = os.path.join(target_root, f)
                if not os.path.exists(dst_f):
                    shutil.copy2(src_f, dst_f)

    else:
        # PyInstaller a veces mete archivos sueltos
        fname = os.path.basename(src)
        dst_file = os.path.join(dst, fname)
        if not os.path.exists(dst_file):
            shutil.copy2(src, dst_file)


def ensure_paths():
    """
    Devuelve las rutas donde la app debe cargar INI y Measurements.
    Si está congelada (.exe), copia desde la carpeta del bundle (_MEIxxxxx)
    solo la primera vez.
    """
    if getattr(sys, "frozen", False):
        # Carpeta donde PyInstaller pone los datos
        base_dir = sys._MEIPASS

        # Dentro del .spec pusiste INI y Measurements
        src_ini = os.path.join(base_dir, "INI")
        src_meas = os.path.join(base_dir, "Measurements")

        appdata = os.getenv("APPDATA")
        root = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

        dst_ini = os.path.join(root, "INI")
        dst_meas = os.path.join(root, "Measurements")

        os.makedirs(root, exist_ok=True)

        # Copia sin sobrescribir (solo primera vez)
        copy_contents(src_ini, dst_ini)
        copy_contents(src_meas, dst_meas)

        return dst_ini, dst_meas

    # Modo desarrollo (Python normal)
    project_root = os.path.dirname(__file__)
    return (
        os.path.join(project_root, "INI"),
        os.path.join(project_root, "Measurements"),
    )


# ----------------------------
# APP
# ----------------------------
def run_app():
    try:
        app = QApplication(sys.argv)
        window = NanoVNAStatusApp()
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Error running application: {e}")
        input("Presiona Enter para cerrar...")
        sys.exit(1)


def main():
    ini_path, meas_path = ensure_paths()

    print("INI:", ini_path)
    print("MEAS:", meas_path)

    check_required_packages()
    run_app()
    cleanup_routine()


if __name__ == "__main__":
    main()
