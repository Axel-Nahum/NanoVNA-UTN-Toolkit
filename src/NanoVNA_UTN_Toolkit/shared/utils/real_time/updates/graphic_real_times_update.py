"""
Utilities for real-time graphics updates in NanoVNA-UTN-Toolkit.
"""

import logging
import numpy as np
import sys

from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.auto_scale.auto_scale import read_auto_scale_data
from NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.cursor_real_time_update import update_realtime_cursors
from NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.panels_real_time_update import update_panel_labels
from NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.set_slider_val_silent import update_slider_range_silent

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

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.sweep_window.sweep_utils.sweep_utils import get_freq_display_unit
except ImportError:
    def get_freq_display_unit(self):
        return 1e6, 'MHz'

# ----------------------------------------------------------------------------------

def _update_smith_realtime(ax, freqs, s_data):
    """Update the Smith chart data trace in-place without redrawing the grid."""
    n = len(s_data)
    x = np.real(s_data)
    y = np.imag(s_data)
    updated = False
    for line_obj in ax.lines:
        xd = line_obj.get_xdata()
        if hasattr(xd, '__len__') and len(xd) == n:
            line_obj.set_data(x, y)
            updated = True
            break
    if not updated and len(ax.lines) > 0:
        # Fallback: update the last line added (the data trace)
        ax.lines[-1].set_data(x, y)

# ----------------------------------------------------------------------------------

def update_single_plot_realtime(self, line, ax, freqs, s_data, graph_type, unit, ax_type):

    if graph_type == "Smith Diagram":
        _update_smith_realtime(ax, freqs, s_data)
        return

    # Recover a stale/None line reference by finding the data trace in the axes
    if line is None:
        n = len(s_data)
        for l in ax.lines:
            xd = l.get_xdata()
            if hasattr(xd, '__len__') and len(xd) == n:
                line = l
                # Heal the stored reference so future calls are direct
                if ax_type == "left":
                    self.line_left = line
                elif ax_type == "right":
                    self.line_right = line
                break
        if line is None:
            return

    if graph_type == "Magnitude":
        if unit == "dB":
            y_data = 20 * np.log10(np.abs(s_data))
        elif unit == "Power ratio":
            y_data = np.abs(s_data) ** 2
        else:
            y_data = np.abs(s_data)
    elif graph_type == "Phase":
        # Unwrap then normalize to avoid ±180° oscillation
        y_data = np.degrees(np.unwrap(np.angle(s_data)))
        if np.mean(y_data) < -90:
            y_data += 360
    else:
        return

    freq_div, freq_unit = get_freq_display_unit(self)
    x_data = freqs / freq_div
    line.set_data(x_data, y_data)

    ax.set_xlabel(f'Frequency ({freq_unit})')

    freq_start = x_data[0]
    freq_end   = x_data[-1]
    margin_x   = (freq_end - freq_start) * 0.05 or 1
    ax.set_xlim(freq_start - margin_x, freq_end + margin_x)

    if ax_type == "left":
        if self.auto_scale_left:
            y_min, y_max = np.min(y_data), np.max(y_data)
            margin_y = (y_max - y_min) * 0.05 if y_max != y_min else 1
            ax.set_ylim(y_min - margin_y, y_max + margin_y)
        else:
            ax.set_ylim(self.ymin_left, self.ymax_left)
    elif ax_type == "right":
        if self.auto_scale_right:
            y_min, y_max = np.min(y_data), np.max(y_data)
            margin_y = (y_max - y_min) * 0.05 if y_max != y_min else 1
            ax.set_ylim(y_min - margin_y, y_max + margin_y)
        else:
            ax.set_ylim(self.ymin_right, self.ymax_right)

    ax.relim()
    ax.autoscale_view()

# ----------------------------------------------------------------------------------

def update_plots_realtime(self):

    try:
        if not hasattr(self.ax_left, "lines") or len(self.ax_left.lines) == 0:
            return
        if not hasattr(self.ax_right, "lines") or len(self.ax_right.lines) == 0:
            return

        if self.freqs is None or self.s11 is None or self.s21 is None:
            return

        config          = load_graph_configuration()
        graph_type_tab1 = config['graph_type_tab1']
        s_param_tab1    = config['s_param_tab1']
        graph_type_tab2 = config['graph_type_tab2']
        s_param_tab2    = config['s_param_tab2']

        # line references may be None/stale (e.g. right after a Smith→Magnitude switch);
        # update_single_plot_realtime recovers them via ax.lines search.

        data_config = read_auto_scale_data(self)
        self.auto_scale_left  = data_config[0]
        self.auto_scale_right = data_config[1]
        self.ymin_left        = data_config[2]
        self.ymax_left        = data_config[3]
        self.ymin_right       = data_config[4]
        self.ymax_right       = data_config[5]

        def _pick(s_param, graph_type):
            # Smith Diagram needs unfiltered complex data — Kalman distorts the curve
            raw_s11 = getattr(self, 's11_raw', self.s11)
            raw_s21 = getattr(self, 's21_raw', self.s21)
            if graph_type == "Smith Diagram":
                return raw_s11 if s_param == "S11" else raw_s21
            return self.s11 if s_param == "S11" else self.s21

        s_data_left  = _pick(s_param_tab1, graph_type_tab1)
        s_data_right = _pick(s_param_tab2, graph_type_tab2)

        if hasattr(self, "update_left_data_2") and self.update_left_data_2:
            try:
                self.update_left_data_2(s_data_left, self.freqs)
            except Exception as e:
                logging.error(f"[update_plots_realtime] update_left_data_2: {e}")

        update_single_plot_realtime(
            self, self.line_left, self.ax_left,
            self.freqs, s_data_left,
            graph_type_tab1, get_graph_unit(self, 1), "left"
        )
        update_single_plot_realtime(
            self, self.line_right, self.ax_right,
            self.freqs, s_data_right,
            graph_type_tab2, get_graph_unit(self, 2), "right"
        )

        n = len(self.freqs)

        def get_idx(slider_name):
            slider = getattr(self, slider_name, None)
            if slider is None:
                return 0
            if hasattr(slider, "valmax") and slider.valmax != n - 1:
                update_slider_range_silent(slider, n - 1)
            return min(max(0, int(slider.val)), n - 1)

        idx_left  = get_idx("slider_left")
        idx_right = get_idx("slider_right")

        update_realtime_cursors(
            self, s_data_left, s_data_right,
            graph_type_tab1, graph_type_tab2,
            get_graph_unit(self, 1), get_graph_unit(self, 2)
        )

        update_panel_labels(
            self, s_data_left, s_data_right,
            graph_type_tab1, graph_type_tab2,
            get_graph_unit(self, 1), get_graph_unit(self, 2),
            idx_left, idx_right
        )

        self.canvas_left.draw_idle()
        self.canvas_right.draw_idle()

    except Exception as e:
        logging.error(f"[update_plots_realtime] {e}")
