import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QComboBox, QStyledItemDelegate,
    QLineEdit, QFrame, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt

from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.view_edit_menu.view_edit_menu import open_view, edit_graphics_markers
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

class CenterDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter

def open_plot_settings(self):

    settings = get_settings(
        "INI/dut_measurement/dark_light_config/dark_light_config.ini",
        "shared/utils/dark_light_mode/dark_light_config.ini",
        Path(__file__).resolve()
    )

    border = settings.value("Dark_Light/QGroupBox/color", "1px solid #999")

    frame_style = f"""
        QFrame {{
            border: {border};
            border-radius: 8px;
            padding: 12px;
        }}
    """

    line_style = """
        QFrame {
            background-color: rgba(255,255,255,160);
            max-height: 1px;
            border: none;
        }
    """

    self.dialog = QDialog(self)
    self.dialog.setWindowTitle("Plot Manager")
    self.dialog.setFixedSize(660, 790)
    self.dialog.setStyleSheet(self.styleSheet())

    self.dialog.setSizeGripEnabled(True)
    self.dialog.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

    self.dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint)

    main = QVBoxLayout(self.dialog)
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

    graphics_btn = QPushButton("Plot View")
    markers_btn = QPushButton("Graphics && Markers Editor")

    graphics_btn.setMinimumSize(180, 45)
    markers_btn.setMinimumSize(180, 45)

    graphics_btn.clicked.connect(lambda: open_view_window(self))
    markers_btn.clicked.connect(lambda: open_edit_graphics_markers(self))

    tools.addStretch()
    tools.addWidget(graphics_btn)
    tools.addSpacing(20)
    tools.addWidget(markers_btn)
    tools.addStretch()

    layout.addLayout(tools)

    layout.addSpacing(12)

    sep1 = QFrame()
    sep1.setFixedHeight(1)
    sep1.setFrameShape(QFrame.NoFrame)
    sep1.setStyleSheet("""
        border-top: 1px solid rgba(255, 255, 255, 140);
    """)
    layout.addWidget(sep1)

    # =====================================================
    # DISPLAY
    # =====================================================

    display_title = QLabel("Display Options")
    display_title.setAlignment(Qt.AlignCenter)
    display_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    layout.addWidget(display_title)

    grid = QGridLayout()
    grid.setHorizontalSpacing(28)

    grid.setColumnStretch(0, 3)
    grid.setColumnStretch(1, 2)
    grid.setColumnStretch(2, 2)

    # HEADERS
    g1 = QLabel("Graphic 1")
    g2 = QLabel("Graphic 2")

    g1.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")
    g2.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    for g in (g1, g2):
        g.setAlignment(Qt.AlignCenter)
        g.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    grid.addWidget(g1, 0, 1)
    grid.addWidget(g2, 0, 2)

    # SHOW GRID
    self.grid1 = QCheckBox()
    self.grid2 = QCheckBox()

    shw_grid_label = QLabel("Show Grid:")
    shw_grid_label.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    grid.addWidget(shw_grid_label, 1, 0, alignment=Qt.AlignLeft)
    grid.addWidget(self.grid1, 1, 1, alignment=Qt.AlignCenter)
    grid.addWidget(self.grid2, 1, 2, alignment=Qt.AlignCenter)

    # AVERAGING
    avg1 = QComboBox()
    avg2 = QComboBox()

    delegate = CenterDelegate()
    avg1.setItemDelegate(delegate)
    avg2.setItemDelegate(delegate)

    avg1.setFixedWidth(120)
    avg1.setFixedHeight(30)
    avg2.setFixedWidth(120)
    avg2.setFixedHeight(30)

    avg1.addItems(["x1", "x10", "x20", "x30"])
    avg2.addItems(["x1", "x10", "x20", "x30"])

    avg_label = QLabel("Averaging:")
    avg_label.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    grid.addWidget(avg_label, 2, 0, alignment=Qt.AlignLeft)
    grid.addWidget(avg1, 2, 1, alignment=Qt.AlignCenter)
    grid.addWidget(avg2, 2, 2, alignment=Qt.AlignCenter)

    layout.addLayout(grid)

    layout.addSpacing(12)

    sep2 = QFrame()
    sep2.setFixedHeight(1)
    sep2.setFrameShape(QFrame.NoFrame)
    sep2.setStyleSheet("""
        border-top: 1px solid rgba(255, 255, 255, 140);
    """)
    layout.addWidget(sep2)

    # =====================================================
    # AXIS
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

    # HEADERS ALIGNMENT FIX
    ag1 = QLabel("Graphic 1")
    ag2 = QLabel("Graphic 2")

    ag1.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")
    ag2.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    for g in (ag1, ag2):
        g.setAlignment(Qt.AlignCenter)
        g.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    axis_grid.addWidget(ag1, 0, 1)
    axis_grid.addWidget(ag2, 0, 2)

    # CHECKS
    auto1 = QCheckBox()
    auto2 = QCheckBox()

    auto_sclae_label = QLabel("Auto Scale:")
    auto_sclae_label.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    axis_grid.addWidget(auto_sclae_label, 1, 0, alignment=Qt.AlignLeft)
    axis_grid.addWidget(auto1, 1, 1, alignment=Qt.AlignCenter)
    axis_grid.addWidget(auto2, 1, 2, alignment=Qt.AlignCenter)

    # Y LIMITS
    y1_min = QLineEdit(); y1_max = QLineEdit()
    y2_min = QLineEdit(); y2_max = QLineEdit()

    for w in (y1_min, y1_max, y2_min, y2_max):
        w.setAlignment(Qt.AlignCenter)

    y1_min.setPlaceholderText("Min")
    y1_max.setPlaceholderText("Max")
    y2_min.setPlaceholderText("Min")
    y2_max.setPlaceholderText("Max")

    y_range_label = QLabel("Y Range:")
    y_range_label.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    axis_grid.addWidget(y_range_label, 3, 0, alignment=Qt.AlignLeft)

    row = QHBoxLayout()
    row.setSpacing(15)
    row.addStretch()
    row.addWidget(y1_min)
    row.addWidget(y1_max)
    row.addSpacing(15)
    row.addWidget(y2_min)
    row.addWidget(y2_max)
    row.addStretch()

    axis_grid.addLayout(row, 3, 1, 1, 2)

    layout.addLayout(axis_grid)

    layout.addSpacing(8)

    sep3 = QFrame()
    sep3.setFixedHeight(1)
    sep3.setFrameShape(QFrame.NoFrame)
    sep3.setStyleSheet("""
        border-top: 1px solid rgba(255, 255, 255, 140);
    """)
    layout.addWidget(sep3)

    layout.addSpacing(10)

    # =====================================================
    # ACTIONS
    # =====================================================

    actions = QHBoxLayout()

    apply_btn = QPushButton("Apply")
    cancel_btn = QPushButton("Cancel")

    apply_btn.setMinimumSize(100, 30)
    cancel_btn.setMinimumSize(100, 30)

    apply_btn.clicked.connect(lambda: apply_plot_settings(self))

    actions.addStretch()
    actions.addWidget(apply_btn)
    actions.addWidget(cancel_btn)

    layout.addLayout(actions)

    main.addWidget(frame)

    cancel_btn.clicked.connect(self.dialog.reject)

    self.dialog.exec()

def open_view_window(self):
    open_view(self)
    self.dialog.close()

def open_edit_graphics_markers(self):
    edit_graphics_markers(self)
    self.dialog.close()

def apply_plot_settings(self):
  
    if self.grid1.isChecked():
        current_state = True
    else:
        current_state = False

    self.ax_left.grid(current_state)
    self.fig_left.canvas.draw_idle()

    if self.grid2.isChecked():
        current_state = True
    else:
        current_state = False
    
    self.ax_right.grid(current_state)
    self.fig_right.canvas.draw_idle()

    self.dialog.accept()

def edit_graphics(self):
    pass


def edit_markers(self):
    pass