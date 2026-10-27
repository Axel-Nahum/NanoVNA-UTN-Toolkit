"""
Characterization wizard main window.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys
import os
import traceback

from PySide6.QtCore import Qt, QObject, QEvent, QSize, QPointF, QRectF
from PySide6.QtGui import QGuiApplication, QFont, QIcon, QPixmap, QPainter, QColor, QPolygonF
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QScrollArea
)

logger = logging.getLogger(__name__)


class _FlashDetector(QObject):
    """App-level event filter: logs any unexpected top-level window that appears."""

    def __init__(self, wizard, parent=None):
        super().__init__(parent)
        self._wizard = wizard

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show:
            widget = obj
            # Only care about top-level windows (no Qt parent) that aren't the wizard.
            try:
                is_top_level = widget.isWidgetType() and widget.parent() is None
                is_wizard = widget is self._wizard
            except RuntimeError:
                return False
            if is_top_level and not is_wizard:
                stack = "".join(traceback.format_stack())
                logger.warning(
                    "[FlashDetector] Unexpected top-level window shown!\n"
                    "  class : %s\n"
                    "  title : %r\n"
                    "  obj   : %r\n"
                    "--- Python stack at Show event ---\n%s",
                    type(widget).__name__,
                    getattr(widget, "windowTitle", lambda: "")(),
                    widget,
                    stack,
                )
        return False  # never consume the event

try:
    from NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode import dark_light_config

    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.introduction_screen import (
        build_introduction_screen
    )

    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.steps_manager import (
        update_step_screen
    )

    from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import get as get_technique
    from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration.permittivity_probe_calibration import (
        PermittivityProbeCalibration
    )

except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    sys.exit(1)

apply_window_icon = safe_import("NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon")

# ------------------------------------------------------------------------------------------------------------------- #

class CharacterizationWizard(QMainWindow):

    def __init__(self, vna_device=None):
        super().__init__()

        self.vna = vna_device

        self.setWindowTitle(
            "NanoVNA Toolkit - Characterization Wizard"
        )

        screen = QGuiApplication.primaryScreen().availableGeometry()
        _W = min(1240, max(940, int(screen.width()  * 0.82)))
        _H = min(740,  max(610, int(screen.height() * 0.82)))
        self._wiz_w = _W
        self._wiz_h = _H
        self.setGeometry(200, 200, _W, _H)
        self.setFixedSize(_W, _H)

        window_geometry = self.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)

        self.move(window_geometry.topLeft())

# ------------------------------------------------------------------------------------------------------------------- #
        # Dark-Light mode
# ------------------------------------------------------------------------------------------------------------------- #

        dark_light_config(self)

# ------------------------------------------------------------------------------------------------------------------- #
        # Internal state
# ------------------------------------------------------------------------------------------------------------------- #

        self.vna_device = vna_device

        # Localized technique name (kept for MeasurementMainWindow compatibility)
        self.selected_method = None
        # Stable technique id used for step dispatch
        self.selected_technique_id = None

        self.current_step = 0

        # Label shown on the Next button when on the final (result) step.
        self.finish_button_text = "Finish ✓"

        # --- Session state ------------------------------------------------ #
        self.perm_calibration = PermittivityProbeCalibration()
        # True after the first pre-cal propagation; individual-only after that.
        self._precal_propagated = False
        self.sweep_start_freq = 50_000          # 50 kHz
        self.sweep_stop_freq = 1_500_000_000    # 1.5 GHz
        self.sweep_steps = 101
        self.temperature_c = 25.0
        self.temperature_warnings = []
        self.unknown_liquid_name = ""
        self.epsilon_result = None
        # Plot handles populated by measurement screens.
        self.current_fig = None
        self.current_ax = None
        self.current_canvas = None
        self.status_label = None

# ------------------------------------------------------------------------------------------------------------------- #
        # Window icon
# ------------------------------------------------------------------------------------------------------------------- #

        apply_window_icon(self)

# ------------------------------------------------------------------------------------------------------------------- #
        # Central widget
# ------------------------------------------------------------------------------------------------------------------- #

        self.central_widget = QWidget()

        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        self.main_layout.setContentsMargins(20, 20, 20, 20)

# ------------------------------------------------------------------------------------------------------------------- #
        # Title
# ------------------------------------------------------------------------------------------------------------------- #

        self.title_label = QLabel("Characterization Methods")

        self.title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
        """)

        def _make_pencil_icon(color_hex: str, sz: int = 20) -> QIcon:
            px = QPixmap(sz, sz)
            px.fill(QColor(0, 0, 0, 0))
            p = QPainter(px)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            # center + rotate so pencil runs NE-SW, fully symmetric around (sz/2, sz/2)
            p.translate(sz / 2, sz / 2)
            p.rotate(45)
            c = QColor(color_hex)
            p.setPen(Qt.PenStyle.NoPen)
            # total span: -8.5 .. +8.5  → center at 0
            # eraser cap (top)
            p.setBrush(QColor("#6688aa"))
            p.drawRoundedRect(QRectF(-3, -8.5, 6, 2.5), 1, 1)
            # body
            p.setBrush(c)
            p.drawRoundedRect(QRectF(-3, -6, 6, 10), 1.5, 1.5)
            # tip triangle (bottom)
            tip = QPolygonF([QPointF(-3, 4), QPointF(3, 4), QPointF(0, 8.5)])
            p.setBrush(c.darker(140))
            p.drawPolygon(tip)
            p.end()
            return QIcon(px)

        self._rename_liquid_btn = QPushButton()
        self._rename_liquid_btn.setIcon(_make_pencil_icon("#7ab3f5", 20))
        self._rename_liquid_btn.setIconSize(QSize(20, 20))
        self._rename_liquid_btn.setFixedSize(30, 30)
        self._rename_liquid_btn.setVisible(False)
        self._rename_liquid_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; }"
            " QPushButton:hover { background: rgba(122,179,245,30); border-radius: 5px; }"
        )
        self._rename_liquid_btn.setToolTip("Rename liquid")

        _title_row = QHBoxLayout()
        _title_row.setSpacing(6)
        _title_row.setContentsMargins(0, 0, 0, 0)
        _title_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        _title_row.addWidget(self.title_label)
        self._rename_liquid_btn.setContentsMargins(0, 4, 0, 0)
        _title_row.addWidget(self._rename_liquid_btn, 0, Qt.AlignmentFlag.AlignBottom)
        _title_row.addStretch()

        # HEADER (FIJO)
        self.header_layout = QVBoxLayout()
        self.header_layout.addLayout(_title_row)
        self.header_layout.addSpacing(10)

        self.main_layout.addLayout(self.header_layout)

# ------------------------------------------------------------------------------------------------------------------- #
        # Content layout
# ------------------------------------------------------------------------------------------------------------------- #

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._content_widget = QWidget()
        self.content_layout = QVBoxLayout(self._content_widget)
        self._scroll_area.setWidget(self._content_widget)

        self.main_layout.addWidget(self._scroll_area, stretch=1)

# ------------------------------------------------------------------------------------------------------------------- #
        # Bottom navigation
# ------------------------------------------------------------------------------------------------------------------- #

        self.bottom_layout = QHBoxLayout()
        self.back_button = QPushButton("◀◀")
        self.back_button.setFixedSize(100, 30)
        self.back_button.setStyleSheet("font-size: 14px;")

        self.back_button.clicked.connect(
            self.go_to_previous_step
        )

        self.next_button = QPushButton("▶▶")
        self.next_button.setEnabled(False)
        self.next_button.setFixedSize(100, 30)
        self.next_button.setStyleSheet("font-size: 14px;")

        self.next_button.clicked.connect(
            self.go_to_next_step
        )

        self.save_calibration_button = QPushButton("💾  Save calibration")
        self.save_calibration_button.setFixedHeight(30)
        self.save_calibration_button.setStyleSheet("font-size: 13px; padding: 0 12px;")
        self.save_calibration_button.setVisible(False)

        self.bottom_layout.addWidget(
            self.back_button,
            alignment=Qt.AlignLeft
        )

        self.bottom_layout.addStretch(1)

        self.bottom_layout.addWidget(
            self.save_calibration_button,
            alignment=Qt.AlignRight
        )

        self.bottom_layout.addSpacing(8)

        self.bottom_layout.addWidget(
            self.next_button,
            alignment=Qt.AlignLeft
        )

        self.bottom_layout.setContentsMargins(0, 15, 0, 0)

        self.bottom_layout.addStretch()

        self.main_layout.addLayout(self.bottom_layout)

# ------------------------------------------------------------------------------------------------------------------- #
        # First screen
# ------------------------------------------------------------------------------------------------------------------- #

        build_introduction_screen(self)

        # Debug: log any unexpected top-level window that appears while the wizard is open.
        self._flash_detector = _FlashDetector(self)
        QApplication.instance().installEventFilter(self._flash_detector)

# ------------------------------------------------------------------------------------------------------------------- #

    def showEvent(self, event):
        super().showEvent(event)
        screen = QGuiApplication.screenAt(self.pos()) or QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            max_h = avail.height() - 60
            if self.height() > max_h:
                self.resize(self.width(), max_h)
            # keep the window inside the screen vertically
            if self.y() + self.height() > avail.y() + avail.height():
                self.move(self.x(), max(avail.y(), avail.y() + avail.height() - self.height()))

    def clear_content(self):

        while self.content_layout.count():

            item = self.content_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:

                widget.deleteLater()

            elif item.layout() is not None:

                self.clear_layout(item.layout())

# ------------------------------------------------------------------------------------------------------------------- #

    def clear_layout(self, layout):

        while layout.count():

            item = layout.takeAt(0)

            widget = item.widget()

            if widget is not None:

                widget.deleteLater()

            elif item.layout() is not None:

                self.clear_layout(item.layout())

        layout.deleteLater()

# ------------------------------------------------------------------------------------------------------------------- #

    def go_to_next_step(self):

        # No technique selected yet -> stay on the intro screen.
        if not self.selected_technique_id:
            return

        descriptor = get_technique(self.selected_technique_id)

        # On the final (result) step, Next acts as "Finish".
        if self.current_step >= len(descriptor.steps):
            self.finish_characterization()
            return

        self.current_step += 1

        update_step_screen(self)

# ------------------------------------------------------------------------------------------------------------------- #

    def go_to_previous_step(self):

        if self.current_step > 0:

            self.current_step -= 1

            update_step_screen(self)

        else:

            self.return_to_previous_window()

# ------------------------------------------------------------------------------------------------------------------- #

    # Sweep getters consumed by the measurement runner.
    def get_sweep_start_frequency(self):
        return self.sweep_start_freq

    def get_sweep_stop_frequency(self):
        return self.sweep_stop_freq

    def get_sweep_steps(self):
        return self.sweep_steps

# ------------------------------------------------------------------------------------------------------------------- #

    def finish_characterization(self):
        """Open the measurement results window and close the wizard."""
        logging.info("[CharacterizationWizard] Finishing -> opening MeasurementMainWindow")

        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.measurement_main_window import (
            MeasurementMainWindow
        )

        self.measurement_window = MeasurementMainWindow(
            vna_device=self.vna_device, wizard_window=self
        )
        self.measurement_window.show()
        self.close()

# ------------------------------------------------------------------------------------------------------------------- #

    def return_to_previous_window(self):

        logging.info(
            "[CharacterizationWizard] Returning to previous window"
        )

        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.characterization_welcome.characterization_welcome import (
            MaterialCharacterizationWelcome
        )

        if self.vna:
            self.welcome_windows = (
                MaterialCharacterizationWelcome(vna_device=self.vna)
            )
        else:
            self.welcome_windows = (
                MaterialCharacterizationWelcome()
            )

        self.welcome_windows.show()

        self.close()

# ------------------------------------------------------------------------------------------------------------------- #

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = CharacterizationWizard()

    window.show()

    sys.exit(app.exec())
