from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys
from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt

from pathlib import Path

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

def show_frequency_difference_dialog(self):

    # --- Función auxiliar para formatear frecuencia ---
    def format_frequency_diff(freq_hz):
        """Return a string with appropriate unit (KHz, MHz, GHz) for frequency difference."""
        if 1e3 <= abs(freq_hz) < 1e6:
            return f"{freq_hz / 1e3:.3f} KHz"
        elif 1e6 <= abs(freq_hz) < 1e9:
            return f"{freq_hz / 1e6:.3f} MHz"
        else:
            return f"{freq_hz / 1e9:.3f} GHz"

    # --- Path to config.ini ---
    # Load configuration for graphics settings and visualization parameters
    settings = get_settings(
        "INI/dut_measurement/graphics_config/graphics_config.ini",
        "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
        Path(__file__).resolve()
    )

    # --- Read cursor indices ---
    cursor_1_1_index = int(settings.value("Cursor_1_1/index", 0))
    cursor_1_2_index = int(settings.value("Cursor_1_2/index", 0))
    cursor_2_1_index = int(settings.value("Cursor_2_1/index", 0))
    cursor_2_2_index = int(settings.value("Cursor_2_2/index", 0))

    # --- LEFT PANEL VALUES ---
    left_marker1_vals = self._update_cursor_orig(index=cursor_1_1_index, from_slider=True, return_values=True)
    left_marker2_vals = self._update_cursor_2_orig(index=cursor_2_1_index, from_slider=True, return_values=True)
    left_diff = {key: left_marker2_vals[key] - left_marker1_vals[key] for key in ["freq", "mag", "phase"]}

    # --- RIGHT PANEL VALUES ---
    right_marker1_vals = self._update_cursor_right_orig(index=cursor_1_2_index, from_slider=True, return_values=True)
    right_marker2_vals = self._update_cursor_2_right_orig(index=cursor_2_2_index, from_slider=True, return_values=True)
    right_diff = {key: right_marker2_vals[key] - right_marker1_vals[key] for key in ["freq", "mag", "phase"]}

    # --- Determine which panels to show ---
    show_left = (self.show_graphic1_marker1 and self.show_graphic1_marker2)
    show_right = (self.show_graphic2_marker1 and self.show_graphic2_marker2)

    # --- CREATE DIALOG ---
    dialog = QDialog(self)
    dialog.setWindowTitle(self.measurement_ui_marker_diff_window_title)
    dialog.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

    layout = QHBoxLayout()

    # --- Adjust size based on panels shown ---
    if show_left and show_right:
        dialog.setFixedSize(500, 120)
    else:  # only one panel
        dialog.setFixedSize(260, 120)

    # --- LEFT PANEL DISPLAY ---
    diff_labels = {
        "freq": self.measurement_ui_marker_diff_freq_label,
        "mag": self.measurement_ui_marker_diff_mag_label,
        "phase": self.measurement_ui_marker_diff_phase_label,
    }

    if show_left:
        left_layout = QVBoxLayout()
        left_title = QLabel(self.measurement_ui_marker_diff_left_title)
        left_title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(left_title)
        for key in ["freq", "mag", "phase"]:
            row = QHBoxLayout()
            row.addWidget(QLabel(diff_labels[key]))
            if key == "freq":
                text = format_frequency_diff(left_diff[key])
            else:
                text = f"{left_diff[key]:.3f}"
            row.addWidget(QLabel(text))
            left_layout.addLayout(row)
        layout.addLayout(left_layout)

    # --- RIGHT PANEL DISPLAY ---
    if show_right:
        right_layout = QVBoxLayout()
        right_title = QLabel(self.measurement_ui_marker_diff_right_title)
        right_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(right_title)
        for key in ["freq", "mag", "phase"]:
            row = QHBoxLayout()
            row.addWidget(QLabel(diff_labels[key]))
            if key == "freq":
                text = format_frequency_diff(right_diff[key])
            else:
                text = f"{right_diff[key]:.3f}"
            row.addWidget(QLabel(text))
            right_layout.addLayout(row)
        layout.addLayout(right_layout)

    # --- Set layout and show ---
    dialog.setLayout(layout)
    dialog.exec()
