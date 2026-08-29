import numpy as np
import logging


def _fmt_freq_smart(hz):
    """Return (value_str, unit_str) for hz, using the most natural unit."""
    if hz >= 1e9:
        return f"{hz / 1e9:.2f}", "GHz"
    if hz >= 1e6:
        return f"{hz / 1e6:.2f}", "MHz"
    if hz >= 1e3:
        return f"{hz / 1e3:.2f}", "kHz"
    return f"{hz:.1f}", "Hz"


def update_panel_labels(self, s_left, s_right, graph_left, graph_right, unit_left, unit_right, idx_left, idx_right):
    try:
        if self.freqs is None:
            return

        # Guardar datos frescos en self para que update_cursor los use
        self._rt_s_left  = s_left
        self._rt_s_right = s_right
        self._rt_freqs   = self.freqs

        freqs = self.freqs

        n = len(freqs)
        idx_left  = min(max(0, idx_left),  n - 1)
        idx_right = min(max(0, idx_right), n - 1)

        def fill_labels(labels, s_data, idx, s_param):
            val        = s_data[idx]
            mag_linear = np.abs(val)
            phase      = np.angle(val) * 180 / np.pi
            freq_val, freq_unit = _fmt_freq_smart(freqs[idx])
            labels["freq"].blockSignals(True)
            labels["freq"].setText(freq_val)
            labels["freq"].blockSignals(False)
            if "unit" in labels:
                labels["unit"].setText(freq_unit)
            labels["val"].setText(f"{s_param}: {val.real:.3f} - j{abs(val.imag):.3f}" if val.imag < 0 else f"{s_param}: {val.real:.3f} + j{val.imag:.3f}")
            labels["mag"].setText(f"|{s_param}|: {mag_linear:.3f}")
            labels["phase"].setText(f"{self.measurement_ui_s_parameter_phase} {phase:.2f}°")

        if hasattr(self, "labels_left")   and self.labels_left   and idx_left  < len(s_left):
            fill_labels(self.labels_left,   s_left,  idx_left,  self.left_s_param)

        if hasattr(self, "labels_left_2") and self.labels_left_2 and idx_left  < len(s_left):
            fill_labels(self.labels_left_2, s_left,  idx_left,  self.left_s_param)

        if hasattr(self, "labels_right")  and self.labels_right  and idx_right < len(s_right):
            fill_labels(self.labels_right,  s_right, idx_right, self.right_s_param)

        if hasattr(self, "labels_right_2") and self.labels_right_2 and idx_right < len(s_right):
            fill_labels(self.labels_right_2, s_right, idx_right, self.right_s_param)

    except Exception as e:
        logging.error(f"[update_panel_labels] {e}")