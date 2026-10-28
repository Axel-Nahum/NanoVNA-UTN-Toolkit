"""
Marker interaction of the DUT graphics window without full redraws.

EN: Moving a marker (slider step, mouse drag, typed frequency) changes four
artists of one panel: the two cursors and the slider handle/bar. Everything
else is static, so the panel is blitted with ``RealtimeBlitter`` instead of
redrawn (a full draw was ~37 ms per step, measured headless). Several calls
per event (slider callback, wrapper, label update) are coalesced into one
blit on the next event-loop pass, and a blit is skipped when a full draw is
already queued, because that draw repaints everything anyway.

The saved marker index (``Cursor_x_y/index`` in graphics_config.ini) is
written once per burst of moves instead of once per event; the dialogs that
read it call ``flush_marker_indices`` first.

ES: Mover un marcador cambia solo cursores y manija del slider; el panel se
pinta por blitting y el índice se guarda al terminar la ráfaga, no por evento.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QTimer

from NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.blit_manager import RealtimeBlitter
from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings

# side -> (canvas attr, trace attr, cursor attrs, slider attrs)
_SIDES = {
    "left":  ("canvas_left",  "line_left",  ("cursor_left",  "cursor_left_2"),  ("slider_left",  "slider_left_2")),
    "right": ("canvas_right", "line_right", ("cursor_right", "cursor_right_2"), ("slider_right", "slider_right_2")),
}

_SLIDER_PARTS = ("poly", "_handle")   # the bar and the knob of a matplotlib Slider

MARKER_INDEX_SAVE_DELAY_MS = 250


# ------------------------------------------------------------------------------------------------------------------ #
# Blitting
# ------------------------------------------------------------------------------------------------------------------ #

def panel_blitters(window) -> dict:
    """The per-panel ``RealtimeBlitter`` registry shared with the real-time tick."""
    blitters = getattr(window, "_rt_blitters", None)
    if blitters is None:
        blitters = {}
        window._rt_blitters = blitters
    return blitters


def marker_artists(window, side):
    """Cursors and visible slider parts of ``side``: what a marker move changes.

    The sliders stop issuing their own ``draw_idle`` on ``set_val`` (``drawon``)
    because the blit repaints the handle.
    """
    _, _, cursor_names, slider_names = _SIDES[side]
    artists = []
    for name in cursor_names:
        cursor = getattr(window, name, None)
        if cursor is not None and getattr(cursor, "axes", None) is not None:
            artists.append(cursor)
    for name in slider_names:
        slider = getattr(window, name, None)
        if slider is None:
            continue
        ax = getattr(slider, "ax", None)
        if ax is None or ax.figure is None:
            continue
        slider.drawon = False
        if not ax.get_visible():
            continue   # draw_artist ignores the axes' visibility; a hidden slider stays hidden
        for part in _SLIDER_PARTS:
            artist = getattr(slider, part, None)
            if artist is not None:
                artists.append(artist)
    return artists


def request_marker_blit(window, side):
    """Blit ``side`` on the next event-loop pass (coalesced per panel)."""
    pending = getattr(window, "_marker_blit_pending", None)
    if pending is None:
        pending = set()
        window._marker_blit_pending = pending
    if side in pending:
        return
    pending.add(side)
    QTimer.singleShot(0, lambda: _do_marker_blit(window, side))


def _do_marker_blit(window, side):
    pending = getattr(window, "_marker_blit_pending", None)
    if pending is not None:
        pending.discard(side)

    canvas_name, line_name, _, _ = _SIDES[side]
    canvas = getattr(window, canvas_name, None)
    if canvas is None:
        return
    try:
        if getattr(canvas, "_draw_pending", False):
            # A full draw is already queued (post-sweep rebuild, visibility
            # toggle, resize): it repaints everything and the blitter captures
            # a fresh background on its draw_event.
            return

        blitters = panel_blitters(window)
        blitter = blitters.get(side)
        if blitter is None or blitter.canvas is not canvas:
            if blitter is not None:
                blitter.release()
            blitter = RealtimeBlitter(canvas)
            blitters[side] = blitter

        artists = marker_artists(window, side)
        if getattr(window, "_rt_active", False):
            # Same artist set as the real-time tick, so neither side invalidates
            # the other's background.
            line = getattr(window, line_name, None)
            if line is not None and getattr(line, "axes", None) is not None:
                artists = [line, *artists]

        # Nothing changed since the last full draw (typical right after a
        # rebuild: the post-sweep draw already painted the markers at index 0):
        # register the artists for the next move, but repaint nothing.
        stale = bool(getattr(canvas.figure, "stale", True))
        blitter.set_artists(artists)
        if not stale:
            return
        blitter.update()
    except Exception as e:
        logging.warning(f"[marker_interaction] blit failed on {side}, full draw instead: {e}")
        try:
            canvas.draw_idle()
        except Exception:
            pass


# ------------------------------------------------------------------------------------------------------------------ #
# Deferred save of the marker index
# ------------------------------------------------------------------------------------------------------------------ #

def save_marker_index_later(window, key, index):
    """Remember ``key = index`` and write it after the burst of moves ends."""
    pending = getattr(window, "_marker_index_pending", None)
    if pending is None:
        pending = {}
        window._marker_index_pending = pending
    pending[key] = int(index)

    timer = getattr(window, "_marker_index_timer", None)
    if timer is None:
        timer = QTimer(window)
        timer.setSingleShot(True)
        timer.setInterval(MARKER_INDEX_SAVE_DELAY_MS)
        timer.timeout.connect(lambda: flush_marker_indices(window))
        window._marker_index_timer = timer
    timer.start()


def flush_marker_indices(window):
    """Write every pending marker index now (dialogs call this before reading)."""
    timer = getattr(window, "_marker_index_timer", None)
    if timer is not None:
        try:
            timer.stop()
        except RuntimeError:
            pass
    pending = getattr(window, "_marker_index_pending", None)
    if not pending:
        return
    try:
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
            Path(__file__).resolve()
        )
        for key, value in pending.items():
            settings.setValue(key, value)
        settings.sync()
    except Exception as e:
        logging.warning(f"[marker_interaction] could not save marker indices: {e}")
    finally:
        pending.clear()
