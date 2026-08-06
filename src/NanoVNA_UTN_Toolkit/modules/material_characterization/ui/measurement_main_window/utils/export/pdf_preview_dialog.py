"""
PDF Export Preview Dialog — Material Characterization.

Two-step preview (S11 Smith chart / permittivity ε'+ε'') with draggable,
resizable marker boxes, mirroring the design of the DUT GraphPreviewExportDialog.

Graph 0 (Smith S11): 1 marker — follows the single S11 trace.
Graph 1 (Permittivity): 2 markers — Marker 1 tracks ε', Marker 2 tracks ε''.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import copy
import logging

import numpy as np
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QWidget, QCheckBox, QLineEdit, QComboBox,
    QFrame, QStylePainter, QStyleOptionComboBox, QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["text.usetex"] = False
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.rm"] = "serif"

logger = logging.getLogger(__name__)

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)

_CHART_INI_EXE = "INI/material_characterization/characterization_chart_config/characterization_chart_config.ini"
_CHART_INI_DEV = "modules/material_characterization/ui/measurement_main_window/characterization_chart_config/characterization_chart_config.ini"

# How many markers each graph supports
_GRAPH_MARKER_COUNT = {0: 1, 1: 2}

# --------------------------------------------------------------------------- #


def _fill_nans(y: np.ndarray) -> np.ndarray:
    finite = np.isfinite(y)
    if finite.all() or not finite.any():
        return y
    x = np.arange(len(y))
    out = y.copy()
    out[~finite] = np.interp(x[~finite], x[finite], y[finite])
    return out


def _freq_scale(freqs):
    max_f = float(np.max(freqs))
    if max_f >= 0.5e9:
        return 1e9, "GHz"
    if max_f >= 0.5e6:
        return 1e6, "MHz"
    return 1e3, "kHz"


class _CenteredComboBox(QComboBox):
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


def _make_centered_combo(items):
    combo = _CenteredComboBox()
    combo.addItems(items)
    combo.setCurrentIndex(0)
    for j in range(combo.count()):
        combo.setItemData(j, Qt.AlignCenter, Qt.TextAlignmentRole)
    return combo


class _NoEnterButton(QPushButton):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.hasFocus():
            event.ignore()
        else:
            super().keyPressEvent(event)


# --------------------------------------------------------------------------- #

class PermittivityPdfPreviewDialog(QDialog):
    """
    Preview dialog for the characterization PDF export.

    Graph 0: S11 Smith chart  — 1 marker (one trace)
    Graph 1: Permittivity ε'+ε'' — 2 markers (Marker 1 = ε', Marker 2 = ε'')
    Colors read from characterization_chart_config.ini for the permittivity markers.
    """

    TOTAL_GRAPHS = 2

    def __init__(
        self, parent=None, freqs=None, s11_data=None, eps_selected=None,
        sample_name=None, output_path=None, wizard_window=None,
    ):
        super().__init__(parent)

        self.freqs = np.asarray(freqs, dtype=float) if freqs is not None else np.linspace(1e6, 1e9, 100)
        self.s11_data = (np.asarray(s11_data, dtype=complex) if s11_data is not None
                         else np.exp(1j * np.linspace(0, 2 * np.pi, 100)))
        self.eps_selected = (np.asarray(eps_selected, dtype=complex) if eps_selected is not None
                             else np.ones(100, dtype=complex) * (2.5 - 0.1j))
        self.sample_name = sample_name or "sample"
        self.output_path = output_path
        self.wizard_window = wizard_window

        self.current_graph_index = 0
        self.current_figure = 0
        self.saved_figures = []

        # Marker state per graph — sized to max markers (2), but only
        # _GRAPH_MARKER_COUNT[g] slots are used for graph g.
        self.marker_positions = {i: [None, None] for i in range(self.TOTAL_GRAPHS)}
        self.marker_active = {i: [False, False] for i in range(self.TOTAL_GRAPHS)}
        self.ann_objects = []
        self.markers = []

        # --- Marker colors ---
        # Smith (graph 0): single green marker
        self._s11_marker_color = "#00cc44"
        # Permittivity (graph 1): one per curve, read from INI
        try:
            _s = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
            self._real_color = _s.value("Epsilon_Real/TraceColor", "#4da6ff")
            self._loss_color = _s.value("Epsilon_Imag/TraceColor", "#d62728")
        except Exception:
            self._real_color, self._loss_color = "#4da6ff", "#d62728"

        self._perm_marker_colors = [self._real_color, self._loss_color]

        # Pre-compute permittivity curves
        self._real_eps = _fill_nans(np.real(self.eps_selected))
        self._loss_eps = _fill_nans(-np.imag(self.eps_selected))
        self._freq_div, self._freq_unit = _freq_scale(self.freqs)
        self._scaled_freqs = self.freqs / self._freq_div

        self.setWindowTitle("Export Preview — Characterization")
        self.setModal(True)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        dialog_h = max(660, min(780, int(screen.height() * 0.72)))
        self.setFixedSize(740, dialog_h)

        self._build_ui()
        self._plot_graph(0)
        self._update_marker_checkboxes()
        self._update_markers(0)
        self._update_nav_buttons()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _marker_count(self, graph_index):
        return _GRAPH_MARKER_COUNT.get(graph_index, 1)

    def _marker_colors(self, graph_index):
        if graph_index == 0:
            return [self._s11_marker_color]
        return self._perm_marker_colors

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # Header
        self.page_label = QLabel(f"1 / {self.TOTAL_GRAPHS}")
        self.page_label.setStyleSheet(
            "color: #aaaaaa; font-size: 12px; font-weight: bold; min-width: 40px;"
        )
        self.page_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        title_label = QLabel("PDF Export Preview")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #e0e0e0;")
        title_label.setAlignment(Qt.AlignCenter)

        left_ph = QWidget()
        left_ph.setFixedWidth(50)
        header_row = QHBoxLayout()
        header_row.addWidget(left_ph)
        header_row.addWidget(title_label, 1, Qt.AlignCenter)
        header_row.addWidget(self.page_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addLayout(header_row)

        subtitle = QLabel("Navigate graphs, position markers, then generate the PDF report.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 11px; color: #999999;")
        main_layout.addWidget(subtitle)
        main_layout.addSpacing(4)

        # Canvas
        self.fig, self.ax = plt.subplots()
        self.fig.patch.set_facecolor("white")
        self.ax.set_facecolor("white")
        self.fig.subplots_adjust(left=0.15, right=0.95, top=0.9, bottom=0.18)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(360)
        self.canvas.resizeEvent = self._on_canvas_resize

        self.prev_button = _NoEnterButton("◀  Previous")
        self.next_button = _NoEnterButton("Next  ▶")
        self.prev_button.setFocusPolicy(Qt.NoFocus)
        self.next_button.setFocusPolicy(Qt.NoFocus)
        self.prev_button.setDefault(False)
        self.prev_button.setAutoDefault(False)
        self.next_button.setDefault(False)
        self.next_button.setAutoDefault(False)

        nav_style = """
            QPushButton {
                background-color: #f0f0f0; color: #333333;
                border: 1px solid #cccccc; border-radius: 5px;
                font-weight: bold; padding: 4px 16px;
                min-width: 80px; font-size: 12px;
            }
            QPushButton:hover:enabled { background-color: #e0e0e0; border-color: #999999; }
            QPushButton:disabled { background-color: #f8f8f8; color: #bbbbbb; border-color: #e0e0e0; }
        """
        self.prev_button.setStyleSheet(nav_style)
        self.next_button.setStyleSheet(nav_style)

        canvas_frame = QFrame()
        canvas_frame.setStyleSheet(
            "QFrame { border: 1px solid #444444; border-radius: 4px; background-color: white; }"
        )
        frame_layout = QVBoxLayout(canvas_frame)
        frame_layout.setContentsMargins(3, 3, 3, 3)
        frame_layout.setSpacing(0)
        frame_layout.addWidget(self.canvas)

        nav_strip = QHBoxLayout()
        nav_strip.setContentsMargins(8, 5, 8, 5)
        nav_strip.addWidget(self.prev_button)
        nav_strip.addStretch(1)
        nav_strip.addStretch(1)
        nav_strip.addWidget(self.next_button)
        frame_layout.addLayout(nav_strip)

        main_layout.addWidget(canvas_frame, alignment=Qt.AlignCenter)
        main_layout.addSpacing(6)

        # Marker widgets — create once for each graph × each slot
        # Graph 0: slot 0 only (1 marker). Graph 1: slots 0 and 1 (2 markers).
        self.marker_checkboxes = {}   # {graph: [cb0, cb1]}
        self.marker_freq_edits = {}   # {graph: [edit0, combo0, edit1, combo1]}

        for g in range(self.TOTAL_GRAPHS):
            n = self._marker_count(g)
            colors = self._marker_colors(g)
            cbs, edits_combos = [], []

            for slot in range(n):
                label = "Marker 1" if n == 1 else f"Marker {slot + 1}"
                cb = QCheckBox(label)
                cb.setStyleSheet(
                    f"color: {colors[slot]}; font-weight: bold; font-size: 12pt;"
                )
                cb.stateChanged.connect(lambda _, idx=g: self._update_markers(idx))
                cbs.append(cb)

                edit = QLineEdit()
                edit.setFixedWidth(80)
                edit.setStyleSheet(
                    "background-color: white; color: black; "
                    "border: 2px solid white; border-radius: 3px;"
                )
                combo = _make_centered_combo(["kHz", "MHz", "GHz"])

                edit.editingFinished.connect(
                    lambda e=edit, c=combo: self._validate_input(e, c) or self._on_marker_input_changed()
                )
                combo.currentIndexChanged.connect(self._on_marker_input_changed)

                edits_combos.append((edit, combo))

            self.marker_checkboxes[g] = cbs
            self.marker_freq_edits[g] = edits_combos

        self.marker_layout = QHBoxLayout()
        self.marker_layout.setContentsMargins(0, 0, 0, 0)
        self.marker_layout.setSpacing(0)

        marker_container = QWidget()
        mc_layout = QHBoxLayout(marker_container)
        mc_layout.setContentsMargins(0, 0, 0, 0)
        mc_layout.addStretch()
        mc_layout.addLayout(self.marker_layout)
        mc_layout.addStretch()
        main_layout.addWidget(marker_container, alignment=Qt.AlignCenter)
        main_layout.addSpacing(10)

        # Generate button
        self.export_button = _NoEnterButton("Generate PDF Report")
        self.export_button.setEnabled(False)
        self.export_button.setDefault(False)
        self.export_button.setAutoDefault(False)
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white; font-weight: bold;
                padding: 6px 16px; border-radius: 5px; font-size: 12px;
            }
            QPushButton:hover:enabled { background-color: #45a049; }
            QPushButton:disabled { background-color: #2d6e30; color: #6a9e6c; }
        """)
        self.export_button.clicked.connect(self._generate_pdf)

        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 4, 0, 0)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.export_button)
        bottom_bar.addStretch()
        main_layout.addLayout(bottom_bar)

        self.prev_button.clicked.connect(self._show_previous_graph)
        self.next_button.clicked.connect(self._show_next_graph)

    # ------------------------------------------------------------------ #

    def _on_canvas_resize(self, event):
        w = self.canvas.width()
        margin = max(0.10, min(0.20, 0.15 * (600 / max(w, 1))))
        self.fig.subplots_adjust(
            left=margin, right=1 - margin,
            top=1 - margin - 0.04, bottom=margin,
        )
        if getattr(self, "current_graph_index", 0) == 0:
            self.fig.subplots_adjust(left=margin, right=1 - margin,
                                     top=1 - margin, bottom=margin)
            self.ax.set_aspect("equal", adjustable="box")
            self.ax.set_anchor("C")
            self.ax.set_xlim(-1.1, 1.1)
            self.ax.set_ylim(-1.1, 1.1)
        self.canvas.draw_idle()

    def _on_marker_input_changed(self):
        self._update_markers(self.current_graph_index)
        self.canvas.draw_idle()

    def _validate_input(self, edit, combo):
        text = edit.text().strip()
        if not text:
            return
        try:
            val = float(text)
        except ValueError:
            return
        factors = {"kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
        f = factors[combo.currentText()]
        val_hz = min(max(val * f, self.freqs[0]), self.freqs[-1])
        edit.setText(f"{val_hz / f:.2f}")

    # ------------------------------------------------------------------ #
    # Graph plotting
    # ------------------------------------------------------------------ #

    def _plot_graph(self, index):
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("white")
        self.fig.subplots_adjust(left=0.15, right=0.90, top=0.90, bottom=0.18)

        if index == 0:
            self._plot_smith()
        else:
            self._plot_permittivity()

        self.canvas.draw()
        self._update_markers(index)

    def _plot_smith(self):
        try:
            import skrf as rf
            dummy_freq = rf.Frequency(
                self.freqs[0] / 1e9, self.freqs[-1] / 1e9, len(self.freqs), unit="GHz"
            )
            dummy_s = np.zeros((len(self.freqs), 1, 1), dtype=complex)
            dummy_ntw = rf.Network(frequency=dummy_freq, s=dummy_s)
            dummy_ntw.plot_s_smith(
                ax=self.ax, draw_labels=True, color="black", lw=0.5, label=None
            )
        except Exception as exc:
            logger.warning("[PdfPreview] skrf Smith grid failed: %s", exc)

        line, = self.ax.plot(
            np.real(self.s11_data), np.imag(self.s11_data),
            color="red", linewidth=1.2, label=r"$S_{11}$", clip_on=False,
        )
        self.ax.set_title(r"$S_{11}$ — Smith Chart", fontsize=14, pad=14)
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.set_xlim(-1.1, 1.1)
        self.ax.set_ylim(-1.1, 1.1)
        self.ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        legend = self.ax.legend(
            handles=[line], loc="lower left",
            bbox_to_anchor=(-0.13, 1.00), borderaxespad=0,
            fontsize=10, facecolor="white", edgecolor="black",
            framealpha=1,
        )
        legend.set_draggable(True)

    def _plot_permittivity(self):
        self.ax.plot(
            self._scaled_freqs, self._real_eps,
            color=self._real_color, linewidth=1.5, label=r"$\varepsilon_r'$",
        )
        self.ax.plot(
            self._scaled_freqs, self._loss_eps,
            color=self._loss_color, linewidth=1.5, label=r"$\varepsilon_r''$",
        )
        self.ax.set_title(r"$\varepsilon_r$ vs Frequency", fontsize=14, pad=14)
        self.ax.set_xlabel(f"Frequency ({self._freq_unit})", fontsize=12)
        self.ax.set_ylabel(r"$\varepsilon_r$", fontsize=12)
        self.ax.grid(True, linestyle="--", alpha=0.5)
        self.ax.legend(loc="upper right", fontsize=11)
        self.fig.subplots_adjust(left=0.13, right=0.95, top=0.90, bottom=0.14)

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def _show_next_graph(self):
        fig_copy = copy.deepcopy(self.fig)
        if len(self.saved_figures) <= self.current_figure:
            self.saved_figures.append(fig_copy)
        else:
            self.saved_figures[self.current_figure] = fig_copy

        if self.current_graph_index < self.TOTAL_GRAPHS - 1:
            self.current_graph_index += 1
            self.current_figure += 1
            self._plot_graph(self.current_graph_index)
            self._update_nav_buttons()
            self._update_marker_checkboxes()

        self.export_button.setEnabled(self.current_graph_index == self.TOTAL_GRAPHS - 1)

    def _show_previous_graph(self):
        fig_copy = copy.deepcopy(self.fig)
        if len(self.saved_figures) <= self.current_figure:
            self.saved_figures.append(fig_copy)
        else:
            self.saved_figures[self.current_figure] = fig_copy

        if self.current_graph_index > 0:
            self.current_graph_index -= 1
            self.current_figure -= 1
            self._plot_graph(self.current_graph_index)
            self._update_nav_buttons()
            self._update_marker_checkboxes()

        self.export_button.setEnabled(self.current_graph_index == self.TOTAL_GRAPHS - 1)

    def _update_nav_buttons(self):
        self.prev_button.setEnabled(self.current_graph_index > 0)
        self.next_button.setEnabled(self.current_graph_index < self.TOTAL_GRAPHS - 1)
        self.page_label.setText(f"{self.current_graph_index + 1} / {self.TOTAL_GRAPHS}")

    # ------------------------------------------------------------------ #
    # Marker checkbox layout
    # ------------------------------------------------------------------ #

    def _update_marker_checkboxes(self):
        while self.marker_layout.count():
            self.marker_layout.takeAt(0)

        g = self.current_graph_index
        n = self._marker_count(g)
        cbs = self.marker_checkboxes[g]
        edits_combos = self.marker_freq_edits[g]

        # Detach all widgets
        for slot in range(n):
            edits_combos[slot][0].setParent(None)
            edits_combos[slot][1].setParent(None)
            cbs[slot].setParent(None)

        for slot in range(n):
            cb = cbs[slot]
            edit, combo = edits_combos[slot]

            vbox = QVBoxLayout()
            vbox.setSpacing(8)
            cb_row = QHBoxLayout()
            cb_row.addStretch()
            cb_row.addWidget(cb)
            cb_row.addStretch()
            vbox.addLayout(cb_row)
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(edit)
            row.addWidget(combo)
            vbox.addLayout(row)

            self.marker_layout.addLayout(vbox)
            if slot < n - 1:
                self.marker_layout.addSpacing(70)

        self.canvas.draw_idle()

    # ------------------------------------------------------------------ #
    # Marker rendering
    # ------------------------------------------------------------------ #

    def _update_markers(self, graph_index=None):
        if graph_index is None:
            graph_index = self.current_graph_index

        ax = self.ax
        n = self._marker_count(graph_index)
        colors = self._marker_colors(graph_index)

        # Remove previous markers
        for obj in getattr(self, "ann_objects", []):
            try: obj["text"].remove()
            except Exception: pass
            try: obj["patch"].remove()
            except Exception: pass
        for mk in getattr(self, "markers", []):
            mk.set_visible(False)
        self.ann_objects = []
        self.markers = []

        cbs = self.marker_checkboxes[graph_index]
        edits_combos = self.marker_freq_edits[graph_index]
        self.marker_active[graph_index] = [cbs[s].isChecked() for s in range(n)]

        _xlim = ax.get_xlim()
        _ylim = ax.get_ylim()

        for slot in range(n):
            active = self.marker_active[graph_index][slot]
            edit, combo = edits_combos[slot]
            color = colors[slot]

            if active:
                edit.setEnabled(True)
                combo.setEnabled(True)
                edit.setStyleSheet(
                    "background-color: white; color: black; "
                    "border: 2px solid white; border-radius: 3px;"
                )

                try:
                    freq_val = float(edit.text())
                    unit_factor = {"kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[combo.currentText()]
                    freq_hz = freq_val * unit_factor
                except Exception:
                    split = len(self.freqs) // 3
                    freq_hz = self.freqs[split if slot == 0 else 2 * split]
                    unit_factor = 1e6

                idx_f = int(np.abs(self.freqs - freq_hz).argmin())
                nearest_hz = self.freqs[idx_f]
                nearest_val = nearest_hz / unit_factor
                edit.setText(f"{nearest_val:.2f}")
                unit_display = combo.currentText()

                if graph_index == 0:
                    # Smith: x=Re, y=Im
                    x = float(np.real(self.s11_data[idx_f]))
                    y = float(np.imag(self.s11_data[idx_f]))
                    text = (
                        f"Marker 1\n"
                        f"Freq: {nearest_val:.2f} {unit_display}\n"
                        f"Re: {x:.3f}   Im: {y:.3f}"
                    )
                else:
                    # Permittivity: x=freq, y depends on slot
                    x = float(self._scaled_freqs[idx_f])
                    if slot == 0:
                        y = float(self._real_eps[idx_f])
                        val_label = "ε'"
                    else:
                        y = float(self._loss_eps[idx_f])
                        val_label = "ε''"
                    text = (
                        f"Marker {slot + 1}\n"
                        f"Freq: {nearest_val:.2f} {unit_display}\n"
                        f"{val_label}: {y:.2f}"
                    )

                ann_x, ann_y = (
                    self.marker_positions[graph_index][slot]
                    if self.marker_positions[graph_index][slot] else (x, y)
                )

                mk_line, = ax.plot(x, y, marker="o", color=color, markersize=8)

                txt = ax.text(
                    ann_x, ann_y, text,
                    ha="center", va="center",
                    color=color, fontsize=9,
                    linespacing=1.8, family="monospace",
                    zorder=10, clip_on=False,
                )

                renderer = self.canvas.get_renderer()
                tbbox = txt.get_window_extent(renderer=renderer)
                PAD = 6
                try:
                    d_lb = ax.transData.inverted().transform((tbbox.x0 - PAD, tbbox.y0 - PAD))
                    d_rt = ax.transData.inverted().transform((tbbox.x1 + PAD, tbbox.y1 + PAD))
                except Exception:
                    d_lb = (ann_x - 0.15, ann_y - 0.08)
                    d_rt = (ann_x + 0.15, ann_y + 0.08)

                patch = FancyBboxPatch(
                    (d_lb[0], d_lb[1]),
                    max(1e-9, d_rt[0] - d_lb[0]),
                    max(1e-9, d_rt[1] - d_lb[1]),
                    boxstyle="square,pad=0",
                    facecolor="white", edgecolor=color,
                    alpha=0.85, transform=ax.transData,
                    zorder=9, clip_on=False,
                )
                ax.add_patch(patch)

                self.markers.append(mk_line)
                self.ann_objects.append({"text": txt, "patch": patch, "idx": slot})
                self.marker_positions[graph_index][slot] = (ann_x, ann_y)

            else:
                edit.setEnabled(False)
                combo.setEnabled(False)
                edit.setStyleSheet(
                    "background-color: #d8d8d8; color: #888888; "
                    "border: 1px solid #aaaaaa; border-radius: 3px;"
                )
                unit_factor = {"kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[combo.currentText()]
                edit.setText(f"{self.freqs[0] / unit_factor:.2f}")

        ax.set_xlim(_xlim)
        ax.set_ylim(_ylim)

        self._enable_drag_annotations()
        self.canvas.draw()

    # ------------------------------------------------------------------ #
    # Drag / resize (identical logic to DUT graph_preview_dialog)
    # ------------------------------------------------------------------ #

    def _enable_drag_annotations(self):
        for cid in getattr(self, "_drag_cids", []):
            try: self.canvas.mpl_disconnect(cid)
            except Exception: pass

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
            return tuple(self.ax.transData.inverted().transform((px, py)))

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
            if edge in ("left", "right"):          return Qt.SizeHorCursor
            if edge in ("top", "bottom"):          return Qt.SizeVerCursor
            if edge in ("top_right", "bot_left"):  return Qt.SizeBDiagCursor
            if edge in ("top_left",  "bot_right"): return Qt.SizeFDiagCursor
            return Qt.ArrowCursor

        def _inside(L, B, R, T, mx, my):
            return L + EDGE_TOL < mx < R - EDGE_TOL and B + EDGE_TOL < my < T - EDGE_TOL

        def on_move_hover(event):
            if drag_state["obj"] is not None:
                return
            for obj in self.ann_objects:
                L, B, R, T = _patch_px(obj["patch"])
                edge = _detect_edge(L, B, R, T, event.x, event.y)
                if edge:
                    self.canvas.setCursor(_edge_cursor(edge))
                    return
                if _inside(L, B, R, T, event.x, event.y):
                    self.canvas.setCursor(Qt.OpenHandCursor)
                    return
            self.canvas.setCursor(Qt.ArrowCursor)

        def on_press(event):
            for obj in self.ann_objects:
                patch, txt = obj["patch"], obj["text"]
                L, B, R, T = _patch_px(patch)
                edge = _detect_edge(L, B, R, T, event.x, event.y)
                if edge:
                    renderer = self.canvas.get_renderer()
                    tbbox = txt.get_window_extent(renderer=renderer)
                    drag_state.update({
                        "obj": obj, "mode": "resize",
                        "press_px": (event.x, event.y),
                        "edge": edge, "bbox0_px": (L, B, R, T),
                        "fontsize0": txt.get_fontsize(),
                        "text_w0": max(1.0, tbbox.width),
                        "text_h0": max(1.0, tbbox.height),
                    })
                    self.canvas.setCursor(_edge_cursor(edge))
                    return
                if _inside(L, B, R, T, event.x, event.y):
                    drag_state.update({
                        "obj": obj, "mode": "move",
                        "press_px": (event.x, event.y),
                        "patch_xy0": (patch.get_x(), patch.get_y()),
                        "txt_pos0": txt.get_position(),
                    })
                    self.canvas.setCursor(Qt.ClosedHandCursor)
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
                    self.marker_positions[self.current_graph_index][obj["idx"]] = (
                        tx0 + ddx, ty0 + ddy
                    )
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

            self.canvas.draw_idle()

        def on_release(event):
            if drag_state["obj"] is not None:
                obj = drag_state["obj"]
                try:
                    L, B, R, T = _patch_px(obj["patch"])
                    cx_d, cy_d = _px_to_data((L + R) / 2, (B + T) / 2)
                    self.marker_positions[self.current_graph_index][obj["idx"]] = (cx_d, cy_d)
                except Exception:
                    pass
            drag_state.update({
                "obj": None, "mode": None, "press_px": None,
                "edge": None, "bbox0_px": None,
                "fontsize0": None, "text_w0": None, "text_h0": None,
                "patch_xy0": None, "txt_pos0": None,
            })
            self.canvas.setCursor(Qt.ArrowCursor)

        self._drag_cids = [
            self.canvas.mpl_connect("motion_notify_event", on_move_hover),
            self.canvas.mpl_connect("button_press_event", on_press),
            self.canvas.mpl_connect("motion_notify_event", on_motion),
            self.canvas.mpl_connect("button_release_event", on_release),
        ]

    # ------------------------------------------------------------------ #
    # PDF generation
    # ------------------------------------------------------------------ #

    def _save_current_graph(self):
        fig_copy = copy.deepcopy(self.fig)
        if len(self.saved_figures) <= self.current_figure:
            self.saved_figures.append(fig_copy)
        else:
            self.saved_figures[self.current_figure] = fig_copy

    def _generate_pdf(self):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.export.permittivity_exporter import (
            PermittivityExporter,
        )

        self._save_current_graph()

        exporter = PermittivityExporter(parent_widget=self, figures=self.saved_figures)

        is_available, compiler_info, error_msg = exporter.check_latex_installation()
        if not is_available:
            QMessageBox.critical(self, "LaTeX not found", error_msg)
            return

        output_path = self.output_path
        if not output_path:
            output_path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report",
                f"characterization_{self.sample_name}.pdf",
                "PDF Files (*.pdf)",
            )
            if not output_path:
                return

        success = exporter.export_to_pdf(
            freqs=self.freqs,
            s11_data=self.s11_data,
            eps_selected=self.eps_selected,
            sample_name=self.sample_name,
            wizard_window=self.wizard_window,
            output_path=output_path,
            compiler_path=compiler_info[1],
        )

        if success:
            QMessageBox.information(
                self, "Export Complete",
                f"PDF successfully created at:\n{output_path}",
            )
            self.accept()
