"""
Calibration menu actions for the characterization main window.
"""

import logging

from PySide6.QtWidgets import QMessageBox

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text

logger = logging.getLogger(__name__)


def open_wizard(main_window):
    """Open the characterization wizard to start a new session."""
    logger.info("[calibration_menu] open_wizard — not yet implemented")


def select_calibration(main_window):
    """Show a dialog to select a saved calibration and jump to the DUT step."""
    logger.info("[calibration_menu] select_calibration — not yet implemented")


def save_calibration(main_window):
    """Show the save-calibration dialog (same as the wizard result-screen button)."""
    wizard = getattr(main_window, "wizard_window", None)
    if wizard is None:
        QMessageBox.warning(
            main_window,
            "No calibration",
            "No active calibration session found.",
        )
        return

    cal = getattr(wizard, "perm_calibration", None)
    if cal is None:
        QMessageBox.warning(
            main_window,
            "No calibration",
            "The calibration object is not available.",
        )
        return

    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.result_screen import (
        _SaveCalibrationDialog,
    )

    texts = load_text("characterization_wizard.json")
    rtexts = texts.get("result", {})
    dlg = _SaveCalibrationDialog(main_window, rtexts, cal)
    dlg.exec()


def delete_calibration(main_window):
    """Show a dialog to delete one or more saved calibrations."""
    logger.info("[calibration_menu] delete_calibration — not yet implemented")
