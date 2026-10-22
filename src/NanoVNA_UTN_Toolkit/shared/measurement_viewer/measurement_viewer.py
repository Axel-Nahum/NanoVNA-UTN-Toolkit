"""
Measurement Viewer — standalone file-based S-parameter visualizer.
"""

from __future__ import annotations

import logging
import os as _os
import tempfile as _tmp
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure as _Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction, QColor, QGuiApplication, QIcon,
    QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton,
    QSizePolicy, QStackedWidget, QTreeWidget, QTreeWidgetItem,
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
_load_text = safe_import(
    "NanoVNA_UTN_Toolkit.shared.measurement_viewer.resources_loader", "load_text"
)
open_preferences_dialog = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.preferences.preferences", "open_preferences_dialog"
)
_get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)
_toggle_menu_dark_mode = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "toggle_menu_dark_mode"
)
_show_app_about = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.help_menu.help_menu", "show_app_about"
)
_show_about_dialog = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.help_menu.help_menu", "show_about_dialog"
)
_get_current_language = safe_import(
    "NanoVNA_UTN_Toolkit.shared.measurement_viewer.resources_loader", "get_current_language"
)

_PALETTE = [
    "#4da6ff", "#ff6b6b", "#51cf66", "#ffd43b",
    "#cc5de8", "#ff922b", "#20c997", "#f06595",
]

_C1_COLOR = "#ffa94d"   # cursor 1 — warm orange (not in graph palette)
_C2_COLOR = "#66d9e8"   # cursor 2 — light cyan  (not in graph palette)

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
_GRID     = "#2a2a42"
_BG       = _CARD_BG

# ── Branch arrow SVGs (written once to a temp dir for Qt stylesheet use) ─── #
def _make_branch_svgs(color: str = _TEXT2) -> tuple[str, str]:
    td = _tmp.mkdtemp(prefix="nv_viewer_")
    closed = _os.path.join(td, "br_c.svg").replace("\\", "/")
    opened = _os.path.join(td, "br_o.svg").replace("\\", "/")
    with open(closed, "w") as _f:
        _f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8">'
                 f'<polygon points="2,1 6,4 2,7" fill="{color}"/></svg>')
    with open(opened, "w") as _f:
        _f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8">'
                 f'<polygon points="1,2 7,2 4,6" fill="{color}"/></svg>')
    return closed, opened


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


def _make_signal_pixmap(size: int = 36, color: str = "#4da6ff") -> QPixmap:
    import math
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), size * 0.075)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    path = QPainterPath()
    steps, margin, amp = 120, size * 0.08, size * 0.36
    cy = size / 2.0
    w = size - 2 * margin
    for i in range(steps + 1):
        t = i / steps
        x = margin + t * w
        y = cy - amp * math.sin(t * 2 * math.pi)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    p.drawPath(path)
    p.end()
    return px


# ─────────────────────────────────────────────────────────────────────────── #
class MeasurementViewerWindow(QMainWindow):

    # Style strings are set as instance attributes in _load_theme_colors()
    _SEG_ACTIVE  = ""
    _SEG_INACTIVE = ""
    _ACTION_BTN  = ""

    def __init__(self, vna_device=None, source_module: str = "menu", source_window=None, display_mode: str = None):
        super().__init__()
        self._vna           = vna_device
        self._source_module = source_module
        self._source_window = source_window
        self._display_mode  = display_mode if display_mode is not None else source_module
        self._cache: dict[str, _FileEntry] = {}
        self._color_map: dict[str, str]    = {}
        self._color_idx   = 0
        self._layout_mode  = 2
        self._param_mode   = "eps" if self._display_mode == "char" else "s11"  # "s11"|"s21"|"eps"|"split"
        self._display2     = "mag_phase"  # "mag_phase" | "real_imag"
        self._compare_mode = False        # False = single file, True = overlay
        self._freq_div     = 1e9          # current display divisor (updated in _redraw)
        self._freq_unit    = "GHz"
        self._data_freq_min: float | None = None   # Hz — set in _redraw
        self._data_freq_max: float | None = None
        self._snap_freqs:    np.ndarray | None = None  # sorted unique freqs in Hz
        self._last_readout_slot = {1: 0, 2: 0}    # slot last dragged per cursor
        self._cursor_enabled  = {1: False, 2: False}
        # Per-cursor, per-row frequency: _cursor_freq[n][row]  row 0=top, 1=bottom
        self._cursor_freq     = {1: [None]*4, 2: [None]*4}   # 4 slots (0-3)
        self._cursor_lines    = {(n,s): [] for n in (1,2) for s in range(4)}
        self._cursor_markers  = {(n,s): [] for n in (1,2) for s in range(4)}
        self._cursor_dragging = None   # (n, slot) or None
        self._cursors_linked  = False  # False = pairs independent; True = all sync
        self._blit_bg         = None   # saved background for fast cursor blitting
        self._y_autoscale     = [True] * 4   # per-chart autoscale flag
        self._y_range         = [(None, None)] * 4  # (ymin, ymax) when manual
        self._y_grid          = [True] * 4   # per-chart grid visibility

        self._load_theme_colors()
        self._texts: dict = _load_text("measurement_viewer.json") if _load_text else {}

        self.setWindowTitle(self._t("window_title", fallback="NanoVNA Toolkit — Measurement Viewer"))
        screen = QGuiApplication.primaryScreen().availableGeometry()
        W = min(1280, max(960, int(screen.width()  * 0.85)))
        H = min(780,  max(600, int(screen.height() * 0.82)))
        x = screen.x() + (screen.width()  - W) // 2
        y = screen.y() + (screen.height() - H) // 2
        self.setGeometry(x, y, W, H)
        self.setMinimumSize(800, 520)

        if apply_window_icon:
            apply_window_icon(self)
        if dark_light_config:
            dark_light_config(self)

        self._build_menu()
        self._build_ui()

    # ── Theme toggle ──────────────────────────────────────────────────────── #
    def _toggle_theme(self, btn):
        if _toggle_menu_dark_mode:
            _toggle_menu_dark_mode(self, btn)
        new_win = MeasurementViewerWindow(
            vna_device=self._vna,
            source_module=self._source_module,
            source_window=self._source_window,
            display_mode=self._display_mode,
        )
        new_win.show()
        self.close()

    # ── Menubar ───────────────────────────────────────────────────────────── #
    def _build_menu(self):
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar {{ background:{self._PANEL_BG}; color:{self._TEXT};"
            f" border-bottom:1px solid {self._BORDER}; }}"
            f" QMenuBar::item:selected {{ background:{self._ACCENT}; color:#ffffff; }}"
            f" QMenu {{ background:{self._PANEL_BG}; color:{self._TEXT};"
            f" border:1px solid {self._BORDER}; }}"
            f" QMenu::item:selected {{ background:{self._ACCENT}; color:#ffffff; }}"
        )
        file_menu = mb.addMenu(self._t("menu", "file", fallback="File"))
        clear_act = QAction(self._t("menu", "clear_selection", fallback="Clear Selection"), self)
        clear_act.triggered.connect(self._clear_selection)
        file_menu.addAction(clear_act)
        file_menu.addSeparator()
        if open_preferences_dialog:
            pref_act = QAction("⚙  " + self._t("menu", "preferences", fallback="Preferences…"), self)
            pref_act.triggered.connect(lambda: open_preferences_dialog(self))
            file_menu.addAction(pref_act)
            file_menu.addSeparator()
        _back_labels = {
            "dut":  self._t("menu", "back_to_dut",  fallback="← Back to DUT"),
            "char": self._t("menu", "back_to_char", fallback="← Back to Characterization"),
        }
        back_act = QAction(_back_labels.get(self._source_module, self._t("menu", "back_to_menu", fallback="← Back to Menu")), self)
        back_act.triggered.connect(self._go_back)
        file_menu.addAction(back_act)

        method_menu = mb.addMenu(self._t("menu", "method", fallback="Method"))
        dut_act = QAction(self._t("menu", "dut_measurement", fallback="↖  DUT Measurement"), self)
        dut_act.triggered.connect(self._go_to_dut)
        method_menu.addAction(dut_act)
        char_act = QAction(self._t("menu", "material_characterization", fallback="↖  Material Characterization"), self)
        char_act.triggered.connect(self._go_to_char)
        method_menu.addAction(char_act)

        help_menu = mb.addMenu(self._t("help_menu", "help", fallback="Help"))
        _lang = _get_current_language() if _get_current_language else "en"
        _readme = "README_VIEWER_ES.md" if _lang == "es" else "README_VIEWER.md"
        if _show_about_dialog:
            doc_act = QAction(self._t("help_menu", "documentation", fallback="Documentation…"), self)
            doc_act.triggered.connect(lambda: _show_about_dialog(
                self, language=_lang, readme_file=_readme))
            help_menu.addAction(doc_act)
            help_menu.addSeparator()
        if _show_app_about:
            about_act = QAction(self._t("help_menu", "about", fallback="About…"), self)
            about_act.triggered.connect(lambda: _show_app_about(self, lang=_lang))
            help_menu.addAction(about_act)

    # ── Root layout ───────────────────────────────────────────────────────── #
    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet(f"background:{self._WIN_BG}; color:{self._TEXT};")
        self.setCentralWidget(root)

        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        v.addWidget(self._build_header())

        hline = QFrame()
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setFixedHeight(1)
        hline.setStyleSheet(f"background:{self._BORDER};")
        v.addWidget(hline)

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        h = QHBoxLayout(content)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        h.addWidget(self._build_left_panel())

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFixedWidth(1)
        vline.setStyleSheet(f"background:{self._BORDER};")
        h.addWidget(vline)

        h.addWidget(self._build_chart_area(), stretch=1)
        v.addWidget(content, stretch=1)

    # ── Header ────────────────────────────────────────────────────────────── #
    def _build_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{self._WIN_BG};")
        hdr.setFixedHeight(130)
        h = QHBoxLayout(hdr)
        h.setContentsMargins(0, 12, 16, 8)
        h.setSpacing(0)

        # ── Left section: branding, fixed width matching left panel ────────── #
        brand = QWidget()
        brand.setFixedWidth(320)
        brand.setStyleSheet("background:transparent;")
        bh = QHBoxLayout(brand)
        bh.setContentsMargins(20, 0, 12, 0)
        bh.setSpacing(10)
        bh.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        icon_lbl = QLabel()
        icon_lbl.setStyleSheet("background:transparent;")
        icon_lbl.setPixmap(_make_signal_pixmap(36, "#4da6ff"))
        bh.addWidget(icon_lbl)
        tcol = QWidget()
        tcol.setStyleSheet("background:transparent;")
        tv = QVBoxLayout(tcol)
        tv.setContentsMargins(0, 0, 0, 0)
        tv.setSpacing(0)
        t1 = QLabel(self._t("header", "title", fallback="Measurement Viewer"))
        t1.setStyleSheet(
            f"font-size:14px; font-weight:bold; color:{self._TEXT}; background:transparent;"
            " margin:0; padding:0;")
        t1.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        t1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        t2 = QLabel(self._t("header", "subtitle", fallback="Compare and inspect measurement files"))
        t2.setStyleSheet(
            f"font-size:10px; color:{self._TEXT2}; background:transparent;"
            " margin:0; padding:0;")
        t2.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        t2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tv.addWidget(t1)
        tv.addWidget(t2)
        bh.addWidget(tcol)
        h.addWidget(brand)

        # ── Right section: ONE card containing tabs + content ─────────────── #
        chart_hdr = QWidget()
        chart_hdr.setObjectName("chart_hdr_card")
        chart_hdr.setStyleSheet(
            f"QWidget#chart_hdr_card {{ background:{self._PANEL_BG};"
            f" border:1px solid {self._BORDER}; border-radius:8px; }}"
        )
        cv = QVBoxLayout(chart_hdr)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        h.addWidget(chart_hdr, stretch=1)

        # ── Tab bar (top of card) ────────────────────────────────────────────── #
        _TAB_ACTIVE = (
            f"QPushButton {{ font-size:11px; font-weight:600; padding:5px 18px;"
            f" border:none; background:{self._ACCENT}; color:#ffffff; border-radius:6px; }}"
        )
        _TAB_INACTIVE = (
            f"QPushButton {{ font-size:11px; font-weight:500; padding:5px 18px;"
            f" border:none; background:transparent; color:{self._TEXT2}; border-radius:6px; }}"
            f" QPushButton:hover {{ color:{self._TEXT}; background:{self._BORDER}; }}"
        )
        tab_bar_w = QWidget()
        tab_bar_w.setStyleSheet("background:transparent;")
        tab_row = QHBoxLayout(tab_bar_w)
        tab_row.setContentsMargins(12, 8, 12, 6)
        tab_row.setSpacing(4)
        tab_row.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self._tab_btns: list[QPushButton] = []
        for i, (icon, name) in enumerate((
            ("∿", self._t("tabs", "graphics", fallback="Graphics")),
            ("⊕", self._t("tabs", "cursors",  fallback="Cursors")),
            ("⇔", self._t("tabs", "range",    fallback="Range")),
            ("↓", self._t("tabs", "export",   fallback="Export")),
        )):
            btn = QPushButton(f"{icon}  {name}")
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, idx=i: self._set_tab(idx))
            self._tab_btns.append(btn)
            tab_row.addWidget(btn)
        cv.addWidget(tab_bar_w)

        # Separator line between tabs and content
        hsep = QFrame()
        hsep.setFrameShape(QFrame.Shape.HLine)
        hsep.setFixedHeight(1)
        hsep.setStyleSheet(f"background:{self._BORDER}; border:none;")
        cv.addWidget(hsep)

        # ── Tab content stack ────────────────────────────────────────────────── #
        self._tab_stack = QStackedWidget()
        self._tab_stack.setStyleSheet("background:transparent;")
        cv.addWidget(self._tab_stack, stretch=1)

        # ── Page 0 — Graphics ───────────────────────────────────────────────── #
        graphics_page = QWidget()
        graphics_page.setStyleSheet("background:transparent;")
        gph = QHBoxLayout(graphics_page)
        gph.setContentsMargins(16, 0, 16, 0)
        gph.setSpacing(0)
        # Left half — Layout (right-aligned so Parameter stays centered)
        left_w = QWidget(); left_w.setStyleSheet("background:transparent;")
        left_h = QHBoxLayout(left_w); left_h.setContentsMargins(16,0,0,0); left_h.setSpacing(0)
        self._btn_2 = QPushButton(self._t("graphics", "charts_2", fallback="2 charts"))
        self._btn_2.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_2.clicked.connect(lambda: self._set_layout(2))
        self._btn_4 = QPushButton(self._t("graphics", "charts_4", fallback="4 charts"))
        self._btn_4.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_4.clicked.connect(lambda: self._set_layout(4))
        self._update_layout_buttons()
        left_h.addStretch(1)
        left_h.addWidget(self._labeled_seg(self._t("graphics", "layout", fallback="Layout"), self._btn_2, self._btn_4))
        left_h.addSpacing(20)
        left_h.addWidget(self._vsep())

        # Center — Parameter (pinned to exact middle)
        self._btn_p2_s11 = QPushButton("S11")
        self._btn_p2_s11.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_p2_s11.clicked.connect(lambda: self._set_param("s11"))
        _p2_s21_label = "ε" if self._display_mode == "char" else "S21"
        _p2_s21_param = "eps" if self._display_mode == "char" else "s21"
        self._btn_p2_s21 = QPushButton(_p2_s21_label)
        self._btn_p2_s21.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_p2_s21.clicked.connect(lambda: self._set_param(_p2_s21_param))
        if self._display_mode == "char":
            self._grp_param2 = self._labeled_seg(self._t("graphics", "parameter", fallback="Parameter"), self._btn_p2_s21, self._btn_p2_s11)
        else:
            self._grp_param2 = self._labeled_seg(self._t("graphics", "parameter", fallback="Parameter"), self._btn_p2_s11, self._btn_p2_s21)

        self._btn_p4_s11 = QPushButton("S11")
        self._btn_p4_s11.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_p4_s11.clicked.connect(self._toggle_p4_s11)
        _p4_s21_label = "ε" if self._display_mode == "char" else "S21"
        self._btn_p4_s21 = QPushButton(_p4_s21_label)
        self._btn_p4_s21.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_p4_s21.clicked.connect(self._toggle_p4_s21)
        self._grp_param4 = self._labeled_seg(self._t("graphics", "parameter", fallback="Parameter"), self._btn_p4_s21, self._btn_p4_s11)

        self._param_stack = QStackedWidget()
        self._param_stack.addWidget(self._grp_param2)
        self._param_stack.addWidget(self._grp_param4)
        self._param_stack.setStyleSheet("background:transparent;")
        self._param_stack.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        # Right half — Display (left-aligned, mirror of left)
        right_w = QWidget(); right_w.setStyleSheet("background:transparent;")
        right_h = QHBoxLayout(right_w); right_h.setContentsMargins(0,0,16,0); right_h.setSpacing(0)
        self._btn_mag_ph = QPushButton(self._t("graphics", "mag_phase", fallback="Mag+Phase"))
        self._btn_mag_ph.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_mag_ph.clicked.connect(lambda: self._set_display2("mag_phase"))
        self._btn_re_im = QPushButton(self._t("graphics", "real_imag", fallback="Real+Imag"))
        self._btn_re_im.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_re_im.clicked.connect(lambda: self._set_display2("real_imag"))
        self._grp_display2 = self._labeled_seg(self._t("graphics", "display", fallback="Display"), self._btn_mag_ph, self._btn_re_im)
        right_h.addWidget(self._vsep())
        right_h.addSpacing(20)
        right_h.addWidget(self._grp_display2)
        right_h.addStretch(1)
        self._update_display2_buttons()

        gph.addWidget(left_w, 1)
        gph.addSpacing(20)
        gph.addWidget(self._param_stack, 0)
        gph.addSpacing(20)
        gph.addWidget(right_w, 1)

        self._update_param_buttons()
        self._update_header_groups()
        self._tab_stack.addWidget(graphics_page)

        # ── Page 1 — Cursors ────────────────────────────────────────────────── #
        cursors_page = QWidget()
        cursors_page.setStyleSheet("background:transparent;")
        cph = QHBoxLayout(cursors_page)
        cph.setContentsMargins(12, 0, 12, 0)
        cph.setSpacing(0)

        def _csep() -> QFrame:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setFixedWidth(1)
            sep.setStyleSheet(f"background:{self._BORDER}; border:none;")
            return sep

        def _cap_lbl(text: str) -> QLabel:
            l = QLabel(text)
            l.setStyleSheet(f"color:{self._TEXT2}; background:transparent; font-size:9px;")
            return l

        def _val_lbl() -> QLabel:
            l = QLabel("—")
            l.setStyleSheet(f"color:{self._TEXT}; background:transparent; font-size:11px; font-weight:500;")
            return l

        # ── cursor button styles ─────────────────────────────────────────────── #
        _C1_ON  = (f"QPushButton {{ font-size:11px; font-weight:600; padding:2px 10px;"
                   f" border:none; background:{_C1_COLOR}; color:#0a0a14;"
                   f" border-radius:5px; }}")
        _C2_ON  = (f"QPushButton {{ font-size:11px; font-weight:600; padding:2px 10px;"
                   f" border:none; background:{_C2_COLOR}; color:#0a0a14;"
                   f" border-radius:5px; }}")
        _CX_OFF = (f"QPushButton {{ font-size:11px; padding:2px 10px;"
                   f" border:1px solid {self._BORDER}; background:transparent;"
                   f" color:{self._TEXT2}; border-radius:5px; }}"
                   f" QPushButton:hover {{ background:{self._BORDER}; color:{self._TEXT}; }}")
        _CX_DIS = (f"QPushButton {{ font-size:11px; padding:2px 10px;"
                   f" border:1px solid {self._BORDER}; background:transparent;"
                   f" color:#44445a; border-radius:5px; }}")
        self._C1_ON_STYLE   = _C1_ON
        self._C2_ON_STYLE   = _C2_ON
        self._CX_OFF_STYLE  = _CX_OFF
        self._CX_DIS_STYLE  = _CX_DIS

        # ── C1 section ───────────────────────────────────────────────────────── #
        c1_sec = QWidget()
        c1_sec.setStyleSheet("background:transparent;")
        c1v = QVBoxLayout(c1_sec)
        c1v.setContentsMargins(14, 4, 14, 4)
        c1v.setSpacing(4)
        c1h = QHBoxLayout()
        c1h.setSpacing(6)
        c1_dot = QLabel("●")
        c1_dot.setStyleSheet(f"color:{_C1_COLOR}; background:transparent; font-size:10px;")
        c1_title = QLabel(self._t("cursors", "cursor_1", fallback="Cursor 1"))
        c1_title.setStyleSheet(f"color:{self._TEXT}; background:transparent; font-size:10px; font-weight:600;")
        self._btn_c1 = QPushButton("C1")
        self._btn_c1.setFixedHeight(22)
        self._btn_c1.setFixedWidth(38)
        self._btn_c1.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_c1.clicked.connect(lambda: self._toggle_cursor(1))
        c1h.addWidget(c1_dot)
        c1h.addWidget(c1_title)
        c1h.addStretch(1)
        c1h.addWidget(self._btn_c1)
        c1v.addLayout(c1h)
        c1d = QHBoxLayout()
        c1d.setSpacing(8)
        c1d.setContentsMargins(0, 0, 0, 0)
        self._lbl_c1_freq = _val_lbl()
        _fw = QWidget(); _fw.setStyleSheet("background:transparent;")
        _fv = QVBoxLayout(_fw); _fv.setContentsMargins(0,0,0,0); _fv.setSpacing(1)
        _fv.addWidget(_cap_lbl(self._t("cursors", "freq", fallback="Freq"))); _fv.addWidget(self._lbl_c1_freq)
        c1d.addWidget(_fw)
        self._c1_vcols: list[tuple] = []
        for _i in range(4):
            _cap = _cap_lbl("—"); _val = _val_lbl()
            _cw = QWidget(); _cw.setStyleSheet("background:transparent;")
            _cv = QVBoxLayout(_cw); _cv.setContentsMargins(0,0,0,0); _cv.setSpacing(1)
            _cv.addWidget(_cap); _cv.addWidget(_val)
            c1d.addWidget(_cw)
            if _i >= 2:
                _cw.hide()
            self._c1_vcols.append((_cw, _cap, _val))
        c1v.addLayout(c1d)
        cph.addWidget(c1_sec, stretch=2)

        cph.addWidget(_csep())

        # ── C2 section ───────────────────────────────────────────────────────── #
        c2_sec = QWidget()
        c2_sec.setStyleSheet("background:transparent;")
        c2v = QVBoxLayout(c2_sec)
        c2v.setContentsMargins(14, 4, 14, 4)
        c2v.setSpacing(4)
        c2h = QHBoxLayout()
        c2h.setSpacing(6)
        c2_dot = QLabel("●")
        c2_dot.setStyleSheet(f"color:{_C2_COLOR}; background:transparent; font-size:10px;")
        c2_title = QLabel(self._t("cursors", "cursor_2", fallback="Cursor 2"))
        c2_title.setStyleSheet(f"color:{self._TEXT}; background:transparent; font-size:10px; font-weight:600;")
        self._btn_c2 = QPushButton("C2")
        self._btn_c2.setFixedHeight(22)
        self._btn_c2.setFixedWidth(38)
        self._btn_c2.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_c2.clicked.connect(lambda: self._toggle_cursor(2))
        c2h.addWidget(c2_dot)
        c2h.addWidget(c2_title)
        c2h.addStretch(1)
        c2h.addWidget(self._btn_c2)
        c2v.addLayout(c2h)
        c2d = QHBoxLayout()
        c2d.setSpacing(8)
        c2d.setContentsMargins(0, 0, 0, 0)
        self._lbl_c2_freq = _val_lbl()
        _fw = QWidget(); _fw.setStyleSheet("background:transparent;")
        _fv = QVBoxLayout(_fw); _fv.setContentsMargins(0,0,0,0); _fv.setSpacing(1)
        _fv.addWidget(_cap_lbl(self._t("cursors", "freq", fallback="Freq"))); _fv.addWidget(self._lbl_c2_freq)
        c2d.addWidget(_fw)
        self._c2_vcols: list[tuple] = []
        for _i in range(4):
            _cap = _cap_lbl("—"); _val = _val_lbl()
            _cw = QWidget(); _cw.setStyleSheet("background:transparent;")
            _cv = QVBoxLayout(_cw); _cv.setContentsMargins(0,0,0,0); _cv.setSpacing(1)
            _cv.addWidget(_cap); _cv.addWidget(_val)
            c2d.addWidget(_cw)
            if _i >= 2:
                _cw.hide()
            self._c2_vcols.append((_cw, _cap, _val))
        c2v.addLayout(c2d)
        cph.addWidget(c2_sec, stretch=2)

        cph.addWidget(_csep())

        # ── Delta section ────────────────────────────────────────────────────── #
        df_sec = QWidget()
        df_sec.setStyleSheet("background:transparent;")
        dfv = QVBoxLayout(df_sec)
        dfv.setContentsMargins(14, 4, 14, 4)
        dfv.setSpacing(4)
        df_title = QLabel(self._t("cursors", "delta_title", fallback="Δ  (C2 − C1)"))
        df_title.setStyleSheet(f"color:{self._TEXT2}; background:transparent; font-size:10px; font-weight:600;")
        dfv.addWidget(df_title)
        dfd = QHBoxLayout()
        dfd.setSpacing(8)
        dfd.setContentsMargins(0, 0, 0, 0)
        self._lbl_df = _val_lbl()
        _fw = QWidget(); _fw.setStyleSheet("background:transparent;")
        _fv = QVBoxLayout(_fw); _fv.setContentsMargins(0,0,0,0); _fv.setSpacing(1)
        _fv.addWidget(_cap_lbl(self._t("cursors", "delta_freq", fallback="ΔF"))); _fv.addWidget(self._lbl_df)
        dfd.addWidget(_fw)
        self._df_vcols: list[tuple] = []
        for _i in range(4):
            _cap = _cap_lbl("—"); _val = _val_lbl()
            _cw = QWidget(); _cw.setStyleSheet("background:transparent;")
            _cv = QVBoxLayout(_cw); _cv.setContentsMargins(0,0,0,0); _cv.setSpacing(1)
            _cv.addWidget(_cap); _cv.addWidget(_val)
            dfd.addWidget(_cw)
            if _i >= 2:
                _cw.hide()
            self._df_vcols.append((_cw, _cap, _val))
        dfv.addLayout(dfd)
        cph.addWidget(df_sec, stretch=2)

        cph.addWidget(_csep())

        # ── Linked section ───────────────────────────────────────────────────── #
        lnk_sec = QWidget()
        lnk_sec.setStyleSheet("background:transparent;")
        lnkv = QVBoxLayout(lnk_sec)
        lnkv.setContentsMargins(14, 4, 14, 4)
        lnkv.setSpacing(4)
        lnkv.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        lnk_title_row = QHBoxLayout()
        lnk_title_row.setSpacing(6)
        lnk_icon = QLabel("⇔")
        lnk_icon.setStyleSheet(f"color:{self._TEXT2}; background:transparent; font-size:12px;")
        lnk_lbl = QLabel(self._t("cursors", "linked", fallback="Linked"))
        lnk_lbl.setStyleSheet(f"color:{self._TEXT}; background:transparent; font-size:10px; font-weight:600;")
        lnk_title_row.addWidget(lnk_icon)
        lnk_title_row.addWidget(lnk_lbl)
        lnk_title_row.addStretch(1)
        lnkv.addLayout(lnk_title_row)
        self._btn_linked = QPushButton("ON")
        self._btn_linked.setFixedHeight(24)
        self._btn_linked.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_linked.clicked.connect(self._toggle_cursors_linked)
        lnkv.addWidget(self._btn_linked)
        self._update_linked_buttons()
        cph.addWidget(lnk_sec, stretch=1)

        self._update_cursor_buttons()
        self._tab_stack.addWidget(cursors_page)

        # ── Page 2 — Range ───────────────────────────────────────────────────── #
        range_page = QWidget()
        range_page.setStyleSheet("background:transparent;")
        rph = QHBoxLayout(range_page)
        rph.setContentsMargins(12, 0, 12, 0)
        rph.setSpacing(0)

        _RNG_ON  = (f"QPushButton {{ font-size:11px; font-weight:600; padding:2px 9px;"
                    f" border:none; background:{self._ACCENT}; color:#ffffff; border-radius:4px; }}"
                    f" QPushButton:hover {{ background:{self._ACCENT_H}; }}")
        _RNG_OFF = (f"QPushButton {{ font-size:11px; padding:2px 9px;"
                    f" border:1px solid {self._BORDER}; background:transparent;"
                    f" color:{self._TEXT2}; border-radius:4px; }}"
                    f" QPushButton:hover {{ background:{self._BORDER}; color:{self._TEXT}; }}")
        _RNG_IN  = (f"QLineEdit {{ font-size:11px; padding:2px 5px; border-radius:3px;"
                    f" border:1px solid {self._BORDER}; background:{self._CARD_BG}; color:{self._TEXT}; }}"
                    f" QLineEdit:focus {{ border-color:{self._ACCENT}; }}"
                    f" QLineEdit:disabled {{ color:#44445a; background:#1a1a2e; border-color:#2a2a42; }}")
        self._RNG_ON_STYLE  = _RNG_ON
        self._RNG_OFF_STYLE = _RNG_OFF

        def _rsep() -> QFrame:
            s = QFrame(); s.setFrameShape(QFrame.Shape.VLine)
            s.setFixedWidth(1); s.setStyleSheet(f"background:{self._BORDER}; border:none;")
            return s

        self._range_sections: list[dict] = []
        for _i in range(4):
            _sec = QWidget(); _sec.setStyleSheet("background:transparent;")
            _secv = QVBoxLayout(_sec)
            _secv.setContentsMargins(12, 5, 12, 5)
            _secv.setSpacing(4)

            # Row 1: label + Auto + Grid
            _r1 = QHBoxLayout(); _r1.setSpacing(4); _r1.setContentsMargins(0,0,0,0)
            _chart_lbl = QLabel("—")
            _chart_lbl.setStyleSheet(f"color:{self._TEXT}; background:transparent; font-size:11px; font-weight:500;")
            _chart_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            _btn_auto = QPushButton(self._t("range", "auto", fallback="Auto"))
            _btn_auto.setFixedSize(52, 23)
            _btn_auto.setCursor(Qt.CursorShape.PointingHandCursor)
            _btn_grid = QPushButton(self._t("range", "grid", fallback="Grid"))
            _btn_grid.setFixedSize(48, 23)
            _btn_grid.setCursor(Qt.CursorShape.PointingHandCursor)
            _r1.addWidget(_chart_lbl)
            _r1.addWidget(_btn_auto)
            _r1.addSpacing(2)
            _r1.addWidget(_btn_grid)
            _secv.addLayout(_r1)

            # Row 2: Ymin / Ymax inputs
            _r2 = QHBoxLayout(); _r2.setSpacing(4); _r2.setContentsMargins(0,0,0,0)
            _lbl_min = QLabel(self._t("range", "y_min", fallback="Y min"))
            _lbl_min.setStyleSheet(f"color:{self._TEXT2}; background:transparent; font-size:10px;")
            _edit_min = QLineEdit(); _edit_min.setFixedHeight(23); _edit_min.setStyleSheet(_RNG_IN)
            _edit_min.setPlaceholderText("auto"); _edit_min.setEnabled(False)
            _lbl_max = QLabel(self._t("range", "y_max", fallback="max"))
            _lbl_max.setStyleSheet(f"color:{self._TEXT2}; background:transparent; font-size:10px;")
            _edit_max = QLineEdit(); _edit_max.setFixedHeight(23); _edit_max.setStyleSheet(_RNG_IN)
            _edit_max.setPlaceholderText("auto"); _edit_max.setEnabled(False)
            _r2.addWidget(_lbl_min)
            _r2.addWidget(_edit_min, 1)
            _r2.addSpacing(2)
            _r2.addWidget(_lbl_max)
            _r2.addWidget(_edit_max, 1)
            _secv.addLayout(_r2)

            _n = _i
            _btn_auto.clicked.connect(lambda _, n=_n: self._toggle_y_autoscale(n))
            _btn_grid.clicked.connect(lambda _, n=_n: self._toggle_y_grid(n))
            _edit_min.editingFinished.connect(lambda n=_n: self._apply_y_range(n))
            _edit_max.editingFinished.connect(lambda n=_n: self._apply_y_range(n))

            _sep_widget = None
            if _i > 0:
                _sep_widget = _rsep()
                rph.addWidget(_sep_widget)
            rph.addWidget(_sec, 1)

            if _i >= 2:
                _sec.hide()
                if _sep_widget is not None:
                    _sep_widget.hide()

            self._range_sections.append({
                "container": _sec,
                "sep":       _sep_widget,
                "label":     _chart_lbl,
                "btn_auto":  _btn_auto,
                "btn_grid":  _btn_grid,
                "edit_min":  _edit_min,
                "edit_max":  _edit_max,
            })

        self._tab_stack.addWidget(range_page)

        # ── Page 3 — Export ─────────────────────────────────────────────────── #
        export_page = QWidget()
        export_page.setStyleSheet("background:transparent;")
        eph = QHBoxLayout(export_page)
        eph.setContentsMargins(12, 0, 12, 0)
        eph.setSpacing(0)

        _EXP_ACT = (f"QPushButton {{ font-size:10px; font-weight:600; padding:2px 9px;"
                    f" border:none; background:{self._ACCENT}; color:#ffffff; border-radius:4px; }}"
                    f" QPushButton:hover {{ background:{self._ACCENT_H}; }}")
        _EXP_OFF = (f"QPushButton {{ font-size:10px; padding:2px 9px;"
                    f" border:1px solid {self._BORDER}; background:transparent;"
                    f" color:{self._TEXT2}; border-radius:4px; }}"
                    f" QPushButton:hover {{ background:{self._BORDER}; color:{self._TEXT}; }}")
        _EXP_GO  = (f"QPushButton {{ font-size:10px; font-weight:600; padding:2px 10px;"
                    f" border:1px solid {self._BORDER}; background:transparent;"
                    f" color:{self._TEXT}; border-radius:4px; }}"
                    f" QPushButton:hover {{ background:{self._BORDER}; }}")
        self._EXP_ACT_STYLE = _EXP_ACT
        self._EXP_OFF_STYLE = _EXP_OFF

        def _exp_sep():
            s = QFrame(); s.setFrameShape(QFrame.Shape.VLine)
            s.setFixedWidth(1); s.setStyleSheet(f"background:{self._BORDER}; border:none;")
            return s

        def _exp_section(label_text, *btns):
            w = QWidget(); w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w); v.setContentsMargins(12, 5, 12, 5); v.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color:{self._TEXT}; background:transparent; font-size:11px; font-weight:600;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            v.addWidget(lbl)
            row = QHBoxLayout(); row.setSpacing(4); row.setContentsMargins(0,0,0,0)
            for b in btns:
                b.setFixedHeight(22)
                row.addWidget(b)
            v.addLayout(row)
            return w

        # ── Format + DPI ─────────────────────────────────────────────────────── #
        self._export_fmt = "png"
        self._export_dpi = QLineEdit("150")
        self._export_dpi.setFixedSize(42, 22)
        self._export_dpi.setStyleSheet(
            f"QLineEdit {{ font-size:10px; padding:1px 4px; border-radius:3px;"
            f" border:1px solid {self._BORDER}; background:{self._CARD_BG}; color:{self._TEXT}; }}")
        dpi_w = QWidget(); dpi_w.setStyleSheet("background:transparent;")
        dpi_v = QVBoxLayout(dpi_w)
        dpi_v.setContentsMargins(12, 5, 12, 5); dpi_v.setSpacing(4)
        dpi_lbl2 = QLabel(self._t("export", "dpi", fallback="DPI"))
        dpi_lbl2.setStyleSheet(f"color:{self._TEXT2}; background:transparent; font-size:9px; font-weight:600;")
        dpi_v.addWidget(dpi_lbl2)
        dpi_v.addWidget(self._export_dpi)
        eph.addWidget(dpi_w)

        eph.addWidget(_exp_sep())

        # ── Individual ───────────────────────────────────────────────────────── #
        def _ebt(label, mode):
            b = QPushButton(label); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(_EXP_GO)
            b.clicked.connect(lambda _=False, m=mode: self._run_export(m))
            return b
        eph.addWidget(_exp_section(self._t("export", "individual", fallback="Individual"),
            _ebt(self._t("export", "mag_db",    fallback="Mag [dB]"),  "ind_mag"),
            _ebt(self._t("export", "phase_deg", fallback="Phase [°]"), "ind_phase"),
            _ebt(self._t("export", "real",      fallback="Real"),      "ind_real"),
            _ebt(self._t("export", "imag",      fallback="Imag"),      "ind_imag"),
        ), stretch=2)

        eph.addWidget(_exp_sep())

        # ── Pairs ─────────────────────────────────────────────────────────────── #
        eph.addWidget(_exp_section(self._t("export", "pairs", fallback="Pairs"),
            _ebt(self._t("export", "mag_phase_pair",  fallback="Mag + Phase"), "pair_mp"),
            _ebt(self._t("export", "real_imag_pair",  fallback="Real + Imag"), "pair_ri"),
        ), stretch=1)

        eph.addWidget(_exp_sep())

        # ── 4-chart ───────────────────────────────────────────────────────────── #
        _4ch_s21_btn = _ebt("S21", "4ch_s21")
        if self._display_mode == "char":
            _4ch_s21_btn.hide()
        eph.addWidget(_exp_section(self._t("export", "four_chart", fallback="4-chart"),
            _ebt("S11", "4ch_s11"),
            _4ch_s21_btn,
        ), stretch=1)

        self._tab_stack.addWidget(export_page)

        self._tab_idx = 0
        self._tab_stack.setCurrentIndex(0)
        self._update_tab_buttons(_TAB_ACTIVE, _TAB_INACTIVE)

        # store styles for _set_tab
        self._TAB_ACTIVE   = _TAB_ACTIVE
        self._TAB_INACTIVE = _TAB_INACTIVE

        self._update_range_page()
        return hdr

    def _t(self, *keys: str, fallback: str = "") -> str:
        """Look up a translation key path in self._texts."""
        d = self._texts
        for k in keys:
            if not isinstance(d, dict):
                return fallback
            d = d.get(k, {})
        return d if isinstance(d, str) else fallback

    def _load_theme_colors(self):
        """Read dark/light mode from INI and set all color instance variables."""
        is_dark = True  # dark by default
        if _get_settings is not None:
            try:
                _s = _get_settings(
                    "INI/dut_measurement/dark_light_config/dark_light_config.ini",
                    "shared/utils/dark_light_mode/dark_light_config.ini",
                    Path(__file__).resolve(),
                )
                # is_dark_mode=False → dark active; True → light active
                is_dark = not _s.value("Dark_Light/is_dark_mode", False, type=bool)
            except Exception:
                pass

        if is_dark:
            self._WIN_BG   = "#1e1e2e"
            self._PANEL_BG = "#252538"
            self._BORDER   = "#383850"
            self._CARD_BG  = "#12121e"
            self._SPINE    = "#2a2a42"
            self._ACCENT   = "#2d5a8e"
            self._ACCENT_H = "#3a6fa0"
            self._TEXT     = "#ffffff"
            self._TEXT2    = "#8888aa"
            self._GRID     = "#2a2a42"
        else:
            self._WIN_BG   = "#f0f0f5"
            self._PANEL_BG = "#ffffff"
            self._BORDER   = "#d0d0e0"
            self._CARD_BG  = "#e8e8f4"
            self._SPINE    = "#c0c0cc"
            self._ACCENT   = "#2d5a8e"
            self._ACCENT_H = "#3a6fa0"
            self._TEXT     = "#1a1a2e"
            self._TEXT2    = "#5555aa"
            self._GRID     = "#d0d0e0"

        self._BG = self._CARD_BG
        self._BR_CLOSED, self._BR_OPEN = _make_branch_svgs(self._TEXT2)

        # Button label: "Light Mode 🔆" (currently dark) or "Dark Mode 🌙" (currently light)
        self._theme_btn_text = "Dark Mode 🌙" if is_dark else "Light Mode 🔆"

        self._SEG_ACTIVE = (
            f"QPushButton {{ font-size:11px; padding:3px 14px;"
            f" border:1px solid {self._ACCENT};"
            f" background:{self._ACCENT}; color:#ffffff; border-radius:5px; }}"
            f" QPushButton:hover {{ background:{self._ACCENT_H}; border-color:{self._ACCENT_H}; }}"
        )
        self._SEG_INACTIVE = (
            f"QPushButton {{ font-size:11px; padding:3px 14px;"
            f" border:1px solid {self._BORDER};"
            f" background:{self._PANEL_BG}; color:{self._TEXT2}; border-radius:5px; }}"
            f" QPushButton:hover {{ background:{self._BORDER}; color:{self._TEXT}; }}"
        )
        self._ACTION_BTN = (
            f"QPushButton {{ font-size:11px; padding:4px 14px; border-radius:6px;"
            f" border:1px solid {self._BORDER}; background:transparent; color:{self._TEXT2}; }}"
            f" QPushButton:hover {{ background:{self._BORDER}; color:{self._TEXT}; }}"
        )

    def _vsep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setFixedHeight(48)
        sep.setStyleSheet(f"background:{self._BORDER};")
        return sep

    def _labeled_seg(self, label: str, *buttons) -> QWidget:
        """Labeled segmented-pill group: label above, pill container below."""
        grp = QWidget()
        grp.setStyleSheet("background:transparent;")
        gv = QVBoxLayout(grp)
        gv.setContentsMargins(0, 6, 0, 6)
        gv.setSpacing(5)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size:10px; color:{self._TEXT2}; background:transparent;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        gv.addWidget(lbl)

        pill = QWidget()
        pill.setStyleSheet("QWidget { background:transparent; }")
        pl = QHBoxLayout(pill)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        for btn in buttons:
            btn.setFixedHeight(32)
            pl.addWidget(btn)
        gv.addWidget(pill)
        return grp

    # ── Left panel ────────────────────────────────────────────────────────── #
    def _build_left_panel(self) -> QWidget:
        left = QWidget()
        left.setStyleSheet(f"background:{self._PANEL_BG};")
        left.setFixedWidth(320)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 14, 12, 12)
        lv.setSpacing(8)

        # Header row
        hrow = QHBoxLayout()
        hrow.setContentsMargins(0, 0, 0, 0)
        fl = QLabel(self._t("files_panel", "title", fallback="Measurement files"))
        fl.setStyleSheet(
            f"font-size:12px; font-weight:bold; color:{self._TEXT}; background:transparent;")
        hrow.addWidget(fl)
        hrow.addStretch()
        self._badge = QLabel(self._t("files_panel", "badge_files", fallback="{n} files").replace("{n}", "0"))
        self._badge.setStyleSheet(
            f"font-size:10px; color:{self._TEXT2}; background:{self._BORDER};"
            " border-radius:8px; padding:1px 7px;")
        hrow.addWidget(self._badge)
        lv.addLayout(hrow)

        # Single / Compare toggle
        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(0)
        _MODE_ACCENT   = "#4a7fc1"   # slightly lighter/more vivid than Add files
        _MODE_ACCENT_H = "#5a8fd1"
        _MODE_ON  = (
            f"QPushButton {{ font-size:12px; font-weight:600;"
            f" background:{_MODE_ACCENT}; color:#ffffff; border:none; }}"
            f" QPushButton:hover {{ background:{_MODE_ACCENT_H}; }}"
        )
        _MODE_OFF = (
            f"QPushButton {{ font-size:12px; font-weight:500;"
            f" background:{self._PANEL_BG}; color:{self._TEXT2}; border:none; }}"
            f" QPushButton:hover {{ background:{self._BORDER}; color:{self._TEXT}; }}"
        )
        self._MODE_ON_STYLE  = _MODE_ON
        self._MODE_OFF_STYLE = _MODE_OFF

        self._btn_single = QPushButton(self._t("files_panel", "single", fallback="Single"))
        self._btn_single.setFixedHeight(34)
        self._btn_single.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_single.clicked.connect(lambda: self._set_compare_mode(False))
        self._btn_compare = QPushButton(self._t("files_panel", "compare", fallback="Compare"))
        self._btn_compare.setFixedHeight(34)
        self._btn_compare.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_compare.clicked.connect(lambda: self._set_compare_mode(True))

        # Segmented control container — rounded outer corners only
        seg_mode = QWidget()
        seg_mode.setStyleSheet(
            f"QWidget {{ background:{self._PANEL_BG}; border:1px solid {self._BORDER};"
            f" border-radius:7px; }}"
        )
        seg_mode.setFixedHeight(36)
        sm = QHBoxLayout(seg_mode)
        sm.setContentsMargins(1, 1, 1, 1)
        sm.setSpacing(0)

        sm.addWidget(self._btn_single, stretch=1)
        sm.addWidget(self._btn_compare, stretch=1)
        mode_row.addWidget(seg_mode, stretch=1)
        self._update_compare_buttons()
        lv.addLayout(mode_row)

        # Buttons
        brow = QHBoxLayout()
        brow.setContentsMargins(0, 0, 0, 0)
        brow.setSpacing(6)

        add_files = QPushButton(self._t("files_panel", "add_files", fallback="+ Add files"))
        add_files.setFixedHeight(36)
        add_files.setCursor(Qt.CursorShape.PointingHandCursor)
        add_files.setStyleSheet(
            f"QPushButton {{ font-size:12px; background:{self._ACCENT}; color:white;"
            f" border:1px solid {self._ACCENT}; border-radius:6px; }}"
            f" QPushButton:hover {{ background:{self._ACCENT_H}; border-color:{self._ACCENT_H}; }}"
        )
        add_files.clicked.connect(self._add_files)
        brow.addWidget(add_files)

        add_folder = QPushButton(self._t("files_panel", "add_folder", fallback="Add folder"))
        add_folder.setFixedHeight(36)
        add_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder.setStyleSheet(
            f"QPushButton {{ font-size:12px; background:{self._PANEL_BG}; color:{self._TEXT2};"
            f" border:1px solid {self._BORDER}; border-radius:6px; }}"
            f" QPushButton:hover {{ background:{self._BORDER}; color:{self._TEXT}; }}"
        )
        add_folder.clicked.connect(self._browse_folder)
        brow.addWidget(add_folder)
        lv.addLayout(brow)

        # Filter
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText(self._t("files_panel", "filter_placeholder", fallback="Filter files…"))
        self._filter_edit.setFixedHeight(30)
        self._filter_edit.setStyleSheet(
            f"QLineEdit {{ background:{self._PANEL_BG}; color:{self._TEXT}; border:1px solid {self._BORDER};"
            " border-radius:5px; padding:0 8px; font-size:11px; }"
            f" QLineEdit:focus {{ border-color:{self._ACCENT}; }}"
        )
        self._filter_edit.textChanged.connect(self._apply_filter)
        lv.addWidget(self._filter_edit)

        # Separator — always visible between filter and list
        _fsep = QFrame()
        _fsep.setFrameShape(QFrame.Shape.HLine)
        _fsep.setFixedHeight(1)
        _fsep.setStyleSheet(f"background:{self._BORDER}; border:none;")
        lv.addWidget(_fsep)

        # File tree
        self._file_list = QTreeWidget()
        self._file_list.setHeaderHidden(True)
        self._file_list.setRootIsDecorated(True)
        self._file_list.setIndentation(14)
        self._file_list.setStyleSheet(
            f"QTreeWidget {{ background:transparent; border:none;"
            f" color:{self._TEXT}; font-size:11px; outline:none; }}"
            f" QTreeWidget::item {{ padding:4px 2px; }}"
            f" QTreeWidget::item:selected {{ background:{self._ACCENT}; color:#ffffff; }}"
            f" QTreeWidget::item:hover:!selected {{ background:{self._BORDER}; }}"
            " QScrollBar:vertical { width:5px; background:transparent; }"
            f" QScrollBar::handle:vertical {{ background:{self._BORDER}; border-radius:2px; }}"
            f" QTreeWidget::branch:has-children:!has-siblings:closed,"
            f" QTreeWidget::branch:closed:has-children:has-siblings {{"
            f"   border-image: none; image: url({self._BR_CLOSED}); }}"
            f" QTreeWidget::branch:open:has-children:!has-siblings,"
            f" QTreeWidget::branch:open:has-children:has-siblings {{"
            f"   border-image: none; image: url({self._BR_OPEN}); }}"
        )
        self._file_list.setSelectionMode(self._file_list.SelectionMode.SingleSelection)
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

        nm = QLabel(self._t("files_panel", "empty_title", fallback="No measurements loaded"))
        nm.setStyleSheet(
            f"font-size:12px; font-weight:bold; color:{self._TEXT}; background:transparent;")
        nm.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        ev.addWidget(nm)

        ht = QLabel(self._t("files_panel", "empty_hint", fallback="Add .s1p or .s2p files to compare curves."))
        ht.setStyleSheet(f"font-size:10px; color:{self._TEXT2}; background:transparent;")
        ht.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        ht.setWordWrap(True)
        ev.addWidget(ht)

        lv.addWidget(self._empty_state, stretch=1)
        return left

    # ── Chart area ────────────────────────────────────────────────────────── #
    def _build_chart_area(self) -> QWidget:
        right = QWidget()
        right.setStyleSheet(f"background:{self._WIN_BG};")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(16, 10, 16, 14)
        rv.setSpacing(0)

        self._fig = _Figure(facecolor=self._BG)
        self._axes = self._fig.subplots(2, 1)
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        rv.addWidget(self._canvas, stretch=1)

        self._canvas.mpl_connect("button_press_event",   self._on_canvas_press)
        self._canvas.mpl_connect("motion_notify_event",  self._on_canvas_motion)
        self._canvas.mpl_connect("button_release_event", self._on_canvas_release)
        self._canvas.mpl_connect("resize_event",         self._on_canvas_resize)

        self._reset_axes()
        return right

    # ── Layout / format toggle ────────────────────────────────────────────── #
    def _update_layout_buttons(self):
        self._btn_2.setStyleSheet(
            self._SEG_ACTIVE if self._layout_mode == 2 else self._SEG_INACTIVE)
        self._btn_4.setStyleSheet(
            self._SEG_ACTIVE if self._layout_mode == 4 else self._SEG_INACTIVE)

    def _update_display2_buttons(self):
        self._btn_mag_ph.setStyleSheet(
            self._SEG_ACTIVE if self._display2 == "mag_phase" else self._SEG_INACTIVE)
        self._btn_re_im.setStyleSheet(
            self._SEG_ACTIVE if self._display2 == "real_imag" else self._SEG_INACTIVE)

    def _update_param_buttons(self):
        # 2-chart: mutually exclusive
        self._btn_p2_s11.setStyleSheet(
            self._SEG_ACTIVE if self._param_mode == "s11" else self._SEG_INACTIVE)
        p2_s21_active = self._param_mode in ("s21", "eps")
        self._btn_p2_s21.setStyleSheet(
            self._SEG_ACTIVE if p2_s21_active else self._SEG_INACTIVE)
        # 4-chart buttons
        if self._display_mode == "char":
            s11_on = self._param_mode == "s11"
            s21_on = self._param_mode == "eps"
        else:
            s11_on = self._param_mode in ("s11", "split")
            s21_on = self._param_mode in ("s21", "split")
        self._btn_p4_s11.setStyleSheet(
            self._SEG_ACTIVE if s11_on else self._SEG_INACTIVE)
        self._btn_p4_s21.setStyleSheet(
            self._SEG_ACTIVE if s21_on else self._SEG_INACTIVE)

    def _update_header_groups(self):
        self._grp_display2.setEnabled(self._param_mode != "eps")
        self._param_stack.setCurrentIndex(0 if self._layout_mode == 2 else 1)

    def _set_layout(self, mode: int):
        if self._layout_mode == mode:
            return
        self._layout_mode = mode
        # "split" is only valid in 4-chart; reset to s11 if switching to 2-chart
        if mode == 2 and self._param_mode == "split":
            self._param_mode = "s11"
        # in char mode, 2-chart always uses eps
        if mode == 2 and self._display_mode == "char":
            self._param_mode = "eps"
        # char mode: eps stays in both 2-chart and 4-chart
        if mode == 4 and self._param_mode == "eps" and self._display_mode != "char":
            self._param_mode = "s11"
        self._update_layout_buttons()
        self._update_param_buttons()
        self._update_header_groups()
        self._update_range_page()
        self._rebuild_figure()
        self._update_cursor_readout()
        self._update_linked_buttons()

    def _set_display2(self, mode: str):
        if self._display2 == mode:
            return
        self._display2 = mode
        self._update_display2_buttons()
        self._update_range_page()
        self._redraw(self._current_entries())

    def _set_param(self, mode: str):
        if self._param_mode == mode:
            return
        self._param_mode = mode
        self._update_param_buttons()
        self._update_header_groups()
        self._update_range_page()
        self._redraw(self._current_entries())

    def _toggle_p4_s11(self):
        if self._display_mode == "char":
            if self._param_mode == "s11":
                return
            self._param_mode = "s11"
        else:
            if self._param_mode == "s11":
                return
            self._param_mode = "s21" if self._param_mode == "split" else "split"
        self._update_param_buttons()
        self._update_header_groups()
        self._update_range_page()
        self._redraw(self._current_entries())

    def _toggle_p4_s21(self):
        if self._display_mode == "char":
            if self._param_mode == "eps":
                return
            self._param_mode = "eps"
        else:
            if self._param_mode == "s21":
                return
            self._param_mode = "s11" if self._param_mode == "split" else "split"
        self._update_param_buttons()
        self._update_header_groups()
        self._update_range_page()
        self._redraw(self._current_entries())

    # ── Range page helpers ────────────────────────────────────────────────── #
    def _chart_labels_for_range(self) -> list[str]:
        result = []
        for t in self._chart_titles():
            tl = t.lower()
            if "magnitude" in tl:
                result.append(t + " [dB]")
            elif "phase" in tl:
                result.append(t + " [°]")
            elif t.startswith("ε"):
                result.append(t + " [–]")
            else:
                result.append(t)
        return result

    def _update_range_page(self):
        if not hasattr(self, "_range_sections"):
            return
        n = 4 if self._layout_mode == 4 else 2
        labels = self._chart_labels_for_range()
        for i, sec in enumerate(self._range_sections):
            visible = i < n
            sec["container"].setVisible(visible)
            if sec["sep"] is not None:
                sec["sep"].setVisible(visible)
            if i < len(labels):
                sec["label"].setText(labels[i])
            auto = self._y_autoscale[i]
            sec["btn_auto"].setStyleSheet(self._RNG_ON_STYLE if auto else self._RNG_OFF_STYLE)
            sec["btn_grid"].setStyleSheet(self._RNG_ON_STYLE if self._y_grid[i] else self._RNG_OFF_STYLE)
            sec["edit_min"].setEnabled(not auto)
            sec["edit_max"].setEnabled(not auto)

    def _toggle_y_autoscale(self, i: int):
        self._y_autoscale[i] = not self._y_autoscale[i]
        if not self._y_autoscale[i]:
            axes = self._flat_axes()
            if i < len(axes):
                ylo, yhi = axes[i].get_ylim()
                self._y_range[i] = (ylo, yhi)
                sec = self._range_sections[i]
                sec["edit_min"].setText(f"{ylo:.4g}")
                sec["edit_max"].setText(f"{yhi:.4g}")
        else:
            self._y_range[i] = (None, None)
            axes = self._flat_axes()
            if i < len(axes):
                ax = axes[i]
                ax.autoscale(enable=True, axis='y')
                if ax.get_lines():
                    ax.relim()
                    ax.autoscale_view()
            self._canvas.draw()
            self._blit_bg = self._canvas.copy_from_bbox(self._fig.bbox)
            self._draw_cursors()
            self._blit_cursors()
        self._update_range_page()

    def _toggle_y_grid(self, i: int):
        self._y_grid[i] = not self._y_grid[i]
        self._update_range_page()
        axes = self._flat_axes()
        if i < len(axes):
            ax = axes[i]
            if self._y_grid[i]:
                ax.grid(True, linestyle="--", alpha=0.45, color=self._GRID, linewidth=0.6)
            else:
                ax.grid(False)
            self._canvas.draw()
            self._blit_bg = self._canvas.copy_from_bbox(self._fig.bbox)
            self._draw_cursors()
            self._blit_cursors()

    def _apply_y_range(self, i: int):
        if self._y_autoscale[i]:
            return
        sec = self._range_sections[i]
        try:
            ymin = float(sec["edit_min"].text())
            ymax = float(sec["edit_max"].text())
        except (ValueError, TypeError):
            return
        if ymin >= ymax:
            return
        self._y_range[i] = (ymin, ymax)
        axes = self._flat_axes()
        if i < len(axes):
            axes[i].set_ylim(ymin, ymax)
            self._canvas.draw()
            self._blit_bg = self._canvas.copy_from_bbox(self._fig.bbox)
            self._draw_cursors()
            self._blit_cursors()

    # ── Export helpers ────────────────────────────────────────────────────── #
    def _build_export_fig(self, mode: str):
        from matplotlib.figure import Figure as _MplFig
        entries = self._current_entries()
        if not entries:
            return None, ""
        div, unit = self._freq_div, self._freq_unit

        p = self._param_mode
        if p == "split":
            p = "s11"

        def _style(ax, title, ylabel):
            ax.set_facecolor(self._CARD_BG)
            ax.set_title(title, fontsize=12, color=self._TEXT, pad=10)
            ax.set_ylabel(ylabel, fontsize=9, color=self._TEXT2)
            ax.set_xlabel(f"Frequency ({unit})", fontsize=9, color=self._TEXT2)
            ax.tick_params(colors=self._TEXT2, labelsize=8)
            ax.grid(True, linestyle="--", alpha=0.45, color=self._GRID, linewidth=0.6)
            for sp in ax.spines.values():
                sp.set_color(self._SPINE); sp.set_linewidth(0.8)

        def _plot(ax, entries, get_y):
            for e in entries:
                y = get_y(e)
                if y is None: continue
                ax.plot(e.freqs / div, y, color=e.color, linewidth=1.6, label=e.name)
            if len(entries) > 1 and ax.get_lines():
                ax.legend(fontsize=7, facecolor=self._PANEL_BG, edgecolor=self._BORDER, labelcolor=self._TEXT)

        def _s(e, param): return e.s11 if param == "s11" else e.s21

        # ── Permittivity (eps) export ─────────────────────────────────────────
        if p == "eps":
            if mode in ("ind_mag", "ind_phase", "ind_real", "ind_imag",
                        "pair_mp", "pair_ri"):
                fig = _MplFig(figsize=(9, 5) if mode.startswith("ind") else (9, 8),
                              facecolor=self._CARD_BG)
                if mode.startswith("ind"):
                    ax = fig.add_subplot(111)
                    if mode in ("ind_mag", "ind_real"):
                        _plot(ax, entries, lambda e: e.s11.real if e.s11 is not None else None)
                        _style(ax, "ε'", "ε' (–)")
                        fname = "eps_real"
                    else:
                        _plot(ax, entries, lambda e: e.s11.imag if e.s11 is not None else None)
                        _style(ax, "ε''", "ε'' (–)")
                        fname = "eps_imag"
                else:
                    ax1, ax2 = fig.subplots(2, 1)
                    _plot(ax1, entries, lambda e: e.s11.real if e.s11 is not None else None)
                    _plot(ax2, entries, lambda e: e.s11.imag if e.s11 is not None else None)
                    _style(ax1, "ε'",  "ε' (–)")
                    _style(ax2, "ε''", "ε'' (–)")
                    fname = "eps_real_imag"
                fig.tight_layout(pad=1.4, h_pad=2.0)
                return fig, fname
            return None, ""

        pname = p.upper()

        if mode in ("ind_mag", "ind_phase", "ind_real", "ind_imag"):
            fig = _MplFig(figsize=(9, 5), facecolor=self._CARD_BG)
            ax = fig.add_subplot(111)
            if mode == "ind_mag":
                _plot(ax, entries, lambda e: 20*np.log10(np.abs(_s(e,p))+1e-15) if _s(e,p) is not None else None)
                _style(ax, f"{pname} Magnitude", f"|{pname}| (dB)")
                fname = f"{pname}_magnitude"
            elif mode == "ind_phase":
                _plot(ax, entries, lambda e: np.angle(_s(e,p), deg=True) if _s(e,p) is not None else None)
                _style(ax, f"{pname} Phase", f"∠{pname} (°)")
                fname = f"{pname}_phase"
            elif mode == "ind_real":
                _plot(ax, entries, lambda e: _s(e,p).real if _s(e,p) is not None else None)
                _style(ax, f"{pname} Real", f"Re({pname})")
                fname = f"{pname}_real"
            else:
                _plot(ax, entries, lambda e: _s(e,p).imag if _s(e,p) is not None else None)
                _style(ax, f"{pname} Imaginary", f"Im({pname})")
                fname = f"{pname}_imag"
            fig.tight_layout(pad=1.4)
            return fig, fname

        if mode in ("pair_mp", "pair_ri"):
            fig = _MplFig(figsize=(9, 8), facecolor=self._CARD_BG)
            ax1, ax2 = fig.subplots(2, 1)
            if mode == "pair_mp":
                _plot(ax1, entries, lambda e: 20*np.log10(np.abs(_s(e,p))+1e-15) if _s(e,p) is not None else None)
                _plot(ax2, entries, lambda e: np.angle(_s(e,p), deg=True) if _s(e,p) is not None else None)
                _style(ax1, f"{pname} Magnitude", f"|{pname}| (dB)")
                _style(ax2, f"{pname} Phase", f"∠{pname} (°)")
                fname = f"{pname}_mag_phase"
            else:
                _plot(ax1, entries, lambda e: _s(e,p).real if _s(e,p) is not None else None)
                _plot(ax2, entries, lambda e: _s(e,p).imag if _s(e,p) is not None else None)
                _style(ax1, f"{pname} Real", f"Re({pname})")
                _style(ax2, f"{pname} Imaginary", f"Im({pname})")
                fname = f"{pname}_real_imag"
            fig.tight_layout(pad=1.4, h_pad=2.0)
            return fig, fname

        if mode in ("4ch_s11", "4ch_s21"):
            param = "s11" if mode == "4ch_s11" else "s21"
            pn = param.upper()
            fig = _MplFig(figsize=(12, 8), facecolor=self._CARD_BG)
            ((ax0, ax1), (ax2, ax3)) = fig.subplots(2, 2)
            for e in entries:
                s = _s(e, param)
                if s is None: continue
                f = e.freqs / div
                ax0.plot(f, 20*np.log10(np.abs(s)+1e-15), color=e.color, lw=1.6, label=e.name)
                ax1.plot(f, np.angle(s, deg=True),         color=e.color, lw=1.6, label=e.name)
                ax2.plot(f, s.real,                        color=e.color, lw=1.6, label=e.name)
                ax3.plot(f, s.imag,                        color=e.color, lw=1.6, label=e.name)
            _style(ax0, f"{pn} Magnitude",  f"|{pn}| (dB)")
            _style(ax1, f"{pn} Phase",      f"∠{pn} (°)")
            _style(ax2, f"{pn} Real",       f"Re({pn})")
            _style(ax3, f"{pn} Imaginary",  f"Im({pn})")
            if len(entries) > 1:
                for ax in (ax0, ax1, ax2, ax3):
                    if ax.get_lines():
                        ax.legend(fontsize=7, facecolor=self._PANEL_BG, edgecolor=self._BORDER, labelcolor=self._TEXT)
            fig.tight_layout(pad=1.4, h_pad=2.0, w_pad=2.0)
            return fig, f"{pn}_4chart"

        return None, ""

    def _run_export(self, mode: str):
        from PySide6.QtWidgets import QMessageBox
        import matplotlib.pyplot as _plt
        if not self._current_entries():
            QMessageBox.warning(self,
                self._t("export", "no_data_title", fallback="No data"),
                self._t("export", "no_data_msg",   fallback="Select at least one measurement file first."))
            return
        fig, hint = self._build_export_fig(mode)
        if fig is None:
            return
        try:
            dpi = max(72, min(600, int(self._export_dpi.text())))
        except ValueError:
            dpi = 150
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._t("export", "export_chart_title", fallback="Export Chart"),
            f"{hint}.png",
            self._t("export", "export_filter", fallback="PNG Images (*.png);;All Files (*.*)")
        )
        if path:
            try:
                fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor=self._CARD_BG)
            except Exception as exc:
                QMessageBox.critical(self, self._t("export", "export_error", fallback="Export Error"), str(exc))
        _plt.close(fig)

    def _update_tab_buttons(self, active_style: str, inactive_style: str):
        for i, btn in enumerate(self._tab_btns):
            btn.setStyleSheet(active_style if i == self._tab_idx else inactive_style)

    def _set_tab(self, idx: int):
        self._tab_idx = idx
        self._tab_stack.setCurrentIndex(idx)
        self._update_tab_buttons(self._TAB_ACTIVE, self._TAB_INACTIVE)

    def _update_compare_buttons(self):
        _left_r = (
            "border-top-left-radius:6px; border-bottom-left-radius:6px;"
            " border-top-right-radius:0px; border-bottom-right-radius:0px;"
        )
        _right_r = (
            "border-top-left-radius:0px; border-bottom-left-radius:0px;"
            f" border-top-right-radius:6px; border-bottom-right-radius:6px;"
            f" border-left:1px solid {self._BORDER};"
        )
        if not self._compare_mode:
            self._btn_single.setStyleSheet(
                self._MODE_ON_STYLE  + f" QPushButton {{ {_left_r} }}")
            self._btn_compare.setStyleSheet(
                self._MODE_OFF_STYLE + f" QPushButton {{ {_right_r} }}")
        else:
            self._btn_single.setStyleSheet(
                self._MODE_OFF_STYLE + f" QPushButton {{ {_left_r} }}")
            self._btn_compare.setStyleSheet(
                self._MODE_ON_STYLE  + f" QPushButton {{ {_right_r} border-left:none; }}")

    def _set_compare_mode(self, compare: bool):
        if self._compare_mode == compare:
            return
        self._compare_mode = compare
        self._update_compare_buttons()
        if compare:
            self._file_list.setSelectionMode(self._file_list.SelectionMode.MultiSelection)
        else:
            self._file_list.setSelectionMode(self._file_list.SelectionMode.SingleSelection)
            # keep at most the first selected file item
            selected = [i for i in self._file_list.selectedItems()
                        if i.data(0, Qt.ItemDataRole.UserRole)]
            if len(selected) > 1:
                self._file_list.blockSignals(True)
                keep = selected[0]
                for item in selected[1:]:
                    item.setSelected(False)
                self._file_list.blockSignals(False)
                p = keep.data(0, Qt.ItemDataRole.UserRole)
                self._redraw([self._cache[p]] if p in self._cache else [])
        self._refresh_item_swatches()

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
                item.data(0, Qt.ItemDataRole.UserRole)
                for item in self._file_list.selectedItems()
                if item.data(0, Qt.ItemDataRole.UserRole)
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
            self,
            self._t("files_panel", "add_files_title", fallback="Add Measurement Files"),
            "",
            self._t("files_panel", "add_files_filter", fallback="Touchstone Files (*.s1p *.s2p);;All Files (*.*)")
        )
        if paths:
            self._add_file_paths(paths)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self._t("files_panel", "select_folder_title", fallback="Select Folder"), "")
        if folder:
            key = str(Path(folder).resolve())
            loaded = getattr(self, "_loaded_folder_paths", set())
            if key in loaded:
                return
            self._file_list.blockSignals(True)
            existing = {item.data(0, Qt.ItemDataRole.UserRole)
                        for item in self._all_file_items()}
            self._add_folder_to_tree(folder, None, existing)
            loaded.add(key)
            self._loaded_folder_paths = loaded
            self._file_list.blockSignals(False)
            self._refresh_panel_state()

    def _all_file_items(self) -> list:
        """Return all leaf (file) QTreeWidgetItems recursively."""
        result = []
        def _collect(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole):
                    result.append(child)
                else:
                    _collect(child)
        for i in range(self._file_list.topLevelItemCount()):
            top = self._file_list.topLevelItem(i)
            if top.data(0, Qt.ItemDataRole.UserRole):
                result.append(top)
            else:
                _collect(top)
        return result

    @staticmethod
    def _folder_has_touchstone(folder: Path) -> bool:
        try:
            for p in folder.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".s1p", ".s2p"):
                    return True
        except PermissionError:
            pass
        return False

    def _add_folder_to_tree(self, folder_path: str, parent, existing: set,
                            auto_expand: bool = True):
        folder = Path(folder_path)
        folder_item = QTreeWidgetItem([f"{folder.name}/"])
        folder_item.setForeground(0, QColor(_TEXT2))
        folder_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        if parent is None:
            self._file_list.addTopLevelItem(folder_item)
        else:
            parent.addChild(folder_item)
        try:
            subfolders = sorted(p for p in folder.iterdir() if p.is_dir())
            files = sorted(p for p in folder.iterdir()
                           if p.is_file() and p.suffix.lower() in (".s1p", ".s2p"))
        except PermissionError:
            return
        subfolders = [s for s in subfolders if self._folder_has_touchstone(s)]
        expand_children = len(subfolders) == 1
        for sub in subfolders:
            self._add_folder_to_tree(str(sub), folder_item, existing,
                                     auto_expand=expand_children)
        for f in files:
            if str(f) in existing:
                continue
            fi = QTreeWidgetItem([f.name])
            fi.setData(0, Qt.ItemDataRole.UserRole, str(f))
            fi.setToolTip(0, str(f))
            folder_item.addChild(fi)
        folder_item.setExpanded(auto_expand)

    def _add_file_paths(self, paths: list[str]):
        existing = {item.data(0, Qt.ItemDataRole.UserRole)
                    for item in self._all_file_items()}
        self._file_list.blockSignals(True)
        for path in paths:
            if path in existing:
                continue
            item = QTreeWidgetItem([Path(path).name])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setToolTip(0, path)
            self._file_list.addTopLevelItem(item)
        self._file_list.blockSignals(False)
        self._refresh_panel_state()

    def _refresh_panel_state(self):
        count = len(self._all_file_items())
        if count == 1:
            self._badge.setText(self._t("files_panel", "badge_file", fallback="1 file"))
        else:
            self._badge.setText(self._t("files_panel", "badge_files", fallback="{n} files").replace("{n}", str(count)))
        has_items = self._file_list.topLevelItemCount() > 0
        self._file_list.setVisible(has_items)
        self._empty_state.setVisible(not has_items)

    def _apply_filter(self, text: str):
        stripped = text.strip()
        try:
            p = Path(stripped)
            if p.is_absolute() and p.is_dir():
                key = str(p.resolve())
                loaded = getattr(self, "_loaded_folder_paths", set())
                if key not in loaded:
                    existing = {item.data(0, Qt.ItemDataRole.UserRole)
                                for item in self._all_file_items()}
                    self._add_folder_to_tree(str(p), None, existing)
                    loaded.add(key)
                    self._loaded_folder_paths = loaded
                self._filter_edit.clear()
                return
        except (OSError, ValueError):
            pass
        text = stripped.lower()
        def _filter(item) -> bool:
            if item.childCount() == 0:
                match = not bool(text) or text in item.text(0).lower()
                item.setHidden(not match)
                return match
            any_child = False
            for i in range(item.childCount()):
                if _filter(item.child(i)):
                    any_child = True
            item.setHidden(bool(text) and not any_child)
            return any_child
        for i in range(self._file_list.topLevelItemCount()):
            _filter(self._file_list.topLevelItem(i))

    def _clear_selection(self):
        self._file_list.clearSelection()

    def _refresh_item_swatches(self):
        show = self._compare_mode
        self._file_list.setIconSize(QSize(14, 14) if show else QSize(0, 0))
        for item in self._all_file_items():
            path = item.data(0, Qt.ItemDataRole.UserRole)
            col  = self._color_map.get(path) if item.isSelected() else None
            item.setForeground(0, QColor(col) if col else QColor(_TEXT))
            item.setIcon(0, self._color_swatch(col if show and col else None))

    @staticmethod
    def _color_swatch(color: str | None, size: int = 12) -> QIcon:
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        if color:
            p = QPainter(px)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QColor(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
            p.end()
        return QIcon(px)

    # ── Selection ─────────────────────────────────────────────────────────── #
    def _on_selection_changed(self):
        selected_paths = [
            item.data(0, Qt.ItemDataRole.UserRole)
            for item in self._file_list.selectedItems()
            if item.data(0, Qt.ItemDataRole.UserRole)
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

        self._refresh_item_swatches()
        self._redraw(entries)

    # ── Drawing ───────────────────────────────────────────────────────────── #
    def _chart_titles(self) -> list[str]:
        p = self._param_mode
        if self._layout_mode == 4:
            if self._display_mode == "char":
                return ["ε'", "ε''", "tan(δ)", "|ε*|"]
            if p == "s11":
                return ["S11 Magnitude", "S11 Phase", "S11 Real", "S11 Imag"]
            if p == "s21":
                return ["S21 Magnitude", "S21 Phase", "S21 Real", "S21 Imag"]
            # split — columns driven by _display2
            if self._display2 == "real_imag":
                return ["S11 Real", "S11 Imag", "S21 Real", "S21 Imag"]
            return ["S11 Magnitude", "S11 Phase", "S21 Magnitude", "S21 Phase"]
        # 2-chart
        if p == "eps":
            return ["ε'", "ε''"]
        name = "S11" if p == "s11" else "S21"
        if self._display2 == "real_imag":
            return [f"{name} Real", f"{name} Imag"]
        return [f"{name} Magnitude", f"{name} Phase"]

    def _flat_axes(self) -> list:
        if self._layout_mode == 4:
            return [self._axes[0][0], self._axes[0][1],
                    self._axes[1][0], self._axes[1][1]]
        return list(self._axes)

    def _reset_axes(self):
        titles = self._chart_titles()

        for _ri, (ax, title) in enumerate(zip(self._flat_axes(), titles)):
            ax.cla()
            ax.set_facecolor(self._CARD_BG)
            ax.set_title(title, fontsize=11, color=self._TEXT, pad=10)
            for spine in ax.spines.values():
                spine.set_color(self._SPINE)
                spine.set_linewidth(0.8)
            ax.tick_params(colors=self._TEXT2, labelsize=8)
            if self._y_grid[_ri]:
                ax.grid(True, linestyle="--", alpha=0.35, color=self._GRID, linewidth=0.6)
            else:
                ax.grid(False)

            t = title.lower()
            if "magnitude" in t:
                ax.set_ylim(-60, 0)
                ax.set_ylabel("|S| (dB)", fontsize=8, color=self._TEXT2)
            elif "phase" in t:
                ax.set_ylim(-180, 180)
                ax.set_ylabel("Phase (°)", fontsize=8, color=self._TEXT2)
            elif "real" in t:
                ax.set_ylim(-1.1, 1.1)
                ax.set_ylabel("Real", fontsize=8, color=self._TEXT2)
            elif "imag" in t:
                ax.set_ylim(-1.1, 1.1)
                ax.set_ylabel("Imag", fontsize=8, color=self._TEXT2)
            elif "ε'" in title:
                ax.set_ylabel("ε' (–)", fontsize=8, color=self._TEXT2)
            elif "ε''" in title:
                ax.set_ylabel("ε'' (–)", fontsize=8, color=self._TEXT2)
            elif "tan" in t:
                ax.set_ylabel("ε''/ε' (–)", fontsize=8, color=self._TEXT2)
            elif "|ε" in title:
                ax.set_ylabel("|ε| (–)", fontsize=8, color=self._TEXT2)

            ax.set_xlim(0, 1500)
            ax.set_xlabel("Frequency (MHz)", fontsize=8, color=self._TEXT2)
            ax.yaxis.label.set_color(self._TEXT2)
            ax.xaxis.label.set_color(self._TEXT2)

            ax.text(0.5, 0.5, "No data to display", transform=ax.transAxes,
                    ha="center", va="center", fontsize=10,
                    color=self._TEXT2, fontstyle="italic")
        try:
            self._fig.tight_layout(pad=1.4, h_pad=2.0, w_pad=2.0)
        except Exception:
            pass
        self._canvas.draw()
        self._blit_bg = self._canvas.copy_from_bbox(self._fig.bbox)
        self._draw_cursors()
        self._blit_cursors()

    def _redraw(self, entries: list[_FileEntry]):
        flat = self._flat_axes()
        for _ai, ax in enumerate(flat):
            ax.cla()
            ax.set_facecolor(self._CARD_BG)
            ax.tick_params(colors=self._TEXT2, labelsize=8)
            if self._y_grid[_ai]:
                ax.grid(True, linestyle="--", alpha=0.45, color=self._GRID, linewidth=0.6)
            else:
                ax.grid(False)
            for spine in ax.spines.values():
                spine.set_color(self._SPINE)
                spine.set_linewidth(0.8)

        if not entries:
            self._reset_axes()
            return

        all_f = np.concatenate([e.freqs for e in entries])
        div, unit = _freq_axis_unit(all_f)
        self._freq_div  = div
        self._freq_unit = unit
        self._data_freq_min = float(all_f.min())
        self._data_freq_max = float(all_f.max())
        self._snap_freqs    = np.unique(all_f)

        p = self._param_mode

        if self._layout_mode == 4:
            ax0, ax1, ax2, ax3 = flat

            if self._display_mode == "char":
                no_data = not any(e.s11 is not None for e in entries)
                for e in entries:
                    if e.s11 is None:
                        continue
                    f, lw = e.freqs / div, 1.6
                    ep_r = e.s11.real
                    ep_i = e.s11.imag
                    tan_d = np.where(ep_r != 0, ep_i / ep_r, np.nan)
                    mod_e = np.sqrt(ep_r**2 + ep_i**2)
                    ax0.plot(f, ep_r,  color=e.color, linewidth=lw, label=e.name)
                    ax1.plot(f, ep_i,  color=e.color, linewidth=lw, label=e.name)
                    ax2.plot(f, tan_d, color=e.color, linewidth=lw, label=e.name)
                    ax3.plot(f, mod_e, color=e.color, linewidth=lw, label=e.name)
                if no_data:
                    for ax in flat:
                        ax.text(0.5, 0.5, "No permittivity data", transform=ax.transAxes,
                                ha="center", va="center", fontsize=9,
                                color=self._TEXT2, fontstyle="italic")
                specs = [
                    (ax0, "ε'",     "ε' (–)"),
                    (ax1, "ε''",    "ε'' (–)"),
                    (ax2, "tan(δ)", "ε''/ε' (–)"),
                    (ax3, "|ε*|",   "|ε| (–)"),
                ]

            elif p == "split":
                has_s21 = any(e.s21 is not None for e in entries)
                ri = self._display2 == "real_imag"

                def _col0(s): return s.real if ri else 20*np.log10(np.abs(s)+1e-15)
                def _col1(s): return s.imag if ri else np.angle(s, deg=True)

                for e in entries:
                    f, lw = e.freqs / div, 1.6
                    if e.s11 is not None:
                        ax0.plot(f, _col0(e.s11), color=e.color, linewidth=lw, label=e.name)
                        ax1.plot(f, _col1(e.s11), color=e.color, linewidth=lw, label=e.name)
                    if e.s21 is not None:
                        ax2.plot(f, _col0(e.s21), color=e.color, linewidth=lw, label=e.name)
                        ax3.plot(f, _col1(e.s21), color=e.color, linewidth=lw, label=e.name)

                if ri:
                    specs = [
                        (ax0, "S11 Real", "Re(S11)"),
                        (ax1, "S11 Imag", "Im(S11)"),
                        (ax2, "S21 Real", "Re(S21)"),
                        (ax3, "S21 Imag", "Im(S21)"),
                    ]
                else:
                    specs = [
                        (ax0, "S11 Magnitude", "|S11| (dB)"),
                        (ax1, "S11 Phase",     "∠S11 (°)"),
                        (ax2, "S21 Magnitude", "|S21| (dB)"),
                        (ax3, "S21 Phase",     "∠S21 (°)"),
                    ]
                if not has_s21:
                    for ax in (ax2, ax3):
                        ax.text(0.5, 0.5, "No S21 data", transform=ax.transAxes,
                                ha="center", va="center", fontsize=9,
                                color=self._TEXT2, fontstyle="italic")
            else:
                # s11 or s21: 4 charts — Mag, Phase, Real, Imag for chosen param
                def _get_s(e):
                    return e.s11 if p == "s11" else e.s21

                pname = p.upper()
                no_data = not any(_get_s(e) is not None for e in entries)
                for e in entries:
                    s = _get_s(e)
                    if s is None:
                        continue
                    f, lw = e.freqs / div, 1.6
                    ax0.plot(f, 20*np.log10(np.abs(s)+1e-15), color=e.color, linewidth=lw, label=e.name)
                    ax1.plot(f, np.angle(s, deg=True),         color=e.color, linewidth=lw, label=e.name)
                    ax2.plot(f, s.real,                        color=e.color, linewidth=lw, label=e.name)
                    ax3.plot(f, s.imag,                        color=e.color, linewidth=lw, label=e.name)
                specs = [
                    (ax0, f"{pname} Magnitude", f"|{pname}| (dB)"),
                    (ax1, f"{pname} Phase",     f"∠{pname} (°)"),
                    (ax2, f"{pname} Real",      f"Re({pname})"),
                    (ax3, f"{pname} Imag",      f"Im({pname})"),
                ]
                if no_data:
                    for ax in flat:
                        ax.text(0.5, 0.5, f"No {pname} data", transform=ax.transAxes,
                                ha="center", va="center", fontsize=9,
                                color=self._TEXT2, fontstyle="italic")
        else:
            ax_top, ax_bot = flat

            if p == "eps":
                no_data = not any(e.s11 is not None for e in entries)
                for e in entries:
                    if e.s11 is None:
                        continue
                    f, lw = e.freqs / div, 1.6
                    ax_top.plot(f, e.s11.real, color=e.color, linewidth=lw, label=e.name)
                    ax_bot.plot(f, e.s11.imag, color=e.color, linewidth=lw, label=e.name)
                if no_data:
                    for ax in (ax_top, ax_bot):
                        ax.text(0.5, 0.5, "No permittivity data", transform=ax.transAxes,
                                ha="center", va="center", fontsize=9,
                                color=self._TEXT2, fontstyle="italic")
                specs = [
                    (ax_top, "ε'",  "ε' (–)"),
                    (ax_bot, "ε''", "ε'' (–)"),
                ]
            else:
                pname = p.upper()

                def _yvals_top(s):
                    if self._display2 == "real_imag":
                        return s.real
                    return 20*np.log10(np.abs(s)+1e-15)

                def _yvals_bot(s):
                    if self._display2 == "real_imag":
                        return s.imag
                    return np.angle(s, deg=True)

                def _get_s(e):
                    return e.s11 if p == "s11" else e.s21

                no_data = not any(_get_s(e) is not None for e in entries)
                for e in entries:
                    s = _get_s(e)
                    if s is None:
                        continue
                    f, lw = e.freqs / div, 1.6
                    ax_top.plot(f, _yvals_top(s), color=e.color, linewidth=lw, label=e.name)
                    ax_bot.plot(f, _yvals_bot(s), color=e.color, linewidth=lw, label=e.name)

                if no_data:
                    for ax in (ax_top, ax_bot):
                        ax.text(0.5, 0.5, f"No {pname} data", transform=ax.transAxes,
                                ha="center", va="center", fontsize=9,
                                color=self._TEXT2, fontstyle="italic")

                if self._display2 == "real_imag":
                    specs = [
                        (ax_top, f"{pname} Real", f"Re({pname})"),
                        (ax_bot, f"{pname} Imag", f"Im({pname})"),
                    ]
                else:
                    specs = [
                        (ax_top, f"{pname} Magnitude", f"|{pname}| (dB)"),
                        (ax_bot, f"{pname} Phase",     f"∠{pname} (°)"),
                    ]

        for ax, title, ylabel in specs:
            ax.set_title(title, fontsize=11, color=self._TEXT, pad=10)
            ax.set_ylabel(ylabel, fontsize=9, color=self._TEXT2)
            ax.set_xlabel(f"Frequency ({unit})", fontsize=9, color=self._TEXT2)

        if len(entries) > 1:
            for ax in flat:
                if ax.get_lines():
                    ax.legend(fontsize=7, loc="best",
                              facecolor=self._PANEL_BG, edgecolor=self._BORDER,
                              labelcolor=self._TEXT)

        # Apply manual Y ranges (overrides matplotlib autoscale)
        for _ri, _ax in enumerate(flat):
            if not self._y_autoscale[_ri]:
                _yl = self._y_range[_ri]
                if _yl[0] is not None and _yl[1] is not None:
                    _ax.set_ylim(_yl[0], _yl[1])

        try:
            self._fig.tight_layout(pad=1.4, h_pad=2.0, w_pad=2.0)
        except Exception:
            pass
        self._canvas.draw()
        self._blit_bg = self._canvas.copy_from_bbox(self._fig.bbox)
        self._draw_cursors()
        self._blit_cursors()
        self._update_cursor_readout()
        self._update_cursor_buttons()

    # ── Cursor controls ───────────────────────────────────────────────────── #
    def _update_cursor_buttons(self):
        has_data = bool(self._current_entries()) if hasattr(self, "_file_list") else False
        for btn, on_style, n in (
            (self._btn_c1, self._C1_ON_STYLE, 1),
            (self._btn_c2, self._C2_ON_STYLE, 2),
        ):
            if not has_data:
                btn.setStyleSheet(self._CX_DIS_STYLE)
                btn.setEnabled(False)
                btn.setCursor(Qt.CursorShape.ForbiddenCursor)
            else:
                btn.setEnabled(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(on_style if self._cursor_enabled[n] else self._CX_OFF_STYLE)

    def _toggle_cursor(self, n: int):
        self._cursor_enabled[n] = not self._cursor_enabled[n]
        if not self._cursor_enabled[n]:
            self._cursor_freq[n] = [None] * 4
            for s in range(4):
                self._cursor_lines[(n, s)] = []
                self._cursor_markers[(n, s)] = []
            if self._cursor_dragging is not None and self._cursor_dragging[0] == n:
                self._cursor_dragging = None
        else:
            # Place cursor at center of current x range on enable
            axes = self._flat_axes()
            if axes:
                xlim = axes[0].get_xlim()
                center_hz = (xlim[0] + xlim[1]) / 2.0 * self._freq_div
                if self._layout_mode == 4 and not self._cursors_linked:
                    self._cursor_freq[n] = [center_hz] * 4   # all 4 individual
                else:
                    self._cursor_freq[n] = [center_hz, center_hz, None, None]
        self._update_cursor_buttons()
        self._redraw(self._current_entries())
        self._update_cursor_readout()

    def _fmt_freq(self, hz: float) -> str:
        if hz >= 1e9:
            return f"{hz / 1e9:.4f} GHz"
        if hz >= 1e6:
            return f"{hz / 1e6:.4f} MHz"
        return f"{hz / 1e3:.4f} kHz"

    def _y_unit_for_ax(self, ax_idx: int) -> str:
        """Return the y-axis unit string for chart at ax_idx."""
        titles = self._chart_titles()
        if ax_idx >= len(titles):
            return ""
        t = titles[ax_idx].lower()
        if "magnitude" in t: return "dB"
        if "phase"     in t: return "°"
        if "real"      in t: return "(Re)"
        if "imag"      in t: return "(Im)"
        return ""

    def _cursor_y_val(self, n: int, row: int):
        """Return (float_value, unit_str) for cursor n row, or (None, '')."""
        for dot, _, ax_idx in self._cursor_markers[(n, row)]:
            yi = dot.get_ydata()
            if len(yi) == 0:
                continue
            return float(yi[0]), self._y_unit_for_ax(ax_idx)
        return None, ""

    def _cursor_y_str(self, n: int, row: int) -> str:
        v, unit = self._cursor_y_val(n, row)
        return f"{v:.3f} {unit}".strip() if v is not None else ""

    def _short_chart_label(self, title: str) -> str:
        t = title.lower()
        if "magnitude" in t: return "Mag"
        if "phase"     in t: return "Phase"
        if "real"      in t: return "Re"
        if "imag"      in t: return "Im"
        return title.split()[-1][:5]

    def _cursor_y_val_at(self, n: int, ax_idx: int):
        """Return (float_value, unit_str) for cursor n at a specific axis index."""
        slot = self._cursor_slot(ax_idx)
        for dot, _, a_idx in self._cursor_markers[(n, slot)]:
            if a_idx == ax_idx:
                yi = dot.get_ydata()
                if len(yi) == 0:
                    continue
                return float(yi[0]), self._y_unit_for_ax(ax_idx)
        return None, ""

    def _update_cursor_readout(self):
        titles = self._chart_titles()
        n = len(titles)   # 2 or 4

        # Show/hide value columns based on chart count
        for vcols in (self._c1_vcols, self._c2_vcols, self._df_vcols):
            for i, (cw, _, __) in enumerate(vcols):
                cw.setVisible(i < n)

        # Update column captions
        for i in range(n):
            short = self._short_chart_label(titles[i])
            self._c1_vcols[i][1].setText(short)
            self._c2_vcols[i][1].setText(short)
            self._df_vcols[i][1].setText(f"Δ{short}")

        f1 = self._cursor_freq[1][self._last_readout_slot[1]]
        f2 = self._cursor_freq[2][self._last_readout_slot[2]]

        def _fv(cursor_n, ax_idx):
            v, u = self._cursor_y_val_at(cursor_n, ax_idx)
            return f"{v:.3f} {u}".strip() if v is not None else "—"

        def _dv(ax_idx):
            v1, u = self._cursor_y_val_at(1, ax_idx)
            v2, _ = self._cursor_y_val_at(2, ax_idx)
            if v1 is not None and v2 is not None:
                dy = v2 - v1
                return f"{'+'if dy>=0 else''}{dy:.3f} {u}".strip()
            return "—"

        # C1
        if f1 is not None:
            self._lbl_c1_freq.setText(self._fmt_freq(f1))
            for i in range(n):
                self._c1_vcols[i][2].setText(_fv(1, i))
        else:
            self._lbl_c1_freq.setText("—")
            for _, _, val in self._c1_vcols:
                val.setText("—")

        # C2
        if f2 is not None:
            self._lbl_c2_freq.setText(self._fmt_freq(f2))
            for i in range(n):
                self._c2_vcols[i][2].setText(_fv(2, i))
        else:
            self._lbl_c2_freq.setText("—")
            for _, _, val in self._c2_vcols:
                val.setText("—")

        # Delta
        if f1 is not None and f2 is not None:
            self._lbl_df.setText(self._fmt_freq(abs(f2 - f1)))
            for i in range(n):
                self._df_vcols[i][2].setText(_dv(i))
        else:
            self._lbl_df.setText("—")
            for _, _, val in self._df_vcols:
                val.setText("—")

    def _update_linked_buttons(self):
        linked = self._cursors_linked
        on  = (f"QPushButton {{ font-size:11px; font-weight:600; border:none;"
               f" background:{self._ACCENT}; color:#ffffff; border-radius:5px; }}"
               f" QPushButton:hover {{ background:{self._ACCENT_H}; }}")
        off = (f"QPushButton {{ font-size:11px; border:1px solid {self._BORDER};"
               f" background:transparent; color:{self._TEXT2}; border-radius:5px; }}"
               f" QPushButton:hover {{ background:{self._BORDER}; color:{self._TEXT}; }}")
        self._btn_linked.setEnabled(True)
        self._btn_linked.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_linked.setText("ON" if linked else "OFF")
        self._btn_linked.setStyleSheet(on if linked else off)

    def _toggle_cursors_linked(self):
        was_linked = self._cursors_linked
        self._cursors_linked = not was_linked
        if self._layout_mode == 4:
            if not self._cursors_linked:
                # linked→unlinked: expand slot 0→(0,1) and slot 1→(2,3)
                for n in (1, 2):
                    f_top = self._cursor_freq[n][0]  # top pair freq
                    f_bot = self._cursor_freq[n][1]  # bottom pair freq
                    self._cursor_freq[n][1] = f_top  # ax1 keeps top freq
                    self._cursor_freq[n][2] = f_bot  # ax2 gets bottom freq
                    self._cursor_freq[n][3] = f_bot  # ax3 gets bottom freq
            else:
                # unlinked→linked: collapse (0,1)→slot 0, (2,3)→slot 1
                for n in (1, 2):
                    # slot 1 now becomes the bottom pair freq (use slot 2 if available)
                    if self._cursor_freq[n][2] is not None:
                        self._cursor_freq[n][1] = self._cursor_freq[n][2]
                    self._cursor_freq[n][2] = None
                    self._cursor_freq[n][3] = None
                    for s in (2, 3):
                        self._cursor_lines[(n, s)] = []
                        self._cursor_markers[(n, s)] = []
        if self._layout_mode != 4 and self._cursors_linked:
            # 2-chart unlinked→linked: snap both slots to slot 0's frequency
            for n in (1, 2):
                if self._cursor_freq[n][0] is not None:
                    self._cursor_freq[n][1] = self._cursor_freq[n][0]
        self._update_linked_buttons()
        self._redraw(self._current_entries())

    def _cursor_slot(self, ax_idx: int) -> int:
        """Map an axis index to its cursor slot.

        2-chart:          ax 0 → slot 0, ax 1 → slot 1.
        4-chart linked:   row pairs — top (ax 0,1) → slot 0; bottom (ax 2,3) → slot 1.
        4-chart unlinked: each axis is its own slot (ax_idx = slot).
        """
        if self._layout_mode != 4:
            return ax_idx
        if self._cursors_linked:
            return 0 if ax_idx < 2 else 1
        return ax_idx   # 0,1,2,3 individual

    def _row_axes(self, slot: int) -> list:
        """Return the axes that belong to a cursor slot.

        2-chart: one axis per slot.
        4-chart linked:   slot 0 → [ax0,ax1], slot 1 → [ax2,ax3].
        4-chart unlinked: one axis per slot (individual).
        """
        all_axes = self._flat_axes()
        if self._layout_mode == 4:
            if self._cursors_linked:
                return all_axes[:2] if slot == 0 else all_axes[2:]
            return [all_axes[slot]]
        return [all_axes[slot]]

    def _blit_cursors(self):
        """Fast cursor repaint using saved background — no full figure redraw."""
        if self._blit_bg is None:
            self._canvas.draw_idle()
            return
        self._canvas.restore_region(self._blit_bg)
        for key in self._cursor_lines:
            for ln in self._cursor_lines[key]:
                try: ln.axes.draw_artist(ln)
                except Exception: pass
        for key in self._cursor_markers:
            for dot, _, _ in self._cursor_markers[key]:
                try: dot.axes.draw_artist(dot)
                except Exception: pass
        self._canvas.blit(self._fig.bbox)

    def _draw_cursors(self):
        # Remove old artists
        for key in list(self._cursor_lines):
            for ln in self._cursor_lines[key]:
                try: ln.remove()
                except Exception: pass
        for key in list(self._cursor_markers):
            for dot, _, _i in self._cursor_markers[key]:
                try: dot.remove()
                except Exception: pass
        self._cursor_lines   = {(n,s): [] for n in (1,2) for s in range(4)}
        self._cursor_markers = {(n,s): [] for n in (1,2) for s in range(4)}
        all_axes = self._flat_axes()
        n_slots = len(all_axes)   # 2 or 4
        for n, color in ((1, _C1_COLOR), (2, _C2_COLOR)):
            if not self._cursor_enabled[n]:
                continue
            for slot in range(n_slots):
                freq = self._cursor_freq[n][slot]
                if freq is None:
                    continue
                x = freq / self._freq_div
                for ax in self._row_axes(slot):
                    ax_idx = all_axes.index(ax)
                    vline = ax.axvline(x, color=color, linewidth=1.2,
                                       linestyle="--", alpha=0.9, zorder=5,
                                       animated=True)
                    self._cursor_lines[(n, slot)].append(vline)
                    for data_line in ax.get_lines():
                        if data_line is vline:
                            continue
                        xd = data_line.get_xdata()
                        yd = data_line.get_ydata()
                        if len(xd) < 2 or not (min(xd) <= x <= max(xd)):
                            continue
                        yi = float(np.interp(x, xd, yd))
                        dot, = ax.plot([x], [yi], "o",
                                       markerfacecolor=color, markeredgecolor=color,
                                       markersize=8, zorder=7, markeredgewidth=0,
                                       animated=True)
                        self._cursor_markers[(n, slot)].append((dot, data_line, ax_idx))

    def _on_canvas_press(self, event):
        if event.inaxes is None or event.button != 1:
            return
        if not any(self._cursor_enabled.values()):
            return

        ax = event.inaxes
        all_ax = self._flat_axes()
        ax_idx = all_ax.index(ax) if ax in all_ax else 0
        slot = self._cursor_slot(ax_idx)

        xlim = ax.get_xlim()
        thresh = (xlim[1] - xlim[0]) * 0.025
        xdata = event.xdata

        # Near an existing cursor line in this slot → drag it
        for n in (1, 2):
            if not self._cursor_enabled[n]:
                continue
            freq = self._cursor_freq[n][slot]
            if freq is not None and abs(xdata - freq / self._freq_div) < thresh:
                self._cursor_dragging = (n, slot)
                return

        # Place the first enabled cursor with no freq in this slot
        for n in (1, 2):
            if self._cursor_enabled[n] and self._cursor_freq[n][slot] is None:
                self._cursor_freq[n][slot] = xdata * self._freq_div
                if self._cursors_linked and self._layout_mode != 4:
                    self._cursor_freq[n][1 - slot] = self._cursor_freq[n][slot]
                self._cursor_dragging = (n, slot)
                self._draw_cursors()
                self._update_cursor_readout()
                self._canvas.draw()
                self._blit_bg = self._canvas.copy_from_bbox(self._fig.bbox)
                return

        # Both placed — move nearest in this slot
        dists = {}
        for n in (1, 2):
            if self._cursor_enabled[n] and self._cursor_freq[n][slot] is not None:
                dists[(n, slot)] = abs(xdata - self._cursor_freq[n][slot] / self._freq_div)
        if dists:
            self._cursor_dragging = min(dists, key=dists.get)

    def _on_canvas_motion(self, event):
        if self._cursor_dragging is None or event.inaxes is None:
            return
        if event.xdata is None:
            return
        x = event.xdata
        if self._snap_freqs is not None and len(self._snap_freqs):
            hz = x * self._freq_div
            idx = int(np.argmin(np.abs(self._snap_freqs - hz)))
            x = self._snap_freqs[idx] / self._freq_div
        n, slot = self._cursor_dragging
        self._cursor_freq[n][slot] = x * self._freq_div
        self._last_readout_slot[n] = slot

        # Linked syncs slots only in 2-chart; in 4-chart pairing is via _row_axes
        keys_to_move = [(n, slot)]
        if self._cursors_linked and self._layout_mode != 4:
            other = 1 - slot
            self._cursor_freq[n][other] = self._cursor_freq[n][slot]
            keys_to_move.append((n, other))

        for key in keys_to_move:
            for line in self._cursor_lines[key]:
                line.set_xdata([x, x])
            for dot, data_line, _i in self._cursor_markers[key]:
                xd = data_line.get_xdata()
                yd = data_line.get_ydata()
                if len(xd) >= 2 and min(xd) <= x <= max(xd):
                    dot.set_xdata([x])
                    dot.set_ydata([float(np.interp(x, xd, yd))])
                    dot.set_visible(True)
                else:
                    dot.set_visible(False)
        self._blit_cursors()
        self._update_cursor_readout()

    def _on_canvas_release(self, event):
        self._cursor_dragging = None
        self._update_cursor_readout()

    def _on_canvas_resize(self, event):
        self._blit_bg = None   # invalidate — will be rebuilt on next _redraw

    def showEvent(self, event):
        super().showEvent(event)
        self._reset_axes()

    # ── Navigation ────────────────────────────────────────────────────────── #
    def _go_back(self):
        if self._source_module == "dut":
            self._go_to_dut()
        elif self._source_module == "char":
            self._go_to_char()
        else:
            self.return_to_menu_window()

    def return_to_menu_window(self):
        try:
            import matplotlib.pyplot as plt
            plt.close("all")
        except Exception:
            pass
        if self._source_window is not None:
            try:
                self._source_window.show()
                self.close()
                return
            except RuntimeError:
                pass
        from NanoVNA_UTN_Toolkit.modules.menu_window import ModuleSelectionWindow
        if self._vna:
            self._menu_win = ModuleSelectionWindow(vna_device=self._vna)
        else:
            self._menu_win = ModuleSelectionWindow()
        self._menu_win.show()
        self.close()

    def _go_to_dut(self):
        try:
            import matplotlib.pyplot as plt
            plt.close("all")
        except Exception:
            pass
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics
        self._dut_win = NanoVNAGraphics(vna_device=self._vna)
        self._dut_win.show()
        self.close()

    def _go_to_char(self):
        try:
            import matplotlib.pyplot as plt
            plt.close("all")
        except Exception:
            pass
        if self._source_window is not None:
            try:
                self._source_window.show()
                self.close()
                return
            except RuntimeError:
                pass
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.measurement_main_window import MeasurementMainWindow
        self._char_win = MeasurementMainWindow(vna_device=self._vna)
        self._char_win.show()
        self.close()
