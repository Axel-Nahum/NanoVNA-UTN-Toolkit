"""
Measurement Viewer — standalone file-based S-parameter visualizer.

Opens from either the DUT Measurements or Material Characterization module.
Loads one or more Touchstone (.s1p / .s2p) files and displays S11 / S21
magnitude (dB) and phase side by side in a 2×2 chart layout.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np
from matplotlib.figure import Figure as _Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from NanoVNA_UTN_Toolkit.utils import safe_import

logger = logging.getLogger(__name__)

apply_window_icon = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon"
)
dark_light_config = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "dark_light_config"
)

# ── Colour palette (cycles for each loaded file) ─────────────────────────── #
_PALETTE = [
    "#4da6ff", "#ff6b6b", "#51cf66", "#ffd43b",
    "#cc5de8", "#ff922b", "#20c997", "#f06595",
]

# ── Dark theme colours (consistent with the rest of the app) ─────────────── #
_BG        = "#1e1e1e"
_AXES_BG   = "#1e1e1e"
_TEXT      = "#cccccc"
_GRID      = "#333344"
_SPINE     = "#555566"

# ── Frequency formatter ───────────────────────────────────────────────────── #
def _fmt_freq(hz: float) -> str:
    if hz >= 1e9:
        return f"{hz/1e9:.4g} GHz"
    if hz >= 1e6:
        return f"{hz/1e6:.4g} MHz"
    return f"{hz/1e3:.4g} kHz"

def _freq_axis_unit(freqs: np.ndarray):
    """Return (divisor, label) for a clean single-unit x-axis."""
    mx = float(freqs[-1]) if len(freqs) else 0.0
    if mx >= 1e9:
        return 1e9, "GHz"
    if mx >= 1e6:
        return 1e6, "MHz"
    return 1e3, "kHz"


# ─────────────────────────────────────────────────────────────────────────── #
#  File entry                                                                  #
# ─────────────────────────────────────────────────────────────────────────── #
class _FileEntry:
    __slots__ = ("path", "name", "color", "visible",
                 "freqs", "s11", "s21")

    def __init__(self, path: str, color: str,
                 freqs, s11, s21):
        self.path    = path
        self.name    = Path(path).name
        self.color   = color
        self.visible = True
        self.freqs   = freqs   # np.ndarray (Hz)
        self.s11     = s11     # np.ndarray complex | None
        self.s21     = s21     # np.ndarray complex | None


# ─────────────────────────────────────────────────────────────────────────── #
#  Touchstone loader                                                           #
# ─────────────────────────────────────────────────────────────────────────── #
def _load_touchstone(path: str):
    """Return (freqs, s11, s21) or raise on error.

    Uses the project's own Touchstone parser so no new dependency is needed.
    s21 is None for .s1p files.
    """
    from NanoVNA_UTN_Toolkit.touchstone.Touchstone import Touchstone
    ts = Touchstone(path)
    ts.load()
    pts = ts.s11
    if not pts:
        raise ValueError("No S11 data in file.")
    freqs = np.array([p.freq for p in pts], dtype=float)
    s11   = np.array([complex(p.re, p.im) for p in pts], dtype=complex)
    s21_pts = ts.s21
    s21 = (np.array([complex(p.re, p.im) for p in s21_pts], dtype=complex)
           if s21_pts else None)
    return freqs, s11, s21


# ─────────────────────────────────────────────────────────────────────────── #
#  File row widget                                                             #
# ─────────────────────────────────────────────────────────────────────────── #
class _FileRow(QWidget):
    def __init__(self, entry: _FileEntry, on_toggle, on_remove, parent=None):
        super().__init__(parent)
        self._entry     = entry
        self._on_toggle = on_toggle
        self._on_remove = on_remove

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)

        # Colour swatch
        swatch = QLabel()
        swatch.setFixedSize(12, 12)
        swatch.setStyleSheet(
            f"background: {entry.color}; border-radius: 2px;"
        )
        lay.addWidget(swatch)

        # Filename (truncated)
        name_lbl = QLabel(entry.name)
        name_lbl.setToolTip(entry.path)
        name_lbl.setStyleSheet("font-size: 11px;")
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay.addWidget(name_lbl, stretch=1)

        # Visibility checkbox
        chk = QCheckBox()
        chk.setChecked(True)
        chk.setToolTip("Show / Hide")
        chk.stateChanged.connect(lambda state: self._on_toggle(
            entry, state == Qt.CheckState.Checked.value))
        lay.addWidget(chk)

        # Remove button
        btn_rm = QPushButton("✕")
        btn_rm.setFixedSize(20, 20)
        btn_rm.setStyleSheet(
            "QPushButton { font-size: 10px; color: #ff6b6b; border: none; }"
            " QPushButton:hover { color: #ff9999; }"
        )
        btn_rm.setToolTip("Remove from session")
        btn_rm.clicked.connect(lambda: self._on_remove(entry))
        lay.addWidget(btn_rm)

        self.setStyleSheet("QWidget { background: transparent; }")


# ─────────────────────────────────────────────────────────────────────────── #
#  Main window                                                                 #
# ─────────────────────────────────────────────────────────────────────────── #
class MeasurementViewerWindow(QMainWindow):
    """Standalone file-based S-parameter / permittivity viewer."""

    def __init__(self, vna_device=None, source_module: str = "menu"):
        """
        Parameters
        ----------
        vna_device : optional VNA device (passed through to back-navigation).
        source_module : "dut" | "char" | "menu" — controls where Back goes.
        """
        super().__init__()
        self._vna           = vna_device
        self._source_module = source_module
        self._entries: list[_FileEntry] = []
        self._color_idx     = 0
        self._row_widgets: dict[int, _FileRow] = {}  # id(entry) → row widget

        self.setWindowTitle("NanoVNA Toolkit — Measurement Viewer")

        screen = QGuiApplication.primaryScreen().availableGeometry()
        W = min(1280, max(960, int(screen.width()  * 0.85)))
        H = min(780,  max(600, int(screen.height() * 0.82)))
        self.setGeometry(120, 80, W, H)
        self.setMinimumSize(800, 520)

        if apply_window_icon:
            apply_window_icon(self)
        if dark_light_config:
            dark_light_config(self)

        self._build_menu()
        self._build_ui()

    # ── Menu ──────────────────────────────────────────────────────────────── #
    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("File")

        add_act = QAction("Add Files…", self)
        add_act.setShortcut("Ctrl+O")
        add_act.triggered.connect(self._add_files)
        file_menu.addAction(add_act)

        clear_act = QAction("Clear All", self)
        clear_act.triggered.connect(self._clear_all)
        file_menu.addAction(clear_act)

        file_menu.addSeparator()

        back_act = QAction("Back to Menu", self)
        back_act.triggered.connect(self.return_to_menu_window)
        file_menu.addAction(back_act)

        # View (placeholder for future options)
        view_menu = mb.addMenu("View")
        _ph = QAction("(coming soon)", self)
        _ph.setEnabled(False)
        view_menu.addAction(_ph)

    # ── UI ────────────────────────────────────────────────────────────────── #
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # ── Left panel ──────────────────────────────────────────────────── #
        left = QWidget()
        left.setFixedWidth(260)
        left.setStyleSheet("background: #161622; border-right: 1px solid #2a2a3a;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(8, 8, 8, 8)
        lv.setSpacing(6)

        title_lbl = QLabel("Files")
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #aaaacc;")
        lv.addWidget(title_lbl)

        add_btn = QPushButton("+ Add Files")
        add_btn.setFixedHeight(30)
        add_btn.setStyleSheet(
            "QPushButton { font-size: 12px; background: #2a2a4a; color: #4da6ff;"
            " border: 1px solid #4da6ff; border-radius: 4px; }"
            " QPushButton:hover { background: #3a3a6a; }"
        )
        add_btn.clicked.connect(self._add_files)
        lv.addWidget(add_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a3a;")
        lv.addWidget(sep)

        # Scroll area for file rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 6px; background: #1a1a2a; }"
            "QScrollBar::handle:vertical { background: #44445a; border-radius: 3px; }"
        )
        self._file_list_widget = QWidget()
        self._file_list_widget.setStyleSheet("background: transparent;")
        self._file_list_layout = QVBoxLayout(self._file_list_widget)
        self._file_list_layout.setContentsMargins(0, 0, 0, 0)
        self._file_list_layout.setSpacing(2)
        self._file_list_layout.addStretch(1)
        scroll.setWidget(self._file_list_widget)
        lv.addWidget(scroll, stretch=1)

        self._no_files_lbl = QLabel("No files loaded.\nUse + Add Files.")
        self._no_files_lbl.setStyleSheet(
            "font-size: 11px; color: #555566; font-style: italic;"
        )
        self._no_files_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.addWidget(self._no_files_lbl)

        h.addWidget(left)

        # ── Right panel: charts ──────────────────────────────────────────── #
        self._fig = _Figure(facecolor=_BG)
        self._axes = self._fig.subplots(2, 2)  # [[ax_s11_mag, ax_s11_ph], [ax_s21_mag, ax_s21_ph]]
        self._fig.subplots_adjust(left=0.08, right=0.97, top=0.93, bottom=0.09,
                                  hspace=0.45, wspace=0.32)

        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        h.addWidget(self._canvas, stretch=1)

        self._init_axes()

    def _init_axes(self):
        titles  = ["S11 Magnitude", "S11 Phase", "S21 Magnitude", "S21 Phase"]
        ylabels = ["|S11| (dB)", "∠S11 (°)", "|S21| (dB)", "∠S21 (°)"]
        flat    = [self._axes[0][0], self._axes[0][1],
                   self._axes[1][0], self._axes[1][1]]
        for ax, title, ylabel in zip(flat, titles, ylabels):
            ax.set_facecolor(_AXES_BG)
            ax.set_title(title, fontsize=10, color=_TEXT, pad=4)
            ax.set_ylabel(ylabel, fontsize=9, color=_TEXT)
            ax.set_xlabel("Frequency", fontsize=9, color=_TEXT)
            ax.tick_params(colors=_TEXT, labelsize=8)
            ax.grid(True, linestyle=":", alpha=0.35, color=_GRID)
            for spine in ax.spines.values():
                spine.set_color(_SPINE)
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                    ha="center", va="center", fontsize=9,
                    color="#444455", fontstyle="italic")
        self._canvas.draw_idle()

    # ── File management ───────────────────────────────────────────────────── #
    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Touchstone Files",
            "",
            "Touchstone (*.s1p *.s2p);;All files (*)",
        )
        if not paths:
            return
        added = 0
        for path in paths:
            if any(e.path == path for e in self._entries):
                continue  # already loaded
            try:
                freqs, s11, s21 = _load_touchstone(path)
            except Exception as exc:
                logger.warning("[MeasurementViewer] Could not load %s: %s", path, exc)
                continue
            color = _PALETTE[self._color_idx % len(_PALETTE)]
            self._color_idx += 1
            entry = _FileEntry(path, color, freqs, s11, s21)
            self._entries.append(entry)
            self._add_row(entry)
            added += 1

        if added:
            self._no_files_lbl.setVisible(False)
            self._redraw()

    def _add_row(self, entry: _FileEntry):
        row = _FileRow(
            entry,
            on_toggle=self._on_toggle,
            on_remove=self._on_remove,
        )
        self._row_widgets[id(entry)] = row
        # Insert before the trailing stretch
        idx = self._file_list_layout.count() - 1
        self._file_list_layout.insertWidget(idx, row)

    def _on_toggle(self, entry: _FileEntry, visible: bool):
        entry.visible = visible
        self._redraw()

    def _on_remove(self, entry: _FileEntry):
        row = self._row_widgets.pop(id(entry), None)
        if row is not None:
            self._file_list_layout.removeWidget(row)
            row.deleteLater()
        self._entries = [e for e in self._entries if e is not entry]
        if not self._entries:
            self._no_files_lbl.setVisible(True)
        self._redraw()

    def _clear_all(self):
        for row in list(self._row_widgets.values()):
            self._file_list_layout.removeWidget(row)
            row.deleteLater()
        self._row_widgets.clear()
        self._entries.clear()
        self._no_files_lbl.setVisible(True)
        self._redraw()

    # ── Drawing ───────────────────────────────────────────────────────────── #
    def _redraw(self):
        ax_s11_mag = self._axes[0][0]
        ax_s11_ph  = self._axes[0][1]
        ax_s21_mag = self._axes[1][0]
        ax_s21_ph  = self._axes[1][1]

        for ax in (ax_s11_mag, ax_s11_ph, ax_s21_mag, ax_s21_ph):
            ax.cla()
            ax.set_facecolor(_AXES_BG)
            ax.tick_params(colors=_TEXT, labelsize=8)
            ax.grid(True, linestyle=":", alpha=0.35, color=_GRID)
            for spine in ax.spines.values():
                spine.set_color(_SPINE)

        visible = [e for e in self._entries if e.visible]

        # Determine shared frequency unit from all loaded files
        all_freqs = np.concatenate([e.freqs for e in visible]) if visible else np.array([1e9])
        div, unit = _freq_axis_unit(all_freqs)

        has_s11 = any(e.s11 is not None for e in visible)
        has_s21 = any(e.s21 is not None for e in visible)

        for entry in visible:
            f = entry.freqs / div
            lw = 1.6

            if entry.s11 is not None:
                mag_db = 20 * np.log10(np.abs(entry.s11) + 1e-15)
                phase  = np.angle(entry.s11, deg=True)
                ax_s11_mag.plot(f, mag_db, color=entry.color, linewidth=lw,
                                label=entry.name)
                ax_s11_ph.plot(f, phase, color=entry.color, linewidth=lw,
                               label=entry.name)

            if entry.s21 is not None:
                mag_db = 20 * np.log10(np.abs(entry.s21) + 1e-15)
                phase  = np.angle(entry.s21, deg=True)
                ax_s21_mag.plot(f, mag_db, color=entry.color, linewidth=lw,
                                label=entry.name)
                ax_s21_ph.plot(f, phase, color=entry.color, linewidth=lw,
                               label=entry.name)

        # Titles / labels
        titles  = ["S11 Magnitude", "S11 Phase", "S21 Magnitude", "S21 Phase"]
        ylabels = ["|S11| (dB)", "∠S11 (°)", "|S21| (dB)", "∠S21 (°)"]
        flat    = [ax_s11_mag, ax_s11_ph, ax_s21_mag, ax_s21_ph]

        for ax, title, ylabel in zip(flat, titles, ylabels):
            ax.set_title(title, fontsize=10, color=_TEXT, pad=4)
            ax.set_ylabel(ylabel, fontsize=9, color=_TEXT)
            ax.set_xlabel(f"Frequency ({unit})", fontsize=9, color=_TEXT)

        # "No data" placeholders for empty axes
        if not has_s11:
            for ax in (ax_s11_mag, ax_s11_ph):
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                        ha="center", va="center", fontsize=9,
                        color="#444455", fontstyle="italic")
        if not has_s21:
            for ax in (ax_s21_mag, ax_s21_ph):
                ax.text(0.5, 0.5, "No S21 data", transform=ax.transAxes,
                        ha="center", va="center", fontsize=9,
                        color="#444455", fontstyle="italic")

        # Legend — only if multiple files
        if len(visible) > 1:
            for ax in flat:
                if ax.get_lines():
                    ax.legend(fontsize=7, loc="upper right",
                              facecolor="#1a1a2a", edgecolor="#333344",
                              labelcolor=_TEXT)

        self._canvas.draw_idle()

    # ── Navigation ────────────────────────────────────────────────────────── #
    def return_to_menu_window(self):
        from NanoVNA_UTN_Toolkit.modules.menu_window import ModuleSelectionWindow
        try:
            import matplotlib.pyplot as plt
            plt.close("all")
        except Exception:
            pass
        if self._vna:
            self._menu_win = ModuleSelectionWindow(vna_device=self._vna)
        else:
            self._menu_win = ModuleSelectionWindow()
        self._menu_win.show()
        self.close()
