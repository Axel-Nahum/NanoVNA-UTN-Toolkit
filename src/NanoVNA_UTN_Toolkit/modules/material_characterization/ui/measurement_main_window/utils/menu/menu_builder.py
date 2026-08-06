from PySide6.QtGui import QAction


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
