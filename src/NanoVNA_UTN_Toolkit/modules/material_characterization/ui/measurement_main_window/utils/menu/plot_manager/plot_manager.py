"""
Plot Manager dialog for the permittivity measurement main window.

Same layout and style as the DUT plot manager but with a single graphic
column and no View button (Edit only in Graphics Tools).
Buttons are visible but not yet functional — wired later.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QCheckBox, QLineEdit, QPushButton, QSizePolicy, QVBoxLayout,
)

from NanoVNA_UTN_Toolkit.utils import safe_import

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)

_INI_EXE = "INI/material_characterization/plot_manager/plot_manager.ini"
_INI_DEV = (
    "modules/material_characterization/ui/measurement_main_window"
    "/utils/menu/plot_manager/plot_manager.ini"
)


def _sep():
    """Thin translucent separator — identical to DUT style."""
    line = QFrame()
    line.setFixedHeight(1)
    line.setFrameShape(QFrame.NoFrame)
    line.setStyleSheet("border-top: 1px solid rgba(255, 255, 255, 140);")
    return line


def _bold(text: str, size: int = 15) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-weight: bold; font-size: {size}px; border: none;")
    return lbl


def open_plot_manager(main_window):
    """Open the Plot Manager modal dialog."""
    pm_settings = get_settings(_INI_EXE, _INI_DEV, Path(__file__).resolve())

    dl_settings = get_settings(
        "INI/dut_measurement/dark_light_config/dark_light_config.ini",
        "shared/utils/dark_light_mode/dark_light_config.ini",
        Path(__file__).resolve(),
    )
    border = dl_settings.value("Dark_Light/QGroupBox/color", "1px solid #999")
    frame_style = f"""
        QFrame {{
            border: {border};
            border-radius: 8px;
            padding: 12px;
        }}
    """

    dialog = QDialog(main_window)
    dialog.setWindowTitle("Plot Manager")
    dialog.setFixedSize(660, 750)
    dialog.setStyleSheet(main_window.styleSheet())
    dialog.setSizeGripEnabled(True)
    dialog.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
    dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint)

    main = QVBoxLayout(dialog)
    main.setContentsMargins(15, 15, 15, 15)

    frame = QFrame()
    frame.setStyleSheet(frame_style)

    layout = QVBoxLayout(frame)
    layout.setSpacing(10)

    # =====================================================
    # TITLE
    # =====================================================
    title = QLabel("Plot Manager")
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet("font-size: 25px; font-weight: bold; border: none;")
    layout.addWidget(title)

    # =====================================================
    # TOOLS
    # =====================================================
    tools_title = QLabel("Graphics Tools")
    tools_title.setAlignment(Qt.AlignCenter)
    tools_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    layout.addWidget(tools_title)

    tools = QHBoxLayout()
    tools.addStretch()

    edit_btn = QPushButton("Graphics && Markers Editor")
    edit_btn.setMinimumSize(200, 45)
    edit_btn.clicked.connect(lambda: _open_edit(main_window, dialog))
    tools.addWidget(edit_btn)

    tools.addStretch()
    layout.addLayout(tools)

    layout.addSpacing(12)
    layout.addWidget(_sep())

    # =====================================================
    # DISPLAY OPTIONS
    # =====================================================
    display_title = QLabel("Display Options")
    display_title.setAlignment(Qt.AlignCenter)
    display_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    layout.addWidget(display_title)

    disp_grid = QGridLayout()
    disp_grid.setHorizontalSpacing(28)
    disp_grid.setColumnStretch(0, 3)
    disp_grid.setColumnStretch(1, 2)
    disp_grid.setColumnStretch(2, 2)

    g1 = QLabel("Permittivity Chart (εᵣ)")
    g1.setAlignment(Qt.AlignCenter)
    g1.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")
    disp_grid.addWidget(g1, 0, 1, 1, 2)

    grid_chk = QCheckBox()
    grid_chk.setChecked(pm_settings.value("grid/current_state", True, type=bool))
    grid_chk.setEnabled(False)

    disp_grid.addWidget(_bold("Show Grid:"), 1, 0, Qt.AlignLeft)
    disp_grid.addWidget(grid_chk, 1, 1, 1, 2, Qt.AlignCenter)

    layout.addLayout(disp_grid)
    layout.addSpacing(12)
    layout.addWidget(_sep())

    # =====================================================
    # AXIS SETTINGS
    # =====================================================
    axis_title = QLabel("Axis Settings (Y Limits)")
    axis_title.setAlignment(Qt.AlignCenter)
    axis_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    layout.addWidget(axis_title)

    axis_grid = QGridLayout()
    axis_grid.setHorizontalSpacing(28)
    axis_grid.setColumnStretch(0, 3)
    axis_grid.setColumnStretch(1, 2)
    axis_grid.setColumnStretch(2, 2)

    ag1 = QLabel("Permittivity Chart (εᵣ)")
    ag1.setAlignment(Qt.AlignCenter)
    ag1.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")
    axis_grid.addWidget(ag1, 0, 1, 1, 2)

    auto_chk = QCheckBox()
    auto_checked = pm_settings.value("auto_scale/current_state", True, type=bool)
    auto_chk.setChecked(auto_checked)
    auto_chk.setEnabled(False)

    axis_grid.addWidget(_bold("Auto Scale:"), 1, 0, Qt.AlignLeft)
    axis_grid.addWidget(auto_chk, 1, 1, 1, 2, Qt.AlignCenter)

    validator = QDoubleValidator()
    validator.setNotation(QDoubleValidator.StandardNotation)

    y_min = QLineEdit()
    y_min.setPlaceholderText("Min")
    y_min.setAlignment(Qt.AlignCenter)
    y_min.setValidator(validator)
    y_min.setEnabled(False)

    y_max = QLineEdit()
    y_max.setPlaceholderText("Max")
    y_max.setAlignment(Qt.AlignCenter)
    y_max.setValidator(validator)
    y_max.setEnabled(False)

    if not auto_checked:
        vmin = pm_settings.value("set_range/ymin", None, type=float)
        vmax = pm_settings.value("set_range/ymax", None, type=float)
        if vmin is not None:
            y_min.setText(f"{vmin:.6g}")
        if vmax is not None:
            y_max.setText(f"{vmax:.6g}")

    axis_grid.addWidget(_bold("Y Range:"), 3, 0, Qt.AlignLeft)

    range_row = QHBoxLayout()
    range_row.setSpacing(15)
    range_row.addStretch()
    range_row.addWidget(y_min)
    range_row.addWidget(y_max)
    range_row.addStretch()
    axis_grid.addLayout(range_row, 3, 1, 1, 2)

    layout.addLayout(axis_grid)
    layout.addSpacing(8)
    layout.addWidget(_sep())
    layout.addSpacing(10)

    # =====================================================
    # ACTIONS
    # =====================================================
    actions = QHBoxLayout()
    actions.addStretch()

    apply_btn = QPushButton("Apply")
    apply_btn.setMinimumSize(100, 30)
    apply_btn.clicked.connect(dialog.accept)   # no-op for now

    cancel_btn = QPushButton("Cancel")
    cancel_btn.setMinimumSize(100, 30)
    cancel_btn.clicked.connect(dialog.reject)

    actions.addWidget(apply_btn)
    actions.addWidget(cancel_btn)
    layout.addLayout(actions)

    main.addWidget(frame)
    dialog.exec()


def _open_edit(main_window, dialog):
    dialog.close()
    QTimer.singleShot(0, lambda: main_window._open_edit_chart())
