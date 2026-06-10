from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from pathlib import Path

# Import get_settings 

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

# ------------------------------------------------------------------------------------------------------------------ #

def update_sweep_info_label(self, parent = None):
    """Update the sweep information label with current configuration."""
    try:
        start_val = self.start_freq_hz
        stop_val  = self.stop_freq_hz

        logging.info(f"[update_sweep_info_label] start_val={start_val} Hz")
        logging.info(f"[update_sweep_info_label] stop_val={stop_val} Hz")

        start_unit = self.start_unit
        stop_unit = self.stop_unit

        logging.info(f"[update_sweep_info_label] start_val={start_val}, stop_val={stop_val}")
        logging.info(f"[update_sweep_info_label] start_unit={start_unit}, stop_unit={stop_unit}")

        # Convert to the stored unit, stripping trailing zeros so the label
        # shows exactly what the user typed in sweep options (e.g. "1.5 GHz"
        # instead of "1.500 GHz", "1500 MHz" instead of "1500.000 MHz").
        _unit_divisors = {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
        _unit_labels   = {"hz": "Hz", "khz": "kHz", "mhz": "MHz", "ghz": "GHz"}

        start_div = _unit_divisors.get(start_unit.lower(), 1)
        start_lbl = _unit_labels.get(start_unit.lower(), start_unit)
        freq_start_str = f"{start_val / start_div:g} {start_lbl}"

        stop_div = _unit_divisors.get(stop_unit.lower(), 1)
        stop_lbl = _unit_labels.get(stop_unit.lower(), stop_unit)
        freq_stop_str = f"{stop_val / stop_div:g} {stop_lbl}"

        info_text = parent.measurement_ui_sweep_info.format(start_freq=freq_start_str, stop_freq=freq_stop_str, points=self.segments)
        if (parent != None):
            parent.sweep_info_label.setText(info_text)
        else:
            self.sweep_info_label.setText(info_text)
        logging.info(f"[graphics_window.update_sweep_info_label] Updated info: {info_text}")
    except Exception as e:
        logging.error(f"[graphics_window.update_sweep_info_label] Error updating label: {e}")

def get_freq_display_unit(self):
    """
    Return (divisor, unit_str) for frequency axis display.
    Reads directly from the sweep INI so it always reflects the latest config.
    Rules: both GHz → GHz/1e9 | both kHz → kHz/1e3 | otherwise → MHz/1e6.
    """
    try:
        settings = get_settings(
            "INI/dut_measurement/sweep_config/sweep_config.ini",
            "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini",
            Path(__file__).resolve()
        )
        s = settings.value("Frequency/StartUnit", "MHz").lower()
        e = settings.value("Frequency/StopUnit",  "MHz").lower()
    except Exception:
        s = getattr(self, 'start_unit', 'MHz').lower()
        e = getattr(self, 'stop_unit',  'MHz').lower()

    if s == 'ghz' and e == 'ghz':
        return 1e9, 'GHz'
    if s == 'khz' and e == 'khz':
        return 1e3, 'kHz'
    return 1e6, 'MHz'

def load_sweep_configuration(self, parent=None):
    try:
        settings = get_settings(
            "INI/dut_measurement/sweep_config/sweep_config.ini",
            "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini", 
            Path(__file__).resolve()        
        )

        default_start_hz = 50e3
        default_stop_hz  = 1.5e9
        default_segments = 101
        
        start_freq_val = settings.value("Frequency/StartFreqHz", default_start_hz)
        stop_freq_val  = settings.value("Frequency/StopFreqHz",  default_stop_hz)
        segments_val   = settings.value("Frequency/Segments",    default_segments)
        start_unit     = settings.value("Frequency/StartUnit",   "kHz")
        stop_unit      = settings.value("Frequency/StopUnit",    "GHz")

        settings.sync()

        try:
            start_freq_hz = int(float(str(start_freq_val)))
            stop_freq_hz  = int(float(str(stop_freq_val)))
            segments      = int(str(segments_val))
        except (ValueError, TypeError) as e:
            logging.error(f"[load_sweep_configuration] Error parsing values: {e}")
            start_freq_hz = int(default_start_hz)
            stop_freq_hz  = int(default_stop_hz)
            segments      = default_segments

        # ← el fix: escribir siempre en el target correcto
        target = parent if parent is not None else self

        target.start_freq_hz = start_freq_hz
        target.stop_freq_hz  = stop_freq_hz
        target.segments      = segments
        target.start_unit    = start_unit
        target.stop_unit     = stop_unit

        logging.info(f"[load_sweep_configuration] Loaded into {'parent' if parent else 'self'}: "
                     f"{start_freq_hz/1e6:.3f} MHz - {stop_freq_hz/1e6:.3f} MHz, {segments} pts")

        update_sweep_info_label(target, parent)

    except Exception as e:
        logging.error(f"[load_sweep_configuration] Error: {e}")
        target = parent if parent is not None else self
        target.start_freq_hz = 50000
        target.stop_freq_hz  = int(1.5e9)
        target.segments = 101


