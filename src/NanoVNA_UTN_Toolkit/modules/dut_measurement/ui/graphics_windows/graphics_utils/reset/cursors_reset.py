"""
Marker reset after a one-shot sweep (GUI thread).

EN: State only. Slider ranges and values are set silently (no ``on_changed``
callbacks, so no cascade of cursor updates and redraws), then the four cursor
updaters place the markers at index 0 and fill the info panels. Every
``draw_idle()`` they queue is coalesced by the Qt backend, and the caller lets
that single full draw per panel happen when it returns to the event loop.

ES: Solo estado. Los sliders se posicionan en silencio y los cuatro
actualizadores de cursor ponen marcadores y paneles en el índice 0; el dibujo
completo (uno por panel) lo hace el ``draw_idle`` acumulado al volver al loop.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging

update_slider_range_silent = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.set_slider_val_silent",
    "update_slider_range_silent"
)

_SLIDERS = ("slider_left", "slider_left_2", "slider_right", "slider_right_2")
_CURSOR_UPDATERS = ("update_cursor", "update_cursor_2", "update_right_cursor", "update_right_cursor_2")

# -------------------------------------------------------------------------------------------------------------------- #

def _reset_markers_after_sweep(self):
    """Sliders at index 0 with the new range, markers and info panels at index 0."""
    cursor = getattr(self, "cursor_left", None)
    if cursor is None or getattr(cursor, "axes", None) is None:
        logging.warning("[graphics_window._reset_markers_after_sweep] left cursor missing, skipped")
        return

    freqs = getattr(self, "freqs", None)
    if freqs is None or len(freqs) == 0:
        logging.warning("[graphics_window._reset_markers_after_sweep] no frequency data, skipped")
        return

    max_index = len(freqs) - 1
    for name in _SLIDERS:
        slider = getattr(self, name, None)
        if slider is not None:
            update_slider_range_silent(slider, max_index, 0)

    for name in _CURSOR_UPDATERS:
        fn = getattr(self, name, None)
        if not callable(fn):
            continue
        try:
            fn(0)
        except Exception as e:
            logging.warning(f"[graphics_window._reset_markers_after_sweep] {name}(0) failed: {e}")

    logging.info("[graphics_window._reset_markers_after_sweep] markers reset to index 0 (0..%d)", max_index)
