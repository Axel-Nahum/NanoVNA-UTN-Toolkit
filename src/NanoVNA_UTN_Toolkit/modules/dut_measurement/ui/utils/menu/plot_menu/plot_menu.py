import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QComboBox, QStyledItemDelegate,
    QLineEdit, QFrame, QGridLayout, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QDoubleValidator

try:
    from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.view_edit_menu.view_edit_menu import open_view, edit_graphics_markers
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.auto_scale.auto_scale import save_auto_scale_data, on_auto_scale_toggled
except ImportError as e:
    import logging, sys
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

    # ----------------------------------------------------
    # Plot Manager settings
    # ----------------------------------------------------

    self.settings = get_settings(
        "INI/dut_measurement/plot_manager/plot_manager.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/plot_manager.ini",
        Path(__file__).resolve()
    )

    # =====================================================
    # TITLE
    # =====================================================

    title = QLabel(f"{self.plot_manager_title}")
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet("font-size: 25px; font-weight: bold; border: none;")
    layout.addWidget(title)

    # =====================================================
    # TOOLS
    # =====================================================

    tools_title = QLabel(f"{self.graphics_tools_title}")
    tools_title.setAlignment(Qt.AlignCenter)
    tools_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    layout.addWidget(tools_title)

    tools = QHBoxLayout()

    graphics_btn = QPushButton(f"{self.plot_view_button_label}")
    markers_btn = QPushButton(f"{self.graphics_markers_editor_button_label}")

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

    display_title = QLabel(f"{self.display_options_title}")
    display_title.setAlignment(Qt.AlignCenter)
    display_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    layout.addWidget(display_title)

    grid = QGridLayout()
    grid.setHorizontalSpacing(28)

    grid.setColumnStretch(0, 3)
    grid.setColumnStretch(1, 2)
    grid.setColumnStretch(2, 2)

    # HEADERS
    g1 = QLabel(f"{self.graphic1_label}")
    g2 = QLabel(f"{self.graphic2_label}")

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

    grid1_set_checked = self.settings.value("grid/current_left_state", "true", type=bool)
    grid2_set_checked = self.settings.value("grid/current_right_state", "true", type=bool)

    self.grid1.setChecked(grid1_set_checked)
    self.grid2.setChecked(grid2_set_checked)

    shw_grid_label = QLabel(f"{self.show_grid_label}")
    shw_grid_label.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    grid.addWidget(shw_grid_label, 1, 0, alignment=Qt.AlignLeft)
    grid.addWidget(self.grid1, 1, 1, alignment=Qt.AlignCenter)
    grid.addWidget(self.grid2, 1, 2, alignment=Qt.AlignCenter)

    # AVERAGING
    avg1 = QComboBox()
    avg2 = QComboBox()

    self.avg1 = avg1
    self.avg2 = avg2

    delegate = CenterDelegate()
    avg1.setItemDelegate(delegate)
    avg2.setItemDelegate(delegate)

    avg1.setFixedWidth(120)
    avg1.setFixedHeight(30)
    avg2.setFixedWidth(120)
    avg2.setFixedHeight(30)

    avg1.addItems(["x1", "x10", "x20", "x30"])
    avg2.addItems(["x1", "x10", "x20", "x30"])

    avg_label = QLabel(f"{self.averaging_label}")
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

    axis_title = QLabel(f"{self.axis_settings_title}")
    axis_title.setAlignment(Qt.AlignCenter)
    axis_title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    layout.addWidget(axis_title)

    axis_grid = QGridLayout()
    axis_grid.setHorizontalSpacing(28)

    axis_grid.setColumnStretch(0, 3)
    axis_grid.setColumnStretch(1, 2)
    axis_grid.setColumnStretch(2, 2)

    # HEADERS ALIGNMENT FIX
    ag1 = QLabel(f"{self.graphic1_label}")
    ag2 = QLabel(f"{self.graphic2_label}")

    ag1.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")
    ag2.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    for g in (ag1, ag2):
        g.setAlignment(Qt.AlignCenter)
        g.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    axis_grid.addWidget(ag1, 0, 1)
    axis_grid.addWidget(ag2, 0, 2)

    # CHECKS
    self.auto1 = QCheckBox()
    self.auto2 = QCheckBox()

    auto1_set_checked = self.settings.value("auto_scale/current_left_state", "true", type=bool) 
    auto2_set_checked = self.settings.value("auto_scale/current_right_state", "true", type=bool) 
    self.auto1.setChecked(auto1_set_checked)
    self.auto2.setChecked(auto2_set_checked)

    self.auto1.toggled.connect(lambda _: update_auto_scale_ui(self))
    self.auto2.toggled.connect(lambda _: update_auto_scale_ui(self))

    self.auto1.toggled.connect(lambda checked: (self.y1_min.setEnabled(not checked), self.y1_max.setEnabled(not checked)))

    self.auto2.toggled.connect(lambda checked: (self.y2_min.setEnabled(not checked), self.y2_max.setEnabled(not checked)))

    auto_sclae_label = QLabel(f"{self.auto_scale_label}")
    auto_sclae_label.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    axis_grid.addWidget(auto_sclae_label, 1, 0, alignment=Qt.AlignLeft)
    axis_grid.addWidget(self.auto1, 1, 1, alignment=Qt.AlignCenter)
    axis_grid.addWidget(self.auto2, 1, 2, alignment=Qt.AlignCenter)

    # Y LIMITS
    self.y1_min = QLineEdit(); self.y1_max = QLineEdit()
    self.y2_min = QLineEdit(); self.y2_max = QLineEdit()

    validator = QDoubleValidator()
    validator.setNotation(QDoubleValidator.StandardNotation)

    self.y1_min.setValidator(validator)
    self.y1_max.setValidator(validator)
    self.y2_min.setValidator(validator)
    self.y2_max.setValidator(validator)

    self.y1_min.setEnabled(False)
    self.y1_max.setEnabled(False)

    self.y2_min.setEnabled(False)
    self.y2_max.setEnabled(False)

    for w in (self.y1_min, self.y1_max, self.y2_min, self.y2_max):
        w.setAlignment(Qt.AlignCenter)

    self.y1_min.setPlaceholderText("Min")
    self.y1_max.setPlaceholderText("Max")
    self.y2_min.setPlaceholderText("Min")
    self.y2_max.setPlaceholderText("Max")

    y_range_label = QLabel(f"{self.y_range_label}")
    y_range_label.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    axis_grid.addWidget(y_range_label, 3, 0, alignment=Qt.AlignLeft)

    row = QHBoxLayout()
    row.setSpacing(15)
    row.addStretch()
    row.addWidget(self.y1_min)
    row.addWidget(self.y1_max)
    row.addSpacing(15)
    row.addWidget(self.y2_min)
    row.addWidget(self.y2_max)
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

    apply_btn = QPushButton(f"{self.apply_button_label}")
    cancel_btn = QPushButton(f"{self.cancel_button_label}")

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
    self.dialog.close()
    QTimer.singleShot(0, lambda: open_view(self))

def open_edit_graphics_markers(self):
    self.dialog.close()
    QTimer.singleShot(0, lambda: edit_graphics_markers(self))

def apply_plot_settings(self):
  
    set_grid_states(self)

    self.dialog.accept()

def set_grid_states(self):
    if self.grid1.isChecked():
        current_state = True
    else:
        current_state = False

    self.settings.setValue("grid/current_left_state", current_state)

    self.ax_left.grid(current_state)
    self.fig_left.canvas.draw_idle()

    if self.grid2.isChecked():
        current_state = True
    else:
        current_state = False
    
    self.settings.setValue("grid/current_right_state", current_state)

    self.ax_right.grid(current_state)
    self.fig_right.canvas.draw_idle()

def update_auto_scale_ui(self):
    state_left = self.auto1.isChecked()
    state_right = self.auto2.isChecked()

    # habilitar / deshabilitar inputs
    self.y1_min.setEnabled(not state_left)
    self.y1_max.setEnabled(not state_left)
    self.y2_min.setEnabled(not state_right)
    self.y2_max.setEnabled(not state_right)

    # SI auto-scale está ON → limpiar todo
    if state_left:
        self.y1_min.clear()
        self.y1_max.clear()
        self.y1_min.setPlaceholderText("Min")
        self.y1_max.setPlaceholderText("Max")

    # SI auto-scale está OFF → asegurar placeholders visibles
    else:
        if not self.y1_min.text():
            self.y1_min.setPlaceholderText("Min")
        if not self.y1_max.text():
            self.y1_max.setPlaceholderText("Max")

    if state_right:
        self.y2_min.clear()
        self.y2_max.clear()
        self.y2_min.setPlaceholderText("Min")
        self.y2_max.setPlaceholderText("Max")
    else:
        if not self.y2_min.text():
            self.y2_min.setPlaceholderText("Min")
        if not self.y2_max.text():
            self.y2_max.setPlaceholderText("Max")

def save_auto_scale_settings(self):
    update_auto_scale_ui(self)

    self.auto_scale_enabled_left = self.auto1.isChecked()
    self.auto_scale_enabled_right = self.auto2.isChecked()

    self.settings.setValue("auto_scale/current_left_state", self.auto1.isChecked())
    self.settings.setValue("auto_scale/current_right_state", self.auto2.isChecked())

    on_auto_scale_toggled(self)

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------

    left_invalid = (
        self.left_graph_type != "Smith Diagram"
        and not self.auto1.isChecked()
        and (
            not self.y1_min.text().strip()
            or not self.y1_max.text().strip()
        )
    )

    right_invalid = (
        self.right_graph_type != "Smith Diagram"
        and not self.auto2.isChecked()
        and (
            not self.y2_min.text().strip()
            or not self.y2_max.text().strip()
        )
    )

    if left_invalid and right_invalid:
        QMessageBox.warning(
            self.dialog,
            f"{self.warning_title}",
            f"{self.missing_both_graphics_message}"
        )
        return False

    if left_invalid:
        QMessageBox.warning(
            self.dialog,
            f"{self.warning_title}",
            f"{self.missing_graphic1_message}"
        )
        return False

    if right_invalid:
        QMessageBox.warning(
            self.dialog,
            f"{self.warning_title}",
            f"{self.missing_graphic2_message}"
        )
        return False

    # -------------------------------------------------
    # Apply Graphic 1
    # -------------------------------------------------

    if self.left_graph_type != "Smith Diagram" and not self.auto1.isChecked():

        ymin = float(self.y1_min.text())
        ymax = float(self.y1_max.text())

        save_auto_scale_data(self, ymin, ymax, self.ax_left)

        self.ax_left.set_ylim(ymin, ymax)
        self.fig_left.canvas.draw_idle()

    # -------------------------------------------------
    # Apply Graphic 2
    # -------------------------------------------------

    if self.right_graph_type != "Smith Diagram" and not self.auto2.isChecked():

        ymin = float(self.y2_min.text())
        ymax = float(self.y2_max.text())

        save_auto_scale_data(self, ymin, ymax, self.ax_right)

        self.ax_right.set_ylim(ymin, ymax)
        self.fig_right.canvas.draw_idle()

    return True

def save_average_settings(self):
    self.settings.setValue(
        "averaging/graphic1",
        self.avg1.currentText()
    )

    self.settings.setValue(
        "averaging/graphic2",
        self.avg2.currentText()
    )

    self.settings.sync()

def apply_plot_settings(self):

    # ---------------------------------------------
    # GRID
    # ---------------------------------------------

    set_grid_states(self)

    # ---------------------------------------------
    # AUTO SCALE
    # ---------------------------------------------

    if not save_auto_scale_settings(self):
        self.settings.setValue("auto_scale/current_left_state", True)
        self.settings.setValue("auto_scale/current_right_state", True)
        self.auto_scale_enabled_left = True
        self.auto_scale_enabled_right = True
        on_auto_scale_toggled(self)
        return
    
    # ---------------------------------------------
    # AVERAGING
    # ---------------------------------------------

    save_average_settings(self)

    self.dialog.accept()