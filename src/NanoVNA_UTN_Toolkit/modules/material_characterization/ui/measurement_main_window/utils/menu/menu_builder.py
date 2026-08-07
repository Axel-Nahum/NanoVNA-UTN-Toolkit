from pathlib import Path

from PySide6.QtGui import QAction

from NanoVNA_UTN_Toolkit.utils import safe_import
from NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode import toggle_menu_dark_mode
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.menu.plot_manager.plot_manager import (
    open_plot_manager,
)

show_about_dialog = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.help_menu.help_menu",
    "show_about_dialog",
)

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

_DL_INI_EXE = "INI/dut_measurement/dark_light_config/dark_light_config.ini"
_DL_INI_DEV = "shared/utils/dark_light_mode/dark_light_config.ini"


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

    plots_menu.addSeparator()

    _dl = get_settings(_DL_INI_EXE, _DL_INI_DEV, Path(__file__).resolve())
    _theme_label = _dl.value("Dark_Light/text_light_dark", "Dark Mode 🌙")
    theme_action = QAction(_theme_label, main_window)
    theme_action.triggered.connect(
        lambda _checked=False, a=theme_action: toggle_menu_dark_mode(main_window, a)
    )
    plots_menu.addAction(theme_action)

    # ------------------------------------------------------------------ #
    # Calibration / Kits
    # ------------------------------------------------------------------ #
    menubar.addMenu(menu.get("calibration", "Calibration"))

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
