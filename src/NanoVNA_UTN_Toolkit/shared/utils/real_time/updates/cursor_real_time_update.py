import numpy as np
import logging

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.sweep_window.sweep_utils.sweep_utils import get_freq_display_unit
except ImportError:
    def get_freq_display_unit(self):
        return 1e6, 'MHz'

def compute_y(val, graph_type, unit):

    if graph_type == "Magnitude":
        if unit == "dB":
            return 20 * np.log10(np.abs(val))
        elif unit == "Power ratio":
            return np.abs(val) ** 2
        else:
            return np.abs(val)

    elif graph_type == "Phase":
        return np.angle(val) * 180 / np.pi

    return np.abs(val)


def _get_y_from_line(line, idx):
    """Read y value at idx from a plotted line (avoids recomputing Phase with wrapping issues)."""
    try:
        ydata = line.get_ydata()
        if ydata is not None and len(ydata) > idx:
            return ydata[idx]
    except Exception:
        pass
    return None


def update_realtime_cursors(self, s_left, s_right, graph_left, graph_right, unit_left, unit_right):
    try:
        if self.freqs is None:
            return

        freqs = self.freqs
        freq_div, _ = get_freq_display_unit(self)
        n = len(freqs)

        def get_idx(slider_name):
            slider = getattr(self, slider_name, None)
            if slider is None:
                return 0
            # Si el rango del slider no coincide con el sweep actual, lo corregimos
            if slider.valmax != n - 1:
                slider.valmin = 0
                slider.valmax = n - 1
                slider.set_val(min(int(slider.val), n - 1))
            return min(max(0, int(slider.val)), n - 1)

        if len(s_left) != len(freqs):
            logging.error("DESYNC DATA")
            return

        # ================= LEFT =================
        if hasattr(self, "cursor_left") and self.cursor_left:
            idx = get_idx("slider_left")
            if graph_left == "Smith Diagram":
                self.cursor_left.set_data([np.real(s_left[idx])], [np.imag(s_left[idx])])
            else:
                x = freqs[idx] / freq_div
                if graph_left == "Phase":
                    y = _get_y_from_line(self.line_left, idx) or compute_y(s_left[idx], graph_left, unit_left)
                else:
                    y = compute_y(s_left[idx], graph_left, unit_left)
                self.cursor_left.set_data([x], [y])

        if hasattr(self, "cursor_left_2") and self.cursor_left_2:
            idx = get_idx("slider_left_2")
            if graph_left == "Smith Diagram":
                self.cursor_left_2.set_data([np.real(s_left[idx])], [np.imag(s_left[idx])])
            else:
                x = freqs[idx] / freq_div
                if graph_left == "Phase":
                    y = _get_y_from_line(self.line_left, idx) or compute_y(s_left[idx], graph_left, unit_left)
                else:
                    y = compute_y(s_left[idx], graph_left, unit_left)
                self.cursor_left_2.set_data([x], [y])

        # ================= RIGHT =================
        if hasattr(self, "cursor_right") and self.cursor_right:
            idx = get_idx("slider_right")
            if graph_right == "Smith Diagram":
                self.cursor_right.set_data([np.real(s_right[idx])], [np.imag(s_right[idx])])
            else:
                x = freqs[idx] / freq_div
                if graph_right == "Phase":
                    y = _get_y_from_line(self.line_right, idx) or compute_y(s_right[idx], graph_right, unit_right)
                else:
                    y = compute_y(s_right[idx], graph_right, unit_right)
                self.cursor_right.set_data([x], [y])

        if hasattr(self, "cursor_right_2") and self.cursor_right_2:
            idx = get_idx("slider_right_2")
            if graph_right == "Smith Diagram":
                self.cursor_right_2.set_data([np.real(s_right[idx])], [np.imag(s_right[idx])])
            else:
                x = freqs[idx] / freq_div
                if graph_right == "Phase":
                    y = _get_y_from_line(self.line_right, idx) or compute_y(s_right[idx], graph_right, unit_right)
                else:
                    y = compute_y(s_right[idx], graph_right, unit_right)
                self.cursor_right_2.set_data([x], [y])

        if hasattr(self, "canvas_left"):
            self.canvas_left.draw_idle()
        if hasattr(self, "canvas_right"):
            self.canvas_right.draw_idle()

    except Exception as e:
        logging.error(f"[realtime_cursor_update] {e}")