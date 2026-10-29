"""
Measurement results window for material characterization.

EN: Displays the computed complex permittivity of the unknown liquid: an info
    strip (technique, temperature, reference liquids, sweep) and a full-width
    epsilon_r(f) chart. The results table and the DUT S11 Smith chart are
    accessible from the View menu. Export is available via right-click on the
    chart.

ES: Muestra la permitividad compleja calculada del líquido incógnita: una
    franja de información y un gráfico epsilon_r(f) a pantalla completa.
    La tabla de resultados y el diagrama de Smith S11 están en el menú View.
    El export se realiza con click derecho sobre el gráfico.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import re
import sys
import logging
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QObject, QPoint, QThread, QTimer, Signal

from NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.blit_manager import RealtimeBlitter
from NanoVNA_UTN_Toolkit.shared.utils.background_task import run_in_background, detach_background_threads
from PySide6.QtGui import QAction, QColor, QGuiApplication, QIcon, QPainter, QPixmap, QPolygon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMenu,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)

_CHART_INI_EXE = "INI/material_characterization/characterization_chart_config/characterization_chart_config.ini"
_CHART_INI_DEV = "modules/material_characterization/ui/measurement_main_window/characterization_chart_config/characterization_chart_config.ini"

_PM_INI_EXE = "INI/material_characterization/plot_manager/plot_manager.ini"
_PM_INI_DEV = "modules/material_characterization/ui/measurement_main_window/utils/menu/plot_manager/plot_manager.ini"

try:
    from NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode import dark_light_config
    from NanoVNA_UTN_Toolkit.modules.menu_window import ModuleSelectionWindow
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    sys.exit(1)

apply_window_icon = safe_import("NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon")

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.permittivity_columns import (
    loss_tangent,
    nonpassive_mask_of,
    permittivity_columns,
    scale_limits,
    shade_unusable_band,
    usable_band_of,
    write_permittivity_csv,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid,
)

_MAX_TABLE_ROWS = 500

def _hsep(color="#383850"):
    line = QWidget()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background-color: {color}; border: none;")
    return line


class MeasurementMainWindow(QMainWindow):

    def __init__(self, vna_device=None, wizard_window=None):
        super().__init__()

        self.vna = vna_device
        self.wizard_window = wizard_window
        self._texts = load_text("characterization_measurement_main.json")
        self._epsilon_fig = None
        self._s11_fig = None
        self._epsilon_canvas = None
        self._epsilon_manager = None
        self._epsilon_ax = None
        # Real-time ticks update the ε curves in place and blit them while this
        # is on; _chart_key_drawn is the static part of the last full redraw.
        self._trace_blit_active = False
        self._chart_key_drawn = None
        self._result = None
        self._sweep_in_progress = False
        self._window_closed = False
        self._sweep_mode = "device"          # "device" | "file"
        self._file_sweep_config = []         # list of {"path": str, "name": str}
        self._file_sweep_idx = 0
        self._file_sweep_saved_names: list = []  # user-built pool of reusable names
        self._realtime_timer = QTimer(self)
        self._realtime_timer.setInterval(2000)
        self._realtime_timer.timeout.connect(self._run_one_sweep)
        self._bg_threads: list = []          # file-mode parse+solve running off the GUI thread
        # Marker/link INI writes are batched: one QSettings write per burst of
        # slider moves instead of one per event (1-2 ms each, every tick too).
        self._ini_pending: dict = {}
        self._ini_timer = QTimer(self)
        self._ini_timer.setSingleShot(True)
        self._ini_timer.setInterval(250)
        self._ini_timer.timeout.connect(self._flush_ini)

        # Signal filter state (Smoothing / Kalman applied to ε after calculation)
        self._active_filter     = "Off"
        self._filter_smooth_pct = 5
        self._kf_eps            = None   # ComplexKalman, reset on settings change
        self._display_eps       = None   # filtered complex eps array used for plotting

        self.setWindowTitle(self._texts.get("window_title", "Material Characterization - Results"))
        screen = QGuiApplication.primaryScreen().availableGeometry()
        w = min(1171, screen.width() - 40)
        h = min(858, screen.height() - 40)
        self.setGeometry(
            screen.x() + (screen.width() - w) // 2,
            screen.y() + (screen.height() - h) // 2,
            w, h,
        )
        self.setMinimumSize(780, 560)

        apply_window_icon(self)
        dark_light_config(self)
        _dl = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve(),
        )
        # In this codebase is_dark_mode=False means dark mode is active (inverted naming).
        self.is_dark_mode = _dl.value("Dark_Light/is_dark_mode", False, type=bool)
        self._is_dark = not self.is_dark_mode

        _app_bg   = "#1e1e2e" if self._is_dark else "#f0f0f8"
        _card_bg  = "#252538" if self._is_dark else "#f8f8ff"
        _card_bdr = "#383850" if self._is_dark else "#c4c4d8"
        self._app_bg  = _app_bg
        self._card_bg = _card_bg
        self._card_bdr = _card_bdr

        # dark_light_config already sets QWidget bg globally; only isolate #mainContent
        # so the card children don't inherit the app bg and override the card color.
        self.central_widget = QWidget()
        self.central_widget.setObjectName("mainContent")
        self.central_widget.setStyleSheet(f"#mainContent {{ background-color: {_app_bg}; }}")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 14, 20, 14)
        self.main_layout.setSpacing(10)

        self._build_header()
        self.main_layout.addWidget(_hsep())
        self._build_info_strip()
        self.main_layout.addWidget(self._build_sweep_controls())
        self.main_layout.addWidget(_hsep())
        self._build_body()
        self._create_menus()

    # --------------------------------------------------------------------- #

    def setStyleSheet(self, stylesheet: str) -> None:
        super().setStyleSheet(stylesheet)
        if not hasattr(self, "central_widget"):
            return
        # During toggle: is_dark_mode=True means switching TO dark (inverted naming).
        _going_dark = getattr(self, "is_dark_mode", False)
        self._is_dark  = _going_dark
        self._app_bg   = "#1e1e2e" if _going_dark else "#f0f0f8"
        self._card_bg  = "#252538" if _going_dark else "#f8f8ff"
        self._card_bdr = "#383850" if _going_dark else "#c4c4d8"
        self.central_widget.setStyleSheet(
            f"#mainContent {{ background-color: {self._app_bg}; }}"
        )

    # --------------------------------------------------------------------- #

    def _build_header(self):
        title = QLabel(self._texts.get("title", "Permittivity Results"))
        title.setAlignment(Qt.AlignCenter)
        _title_fg    = "#e8e8f0" if self._is_dark else "#1a1a2e"
        _subtitle_fg = "#8888a0" if self._is_dark else "#606080"
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {_title_fg}; border: none; background: transparent;")
        subtitle = QLabel("Complex permittivity ε_r(f) of the characterized material")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"font-size: 12px; color: {_subtitle_fg}; border: none; background: transparent;")
        self.main_layout.addWidget(title)
        self.main_layout.addWidget(subtitle)

    # --------------------------------------------------------------------- #

    def _probe_text(self):
        """Probe of the session and the C0 of its capacitive model."""
        from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.probe_models import get_probe

        probe = get_probe(getattr(getattr(self.wizard_window, "perm_calibration", None),
                                  "probe_key", None))
        names = load_text("characterization_wizard.json").get("probes", {})
        return f"{names.get(probe.key, probe.display_name)} (C0 {probe.c0_f * 1e12:.3g} pF)"

    def _temperature_text(self, temp):
        """Session temperature, plus the one of any reference loaded from a preset."""
        if temp is None:
            return "—"
        text = f"{temp:.1f} °C"
        cal = getattr(self.wizard_window, "perm_calibration", None)
        if cal is None:
            return text
        own = sorted({
            round(float(t), 1)
            for t in (cal.standard_temperature("ref1"), cal.standard_temperature("ref2"))
            if t is not None
        })
        if own:
            preset = self._texts.get("info", {}).get("temperature_preset", "ref. preset")
            text += f" ({preset}: " + ", ".join(f"{t:.1f} °C" for t in own) + ")"
        return text

    def _build_info_strip(self):
        info = self._texts.get("info", {})
        wiz = self.wizard_window
        cal = getattr(wiz, "perm_calibration", None)

        technique = getattr(wiz, "selected_method", "") or "—"
        temp = getattr(wiz, "temperature_c", None)
        start = getattr(wiz, "sweep_start_freq", None)
        stop = getattr(wiz, "sweep_stop_freq", None)
        steps = getattr(wiz, "sweep_steps", None)

        refs_text = "—"
        if cal is not None and cal.ref1_key:
            refs_text = get_reference_liquid(cal.ref1_key).display_name
            # The simplified technique uses a single reference (ref2 is None).
            if cal.ref2_key:
                refs_text += f" / {get_reference_liquid(cal.ref2_key).display_name}"

        items = [
            (info.get("technique",    "Technique"),   technique),
            (info.get("temperature",  "Temperature"), self._temperature_text(temp)),
            (info.get("references",   "References"),  refs_text),
            (info.get("probe",        "Probe"),       self._probe_text()),
            (info.get("sweep",        "Sweep"),
             (
                 "–".join(
                     f"{hz/1e9:.3f} GHz" if hz >= 1e9
                     else f"{hz/1e6:.3f} MHz" if hz >= 1e6
                     else f"{hz/1e3:.1f} kHz"
                     for hz in (start, stop)
                 ) + f" · {steps} pts"
             ) if start is not None and stop is not None else "—"),
        ]

        if self._is_dark:
            _BADGE = (
                "background-color: #1e2a3a; border: 1px solid #2d5a8e;"
                " border-radius: 6px; padding: 4px 14px;"
            )
            _KEY_STYLE = "font-size: 10px; font-weight: bold; color: #5a8fc0; border: none; background: transparent;"
            _VAL_STYLE = "font-size: 12px; color: #7ab3f5; border: none; background: transparent;"
        else:
            _BADGE = (
                "background-color: #dce8f8; border: 1px solid #a0bcd8;"
                " border-radius: 6px; padding: 4px 14px;"
            )
            _KEY_STYLE = "font-size: 10px; font-weight: bold; color: #2a5580; border: none; background: transparent;"
            _VAL_STYLE = "font-size: 12px; color: #1a3a5c; border: none; background: transparent;"

        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 6, 0, 6)

        for label_text, value_text in items:
            badge = QWidget()
            badge.setStyleSheet(_BADGE)
            badge_layout = QVBoxLayout(badge)
            badge_layout.setContentsMargins(10, 6, 10, 6)
            badge_layout.setSpacing(2)

            key_lbl = QLabel(label_text.rstrip(":"))
            key_lbl.setAlignment(Qt.AlignCenter)
            key_lbl.setStyleSheet(_KEY_STYLE)

            val_lbl = QLabel(value_text)
            val_lbl.setAlignment(Qt.AlignCenter)
            val_lbl.setStyleSheet(_VAL_STYLE)

            badge_layout.addWidget(key_lbl)
            badge_layout.addWidget(val_lbl)
            row.addWidget(badge, stretch=1)

        self.main_layout.addLayout(row)

    # --------------------------------------------------------------------- #

    def _build_sweep_controls(self):
        """Sweep control bar: compact status left, solid blue Run Sweep right, symmetric."""
        if self._is_dark:
            _bg      = "#1e2a3a"
            _border  = "#2d5a8e"
            _fg      = "#7ab3f5"
            _sep_col = "#2d5a8e"
            _btn_bg  = "#2d6abf"
            _btn_hover = "#3a7fd4"
            _btn_press = "#1e5099"
        else:
            _bg      = "#dce8f8"
            _border  = "#a0bcd8"
            _fg      = "#1a3a5c"
            _sep_col = "#a0bcd8"
            _btn_bg  = "#2d6abf"
            _btn_hover = "#3a7fd4"
            _btn_press = "#1e5099"

        _CONTAINER = (
            f"QWidget#sweepBar {{ background-color: {_bg}; border: 1px solid {_border};"
            f" border-radius: 6px; }}"
        )
        _LBL = f"font-size: 12px; color: {_fg}; border: none; background: transparent;"
        _CHK = (
            f"QCheckBox {{ color: {_fg}; font-size: 12px; spacing: 6px;"
            f" border: none; background: transparent; }}"
            f" QCheckBox::indicator {{"
            f"  width: 14px; height: 14px;"
            f"  border: 2px solid {_border}; border-radius: 3px;"
            f"  background-color: transparent; }}"
            f" QCheckBox::indicator:checked {{"
            f"  background-color: #2196f3; border-color: #2196f3; }}"
            f" QCheckBox::indicator:unchecked {{ background-color: transparent; }}"
        )
        _BTN = (
            f"QPushButton {{ background-color: {_btn_bg}; color: #ffffff;"
            f" border: none; border-radius: 4px;"
            f" font-size: 12px; font-weight: bold; padding: 0 14px; }}"
            f" QPushButton:hover {{ background-color: {_btn_hover}; }}"
            f" QPushButton:pressed {{ background-color: {_btn_press}; }}"
            f" QPushButton:disabled {{ background-color: #444455; color: #888888; }}"
        )

        outer = QWidget()
        outer.setStyleSheet("background: transparent; border: none;")
        outer_row = QHBoxLayout(outer)
        outer_row.setContentsMargins(0, 6, 0, 6)
        outer_row.setSpacing(0)

        bar = QWidget()
        bar.setObjectName("sweepBar")
        bar.setStyleSheet(_CONTAINER)
        inner = QHBoxLayout(bar)
        inner.setContentsMargins(14, 10, 14, 10)
        inner.setSpacing(10)

        # Left: compact status section (green dot + label, not stretching)
        self._sweep_dot = QLabel()
        self._sweep_dot.setFixedSize(14, 14)
        self._sweep_dot.setStyleSheet(
            "background-color: #4caf50; border-radius: 7px; border: none;"
        )
        inner.addWidget(self._sweep_dot, 0, Qt.AlignVCenter)

        self._sweep_status_label = QLabel(
            self._texts.get("sweep_controls", {}).get("status_ready", "Ready")
        )
        self._sweep_status_label.setStyleSheet(_LBL)
        inner.addWidget(self._sweep_status_label, 0, Qt.AlignVCenter)

        self._filter_status_label = QLabel(
            self._texts.get("sweep_controls", {}).get("filter_off", "—  No filter")
        )
        self._filter_status_label.setStyleSheet(
            "font-size: 12px; color: #4a5a7a; border: none; background: transparent;"
        )
        inner.addWidget(self._filter_status_label, 0, Qt.AlignVCenter)

        # Reconnect button (device mode only, shown when no NanoVNA is connected)
        _reconn_style = (
            "QPushButton { background: transparent; color: #e07b54;"
            " border: 1px solid #704030; border-radius: 4px;"
            " font-size: 11px; padding: 2px 10px; }"
            " QPushButton:hover { background-color: #3a2010; }"
            " QPushButton:disabled { color: #666666; border-color: #444444; }"
        )
        self._reconnect_btn = QPushButton(
            self._texts.get("sweep_controls", {}).get("reconnect_label", "Connect NanoVNA")
        )
        self._reconnect_btn.setFixedHeight(24)
        self._reconnect_btn.setStyleSheet(_reconn_style)
        self._reconnect_btn.clicked.connect(self._on_reconnect_clicked)
        inner.addWidget(self._reconnect_btn, 0, Qt.AlignVCenter)
        # Visibility updated after mode is known
        self._reconnect_btn.setVisible(False)

        # Stretch separates left from right symmetrically
        inner.addStretch()

        # Real-time checkbox
        self._realtime_check = QCheckBox(
            self._texts.get("sweep_controls", {}).get("realtime_label", "Real-time")
        )
        self._realtime_check.setChecked(False)
        self._realtime_check.setStyleSheet(_CHK)
        inner.addWidget(self._realtime_check, 0, Qt.AlignVCenter)

        # Vertical separator
        sep = QWidget()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet(f"background-color: {_sep_col}; border: none;")
        inner.addWidget(sep, 0, Qt.AlignVCenter)

        # Run Sweep — solid blue button with painted triangle icon
        _play_pix = QPixmap(14, 14)
        _play_pix.fill(QColor(0, 0, 0, 0))
        _p = QPainter(_play_pix)
        _p.setRenderHint(QPainter.Antialiasing)
        _p.setBrush(QColor("#ffffff"))
        _p.setPen(Qt.NoPen)
        _p.drawPolygon(QPolygon([QPoint(2, 1), QPoint(13, 7), QPoint(2, 13)]))
        _p.end()

        self._run_sweep_btn = QPushButton(
            self._texts.get("sweep_controls", {}).get("run_sweep_label", "Run Sweep")
        )
        self._run_sweep_btn.setIcon(QIcon(_play_pix))
        self._run_sweep_btn.setFixedHeight(34)
        self._run_sweep_btn.setStyleSheet(_BTN)
        inner.addWidget(self._run_sweep_btn, 0, Qt.AlignVCenter)

        outer_row.addWidget(bar)
        return outer

    # --------------------------------------------------------------------- #

    def _build_body(self):
        result = getattr(self.wizard_window, "epsilon_result", None)
        self._result = result

        if result is None:
            placeholder = QLabel(self._texts.get(
                "no_result", "No permittivity result is available. Please complete the wizard."
            ))
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("font-size: 15px;")
            self.main_layout.addWidget(placeholder, stretch=1)
            return

        self.main_layout.addWidget(self._build_epsilon_chart(result), stretch=1)
        self._wire_sweep_controls()
        self._update_reconnect_btn_visibility()

    # --------------------------------------------------------------------- #

    def _build_epsilon_chart(self, result):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.charts.epsilon_chart import (
            EpsilonChartManager,
            EpsilonChartConfig,
        )
        exp = self._texts.get("export", {})

        config = self._make_chart_config(EpsilonChartConfig())

        geo = QGuiApplication.primaryScreen().availableGeometry()
        max_w = geo.width() - 80

        _card_bg  = getattr(self, "_card_bg",  "#252525")
        _card_bdr = getattr(self, "_card_bdr", "#3d3d3d")
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(
            f"QWidget#card {{ background-color: {_card_bg};"
            f" border: 1px solid {_card_bdr}; border-radius: 10px; }}"
        )
        card.setMinimumSize(0, 0)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 12)
        card_layout.setSpacing(8)

        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)

        manager = EpsilonChartManager(config=config)
        title = exp.get("epsilon_title", "εr — {sample}").format(sample=self._sample_name())
        fig, ax, canvas = manager.create_wizard_epsilon_chart(
            result.f_hz, figsize=(7, 6.5), container_layout=chart_layout,
            title=title,
            real_label=self._texts.get("table", {}).get("eps_real", "ε′"),
            loss_label=self._texts.get("table", {}).get("eps_imag", "ε″"),
        )
        manager.update_epsilon_curves(
            ax, result.f_hz, result.eps_selected, canvas=canvas,
        )
        self._epsilon_manager = manager
        self._epsilon_fig = fig
        self._epsilon_ax = ax
        self._epsilon_canvas = canvas

        # Apply saved grid + y-range state
        _pm = get_settings(_PM_INI_EXE, _PM_INI_DEV, Path(__file__).resolve())
        self._grid_enabled = _pm.value("grid/current_state", True, type=bool)
        if not self._grid_enabled:
            ax.grid(False)
        self._apply_reliable_band(ax, _pm.value("auto_scale/current_state", True, type=bool))
        if not _pm.value("auto_scale/current_state", True, type=bool):
            _ymin = _pm.value("set_range/ymin", None, type=float)
            _ymax = _pm.value("set_range/ymax", None, type=float)
            if _ymin is not None and _ymax is not None and _ymax > _ymin:
                ax.set_ylim(_ymin, _ymax)

        # Build marker data row BEFORE setup_markers so labels exist when sliders init
        marker_bar = self._build_marker_data_row()

        self._setup_markers(fig, ax, canvas, result)

        canvas.setMaximumWidth(max_w)
        canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        canvas.customContextMenuRequested.connect(self._show_chart_context_menu)

        # Match marker-bar background to the matplotlib figure so they look like one canvas
        _fc = fig.get_facecolor()
        _fig_bg = "#{:02x}{:02x}{:02x}".format(
            int(_fc[0] * 255), int(_fc[1] * 255), int(_fc[2] * 255))
        marker_bar.setStyleSheet(
            f"#markerBar {{ background-color: {_fig_bg}; border: none; }}"
        )

        # Wrap canvas + marker-bar in a single panel so they scale together
        chart_panel = QWidget()
        chart_panel.setStyleSheet(f"background-color: {_fig_bg}; border: none;")
        chart_panel.setMaximumWidth(max_w)
        _cp_layout = QVBoxLayout(chart_panel)
        _cp_layout.setContentsMargins(0, 0, 0, 10)
        _cp_layout.setSpacing(0)
        _cp_layout.addLayout(chart_layout, 1)
        _cp_layout.addWidget(marker_bar)

        card_layout.addWidget(chart_panel, 1)

        sep = QWidget()
        sep.setObjectName("cardSep")
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"#cardSep {{ background-color: #484848; border: none; }}")
        card_layout.addWidget(sep)

        caption = QLabel(
            "ε′ = real part (energy storage)  ;  "
            "ε″ = imaginary part (dielectric losses)  ;  "
            "Right-click on chart to export"
        )
        caption.setObjectName("chartCaption")
        caption.setWordWrap(True)
        caption.setStyleSheet(
            f"#chartCaption {{ font-size: 10px; color: #555566;"
            f" border: none; background-color: {_card_bg}; }}"
        )
        card_layout.addWidget(caption)

        return card

    # --------------------------------------------------------------------- #

    def _build_marker_data_row(self):
        """Two compact badge-style labels centered under their respective sliders."""
        from PySide6.QtWidgets import QSizePolicy

        _card_bg = getattr(self, "_card_bg", "#363638")

        _BADGE_BG = (
            "background-color: #1a1f2e; border: 1px solid #2d4a6e; border-radius: 5px;"
        )
        _KEY_STYLE = (
            "font-size: 9px; font-weight: bold; color: #5a8fc0;"
            " border: none; background: transparent;"
        )
        _VAL_STYLE = (
            "font-size: 11px; color: #7ab3f5; border: none; background: transparent;"
        )

        def _make_badge(key_text, placeholder):
            badge = QWidget()
            badge.setStyleSheet(_BADGE_BG)
            badge.setFixedHeight(30)
            bl = QHBoxLayout(badge)
            bl.setContentsMargins(8, 0, 8, 0)
            bl.setSpacing(5)
            key_lbl = QLabel(key_text)
            key_lbl.setStyleSheet(_KEY_STYLE)
            val_lbl = QLabel(placeholder)
            val_lbl.setStyleSheet(_VAL_STYLE)
            bl.addStretch(1)
            bl.addWidget(key_lbl)
            bl.addWidget(val_lbl)
            bl.addStretch(1)
            return badge, val_lbl

        row = QWidget()
        row.setObjectName("markerBar")
        row.setStyleSheet(f"#markerBar {{ background-color: {_card_bg}; border: none; }}")
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 4, 0, 4)
        row_layout.setSpacing(0)

        badge1, self._marker1_info_label = _make_badge("ε′:", "—")
        badge2, self._marker2_info_label = _make_badge("ε″:", "—")

        # Mirror the matplotlib slider positions [0.08, 0.38] and [0.54, 0.38]
        # so each badge sits centered under its slider track.
        # Stretch proportions: 8 | badge(38) | 8 | badge(38) | 8  = 100 units
        row_layout.addStretch(8)
        row_layout.addWidget(badge1, 38)
        row_layout.addStretch(8)
        row_layout.addWidget(badge2, 38)
        row_layout.addStretch(8)

        return row

    # --------------------------------------------------------------------- #

    def _make_chart_config(self, config):
        """Reload EpsilonChartConfig fields from the persisted INI."""
        _s = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
        config.real_color = _s.value("Epsilon_Real/TraceColor", config.real_color)
        config.real_linewidth = float(_s.value("Epsilon_Real/TraceWidth", config.real_linewidth))
        config.loss_color = _s.value("Epsilon_Imag/TraceColor", config.loss_color)
        config.loss_linewidth = float(_s.value("Epsilon_Imag/TraceWidth", config.loss_linewidth))
        config.background_color = _s.value("Epsilon_Real/BackgroundColor", config.background_color)
        config.text_color = _s.value("Epsilon_Real/TextColor", config.text_color)
        config.spine_color = _s.value("Epsilon_Real/AxisColor", config.spine_color)
        config.grid_color = _s.value("Epsilon_Real/AxisColor", config.grid_color)
        return config

    # --------------------------------------------------------------------- #

    def _setup_markers(self, fig, ax, canvas, result):
        """Add two matplotlib sliders + marker cursors to the permittivity chart."""
        from matplotlib.widgets import Slider

        _s = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
        m1_color = _s.value("Epsilon_Real/MarkerColor1", "#ff0000")
        m2_color = _s.value("Epsilon_Imag/MarkerColor1", "#ff0000")
        m1_size  = float(_s.value("Epsilon_Real/MarkerWidth1", "6"))
        m2_size  = float(_s.value("Epsilon_Imag/MarkerWidth1", "6"))

        freqs = np.asarray(result.f_hz, dtype=float)
        n = len(freqs)
        self._marker_freqs    = freqs
        # Real values only: at a gap the cursor hides and the label reads "—",
        # instead of reporting an interpolated number that was never measured.
        self._marker_real_eps, self._marker_loss_eps = permittivity_columns(result.eps_selected)
        self._marker_n        = n

        try:
            fig.set_layout_engine("none")
        except Exception:
            pass

        # ------------------------------------------------------------------ #
        # Slider band: fixed fractions with a pixel minimum for usability.
        # The main axes is positioned by tight_layout so it auto-fits the
        # title, axis labels and tick labels at every window size.
        # ------------------------------------------------------------------ #
        _SL_BOT_FRAC  = 0.015
        _SL_H_FRAC    = 0.045
        _SL_H_MIN_PX  = 22

        def _slider_positions():
            fig_h  = max(1.0, fig.get_size_inches()[1] * fig.dpi)
            sl_bot = _SL_BOT_FRAC
            sl_h   = max(_SL_H_MIN_PX / fig_h, _SL_H_FRAC)
            return sl_bot, sl_h

        sl_bot0, sl_h0 = _slider_positions()

        # Marker cursors
        self._cursor1, = ax.plot([], [], "o", markersize=m1_size, color=m1_color,
                                  zorder=5, clip_on=True)
        self._cursor2, = ax.plot([], [], "o", markersize=m2_size, color=m2_color,
                                  zorder=5, clip_on=True)

        _CHART_LEFT  = 0.08   # aligned to slider left edge
        _CHART_RIGHT = 0.92   # aligned to slider right edge
        _TITLE_PX    = 48     # px above axes for title  → converted to fraction at runtime
        _XLABEL_PX   = 68     # px below axes for xticks + Frequency label

        # Slider axes
        sl1_ax = fig.add_axes([0.08, sl_bot0, 0.38, sl_h0])
        sl2_ax = fig.add_axes([0.54, sl_bot0, 0.38, sl_h0])
        for sax in (sl1_ax, sl2_ax):
            sax.set_facecolor("#2a2a2a")
            for spine in sax.spines.values():
                spine.set_color("#444444")
        _CHART_TOP   = 0.87   # fixed top margin — space for the title

        def _adjust_layout(event=None, draw=True):
            try:
                sl_bot, sl_h = _slider_positions()
                fig_h_px = max(1.0, fig.get_size_inches()[1] * fig.dpi)

                # Convert pixel targets to fractions — margins stay ~constant in
                # pixels so the chart grows when the window is maximised.
                top_frac    = min(0.13, max(0.06, _TITLE_PX  / fig_h_px))
                xlabel_frac = min(0.15, max(0.06, _XLABEL_PX / fig_h_px))

                _top    = 1.0 - top_frac
                _bottom = sl_bot + sl_h + xlabel_frac

                # Set the main axes position directly — subplots_adjust does not
                # override positions that constrained layout already set explicitly.
                ax.set_position([
                    _CHART_LEFT,
                    _bottom,
                    _CHART_RIGHT - _CHART_LEFT,
                    _top        - _bottom,
                ])

                # Place slider axes at their original positions.
                sl1_ax.set_position([0.08, sl_bot, 0.38, sl_h])
                sl2_ax.set_position([0.54, sl_bot, 0.38, sl_h])

                # Center title over the full figure width, not just the axes box.
                pos = ax.get_position()
                if pos.width > 0:
                    ax.title.set_x((0.5 - pos.x0) / pos.width)

                if draw:   # redraw_chart draws once itself right after
                    canvas.draw_idle()
            except Exception:
                logging.exception("[_adjust_layout] failed")

        # Disable the constrained layout engine that epsilon_chart sets up —
        # it overrides subplots_adjust on every draw, making manual layout impossible.
        fig.set_layout_engine("none")
        _adjust_layout()
        fig.canvas.mpl_connect("resize_event", _adjust_layout)

        # Always start both markers at index 0, always unlinked.
        # Saved INI positions and link state are intentionally ignored here —
        # each new result window is a fresh measurement session.
        self._cursors_linked = False
        _init_idx1 = 0
        _init_idx2 = 0

        try:
            slider1 = Slider(sl1_ax, "", 0, n - 1, valinit=_init_idx1, valstep=1,
                             track_color="#555555",
                             handle_style={"facecolor": m1_color, "edgecolor": m1_color, "size": 10})
            slider2 = Slider(sl2_ax, "", 0, n - 1, valinit=_init_idx2, valstep=1,
                             track_color="#555555",
                             handle_style={"facecolor": m2_color, "edgecolor": m2_color, "size": 10})
        except TypeError:
            slider1 = Slider(sl1_ax, "", 0, n - 1, valinit=_init_idx1, valstep=1, color=m1_color)
            slider2 = Slider(sl2_ax, "", 0, n - 1, valinit=_init_idx2, valstep=1, color=m2_color)

        for s in (slider1, slider2):
            try:
                s.vline.set_visible(False)
            except Exception:
                pass
            s.label.set_visible(False)
            s.valtext.set_visible(False)
            s.drawon = False   # the marker blit repaints the handle; no draw_idle per set_val

        # A marker move changes only the two cursor dots and the slider
        # handles: they are blitted over the saved background (a full draw of
        # this chart is ~45-80 ms). The blitter re-captures its background on
        # every full draw (redraw_chart, resize), so the chart stays consistent.
        self._marker_blitter = RealtimeBlitter(canvas)

        def _marker_artists():
            arts = []
            if getattr(self, "_trace_blit_active", False) and self._epsilon_manager is not None:
                # Real-time ticks blit the ε curves too: one artist set for
                # ticks and marker moves, so neither invalidates the other's
                # background (see _update_chart_inplace).
                arts.extend(self._epsilon_manager.trace_artists(self._epsilon_ax))
            for a in (getattr(self, "_cursor1", None), getattr(self, "_cursor2", None),
                      slider1.poly, slider1._handle, slider2.poly, slider2._handle):
                if a is not None and getattr(a, "axes", None) is not None:
                    arts.append(a)
            return arts

        def _blit_markers():
            try:
                if getattr(canvas, "_draw_pending", False):
                    return                      # a queued full draw repaints everything
                self._marker_blitter.set_artists(_marker_artists())
                if not canvas.figure.stale:
                    return                      # nothing changed since the last full draw
                self._marker_blitter.update()
            except Exception as exc:
                logging.warning("[_blit_markers] %s; full draw instead", exc)
                canvas.draw_idle()

        self._marker_artists = _marker_artists
        self._blit_markers = _blit_markers

        def _fmt_freq(hz):
            return f"{hz/1e9:.4f} GHz" if hz >= 1e9 else f"{hz/1e6:.4f} MHz"

        def _fmt_eps(value):
            return f"{value:.4f}" if np.isfinite(value) else "—"

        self._marker_updating = False

        def _upd1(val, draw=True):
            if self._marker_updating:
                return
            if not hasattr(self, "_cursor1") or self._cursor1 is None:
                return
            idx = min(max(int(round(val)), 0), self._marker_n - 1)
            freq = self._marker_freqs[idx]
            eps_r = self._marker_real_eps[idx]
            self._cursor1.set_data([freq], [eps_r])
            if hasattr(self, "_marker1_info_label"):
                self._marker1_info_label.setText(
                    f"F = {_fmt_freq(freq)} ; ε ={_fmt_eps(eps_r)}")
            self._save_ini_later("markers/index_1", idx)
            if getattr(self, "_cursors_linked", False):
                self._marker_updating = True
                slider2.set_val(idx)
                self._marker_updating = False
                if hasattr(self, "_cursor2") and self._cursor2 is not None:
                    self._cursor2.set_data([freq], [self._marker_loss_eps[idx]])
                if hasattr(self, "_marker2_info_label"):
                    self._marker2_info_label.setText(
                        f"F = {_fmt_freq(freq)} ; ε ={_fmt_eps(self._marker_loss_eps[idx])}")
                self._save_ini_later("markers/index_2", idx)
            if draw:
                _blit_markers()

        def _upd2(val, draw=True):
            if self._marker_updating:
                return
            if not hasattr(self, "_cursor2") or self._cursor2 is None:
                return
            idx = min(max(int(round(val)), 0), self._marker_n - 1)
            freq = self._marker_freqs[idx]
            eps_i = self._marker_loss_eps[idx]
            self._cursor2.set_data([freq], [eps_i])
            if hasattr(self, "_marker2_info_label"):
                self._marker2_info_label.setText(
                    f"F = {_fmt_freq(freq)} ; ε ={_fmt_eps(eps_i)}")
            self._save_ini_later("markers/index_2", idx)
            if getattr(self, "_cursors_linked", False):
                self._marker_updating = True
                slider1.set_val(idx)
                self._marker_updating = False
                if hasattr(self, "_cursor1") and self._cursor1 is not None:
                    self._cursor1.set_data([freq], [self._marker_real_eps[idx]])
                if hasattr(self, "_marker1_info_label"):
                    self._marker1_info_label.setText(
                        f"F = {_fmt_freq(freq)} ; ε ={_fmt_eps(self._marker_real_eps[idx])}")
                self._save_ini_later("markers/index_1", idx)
            if draw:
                _blit_markers()

        slider1.on_changed(lambda val: _upd1(int(val)))
        slider2.on_changed(lambda val: _upd2(int(val)))

        # Expose so _on_sweep_success_result can refresh cursors after a new result
        self._upd1 = _upd1
        self._upd2 = _upd2

        # Populate labels with the initial slider positions
        _upd1(_init_idx1, draw=False)   # the chart is drawn once when the window shows
        _upd2(_init_idx2, draw=False)

        # Persist link state (read above, before the sliders were built)
        def _toggle_link():
            self._cursors_linked = not self._cursors_linked
            self._save_ini_later("markers/linked", self._cursors_linked)
            if self._cursors_linked:
                slider2.set_val(int(slider1.val))

        self._toggle_cursors_link = _toggle_link
        self._adjust_chart_layout = _adjust_layout

        self._slider1 = slider1
        self._slider2 = slider2

        # ---- Cursor visibility toggle ---- #
        _vis_ini = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
        self._cursor1_visible = str(_vis_ini.value("markers/visible_1", "true")).lower() != "false"
        self._cursor2_visible = str(_vis_ini.value("markers/visible_2", "true")).lower() != "false"

        def _set_cursor1_visible(visible: bool, draw=True):
            self._cursor1_visible = visible
            if hasattr(self, "_cursor1") and self._cursor1 is not None:
                self._cursor1.set_visible(visible)
            if hasattr(self, "_marker1_info_label"):
                self._marker1_info_label.setVisible(visible)
            self._save_ini_later("markers/visible_1", visible)
            if draw:
                _blit_markers()

        def _set_cursor2_visible(visible: bool, draw=True):
            self._cursor2_visible = visible
            if hasattr(self, "_cursor2") and self._cursor2 is not None:
                self._cursor2.set_visible(visible)
            if hasattr(self, "_marker2_info_label"):
                self._marker2_info_label.setVisible(visible)
            self._save_ini_later("markers/visible_2", visible)
            if draw:
                _blit_markers()

        self._set_cursor1_visible = _set_cursor1_visible
        self._set_cursor2_visible = _set_cursor2_visible

        # Apply persisted state before first draw
        _set_cursor1_visible(self._cursor1_visible, draw=False)
        _set_cursor2_visible(self._cursor2_visible, draw=False)
        # Animate the marker artists now: the first full draw (window shown)
        # captures the blit background and paints them on top.
        self._marker_blitter.set_artists(_marker_artists())

        _upd1(_init_idx1, draw=False)   # the chart is drawn once when the window shows
        _upd2(_init_idx2, draw=False)

    # --------------------------------------------------------------------- #

    def _restore_markers_after_redraw(self):
        """Re-add marker cursors to the axes after ax.clear() clears them."""
        if not hasattr(self, "_slider1") or self._epsilon_ax is None:
            return
        _s = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
        m1_color = _s.value("Epsilon_Real/MarkerColor1", "#ff0000")
        m2_color = _s.value("Epsilon_Imag/MarkerColor1", "#ff0000")
        m1_size  = float(_s.value("Epsilon_Real/MarkerWidth1", "6"))
        m2_size  = float(_s.value("Epsilon_Imag/MarkerWidth1", "6"))

        ax = self._epsilon_ax
        self._cursor1, = ax.plot([], [], "o", markersize=m1_size, color=m1_color, zorder=5)
        self._cursor2, = ax.plot([], [], "o", markersize=m2_size, color=m2_color, zorder=5)

        idx1 = min(max(int(self._slider1.val), 0), self._marker_n - 1)
        idx2 = min(max(int(self._slider2.val), 0), self._marker_n - 1)
        self._cursor1.set_data([self._marker_freqs[idx1]], [self._marker_real_eps[idx1]])
        self._cursor2.set_data([self._marker_freqs[idx2]], [self._marker_loss_eps[idx2]])

        self._cursor1.set_visible(getattr(self, "_cursor1_visible", True))
        self._cursor2.set_visible(getattr(self, "_cursor2_visible", True))

    # --------------------------------------------------------------------- #

    def _show_chart_context_menu(self, pos):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.menu.plot_manager.plot_manager import (
            open_plot_manager,
        )
        menu = QMenu(self)

        pm_action = QAction("Plot Manager", self)
        pm_action.triggered.connect(lambda: open_plot_manager(self))
        menu.addAction(pm_action)
        menu.addSeparator()

        grid_label = "Hide Grid" if getattr(self, "_grid_enabled", True) else "Show Grid"
        grid_action = QAction(grid_label, self)
        grid_action.triggered.connect(self._toggle_grid)
        menu.addAction(grid_action)

        if hasattr(self, "_set_cursor1_visible"):
            menu.addSeparator()
            vis1 = getattr(self, "_cursor1_visible", True)
            vis2 = getattr(self, "_cursor2_visible", True)
            c1_action = QAction("Hide ε′ cursor" if vis1 else "Show ε′ cursor", self)
            c1_action.triggered.connect(lambda: self._set_cursor1_visible(not vis1))
            menu.addAction(c1_action)
            c2_action = QAction("Hide ε″ cursor" if vis2 else "Show ε″ cursor", self)
            c2_action.triggered.connect(lambda: self._set_cursor2_visible(not vis2))
            menu.addAction(c2_action)

        if hasattr(self, "_toggle_cursors_link"):
            linked = getattr(self, "_cursors_linked", False)
            link_action = QAction("Unlink cursors" if linked else "Link cursors", self)
            link_action.triggered.connect(self._toggle_cursors_link)
            menu.addAction(link_action)

        menu.addSeparator()
        export_action = QAction("Export…", self)
        export_action.triggered.connect(self._open_chart_export_dialog)
        menu.addAction(export_action)
        menu.exec(self._epsilon_canvas.mapToGlobal(pos))

    def _apply_grid(self, state: bool):
        if not hasattr(self, "_epsilon_ax") or self._epsilon_ax is None:
            return
        self._grid_enabled = state
        if state:
            cfg = getattr(self._epsilon_manager, "config", None)
            grid_color = cfg.grid_color if cfg else "#444444"
            self._epsilon_ax.grid(True, linestyle=":", alpha=0.4, color=grid_color)
        else:
            self._epsilon_ax.grid(False)
        get_settings(_PM_INI_EXE, _PM_INI_DEV, Path(__file__).resolve()).setValue(
            "grid/current_state", state
        )
        if hasattr(self, "_epsilon_canvas") and self._epsilon_canvas:
            self._epsilon_canvas.draw_idle()

    def _toggle_grid(self):
        self._apply_grid(not getattr(self, "_grid_enabled", True))

    def _apply_y_autoscale(self):
        self.redraw_chart()

    def _apply_y_limits(self, ymin: float, ymax: float):
        if not hasattr(self, "_epsilon_ax") or self._epsilon_ax is None:
            return
        self._epsilon_ax.set_ylim(ymin, ymax)
        if hasattr(self, "_epsilon_canvas") and self._epsilon_canvas:
            self._epsilon_canvas.draw_idle()

    def _open_chart_export_dialog(self):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.export.chart_export_dialog import (
            ChartExportDialog,
        )
        # Gather current marker positions and colors for the preview boxes
        marker_data = None
        if hasattr(self, "_slider1") and hasattr(self, "_marker_freqs"):
            _s = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
            idx1 = int(self._slider1.val)
            idx2 = int(self._slider2.val)
            marker_data = {
                "freqs":     self._marker_freqs,
                "real_eps":  self._marker_real_eps,
                "loss_eps":  self._marker_loss_eps,
                "idx1":      idx1,
                "idx2":      idx2,
                "m1_color":  _s.value("Epsilon_Real/MarkerColor1", "#ff0000"),
                "m2_color":  _s.value("Epsilon_Imag/MarkerColor1", "#ff0000"),
                "vis1":      getattr(self, "_cursor1_visible", True),
                "vis2":      getattr(self, "_cursor2_visible", True),
            }
        # The dialog deep-copies the figure: the ε curves must not be animated
        # (blitted real-time ticks) or the copy renders without them.
        self._release_trace_blit()
        dlg = ChartExportDialog(
            parent=self,
            fig=self._epsilon_fig,
            result=self._result,
            sample_name=self._sample_name(),
            marker_data=marker_data,
        )
        dlg.exec()

    # --------------------------------------------------------------------- #

    def _show_s11_window(self):
        from PySide6.QtWidgets import QSlider, QSizePolicy
        from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import SmithChartManager

        cal = getattr(self.wizard_window, "perm_calibration", None)
        dut = cal.get_measurement("dut") if cal is not None else None
        if dut is None:
            return

        freqs    = np.asarray(dut[0], dtype=float)
        s11_data = np.asarray(dut[1], dtype=complex)
        n = len(freqs)

        dlg = QDialog(self)
        dlg.setWindowTitle("S11 — Smith Chart (DUT)")
        dlg.setMinimumSize(520, 600)
        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(6)

        try:
            _M_COLOR = "#ff6600"

            sm = SmithChartManager()
            s11_fig, _ax, _canvas, cursor, _ = sm.create_graphics_panel_smith_chart(
                s_data=s11_data, freqs=freqs, s_param="S11 (DUT)",
                figsize=(4.8, 4.8), container_layout=None,
                trace_color="orange", marker_color=_M_COLOR,
            )
            self._s11_fig = s11_fig
            cursor.set_visible(True)

            _canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            _canvas.setContextMenuPolicy(Qt.CustomContextMenu)
            _canvas.customContextMenuRequested.connect(
                lambda pos: self._s11_context_menu(pos, _canvas)
            )
            outer.addWidget(_canvas, stretch=1)

            # ── Qt slider ─────────────────────────────────────────────────
            qsl = QSlider(Qt.Horizontal)
            qsl.setRange(0, n - 1)
            qsl.setValue(0)
            qsl.setStyleSheet(
                "QSlider::groove:horizontal {"
                "  height: 4px; background: #444444; border-radius: 2px; }"
                "QSlider::handle:horizontal {"
                "  width: 14px; height: 14px; margin: -5px 0;"
                f"  background: {_M_COLOR}; border-radius: 7px; }}"
                "QSlider::sub-page:horizontal {"
                f"  background: {_M_COLOR}; border-radius: 2px; }}"
            )
            outer.addWidget(qsl)

            # ── Info label ────────────────────────────────────────────────
            info_lbl = QLabel("—")
            info_lbl.setAlignment(Qt.AlignCenter)
            info_lbl.setStyleSheet("font-size: 12px; border: none; background: transparent;")
            outer.addWidget(info_lbl)

            def _fmt_freq(hz):
                return f"{hz/1e9:.4f} GHz" if hz >= 1e9 else f"{hz/1e6:.4f} MHz"

            def _upd_s11(idx):
                idx = min(max(idx, 0), n - 1)
                cursor.set_data([np.real(s11_data[idx])], [np.imag(s11_data[idx])])
                mag = 20 * np.log10(abs(s11_data[idx])) if abs(s11_data[idx]) > 1e-12 else -np.inf
                info_lbl.setText(f"f = {_fmt_freq(freqs[idx])}    |S11| = {mag:.2f} dB")
                _canvas.draw_idle()

            qsl.valueChanged.connect(_upd_s11)
            _upd_s11(0)

        except Exception as exc:
            logging.error("[MeasurementMainWindow] S11 chart failed: %s", exc)
            outer.addWidget(QLabel(f"Could not render S11 chart: {exc}"))

        dlg.show()
        self._s11_dialog = dlg

    def _s11_context_menu(self, pos, canvas):
        menu = QMenu(self)
        exp = self._texts.get("export", {})
        action = QAction(exp.get("export_s11", "Export S11 image…"), self)
        action.triggered.connect(
            lambda: self._export_figure(self._s11_fig, f"s11_{self._sample_name()}")
        )
        menu.addAction(action)
        menu.exec(canvas.mapToGlobal(pos))

    # --------------------------------------------------------------------- #

    def _show_table_window(self):
        result = self._result
        if result is None:
            return

        from PySide6.QtWidgets import QFileDialog, QFrame, QMessageBox, QPushButton

        t = self._texts.get("table", {})
        wiz = self.wizard_window
        _is_dark = self.palette().window().color().lightness() < 128

        # ── Palette ────────────────────────────────────────────────────────
        if _is_dark:
            title_color    = "#c8daf5"       # azul claro solo para titulo
            key_color      = "#5a8fc0"       # azul para keys del strip
            val_color      = "#7ab3f5"       # azul para vals del strip
            strip_bg       = "#1a2640"
            strip_bdr      = "#2d5a8e"
            tbl_bg         = "#0e0e12"       # casi negro neutro
            tbl_alt        = "#1a1a22"       # gris muy oscuro neutro
            tbl_text       = "#e0e0e0"       # gris claro puro, sin azul
            tbl_grid       = "#232323"       # gris oscuro para grilla
            hdr_bg         = "#0f1e30"       # azul oscuro solo para header
            hdr_fg         = "#7ab3f5"       # azul claro en header
            hdr_bdr        = "#2a2a2a"       # separador header→filas gris
            hdr_grid       = "#1e1e1e"       # divisor entre columnas de header
            sel_bg         = "#1e4878"       # azul para selección
            sel_fg         = "#ffffff"
            scroll_track   = "#111116"       # gris casi negro
            scroll_handle  = "#3a3a44"       # gris medio
            scroll_hover   = "#555560"       # gris más claro en hover
            legend_color   = "#606070"
            btn_bg         = "#1a1a24"
            btn_fg         = "#7ab3f5"       # azul solo en texto del botón
            btn_bdr        = "#2d5a8e"
            btn_hover      = "#1e3a60"
            btn_press      = "#142a50"
            outer_bdr      = "#2a2a30"       # borde del frame gris oscuro
        else:
            title_color    = "#1a2a3a"
            key_color      = "#3a6090"
            val_color      = "#1a3a5c"
            strip_bg       = "#dce8f5"
            strip_bdr      = "#9bbcd8"
            tbl_bg         = "#ffffff"
            tbl_alt        = "#f4f4f6"       # gris muy claro neutro
            tbl_text       = "#1a1a1a"
            tbl_grid       = "#d0d0d8"
            hdr_bg         = "#dce8f5"
            hdr_fg         = "#1a3a5c"
            hdr_bdr        = "#9bbcd8"
            hdr_grid       = "#c0ccd8"
            sel_bg         = "#b8d4f8"
            sel_fg         = "#0a1a2a"
            scroll_track   = "#e4e4e8"
            scroll_handle  = "#aaaabc"
            scroll_hover   = "#888898"
            legend_color   = "#8080a0"
            btn_bg         = "#dce8f5"
            btn_fg         = "#1a3a5c"
            btn_bdr        = "#9bbcd8"
            btn_hover      = "#c8dcf0"
            btn_press      = "#b0ccec"
            outer_bdr      = "#9bbcd8"

        # ── Dialog ─────────────────────────────────────────────────────────
        dlg = QDialog(self)
        dlg.setWindowTitle(t.get("window_title", "Results Table"))
        dlg.setMinimumSize(580, 680)
        dlg.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(0)

        # ── Title ──────────────────────────────────────────────────────────
        title_lbl = QLabel(t.get("window_title", "Results Table"))
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {title_color};"
            " padding-bottom: 10px; border: none;"
        )
        layout.addWidget(title_lbl)

        # ── Info strip ─────────────────────────────────────────────────────
        f_hz = result.f_hz
        eps  = result.eps_selected
        n_pts = len(f_hz)
        temp = getattr(wiz, "temperature_c", None)
        temp_str  = self._temperature_text(temp)
        freq_str  = f"{f_hz[0]/1e6:.3f} – {f_hz[-1]/1e6:.3f} MHz"

        info_items = [
            ("Number of points", str(n_pts)),
            ("Frequency range",  freq_str),
            ("Temperature",      temp_str),
        ]

        info_strip = QWidget()
        info_strip.setStyleSheet(
            f"background-color: {strip_bg}; border: 1px solid {strip_bdr};"
            " border-radius: 8px;"
        )
        info_row = QHBoxLayout(info_strip)
        info_row.setContentsMargins(16, 10, 16, 10)
        info_row.setSpacing(0)

        for idx, (key, val) in enumerate(info_items):
            if idx > 0:
                sep = QWidget()
                sep.setFixedWidth(1)
                sep.setFixedHeight(28)
                sep.setStyleSheet(f"background-color: {strip_bdr}; border: none;")
                info_row.addWidget(sep)

            cell = QWidget()
            cell.setStyleSheet("border: none; background: transparent;")
            cell_l = QVBoxLayout(cell)
            cell_l.setContentsMargins(16, 0, 16, 0)
            cell_l.setSpacing(1)

            k_lbl = QLabel(key)
            k_lbl.setAlignment(Qt.AlignCenter)
            k_lbl.setStyleSheet(
                f"font-size: 10px; font-weight: bold; color: {key_color};"
                " border: none; background: transparent;"
            )
            v_lbl = QLabel(val)
            v_lbl.setAlignment(Qt.AlignCenter)
            v_lbl.setStyleSheet(
                f"font-size: 12px; color: {val_color};"
                " border: none; background: transparent;"
            )
            cell_l.addWidget(k_lbl)
            cell_l.addWidget(v_lbl)
            info_row.addWidget(cell, stretch=1)

        layout.addWidget(info_strip)
        layout.addSpacing(12)

        # ── Table ──────────────────────────────────────────────────────────
        def _fmt(v, decimals):
            return "—" if not np.isfinite(v) else f"{v:.{decimals}f}"

        stride   = max(1, n_pts // _MAX_TABLE_ROWS)
        rows_idx = list(range(0, n_pts, stride))

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([
            t.get("frequency",    "Frequency (MHz)"),
            t.get("eps_real",     "ε′"),
            t.get("eps_imag",     "ε″"),
            t.get("loss_tangent", "tan δ"),
        ])
        table.setRowCount(len(rows_idx))
        table.setShowGrid(True)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setStyleSheet(f"""
            QTableView {{
                outline: 0;
            }}
            QTableWidget {{
                background-color: {tbl_bg};
                alternate-background-color: {tbl_alt};
                color: {tbl_text};
                gridline-color: {tbl_grid};
                border: none;
                font-size: 12px;
                selection-background-color: {sel_bg};
                selection-color: {sel_fg};
            }}
            QTableWidget::item {{
                padding: 5px 14px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {sel_bg};
                color: {sel_fg};
                border: none;
            }}
            QTableWidget::item:focus {{
                border: none;
                outline: none;
            }}
            QHeaderView::section {{
                background-color: {hdr_bg};
                color: {hdr_fg};
                font-weight: bold;
                font-size: 12px;
                padding: 8px 14px;
                border: none;
                border-bottom: 2px solid {hdr_bdr};
                border-right: 1px solid {hdr_grid};
            }}
            QHeaderView::section:last {{
                border-right: none;
            }}
            QScrollBar:vertical {{
                background: {scroll_track};
                width: 8px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_hover};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
                border: none;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        # eps'' = -Im(eps); a gap is NaN in both columns -> "—" in both.
        # Points the solver flags as non-physical get a dagger, as in the PDF.
        eps_real, eps_loss = permittivity_columns(eps)
        tand = loss_tangent(eps_real, eps_loss)
        flag_mask = nonpassive_mask_of(result)
        flagged = (flag_mask & np.isfinite(eps_real) if flag_mask is not None
                   else np.zeros(eps_real.shape, dtype=bool))
        for r, i in enumerate(rows_idx):
            for c, val in enumerate([
                f"{f_hz[i]/1e6:.4f}",
                _fmt(eps_real[i], 4),
                _fmt(eps_loss[i], 4) + (" †" if flagged[i] else ""),
                _fmt(tand[i],     5),
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(r, c, item)

        table.resizeColumnsToContents()

        # Wrap table in a QFrame so border-radius is actually visible.
        # The 3px margin keeps table content away from the corners,
        # so Qt doesn't clip them with the table's rectangular viewport.
        tbl_frame = QFrame()
        tbl_frame.setObjectName("tbl_frame")
        tbl_frame.setStyleSheet(
            f"QFrame#tbl_frame {{"
            f" border: 2px solid {outer_bdr};"
            f" border-radius: 10px;"
            f" background: {tbl_bg};"
            f"}}"
        )
        tbl_frame_layout = QVBoxLayout(tbl_frame)
        tbl_frame_layout.setContentsMargins(3, 3, 3, 3)
        tbl_frame_layout.setSpacing(0)
        tbl_frame_layout.addWidget(table)
        layout.addWidget(tbl_frame)
        layout.addSpacing(8)

        # ── Footer ─────────────────────────────────────────────────────────
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(4, 4, 4, 0)

        legend_text = "  " + t.get("legend_no_data", "— : No data (NaN)")
        if flagged.any():
            legend_text += "     " + t.get(
                "legend_flagged", "† : non-physical (ε″ < 0 or ε′ < 1), kept and flagged")
        legend_lbl = QLabel(legend_text)
        legend_lbl.setStyleSheet(
            f"font-size: 10px; color: {legend_color}; border: none;"
            " font-style: italic;"
        )
        footer_row.addWidget(legend_lbl)
        footer_row.addStretch()

        export_btn_style = (
            f"QPushButton {{ background-color: {btn_bg}; color: {btn_fg};"
            f" border: 1px solid {btn_bdr}; border-radius: 6px;"
            f" padding: 3px 12px; font-size: 11px; font-weight: bold; }}"
            f" QPushButton:hover {{ background-color: {btn_hover};"
            f"   border-color: {scroll_hover}; }}"
            f" QPushButton:pressed {{ background-color: {btn_press}; }}"
        )
        export_btn = QPushButton(f"  {t.get('export_csv', 'Export CSV')}  ")
        export_btn.setDefault(False)
        export_btn.setAutoDefault(False)
        export_btn.setFixedHeight(28)
        export_btn.setStyleSheet(export_btn_style)

        s1p_btn = QPushButton(f"  {t.get('export_s1p', 'Export .s1p')}  ")
        s1p_btn.setDefault(False)
        s1p_btn.setAutoDefault(False)
        s1p_btn.setFixedHeight(28)
        s1p_btn.setStyleSheet(export_btn_style)
        s1p_btn.clicked.connect(lambda: self._export_permittivity_touchstone(dlg))

        def _do_export_csv():
            path, _ = QFileDialog.getSaveFileName(
                dlg, "Save CSV", "permittivity.csv", "CSV Files (*.csv)"
            )
            if not path:
                return
            try:
                write_permittivity_csv(path, f_hz, eps)
                QMessageBox.information(dlg, "Saved", f"CSV saved to:\n{path}")
            except Exception as exc:
                QMessageBox.critical(dlg, "Error", f"Failed to save CSV:\n{exc}")

        export_btn.clicked.connect(_do_export_csv)
        footer_row.addWidget(export_btn)
        footer_row.addWidget(s1p_btn)

        footer_w = QWidget()
        footer_w.setLayout(footer_row)
        footer_w.setStyleSheet("border: none;")
        layout.addWidget(footer_w)

        dlg.show()
        self._table_dialog = dlg

    # --------------------------------------------------------------------- #

    def _export_figure(self, fig, default_stem):
        if fig is None:
            return
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        exp = self._texts.get("export", {})
        stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in default_stem).strip() or "figure"
        path, _ = QFileDialog.getSaveFileName(
            self, exp.get("dialog_title", "Save figure"),
            f"{stem}.png",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg)",
        )
        if not path:
            return
        try:
            fig.savefig(path, dpi=300, bbox_inches="tight")
            QMessageBox.information(
                self, exp.get("ok_title", "Saved"),
                exp.get("ok_message", "Figure saved to:\n{path}").format(path=path),
            )
        except Exception as exc:
            logging.error("[MeasurementMainWindow] export failed: %s", exc)
            QMessageBox.critical(self, "Export Error", f"Failed to save image: {exc}")

    # --------------------------------------------------------------------- #

    def _sample_name(self):
        name = (getattr(self.wizard_window, "unknown_liquid_name", "") or "").strip()
        return name or "sample"

    # --------------------------------------------------------------------- #

    def _create_menus(self):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.menu.menu_builder import build_menu
        build_menu(self)

    def _open_edit_chart(self):
        if not hasattr(self, "_epsilon_manager") or self._epsilon_manager is None:
            return
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.edit_characterization.edit_characterization_window import (
            EditCharacterization,
        )
        self._edit_chart_window = EditCharacterization(self)
        self._edit_chart_window.show()

    def _apply_reliable_band(self, ax, auto_scale: bool) -> None:
        """
        Shade the unreliable band and, with auto-scale, fit y to reliable points.

        EN: Same rule as the wizard's result chart: points that failed the
            quality checks stay drawn but never set the y-scale (a manual
            range from the plot manager still wins).
        ES: La misma regla que el grafico de resultado del asistente: los
            puntos que no pasaron los controles se dibujan pero nunca fijan la
            escala en y (un rango manual del plot manager sigue mandando).
        """
        usable, f_min = usable_band_of(self._result)
        if f_min is not None:
            label = load_text("characterization_wizard.json").get("result", {}).get(
                "low_sensitivity_label", "unreliable")
            shade_unusable_band(ax, float(self._result.f_hz[0]), f_min, label=label)
            ax.legend(loc="upper right")
        if auto_scale:
            limits = scale_limits(self._result.eps_selected, usable)
            if limits is not None:
                ax.set_ylim(limits)

    # --------------------------------------------------------------------- #
    # Signal filters                                                         #
    # --------------------------------------------------------------------- #

    def _open_signal_filters(self):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.menu.signal_filters.signal_filters_char import (
            open_signal_filters_char,
        )
        open_signal_filters_char(self)

    def _apply_eps_filter(self, real, loss):
        """Apply the active filter to ε′ (real) and ε″ (loss) arrays.

        In real-time mode Smoothing uses a temporal buffer (sweep-to-sweep
        average) instead of a frequency moving average, preserving the shape of
        each curve while reducing inter-sweep variance.
        """
        import numpy as np
        active = getattr(self, "_active_filter", "Off")
        if active == "Smoothing":
            k = max(2, round(self._filter_smooth_pct / 5))
            if not hasattr(self, '_tb_eps_r') or self._tb_eps_r is None:
                from NanoVNA_UTN_Toolkit.shared.utils.real_time.temporal_buffer import TemporalBuffer
                self._tb_eps_r = TemporalBuffer(k)
                self._tb_eps_l = TemporalBuffer(k)
            else:
                self._tb_eps_r.resize(k)
                self._tb_eps_l.resize(k)
            real = self._tb_eps_r.push(np.asarray(real, dtype=float))
            loss = self._tb_eps_l.push(np.asarray(loss, dtype=float))
        elif active == "Kalman":
            # Temporal Kalman: one filter per frequency point updated each sweep.
            if not hasattr(self, '_tk_eps') or self._tk_eps is None:
                from NanoVNA_UTN_Toolkit.shared.utils.real_time.temporal_buffer import TemporalKalman
                pn = getattr(self, '_kf_process_noise', 0.0001)
                mn = getattr(self, '_kf_measurement_noise', 10.0)
                self._tk_eps = TemporalKalman(len(real), pn, mn)
            # Feed ε′ + j·ε″ as a complex array; Re→ε′, Im→ε″ after filtering.
            eps_complex = np.asarray(real, dtype=float) + 1j * np.asarray(loss, dtype=float)
            filtered = self._tk_eps.update(eps_complex)
            real = filtered.real
            loss = filtered.imag
        return real, loss

    def _update_filter_label(self):
        if not hasattr(self, "_filter_status_label"):
            return
        sc = self._texts.get("sweep_controls", {})
        active = getattr(self, "_active_filter", "Off")
        if active == "Smoothing":
            pct = getattr(self, "_filter_smooth_pct", 5)
            self._filter_status_label.setText(
                sc.get("filter_smoothing", "·  Smoothing: {pct}%").format(pct=pct)
            )
            self._filter_status_label.setStyleSheet(
                "font-size: 12px; color: #8899bb; border: none; background: transparent;"
            )
        elif active == "Kalman":
            preset = getattr(self, "_filter_kalman_preset", "Kalman")
            self._filter_status_label.setText(
                sc.get("filter_kalman", "·  Kalman: {preset}").format(preset=preset)
            )
            self._filter_status_label.setStyleSheet(
                "font-size: 12px; color: #8899bb; border: none; background: transparent;"
            )
        else:
            self._filter_status_label.setText(sc.get("filter_off", "—  No filter"))
            self._filter_status_label.setStyleSheet(
                "font-size: 12px; color: #4a5a7a; border: none; background: transparent;"
            )
        self._filter_status_label.show()

    def _on_filter_settings_changed(self):
        """Called after filter dialog applies new settings — redraw with new settings."""
        self._update_filter_label()
        if self._result is None:
            return
        # Reset temporal buffers/filters so the new settings take effect immediately.
        self._tb_eps_r = None
        self._tb_eps_l = None
        self._tk_eps = None
        # Filter is only active in real-time; changing settings outside real-time just redraws raw.
        _is_realtime = (
            getattr(self, "_realtime_check", None) is not None
            and self._realtime_check.isChecked()
        )
        if _is_realtime:
            import numpy as np
            raw_real, raw_loss = permittivity_columns(self._result.eps_selected)
            if self._active_filter == "Kalman" and self._kf_eps is not None:
                self._kf_eps.reset()
            filtered_real, filtered_loss = self._apply_eps_filter(
                np.asarray(raw_real, dtype=float),
                np.asarray(raw_loss, dtype=float),
            )
            self._display_eps     = (filtered_real - 1j * filtered_loss).astype(complex)
            self._marker_real_eps = filtered_real
            self._marker_loss_eps = filtered_loss
        else:
            self._display_eps = None
        self.redraw_chart()

    def redraw_chart(self):
        if not hasattr(self, "_epsilon_ax") or self._epsilon_ax is None:
            return
        if self._result is None or self._epsilon_manager is None:
            return
        try:
            from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.charts.epsilon_chart import (
                EpsilonChartConfig,
            )
            self._epsilon_manager.config = self._make_chart_config(EpsilonChartConfig())
            # Pass canvas=None so update_epsilon_curves doesn't draw mid-way;
            # we draw once at the end after restoring the marker cursors.
            _eps_to_draw = (
                self._display_eps
                if self._display_eps is not None
                else self._result.eps_selected
            )
            self._epsilon_manager.update_epsilon_curves(
                self._epsilon_ax,
                self._result.f_hz,
                _eps_to_draw,
                canvas=None,
            )
            if not getattr(self, "_grid_enabled", True):
                self._epsilon_ax.grid(False)
            _pm2 = get_settings(_PM_INI_EXE, _PM_INI_DEV, Path(__file__).resolve())
            self._apply_reliable_band(
                self._epsilon_ax, _pm2.value("auto_scale/current_state", True, type=bool))
            if not _pm2.value("auto_scale/current_state", True, type=bool):
                _ymin = _pm2.value("set_range/ymin", None, type=float)
                _ymax = _pm2.value("set_range/ymax", None, type=float)
                if _ymin is not None and _ymax is not None and _ymax > _ymin:
                    self._epsilon_ax.set_ylim(_ymin, _ymax)
            self._restore_markers_after_redraw()
            if hasattr(self, "_marker_blitter"):
                # New cursor artists: animate them before the single full draw
                # below captures the background and paints them on top.
                self._marker_blitter.set_artists(self._marker_artists())
            if hasattr(self, "_adjust_chart_layout"):
                self._adjust_chart_layout(draw=False)
            self._epsilon_canvas.draw()   # the ONE full draw of a redraw
            self._chart_key_drawn = self._chart_static_key()
        except Exception as exc:
            self._chart_key_drawn = None
            logging.error("[MeasurementMainWindow] redraw_chart failed: %s", exc)

    # --------------------------------------------------------------------- #
    # Real-time tick without rebuilding the chart                           #
    # --------------------------------------------------------------------- #

    def _chart_static_key(self):
        """Everything a full redraw_chart derives besides the curve data.

        EN: Title and labels, colors and widths from the INI, grid, the shaded
            unreliable band, auto-scale state and manual range, frequency grid.
            When it differs from the key of the last full redraw (filter dialog,
            Edit chart, Plot Manager, new sample name, another sweep range) the
            next tick rebuilds the chart; otherwise it updates the curves in place.
        ES: Todo lo que redraw_chart arma ademas de los datos; si cambia, el
            siguiente tick reconstruye el grafico.
        """
        mgr = self._epsilon_manager
        if mgr is None or self._result is None:
            return None
        try:
            from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.charts.epsilon_chart import (
                EpsilonChartConfig,
            )
            cfg = self._make_chart_config(EpsilonChartConfig())
            pm = get_settings(_PM_INI_EXE, _PM_INI_DEV, Path(__file__).resolve())
            auto_scale = pm.value("auto_scale/current_state", True, type=bool)
            manual = None if auto_scale else (pm.value("set_range/ymin", None, type=float),
                                              pm.value("set_range/ymax", None, type=float))
            _usable, f_min = usable_band_of(self._result)
            f_hz = np.asarray(self._result.f_hz, dtype=float)
            return (
                getattr(mgr, "_title", None), getattr(mgr, "_real_label", None),
                getattr(mgr, "_loss_label", None),
                str(cfg.real_color), float(cfg.real_linewidth), str(cfg.loss_color),
                float(cfg.loss_linewidth), str(cfg.background_color), str(cfg.text_color),
                str(cfg.spine_color), str(cfg.grid_color),
                bool(getattr(self, "_grid_enabled", True)), f_min, bool(auto_scale), manual,
                int(f_hz.size), float(f_hz[0]) if f_hz.size else None,
                float(f_hz[-1]) if f_hz.size else None,
            )
        except Exception as exc:
            logging.debug("[MeasurementMainWindow] _chart_static_key: %s", exc)
            return None

    def _update_chart_inplace(self) -> bool:
        """Real-time tick: new ε data into the existing curves, no axes rebuild.

        EN: Valid only while the static part matches the last full redraw
            (otherwise returns False and the caller does redraw_chart). With
            auto-scale the y-limits follow the hysteresis of the DUT real-time
            panels: kept while the data lies inside them and uses at least 60 %
            of their span; else the limits a full redraw would set are applied
            and that tick is one full draw, still without rebuilding the axes.
            The curves join the marker blitter's animated artists; the caller
            blits once the cursors are placed (_blit_markers).
        ES: Tick de tiempo real: datos nuevos en las curvas existentes, sin
            reconstruir ejes; False si hace falta el redibujado completo.
        """
        ax = self._epsilon_ax
        mgr = self._epsilon_manager
        if ax is None or mgr is None or self._result is None or not hasattr(self, "_marker_blitter"):
            return False
        key = self._chart_static_key()
        if key is None or key != self._chart_key_drawn:
            return False
        eps = self._display_eps if self._display_eps is not None else self._result.eps_selected

        new_ylim = None
        auto_scale = get_settings(_PM_INI_EXE, _PM_INI_DEV, Path(__file__).resolve()).value(
            "auto_scale/current_state", True, type=bool)
        if auto_scale:
            usable, _f_min = usable_band_of(self._result)
            new_ylim = scale_limits(eps, usable)
            if new_ylim is None:
                return False
            if new_ylim == tuple(ax.get_ylim()):
                new_ylim = None   # limits unchanged — skip the invalidate

        if mgr.update_epsilon_curves_inplace(ax, self._result.f_hz, eps) is None:
            return False
        if new_ylim is not None:
            # Same limits a full redraw would set; the ticks change, so the next
            # blit is a full draw (no axes rebuild).
            ax.set_ylim(new_ylim)
            self._marker_blitter.invalidate()
        if not self._trace_blit_active:
            self._trace_blit_active = True   # the curves join the blitted artists
        return True

    def _release_trace_blit(self):
        """Back to normal drawing of the ε curves (real time off, export).

        Animated artists are skipped by a plain ``Figure.draw``/``savefig`` and
        by a deep copy's render, so the curves must not stay animated outside
        the real-time ticks.
        """
        if not self._trace_blit_active:
            return
        self._trace_blit_active = False
        try:
            if hasattr(self, "_marker_blitter"):
                self._marker_blitter.set_artists(self._marker_artists())   # un-animates the curves
            if self._epsilon_canvas is not None:
                self._epsilon_canvas.draw_idle()
        except Exception as exc:
            logging.warning("[MeasurementMainWindow] _release_trace_blit: %s", exc)

    def _export_pdf(self):
        from PySide6.QtWidgets import QMessageBox
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.export.latex_export_setup_dialog import (
            PermittivityLatexSetupDialog,
        )

        if self._result is None:
            QMessageBox.warning(self, "Export PDF", "No permittivity result available.")
            return

        cal = getattr(self.wizard_window, "perm_calibration", None)
        if cal is None or cal.get_measurement("dut") is None:
            QMessageBox.warning(self, "Export PDF", "No S11 data available.")
            return

        dlg = PermittivityLatexSetupDialog(
            parent=self,
            default_filename=f"characterization_{self._sample_name()}",
        )
        dlg.exec()

    def _export_s11_touchstone(self):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.export.export_s11_touchstone import (
            export_s11_touchstone,
        )
        export_s11_touchstone(self)

    def _export_permittivity_touchstone(self, parent=None):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.utils.export.export_permittivity_touchstone import (
            export_permittivity_touchstone,
        )
        export_permittivity_touchstone(parent or self, self._result, self._sample_name(),
                                       self._permittivity_notes())

    def _permittivity_notes(self):
        """Provenance lines for the header of the εr .s1p export."""
        wiz = self.wizard_window
        cal = getattr(wiz, "perm_calibration", None)
        notes = []
        technique = getattr(wiz, "selected_method", "")
        if technique:
            notes.append(f"Technique / Tecnica: {technique}")
        if cal is not None and cal.ref1_key:
            refs = cal.ref1_key + (f" + {cal.ref2_key}" if cal.ref2_key else "")
            notes.append(f"References / Referencias: {refs}")
        notes.append(f"Probe / Sonda: {self._probe_text()}")
        notes.append("Temperature / Temperatura: "
                     + self._temperature_text(getattr(wiz, "temperature_c", None)))
        return notes

    # --------------------------------------------------------------------- #
    # Real-time sweep                                                        #
    # --------------------------------------------------------------------- #

    def _wire_sweep_controls(self):
        """Connect Run Sweep button and Real-time checkbox to sweep logic."""
        if hasattr(self, "_run_sweep_btn"):
            self._run_sweep_btn.clicked.connect(self._run_one_sweep)
        if hasattr(self, "_realtime_check"):
            self._realtime_check.stateChanged.connect(
                lambda state: self._on_realtime_toggled(state != 0)
            )

    def _update_reconnect_btn_visibility(self):
        """Show the 'Connect NanoVNA' button when device mode has no device."""
        if not hasattr(self, "_reconnect_btn"):
            return
        wiz = self.wizard_window
        device = getattr(wiz, "vna_device", None) if wiz else None
        no_device = device is None or not hasattr(device, "connected")
        self._reconnect_btn.setVisible(self._sweep_mode == "device" and no_device)

    def _on_reconnect_clicked(self):
        """Scan for a NanoVNA and update wizard_window.vna_device on success."""
        if not hasattr(self, "_reconnect_btn"):
            return
        self._reconnect_btn.setEnabled(False)
        self._reconnect_btn.setText(
            self._texts.get("sweep_controls", {}).get("reconnect_scanning", "Scanning…")
        )

        class _ScanWorker(QObject):
            found    = Signal(object)
            error    = Signal(str)
            finished = Signal()

            def scan(self):
                try:
                    from NanoVNA_UTN_Toolkit.Hardware.Hardware import get_interfaces, get_VNA
                    interfaces = get_interfaces()
                    if not interfaces:
                        self.error.emit("No NanoVNA detected on any port.")
                        return
                    for iface in interfaces:
                        try:
                            vna = get_VNA(iface)
                            if vna:
                                self.found.emit(vna)
                                return
                        except Exception:
                            continue
                    self.error.emit("Could not connect to any detected device.")
                except Exception as exc:
                    self.error.emit(f"Scan error: {exc}")
                finally:
                    self.finished.emit()

        thread = QThread()
        worker = _ScanWorker()
        worker.moveToThread(thread)
        self._reconn_thread = thread
        self._reconn_worker = worker

        def on_found(vna):
            logging.info("[MeasurementMainWindow] Reconnect scan found: %s", type(vna).__name__)
            self.vna = vna
            wiz = self.wizard_window
            if wiz is not None:
                wiz.vna_device = vna
                if hasattr(wiz, "vna"):
                    wiz.vna = vna
            self._update_reconnect_btn_visibility()
            sc = self._texts.get("sweep_controls", {})
            self._set_sweep_status(sc.get("status_ready", "Ready"), "#4caf50")

        def on_error(msg):
            logging.warning("[MeasurementMainWindow] Reconnect scan failed: %s", msg)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Connection Failed", msg)
            self._reconnect_btn.setEnabled(True)
            self._reconnect_btn.setText(
                self._texts.get("sweep_controls", {}).get("reconnect_label", "Connect NanoVNA")
            )

        def on_done():
            thread.quit()

        worker.found.connect(on_found)
        worker.error.connect(on_error)
        worker.finished.connect(on_done)
        thread.started.connect(worker.scan)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _on_realtime_toggled(self, enabled: bool):
        if hasattr(self, "_run_sweep_btn"):
            self._run_sweep_btn.setEnabled(not enabled)
        if enabled:
            self._realtime_timer.start()
            sc = self._texts.get("sweep_controls", {})
            self._set_sweep_status(sc.get("status_realtime", "Real-time"), "#2196f3")
        else:
            self._realtime_timer.stop()
            self._release_trace_blit()
            sc = self._texts.get("sweep_controls", {})
            if self._sweep_mode == "file":
                self._set_sweep_status(sc.get("status_file_mode", "File mode"), "#ff9800")
            else:
                self._set_sweep_status(sc.get("status_ready", "Ready"), "#4caf50")

    def _set_sweep_status(self, text: str, color: str):
        if hasattr(self, "_sweep_dot"):
            self._sweep_dot.setStyleSheet(
                f"background-color: {color}; border-radius: 7px; border: none;"
            )
        if hasattr(self, "_sweep_status_label"):
            self._sweep_status_label.setText(text)

    def _run_one_sweep(self):
        if self._sweep_in_progress or self._result is None:
            return
        self._sweep_in_progress = True
        sc = self._texts.get("sweep_controls", {})
        self._set_sweep_status(sc.get("status_measuring", "Measuring..."), "#ff9800")
        if hasattr(self, "_run_sweep_btn"):
            self._run_sweep_btn.setEnabled(False)

        if self._sweep_mode == "file":
            self._sweep_from_file()
        else:
            self._sweep_from_device()

    def _sweep_from_file(self):
        """Cycle through the user-configured S11 files and recompute ε.

        Parse and solver run off the GUI thread (``_file_sweep_compute``);
        ``_on_file_sweep_done`` finishes on the GUI thread.
        """
        if not self._file_sweep_config:
            self._on_sweep_error("No S11 files configured")
            return
        cal = getattr(self.wizard_window, "perm_calibration", None)
        if cal is None:
            self._on_sweep_error("No calibration available")
            return
        entry = self._file_sweep_config[self._file_sweep_idx % len(self._file_sweep_config)]
        self._file_sweep_idx += 1
        name = (entry["name"] or "").strip() or self._sample_name()
        if hasattr(self, "_epsilon_manager") and self._epsilon_manager is not None:
            exp = self._texts.get("export", {})
            self._epsilon_manager._title = exp.get(
                "epsilon_title", "εr — {sample}"
            ).format(sample=name)
        logging.info("[MeasurementMainWindow] file sweep: %s", entry["path"])
        run_in_background(_file_sweep_compute, (entry["path"], cal),
                          self._on_file_sweep_done, self._bg_threads)

    def _on_file_sweep_done(self, outcome):   # GUI thread
        if self._window_closed:
            return
        if isinstance(outcome, Exception):
            self._on_sweep_error(str(outcome))
            return
        new_result = outcome[2]
        if new_result is not None:
            self._on_sweep_success_result(new_result)
        else:
            self._on_sweep_error("compute_epsilon returned None")

    def _sweep_from_device(self):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.measure_runner import (
            run_s11_sweep_async,
        )
        wiz = self.wizard_window
        if wiz is None:
            self._on_sweep_error("No wizard reference")
            return
        device = getattr(wiz, "vna_device", None)
        if device is None or not hasattr(device, "connected"):
            self._on_sweep_error("No VNA device")
            logging.warning("[MeasurementMainWindow] Run Sweep: no NanoVNA device available")
            return
        cal = getattr(wiz, "perm_calibration", None)
        if cal is None:
            self._on_sweep_error("No calibration available")
            return
        # The solver (0.1-0.5 s) runs in the sweep worker right after the read;
        # only the chart update is left for the GUI thread.
        run_s11_sweep_async(
            wiz,
            on_success=self._on_sweep_epsilon_ready,
            on_error=lambda: self._on_sweep_error("Device sweep failed"),
            post_process=cal.compute_epsilon,
        )

    def _on_sweep_epsilon_ready(self, freqs, s11, new_result):   # GUI thread
        if self._window_closed:
            return
        if new_result is not None:
            self._on_sweep_success_result(new_result)
        else:
            self._on_sweep_error("compute_epsilon returned None")

    def _on_sweep_success_result(self, new_result):
        if self._window_closed:
            return
        self._result = new_result
        new_real, new_loss = permittivity_columns(new_result.eps_selected)
        logging.info(
            "[MeasurementMainWindow] sweep success — median ε′=%.3f  ε″=%.3f  NaN=%d/%d",
            float(np.nanmedian(new_real)), float(np.nanmedian(new_loss)),
            int(np.sum(~np.isfinite(new_real))), len(new_real),
        )
        _is_realtime = (
            getattr(self, "_realtime_check", None) is not None
            and self._realtime_check.isChecked()
        )
        # Apply filter in both single-shot and real-time: each sweep accumulates
        # into the temporal buffer/Kalman, so repeated Run Sweep clicks average
        # across shots just like RT does across ticks.
        if getattr(self, "_active_filter", "Off") != "Off":
            filtered_real, filtered_loss = self._apply_eps_filter(
                np.asarray(new_real, dtype=float),
                np.asarray(new_loss, dtype=float),
            )
            self._display_eps = (filtered_real - 1j * filtered_loss).astype(complex)
        else:
            filtered_real, filtered_loss = new_real, new_loss
            self._display_eps = None
        # Refresh marker data arrays so cursors and badges reflect the result
        self._marker_real_eps = filtered_real
        self._marker_loss_eps = filtered_loss
        self._marker_freqs = np.asarray(new_result.f_hz, dtype=float)
        self._marker_n = len(self._marker_freqs)
        # Real time: new data into the existing curves, blitted with the
        # markers (no axes rebuild, no full draw). A changed static part or a
        # y-range that no longer fits falls back to the full redraw.
        inplace = _is_realtime and self._update_chart_inplace()
        if not inplace:
            self.redraw_chart()
        # Badge labels for the current slider positions; the cursor dots were
        # already placed by redraw_chart (no second draw).
        if hasattr(self, "_upd1") and hasattr(self, "_slider1"):
            self._upd1(int(self._slider1.val), draw=False)
        if hasattr(self, "_upd2") and hasattr(self, "_slider2"):
            self._upd2(int(self._slider2.val), draw=False)
        if inplace and hasattr(self, "_blit_markers"):
            self._blit_markers()   # curves + cursors + handles, one blit
        self._sweep_in_progress = False
        _rt = getattr(self, "_realtime_check", None)
        _rt_on = _rt is not None and _rt.isChecked()
        if hasattr(self, "_run_sweep_btn"):
            self._run_sweep_btn.setEnabled(not _rt_on)
        sc = self._texts.get("sweep_controls", {})
        if _rt_on:
            self._set_sweep_status(sc.get("status_realtime", "Real-time"), "#2196f3")
        elif self._sweep_mode == "file":
            self._set_sweep_status(sc.get("status_file_mode", "File mode"), "#ff9800")
        else:
            self._set_sweep_status(sc.get("status_ready", "Ready"), "#4caf50")

    def _save_ini_later(self, key: str, value):
        """Batch chart INI writes (marker index, link, visibility)."""
        self._ini_pending[key] = value
        self._ini_timer.start()

    def _flush_ini(self):
        self._ini_timer.stop()
        if not self._ini_pending:
            return
        try:
            s = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
            for key, value in self._ini_pending.items():
                s.setValue(key, value)
            s.sync()
        except Exception as exc:
            logging.warning("[MeasurementMainWindow] chart INI save failed: %s", exc)
        finally:
            self._ini_pending.clear()

    def _on_sweep_error(self, msg: str = ""):
        if self._window_closed:
            return
        logging.error("[MeasurementMainWindow] sweep error: %s", msg)
        self._sweep_in_progress = False
        if hasattr(self, "_run_sweep_btn"):
            self._run_sweep_btn.setEnabled(True)
        # Stop real-time on error to avoid repeating blocking dialogs every tick
        if hasattr(self, "_realtime_check") and self._realtime_check.isChecked():
            self._realtime_check.setChecked(False)
        sc = self._texts.get("sweep_controls", {})
        self._set_sweep_status(sc.get("status_error", "Error"), "#f44336")

    # --------------------------------------------------------------------- #
    # File sweep source                                                      #
    # --------------------------------------------------------------------- #

    def _handle_sweep_source_action(self):
        if self._sweep_mode == "device":
            self._open_file_sweep_config_dialog()
        else:
            self._switch_to_device_mode()
            self._open_device_sweep_settings_dialog()

    def _switch_to_device_mode(self):
        self._sweep_mode = "device"
        self._update_sweep_source_action()
        self._update_reconnect_btn_visibility()
        sc = self._texts.get("sweep_controls", {})
        self._set_sweep_status(sc.get("status_ready", "Ready"), "#4caf50")

    def _update_sweep_source_action(self):
        m = self._texts.get("menu", {})
        if hasattr(self, "_sweep_source_action"):
            if self._sweep_mode == "device":
                self._sweep_source_action.setText(
                    m.get("source_file_mode", "Configure File Source…")
                )
            else:
                self._sweep_source_action.setText(
                    m.get("source_device_mode", "Use Device (NanoVNA)")
                )
        if hasattr(self, "_sweep_config_action"):
            if self._sweep_mode == "device":
                self._sweep_config_action.setText(
                    m.get("sweep_settings", "Sweep Settings…")
                )
            else:
                self._sweep_config_action.setText(
                    m.get("source_file_mode", "Configure File Source…")
                )

    def _handle_sweep_config_action(self):
        if self._sweep_mode == "file":
            self._open_file_sweep_config_dialog()
        else:
            self._open_device_sweep_settings_dialog()

    def _open_device_sweep_settings_dialog(self):
        t = self._texts.get("device_settings_dialog", {})

        _is_dark    = self.palette().window().color().lightness() < 128
        _dlg_bg     = "#0a1220" if _is_dark else "#eef4fa"
        title_color = "#c8daf5" if _is_dark else "#1a2a3a"
        sep_color   = "#2d5a8e" if _is_dark else "#c8d4e0"
        lbl_color   = "#7ab3f5" if _is_dark else "#3a5a7a"
        tbl_text    = "#c8daf5" if _is_dark else "#1a1a1a"
        edit_bg     = "#0d1520" if _is_dark else "#ffffff"
        edit_bdr    = "#2d5a8e" if _is_dark else "#9bbcd8"
        btn_bg      = "#1a2640" if _is_dark else "#dce8f5"
        btn_fg      = "#7ab3f5" if _is_dark else "#1a3a5c"
        btn_bdr     = "#2d5a8e" if _is_dark else "#9bbcd8"
        btn_hover   = "#1e3a60" if _is_dark else "#c8dcf0"
        btn_press   = "#142a50" if _is_dark else "#b0ccec"

        from PySide6.QtWidgets import QFrame as _QF, QDoubleSpinBox

        class _FlexSpin(QDoubleSpinBox):
            def valueFromText(self, text):
                sfx = self.suffix()
                s = text[: text.rfind(sfx)].strip() if sfx and sfx in text else text.strip()
                try:
                    return float(s.replace(",", "."))
                except ValueError:
                    return self.value()
            def validate(self, text, pos):
                return super().validate(text.replace(",", "."), pos)

        dlg = QDialog(self)
        dlg.setWindowTitle(t.get("title", "Sweep Settings"))
        dlg.setFixedSize(400, 210)
        dlg.setStyleSheet(
            self.styleSheet()
            + f" QDialog {{ background-color: {_dlg_bg}; }}"
            + " QDialog QLabel { background: transparent; }"
        )

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(0)

        def _sep():
            s = _QF(); s.setFrameShape(_QF.Shape.HLine)
            s.setFixedHeight(1)
            s.setStyleSheet(f"background-color: {sep_color}; border: none;")
            return s

        title_lbl = QLabel(t.get("title", "Sweep Settings"))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {title_color};"
            " padding-bottom: 10px; border: none;"
        )
        layout.addWidget(title_lbl)
        layout.addWidget(_sep())
        layout.addSpacing(14)

        # Interval row
        iv_row = QHBoxLayout()
        iv_lbl = QLabel(t.get("interval_label", "Sweep every:"))
        iv_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {lbl_color}; border: none;")

        spin = _FlexSpin()
        spin.setRange(0.1, 3600.0)
        spin.setSingleStep(0.1)
        spin.setDecimals(1)
        spin.setSuffix(t.get("interval_suffix", " s"))
        spin.setValue(max(0.1, self._realtime_timer.interval() / 1000.0))
        spin.setButtonSymbols(_FlexSpin.ButtonSymbols.NoButtons)
        spin.setStyleSheet("QDoubleSpinBox { border: none; background: transparent; }")

        spin_frame = _QF()
        spin_frame.setObjectName("spinboxContainer")
        spin_frame.setFixedHeight(32)
        spin_frame.setFixedWidth(100)
        spin_frame.setStyleSheet(
            f"QFrame#spinboxContainer {{ background-color: {edit_bg}; border: 1px solid {edit_bdr}; border-radius: 6px; }}"
            f" QPushButton#spinboxUpBtn, QPushButton#spinboxDownBtn {{ background-color: {btn_bg}; border: 1px solid {btn_bdr}; color: {btn_fg}; }}"
            f" QPushButton#spinboxUpBtn:hover, QPushButton#spinboxDownBtn:hover {{ background-color: {btn_hover}; }}"
        )
        sfl = QHBoxLayout(spin_frame); sfl.setContentsMargins(6, 1, 0, 1); sfl.setSpacing(0)
        _su = QPushButton("▲"); _su.setObjectName("spinboxUpBtn");   _su.setFixedSize(18, 14); _su.clicked.connect(spin.stepUp)
        _sd = QPushButton("▼"); _sd.setObjectName("spinboxDownBtn"); _sd.setFixedSize(18, 14); _sd.clicked.connect(spin.stepDown)
        _sc = QVBoxLayout(); _sc.setSpacing(1); _sc.setContentsMargins(3, 0, 0, 0); _sc.addWidget(_su); _sc.addWidget(_sd)
        sfl.addWidget(spin, 1); sfl.addLayout(_sc)

        iv_row.addWidget(iv_lbl)
        iv_row.addSpacing(8)
        iv_row.addWidget(spin_frame)
        iv_row.addStretch()
        layout.addLayout(iv_row)
        layout.addSpacing(14)

        # Re-open wizard button
        _btn_style = (
            f"QPushButton {{ background-color: {btn_bg}; border: 1px solid {btn_bdr};"
            f" border-radius: 6px; color: {btn_fg}; padding: 7px 16px; font-size: 12px; }}"
            f" QPushButton:hover {{ background-color: {btn_hover}; }}"
            f" QPushButton:pressed {{ background-color: {btn_press}; }}"
        )
        wizard_btn = QPushButton(t.get("reopen_wizard", "Re-open Wizard…"))
        wizard_btn.setStyleSheet(_btn_style)

        def _reopen():
            from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.wizard_methods_window import (
                CharacterizationWizard,
            )
            from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.steps_manager import (
                update_step_screen,
            )
            from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import get as _get_tech
            from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.base import StepKind

            old_wiz = self.wizard_window
            vna = getattr(old_wiz, "vna_device", None) or getattr(self, "vna", None)
            wiz = CharacterizationWizard(vna_device=vna, caller_window=self)

            if old_wiz is not None:
                cal = getattr(old_wiz, "perm_calibration", None)
                if cal is not None:
                    wiz.perm_calibration = cal
                wiz.unknown_liquid_name = getattr(old_wiz, "unknown_liquid_name", "")
                wiz.temperature_c       = getattr(old_wiz, "temperature_c", 25.0)
                wiz.sweep_start_freq    = getattr(old_wiz, "sweep_start_freq", 50_000)
                wiz.sweep_stop_freq     = getattr(old_wiz, "sweep_stop_freq", 1_500_000_000)
                wiz.sweep_steps         = getattr(old_wiz, "sweep_steps", 101)
                wiz._precal_propagated  = True

                tech_id = getattr(old_wiz, "selected_technique_id", None)
                wiz.selected_technique_id = tech_id
                wiz.selected_method       = getattr(old_wiz, "selected_method", None)

                if tech_id:
                    descriptor = _get_tech(tech_id)
                    dut_step = next(
                        (i + 1 for i, s in enumerate(descriptor.steps)
                         if s.kind is StepKind.DUT_MEASURE),
                        None,
                    )
                    if dut_step is not None:
                        wiz.current_step = dut_step
                        update_step_screen(wiz)

            self.hide()
            wiz.show()
            dlg.accept()

        wizard_btn.clicked.connect(_reopen)
        layout.addWidget(wizard_btn)

        layout.addSpacing(14)
        layout.addWidget(_sep())
        layout.addSpacing(10)

        # Cancel / Apply
        _act = (
            f"QPushButton {{ background-color: {btn_bg}; border: 1px solid {btn_bdr};"
            f" border-radius: 6px; color: {btn_fg}; padding: 6px 22px; font-size: 12px; }}"
            f" QPushButton:hover {{ background-color: {btn_hover}; }}"
            f" QPushButton:pressed {{ background-color: {btn_press}; }}"
        )
        cancel_btn = QPushButton(t.get("cancel", "Cancel"))
        apply_btn  = QPushButton(t.get("apply",  "Apply"))
        cancel_btn.setStyleSheet(_act)
        apply_btn.setStyleSheet(_act)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

        cancel_btn.clicked.connect(dlg.reject)

        def _apply():
            self._realtime_timer.setInterval(max(100, int(spin.value() * 1000)))
            dlg.accept()

        apply_btn.clicked.connect(_apply)
        dlg.exec()

    def _open_file_sweep_config_dialog(self):
        t = self._texts.get("file_sweep_dialog", {})

        _is_dark = self.palette().window().color().lightness() < 128
        if _is_dark:
            title_color  = "#c8daf5"
            sep_color    = "#2d5a8e"
            tbl_bg       = "#0d1520"
            tbl_alt      = "#132030"
            tbl_text     = "#c8daf5"
            tbl_grid     = "#1e3a5a"
            hdr_bg       = "#0f1e30"
            hdr_fg       = "#7ab3f5"
            hdr_bdr      = "#2d5a8e"
            sel_bg       = "#1e4878"
            sel_fg       = "#ffffff"
            scroll_track = "#0a1020"
            scroll_hdl   = "#2d5a8e"
            scroll_hov   = "#3a72b0"
            btn_bg       = "#1a2640"
            btn_fg       = "#7ab3f5"
            btn_bdr      = "#2d5a8e"
            btn_hover    = "#1e3a60"
            btn_press    = "#142a50"
            outer_bdr    = "#2d5a8e"
            frame_bg     = "#1a2640"
            lbl_color    = "#7ab3f5"
            edit_bg      = "#0d1520"
            edit_bdr     = "#2d5a8e"
            no_file_col  = "#e05050"
            icon_btn_bg  = "#1a2640"
            icon_btn_bdr = "#2d5a8e"
            icon_btn_fg  = "#7ab3f5"
            icon_btn_hov = "#1e3a60"
        else:
            title_color  = "#1a2a3a"
            sep_color    = "#c8d4e0"
            tbl_bg       = "#ffffff"
            tbl_alt      = "#f4f4f6"
            tbl_text     = "#1a1a1a"
            tbl_grid     = "#d0d0d8"
            hdr_bg       = "#dce8f5"
            hdr_fg       = "#1a3a5c"
            hdr_bdr      = "#9bbcd8"
            sel_bg       = "#b8d4f8"
            sel_fg       = "#0a1a2a"
            scroll_track = "#e4e4e8"
            scroll_hdl   = "#aaaabc"
            scroll_hov   = "#888898"
            btn_bg       = "#dce8f5"
            btn_fg       = "#1a3a5c"
            btn_bdr      = "#9bbcd8"
            btn_hover    = "#c8dcf0"
            btn_press    = "#b0ccec"
            outer_bdr    = "#9bbcd8"
            frame_bg     = "#f0f4f8"
            lbl_color    = "#3a5a7a"
            edit_bg      = "#ffffff"
            edit_bdr     = "#9bbcd8"
            no_file_col  = "#c0392b"
            icon_btn_bg  = "#dce8f5"
            icon_btn_bdr = "#9bbcd8"
            icon_btn_fg  = "#1a3a5c"
            icon_btn_hov = "#c8dcf0"

        from PySide6.QtWidgets import QFrame as _QFrame

        _dlg_bg = "#0a1220" if _is_dark else "#eef4fa"

        dlg = QDialog(self)
        dlg.setWindowTitle(t.get("title", "Configure S11 File Source"))
        dlg.setFixedSize(560, 600)
        dlg.setStyleSheet(
            self.styleSheet()
            + f" QDialog {{ background-color: {_dlg_bg}; }}"
            + " QDialog QLabel { background: transparent; }"
        )

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(0)

        # ── Title ──────────────────────────────────────────────────────────
        title_lbl = QLabel(t.get("title", "Configure S11 File Source"))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {title_color};"
            " padding-bottom: 14px; border: none;"
        )
        layout.addWidget(title_lbl)

        def _sep():
            s = _QFrame()
            s.setFrameShape(_QFrame.Shape.HLine)
            s.setFixedHeight(1)
            s.setStyleSheet(f"background-color: {sep_color}; border: none;")
            return s

        layout.addWidget(_sep())
        layout.addSpacing(14)

        # ── Folder section ─────────────────────────────────────────────────
        folder_sect_lbl = QLabel(t.get("folder_label", "Folder:"))
        folder_sect_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {lbl_color}; border: none;"
        )
        layout.addWidget(folder_sect_lbl)
        layout.addSpacing(6)

        folder_frame = _QFrame()
        folder_frame.setStyleSheet(
            f"QFrame {{ border: 1px solid {outer_bdr}; border-radius: 8px;"
            f" background-color: {frame_bg}; }}"
        )
        folder_fl = QHBoxLayout(folder_frame)
        folder_fl.setContentsMargins(12, 10, 12, 10)
        folder_fl.setSpacing(8)

        folder_edit = QLineEdit()
        folder_edit.setPlaceholderText("…")
        folder_edit.setStyleSheet(
            f"QLineEdit {{ background-color: {edit_bg}; border: 1px solid {edit_bdr};"
            f" border-radius: 5px; padding: 4px 8px; color: {tbl_text}; }}"
        )
        if self._file_sweep_config:
            folder_edit.setText(str(Path(self._file_sweep_config[0]["path"]).parent))

        browse_btn = QPushButton(t.get("browse", "Browse…"))
        browse_btn.setFixedWidth(90)
        browse_btn.setStyleSheet(
            f"QPushButton {{ background-color: {btn_bg}; border: 1px solid {btn_bdr};"
            f" border-radius: 5px; color: {btn_fg}; padding: 4px 10px; }}"
            f" QPushButton:hover {{ background-color: {btn_hover}; }}"
            f" QPushButton:pressed {{ background-color: {btn_press}; }}"
        )
        folder_fl.addWidget(folder_edit, 1)
        folder_fl.addWidget(browse_btn)
        layout.addWidget(folder_frame)
        layout.addSpacing(14)

        # ── Sweep interval ─────────────────────────────────────────────────
        from PySide6.QtWidgets import QDoubleSpinBox

        class _FlexSpinBox(QDoubleSpinBox):
            """Accepts both '.' and ',' as decimal separator."""
            def valueFromText(self, text: str) -> float:
                sfx = self.suffix()
                s = text[: text.rfind(sfx)].strip() if sfx and sfx in text else text.strip()
                try:
                    return float(s.replace(",", "."))
                except ValueError:
                    return self.value()
            def validate(self, text: str, pos: int):
                return super().validate(text.replace(",", "."), pos)

        interval_row = QHBoxLayout()
        interval_lbl = QLabel(t.get("interval_label", "Sweep every:"))
        interval_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {lbl_color}; border: none;"
        )
        from PySide6.QtWidgets import QFrame as _QFr
        interval_spin = _FlexSpinBox()
        interval_spin.setRange(0.1, 3600.0)
        interval_spin.setSingleStep(0.1)
        interval_spin.setDecimals(1)
        interval_spin.setSuffix(t.get("interval_suffix", " s"))
        interval_spin.setValue(max(0.1, self._realtime_timer.interval() / 1000.0))
        interval_spin.setButtonSymbols(_FlexSpinBox.ButtonSymbols.NoButtons)
        interval_spin.setStyleSheet("QDoubleSpinBox { border: none; background: transparent; }")

        spin_frame = _QFr()
        spin_frame.setObjectName("spinboxContainer")
        spin_frame.setFixedHeight(32)
        spin_frame.setFixedWidth(100)
        spin_frame.setStyleSheet(
            f"QFrame#spinboxContainer {{ background-color: {edit_bg}; border: 1px solid {edit_bdr}; border-radius: 6px; }}"
            f" QPushButton#spinboxUpBtn, QPushButton#spinboxDownBtn {{ background-color: {btn_bg}; border: 1px solid {btn_bdr}; color: {btn_fg}; }}"
            f" QPushButton#spinboxUpBtn:hover, QPushButton#spinboxDownBtn:hover {{ background-color: {btn_hover}; }}"
        )
        spin_fl = QHBoxLayout(spin_frame)
        spin_fl.setContentsMargins(6, 1, 0, 1)
        spin_fl.setSpacing(0)
        _su = QPushButton("▲"); _su.setObjectName("spinboxUpBtn");   _su.setFixedSize(18, 14); _su.clicked.connect(interval_spin.stepUp)
        _sd = QPushButton("▼"); _sd.setObjectName("spinboxDownBtn"); _sd.setFixedSize(18, 14); _sd.clicked.connect(interval_spin.stepDown)
        _scol = QVBoxLayout(); _scol.setSpacing(1); _scol.setContentsMargins(3, 0, 0, 0)
        _scol.addWidget(_su); _scol.addWidget(_sd)
        spin_fl.addWidget(interval_spin, 1)
        spin_fl.addLayout(_scol)

        interval_row.addWidget(interval_lbl)
        interval_row.addSpacing(8)
        interval_row.addWidget(spin_frame)
        interval_row.addStretch()
        layout.addLayout(interval_row)
        layout.addSpacing(18)

        layout.addWidget(_sep())
        layout.addSpacing(14)

        # ── Files section ──────────────────────────────────────────────────
        files_hdr = QHBoxLayout()
        files_sect_lbl = QLabel(t.get("files_label", "S11 files — set order and display name:"))
        files_sect_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {lbl_color}; border: none;"
        )
        files_hdr.addWidget(files_sect_lbl)
        files_hdr.addStretch()

        _icon_style = (
            f"QPushButton {{ background-color: {icon_btn_bg}; border: 1px solid {icon_btn_bdr};"
            f" border-radius: 5px; color: {icon_btn_fg}; font-size: 14px;"
            f" padding: 0px; min-width: 28px; max-width: 28px;"
            f" min-height: 24px; max-height: 24px; }}"
            f" QPushButton:hover {{ background-color: {icon_btn_hov}; }}"
            f" QPushButton:disabled {{ color: {sep_color}; border-color: {sep_color}; }}"
        )
        up_btn = QPushButton("↑")
        dn_btn = QPushButton("↓")
        up_btn.setStyleSheet(_icon_style)
        dn_btn.setStyleSheet(_icon_style)
        files_hdr.addWidget(up_btn)
        files_hdr.addSpacing(4)
        files_hdr.addWidget(dn_btn)
        layout.addLayout(files_hdr)
        layout.addSpacing(6)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels([
            t.get("col_file", "File"),
            "",
        ])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(1, 34)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {outer_bdr};
                border-radius: 8px;
                background-color: {tbl_bg};
                alternate-background-color: {tbl_alt};
                color: {tbl_text};
                gridline-color: {tbl_grid};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 5px 10px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {sel_bg};
                color: {sel_fg};
            }}
            QHeaderView::section {{
                background-color: {hdr_bg};
                color: {hdr_fg};
                border: none;
                border-bottom: 1px solid {hdr_bdr};
                padding: 6px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QHeaderView::section:first {{
                border-top-left-radius: 7px;
            }}
            QHeaderView::section:last {{
                border-top-right-radius: 7px;
            }}
            QScrollBar:vertical {{
                background: {scroll_track};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_hdl};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_hov};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        layout.addWidget(table, 1)
        layout.addSpacing(8)

        no_files_lbl = QLabel(t.get("no_files", "No .s1p files found in this folder."))
        no_files_lbl.setStyleSheet(f"color: {no_file_col}; border: none; font-size: 11px;")
        no_files_lbl.setVisible(False)
        layout.addWidget(no_files_lbl)

        layout.addSpacing(14)
        layout.addWidget(_sep())
        layout.addSpacing(14)

        # ── Cancel / Apply ─────────────────────────────────────────────────
        _action_style = (
            f"QPushButton {{ background-color: {btn_bg}; border: 1px solid {btn_bdr};"
            f" border-radius: 6px; color: {btn_fg}; padding: 6px 22px; font-size: 12px; }}"
            f" QPushButton:hover {{ background-color: {btn_hover}; }}"
            f" QPushButton:pressed {{ background-color: {btn_press}; }}"
        )
        cancel_btn = QPushButton(t.get("cancel", "Cancel"))
        apply_btn  = QPushButton(t.get("apply", "Apply"))
        cancel_btn.setStyleSheet(_action_style)
        apply_btn.setStyleSheet(_action_style)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

        # ── Logic ──────────────────────────────────────────────────────────
        _rm_style = (
            "QPushButton { border: none; background: transparent;"
            " color: #cc4444; font-size: 13px; font-weight: bold; }"
            " QPushButton:hover { color: #ff6666; }"
        )

        def _add_remove_btn(row):
            rm = QPushButton("✕")
            rm.setFixedSize(28, 24)
            rm.setStyleSheet(_rm_style)
            rm.clicked.connect(lambda: _remove_row(rm))
            table.setCellWidget(row, 1, rm)

        def _remove_row(btn):
            for r in range(table.rowCount()):
                if table.cellWidget(r, 1) is btn:
                    table.removeRow(r)
                    no_files_lbl.setVisible(table.rowCount() == 0)
                    break

        def _populate(folder_str):
            folder = Path(folder_str)
            if not folder.is_dir():
                return
            def _nat_key(p):
                return [int(c) if c.isdigit() else c.lower()
                        for c in re.split(r'(\d+)', p.stem)]
            files = sorted(folder.glob("*.s1p"), key=_nat_key)
            table.setRowCount(0)
            existing = {e["path"]: e["name"] for e in self._file_sweep_config}
            for f in files:
                row = table.rowCount()
                table.insertRow(row)
                fname_item = QTableWidgetItem(f.name)
                fname_item.setFlags(fname_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                fname_item.setData(Qt.ItemDataRole.UserRole, str(f))
                table.setItem(row, 0, fname_item)
                _add_remove_btn(row)
            no_files_lbl.setVisible(table.rowCount() == 0)

        def _swap_rows(r1, r2):
            item0_a = table.takeItem(r1, 0)
            item0_b = table.takeItem(r2, 0)
            table.setItem(r1, 0, item0_b)
            table.setItem(r2, 0, item0_a)

        def _move_up():
            r = table.currentRow()
            if r > 0:
                _swap_rows(r, r - 1)
                table.setCurrentCell(r - 1, table.currentColumn())

        def _move_dn():
            r = table.currentRow()
            if 0 <= r < table.rowCount() - 1:
                _swap_rows(r, r + 1)
                table.setCurrentCell(r + 1, table.currentColumn())

        up_btn.clicked.connect(_move_up)
        dn_btn.clicked.connect(_move_dn)

        def _browse():
            folder = QFileDialog.getExistingDirectory(
                dlg, t.get("browse_title", "Select folder with .s1p files")
            )
            if folder:
                folder_edit.setText(folder)
                _populate(folder)

        browse_btn.clicked.connect(_browse)
        folder_edit.editingFinished.connect(lambda: _populate(folder_edit.text()))

        if folder_edit.text():
            _populate(folder_edit.text())

        cancel_btn.clicked.connect(dlg.reject)

        def _apply():
            config = []
            for row in range(table.rowCount()):
                path_item = table.item(row, 0)
                if path_item:
                    path = path_item.data(Qt.ItemDataRole.UserRole)
                    prev = next(
                        (e["name"] for e in self._file_sweep_config if e["path"] == path), ""
                    )
                    config.append({"path": path, "name": prev})
            if not config:
                return
            secs = interval_spin.value()
            if self._open_name_assignment_dialog(config, dlg):
                self._file_sweep_config = config
                self._file_sweep_idx    = 0
                self._sweep_mode        = "file"
                self._realtime_timer.setInterval(max(100, int(secs * 1000)))
                self._update_sweep_source_action()
                self._update_reconnect_btn_visibility()
                sc = self._texts.get("sweep_controls", {})
                self._set_sweep_status(sc.get("status_file_mode", "File mode"), "#ff9800")
                dlg.accept()

        apply_btn.clicked.connect(_apply)
        dlg.exec()

    def _open_name_assignment_dialog(self, config: list, parent) -> bool:
        """Assign display names to each file in config (modified in place). Returns True if confirmed."""
        t  = self._texts.get("file_sweep_dialog", {})
        nd = self._texts.get("name_dialog", {})

        _is_dark    = self.palette().window().color().lightness() < 128
        _dlg_bg     = "#0a1220" if _is_dark else "#eef4fa"
        title_color = "#c8daf5" if _is_dark else "#1a2a3a"
        sep_color   = "#2d5a8e" if _is_dark else "#c8d4e0"
        lbl_color   = "#7ab3f5" if _is_dark else "#3a5a7a"
        tbl_text    = "#c8daf5" if _is_dark else "#1a1a1a"
        edit_bg     = "#0d1520" if _is_dark else "#ffffff"
        edit_bdr    = "#2d5a8e" if _is_dark else "#9bbcd8"
        btn_bg      = "#1a2640" if _is_dark else "#dce8f5"
        btn_fg      = "#7ab3f5" if _is_dark else "#1a3a5c"
        btn_bdr     = "#2d5a8e" if _is_dark else "#9bbcd8"
        btn_hover   = "#1e3a60" if _is_dark else "#c8dcf0"
        btn_press   = "#142a50" if _is_dark else "#b0ccec"
        scroll_bg   = "#0a1220" if _is_dark else "#eef4fa"
        scroll_hdl  = "#2d5a8e" if _is_dark else "#9bbcd8"
        scroll_hov  = "#3a72b0" if _is_dark else "#7aaad0"

        from PySide6.QtWidgets import QFrame as _QF, QScrollArea

        _ROW_H    = 62   # px per file row (label + input + spacing)
        _MAX_ROWS = 4
        n         = len(config)
        scroll_h  = min(n, _MAX_ROWS) * _ROW_H + 8
        dlg_h     = 80 + scroll_h + 20 + 60   # title+sep + scroll + sep + buttons

        dlg = QDialog(parent)
        dlg.setWindowTitle(nd.get("title", "Assign display names"))
        dlg.setFixedSize(480, dlg_h)
        dlg.setStyleSheet(
            self.styleSheet()
            + f" QDialog {{ background-color: {_dlg_bg}; }}"
            + " QDialog QLabel { background: transparent; }"
        )

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(22, 18, 22, 18)
        outer.setSpacing(0)

        def _sep():
            s = _QF(); s.setFrameShape(_QF.Shape.HLine)
            s.setFixedHeight(1)
            s.setStyleSheet(f"background-color: {sep_color}; border: none;")
            return s

        title_lbl = QLabel(nd.get("title", "Assign display names"))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {title_color};"
            " padding-bottom: 12px; border: none;"
        )
        outer.addWidget(title_lbl)
        outer.addWidget(_sep())
        outer.addSpacing(10)

        # ── Scrollable file rows ───────────────────────────────────────────
        _edit_style = (
            f"QLineEdit {{ background-color: {edit_bg}; border: 1px solid {edit_bdr};"
            f" border-radius: 5px; padding: 4px 8px; color: {tbl_text}; }}"
        )
        _lbl_style = f"font-size: 11px; color: {lbl_color}; border: none; background: transparent;"

        rows_widget = QWidget()
        rows_widget.setStyleSheet("background: transparent;")
        rows_layout = QVBoxLayout(rows_widget)
        rows_layout.setContentsMargins(4, 4, 4, 4)
        rows_layout.setSpacing(0)

        name_edits: list[QLineEdit] = []
        for entry in config:
            lbl = QLabel(Path(entry["path"]).name)
            lbl.setStyleSheet(_lbl_style)
            lbl.setToolTip(entry["path"])
            ed = QLineEdit(entry.get("name", ""))
            ed.setPlaceholderText("sample")
            ed.setStyleSheet(_edit_style)
            name_edits.append(ed)
            rows_layout.addWidget(lbl)
            rows_layout.addSpacing(3)
            rows_layout.addWidget(ed)
            rows_layout.addSpacing(12)
        rows_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(rows_widget)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(scroll_h)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded if n > _MAX_ROWS
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: {scroll_bg};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_hdl};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_hov};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        outer.addWidget(scroll, 1)
        outer.addSpacing(10)
        outer.addWidget(_sep())
        outer.addSpacing(12)

        # ── Buttons ────────────────────────────────────────────────────────
        _act = (
            f"QPushButton {{ background-color: {btn_bg}; border: 1px solid {btn_bdr};"
            f" border-radius: 6px; color: {btn_fg}; padding: 6px 22px; font-size: 12px; }}"
            f" QPushButton:hover {{ background-color: {btn_hover}; }}"
            f" QPushButton:pressed {{ background-color: {btn_press}; }}"
        )
        cancel_btn = QPushButton(t.get("cancel", "Cancel"))
        ok_btn     = QPushButton(t.get("apply",  "Apply"))
        cancel_btn.setStyleSheet(_act)
        ok_btn.setStyleSheet(_act)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(ok_btn)
        outer.addLayout(btn_row)

        cancel_btn.clicked.connect(dlg.reject)

        def _confirm():
            for entry, ed in zip(config, name_edits):
                entry["name"] = ed.text().strip()
            dlg.accept()

        ok_btn.clicked.connect(_confirm)
        return dlg.exec() == QDialog.DialogCode.Accepted

    # --------------------------------------------------------------------- #

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_adjust_chart_layout"):
            self._adjust_chart_layout()

    def hideEvent(self, event):
        # A hidden window (e.g. while the wizard is re-opened on top) must not
        # keep sweeping: every tick costs ~200 ms on the GUI thread (solver +
        # chart redraw) and holds the VNA serial port the wizard needs.
        self._realtime_paused_by_hide = self._realtime_timer.isActive()
        if self._realtime_paused_by_hide:
            self._realtime_timer.stop()
            logging.info("[MeasurementMainWindow] hideEvent(): real-time paused")
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_realtime_paused_by_hide", False):
            self._realtime_paused_by_hide = False
            if getattr(self, "_realtime_check", None) and self._realtime_check.isChecked():
                self._realtime_timer.start()
                logging.info("[MeasurementMainWindow] showEvent(): real-time resumed")

    def closeEvent(self, event):
        self._window_closed = True
        self._realtime_timer.stop()
        self._sweep_in_progress = False  # discard any pending sweep callback
        self._flush_ini()
        # A device sweep in flight belongs to the wizard and finishes on its
        # own (its result handler checks _window_closed); file-mode work is
        # detached here. No quit()+wait(): a blocking serial read ignores it
        # and the wait only froze the close for up to a second.
        detach_background_threads(self._bg_threads)
        super().closeEvent(event)

    def return_to_menu_window(self):
        try:
            import matplotlib.pyplot as plt
            plt.close("all")
        except Exception:
            pass
        if self.vna:
            self.menu_windows = ModuleSelectionWindow(vna_device=self.vna)
        else:
            self.menu_windows = ModuleSelectionWindow()
        self.menu_windows.show()
        self.close()


# --------------------------------------------------------------------------- #

def _file_sweep_compute(path, cal):
    """Worker side of a file-mode sweep: parse the touchstone and solve ε."""
    import skrf as rf
    net = rf.Network(path)
    freqs = np.asarray(net.f, dtype=float)
    s11 = np.asarray(net.s[:, 0, 0], dtype=complex)
    return freqs, s11, cal.compute_epsilon(freqs, s11)


# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MeasurementMainWindow()
    window.show()
    sys.exit(app.exec())
