"""
Measurement Viewer — standalone file-based S-parameter visualizer.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure as _Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QGuiApplication
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

_PALETTE = [
    "#4da6ff", "#ff6b6b", "#51cf66", "#ffd43b",
    "#cc5de8", "#ff922b", "#20c997", "#f06595",
]

# ── Theme (app dark palette: blue-gray/slate with violet undertone) ───────── #
_WIN_BG   = "#1e1e2e"   # fondo principal app
_PANEL_BG = "#252538"   # cards / paneles elevados app
_BORDER   = "#383850"   # bordes app
_CARD_BG  = "#12121e"   # chart boxes — más oscuro, misma familia
_SPINE    = "#2a2a42"   # borde de ejes matplotlib
_ACCENT   = "#2d5a8e"
_ACCENT_H = "#3a6fa0"
_TEXT     = "#ffffff"
_TEXT2    = "#8888aa"
_GRID     = "#1e1e2e"
_BG       = _CARD_BG


# ─────────────────────────────────────────────────────────────────────────── #
def _freq_axis_unit(freqs: np.ndarray):
    mx = float(freqs[-1]) if len(freqs) else 1e9
    if mx >= 1e9: return 1e9, "GHz"
    if mx >= 1e6: return 1e6, "MHz"
    return 1e3, "kHz"


def _load_touchstone(path: str):
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
class MeasurementViewerWindow(QMainWindow):

    # Segmented-pill button styles
    _SEG_ACTIVE = (
        f"QPushButton {{ font-size:11px; padding:3px 14px; border:none;"
        f" background:{_ACCENT}; color:#ffffff; border-radius:5px; }}"
        f" QPushButton:hover {{ background:{_ACCENT_H}; }}"
    )
    _SEG_INACTIVE = (
        f"QPushButton {{ font-size:11px; padding:3px 14px; border:none;"
        f" background:transparent; color:{_TEXT2}; border-radius:5px; }}"
        f" QPushButton:hover {{ background:{_BORDER}; color:{_TEXT}; }}"
    )
    _ACTION_BTN = (
        f"QPushButton {{ font-size:11px; padding:4px 14px; border-radius:6px;"
        f" border:1px solid {_BORDER}; background:transparent; color:{_TEXT2}; }}"
        f" QPushButton:hover {{ background:{_BORDER}; color:{_TEXT}; }}"
    )

    def __init__(self, vna_device=None, source_module: str = "menu"):
        super().__init__()
        self._vna           = vna_device
        self._source_module = source_module
        self._cache: dict[str, _FileEntry] = {}
        self._color_map: dict[str, str]    = {}
        self._color_idx   = 0
        self._layout_mode = 2
        self._format_mode = "db"

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

    # ── Menubar ───────────────────────────────────────────────────────────── #
    def _build_menu(self):
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar {{ background:{_PANEL_BG}; color:{_TEXT};"
            f" border-bottom:1px solid {_BORDER}; }}"
            " QMenuBar::item:selected { background:#1c2433; }"
            f" QMenu {{ background:{_PANEL_BG}; color:{_TEXT};"
            f" border:1px solid {_BORDER}; }}"
            " QMenu::item:selected { background:#1c2433; }"
        )
        file_menu = mb.addMenu("File")
        clear_act = QAction("Clear Selection", self)
        clear_act.triggered.connect(self._clear_selection)
        file_menu.addAction(clear_act)
        file_menu.addSeparator()
        back_act = QAction("Back to Menu", self)
        back_act.triggered.connect(self.return_to_menu_window)
        file_menu.addAction(back_act)

    # ── Root layout ───────────────────────────────────────────────────────── #
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        v.addWidget(self._build_header())

        hline = QFrame()
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setFixedHeight(1)
        hline.setStyleSheet(f"background:{_BORDER};")
        v.addWidget(hline)

        content = QWidget()
        h = QHBoxLayout(content)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        h.addWidget(self._build_left_panel())

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFixedWidth(1)
        vline.setStyleSheet(f"background:{_BORDER};")
        h.addWidget(vline)

        h.addWidget(self._build_chart_area(), stretch=1)
        v.addWidget(content, stretch=1)

    # ── Header ────────────────────────────────────────────────────────────── #
    def _build_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setFixedHeight(72)
        h = QHBoxLayout(hdr)
        h.setContentsMargins(20, 0, 16, 0)
        h.setSpacing(0)

        # Branding
        brand = QWidget()
        brand.setStyleSheet("background:transparent;")
        bh = QHBoxLayout(brand)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(10)
        icon_lbl = QLabel()
        icon_lbl.setStyleSheet("background:transparent;")
        _ico = self.windowIcon()
        if not _ico.isNull():
            icon_lbl.setPixmap(_ico.pixmap(32, 32))
        else:
            icon_lbl.setText("~")
            icon_lbl.setStyleSheet("font-size:22px; color:#7ab3f5; background:transparent;")
        bh.addWidget(icon_lbl)
        tcol = QWidget()
        tcol.setStyleSheet("background:transparent;")
        tv = QVBoxLayout(tcol)
        tv.setContentsMargins(0, 0, 0, 0)
        tv.setSpacing(1)
        t1 = QLabel("Measurement Viewer")
        t1.setStyleSheet(
            f"font-size:14px; font-weight:bold; color:{_TEXT}; background:transparent;")
        t2 = QLabel("Compare and inspect measurement files")
        t2.setStyleSheet(
            f"font-size:10px; color:{_TEXT2}; background:transparent;")
        tv.addWidget(t1)
        tv.addWidget(t2)
        bh.addWidget(tcol)
        h.addWidget(brand)
        h.addStretch(1)

        # Layout group
        self._btn_2 = QPushButton("2 charts")
        self._btn_2.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_2.clicked.connect(lambda: self._set_layout(2))
        self._btn_4 = QPushButton("4 charts")
        self._btn_4.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_4.clicked.connect(lambda: self._set_layout(4))
        self._update_layout_buttons()
        h.addWidget(self._labeled_seg("Layout", self._btn_2, self._btn_4))
        h.addSpacing(16)

        # Display group
        self._fmt_btns: dict[str, QPushButton] = {}
        for fk, fl in [("db","dB"),("phase","Phase"),("real","Real"),("imag","Imag")]:
            b = QPushButton(fl)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, f=fk: self._set_format(f))
            self._fmt_btns[fk] = b
        self._update_format_buttons()
        h.addWidget(self._labeled_seg("Display", *self._fmt_btns.values()))

        h.addStretch(1)

        # Fit view
        fit_btn = QPushButton("Fit view")
        fit_btn.setStyleSheet(self._ACTION_BTN)
        fit_btn.setFixedHeight(32)
        fit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fit_btn.clicked.connect(self._fit_view)
        h.addWidget(fit_btn)

        return hdr

    def _labeled_seg(self, label: str, *buttons) -> QWidget:
        """Labeled segmented-pill group: label above, pill container below."""
        grp = QWidget()
        grp.setStyleSheet("background:transparent;")
        gv = QVBoxLayout(grp)
        gv.setContentsMargins(0, 8, 0, 8)
        gv.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size:9px; color:{_TEXT2}; background:transparent;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        gv.addWidget(lbl)

        pill = QWidget()
        pill.setStyleSheet("QWidget { background:#2e2e42; border-radius:7px; }")
        pl = QHBoxLayout(pill)
        pl.setContentsMargins(3, 3, 3, 3)
        pl.setSpacing(1)
        for btn in buttons:
            btn.setFixedHeight(26)
            pl.addWidget(btn)
        gv.addWidget(pill)
        return grp

    # ── Left panel ────────────────────────────────────────────────────────── #
    def _build_left_panel(self) -> QWidget:
        left = QWidget()
        left.setFixedWidth(275)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 14, 12, 12)
        lv.setSpacing(8)

        # Header row
        hrow = QHBoxLayout()
        hrow.setContentsMargins(0, 0, 0, 0)
        fl = QLabel("Measurement files")
        fl.setStyleSheet(
            f"font-size:12px; font-weight:bold; color:{_TEXT}; background:transparent;")
        hrow.addWidget(fl)
        hrow.addStretch()
        self._badge = QLabel("0 files")
        self._badge.setStyleSheet(
            f"font-size:10px; color:{_TEXT2}; background:{_BORDER};"
            " border-radius:8px; padding:1px 7px;")
        hrow.addWidget(self._badge)
        lv.addLayout(hrow)

        # Buttons
        brow = QHBoxLayout()
        brow.setContentsMargins(0, 0, 0, 0)
        brow.setSpacing(6)

        add_files = QPushButton("+ Add files")
        add_files.setFixedHeight(30)
        add_files.setCursor(Qt.CursorShape.PointingHandCursor)
        add_files.setStyleSheet(
            f"QPushButton {{ font-size:11px; background:{_ACCENT}; color:white;"
            " border:none; border-radius:5px; }"
            f" QPushButton:hover {{ background:{_ACCENT_H}; }}"
        )
        add_files.clicked.connect(self._add_files)
        brow.addWidget(add_files)

        add_folder = QPushButton("Add folder")
        add_folder.setFixedHeight(30)
        add_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder.setStyleSheet(
            f"QPushButton {{ font-size:11px; background:transparent; color:{_TEXT2};"
            f" border:1px solid {_BORDER}; border-radius:5px; }}"
            f" QPushButton:hover {{ background:{_BORDER}; color:{_TEXT}; }}"
        )
        add_folder.clicked.connect(self._browse_folder)
        brow.addWidget(add_folder)
        lv.addLayout(brow)

        # Filter
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filter files…")
        self._filter_edit.setFixedHeight(30)
        self._filter_edit.setStyleSheet(
            f"QLineEdit {{ background:{_PANEL_BG}; color:{_TEXT}; border:1px solid {_BORDER};"
            " border-radius:5px; padding:0 8px; font-size:11px; }"
            f" QLineEdit:focus {{ border-color:{_ACCENT}; }}"
        )
        self._filter_edit.textChanged.connect(self._apply_filter)
        lv.addWidget(self._filter_edit)

        # File list
        self._file_list = QListWidget()
        self._file_list.setStyleSheet(
            "QListWidget { background:transparent; border:none;"
            f" color:{_TEXT}; font-size:11px; outline:none; }}"
            f" QListWidget::item {{ padding:5px 4px; border-bottom:1px solid {_BORDER}; }}"
            f" QListWidget::item:selected {{ background:{_ACCENT}; color:#ffffff; }}"
            f" QListWidget::item:hover {{ background:{_BORDER}; }}"
            " QScrollBar:vertical { width:5px; background:transparent; }"
            f" QScrollBar::handle:vertical {{ background:{_BORDER}; border-radius:2px; }}"
        )
        self._file_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._file_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._file_list.setVisible(False)
        lv.addWidget(self._file_list, stretch=1)

        # Empty state
        self._empty_state = QWidget()
        ev = QVBoxLayout(self._empty_state)
        ev.setContentsMargins(0, 24, 0, 0)
        ev.setSpacing(6)
        ev.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        ico = QLabel("\U0001f4c1")
        ico.setStyleSheet("font-size:40px; background:transparent;")
        ico.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        ev.addWidget(ico)

        nm = QLabel("No measurements loaded")
        nm.setStyleSheet(
            f"font-size:12px; font-weight:bold; color:{_TEXT}; background:transparent;")
        nm.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        ev.addWidget(nm)

        ht = QLabel("Add .s1p or .s2p files to compare curves.")
        ht.setStyleSheet(f"font-size:10px; color:{_TEXT2}; background:transparent;")
        ht.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        ht.setWordWrap(True)
        ev.addWidget(ht)

        lv.addWidget(self._empty_state, stretch=1)
        return left

    # ── Chart area ────────────────────────────────────────────────────────── #
    def _build_chart_area(self) -> QWidget:
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(16, 10, 16, 14)
        rv.setSpacing(0)

        self._fig = _Figure(facecolor=_BG)
        self._axes = self._fig.subplots(2, 1)
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        rv.addWidget(self._canvas, stretch=1)

        self._reset_axes()
        return right

    # ── Layout / format toggle ────────────────────────────────────────────── #
    def _update_layout_buttons(self):
        self._btn_2.setStyleSheet(
            self._SEG_ACTIVE if self._layout_mode == 2 else self._SEG_INACTIVE)
        self._btn_4.setStyleSheet(
            self._SEG_ACTIVE if self._layout_mode == 4 else self._SEG_INACTIVE)

    def _update_format_buttons(self):
        for fmt, btn in self._fmt_btns.items():
            btn.setStyleSheet(
                self._SEG_ACTIVE if fmt == self._format_mode else self._SEG_INACTIVE)

    def _set_layout(self, mode: int):
        if self._layout_mode == mode:
            return
        self._layout_mode = mode
        self._update_layout_buttons()
        self._rebuild_figure()

    def _set_format(self, mode: str):
        if self._format_mode == mode:
            return
        self._format_mode = mode
        self._update_format_buttons()
        self._redraw(self._current_entries())

    def _rebuild_figure(self):
        self._fig.clear()
        if self._layout_mode == 4:
            self._axes = self._fig.subplots(2, 2)
        else:
            self._axes = self._fig.subplots(2, 1)
        self._redraw(self._current_entries())

    def _current_entries(self) -> list[_FileEntry]:
        return [
            self._cache[p]
            for p in (
                item.data(Qt.ItemDataRole.UserRole)
                for item in self._file_list.selectedItems()
            )
            if p in self._cache
        ]

    def _fit_view(self):
        for ax in self._flat_axes():
            if ax.get_lines():
                ax.relim()
                ax.autoscale_view()
        self._canvas.draw_idle()

    # ── File management ────────────────────────────────────────────────────── #
    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add Measurement Files", "",
            "Touchstone Files (*.s1p *.s2p);;All Files (*.*)"
        )
        if paths:
            self._add_file_paths(paths)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            files = sorted(
                str(f) for f in Path(folder).iterdir()
                if f.suffix.lower() in (".s1p", ".s2p")
            )
            self._add_file_paths(files)

    def _add_file_paths(self, paths: list[str]):
        existing = {
            self._file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._file_list.count())
        }
        self._file_list.blockSignals(True)
        for path in paths:
            if path in existing:
                continue
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self._file_list.addItem(item)
        self._file_list.blockSignals(False)
        self._refresh_panel_state()

    def _refresh_panel_state(self):
        count = self._file_list.count()
        self._badge.setText(f"{count} file{'s' if count != 1 else ''}")
        self._file_list.setVisible(count > 0)
        self._empty_state.setVisible(count == 0)

    def _apply_filter(self, text: str):
        text = text.lower()
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            item.setHidden(bool(text) and text not in item.text().lower())

    def _clear_selection(self):
        self._file_list.clearSelection()

    # ── Selection ─────────────────────────────────────────────────────────── #
    def _on_selection_changed(self):
        selected_paths = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._file_list.selectedItems()
        ]
        for path in selected_paths:
            if path not in self._color_map:
                self._color_map[path] = _PALETTE[self._color_idx % len(_PALETTE)]
                self._color_idx += 1

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

        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            col  = self._color_map.get(path) if item.isSelected() else None
            item.setForeground(QColor(col) if col else QColor(_TEXT))

        self._redraw(entries)

    # ── Drawing ───────────────────────────────────────────────────────────── #
    def _flat_axes(self) -> list:
        if self._layout_mode == 4:
            return [self._axes[0][0], self._axes[0][1],
                    self._axes[1][0], self._axes[1][1]]
        return list(self._axes)

    def _reset_axes(self):
        titles = (
            ["S11 Magnitude", "S11 Phase", "S21 Magnitude", "S21 Phase"]
            if self._layout_mode == 4 else ["S11", "S21"]
        )
        for ax, title in zip(self._flat_axes(), titles):
            ax.set_facecolor(_CARD_BG)
            ax.set_title(title, fontsize=11, color=_TEXT, pad=10)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color(_SPINE)
                spine.set_linewidth(0.8)
            ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                    ha="center", va="center", fontsize=10,
                    color=_TEXT2, fontstyle="italic")
        try:
            self._fig.tight_layout(pad=1.4, h_pad=2.0, w_pad=2.0)
        except Exception:
            pass
        self._canvas.draw_idle()

    def _redraw(self, entries: list[_FileEntry]):
        flat = self._flat_axes()
        for ax in flat:
            ax.cla()
            ax.set_facecolor(_CARD_BG)
            ax.tick_params(colors=_TEXT2, labelsize=8)
            ax.grid(True, linestyle=":", alpha=0.3, color=_GRID)
            for spine in ax.spines.values():
                spine.set_color(_SPINE)
                spine.set_linewidth(0.8)

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
                    ax_s11_mag.plot(f, 20*np.log10(np.abs(e.s11)+1e-15),
                                    color=e.color, linewidth=lw, label=e.name)
                    ax_s11_ph.plot(f, np.angle(e.s11, deg=True),
                                   color=e.color, linewidth=lw, label=e.name)
                if e.s21 is not None:
                    ax_s21_mag.plot(f, 20*np.log10(np.abs(e.s21)+1e-15),
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
                            color=_TEXT2, fontstyle="italic")
        else:
            ax_top, ax_bot = flat
            _fmt_meta = {
                "db":    ("Magnitude (dB)", "|S| (dB)"),
                "phase": ("Phase (°)",      "∠S (°)"),
                "real":  ("Real Part",      "Re(S)"),
                "imag":  ("Imag Part",      "Im(S)"),
            }
            fmt_title, fmt_ylabel = _fmt_meta[self._format_mode]

            def _yvals(s):
                if self._format_mode == "db":
                    return 20*np.log10(np.abs(s)+1e-15)
                if self._format_mode == "phase":
                    return np.angle(s, deg=True)
                if self._format_mode == "real":
                    return s.real
                return s.imag

            for e in entries:
                f, lw = e.freqs / div, 1.6
                if e.s11 is not None:
                    ax_top.plot(f, _yvals(e.s11), color=e.color, linewidth=lw, label=e.name)
                if e.s21 is not None:
                    ax_bot.plot(f, _yvals(e.s21), color=e.color, linewidth=lw, label=e.name)

            if not any(e.s21 is not None for e in entries):
                ax_bot.text(0.5, 0.5, "No S21 data", transform=ax_bot.transAxes,
                            ha="center", va="center", fontsize=9,
                            color=_TEXT2, fontstyle="italic")

            specs = [
                (ax_top, f"S11 — {fmt_title}", fmt_ylabel),
                (ax_bot, f"S21 — {fmt_title}", fmt_ylabel),
            ]

        for ax, title, ylabel in specs:
            ax.set_title(title, fontsize=11, color=_TEXT, pad=10)
            ax.set_ylabel(ylabel, fontsize=9, color=_TEXT2)
            ax.set_xlabel(f"Frequency ({unit})", fontsize=9, color=_TEXT2)

        if len(entries) > 1:
            for ax in flat:
                if ax.get_lines():
                    ax.legend(fontsize=7, loc="best",
                              facecolor=_PANEL_BG, edgecolor=_BORDER,
                              labelcolor=_TEXT)

        try:
            self._fig.tight_layout(pad=1.4, h_pad=2.0, w_pad=2.0)
        except Exception:
            pass
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
