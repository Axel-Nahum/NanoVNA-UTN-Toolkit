"""
Utilities for real-time graphics updates in NanoVNA-UTN-Toolkit.
"""

import logging
import numpy as np
import sys

from pyparsing import line

from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.auto_scale.auto_scale import read_auto_scale_data
from NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.cursor_real_time_update import update_realtime_cursors
from src.NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.panels_real_time_update import update_panel_labels

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.db_unit.db_unit import get_graph_unit
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.load_graph_config.load_graph_config import load_graph_configuration
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    sys.exit(1)

# ----------------------------------------------------------------------------------

def update_single_plot_realtime(
    self,
    line,
    ax,
    freqs,
    s_data,
    graph_type,
    unit,
    ax_type
):

    # -----------------------------
    # DATA TRANSFORM
    # -----------------------------
    if graph_type == "Magnitude":

        if unit == "dB":
            y_data = 20 * np.log10(np.abs(s_data))
        elif unit == "Power ratio":
            y_data = np.abs(s_data) ** 2
        else:
            y_data = np.abs(s_data)

    elif graph_type == "Phase":
        y_data = np.angle(s_data) * 180 / np.pi

    else:
        return

    x_data = freqs / 1e6

    # -----------------------------
    # UPDATE LINE ONLY
    # -----------------------------

    line.set_data(x_data, y_data)

    # -----------------------------
    # AXIS SCALING CONTROLLED (NO autoscale_view)
    # -----------------------------
    if ax_type == "left":

        if self.auto_scale_left:
            y_min = np.min(y_data)
            y_max = np.max(y_data)
            margin = (y_max - y_min) * 0.05 if y_max != y_min else 1

            ax.set_ylim(y_min - margin, y_max + margin)
        else:
            ax.set_ylim(self.ymin_left, self.ymax_left)

    elif ax_type == "right":

        if self.auto_scale_right:
            y_min = np.min(y_data)
            y_max = np.max(y_data)
            margin = (y_max - y_min) * 0.05 if y_max != y_min else 1

            ax.set_ylim(y_min - margin, y_max + margin)
        else:
            ax.set_ylim(self.ymin_right, self.ymax_right)

    # ----------------------------
    # X LIM FIX (igual que recreate)
    # ----------------------------

    freq_start = x_data[0]
    freq_end = x_data[-1]
    freq_range = freq_end - freq_start
    margin = freq_range * 0.05

    ax.set_xlim(freq_start - margin, freq_end + margin)

    # ----------------------------
    # Y autoscale clásico
    # ----------------------------
    ax.relim()
    ax.autoscale_view()

# ----------------------------------------------------------------------------------

def update_plots_realtime(self):

    try:
        # -----------------------------
        # GET LINES (SAFE)
        # -----------------------------
        if not hasattr(self.ax_left, "lines") or len(self.ax_left.lines) == 0:
            return
        if not hasattr(self.ax_right, "lines") or len(self.ax_right.lines) == 0:
            return

        self.line_left = self.ax_left.lines[0]
        self.line_right = self.ax_right.lines[0]

        # -----------------------------
        # DATA CHECK
        # -----------------------------
        if self.freqs is None or self.s11 is None or self.s21 is None:
            return

        # -----------------------------
        # AUTO SCALE CONFIG (ONCE PER UPDATE, NOT PER LINE)
        # -----------------------------
        data_config = read_auto_scale_data(self)

        self.auto_scale_left = data_config[0]
        self.auto_scale_right = data_config[1]

        self.ymin_left = data_config[2]
        self.ymax_left = data_config[3]
        self.ymin_right = data_config[4]
        self.ymax_right = data_config[5]

        # -----------------------------
        # GRAPH CONFIG
        # -----------------------------
        config = load_graph_configuration()

        graph_type_tab1 = config['graph_type_tab1']
        s_param_tab1 = config['s_param_tab1']

        graph_type_tab2 = config['graph_type_tab2']
        s_param_tab2 = config['s_param_tab2']

        # -----------------------------
        # DATA SELECTION
        # -----------------------------
        s_data_left = self.s11 if s_param_tab1 == "S11" else self.s21
        s_data_right = self.s11 if s_param_tab2 == "S11" else self.s21

        # -----------------------------
        # UPDATE LEFT
        # -----------------------------
        update_single_plot_realtime(
            self,
            self.line_left,
            self.ax_left,
            self.freqs,
            s_data_left,
            graph_type_tab1,
            get_graph_unit(self, 1),
            "left"
        )

        # -----------------------------
        # UPDATE RIGHT
        # -----------------------------
        update_single_plot_realtime(
            self,
            self.line_right,
            self.ax_right,
            self.freqs,
            s_data_right,
            graph_type_tab2,
            get_graph_unit(self, 2),
            "right"
        )

        # -----------------------------
        # NO RESET HERE (IMPORTANT)
        # -----------------------------
        
        update_realtime_cursors(self, s_data_left, s_data_right, graph_type_tab1, graph_type_tab2, get_graph_unit(self, 1), get_graph_unit(self, 2))

        update_panel_labels(self, s_data_left, s_data_right, graph_type_tab1, graph_type_tab2, get_graph_unit(self, 1), get_graph_unit(self, 2), int(getattr(self, "slider_left").val), int(getattr(self, "slider_right").val))

        # -----------------------------
        # DRAW LIGHTWEIGHT
        # -----------------------------
        self.canvas_left.draw_idle()
        self.canvas_right.draw_idle()

    except Exception as e:
        logging.error(f"[update_plots_realtime] {e}")