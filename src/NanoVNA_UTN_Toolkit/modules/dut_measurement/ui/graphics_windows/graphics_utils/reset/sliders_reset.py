"""
Slider resets around a sweep / reconnection (GUI thread).

EN: Programmatic slider moves go through the silent setter so they do not fire
``on_changed`` (each callback updated a cursor, rewrote the info panel and
queued a redraw, four times, right before everything was cleared anyway).

ES: Los movimientos programáticos de slider usan el setter silencioso para no
disparar ``on_changed`` cuatro veces justo antes de limpiar todo.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging

_clear_all_marker_fields = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.panels_utils", "_clear_all_marker_fields")

set_slider_val_silent = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.set_slider_val_silent",
    "set_slider_val_silent"
)

_SLIDERS = ("slider_left", "slider_left_2", "slider_right", "slider_right_2")
_CURSOR_UPDATERS = ("update_cursor", "update_cursor_2", "update_right_cursor", "update_right_cursor_2")


def _sliders_to_zero_silent(self):
    for name in _SLIDERS:
        slider = getattr(self, name, None)
        if slider is not None:
            set_slider_val_silent(slider, 0)


def _reset_sliders_after_reconnect(self):
    """Reset sliders and show cursor information after successful device reconnection."""
    try:
        logging.info("[graphics_window._reset_sliders_after_reconnect] Resetting sliders after successful reconnection")

        # Only reset if we have data available
        if not (hasattr(self, 'freqs') and self.freqs is not None and len(self.freqs) > 0):
            logging.info("[graphics_window._reset_sliders_after_reconnect] No sweep data available, skipping reset")
            return

        _sliders_to_zero_silent(self)

        # Cursor information for the minimum position (each call queues a draw_idle)
        for name in _CURSOR_UPDATERS:
            fn = getattr(self, name, None)
            if not callable(fn):
                continue
            try:
                fn(0)
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_after_reconnect] {name}(0) failed: {e}")

        # One coalesced redraw per panel on the next event-loop pass
        if getattr(self, 'canvas_left', None):
            self.canvas_left.draw_idle()
        if getattr(self, 'canvas_right', None):
            self.canvas_right.draw_idle()

        logging.info("[graphics_window._reset_sliders_after_reconnect] Sliders reset and info updated after reconnection")

    except Exception as e:
        logging.error(f"[graphics_window._reset_sliders_after_reconnect] Error resetting sliders after reconnection: {e}")


def _reset_sliders_before_sweep(self):
    """Reset sliders and CLEAR all cursor information before starting a sweep."""
    try:
        logging.info("[graphics_window._reset_sliders_before_sweep] Resetting sliders and clearing info before sweep starts")

        _sliders_to_zero_silent(self)

        # CLEAR all marker information (DO NOT update cursor info - just clear it)
        _clear_all_marker_fields(self)

        logging.info("[graphics_window._reset_sliders_before_sweep] Sliders reset and info cleared before sweep")

    except Exception as e:
        logging.error(f"[graphics_window._reset_sliders_before_sweep] Error resetting sliders before sweep: {e}")
