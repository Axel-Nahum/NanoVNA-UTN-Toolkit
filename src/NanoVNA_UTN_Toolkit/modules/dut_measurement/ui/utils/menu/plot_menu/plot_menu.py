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


KALMAN_PRESETS = {
    "Light":  {"Q": 0.1,   "R": 0.01},
    "Medium": {"Q": 0.01,  "R": 0.1},
    "Strong": {"Q": 0.001, "R": 1.0},
}


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

    self.dialog = QDialog(self)
    self.dialog.setWindowTitle("Plot Manager")
    self.dialog.setFixedSize(660, 860)
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
    sep1.setStyleSheet("border-top: 1px solid rgba(255, 255, 255, 140);")
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

    # -------------------------------------------------------
    # KALMAN FILTER — Enable checkboxes (row 2)
    # -------------------------------------------------------

    self.kalman_check1 = QCheckBox()
    self.kalman_check2 = QCheckBox()

    kalman1_enabled = self.settings.value("kalman/enabled_left", "false", type=bool)
    kalman2_enabled = self.settings.value("kalman/enabled_right", "false", type=bool)

    self.kalman_check1.setChecked(kalman1_enabled)
    self.kalman_check2.setChecked(kalman2_enabled)

    kalman_enable_label = QLabel("Kalman Filter")
    kalman_enable_label.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    grid.addWidget(kalman_enable_label, 2, 0, alignment=Qt.AlignLeft)
    grid.addWidget(self.kalman_check1, 2, 1, alignment=Qt.AlignCenter)
    grid.addWidget(self.kalman_check2, 2, 2, alignment=Qt.AlignCenter)

    # -------------------------------------------------------
    # KALMAN FILTER — Preset combos + Advanced button (row 3)
    # -------------------------------------------------------

    self.kalman_combo1 = QComboBox()
    self.kalman_combo2 = QComboBox()

    delegate = CenterDelegate()
    self.kalman_combo1.setItemDelegate(delegate)
    self.kalman_combo2.setItemDelegate(delegate)

    self.kalman_combo1.setFixedWidth(120)
    self.kalman_combo1.setFixedHeight(30)
    self.kalman_combo2.setFixedWidth(120)
    self.kalman_combo2.setFixedHeight(30)

    for combo in (self.kalman_combo1, self.kalman_combo2):
        combo.addItems(list(KALMAN_PRESETS.keys()))

    self.kalman_combo1.currentTextChanged.connect(
        lambda _: handle_kalman_combo_change(self, self.kalman_combo1)
    )

    self.kalman_combo2.currentTextChanged.connect(
        lambda _: handle_kalman_combo_change(self, self.kalman_combo2)
    )

    saved_preset1 = self.settings.value("kalman/preset_left", "Medium")
    saved_preset2 = self.settings.value("kalman/preset_right", "Medium")

    if saved_preset1 == "Custom":
        self.kalman_combo1.addItem("Custom")

    if saved_preset2 == "Custom":
        self.kalman_combo2.addItem("Custom")

    idx1 = self.kalman_combo1.findText(saved_preset1)
    idx2 = self.kalman_combo2.findText(saved_preset2)
    if idx1 >= 0:
        self.kalman_combo1.setCurrentIndex(idx1)
    if idx2 >= 0:
        self.kalman_combo2.setCurrentIndex(idx2)

    # Disable combos if filter is off
    self.kalman_combo1.setEnabled(kalman1_enabled)
    self.kalman_combo2.setEnabled(kalman2_enabled)

    # Wire checkboxes → enable/disable combos
    self.kalman_check1.toggled.connect(lambda: update_kalman_ui(self))  
    self.kalman_check2.toggled.connect(lambda: update_kalman_ui(self))

    # Combos centered in their respective columns (row 3)
    grid.addWidget(self.kalman_combo1, 3, 1, alignment=Qt.AlignCenter)
    grid.addWidget(self.kalman_combo2, 3, 2, alignment=Qt.AlignCenter)

    grid.setRowMinimumHeight(4, 15)

    # Advanced — flat text button, centered below combos (row 4, spans all cols)
    self.kalman_adv_btn = QPushButton("Advanced...")
    self.kalman_adv_btn.setFlat(True)
    self.kalman_adv_btn.setStyleSheet("""
        QPushButton {
            border: none;
            background: transparent;
            color: white;
            font-size: 12px;
        }

        QPushButton:hover {
            text-decoration: underline;
        }
        QPushButton:disabled {
            color: gray;
        }
        """
    )
    self.kalman_adv_btn.setCursor(Qt.PointingHandCursor)
    self.kalman_adv_btn.clicked.connect(lambda: open_kalman_advanced(self))

    advanced_layout = QHBoxLayout()

    advanced_layout.addStretch()
    advanced_layout.addWidget(self.kalman_adv_btn)
    advanced_layout.addStretch()

    grid.addLayout(
        advanced_layout,
        4,
        1,
        1,
        2
    )

    update_kalman_ui(self)

    layout.addLayout(grid)

    layout.addSpacing(12)

    sep2 = QFrame()
    sep2.setFixedHeight(1)
    sep2.setFrameShape(QFrame.NoFrame)
    sep2.setStyleSheet("border-top: 1px solid rgba(255, 255, 255, 140);")
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

    ag1 = QLabel(f"{self.graphic1_label}")
    ag2 = QLabel(f"{self.graphic2_label}")

    for g in (ag1, ag2):
        g.setAlignment(Qt.AlignCenter)
        g.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    axis_grid.addWidget(ag1, 0, 1)
    axis_grid.addWidget(ag2, 0, 2)

    # AUTO SCALE CHECKS
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

    auto_scale_label = QLabel(f"{self.auto_scale_label}")
    auto_scale_label.setStyleSheet("font-weight: bold; font-size: 15px; border: none;")

    axis_grid.addWidget(auto_scale_label, 1, 0, alignment=Qt.AlignLeft)
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
    sep3.setStyleSheet("border-top: 1px solid rgba(255, 255, 255, 140);")
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


# =========================================================
# KALMAN ADVANCED DIALOG
# =========================================================

def open_kalman_advanced(self):
    adv = QDialog(self.dialog)
    adv.setWindowTitle("Kalman Filter — Advanced")
    adv.setStyleSheet(self.styleSheet())
    adv.setWindowFlags(
        Qt.WindowType.Dialog |
        Qt.WindowType.MSWindowsFixedSizeDialogHint
    )
    adv.setFocus()

    adv.setFixedSize(340, 280)

    layout = QVBoxLayout(adv)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(12)

    title = QLabel("Custom Parameters")
    title.setAlignment(Qt.AlignCenter)
    title.setStyleSheet("font-size: 16px; font-weight: bold;")
    layout.addWidget(title)

    validator = QDoubleValidator(1e-9, 1e9, 6)
    validator.setNotation(QDoubleValidator.ScientificNotation)

    show_left = self.kalman_check1.isChecked()
    show_right = self.kalman_check2.isChecked()

    # =====================================================
    # Q
    # =====================================================

    q_label = QLabel("Process noise (Q)")
    q_label.setAlignment(Qt.AlignCenter)
    q_label.setStyleSheet("font-weight: bold; font-size: 13px;")
    layout.addWidget(q_label)

    q_row = QHBoxLayout()

    q1_edit = None
    q2_edit = None

    if show_left:
        q1_edit = QLineEdit()
        q1_edit.setAlignment(Qt.AlignCenter)
        q1_edit.setPlaceholderText("Q1")
        q1_edit.setValidator(validator)

        saved_q1 = self.settings.value("kalman/custom_Q_left", "")
        if saved_q1:
            q1_edit.setText(saved_q1)

        q_row.addWidget(q1_edit)

    if show_right:
        q2_edit = QLineEdit()
        q2_edit.setAlignment(Qt.AlignCenter)
        q2_edit.setPlaceholderText("Q2")
        q2_edit.setValidator(validator)

        saved_q2 = self.settings.value("kalman/custom_Q_right", "")
        if saved_q2:
            q2_edit.setText(saved_q2)

        q_row.addWidget(q2_edit)

    if q1_edit:
        q1_edit.clearFocus()

    if q2_edit:
        q2_edit.clearFocus()

    layout.addLayout(q_row)

    q_hint = QLabel(
        "Controls how much the model trusts new measurements.\n"
        "Higher Q → faster response, more noise."
    )
    q_hint.setAlignment(Qt.AlignCenter)
    q_hint.setWordWrap(True)
    q_hint.setStyleSheet("font-size: 11px; color: gray;")
    layout.addWidget(q_hint)

    layout.addSpacing(4)

    # =====================================================
    # R
    # =====================================================

    r_label = QLabel("Measurement noise (R)")
    r_label.setAlignment(Qt.AlignCenter)
    r_label.setStyleSheet("font-weight: bold; font-size: 13px;")
    layout.addWidget(r_label)

    r_row = QHBoxLayout()

    r1_edit = None
    r2_edit = None

    if show_left:
        r1_edit = QLineEdit()
        r1_edit.setAlignment(Qt.AlignCenter)
        r1_edit.setPlaceholderText("R1")
        r1_edit.setValidator(validator)

        saved_r1 = self.settings.value("kalman/custom_R_left", "")
        if saved_r1:
            r1_edit.setText(saved_r1)

        r_row.addWidget(r1_edit)

    if show_right:
        r2_edit = QLineEdit()
        r2_edit.setAlignment(Qt.AlignCenter)
        r2_edit.setPlaceholderText("R2")
        r2_edit.setValidator(validator)

        saved_r2 = self.settings.value("kalman/custom_R_right", "")
        if saved_r2:
            r2_edit.setText(saved_r2)

        r_row.addWidget(r2_edit)

    if r1_edit:
        r1_edit.clearFocus()

    if r2_edit:
        r2_edit.clearFocus()

    layout.addLayout(r_row)

    r_hint = QLabel(
        "Controls how much the filter smooths the signal.\n"
        "Higher R → smoother output, slower tracking."
    )
    r_hint.setAlignment(Qt.AlignCenter)
    r_hint.setWordWrap(True)
    r_hint.setStyleSheet("font-size: 11px; color: gray;")
    layout.addWidget(r_hint)

    layout.addSpacing(8)

    # =====================================================
    # BUTTONS
    # =====================================================

    btn_row = QHBoxLayout()

    ok_btn = QPushButton("Apply")
    cancel_btn = QPushButton("Cancel")

    ok_btn.setMinimumSize(90, 28)
    cancel_btn.setMinimumSize(90, 28)

    btn_row.addStretch()
    btn_row.addWidget(ok_btn)
    btn_row.addWidget(cancel_btn)
    btn_row.addStretch()

    layout.addLayout(btn_row)

    def apply_advanced():

        if show_left:

            if not q1_edit.text().strip() or not r1_edit.text().strip():
                QMessageBox.warning(
                    adv,
                    "Missing values",
                    "Please enter Q and R values for Graphic 1."
                )
                return

            self.settings.setValue(
                "kalman/custom_Q_left",
                q1_edit.text().strip()
            )

            self.settings.setValue(
                "kalman/custom_R_left",
                r1_edit.text().strip()
            )

            if self.kalman_combo1.findText("Custom") < 0:
                self.kalman_combo1.addItem("Custom")

            self.kalman_combo1.setCurrentText("Custom")

        if show_right:

            if not q2_edit.text().strip() or not r2_edit.text().strip():
                QMessageBox.warning(
                    adv,
                    "Missing values",
                    "Please enter Q and R values for Graphic 2."
                )
                return

            self.settings.setValue(
                "kalman/custom_Q_right",
                q2_edit.text().strip()
            )

            self.settings.setValue(
                "kalman/custom_R_right",
                r2_edit.text().strip()
            )

            if self.kalman_combo2.findText("Custom") < 0:
                self.kalman_combo2.addItem("Custom")

            self.kalman_combo2.setCurrentText("Custom")

        adv.accept()

    ok_btn.clicked.connect(apply_advanced)
    cancel_btn.clicked.connect(adv.reject)

    adv.adjustSize()
    adv.exec()

# =========================================================
# KALMAN UI UPDATE
# =========================================================

def update_kalman_ui(self):

    left_enabled = self.kalman_check1.isChecked()
    right_enabled = self.kalman_check2.isChecked()

    self.kalman_combo1.setEnabled(left_enabled)
    self.kalman_combo2.setEnabled(right_enabled)

    # LEFT
    if not left_enabled:

        if self.kalman_combo1.findText("Off") < 0:
            self.kalman_combo1.insertItem(0, "Off")

        self.kalman_combo1.setCurrentText("Off")

    else:

        idx = self.kalman_combo1.findText("Off")

        if idx >= 0:
            self.kalman_combo1.removeItem(idx)

        if self.kalman_combo1.currentText() == "":
            self.kalman_combo1.setCurrentText("Medium")

    # RIGHT
    if not right_enabled:

        if self.kalman_combo2.findText("Off") < 0:
            self.kalman_combo2.insertItem(0, "Off")

        self.kalman_combo2.setCurrentText("Off")

    else:

        idx = self.kalman_combo2.findText("Off")

        if idx >= 0:
            self.kalman_combo2.removeItem(idx)

        if self.kalman_combo2.currentText() == "":
            self.kalman_combo2.setCurrentText("Medium")

    self.kalman_adv_btn.setEnabled(
        left_enabled or right_enabled
    )

def handle_kalman_combo_change(self, combo):

    if combo.currentText() == "Custom":
        return

    idx = combo.findText("Custom")

    if idx >= 0:
        combo.removeItem(idx)

# =========================================================
# Helpers (unchanged logic)
# =========================================================

def open_view_window(self):
    self.dialog.close()
    QTimer.singleShot(0, lambda: open_view(self))


def open_edit_graphics_markers(self):
    self.dialog.close()
    QTimer.singleShot(0, lambda: edit_graphics_markers(self))


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

    self.y1_min.setEnabled(not state_left)
    self.y1_max.setEnabled(not state_left)
    self.y2_min.setEnabled(not state_right)
    self.y2_max.setEnabled(not state_right)

    if state_left:
        self.y1_min.clear()
        self.y1_max.clear()
        self.y1_min.setPlaceholderText("Min")
        self.y1_max.setPlaceholderText("Max")
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

    if self.left_graph_type != "Smith Diagram" and not self.auto1.isChecked():
        ymin = float(self.y1_min.text())
        ymax = float(self.y1_max.text())
        save_auto_scale_data(self, ymin, ymax, self.ax_left)
        self.ax_left.set_ylim(ymin, ymax)
        self.fig_left.canvas.draw_idle()

    if self.right_graph_type != "Smith Diagram" and not self.auto2.isChecked():
        ymin = float(self.y2_min.text())
        ymax = float(self.y2_max.text())
        save_auto_scale_data(self, ymin, ymax, self.ax_right)
        self.ax_right.set_ylim(ymin, ymax)
        self.fig_right.canvas.draw_idle()

    return True


def save_kalman_settings(self):
    enabled_left  = self.kalman_check1.isChecked()
    enabled_right = self.kalman_check2.isChecked()

    self.settings.setValue("kalman/enabled_left",  enabled_left)
    self.settings.setValue("kalman/enabled_right", enabled_right)

    preset_left  = self.kalman_combo1.currentText()
    preset_right = self.kalman_combo2.currentText()

    self.settings.setValue("kalman/preset_left",  preset_left)
    self.settings.setValue("kalman/preset_right", preset_right)

    def resolve(preset, channel):

        if preset == "Custom":

            q = self.settings.value(
                f"kalman/custom_Q_{channel}",
                None
            )

            r = self.settings.value(
                f"kalman/custom_R_{channel}",
                None
            )

            if q is None or r is None:
                return None, None

            return float(q), float(r)

        params = KALMAN_PRESETS.get(
            preset,
            KALMAN_PRESETS["Medium"]
        )

        return params["Q"], params["R"]

    q1, r1 = resolve(preset_left,  "left")
    q2, r2 = resolve(preset_right, "right")

    # Custom preset chosen but values missing → warn
    if enabled_left and preset_left == "Custom" and (q1 is None or r1 is None):
        QMessageBox.warning(
            self.dialog,
            "Missing Kalman values",
            "Graphic 1 is set to Custom but no Q/R values were entered.\n"
            "Please use the Advanced button to set them."
        )
        return False

    if enabled_right and preset_right == "Custom" and (q2 is None or r2 is None):
        QMessageBox.warning(
            self.dialog,
            "Missing Kalman values",
            "Graphic 2 is set to Custom but no Q/R values were entered.\n"
            "Please use the Advanced button to set them."
        )
        return False

    # Expose to the rest of the application
    self.kalman_enabled_left  = enabled_left
    self.kalman_enabled_right = enabled_right
    self.kalman_Q_left  = q1 if enabled_left  else None
    self.kalman_R_left  = r1 if enabled_left  else None
    self.kalman_Q_right = q2 if enabled_right else None
    self.kalman_R_right = r2 if enabled_right else None

    return True

def apply_plot_settings(self):

    # GRID
    set_grid_states(self)

    # AUTO SCALE
    if not save_auto_scale_settings(self):
        self.settings.setValue("auto_scale/current_left_state", True)
        self.settings.setValue("auto_scale/current_right_state", True)
        self.auto_scale_enabled_left  = True
        self.auto_scale_enabled_right = True
        on_auto_scale_toggled(self)
        return

    # KALMAN
    if not save_kalman_settings(self):
        return

    self.dialog.accept()