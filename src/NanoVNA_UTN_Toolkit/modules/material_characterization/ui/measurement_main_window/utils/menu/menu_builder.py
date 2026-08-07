from pathlib import Path

from PySide6.QtGui import QAction

from NanoVNA_UTN_Toolkit.utils import safe_import
from NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode import toggle_menu_dark_mode

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
    # View
    # ------------------------------------------------------------------ #
    view_menu = menubar.addMenu(menu.get("view", "View"))

    s11_action = QAction(menu.get("show_s11", "S11 — Smith Chart"), main_window)
    s11_action.triggered.connect(main_window._show_s11_window)
    view_menu.addAction(s11_action)

    table_action = QAction(menu.get("show_table", "Results Table"), main_window)
    table_action.triggered.connect(main_window._show_table_window)
    view_menu.addAction(table_action)

    view_menu.addSeparator()

    _dl = get_settings(_DL_INI_EXE, _DL_INI_DEV, Path(__file__).resolve())
    _theme_label = _dl.value("Dark_Light/text_light_dark", "Dark Mode 🌙")
    theme_action = QAction(_theme_label, main_window)
    theme_action.triggered.connect(
        lambda _checked=False, a=theme_action: toggle_menu_dark_mode(main_window, a)
    )
    view_menu.addAction(theme_action)

    # ------------------------------------------------------------------ #
    # Edit
    # ------------------------------------------------------------------ #
    edit_menu = menubar.addMenu(menu.get("edit", "Edit"))

    edit_chart_action = QAction(menu.get("edit_chart", "Edit Chart…"), main_window)
    edit_chart_action.triggered.connect(main_window._open_edit_chart)
    edit_menu.addAction(edit_chart_action)

    # ------------------------------------------------------------------ #
    # Help  (empty for now — to be expanded)
    # ------------------------------------------------------------------ #
    menubar.addMenu(menu.get("help", "Help"))
