"""
Blitting helper for the real-time DUT panels.

EN: A full matplotlib draw of one DUT panel costs 20-30 ms (Smith grid, tick
    labels, legend). The real-time loop only moves two kinds of artists per
    tick, the data trace and the cursor markers, so it can keep the rendered
    background and paint just those on top ("blitting"), the same technique the
    Measurement Viewer uses for cursor dragging.

    Protocol (matplotlib's BlitManager recipe):
      - dynamic artists are flagged ``animated``: full draws skip them;
      - after every full draw (``draw_event``) the background is captured and
        the animated artists are painted on top, so a redraw triggered by any
        other code path (slider, resize, one-shot sweep) never hides the trace;
      - a tick calls ``update()``: restore background, draw artists, blit;
      - ``invalidate()`` forces the next update to be a full draw (axis limits
        or artists changed); ``release()`` un-flags the artists and restores
        normal drawing when real-time stops.

ES: Un dibujo completo de un panel cuesta 20-30 ms. Por tick solo cambian la
    traza y los marcadores de cursor, asi que se conserva el fondo renderizado
    y se pintan solo esos artistas encima (blitting), igual que el viewer.
"""

import logging

logger = logging.getLogger(__name__)


class RealtimeBlitter:

    def __init__(self, canvas):
        self._canvas = canvas
        self._artists: list = []
        self._bg = None
        self._cid = canvas.mpl_connect("draw_event", self._on_draw)

    # ------------------------------------------------------------------ #
    @property
    def canvas(self):
        return self._canvas

    def set_artists(self, artists):
        """Declare the artists that move per tick (trace line, cursor markers).

        Artists that were animated before but are no longer listed (recreated
        lines) get their flag back, otherwise they would never be drawn again.
        """
        new = [a for a in artists if a is not None]
        if new == self._artists:
            return
        for old in self._artists:
            if old not in new:
                try:
                    old.set_animated(False)
                except Exception:  # artist already removed from its axes
                    pass
        for a in new:
            a.set_animated(True)
        self._artists = new
        self._bg = None

    def invalidate(self):
        """The static part changed (axis limits, labels): redraw fully next time."""
        self._bg = None

    def update(self):
        """Paint the dynamic artists; a full draw only when no background is cached."""
        canvas = self._canvas
        if self._bg is None:
            # draw() is synchronous: _on_draw captures the background and paints
            # the animated artists before returning.
            canvas.draw()
            return
        try:
            canvas.restore_region(self._bg)
            self._draw_animated()
            canvas.blit(canvas.figure.bbox)
            canvas.flush_events()
        except Exception as exc:  # fall back to a normal draw, never lose the trace
            logger.warning("[RealtimeBlitter] blit failed, full redraw: %s", exc)
            self._bg = None
            canvas.draw_idle()

    def release(self):
        """Stop blitting: artists draw normally again, background dropped."""
        for a in self._artists:
            try:
                a.set_animated(False)
            except Exception:
                pass
        self._artists = []
        self._bg = None
        if self._cid is not None:
            try:
                self._canvas.mpl_disconnect(self._cid)
            except Exception:
                pass
            self._cid = None
        try:
            self._canvas.draw_idle()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    def _on_draw(self, event):
        if event is not None and event.canvas is not self._canvas:
            return
        try:
            self._bg = self._canvas.copy_from_bbox(self._canvas.figure.bbox)
            self._draw_animated()
        except Exception as exc:
            logger.warning("[RealtimeBlitter] background capture failed: %s", exc)
            self._bg = None

    def _draw_animated(self):
        for a in self._artists:
            try:
                if a.axes is not None:
                    a.axes.draw_artist(a)
            except Exception:
                pass
