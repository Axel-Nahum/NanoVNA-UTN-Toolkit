"""
Shared widgets and utilities used by both PDF preview dialogs.

Consumers:
    - dut_measurement.exporters.export.graph_preview_dialog
    - material_characterization...utils.export.pdf_preview_dialog
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QLabel, QPushButton, QStyleOptionComboBox, QStylePainter,
)


# --------------------------------------------------------------------------- #
# _HoverHelpButton
# --------------------------------------------------------------------------- #

class HoverHelpButton(QPushButton):
    """Round ? button that shows a styled floating label on mouse hover."""

    _POPUP_SS = (
        "QLabel { background: #1e1e32; border: 1px solid #5555aa;"
        " border-radius: 10px; padding: 10px 13px;"
        " color: #ccccdd; font-size: 11px; }"
    )

    def __init__(self, title, body, parent=None):
        super().__init__("?", parent)
        self._title = title
        self._body = body
        self._popup = None
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(18, 18)
        self.setStyleSheet(
            "QPushButton { border: 1px solid #555577; border-radius: 9px;"
            " color: #8888aa; font-size: 10px; font-weight: bold;"
            " background: transparent; padding: 0; }"
            " QPushButton:hover { border-color: #8888cc; color: #bbbbff; }"
        )

    def enterEvent(self, event):
        self._show_popup()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._close_popup()
        super().leaveEvent(event)

    def hideEvent(self, event):
        self._close_popup()
        super().hideEvent(event)

    def _show_popup(self):
        if self._popup is not None:
            return
        html = (
            f"<b style='font-size:12px;color:#aaaaff'>{self._title}</b>"
            f"<br><br>{self._body.replace(chr(10), '<br>')}"
        )
        popup = QLabel(html)
        popup.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        popup.setStyleSheet(self._POPUP_SS)
        popup.setWordWrap(True)
        popup.setMaximumWidth(280)
        popup.adjustSize()
        pos = self.mapToGlobal(self.rect().bottomLeft())
        popup.move(pos)
        popup.show()
        self._popup = popup

    def _close_popup(self):
        if self._popup is not None:
            self._popup.close()
            self._popup = None


# Keep the private-name alias so existing code that still references the old
# name inside each module won't break during the migration.
_HoverHelpButton = HoverHelpButton


# --------------------------------------------------------------------------- #
# _CenteredComboBox / _make_centered_combo
# --------------------------------------------------------------------------- #

class CenteredComboBox(QComboBox):
    """QComboBox that draws its selected text centered."""

    def paintEvent(self, event):
        from PySide6.QtWidgets import QStyle
        from PySide6.QtGui import QPalette
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        opt.currentText = ""
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        arrow_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, opt,
            QStyle.SubControl.SC_ComboBoxArrow, self,
        )
        text_rect = self.rect()
        text_rect.setRight(arrow_rect.left())
        group = (QPalette.ColorGroup.Normal if self.isEnabled()
                 else QPalette.ColorGroup.Disabled)
        painter.setPen(self.palette().color(group, QPalette.ColorRole.Text))
        painter.drawText(text_rect, Qt.AlignCenter | Qt.AlignVCenter, self.currentText())


_CenteredComboBox = CenteredComboBox


def make_centered_combo(items):
    combo = CenteredComboBox()
    combo.addItems(items)
    combo.setCurrentIndex(0)
    for j in range(combo.count()):
        combo.setItemData(j, Qt.AlignCenter, Qt.TextAlignmentRole)
    return combo


_make_centered_combo = make_centered_combo


# --------------------------------------------------------------------------- #
# NoEnterButton
# --------------------------------------------------------------------------- #

class NoEnterButton(QPushButton):
    """QPushButton that ignores Return/Enter to avoid accidental form submission."""

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.hasFocus():
            event.ignore()
        else:
            super().keyPressEvent(event)


_NoEnterButton = NoEnterButton


# --------------------------------------------------------------------------- #
# enable_drag_annotations  (shared logic; only marker-index differs per dialog)
# --------------------------------------------------------------------------- #

def enable_drag_annotations(dialog, page_key_fn=None):
    """
    Wire up draggable / resizable marker annotation boxes on *dialog*.

    Parameters
    ----------
    dialog : QDialog
        Must expose: canvas, ax, ann_objects, marker_positions,
        current_graph_index, _drag_cids.
    page_key_fn : callable | None
        Called with no arguments to obtain the key into marker_positions.
        Defaults to ``lambda: dialog.current_graph_index``.
    """
    for cid in getattr(dialog, "_drag_cids", []):
        try:
            dialog.canvas.mpl_disconnect(cid)
        except Exception:
            pass

    if page_key_fn is None:
        page_key_fn = lambda: dialog.current_graph_index  # noqa: E731

    drag_state = {
        "obj": None, "mode": None, "press_px": None,
        "edge": None, "bbox0_px": None,
        "fontsize0": None, "text_w0": None, "text_h0": None,
        "patch_xy0": None, "txt_pos0": None,
    }

    EDGE_TOL = 10
    MIN_W_PX, MIN_H_PX = 50, 35

    def _patch_px(patch):
        t = patch.get_transform()
        x, y = patch.get_x(), patch.get_y()
        lb = t.transform((x, y))
        rt = t.transform((x + patch.get_width(), y + patch.get_height()))
        return lb[0], lb[1], rt[0], rt[1]

    def _px_to_data(px, py):
        return tuple(dialog.ax.transData.inverted().transform((px, py)))

    def _detect_edge(L, B, R, T, mx, my):
        on_l = abs(mx - L) < EDGE_TOL
        on_r = abs(mx - R) < EDGE_TOL
        on_b = abs(my - B) < EDGE_TOL
        on_t = abs(my - T) < EDGE_TOL
        in_x = L + EDGE_TOL < mx < R - EDGE_TOL
        in_y = B + EDGE_TOL < my < T - EDGE_TOL
        if on_r and on_t: return "top_right"
        if on_l and on_t: return "top_left"
        if on_r and on_b: return "bot_right"
        if on_l and on_b: return "bot_left"
        if on_r and in_y: return "right"
        if on_l and in_y: return "left"
        if on_t and in_x: return "top"
        if on_b and in_x: return "bottom"
        return None

    def _edge_cursor(edge):
        if edge in ("left", "right"):         return Qt.SizeHorCursor
        if edge in ("top", "bottom"):         return Qt.SizeVerCursor
        if edge in ("top_right", "bot_left"): return Qt.SizeBDiagCursor
        if edge in ("top_left", "bot_right"): return Qt.SizeFDiagCursor
        return Qt.ArrowCursor

    def _inside(L, B, R, T, mx, my):
        return L + EDGE_TOL < mx < R - EDGE_TOL and B + EDGE_TOL < my < T - EDGE_TOL

    def on_move_hover(event):
        if drag_state["obj"] is not None:
            return
        for obj in dialog.ann_objects:
            L, B, R, T = _patch_px(obj["patch"])
            edge = _detect_edge(L, B, R, T, event.x, event.y)
            if edge:
                dialog.canvas.setCursor(_edge_cursor(edge))
                return
            if _inside(L, B, R, T, event.x, event.y):
                dialog.canvas.setCursor(Qt.OpenHandCursor)
                return
        dialog.canvas.setCursor(Qt.ArrowCursor)

    def on_press(event):
        for obj in dialog.ann_objects:
            patch, txt = obj["patch"], obj["text"]
            L, B, R, T = _patch_px(patch)
            edge = _detect_edge(L, B, R, T, event.x, event.y)
            if edge:
                renderer = dialog.canvas.get_renderer()
                tbbox = txt.get_window_extent(renderer=renderer)
                drag_state.update({
                    "obj": obj, "mode": "resize",
                    "press_px": (event.x, event.y),
                    "edge": edge, "bbox0_px": (L, B, R, T),
                    "fontsize0": txt.get_fontsize(),
                    "text_w0": max(1.0, tbbox.width),
                    "text_h0": max(1.0, tbbox.height),
                })
                dialog.canvas.setCursor(_edge_cursor(edge))
                return
            if _inside(L, B, R, T, event.x, event.y):
                drag_state.update({
                    "obj": obj, "mode": "move",
                    "press_px": (event.x, event.y),
                    "patch_xy0": (patch.get_x(), patch.get_y()),
                    "txt_pos0": txt.get_position(),
                })
                dialog.canvas.setCursor(Qt.ClosedHandCursor)
                return

    def on_motion(event):
        if drag_state["obj"] is None:
            return
        obj = drag_state["obj"]
        patch, txt = obj["patch"], obj["text"]
        press_px, press_py = drag_state["press_px"]
        dx = event.x - press_px
        dy = event.y - press_py

        if drag_state["mode"] == "move":
            try:
                d0 = _px_to_data(press_px, press_py)
                d1 = _px_to_data(event.x, event.y)
                ddx, ddy = d1[0] - d0[0], d1[1] - d0[1]
                px0, py0 = drag_state["patch_xy0"]
                tx0, ty0 = drag_state["txt_pos0"]
                patch.set_x(px0 + ddx)
                patch.set_y(py0 + ddy)
                txt.set_position((tx0 + ddx, ty0 + ddy))
                dialog.marker_positions[page_key_fn()][obj["idx"]] = (tx0 + ddx, ty0 + ddy)
            except Exception:
                pass

        elif drag_state["mode"] == "resize":
            L0, B0, R0, T0 = drag_state["bbox0_px"]
            edge = drag_state["edge"]
            if   edge == "right":     nL,nB,nR,nT = L0,    B0,    R0+dx, T0
            elif edge == "left":      nL,nB,nR,nT = L0+dx, B0,    R0,    T0
            elif edge == "top":       nL,nB,nR,nT = L0,    B0,    R0,    T0+dy
            elif edge == "bottom":    nL,nB,nR,nT = L0,    B0+dy, R0,    T0
            elif edge == "top_right": nL,nB,nR,nT = L0,    B0,    R0+dx, T0+dy
            elif edge == "top_left":  nL,nB,nR,nT = L0+dx, B0,    R0,    T0+dy
            elif edge == "bot_right": nL,nB,nR,nT = L0,    B0+dy, R0+dx, T0
            elif edge == "bot_left":  nL,nB,nR,nT = L0+dx, B0+dy, R0,    T0
            else: return

            if nR - nL < MIN_W_PX:
                if "left" in edge: nL = nR - MIN_W_PX
                else:              nR = nL + MIN_W_PX
            if nT - nB < MIN_H_PX:
                if "bot" in edge or edge == "bottom": nB = nT - MIN_H_PX
                else:                                  nT = nB + MIN_H_PX

            try:
                d_lb = _px_to_data(nL, nB)
                d_rt = _px_to_data(nR, nT)
                patch.set_x(d_lb[0]); patch.set_y(d_lb[1])
                patch.set_width(max(1e-9, d_rt[0] - d_lb[0]))
                patch.set_height(max(1e-9, d_rt[1] - d_lb[1]))
                txt.set_position(((d_lb[0] + d_rt[0]) / 2, (d_lb[1] + d_rt[1]) / 2))
                PAD_PX = 8
                avail_w = max(1.0, (nR - nL) - 2 * PAD_PX)
                avail_h = max(1.0, (nT - nB) - 2 * PAD_PX)
                fs_w = drag_state["fontsize0"] * (avail_w / drag_state["text_w0"])
                fs_h = drag_state["fontsize0"] * (avail_h / drag_state["text_h0"])
                txt.set_fontsize(max(4, min(fs_w, fs_h)))
            except Exception:
                pass

        dialog.canvas.draw_idle()

    def on_release(event):
        if drag_state["obj"] is not None:
            obj = drag_state["obj"]
            try:
                L, B, R, T = _patch_px(obj["patch"])
                cx_d, cy_d = _px_to_data((L + R) / 2, (B + T) / 2)
                dialog.marker_positions[page_key_fn()][obj["idx"]] = (cx_d, cy_d)
            except Exception:
                pass
        drag_state.update({
            "obj": None, "mode": None, "press_px": None,
            "edge": None, "bbox0_px": None,
            "fontsize0": None, "text_w0": None, "text_h0": None,
            "patch_xy0": None, "txt_pos0": None,
        })
        dialog.canvas.setCursor(Qt.ArrowCursor)

    dialog._drag_cids = [
        dialog.canvas.mpl_connect("motion_notify_event", on_move_hover),
        dialog.canvas.mpl_connect("button_press_event",  on_press),
        dialog.canvas.mpl_connect("motion_notify_event", on_motion),
        dialog.canvas.mpl_connect("button_release_event", on_release),
    ]
