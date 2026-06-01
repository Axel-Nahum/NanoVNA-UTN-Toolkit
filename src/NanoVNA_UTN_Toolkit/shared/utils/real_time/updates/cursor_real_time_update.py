import numpy as np
import logging

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


def update_realtime_cursors(self, s_left, s_right, graph_left, graph_right, unit_left, unit_right):

    try:
        if self.freqs is None:
            return

        freqs = self.freqs

        # ================= LEFT PANEL =================
        if hasattr(self, "cursor_left") and self.cursor_left:
            idx = int(getattr(self, "slider_left").val)

            if idx < len(freqs) and idx < len(s_left):
                x = freqs[idx] / 1e6
                y = compute_y(s_left[idx], graph_left, unit_left)

                self.cursor_left.set_data([x], [y])

        if hasattr(self, "cursor_left_2") and self.cursor_left_2:
            idx = int(getattr(self, "slider_left_2").val)

            if idx < len(freqs) and idx < len(s_left):
                x = freqs[idx] / 1e6
                y = compute_y(s_left[idx], graph_left, unit_left)

                self.cursor_left_2.set_data([x], [y])

        # ================= RIGHT PANEL =================
        if hasattr(self, "cursor_right") and self.cursor_right:
            idx = int(getattr(self, "slider_right").val)

            if idx < len(freqs) and idx < len(s_right):
                x = freqs[idx] / 1e6
                y = compute_y(s_right[idx], graph_right, unit_right)

                self.cursor_right.set_data([x], [y])

        if hasattr(self, "cursor_right_2") and self.cursor_right_2:
            idx = int(getattr(self, "slider_right_2").val)

            if idx < len(freqs) and idx < len(s_right):
                x = freqs[idx] / 1e6
                y = compute_y(s_right[idx], graph_right, unit_right)

                self.cursor_right_2.set_data([x], [y])

        # redraw
        if hasattr(self, "canvas_left"):
            self.canvas_left.draw_idle()

        if hasattr(self, "canvas_right"):
            self.canvas_right.draw_idle()

    except Exception as e:
        logging.error(f"[realtime_cursor_update] {e}")