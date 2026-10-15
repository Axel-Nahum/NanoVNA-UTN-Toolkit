"""
Measurement Viewer — standalone file-based S-parameter visualizer.

Opens from either the DUT Measurements or Material Characterization module.
Browse to a folder, click files from the list, and compare their S11 / S21
curves in a 2×2 chart layout (magnitude dB and phase per parameter).
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure as _Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from NanoVNA_UTN_Toolkit.utils import safe_import

logger = logging.getLogger(__name__)

apply_window_icon = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon"
)
dark_light_config = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "dark_light_config"
)

# ── Colour palette ────────────────────────────────────────────────────────── #
_PALETTE = [
    "#4da6ff", "#ff6b6b", "#51cf66", "#ffd43b",
    "#cc5de8", "#ff922b", "#20c997", "#f06595",
]

# ── Dark theme ────────────────────────────────────────────────────────────── #
_BG      = "#1e1e1e"
_TEXT    = "#cccccc"
_GRID    = "#333344"
_SPINE   = "#555566"


# ─────────────────────────────────────────────────────────────────────────── #
#  Helpers                                                                     #
# ─────────────────────────────────────────────────────────────────────────── #
def _freq_axis_unit(freqs: np.ndarray):
    mx = float(freqs[-1]) if len(freqs) else 1e9
    if mx >= 1e9: return 1e9, "GHz"
    if mx >= 1e6: return 1e6, "MHz"
    return 1e3, "kHz"


def _load_touchstone(path: str):
    """Return (freqs, s11, s21) or raise."""
    from NanoVNA_UTN_Toolkit.touchstone.Touchstone import Touchstone
    ts = Touchstone(path)
    ts.load()
    pts = ts.s11
    if not pts:
        raise ValueError("No S11 data.")
    freqs = np.array([p.freq for p in pts], dtype=float)
    s11   = np.array([complex(p.re, p.im) for p in pts], dtype=complex)
    s21_pts = ts.s21
    s21 = (np.array([complex(p.re, p.im) for p in s21_pts], dtype=complex)
           if s21_pts else None)
    return freqs, s11, s21


# ─────────────────────────────────────────────────────────────────────────── #
#  File data container                                                         #
# ─────────────────────────────────────────────────────────────────────────── #
class _FileEntry:
    __slots__ = ("path", "name", "color", "freqs", "s11", "s21")

    def __init__(self, path, color, freqs, s11, s21):
        self.path  = path
        self.name  = Path(path).name
        self.color = color
        self.freqs = freqs
        self.s11   = s11
        self.s21   = s21


# ─────────────────────────────────────────────────────────────────────────── #
#  Main window                                                                 #
# ─────────────────────────────────────────────────────────────────────────── #
class MeasurementViewerWindow(QMainWindow):

    def __init__(self, vna_device=None, source_module: str = "menu"):
        super().__init__()
        self._vna           = vna_device
        self._source_module = source_module

        # path → _FileEntry (cached loaded data)
        self._cache: dict[str, _FileEntry] = {}
        # path → colour index (persistent across folder changes)
        self._color_map: dict[str, str] = {}
        self._color_idx = 0
        self._layout_mode = 2  # 2 = S11 Mag/Phase stacked (default),  4 = 2×2 grid

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
        file_menu = mb.addMenu("File")

        clear_act = QAction("Clear Selection", self)
        clear_act.triggered.connect(self._clear_selection)
        file_menu.addAction(clear_act)

        file_menu.addSeparator()

        back_act = QAction("Back to Menu", self)
        back_act.triggered.connect(self.return_to_menu_window)
        file_menu.addAction(back_act)

    # ── UI ────────────────────────────────────────────────────────────────── #
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        h_root = QHBoxLayout(root)
        h_root.setContentsMargins(0, 0, 0, 0)
        h_root.setSpacing(0)

        # ── Left panel ──────────────────────────────────────────────────── #
        left = QWidget()
        left.setFixedWidth(270)
        left.setStyleSheet("background: #161622; border-right: 1px solid #2a2a3a;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(8, 10, 8, 8)
        lv.setSpacing(6)

        # Title
        lbl = QLabel("Files")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #aaaacc;")
        lv.addWidget(lbl)

        # Folder path bar
        path_row = QHBoxLayout()
        path_row.setSpacing(4)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Folder path…")
        self._path_edit.setStyleSheet(
            "QLineEdit { background: #1a1a2e; color: #cccccc; border: 1px solid #333355;"
            " border-radius: 3px; padding: 2px 6px; font-size: 11px; }"
        )
        self._path_edit.returnPressed.connect(self._load_folder_from_edit)
        path_row.addWidget(self._path_edit, stretch=1)

        browse_btn = QPushButton("…")
        browse_btn.setFixedSize(26, 26)
        browse_btn.setToolTip("Browse for folder")
        browse_btn.setStyleSheet(
            "QPushButton { background: #2a2a4a; color: #aaaacc; border: 1px solid #333355;"
            " border-radius: 3px; font-size: 13px; }"
            " QPushButton:hover { background: #3a3a6a; }"
        )
        browse_btn.clicked.connect(self._browse_folder)
        path_row.addWidget(browse_btn)
        lv.addLayout(path_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a3a;")
        lv.addWidget(sep)

        # File list
        self._file_list = QListWidget()
        self._file_list.setStyleSheet(
            "QListWidget { background: #12121e; border: none; color: #cccccc;"
            " font-size: 11px; outline: none; }"
            " QListWidget::item { padding: 5px 6px; border-bottom: 1px solid #1e1e2e; }"
            " QListWidget::item:selected { background: #2a2a4a; color: #ffffff; }"
            " QListWidget::item:hover { background: #1e1e3a; }"
            " QScrollBar:vertical { width: 6px; background: #1a1a2a; }"
            " QScrollBar::handle:vertical { background: #44445a; border-radius: 3px; }"
        )
        self._file_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection
        )
        self._file_list.itemSelectionChanged.connect(self._on_selection_changed)
        lv.addWidget(self._file_list, stretch=1)

        # Info label (file count)
        self._info_lbl = QLabel("")
        self._info_lbl.setStyleSheet("font-size: 10px; color: #555566; font-style: italic;")
        self._info_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        lv.addWidget(self._info_lbl)

        h_root.addWidget(left)

        # ── Right panel: toolbar + charts ────────────────────────────────── #
        right = QWidget()
        right.setStyleSheet("background: #1e1e1e;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        # Toolbar — Word/Altium style: labeled groups separated by dividers
        toolbar = QWidget()
        toolbar.setFixedHeight(52)
        toolbar.setStyleSheet("background: #161622; border-bottom: 1px solid #252535;")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(8, 0, 8, 0)
        tb.setSpacing(0)

        def _group(label_text: str, *widgets) -> QWidget:
            """Labeled group: controls on top, tiny label centred below."""
            grp = QWidget()
            grp.setStyleSheet("QWidget { background: transparent; }")
            gv = QVBoxLayout(grp)
            gv.setContentsMargins(6, 4, 6, 2)
            gv.setSpacing(2)

            ctrl_row = QWidget()
            ctrl_row.setStyleSheet("QWidget { background: transparent; }")
            cr = QHBoxLayout(ctrl_row)
            cr.setContentsMargins(0, 0, 0, 0)
            cr.setSpacing(2)
            for w in widgets:
                cr.addWidget(w)
            gv.addWidget(ctrl_row, alignment=Qt.AlignmentFlag.AlignHCenter)

            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 9px; color: #7777a0;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            gv.addWidget(lbl)
            return grp

        def _vsep() -> QFrame:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setFixedHeight(36)
            sep.setStyleSheet("color: #252535;")
            return sep

        # ── Group: Layout ────────────────────────────────────────────────── #
        self._btn_2 = QPushButton("2 Charts")
        self._btn_2.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_2.clicked.connect(lambda: self._set_layout(2))

        self._btn_4 = QPushButton("4 Charts")
        self._btn_4.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_4.clicked.connect(lambda: self._set_layout(4))

        self._update_layout_buttons()

        seg = QWidget()
        seg.setStyleSheet(
            "QWidget { background: #1a1a2e; border: 1px solid #2e2e4e; border-radius: 4px; }"
        )
        seg_lay = QHBoxLayout(seg)
        seg_lay.setContentsMargins(2, 2, 2, 2)
        seg_lay.setSpacing(1)
        seg_lay.addWidget(self._btn_2)
        seg_lay.addWidget(self._btn_4)

        tb.addWidget(_group("Layout", seg))
        tb.addWidget(_vsep())
        tb.addStretch(1)  # future groups go here

        rv.addWidget(toolbar)

        # Canvas
        self._fig = _Figure(facecolor=_BG)
        self._axes = self._fig.subplots(2, 1)   # default: 2-chart mode
        self._fig.subplots_adjust(left=0.09, right=0.97, top=0.93,
                                  bottom=0.09, hspace=0.45)
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        rv.addWidget(self._canvas, stretch=1)

        h_root.addWidget(right, stretch=1)

        self._reset_axes()

    # ── Layout toggle ─────────────────────────────────────────────────────── #
    _SEG_ACTIVE   = ("QPushButton { font-size:11px; padding:0 12px; height:22px;"
                     " border:none; background:#3a3a5a; color:#ccccff; border-radius:3px; }"
                     " QPushButton:hover { background:#4a4a6a; }")
    _SEG_INACTIVE = ("QPushButton { font-size:11px; padding:0 12px; height:22px;"
                     " border:none; background:transparent; color:#666688; border-radius:3px; }"
                     " QPushButton:hover { background:#252535; color:#aaaacc; }")

    def _update_layout_buttons(self):
        self._btn_4.setStyleSheet(
            self._SEG_ACTIVE if self._layout_mode == 4 else self._SEG_INACTIVE)
        self._btn_2.setStyleSheet(
            self._SEG_ACTIVE if self._layout_mode == 2 else self._SEG_INACTIVE)

    def _set_layout(self, mode: int):
        if self._layout_mode == mode:
            return
        self._layout_mode = mode
        self._update_layout_buttons()
        self._rebuild_figure()

    def _rebuild_figure(self):
        """Recreate matplotlib subplots for the current layout mode."""
        self._fig.clear()
        if self._layout_mode == 4:
            self._axes = self._fig.subplots(2, 2)
            self._fig.subplots_adjust(left=0.09, right=0.97, top=0.93,
                                      bottom=0.09, hspace=0.48, wspace=0.32)
        else:  # 2-chart mode
            self._axes = self._fig.subplots(2, 1)
            self._fig.subplots_adjust(left=0.09, right=0.97, top=0.93,
                                      bottom=0.09, hspace=0.45)
        # Replay current selection
        selected_paths = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._file_list.selectedItems()
        ]
        entries = [self._cache[p] for p in selected_paths if p in self._cache]
        self._redraw(entries)

    # ── Folder management ─────────────────────────────────────────────────── #
    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            self._path_edit.setText(folder)
            self._load_folder(folder)

    def _load_folder_from_edit(self):
        self._load_folder(self._path_edit.text().strip())

    def _load_folder(self, folder: str):
        from pathlib import Path as _P
        p = _P(folder)
        if not p.is_dir():
            return
        files = sorted(
            f for f in p.iterdir()
            if f.suffix.lower() in (".s1p", ".s2p")
        )
        self._file_list.blockSignals(True)
        self._file_list.clear()
        for f in files:
            item = QListWidgetItem(f.name)
            item.setData(Qt.ItemDataRole.UserRole, str(f))
            item.setToolTip(str(f))
            self._file_list.addItem(item)
        self._file_list.blockSignals(False)

        count = len(files)
        self._info_lbl.setText(
            f"{count} file{'s' if count != 1 else ''} found"
            if count else "No .s1p/.s2p files found"
        )
        self._redraw([])

    def _clear_selection(self):
        self._file_list.clearSelection()

    # ── Selection → redraw ────────────────────────────────────────────────── #
    def _on_selection_changed(self):
        selected_paths = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._file_list.selectedItems()
        ]
        # Assign colour to newly selected files
        for path in selected_paths:
            if path not in self._color_map:
                self._color_map[path] = _PALETTE[self._color_idx % len(_PALETTE)]
                self._color_idx += 1

        # Load uncached files
        entries = []
        for path in selected_paths:
            if path not in self._cache:
                try:
                    freqs, s11, s21 = _load_touchstone(path)
                    self._cache[path] = _FileEntry(
                        path, self._color_map[path], freqs, s11, s21
                    )
                except Exception as exc:
                    logger.warning("[MeasurementViewer] %s: %s", path, exc)
                    continue
            else:
                self._cache[path].color = self._color_map[path]
            entries.append(self._cache[path])

        # Update list item colours to reflect their assigned colour
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self._color_map and item.isSelected():
                item.setForeground(
                    __import__("PySide6.QtGui", fromlist=["QColor"]).QColor(
                        self._color_map[path]
                    )
                )
            else:
                from PySide6.QtGui import QColor
                item.setForeground(QColor(_TEXT))

        self._redraw(entries)

    # ── Drawing ───────────────────────────────────────────────────────────── #
    def _flat_axes(self) -> list:
        if self._layout_mode == 4:
            return [self._axes[0][0], self._axes[0][1],
                    self._axes[1][0], self._axes[1][1]]
        else:
            return list(self._axes)  # [ax_top, ax_bottom]

    def _reset_axes(self):
        titles = (["S11 Magnitude", "S11 Phase", "S21 Magnitude", "S21 Phase"]
                  if self._layout_mode == 4 else
                  ["S11 Magnitude", "S11 Phase"])
        for ax, title in zip(self._flat_axes(), titles):
            ax.set_facecolor(_BG)
            ax.set_title(title, fontsize=10, color=_TEXT, pad=4)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_xlabel("")
            ax.set_ylabel("")
            for spine in ax.spines.values():
                spine.set_color(_SPINE)
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                    ha="center", va="center", fontsize=10,
                    color="#666688", fontstyle="italic")
        self._canvas.draw_idle()

    def _redraw(self, entries: list[_FileEntry]):
        flat = self._flat_axes()
        for ax in flat:
            ax.cla()
            ax.set_facecolor(_BG)
            ax.tick_params(colors=_TEXT, labelsize=8)
            ax.grid(True, linestyle=":", alpha=0.35, color=_GRID)
            for spine in ax.spines.values():
                spine.set_color(_SPINE)

        if not entries:
            self._reset_axes()
            return

        all_f = np.concatenate([e.freqs for e in entries])
        div, unit = _freq_axis_unit(all_f)

        if self._layout_mode == 4:
            ax_s11_mag, ax_s11_ph, ax_s21_mag, ax_s21_ph = flat
            has_s21 = any(e.s21 is not None for e in entries)
            for e in entries:
                f, lw = e.freqs / div, 1.6
                if e.s11 is not None:
                    ax_s11_mag.plot(f, 20 * np.log10(np.abs(e.s11) + 1e-15),
                                    color=e.color, linewidth=lw, label=e.name)
                    ax_s11_ph.plot(f, np.angle(e.s11, deg=True),
                                   color=e.color, linewidth=lw, label=e.name)
                if e.s21 is not None:
                    ax_s21_mag.plot(f, 20 * np.log10(np.abs(e.s21) + 1e-15),
                                    color=e.color, linewidth=lw, label=e.name)
                    ax_s21_ph.plot(f, np.angle(e.s21, deg=True),
                                   color=e.color, linewidth=lw, label=e.name)
            specs = [
                (ax_s11_mag, "S11 Magnitude", "|S11| (dB)"),
                (ax_s11_ph,  "S11 Phase",     "∠S11 (°)"),
                (ax_s21_mag, "S21 Magnitude", "|S21| (dB)"),
                (ax_s21_ph,  "S21 Phase",     "∠S21 (°)"),
            ]
            if not has_s21:
                for ax in (ax_s21_mag, ax_s21_ph):
                    ax.text(0.5, 0.5, "No S21 data", transform=ax.transAxes,
                            ha="center", va="center", fontsize=9,
                            color="#666688", fontstyle="italic")
        else:
            ax_mag, ax_ph = flat
            for e in entries:
                f, lw = e.freqs / div, 1.6
                if e.s11 is not None:
                    ax_mag.plot(f, 20 * np.log10(np.abs(e.s11) + 1e-15),
                                color=e.color, linewidth=lw, label=e.name)
                    ax_ph.plot(f, np.angle(e.s11, deg=True),
                               color=e.color, linewidth=lw, label=e.name)
            specs = [
                (ax_mag, "S11 Magnitude", "|S11| (dB)"),
                (ax_ph,  "S11 Phase",     "∠S11 (°)"),
            ]

        for ax, title, ylabel in specs:
            ax.set_title(title, fontsize=10, color=_TEXT, pad=4)
            ax.set_ylabel(ylabel, fontsize=9, color=_TEXT)
            ax.set_xlabel(f"Frequency ({unit})", fontsize=9, color=_TEXT)

        if len(entries) > 1:
            for ax in flat:
                if ax.get_lines():
                    ax.legend(fontsize=7, loc="best",
                              facecolor="#1a1a2e", edgecolor="#333344",
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
