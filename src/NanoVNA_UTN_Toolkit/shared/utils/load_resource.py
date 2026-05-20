from pathlib import Path
import sys
import json
import logging


def resource_path(relative_path):

    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parents[3] / "NanoVNA_UTN_Toolkit"

    return base_path / relative_path


def load_resource(module, lang="en", relative_file = " "):

    full_path = resource_path(
        f"shared/resources/{module}/{lang}/{relative_file}"
    )

    logging.info(f"full_path: {full_path}")

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        logging.error(f"[text_loader.load] Error loading {full_path}: {e}")
        return {}