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

        # Convert to proper units
        if start_unit.lower() == "khz":
            freq_start_str = f"{start_val/1e3:.1f} kHz"
        elif start_unit.lower() == "mhz":
            freq_start_str = f"{start_val/1e6:.3f} MHz"
        elif start_unit.lower() == "ghz":
            freq_start_str = f"{start_val/1e9:.3f} GHz"
        else:
            freq_start_str = f"{start_val} Hz"

        if stop_unit.lower() == "khz":
            freq_stop_str = f"{stop_val/1e3:.1f} kHz"
        elif stop_unit.lower() == "mhz":
            freq_stop_str = f"{stop_val/1e6:.3f} MHz"
        elif stop_unit.lower() == "ghz":
            freq_stop_str = f"{stop_val/1e9:.3f} GHz"
        else:
            freq_stop_str = f"{stop_val} Hz"

        info_text = parent.measurement_ui_sweep_info.format(start_freq=freq_start_str, stop_freq=freq_stop_str, points=self.segments)
        if (parent != None):
            parent.sweep_info_label.setText(info_text)
        else:
            self.sweep_info_label.setText(info_text)
        logging.info(f"[graphics_window.update_sweep_info_label] Updated info: {info_text}")
    except Exception as e:
        logging.error(f"[graphics_window.update_sweep_info_label] Error updating label: {e}")

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


