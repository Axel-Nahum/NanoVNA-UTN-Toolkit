"""
Export preview dialog for the permittivity chart.

Shows a clean preview of the εr(f) chart (slider axes hidden, main axes
expanded) with two draggable / resizable marker boxes — one for ε' and one
for ε'' — using the same FancyBboxPatch + edge-detection pattern as the DUT.

Actions: Copy to Clipboard (300 DPI) | Save as Image | Save as CSV | Close
CSV columns: Frequency (Hz) | Epsilon_real | Epsilon_imag
"""

import copy
import csv
import io
import logging

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QSizePolicy, QVBoxLayout,
)

logger = logging.getLogger(__name__)


class ChartExportDialog(QDialog):
    """Preview + export dialog for the permittivity εr(f) chart."""

    def __init__(self, parent=None, fig=None, result=None,
                 sample_name="sample", marker_data=None):
        super().__init__(parent)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        w = min(int(screen.width()  * 0.80), 1100)
        h = min(int(screen.height() * 0.82), 780)
        self.setMinimumSize(w, h)
        self.resize(w, h)
        self.setWindowTitle(f"Export — Permittivity Chart — {sample_name}")
        self.setModal(True)

        self._source_fig   = fig
        self._result       = result
        self._sample_name  = sample_name
        self._marker_data  = marker_data   # dict or None
        self._preview_fig  = None
        self._ann_objects  = []            # [{"text": txt, "patch": patch}, ...]
        self._drag_cids    = []

        self._setup_ui()

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        lbl = QLabel("Preview  —  drag boxes to reposition · resize from edges")
        lbl.setStyleSheet("color: #aaaaaa; font-size: 11px; border: none;")
        layout.addWidget(lbl)

        self._preview_fig = self._build_preview_figure()
        self._canvas = FigureCanvas(self._preview_fig)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._canvas, 1)

        # Draw once so the renderer is ready, then add marker boxes
        self._canvas.draw()
        self._add_marker_boxes()
        self._enable_drag_resize()

        btn_row = QHBoxLayout()

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(copy_btn)

        image_btn = QPushButton("Save as Image")
        image_btn.clicked.connect(self._save_as_image)
        btn_row.addWidget(image_btn)

        csv_btn = QPushButton("Save as CSV")
        csv_btn.clicked.connect(self._save_as_csv)
        btn_row.addWidget(csv_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    # Figure helpers
    # ------------------------------------------------------------------ #

    def _build_preview_figure(self):
        fig_copy = copy.deepcopy(self._source_fig)
        main_ax = None
        for ax in fig_copy.get_axes():
            if ax.get_position().height < 0.1:
                ax.set_visible(False)
            else:
                main_ax = ax
        if main_ax is not None:
            main_ax.set_position([0.10, 0.10, 0.86, 0.85])
        return fig_copy

    def _main_ax(self):
        for ax in self._preview_fig.get_axes():
            if ax.get_visible():
                return ax
        return None

    # ------------------------------------------------------------------ #
    # Marker boxes
    # ------------------------------------------------------------------ #

    def _add_marker_boxes(self):
        md = self._marker_data
        if md is None:
            return
        ax = self._main_ax()
        if ax is None:
            return

        freqs    = md["freqs"]
        real_eps = md["real_eps"]
        loss_eps = md["loss_eps"]
        idx1     = int(md["idx1"])
        idx2     = int(md["idx2"])
        m1_color = md["m1_color"]
        m2_color = md["m2_color"]

        def _fmt_freq(hz):
            return f"{hz/1e9:.4f} GHz" if hz >= 0.5e9 else f"{hz/1e6:.4f} MHz"

        # Compute default text-box positions (in data coords of the preview axes)
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        x_span = xlim[1] - xlim[0]
        y_span = ylim[1] - ylim[0]

        specs = [
            (idx1, real_eps, m1_color,
             f"f = {_fmt_freq(freqs[idx1])}\nε' = {real_eps[idx1]:.4f}",
             xlim[0] + x_span * 0.10,
             ylim[1] - y_span * 0.15),
            (idx2, loss_eps, m2_color,
             f"f = {_fmt_freq(freqs[idx2])}\nε'' = {loss_eps[idx2]:.4f}",
             xlim[0] + x_span * 0.60,
             ylim[1] - y_span * 0.15),
        ]

        renderer = self._canvas.get_renderer()
        PAD = 6

        for _idx, _arr, color, text, bx, by in specs:
            txt = ax.text(
                bx, by, text,
                ha="center", va="center",
                color=color, fontsize=9,
                linespacing=1.8, family="monospace",
                zorder=10, clip_on=False,
            )
            self._canvas.draw()
            tbbox = txt.get_window_extent(renderer=renderer)
            try:
                d_lb = ax.transData.inverted().transform(
                    (tbbox.x0 - PAD, tbbox.y0 - PAD))
                d_rt = ax.transData.inverted().transform(
                    (tbbox.x1 + PAD, tbbox.y1 + PAD))
            except Exception:
                d_lb = (bx - 0.1, by - 0.05)
                d_rt = (bx + 0.1, by + 0.05)

            patch = FancyBboxPatch(
                (d_lb[0], d_lb[1]),
                max(1e-9, d_rt[0] - d_lb[0]),
                max(1e-9, d_rt[1] - d_lb[1]),
                boxstyle="square,pad=0",
                facecolor="white", edgecolor=color,
                alpha=0.88, transform=ax.transData,
                zorder=9, clip_on=False,
            )
            ax.add_patch(patch)
            self._ann_objects.append({"text": txt, "patch": patch})

        self._canvas.draw()

    # ------------------------------------------------------------------ #
    # Drag / resize  (same pattern as DUT ExportDialog / pdf_preview_dialog)
    # ------------------------------------------------------------------ #

    def _enable_drag_resize(self):
        for cid in self._drag_cids:
            try:
                self._canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self._drag_cids = []

        ax = self._main_ax()
        if ax is None or not self._ann_objects:
            return

        EDGE_TOL = 10
        MIN_W_PX, MIN_H_PX = 50, 30

        drag_state = {
            "obj": None, "mode": None, "press_px": None,
            "edge": None, "bbox0_px": None,
            "patch_xy0": None, "txt_pos0": None,
        }

        def _patch_px(patch):
            """Patch bounds in matplotlib display coords (px, origin=bottom-left)."""
            t = patch.get_transform()
            x, y = patch.get_x(), patch.get_y()
            lb = t.transform((x, y))
            rt = t.transform((x + patch.get_width(), y + patch.get_height()))
            return lb[0], lb[1], rt[0], rt[1]

        def _px_to_data(px, py):
            return tuple(ax.transData.inverted().transform((px, py)))

        def _data_to_px(dx, dy):
            return ax.transData.transform((dx, dy))

        def _detect_edge(L, B, R, T, mx, my):
            on_l = abs(mx - L) < EDGE_TOL
            on_r = abs(mx - R) < EDGE_TOL
            on_b = abs(my - B) < EDGE_TOL
            on_t = abs(my - T) < EDGE_TOL
            in_x = L + EDGE_TOL < mx < R - EDGE_TOL
            in_y = B + EDGE_TOL < my < T - EDGE_TOL
            if on_r and on_t:  return "top_right"
            if on_l and on_t:  return "top_left"
            if on_r and on_b:  return "bot_right"
            if on_l and on_b:  return "bot_left"
            if on_r and in_y:  return "right"
            if on_l and in_y:  return "left"
            if on_t and in_x:  return "top"
            if on_b and in_x:  return "bottom"
            return None

        def _edge_cursor(edge):
            if edge in ("left", "right"):          return Qt.SizeHorCursor
            if edge in ("top", "bottom"):          return Qt.SizeVerCursor
            if edge in ("top_right", "bot_left"):  return Qt.SizeBDiagCursor
            if edge in ("top_left",  "bot_right"): return Qt.SizeFDiagCursor
            return Qt.ArrowCursor

        def _inside(L, B, R, T, mx, my):
            return (L + EDGE_TOL < mx < R - EDGE_TOL and
                    B + EDGE_TOL < my < T - EDGE_TOL)

        def on_move_hover(event):
            if event.x is None or event.y is None:
                return
            if drag_state["obj"] is not None:
                return
            try:
                for obj in self._ann_objects:
                    L, B, R, T = _patch_px(obj["patch"])
                    edge = _detect_edge(L, B, R, T, event.x, event.y)
                    if edge:
                        self._canvas.setCursor(_edge_cursor(edge))
                        return
                    if _inside(L, B, R, T, event.x, event.y):
                        self._canvas.setCursor(Qt.OpenHandCursor)
                        return
                self._canvas.setCursor(Qt.ArrowCursor)
            except Exception:
                pass

        def on_press(event):
            if event.x is None or event.y is None:
                return
            if event.button != 1:
                return
            try:
                for obj in self._ann_objects:
                    patch, txt = obj["patch"], obj["text"]
                    L, B, R, T = _patch_px(patch)
                    edge = _detect_edge(L, B, R, T, event.x, event.y)
                    if edge:
                        drag_state.update({
                            "obj": obj, "mode": "resize",
                            "press_px": (event.x, event.y),
                            "edge": edge,
                            "bbox0_px": (L, B, R, T),
                            "patch_xy0": (patch.get_x(), patch.get_y(),
                                          patch.get_width(), patch.get_height()),
                            "txt_pos0": txt.get_position(),
                        })
                        self._canvas.setCursor(_edge_cursor(edge))
                        return
                    if _inside(L, B, R, T, event.x, event.y):
                        drag_state.update({
                            "obj": obj, "mode": "drag",
                            "press_px": (event.x, event.y),
                            "patch_xy0": (patch.get_x(), patch.get_y(),
                                          patch.get_width(), patch.get_height()),
                            "txt_pos0": txt.get_position(),
                        })
                        self._canvas.setCursor(Qt.ClosedHandCursor)
                        return
            except Exception as exc:
                logger.error("[ChartExportDialog] on_press: %s", exc)

        def on_motion(event):
            if event.x is None or event.y is None:
                return
            if drag_state["obj"] is None:
                on_move_hover(event)
                return
            try:
                obj  = drag_state["obj"]
                patch, txt = obj["patch"], obj["text"]
                dx_px = event.x - drag_state["press_px"][0]
                dy_px = event.y - drag_state["press_px"][1]
                mode  = drag_state["mode"]

                if mode == "drag":
                    # Convert pixel delta to data-coord delta (same as DUT pattern)
                    press_px, press_py = drag_state["press_px"]
                    d0 = _px_to_data(press_px, press_py)
                    d1 = _px_to_data(event.x, event.y)
                    ddx, ddy = d1[0] - d0[0], d1[1] - d0[1]
                    bx0, by0, bw0, bh0 = drag_state["patch_xy0"]
                    tx0, ty0 = drag_state["txt_pos0"]
                    patch.set_x(bx0 + ddx)
                    patch.set_y(by0 + ddy)
                    txt.set_position((tx0 + ddx, ty0 + ddy))

                elif mode == "resize":
                    L0, B0, R0, T0 = drag_state["bbox0_px"]
                    edge = drag_state["edge"]
                    dx, dy = dx_px, dy_px

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

                    d_lb = _px_to_data(nL, nB)
                    d_rt = _px_to_data(nR, nT)
                    patch.set_x(d_lb[0])
                    patch.set_y(d_lb[1])
                    patch.set_width(max(1e-9, d_rt[0] - d_lb[0]))
                    patch.set_height(max(1e-9, d_rt[1] - d_lb[1]))
                    txt.set_position(((d_lb[0] + d_rt[0]) / 2, (d_lb[1] + d_rt[1]) / 2))

                self._canvas.draw_idle()
            except Exception as exc:
                logger.error("[ChartExportDialog] on_motion: %s", exc)

        def on_release(_event):
            drag_state["obj"] = None
            self._canvas.setCursor(Qt.ArrowCursor)

        self._drag_cids = [
            self._canvas.mpl_connect("motion_notify_event",  on_motion),
            self._canvas.mpl_connect("button_press_event",   on_press),
            self._canvas.mpl_connect("button_release_event", on_release),
        ]

    # ------------------------------------------------------------------ #
    # Export actions
    # ------------------------------------------------------------------ #

    def _prepare_export_figure(self):
        fig_copy = copy.deepcopy(self._preview_fig)
        fig_copy.set_size_inches(10, 7)
        return fig_copy

    def _copy_to_clipboard(self):
        try:
            fig = self._prepare_export_figure()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=300)
            buf.seek(0)
            plt.close(fig)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            QApplication.clipboard().setPixmap(pixmap)
            QMessageBox.information(self, "Copied", "Chart copied to clipboard at 300 DPI.")
        except Exception as exc:
            logger.error("[ChartExportDialog] clipboard: %s", exc)
            QMessageBox.critical(self, "Error", f"Failed to copy:\n{exc}")

    def _save_as_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Chart Image",
            f"{self._sample_name}_permittivity.png",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg)",
        )
        if not path:
            return
        try:
            fig = self._prepare_export_figure()
            fig.savefig(path, dpi=300, bbox_inches="tight")
            plt.close(fig)
            QMessageBox.information(self, "Saved", f"Image saved to:\n{path}")
        except Exception as exc:
            logger.error("[ChartExportDialog] image save: %s", exc)
            QMessageBox.critical(self, "Error", f"Failed to save image:\n{exc}")

    def _save_as_csv(self):
        if self._result is None:
            QMessageBox.warning(self, "No Data", "No permittivity data available.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV",
            f"{self._sample_name}_permittivity.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        try:
            f_hz   = np.asarray(self._result.f_hz, dtype=float)
            eps    = np.asarray(self._result.eps_selected, dtype=complex)
            e_real = np.real(eps)
            e_imag = -np.imag(eps)
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Frequency (Hz)", "Epsilon_real", "Epsilon_imag"])
                for freq, er, ei in zip(f_hz, e_real, e_imag):
                    writer.writerow([f"{freq:.4f}", f"{er:.6f}", f"{ei:.6f}"])
            QMessageBox.information(self, "Saved", f"CSV saved to:\n{path}")
        except Exception as exc:
            logger.error("[ChartExportDialog] CSV save: %s", exc)
            QMessageBox.critical(self, "Error", f"Failed to save CSV:\n{exc}")

    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        for cid in self._drag_cids:
            try:
                self._canvas.mpl_disconnect(cid)
            except Exception:
                pass
        if self._preview_fig is not None:
            try:
                plt.close(self._preview_fig)
            except Exception:
                pass
        event.accept()
