import numpy as np
import logging


def update_panel_labels(self, s_left, s_right, graph_left, graph_right, unit_left, unit_right, idx_left, idx_right):
    try:
        if self.freqs is None:
            return

        freqs = self.freqs

        if hasattr(self, "labels_left") and self.labels_left:
            if idx_left < len(freqs) and idx_left < len(s_left):
                val = s_left[idx_left]
                x = freqs[idx_left] / 1e6
                mag_linear = np.abs(val)
                phase = np.angle(val) * 180 / np.pi
                self.labels_left["freq"].setText(f"{x:.6f} MHz")
                self.labels_left["val"].setText(f"{self.left_s_param}: {val.real:.3f} + j{val.imag:.3f}")
                self.labels_left["mag"].setText(f"|{self.left_s_param}|: {mag_linear:.3f}")
                self.labels_left["phase"].setText(f"∠{self.left_s_param}: {phase:.3f}°")

        if hasattr(self, "labels_left_2") and self.labels_left_2:
            if idx_left < len(freqs) and idx_left < len(s_left):
                val = s_left[idx_left]
                x = freqs[idx_left] / 1e6
                mag_linear = np.abs(val)
                phase = np.angle(val) * 180 / np.pi
                self.labels_left_2["freq"].setText(f"{x:.6f} MHz")
                self.labels_left_2["val"].setText(f"{self.left_s_param}: {val.real:.3f} + j{val.imag:.3f}")
                self.labels_left_2["mag"].setText(f"|{self.left_s_param}|: {mag_linear:.3f}")
                self.labels_left_2["phase"].setText(f"∠{self.left_s_param}: {phase:.3f}°")

        if hasattr(self, "labels_right") and self.labels_right:
            if idx_right < len(freqs) and idx_right < len(s_right):
                val = s_right[idx_right]
                x = freqs[idx_right] / 1e6
                mag_linear = np.abs(val)
                phase = np.angle(val) * 180 / np.pi
                self.labels_right["freq"].setText(f"{x:.6f} MHz")
                self.labels_right["val"].setText(f"{self.right_s_param}: {val.real:.3f} + j{val.imag:.3f}")
                self.labels_right["mag"].setText(f"|{self.right_s_param}|: {mag_linear:.3f}")
                self.labels_right["phase"].setText(f"∠{self.right_s_param}: {phase:.3f}°")

        if hasattr(self, "labels_right_2") and self.labels_right_2:
            if idx_right < len(freqs) and idx_right < len(s_right):
                val = s_right[idx_right]
                x = freqs[idx_right] / 1e6
                mag_linear = np.abs(val)
                phase = np.angle(val) * 180 / np.pi
                self.labels_right_2["freq"].setText(f"{x:.6f} MHz")
                self.labels_right_2["val"].setText(f"{self.right_s_param}: {val.real:.3f} + j{val.imag:.3f}")
                self.labels_right_2["mag"].setText(f"|{self.right_s_param}|: {mag_linear:.3f}")
                self.labels_right_2["phase"].setText(f"∠{self.right_s_param}: {phase:.3f}°")

    except Exception as e:
        logging.error(f"[update_panel_labels] {e}")