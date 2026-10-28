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

# panel -> (cursor that must exist, its sliders, its cursor updaters)
_PANEL_MARKERS = {
    "left":  ("cursor_left",  ("slider_left", "slider_left_2"),
              ("update_cursor", "update_cursor_2")),
    "right": ("cursor_right", ("slider_right", "slider_right_2"),
              ("update_right_cursor", "update_right_cursor_2")),
}

# -------------------------------------------------------------------------------------------------------------------- #

def _reset_markers_after_sweep(self, panels=("left", "right")):
    """Sliders at index 0 with the new range, markers and info panels at index 0.

    ``panels`` limits the reset to rebuilt panels (a one-panel rebuild leaves
    the other panel's markers where the user put them). Locked markers
    (``markers_locked``) share their index across panels, so then both reset.
    """
    if getattr(self, "markers_locked", False):
        panels = ("left", "right")
    panels = [p for p in ("left", "right") if p in panels]
    if not panels:
        return

    cursor = getattr(self, _PANEL_MARKERS[panels[0]][0], None)
    if cursor is None or getattr(cursor, "axes", None) is None:
        logging.warning("[graphics_window._reset_markers_after_sweep] %s cursor missing, skipped", panels[0])
        return

    freqs = getattr(self, "freqs", None)
    if freqs is None or len(freqs) == 0:
        logging.warning("[graphics_window._reset_markers_after_sweep] no frequency data, skipped")
        return

    slider_names = [s for p in panels for s in _PANEL_MARKERS[p][1]]
    updater_names = [u for p in panels for u in _PANEL_MARKERS[p][2]]

    max_index = len(freqs) - 1
    for name in slider_names:
        slider = getattr(self, name, None)
        if slider is not None:
            update_slider_range_silent(slider, max_index, 0)

    for name in updater_names:
        fn = getattr(self, name, None)
        if not callable(fn):
            continue
        try:
            fn(0)
        except Exception as e:
            logging.warning(f"[graphics_window._reset_markers_after_sweep] {name}(0) failed: {e}")

    logging.info("[graphics_window._reset_markers_after_sweep] markers reset to index 0 (0..%d)", max_index)
