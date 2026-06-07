"""
Characterization wizard main window.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel
)

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

        self.setGeometry(200, 200, 950, 620)

        screen = QGuiApplication.primaryScreen().availableGeometry()
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

        # HEADER (FIJO)
        self.header_layout = QVBoxLayout()

        self.header_layout.addWidget(
            self.title_label,
            alignment=Qt.AlignTop
        )

        self.main_layout.addLayout(self.header_layout)

# ------------------------------------------------------------------------------------------------------------------- #
        # Content layout
# ------------------------------------------------------------------------------------------------------------------- #

        self.content_layout = QVBoxLayout()

        self.main_layout.addLayout(self.content_layout, stretch=1)

# ------------------------------------------------------------------------------------------------------------------- #
        # Bottom navigation
# ------------------------------------------------------------------------------------------------------------------- #

        self.bottom_layout = QHBoxLayout()
        self.back_button = QPushButton("◀◀")
        self.back_button.setFixedSize(120, 35)
        self.back_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
            }
        """)

        self.back_button.clicked.connect(
            self.go_to_previous_step
        )

        self.next_button = QPushButton("▶▶")
        self.next_button.setEnabled(False)
        self.next_button.setFixedSize(120, 35)
        self.next_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
            }
        """)

        self.next_button.clicked.connect(
            self.go_to_next_step
        )

        self.bottom_layout.addWidget(
            self.back_button,
            alignment=Qt.AlignLeft
        )

        self.bottom_layout.addStretch(1)

        self.bottom_layout.addWidget(
            self.next_button,
            alignment=Qt.AlignLeft
        )

        self.bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.bottom_layout.addStretch()

        self.main_layout.addLayout(self.bottom_layout)

# ------------------------------------------------------------------------------------------------------------------- #
        # First screen
# ------------------------------------------------------------------------------------------------------------------- #

        build_introduction_screen(self)

# ------------------------------------------------------------------------------------------------------------------- #

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