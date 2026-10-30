from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

import numpy as np

from shiboken6 import isValid

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

get_sweep_start_frequency, get_sweep_stop_frequency, get_sweep_steps = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.wizard_cal_windows.wizard_cal_utils.sweep_cal", "get_sweep_start_frequency", "get_sweep_stop_frequency", "get_sweep_steps")

# ------------------------------------------------------------------------------------------------------------------ #

# --- Step definitions (each step is unique) ---------------------------------
def step_OSM_OPEN(self):
    label = QLabel("Step 1: OPEN (OSM)")
    label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    return label

def step_OSM_SHORT(self):
    label = QLabel("Step 2: SHORT (OSM)")
    label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    return label

def step_OSM_MATCH(self):
    label = QLabel("Step 3: MATCH (OSM)")
    label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    return label

def step_Normalization(self):
    label = QLabel("Step 1: Thru Normalization")
    label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    return label

def step_OpenShortNormalization(self):
    label = QLabel("Step 1: Open or Short (Open/Short Normalization)")
    label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    return label

def step_OnePortN_OPEN(self):
    label = QLabel("Step 1: OPEN (1-Port+N)")
    label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    return label

def step_OnePortN_SHORT(self):
    label = QLabel("Step 2: SHORT (1-Port+N)")
    label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    return label

def step_OnePortN_MATCH(self):
    label = QLabel("Step 3: MATCH (1-Port+N)")
    label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    return label

def step_OnePortN_THRU(self):
    label = QLabel("Step 4: THRU (1-Port+N)")
    label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 8px;")
    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    return label

# --- Get steps for current method -----------------------------------------
def get_steps_for_method(self):
    """Return a list of unique step methods for the selected method."""
    if self.selected_method == "OSM (Open - Short - Match)":
        return [
            step_OSM_OPEN(self),
            step_OSM_SHORT(self),
            step_OSM_MATCH(self)
        ]
    elif self.selected_method == "Thru Normalization":
        return [step_Normalization(self)]
    elif self.selected_method == "Open/Short Normalization":
        return [step_OpenShortNormalization(self)]
    elif self.selected_method == "1-Port+N":
        return [
            step_OnePortN_OPEN(self),
            step_OnePortN_SHORT(self),
            step_OnePortN_MATCH(self),
            step_OnePortN_THRU(self)
        ]
    elif self.selected_method == "Enhanced-Response":
        return [
            lambda: QLabel("Step 1: OPEN (Enhanced-Response)", alignment=Qt.AlignRight | Qt.AlignTop),
            lambda: QLabel("Step 2: SHORT (Enhanced-Response)", alignment=Qt.AlignRight | Qt.AlignTop),
            lambda: QLabel("Step 3: MATCH (Enhanced-Response)", alignment=Qt.AlignRight | Qt.AlignTop),
            lambda: QLabel("Step 4: THRU (Enhanced-Response)", alignment=Qt.AlignRight | Qt.AlignTop)
        ]
    elif self.selected_method == "1-Path 2-Port":
        return [
            lambda: QLabel("Step 1: OPEN (1-Path 2-Port)", alignment=Qt.AlignRight | Qt.AlignTop),
            lambda: QLabel("Step 2: SHORT (1-Path 2-Port)", alignment=Qt.AlignRight | Qt.AlignTop),
            lambda: QLabel("Step 3: MATCH (1-Path 2-Port)", alignment=Qt.AlignRight | Qt.AlignTop),
            lambda: QLabel("Step 4: THRU (1-Path 2-Port)", alignment=Qt.AlignRight | Qt.AlignTop)
        ]
    else:
        return []

def show_current_step_measurement(self, step):
    """Show only the measurement for the current step on Smith chart."""
    # Use consolidated Smith chart creation
    from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import SmithChartManager
    from NanoVNA_UTN_Toolkit.utils.magnitude_chat_utils import MagnitudeChartManager
    
    if not hasattr(self, 'current_ax'):
        return
        
    try:
        # Determine which standard corresponds to current step
        step_name = None
        if self.selected_method == "OSM (Open - Short - Match)":
            if step == 1:
                step_name = "open"
            elif step == 2:
                step_name = "short"
            elif step == 3:
                step_name = "match"
        elif self.selected_method == "Thru Normalization":
            if step == 1:
                step_name = "thru"
        elif self.selected_method == "Open/Short Normalization":
            if step == 1:
                step_name = "open"

        # Show only the measurement for the current step if it exists
        if self.selected_method == "OSM (Open - Short - Match)" and step_name in ["open", "short", "match"]:
            if self.osm_calibration and self.osm_calibration.is_standard_measured(step_name):
                measurement = self.osm_calibration.get_measurement(step_name)
                if measurement:
                    freqs, s11 = measurement
                    manager = SmithChartManager()
                    manager.update_wizard_measurement(
                        ax=self.current_ax,
                        freqs=freqs,
                        s11_data=s11,
                        standard_name=step_name,
                        canvas=self.current_canvas
                    )
                    return

        # Draw an empty base Smith chart to reset the canvas.
        # Skip for Enhanced-Response / 1-Port+N at step 4 (THRU): the THRU step
        # setup clears right_layout and replaces the Smith chart with a magnitude
        # chart, leaving current_ax/current_canvas pointing at an orphaned widget
        # that is no longer in the widget tree.  Attempting to draw on it can raise
        # an exception that would abort this function before the magnitude-chart
        # restoration block below gets to run.
        _enh_thru = self.selected_method in ("Enhanced-Response", "1-Port+N") and step == 4
        if not _enh_thru:
            self.current_ax.clear()
            manager = SmithChartManager()
            base_network = manager.builder.create_empty_network(
                get_sweep_start_frequency(self),
                get_sweep_stop_frequency(self),
                get_sweep_steps(self)
            )
            manager.builder.ax = self.current_ax
            manager.builder.draw_base_smith_chart(base_network)
            self.current_canvas.draw()

        if self.selected_method == "Thru Normalization" and step_name == "thru":
            if self.thru_calibration.is_standard_measured(step_name):
                measurement = self.thru_calibration.get_measurement()
                if measurement:
                    freqs, s11 = measurement

                    # Use consolidated Magnitude plot functionality for single measurement
                    manager = MagnitudeChartManager()  # New manager for magnitude
                    manager.update_wizard_measurement(
                        ax=self.current_ax,
                        freqs=freqs,
                        s21_data=np.abs(s11),
                        standard_name=step_name,
                        canvas=self.current_canvas_magnitude
                    )
            else:
                # Clear and show empty magnitude plot if no measurement exists
                self.current_ax.clear()
                manager = MagnitudePlotManager()
                freqs_base = np.linspace(
                    get_sweep_start_frequency(self),
                    get_sweep_stop_frequency(self),
                    get_sweep_steps(self)
                )
                # Create empty y-data for magnitude plot
                s_data_empty = np.zeros_like(freqs_base)

                manager.builder.ax = self.current_ax
                manager.builder.plot_base_magnitude(freqs_base, s_data_empty)  # Replace Smith chart base with magnitude
                self.current_canvas.draw()

        if self.selected_method == "Open/Short Normalization" and step_name in ("open", "short"):
            if hasattr(self, 'os_calibration') and self.os_calibration and self.os_calibration.is_standard_measured(step_name):
                measurement = self.os_calibration.get_measurement()
                if measurement:
                    freqs, s11 = measurement
                    manager = SmithChartManager()
                    manager.update_wizard_measurement(
                        ax=self.current_ax,
                        freqs=freqs,
                        s11_data=s11,
                        standard_name=step_name,
                        canvas=self.current_canvas
                    )

        if self.selected_method in ("Enhanced-Response", "1-Port+N"):
            if step <= 3 and self.osm_calibration:
                enh_step_name = ["open", "short", "match"][step - 1]
                if self.osm_calibration.is_standard_measured(enh_step_name):
                    measurement = self.osm_calibration.get_measurement(enh_step_name)
                    if measurement:
                        freqs, s11 = measurement
                        manager = SmithChartManager()
                        manager.update_wizard_measurement(
                            ax=self.current_ax,
                            freqs=freqs,
                            s11_data=s11,
                            standard_name=enh_step_name,
                            canvas=self.current_canvas
                        )
            elif step == 4 and self.thru_calibration:
                if self.thru_calibration.is_standard_measured("thru"):
                    measurement = self.thru_calibration.get_measurement()
                    if measurement and hasattr(self, 'current_ax_magnitude'):
                        freqs, s11 = measurement
                        manager = MagnitudeChartManager()
                        manager.update_wizard_measurement(
                            ax=self.current_ax_magnitude,
                            freqs=freqs,
                            s21_data=np.abs(s11),
                            standard_name="thru",
                            canvas=self.current_canvas_magnitude
                        )

    except Exception as e:
        logging.error(f"[CalibrationWizard] Error showing current step measurement: {e}")

# --- layout clearing helpers ------------------------------------------------
def clear_layout(self, layout):
    """Recursively remove widgets and nested layouts from a layout."""
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        child_layout = item.layout()
        if widget:
            widget.setParent(None)
            widget.deleteLater()
        elif child_layout:
            # Recursively clear nested layout
            clear_layout(self, child_layout)

def clear_content(self):
    """Clear everything inside content_layout (handles nested layouts)."""
    clear_layout(self, self.content_layout)

def clear_main_content(self):
    """Clear everything inside content_layout and remove old panels if exist."""
    clear_content(self)  # limpia content_layout
    # elimina widgets antiguos si existen
    if hasattr(self, "left_panel_widget") and self.left_panel_widget:
        if isValid(self.left_panel_widget):
            self.left_panel_widget.setParent(None)
        self.left_panel_widget = None

    if hasattr(self, "right_panel_widget") and self.right_panel_widget:
        if isValid(self.right_panel_widget):
            self.right_panel_widget.setParent(None)
        self.right_panel_widget = None