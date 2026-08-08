from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MaxNLocator
from pathlib import Path
from typing import Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGroupBox,
    QColorDialog, QSpinBox, QSizePolicy, QSpacerItem,
)
from PySide6.QtCore import Qt

from NanoVNA_UTN_Toolkit.utils import safe_import

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)

_INI_EXE = "INI/material_characterization/characterization_chart_config/characterization_chart_config.ini"
_INI_DEV = "modules/material_characterization/ui/measurement_main_window/characterization_chart_config/characterization_chart_config.ini"

_DL_INI_EXE = "INI/dut_measurement/dark_light_config/dark_light_config.ini"
_DL_INI_DEV = "shared/utils/dark_light_mode/dark_light_config.ini"


def _qframe_color(caller_path: Path) -> str:
    s = get_settings(_DL_INI_EXE, _DL_INI_DEV, caller_path)
    return s.value("Dark_Light/QFrame/background-color", "white")


def _separator(color: str) -> QFrame:
    line = QFrame()
    line.setStyleSheet(f"background-color: {color}; color: {color};")
    line.setObjectName("separatorLine")
    line.setFixedHeight(2)
    return line

_GROUPBOX_STYLE = (
    "QGroupBox { border: 1px solid #b0b0b0; border-radius: 5px; margin-top: 1.3ex;"
    " padding-top: 6px; }"
    " QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }"
)
_CANVAS_SIZE = 360


def _swatch(color: str) -> QFrame:
    f = QFrame()
    f.setFixedSize(26, 26)
    f.setStyleSheet(
        f"background-color: {color}; border: 1px solid white; border-radius: 6px;"
    )
    return f


def _get_color(widget: QFrame) -> str:
    return widget.styleSheet().split("background-color:")[1].split(";")[0].strip()


def _pick_color(btn: QFrame, on_change):
    def handler(event=None):
        color = QColorDialog.getColor()
        if color.isValid():
            btn.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid white; border-radius: 6px;"
            )
            on_change()
    return handler


def _fill_nans(y: np.ndarray) -> np.ndarray:
    finite = np.isfinite(y)
    if finite.all() or not finite.any():
        return y
    x = np.arange(len(y))
    out = y.copy()
    out[~finite] = np.interp(x[~finite], x[finite], y[finite])
    return out


def _dummy_data():
    freqs = np.linspace(1e6, 3e9, 101)
    real_data = np.linspace(80, 20, 101)
    loss_data = np.linspace(30, 5, 101)
    return freqs, real_data, loss_data


def _label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 11pt;")
    return lbl


def _color_row(label_text: str, color: str):
    """Return (layout, swatch_widget)."""
    row = QHBoxLayout()
    row.addWidget(_label(label_text))
    btn = _swatch(color)
    row.addWidget(btn, alignment=Qt.AlignVCenter)
    return row, btn


def _spin_row(label_text: str, value: int):
    """Return (layout, spinbox_widget)."""
    row = QHBoxLayout()
    row.addWidget(_label(label_text))
    spin = QSpinBox()
    spin.setRange(1, 10)
    spin.setValue(value)
    spin.setAlignment(Qt.AlignCenter)
    spin.setFixedWidth(46)
    row.addWidget(spin, alignment=Qt.AlignVCenter)
    return row, spin


####################################################################################################
# Tab ε' (parte real)
####################################################################################################

def create_tab_real(main_window, texts: Dict):
    """
    Tab for ε' (real part).
    Controls: trace color + width, markers, background color, text color, axis color.
    Preview shows only the ε' curve.

    Returns (tab_widget, get_trace_color, get_trace_width,
             get_marker1_color, get_marker2_color, get_marker1_size, get_marker2_size,
             get_bg_color, get_text_color, get_axis_color).
    """
    t_trace = texts.get("trace", {})
    t_markers = texts.get("markers", {})
    t_chart = texts.get("chart_settings", {})
    t_groups = texts.get("groups", {})

    caller = Path(__file__).resolve()
    qfc = _qframe_color(caller)

    settings = get_settings(_INI_EXE, _INI_DEV, caller)
    tc = settings.value("Epsilon_Real/TraceColor", "#4da6ff")
    tw = int(settings.value("Epsilon_Real/TraceWidth", 2))
    mc1 = settings.value("Epsilon_Real/MarkerColor1", "#ff0000")
    mc2 = settings.value("Epsilon_Real/MarkerColor2", "#ffff00")
    ms1 = int(settings.value("Epsilon_Real/MarkerWidth1", 6))
    ms2 = int(settings.value("Epsilon_Real/MarkerWidth2", 6))
    bg = settings.value("Epsilon_Real/BackgroundColor", "#1e1e1e")
    txt = settings.value("Epsilon_Real/TextColor", "#cccccc")
    ax_c = settings.value("Epsilon_Real/AxisColor", "#555555")

    tab = QWidget()
    tab_layout = QVBoxLayout(tab)
    tab_layout.setContentsMargins(0, 0, 0, 0)
    tab_layout.setSpacing(0)
    tab_layout.addWidget(_separator(qfc))
    tab_layout.addItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

    content = QWidget()
    h_layout = QHBoxLayout(content)
    h_layout.setContentsMargins(12, 0, 12, 0)
    h_layout.setSpacing(20)
    h_layout.setAlignment(Qt.AlignVCenter)
    tab_layout.addWidget(content)

    # --- Controls ---
    ctrl = QWidget()
    v_layout = QVBoxLayout(ctrl)
    v_layout.setContentsMargins(0, 0, 0, 0)
    v_layout.setSpacing(20)
    v_layout.setAlignment(Qt.AlignHCenter)

    # GroupBox: Curve ε'
    grp_curve = QGroupBox(t_groups.get("curve_real", " Edit Curve ε′ "))
    grp_curve.setStyleSheet(_GROUPBOX_STYLE)
    gl = QVBoxLayout(grp_curve)
    gl.setAlignment(Qt.AlignTop)
    gl.setSpacing(20)
    gl.setContentsMargins(10, 10, 10, 5)

    row_tc, btn_trace = _color_row(t_trace.get("trace_color", "Trace color:"), tc)
    gl.addLayout(row_tc)

    row_tw, spin_w = _spin_row(t_trace.get("trace_width", "Trace width:"), tw)
    gl.addLayout(row_tw)

    # GroupBox: Markers
    grp_markers = QGroupBox(t_groups.get("markers", " Edit Markers "))
    grp_markers.setStyleSheet(_GROUPBOX_STYLE)
    gml = QVBoxLayout(grp_markers)
    gml.setAlignment(Qt.AlignTop)
    gml.setSpacing(20)
    gml.setContentsMargins(10, 10, 10, 5)

    row_mc1, btn_mc1 = _color_row(t_markers.get("marker_1_color", "Marker 1 color:"), mc1)
    gml.addLayout(row_mc1)
    row_mc2, btn_mc2 = _color_row(t_markers.get("marker_2_color", "Marker 2 color:"), mc2)
    gml.addLayout(row_mc2)
    row_ms1, spin_ms1 = _spin_row(t_markers.get("marker_1_size", "Marker 1 size:"), ms1)
    spin_ms1.setRange(1, 20)
    gml.addLayout(row_ms1)
    row_ms2, spin_ms2 = _spin_row(t_markers.get("marker_2_size", "Marker 2 size:"), ms2)
    spin_ms2.setRange(1, 20)
    gml.addLayout(row_ms2)

    # GroupBox: Chart
    grp_chart = QGroupBox(t_groups.get("chart", " Chart "))
    grp_chart.setStyleSheet(_GROUPBOX_STYLE)
    gcl = QVBoxLayout(grp_chart)
    gcl.setAlignment(Qt.AlignTop)
    gcl.setSpacing(20)
    gcl.setContentsMargins(10, 10, 10, 5)

    row_bg, btn_bg = _color_row(t_chart.get("background_color", "Background color:"), bg)
    gcl.addLayout(row_bg)
    row_txt, btn_text = _color_row(t_chart.get("text_color", "Text color:"), txt)
    gcl.addLayout(row_txt)
    row_ax, btn_axis = _color_row(t_chart.get("axis_color", "Axis color:"), ax_c)
    gcl.addLayout(row_ax)

    grp_curve.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    grp_markers.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    grp_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    v_layout.addWidget(grp_curve)
    v_layout.addWidget(grp_markers)
    v_layout.addWidget(grp_chart)

    # --- Canvas ---
    fig, ax = plt.subplots(figsize=(3.2, 3.2))
    fig.subplots_adjust(left=0.22, right=0.95, top=0.88, bottom=0.18)
    canvas = FigureCanvas(fig)
    canvas.setFixedSize(_CANVAS_SIZE, _CANVAS_SIZE)

    result = getattr(main_window, "_result", None)
    if result is not None:
        freqs     = result.f_hz
        real_data = _fill_nans(np.real(result.eps_selected))
    else:
        freqs, real_data, _ = _dummy_data()

    def draw():
        ax.clear()
        c    = _get_color(btn_trace)
        bg_c = _get_color(btn_bg)
        tc_c = _get_color(btn_text)
        ac_c = _get_color(btn_axis)
        w    = spin_w.value()
        fig.patch.set_facecolor(bg_c)
        ax.set_facecolor(bg_c)
        ax.plot(freqs / 1e6, real_data, color=c, linewidth=w, label=r"$\varepsilon_r'$")
        _mk_s = get_settings(_INI_EXE, _INI_DEV, Path(__file__).resolve())
        _idx1 = min(max(int(_mk_s.value("markers/index_1", 0)), 0), len(freqs) - 1)
        ax.plot(freqs[_idx1] / 1e6, real_data[_idx1], "o",
                color=_get_color(btn_mc1), markersize=spin_ms1.value(), zorder=5)
        ax.set_xlabel("Frequency (MHz)", color=tc_c, fontsize=9)
        ax.set_ylabel(r"$\varepsilon_r'$", color=tc_c, fontsize=10)
        ax.set_title(r"$\varepsilon_r'$", color=tc_c, fontsize=10, pad=6)
        ax.tick_params(colors=ac_c, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(ac_c)
        ax.grid(True, linestyle=":", alpha=0.4, color=ac_c)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.legend(loc="upper right", labelcolor=tc_c, facecolor=bg_c,
                  edgecolor=ac_c, fontsize=8)
        canvas.draw()

    draw()

    btn_trace.mousePressEvent = _pick_color(btn_trace, draw)
    btn_mc1.mousePressEvent   = _pick_color(btn_mc1, draw)
    btn_mc2.mousePressEvent   = _pick_color(btn_mc2, draw)
    btn_bg.mousePressEvent    = _pick_color(btn_bg, draw)
    btn_text.mousePressEvent  = _pick_color(btn_text, draw)
    btn_axis.mousePressEvent  = _pick_color(btn_axis, draw)
    spin_w.valueChanged.connect(lambda _: draw())
    spin_ms1.valueChanged.connect(lambda _: draw())
    spin_ms2.valueChanged.connect(lambda _: draw())

    def get_trace_color(): return _get_color(btn_trace)
    def get_trace_width(): return spin_w.value()
    def get_marker1_color(): return _get_color(btn_mc1)
    def get_marker2_color(): return _get_color(btn_mc2)
    def get_marker1_size(): return spin_ms1.value()
    def get_marker2_size(): return spin_ms2.value()
    def get_bg_color(): return _get_color(btn_bg)
    def get_text_color(): return _get_color(btn_text)
    def get_axis_color(): return _get_color(btn_axis)

    h_layout.addWidget(ctrl, 1, Qt.AlignVCenter)
    h_layout.addWidget(canvas, 0, Qt.AlignVCenter)

    tab_layout.addItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

    return (tab, get_trace_color, get_trace_width,
            get_marker1_color, get_marker2_color, get_marker1_size, get_marker2_size,
            get_bg_color, get_text_color, get_axis_color)


####################################################################################################
# Tab ε'' (pérdidas)
####################################################################################################

def create_tab_imag(main_window, texts: Dict):
    """
    Tab for ε'' (loss part).
    Controls: trace color + width, background color, text color, axis color.
    The shared chart settings (bg, text, axis) read from INI for preview context;
    on Apply the window uses Tab ε' values for those shared fields.

    Returns (tab_widget, get_trace_color, get_trace_width,
             get_marker1_color, get_marker2_color, get_marker1_size, get_marker2_size).
    """
    t_trace = texts.get("trace", {})
    t_markers = texts.get("markers", {})
    t_chart = texts.get("chart_settings", {})
    t_groups = texts.get("groups", {})

    caller = Path(__file__).resolve()
    qfc = _qframe_color(caller)

    settings = get_settings(_INI_EXE, _INI_DEV, caller)
    tc = settings.value("Epsilon_Imag/TraceColor", "#d62728")
    tw = int(settings.value("Epsilon_Imag/TraceWidth", 2))
    mc1 = settings.value("Epsilon_Imag/MarkerColor1", "#ff0000")
    mc2 = settings.value("Epsilon_Imag/MarkerColor2", "#ffff00")
    ms1 = int(settings.value("Epsilon_Imag/MarkerWidth1", 6))
    ms2 = int(settings.value("Epsilon_Imag/MarkerWidth2", 6))
    bg = settings.value("Epsilon_Real/BackgroundColor", "#1e1e1e")
    txt = settings.value("Epsilon_Real/TextColor", "#cccccc")
    ax_c = settings.value("Epsilon_Real/AxisColor", "#555555")

    tab = QWidget()
    tab_layout = QVBoxLayout(tab)
    tab_layout.setContentsMargins(0, 0, 0, 0)
    tab_layout.setSpacing(0)
    tab_layout.addWidget(_separator(qfc))
    tab_layout.addItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

    content = QWidget()
    h_layout = QHBoxLayout(content)
    h_layout.setContentsMargins(12, 0, 12, 0)
    h_layout.setSpacing(20)
    h_layout.setAlignment(Qt.AlignVCenter)
    tab_layout.addWidget(content)

    # --- Controls ---
    ctrl = QWidget()
    v_layout = QVBoxLayout(ctrl)
    v_layout.setContentsMargins(0, 0, 0, 0)
    v_layout.setSpacing(20)
    v_layout.setAlignment(Qt.AlignHCenter)

    # GroupBox: Curve ε''
    grp_curve = QGroupBox(t_groups.get("curve_imag", " Edit Curve ε″ "))
    grp_curve.setStyleSheet(_GROUPBOX_STYLE)
    gl = QVBoxLayout(grp_curve)
    gl.setAlignment(Qt.AlignTop)
    gl.setSpacing(20)
    gl.setContentsMargins(10, 10, 10, 5)

    row_tc, btn_trace = _color_row(t_trace.get("trace_color", "Trace color:"), tc)
    gl.addLayout(row_tc)

    row_tw, spin_w = _spin_row(t_trace.get("trace_width", "Trace width:"), tw)
    gl.addLayout(row_tw)

    # GroupBox: Markers
    grp_markers = QGroupBox(t_groups.get("markers", " Edit Markers "))
    grp_markers.setStyleSheet(_GROUPBOX_STYLE)
    gml = QVBoxLayout(grp_markers)
    gml.setAlignment(Qt.AlignTop)
    gml.setSpacing(20)
    gml.setContentsMargins(10, 10, 10, 5)

    row_mc1, btn_mc1 = _color_row(t_markers.get("marker_1_color", "Marker 1 color:"), mc1)
    gml.addLayout(row_mc1)
    row_mc2, btn_mc2 = _color_row(t_markers.get("marker_2_color", "Marker 2 color:"), mc2)
    gml.addLayout(row_mc2)
    row_ms1, spin_ms1 = _spin_row(t_markers.get("marker_1_size", "Marker 1 size:"), ms1)
    spin_ms1.setRange(1, 20)
    gml.addLayout(row_ms1)
    row_ms2, spin_ms2 = _spin_row(t_markers.get("marker_2_size", "Marker 2 size:"), ms2)
    spin_ms2.setRange(1, 20)
    gml.addLayout(row_ms2)

    # GroupBox: Chart (shared settings - for preview coherence)
    grp_chart = QGroupBox(t_groups.get("chart", " Chart "))
    grp_chart.setStyleSheet(_GROUPBOX_STYLE)
    gcl = QVBoxLayout(grp_chart)
    gcl.setAlignment(Qt.AlignTop)
    gcl.setSpacing(20)
    gcl.setContentsMargins(10, 10, 10, 5)

    row_bg, btn_bg = _color_row(t_chart.get("background_color", "Background color:"), bg)
    gcl.addLayout(row_bg)
    row_txt, btn_text = _color_row(t_chart.get("text_color", "Text color:"), txt)
    gcl.addLayout(row_txt)
    row_ax, btn_axis = _color_row(t_chart.get("axis_color", "Axis color:"), ax_c)
    gcl.addLayout(row_ax)

    grp_curve.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    grp_markers.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    grp_chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    v_layout.addWidget(grp_curve)
    v_layout.addWidget(grp_markers)
    v_layout.addWidget(grp_chart)

    # --- Canvas ---
    fig, ax = plt.subplots(figsize=(3.2, 3.2))
    fig.subplots_adjust(left=0.22, right=0.95, top=0.88, bottom=0.18)
    canvas = FigureCanvas(fig)
    canvas.setFixedSize(_CANVAS_SIZE, _CANVAS_SIZE)

    result = getattr(main_window, "_result", None)
    if result is not None:
        freqs     = result.f_hz
        loss_data = _fill_nans(-np.imag(result.eps_selected))
    else:
        freqs, _, loss_data = _dummy_data()

    def draw():
        ax.clear()
        c    = _get_color(btn_trace)
        bg_c = _get_color(btn_bg)
        tc_c = _get_color(btn_text)
        ac_c = _get_color(btn_axis)
        w    = spin_w.value()
        fig.patch.set_facecolor(bg_c)
        ax.set_facecolor(bg_c)
        ax.plot(freqs / 1e6, loss_data, color=c, linewidth=w, label=r"$\varepsilon_r''$")
        _mk_s = get_settings(_INI_EXE, _INI_DEV, Path(__file__).resolve())
        _idx2 = min(max(int(_mk_s.value("markers/index_2", 0)), 0), len(freqs) - 1)
        ax.plot(freqs[_idx2] / 1e6, loss_data[_idx2], "o",
                color=_get_color(btn_mc1), markersize=spin_ms1.value(), zorder=5)
        ax.set_xlabel("Frequency (MHz)", color=tc_c, fontsize=9)
        ax.set_ylabel(r"$\varepsilon_r''$", color=tc_c, fontsize=10)
        ax.set_title(r"$\varepsilon_r''$", color=tc_c, fontsize=10, pad=6)
        ax.tick_params(colors=ac_c, labelsize=7)
        for spine in ax.spines.values():
            spine.set_color(ac_c)
        ax.grid(True, linestyle=":", alpha=0.4, color=ac_c)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
        ax.legend(loc="upper right", labelcolor=tc_c, facecolor=bg_c,
                  edgecolor=ac_c, fontsize=8)
        canvas.draw()

    draw()

    btn_trace.mousePressEvent = _pick_color(btn_trace, draw)
    btn_mc1.mousePressEvent   = _pick_color(btn_mc1, draw)
    btn_mc2.mousePressEvent   = _pick_color(btn_mc2, draw)
    btn_bg.mousePressEvent    = _pick_color(btn_bg, draw)
    btn_text.mousePressEvent  = _pick_color(btn_text, draw)
    btn_axis.mousePressEvent  = _pick_color(btn_axis, draw)
    spin_w.valueChanged.connect(lambda _: draw())
    spin_ms1.valueChanged.connect(lambda _: draw())
    spin_ms2.valueChanged.connect(lambda _: draw())

    def get_trace_color(): return _get_color(btn_trace)
    def get_trace_width(): return spin_w.value()
    def get_marker1_color(): return _get_color(btn_mc1)
    def get_marker2_color(): return _get_color(btn_mc2)
    def get_marker1_size(): return spin_ms1.value()
    def get_marker2_size(): return spin_ms2.value()

    h_layout.addWidget(ctrl, 1, Qt.AlignVCenter)
    h_layout.addWidget(canvas, 0, Qt.AlignVCenter)

    tab_layout.addItem(QSpacerItem(0, 8, QSizePolicy.Minimum, QSizePolicy.Fixed))

    return (tab, get_trace_color, get_trace_width,
            get_marker1_color, get_marker2_color, get_marker1_size, get_marker2_size)
