from pathlib import Path

from PySide6.QtGui import QAction

from NanoVNA_UTN_Toolkit.utils import safe_import

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.menu.plot_manager.plot_manager import (
    open_plot_manager,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.menu.calibration_menu.calibration_menu import (
    import_calibration_pkg,
    open_wizard,
    select_calibration,
    save_calibration,
    delete_calibration,
)

show_about_dialog = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.help_menu.help_menu",
    "show_about_dialog",
)



def build_menu(main_window) -> None:
    """Build the full menubar for the characterization main window."""
    menu = main_window._texts.get("menu", {})
    menubar = main_window.menuBar()

    # ------------------------------------------------------------------ #
    # File
    # ------------------------------------------------------------------ #
    file_menu = menubar.addMenu(menu.get("file", "File"))

    back_action = QAction(menu.get("back_to_menu", "Back to menu"), main_window)
    back_action.triggered.connect(main_window.return_to_menu_window)
    file_menu.addAction(back_action)

    file_menu.addSeparator()

    export_s11_action = QAction(menu.get("export_s11_touchstone", "Export Touchstone S11…"), main_window)
    export_s11_action.triggered.connect(main_window._export_s11_touchstone)
    file_menu.addAction(export_s11_action)

    export_pdf_action = QAction(menu.get("export_pdf", "Export PDF Report…"), main_window)
    export_pdf_action.triggered.connect(main_window._export_pdf)
    file_menu.addAction(export_pdf_action)

    file_menu.addSeparator()
    from NanoVNA_UTN_Toolkit.shared.utils.preferences.preferences import open_preferences_dialog
    pref_action = QAction("⚙  Preferences…", main_window)
    pref_action.triggered.connect(lambda: open_preferences_dialog(main_window))
    file_menu.addAction(pref_action)

    # ------------------------------------------------------------------ #
    # Plots
    # ------------------------------------------------------------------ #
    plots_menu = menubar.addMenu(menu.get("plots", "Plots"))

    plot_manager_action = QAction(menu.get("plot_manager", "Plot Manager"), main_window)
    plot_manager_action.triggered.connect(lambda: open_plot_manager(main_window))
    plots_menu.addAction(plot_manager_action)

    plots_menu.addSeparator()

    s11_action = QAction(menu.get("show_s11", "S11 — Smith Chart"), main_window)
    s11_action.triggered.connect(main_window._show_s11_window)
    plots_menu.addAction(s11_action)

    table_action = QAction(menu.get("show_table", "Results Table"), main_window)
    table_action.triggered.connect(main_window._show_table_window)
    plots_menu.addAction(table_action)

    # ------------------------------------------------------------------ #
    # Calibration / Kits
    # ------------------------------------------------------------------ #
    cal_menu = menubar.addMenu(menu.get("calibration", "Calibration"))

    wizard_action = QAction(menu.get("cal_open_wizard", "Open Wizard…"), main_window)
    wizard_action.triggered.connect(lambda: open_wizard(main_window))
    cal_menu.addAction(wizard_action)

    cal_menu.addSeparator()

    import_action = QAction(menu.get("cal_import", "Import Calibration…"), main_window)
    import_action.triggered.connect(lambda: import_calibration_pkg(main_window))
    cal_menu.addAction(import_action)

    select_action = QAction(menu.get("cal_select_kit", "Select Calibration…"), main_window)
    select_action.triggered.connect(lambda: select_calibration(main_window))
    cal_menu.addAction(select_action)

    save_action = QAction(menu.get("cal_save_kit", "Save Calibration…"), main_window)
    save_action.triggered.connect(lambda: save_calibration(main_window))
    cal_menu.addAction(save_action)

    delete_action = QAction(menu.get("cal_delete_kit", "Delete Calibration…"), main_window)
    delete_action.triggered.connect(lambda: delete_calibration(main_window))
    cal_menu.addAction(delete_action)

    # ------------------------------------------------------------------ #
    # Help
    # ------------------------------------------------------------------ #
    help_menu = menubar.addMenu(menu.get("help", "Help"))

    if show_about_dialog:
        about_en = QAction(menu.get("about_en", "About (EN)"), main_window)
        about_en.triggered.connect(lambda: show_about_dialog(main_window, "en"))
        help_menu.addAction(about_en)

        about_es = QAction(menu.get("about_es", "About (ES)"), main_window)
        about_es.triggered.connect(lambda: show_about_dialog(main_window, "es"))
        help_menu.addAction(about_es)
