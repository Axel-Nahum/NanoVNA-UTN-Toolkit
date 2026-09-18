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
import shutil
import tempfile

import numpy as np
from pathlib import Path

from NanoVNA_UTN_Toolkit.shared.utils.export.pdf_generation_task import (
    GeneratingButton, PdfCompileTask,
)

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QWidget, QCheckBox, QLineEdit, QComboBox,
    QFrame, QFileDialog, QTextEdit,
    QGridLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QTextCharFormat, QFont, QTextListFormat

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

from NanoVNA_UTN_Toolkit.shared.ui.pdf_export_widgets import (
    HoverHelpButton as _HoverHelpButton,
    CenteredComboBox as _CenteredComboBox,
    make_centered_combo as _make_centered_combo,
    NoEnterButton as _NoEnterButton,
    enable_drag_annotations as _enable_drag_annotations_shared,
)

_CHART_INI_EXE = "INI/material_characterization/characterization_chart_config/characterization_chart_config.ini"
_CHART_INI_DEV = "modules/material_characterization/ui/measurement_main_window/characterization_chart_config/characterization_chart_config.ini"

# How many markers each graph supports  (graph 0 = permittivity, graph 1 = Smith)
_GRAPH_MARKER_COUNT = {0: 2, 1: 1}

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


# --------------------------------------------------------------------------- #

_DASH_STYLE = "dash"   # sentinel: no QTextList, insert "– " prefix


class _NotesEdit(QTextEdit):
    """QTextEdit with a custom placeholder that disappears when there is real content
    (typed text OR an active list), and reappears when the editor is truly empty."""

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self._placeholder = placeholder
        self._saved_cursor = None

    def focusOutEvent(self, event):
        self._saved_cursor = self.textCursor()
        super().focusOutEvent(event)

    def _is_empty(self) -> bool:
        cursor = self.textCursor()
        cursor.select(cursor.SelectionType.Document)
        doc = self.document()
        # Has a list anywhere → not empty
        block = doc.begin()
        while block.isValid():
            if block.textList():
                return False
            block = block.next()
        # Has actual text → not empty
        return doc.toPlainText().strip() == ""

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        was_on_list = cursor.currentList() is not None
        super().keyPressEvent(event)
        if was_on_list and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            new_cursor = self.textCursor()
            if new_cursor.currentList() is not None and not new_cursor.block().text():
                new_cursor.insertText("  ")
                self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._is_empty():
            return
        from PySide6.QtGui import QPainter, QColor
        p = QPainter(self.viewport())
        p.setPen(QColor("#8888aa"))
        p.setFont(self.font())
        offset = int(self.document().documentMargin())
        p.drawText(
            self.viewport().rect().adjusted(offset, offset, -offset, -offset),
            Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap,
            self._placeholder,
        )
        p.end()

_LIST_STYLES = [
    ("•",  "Disc",        QTextListFormat.ListDisc),
    ("◦",  "Circle",      QTextListFormat.ListCircle),
    ("▪",  "Square",      QTextListFormat.ListSquare),
    ("–",  "Dash",        _DASH_STYLE),
    ("1.", "Numbered",    QTextListFormat.ListDecimal),
    ("a.", "Lower alpha", QTextListFormat.ListLowerAlpha),
    ("A.", "Upper alpha", QTextListFormat.ListUpperAlpha),
    ("i.", "Lower roman", QTextListFormat.ListLowerRoman),
    ("I.", "Upper roman", QTextListFormat.ListUpperRoman),
]
_LIST_COLS = 3   # 3×3 grid


class _ListPickerPopup(QFrame):
    """2×5 grid popup for choosing bullet/list style."""
    from PySide6.QtCore import Signal
    styleChosen = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setStyleSheet(
            "QFrame { background-color: #2a2a3e; border: 1px solid #4a4a6a; border-radius: 6px; }"
            " QPushButton { background: transparent; color: #ddddee; border: 1px solid transparent;"
            " border-radius: 4px; font-size: 14px; min-width: 36px; max-width: 36px;"
            " min-height: 32px; max-height: 32px; }"
            " QPushButton:hover { background-color: #3a3a6a; border: 1px solid #6666aa; }"
        )
        grid = QGridLayout(self)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setSpacing(4)
        for idx, (symbol, tooltip, style) in enumerate(_LIST_STYLES):
            btn = QPushButton(symbol)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda _=False, s=style: self._pick(s))
            grid.addWidget(btn, idx // _LIST_COLS, idx % _LIST_COLS)

    def _pick(self, style):
        self.styleChosen.emit(style)
        self.close()


# --------------------------------------------------------------------------- #

class PermittivityPdfPreviewDialog(QDialog):
    """
    Preview dialog for the characterization PDF export.

    When include_notes=False — 2 steps:
      Step 0: Permittivity ε'+ε''  (2 markers)
      Step 1: S11 Smith chart       (1 marker)

    When include_notes=True — 3 steps:
      Step 0: Notes / Comments      (text editor, no graph)
      Step 1: Permittivity ε'+ε''  (2 markers)
      Step 2: S11 Smith chart       (1 marker)
    """

    def __init__(
        self, parent=None, freqs=None, s11_data=None, eps_selected=None,
        sample_name=None, output_path=None, wizard_window=None,
        include_steps=False, include_notes=False, include_tables=False,
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
        self.include_steps = include_steps
        self.include_notes = include_notes
        self.include_tables = include_tables
        self.TOTAL_GRAPHS = 3 if include_notes else 2

        self.current_graph_index = 0
        self.saved_figures = []

        # Marker state keyed by data-graph index (0=permittivity, 1=smith)
        self.marker_positions = {i: [None, None] for i in range(2)}
        self.marker_active = {i: [False, False] for i in range(2)}
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

        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text as _lt
        self._options_help = _lt("characterization_measurement_main.json").get("pdf_options_help", {})

        self.setWindowTitle("Export Preview — Characterization")
        self.setModal(True)
        _theme = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve()
        )
        self._is_dark = not _theme.value("Dark_Light/is_dark_mode", False, type=bool)
        if self._is_dark:
            _cb_bg, _cb_border = "#252538", "1px solid #383850"
        else:
            _cb_bg, _cb_border = "#f8f8ff", "1px solid #c4c4d8"
        self._cb_indicator_ss = (
            " QCheckBox::indicator { width: 14px; height: 14px; }"
            f" QCheckBox::indicator:unchecked {{ background-color: {_cb_bg}; border: {_cb_border}; border-radius: 3px; }}"
            " QCheckBox::indicator:checked { background-color: #4d90fe; border: 1px solid #4d90fe; border-radius: 3px; }"
            " QCheckBox::indicator:hover { border: 1px solid #6aa2ff; }"
        )
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

    def _data_graph_index(self, graph_index):
        """Map navigation index → data index (0=permittivity, 1=smith).
        Returns -1 for the notes step."""
        return graph_index - (1 if self.include_notes else 0)

    def _marker_count(self, graph_index):
        dgi = self._data_graph_index(graph_index)
        return _GRAPH_MARKER_COUNT.get(dgi, 0)

    def _marker_colors(self, graph_index):
        if self._data_graph_index(graph_index) == 1:
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

        # Notes step widget (full-size panel, replaces canvas when on step 0 with include_notes)
        self.notes_step_widget = QWidget()
        self.notes_step_widget.setMinimumHeight(360)
        notes_step_layout = QVBoxLayout(self.notes_step_widget)
        notes_step_layout.setContentsMargins(8, 12, 8, 12)
        notes_step_label = QLabel("Notes / Comments")
        notes_step_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #cccccc;")
        notes_step_layout.addWidget(notes_step_label)
        notes_step_hint = QLabel(
            "Write any observations, conclusions or relevant information to include in the report."
        )
        notes_step_hint.setStyleSheet("font-size: 11px; color: #999999;")
        notes_step_hint.setWordWrap(True)
        notes_step_layout.addWidget(notes_step_hint)
        notes_step_layout.addSpacing(6)

        # Rich text editor: toolbar + text area inside a single styled frame
        editor_frame = QFrame()
        editor_frame.setStyleSheet(
            "QFrame { background-color: #252538; border: 1px solid #383850; border-radius: 6px; }"
        )
        editor_frame_l = QVBoxLayout(editor_frame)
        editor_frame_l.setContentsMargins(0, 0, 0, 0)
        editor_frame_l.setSpacing(0)

        # Toolbar row
        toolbar_w = QWidget()
        toolbar_w.setStyleSheet(
            "QWidget { background-color: #2a2a3e; border-bottom: 1px solid #383850;"
            " border-radius: 0px; }"
        )
        toolbar_l = QHBoxLayout(toolbar_w)
        toolbar_l.setContentsMargins(6, 4, 6, 4)
        toolbar_l.setSpacing(3)

        _btn_base = (
            "QPushButton { background-color: transparent; color: #cccccc;"
            " border: 1px solid transparent; border-radius: 4px;"
            " min-width: 28px; max-width: 28px; min-height: 24px; max-height: 24px;"
            " font-size: 13px; }"
            " QPushButton:hover { background-color: #383850; border: 1px solid #4a4a6a; }"
            " QPushButton:checked { background-color: #3a3a6a; border: 1px solid #6666aa;"
            " color: white; }"
        )

        def _vsep():
            s = QFrame()
            s.setFrameShape(QFrame.VLine)
            s.setFixedHeight(18)
            s.setStyleSheet("QFrame { border: none; background-color: #383850; min-width: 1px; max-width: 1px; }")
            return s

        # Paragraph style selector
        _combo_ss_base = (
            "QComboBox {{ background-color: {bg}; color: {fg}; border: 1px solid {bd};"
            " border-radius: 4px; padding: 1px 4px; font-size: 11px; min-height: 22px; }}"
            " QComboBox:hover:enabled {{ background-color: #383850; }}"
            " QComboBox::drop-down {{ border: none; width: 14px; }}"
            " QComboBox:disabled {{ background-color: #1e1e2e; color: #4a4a6a; border-color: #2a2a3e; }}"
            " QComboBox QAbstractItemView {{ background-color: #2a2a3e; color: #cccccc;"
            " selection-background-color: #3a3a6a; }}"
        )
        _combo_ss_on  = _combo_ss_base.format(bg="#2e2e42", fg="#cccccc", bd="#4a4a6a")
        self._style_combo = QComboBox()
        self._style_combo.setFocusPolicy(Qt.NoFocus)
        self._style_combo.addItems(["Body", "Subsection", "Sub-subsection"])
        self._style_combo.setFixedWidth(118)
        self._style_combo.setToolTip(
            "Paragraph style\n"
            "Body — normal text\n"
            "Subsection — \\subsection in PDF\n"
            "Sub-subsection — \\subsubsection in PDF"
        )
        self._style_combo.setStyleSheet(_combo_ss_on)
        self._style_combo.setEnabled(False)
        self._style_combo.currentIndexChanged.connect(self._apply_paragraph_style)
        toolbar_l.addWidget(self._style_combo)

        # Checkbox: enable PDF heading structure
        from PySide6.QtWidgets import QCheckBox as _QCheckBox
        self._heading_chk = _QCheckBox()
        self._heading_chk.setFocusPolicy(Qt.NoFocus)
        self._heading_chk.setToolTip("Enable subsection / sub-subsection headings in PDF")
        self._heading_chk.setStyleSheet("QCheckBox { spacing: 0px; } " + self._cb_indicator_ss)
        self._heading_chk.toggled.connect(self._on_heading_mode_toggled)
        toolbar_l.addSpacing(4)
        toolbar_l.addWidget(self._heading_chk)
        toolbar_l.addSpacing(5)

        _sh = getattr(self, '_options_help', {})
        _btn_style_help = _HoverHelpButton(
            _sh.get("style_help_title", "Paragraph Style"),
            _sh.get("style_help_body",
                    "Body — normal text in the PDF.\n"
                    "Subsection — section heading (\\subsection).\n"
                    "Sub-subsection — sub-heading (\\subsubsection).\n\n"
                    "Enable the checkbox to use headings."),
        )
        toolbar_l.addWidget(_btn_style_help)
        toolbar_l.addSpacing(5)

        toolbar_l.addSpacing(4)
        toolbar_l.addWidget(_vsep())
        toolbar_l.addSpacing(4)

        self._btn_bold = QPushButton("B")
        self._btn_bold.setCheckable(True)
        self._btn_bold.setFocusPolicy(Qt.NoFocus)
        self._btn_bold.setStyleSheet(_btn_base + " QPushButton { font-weight: bold; }")
        self._btn_bold.setToolTip("Bold (Ctrl+B)")
        self._btn_bold.clicked.connect(lambda checked: self._apply_char_format("bold", checked))
        toolbar_l.addWidget(self._btn_bold)

        self._btn_italic = QPushButton("I")
        self._btn_italic.setCheckable(True)
        self._btn_italic.setFocusPolicy(Qt.NoFocus)
        self._btn_italic.setStyleSheet(_btn_base + " QPushButton { font-style: italic; }")
        self._btn_italic.setToolTip("Italic (Ctrl+I)")
        self._btn_italic.clicked.connect(lambda checked: self._apply_char_format("italic", checked))
        toolbar_l.addWidget(self._btn_italic)

        self._btn_underline = QPushButton("U")
        self._btn_underline.setCheckable(True)
        self._btn_underline.setFocusPolicy(Qt.NoFocus)
        self._btn_underline.setStyleSheet(_btn_base + " QPushButton { text-decoration: underline; }")
        self._btn_underline.setToolTip("Underline (Ctrl+U)")
        self._btn_underline.clicked.connect(lambda checked: self._apply_char_format("underline", checked))
        toolbar_l.addWidget(self._btn_underline)

        toolbar_l.addWidget(_vsep())

        # List style button — opens 3×3 picker popup on click
        self._current_list_style = QTextListFormat.ListDisc
        self._btn_list = QPushButton("≡•")
        self._btn_list.setCheckable(True)
        self._btn_list.setFocusPolicy(Qt.NoFocus)
        self._btn_list.setStyleSheet(_btn_base + " QPushButton { font-size: 11px; max-width: 34px; min-width: 34px; }")
        self._btn_list.setToolTip("List style")
        self._btn_list.clicked.connect(self._on_list_btn_clicked)
        toolbar_l.addWidget(self._btn_list)

        toolbar_l.addSpacing(6)
        toolbar_l.addWidget(_vsep())
        toolbar_l.addSpacing(6)

        self._size_label = QLabel("Aa")
        self._size_label.setStyleSheet("QLabel { color: #888888; font-size: 11px; background: transparent; border: none; }")
        toolbar_l.addWidget(self._size_label)
        toolbar_l.addSpacing(3)

        self._size_combo = QComboBox()
        self._size_combo.setFocusPolicy(Qt.NoFocus)
        self._size_combo.setStyleSheet(
            "QComboBox { background-color: #2e2e42; color: #cccccc; border: 1px solid #4a4a6a;"
            " border-radius: 4px; padding: 1px 4px; font-size: 11px; min-height: 22px; }"
            " QComboBox:hover:enabled { background-color: #383850; }"
            " QComboBox::drop-down { border: none; width: 14px; }"
            " QComboBox:disabled { background-color: #1e1e2e; color: #4a4a6a;"
            " border-color: #2a2a3e; }"
            " QComboBox QAbstractItemView { background-color: #2a2a3e; color: #cccccc;"
            " selection-background-color: #3a3a6a; }"
        )
        for s in ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "36"]:
            self._size_combo.addItem(s)
        self._size_combo.setCurrentText("10")
        self._size_combo.setFixedWidth(56)
        self._size_combo.currentTextChanged.connect(self._apply_font_size)
        toolbar_l.addWidget(self._size_combo)

        toolbar_l.addStretch()
        editor_frame_l.addWidget(toolbar_w)

        # Editor con placeholder custom (funciona también con listas)
        self.notes_edit = _NotesEdit("Enter notes here…")
        self.notes_edit.document().setIndentWidth(20)
        _theme = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve()
        )
        _is_dark = not _theme.value("Dark_Light/is_dark_mode", False, type=bool)
        if _is_dark:
            _edit_bg, _edit_color = "#1e1e2e", "#e0e0f0"
            _sb_track, _sb_handle, _sb_handle_hover = "#1e1e2e", "#44446a", "#5a5a8a"
        else:
            _edit_bg, _edit_color = "#f8f8ff", "#1e1e2e"
            _sb_track, _sb_handle, _sb_handle_hover = "#f0f0f8", "#b8b8d0", "#9898b8"
        self.notes_edit.setStyleSheet(
            f"QTextEdit {{ background-color: {_edit_bg}; color: {_edit_color};"
            " border: none; border-radius: 0px; padding: 8px; }"
            f"QScrollBar:vertical {{ background: {_sb_track}; width: 8px; margin: 0; border: none; }}"
            f"QScrollBar::handle:vertical {{ background: {_sb_handle}; border-radius: 4px; min-height: 20px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: {_sb_handle_hover}; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; border: none; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
            f"QScrollBar:horizontal {{ background: {_sb_track}; height: 8px; margin: 0; border: none; }}"
            f"QScrollBar::handle:horizontal {{ background: {_sb_handle}; border-radius: 4px; min-width: 20px; }}"
            f"QScrollBar::handle:horizontal:hover {{ background: {_sb_handle_hover}; }}"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; border: none; }"
            "QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }"
        )
        from PySide6.QtGui import QFont as _QFont
        _default_font = _QFont()
        _default_font.setPointSize(10)
        self.notes_edit.document().setDefaultFont(_default_font)
        self.notes_edit.currentCharFormatChanged.connect(self._sync_toolbar_state)
        self.notes_edit.cursorPositionChanged.connect(self._sync_list_button)
        self.notes_edit.cursorPositionChanged.connect(self._sync_style_combo)
        self.notes_edit.cursorPositionChanged.connect(
            lambda: setattr(self.notes_edit, '_saved_cursor', None)
        )
        editor_frame_l.addWidget(self.notes_edit)

        notes_step_layout.addWidget(editor_frame)
        self.notes_step_widget.setVisible(False)
        main_layout.addWidget(self.notes_step_widget)

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

        self.canvas_frame = QFrame()
        canvas_frame = self.canvas_frame
        canvas_frame.setStyleSheet(
            "QFrame { border: 1px solid #444444; border-radius: 4px; background-color: white; }"
        )
        frame_layout = QVBoxLayout(canvas_frame)
        frame_layout.setContentsMargins(3, 3, 3, 3)
        frame_layout.setSpacing(0)
        frame_layout.addWidget(self.canvas)

        main_layout.addWidget(canvas_frame, alignment=Qt.AlignCenter)
        main_layout.addSpacing(4)

        nav_strip = QHBoxLayout()
        nav_strip.setContentsMargins(8, 2, 8, 2)
        nav_strip.addWidget(self.prev_button)
        nav_strip.addStretch(1)
        nav_strip.addWidget(self.next_button)
        main_layout.addLayout(nav_strip)
        main_layout.addSpacing(2)

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
                    f"QCheckBox {{ color: {colors[slot]}; font-weight: bold; font-size: 12pt; }} " + self._cb_indicator_ss
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

        self.marker_container = QWidget()
        marker_container = self.marker_container
        mc_layout = QHBoxLayout(marker_container)
        mc_layout.setContentsMargins(0, 0, 0, 0)
        mc_layout.addStretch()
        mc_layout.addLayout(self.marker_layout)
        mc_layout.addStretch()
        main_layout.addWidget(marker_container, alignment=Qt.AlignCenter)
        main_layout.addSpacing(4)

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
        if self._data_graph_index(getattr(self, "current_graph_index", 0)) == 1:
            self.fig.subplots_adjust(left=margin, right=1 - margin,
                                     top=1 - margin, bottom=margin)
            self.ax.set_aspect("equal", adjustable="box")
            self.ax.set_anchor("C")
            self.ax.set_xlim(-1.1, 1.1)
            self.ax.set_ylim(-1.1, 1.1)
        self.canvas.draw_idle()

    # ------------------------------------------------------------------ #
    # Rich text toolbar helpers
    # ------------------------------------------------------------------ #

    def _restore_editor_cursor(self):
        """If the editor lost its selection (e.g. focus stolen by toolbar), restore it."""
        edit = self.notes_edit
        current = edit.textCursor()
        if not current.hasSelection():
            saved = edit._saved_cursor
            if saved is not None and saved.hasSelection():
                edit.setTextCursor(saved)
        edit._saved_cursor = None
        edit.setFocus()

    def _apply_char_format(self, fmt, enabled):
        from PySide6.QtGui import QTextCharFormat, QFont
        self._restore_editor_cursor()
        cf = QTextCharFormat()
        if fmt == "bold":
            cf.setFontWeight(QFont.Bold if enabled else QFont.Normal)
        elif fmt == "italic":
            cf.setFontItalic(enabled)
        elif fmt == "underline":
            cf.setFontUnderline(enabled)
        self.notes_edit.mergeCurrentCharFormat(cf)

    def _apply_font_size(self, size_str):
        from PySide6.QtGui import QTextCharFormat
        try:
            size = float(size_str)
        except ValueError:
            return
        self._restore_editor_cursor()
        cf = QTextCharFormat()
        cf.setFontPointSize(size)
        self.notes_edit.mergeCurrentCharFormat(cf)

    _STYLE_PREFIXES = ["", "## ", "### "]
    _STYLE_SIZES    = [10,    14,     12]   # Body=10, Subsection=14, Sub-subsection=12

    def _apply_paragraph_style(self, index):
        from PySide6.QtGui import QTextCharFormat
        prefix    = self._STYLE_PREFIXES[index] if 0 <= index < len(self._STYLE_PREFIXES) else ""
        fixed_pt  = self._STYLE_SIZES[index]    if 0 <= index < len(self._STYLE_SIZES)    else 10
        edit      = self.notes_edit
        cursor    = edit.textCursor()
        cursor.beginEditBlock()
        # Replace prefix in block text
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)
        cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
        text = cursor.selectedText()
        for p in ("### ", "## ", "# "):
            if text.startswith(p):
                text = text[len(p):]
                break
        cursor.insertText(prefix + text)
        # Apply fixed font size to whole block
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)
        cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
        cf = QTextCharFormat()
        cf.setFontPointSize(float(fixed_pt))
        cursor.mergeCharFormat(cf)
        cursor.endEditBlock()
        self._update_size_combo_lock(index, fixed_pt)
        edit.setFocus()

    def _update_size_combo_lock(self, style_index, fixed_pt):
        locked = self._heading_chk.isChecked()   # ALL styles locked when heading mode ON
        self._size_combo.setEnabled(not locked)
        self._size_combo.blockSignals(True)
        self._size_combo.setCurrentText(str(fixed_pt))
        self._size_combo.blockSignals(False)
        label_color = "#4a4a6a" if locked else "#888888"
        self._size_label.setStyleSheet(
            f"QLabel {{ color: {label_color}; font-size: 11px; background: transparent; border: none; }}"
        )

    def _on_heading_mode_toggled(self, checked):
        from PySide6.QtGui import QTextCursor, QTextCharFormat
        self._style_combo.setEnabled(checked)
        if not checked:
            # Strip heading prefixes from all blocks and reset ALL to body size
            edit      = self.notes_edit
            doc       = edit.document()
            cur       = edit.textCursor()
            body_pt   = float(self._STYLE_SIZES[0])
            cur.beginEditBlock()
            block = doc.begin()
            while block.isValid():
                text = block.text()
                bc   = QTextCursor(block)
                bc.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                bc.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                QTextCursor.MoveMode.KeepAnchor)
                for p in ("### ", "## "):
                    if text.startswith(p):
                        bc.insertText(text[len(p):])
                        # re-select after insert
                        bc.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                        bc.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                        QTextCursor.MoveMode.KeepAnchor)
                        break
                cf = QTextCharFormat()
                cf.setFontPointSize(body_pt)
                bc.mergeCharFormat(cf)
                block = block.next()
            cur.endEditBlock()
            self._style_combo.blockSignals(True)
            self._style_combo.setCurrentIndex(0)
            self._style_combo.blockSignals(False)
            self._update_size_combo_lock(0, self._STYLE_SIZES[0])
        else:
            self._sync_style_combo()

    def _sync_style_combo(self):
        if not self._style_combo.isEnabled():
            return
        text = self.notes_edit.textCursor().block().text()
        if text.startswith("### "):
            idx = 2
        elif text.startswith("## "):
            idx = 1
        else:
            idx = 0
        self._style_combo.blockSignals(True)
        self._style_combo.setCurrentIndex(idx)
        self._style_combo.blockSignals(False)
        self._update_size_combo_lock(idx, self._STYLE_SIZES[idx])

    def _on_list_btn_clicked(self, checked):
        if not checked:
            from PySide6.QtGui import QTextBlockFormat
            self.notes_edit.textCursor().setBlockFormat(QTextBlockFormat())
            self.notes_edit.viewport().update()
            self.notes_edit.setFocus()
            return
        # Mostrar picker
        self._btn_list.setChecked(False)   # el picker decide el estado real
        picker = _ListPickerPopup(self)
        picker.styleChosen.connect(self._on_list_style_chosen)
        btn_pos = self._btn_list.mapToGlobal(self._btn_list.rect().bottomLeft())
        picker.move(btn_pos)
        picker.show()

    def _on_list_style_chosen(self, style):
        if style is None:
            from PySide6.QtGui import QTextBlockFormat
            cursor = self.notes_edit.textCursor()
            cursor.setBlockFormat(QTextBlockFormat())
        elif style == _DASH_STYLE:
            # Qt has no native dash list — remove any existing list and insert "– " prefix
            from PySide6.QtGui import QTextBlockFormat
            cursor = self.notes_edit.textCursor()
            cursor.setBlockFormat(QTextBlockFormat())
            if not cursor.block().text().startswith("– "):
                cursor.movePosition(cursor.MoveOperation.StartOfBlock)
                cursor.insertText("– ")
            self.notes_edit.setTextCursor(cursor)
        else:
            self._current_list_style = style
            cursor = self.notes_edit.textCursor()
            fmt = QTextListFormat()
            fmt.setStyle(style)
            cursor.createList(fmt)
            if not cursor.block().text():
                cursor.insertText("  ")
        self._sync_list_button()
        self.notes_edit.viewport().update()   # force placeholder repaint
        self.notes_edit.setFocus()

    def _sync_toolbar_state(self, fmt):
        for w in (self._btn_bold, self._btn_italic, self._btn_underline, self._size_combo):
            w.blockSignals(True)
        self._btn_bold.setChecked(fmt.fontWeight() >= QFont.Bold)
        self._btn_italic.setChecked(fmt.fontItalic())
        self._btn_underline.setChecked(fmt.fontUnderline())
        pt = fmt.fontPointSize()
        if pt <= 0:
            pt = self.notes_edit.document().defaultFont().pointSize()
        if pt > 0:
            self._size_combo.setCurrentText(str(int(pt)))
        for w in (self._btn_bold, self._btn_italic, self._btn_underline, self._size_combo):
            w.blockSignals(False)

    def _sync_list_button(self):
        self._btn_list.blockSignals(True)
        self._btn_list.setChecked(self.notes_edit.textCursor().currentList() is not None)
        self._btn_list.blockSignals(False)

    # ------------------------------------------------------------------ #

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
        is_notes_step = self.include_notes and index == 0
        self.notes_step_widget.setVisible(is_notes_step)
        self.canvas_frame.setVisible(not is_notes_step)
        self.marker_container.setVisible(not is_notes_step)

        if is_notes_step:
            return

        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("white")
        self.fig.subplots_adjust(left=0.15, right=0.90, top=0.90, bottom=0.18)

        dgi = self._data_graph_index(index)
        if dgi == 0:
            self._plot_permittivity()
        else:
            self._plot_smith()
            self.fig.subplots_adjust(left=0.14, right=0.86, top=0.86, bottom=0.14)

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
        self.fig.subplots_adjust(left=0.13, right=0.92, top=0.87, bottom=0.14)

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #

    def _save_fig_at_current(self):
        """Save the current matplotlib figure into saved_figures by data index."""
        if self.include_notes and self.current_graph_index == 0:
            return
        dgi = self._data_graph_index(self.current_graph_index)
        fig_copy = copy.deepcopy(self.fig)
        if dgi >= len(self.saved_figures):
            while len(self.saved_figures) < dgi:
                self.saved_figures.append(None)
            self.saved_figures.append(fig_copy)
        else:
            self.saved_figures[dgi] = fig_copy

    def _show_next_graph(self):
        self._save_fig_at_current()
        if self.current_graph_index < self.TOTAL_GRAPHS - 1:
            self.current_graph_index += 1
            self._plot_graph(self.current_graph_index)
            self._update_nav_buttons()
            self._update_marker_checkboxes()
        self.export_button.setEnabled(self.current_graph_index == self.TOTAL_GRAPHS - 1)

    def _show_previous_graph(self):
        self._save_fig_at_current()
        if self.current_graph_index > 0:
            self.current_graph_index -= 1
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

        # Notes step has no markers/axes
        if self.include_notes and graph_index == 0:
            return

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

        dgi = self._data_graph_index(graph_index)
        cbs = self.marker_checkboxes[graph_index]
        edits_combos = self.marker_freq_edits[graph_index]
        self.marker_active[dgi] = [cbs[s].isChecked() for s in range(n)]

        _xlim = ax.get_xlim()
        _ylim = ax.get_ylim()

        for slot in range(n):
            active = self.marker_active[dgi][slot]
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

                if dgi == 1:
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
                    self.marker_positions[dgi][slot]
                    if self.marker_positions[dgi][slot] else (x, y)
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
                self.marker_positions[dgi][slot] = (ann_x, ann_y)

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
        _enable_drag_annotations_shared(
            self,
            page_key_fn=lambda: self._data_graph_index(self.current_graph_index),
        )

    # ------------------------------------------------------------------ #
    # PDF generation
    # ------------------------------------------------------------------ #

    def _save_current_graph(self):
        self._save_fig_at_current()

    def _generate_pdf(self):
        """Rasterize the previews here, then compile LaTeX on a worker thread.

        LaTeX takes several seconds; running it inline froze the dialog with no
        sign the click had registered. The split keeps matplotlib on the UI
        thread (it is not thread-safe) and only hands off the compilation.
        """
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

        # Derive display name from chosen filename:
        # strip folder + extension, then strip "characterization_" prefix if present
        import os as _os
        _stem = _os.path.splitext(_os.path.basename(output_path))[0]
        _PREFIX = "characterization_"
        if _stem.lower().startswith(_PREFIX):
            _stem = _stem[len(_PREFIX):]
        display_sample_name = _stem.capitalize() if _stem else self.sample_name

        busy = GeneratingButton(self.export_button, "Generating report…")
        busy.begin()

        tmp_dir = tempfile.mkdtemp(prefix="nanovna_report_")
        try:
            image_files = exporter.render_images(
                self.freqs, self.s11_data, self.eps_selected, tmp_dir,
                wizard_window=self.wizard_window,
                include_steps=self.include_steps,
            )
        except Exception as exc:
            logger.exception("[PermittivityPdfPreviewDialog] figure rendering failed")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            busy.end()
            QMessageBox.critical(self, "Export Failed", f"Could not render the plots:\n{exc}")
            return

        notes_doc = self.notes_edit.document() if self.include_notes else None

        def _compile():
            exporter.compile_pdf(
                freqs=self.freqs,
                eps_selected=self.eps_selected,
                s11_data=self.s11_data,
                image_files=image_files,
                sample_name=display_sample_name,
                wizard_window=self.wizard_window,
                output_path=output_path,
                compiler_path=compiler_info[1],
                include_steps=self.include_steps,
                notes_doc=notes_doc,
                include_tables=self.include_tables,
            )

        def _on_done(success, error_message):
            shutil.rmtree(tmp_dir, ignore_errors=True)
            busy.end()
            self._pdf_task = None
            if success:
                export_folder = getattr(exporter, '_last_export_folder', None)
                location = str(export_folder) if export_folder else output_path
                QMessageBox.information(
                    self, "Export Complete",
                    f"PDF successfully created in:\n{location}",
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self, "Export Failed",
                    f"Failed to generate PDF:\n{error_message}",
                )

        # Held on the dialog so the thread is not garbage-collected mid-run.
        self._pdf_task = PdfCompileTask(_compile, parent=self)
        self._pdf_task.completed.connect(_on_done)
        self._pdf_task.start()
