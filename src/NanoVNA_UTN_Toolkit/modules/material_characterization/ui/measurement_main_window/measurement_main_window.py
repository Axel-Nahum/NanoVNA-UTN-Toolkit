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
import sys
import logging
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMainWindow, QMenu,
    QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
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
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    get_reference_liquid,
)

_MAX_TABLE_ROWS = 500

_CARD = "QWidget#card { background-color: #252525; border: 1px solid #3d3d3d; border-radius: 10px; }"
_BADGE = (
    "QLabel { background-color: #1e2a3a; color: #7ab3f5; border: 1px solid #2d5a8e;"
    " border-radius: 5px; padding: 3px 10px; font-size: 11px; }"
)


def _hsep(color="#363636"):
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
        self._result = None

        self.setWindowTitle(self._texts.get("window_title", "Material Characterization - Results"))
        self.setGeometry(200, 200, 1150, 720)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen.center())
        self.move(window_geometry.topLeft())

        apply_window_icon(self)
        dark_light_config(self)
        _dl = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve(),
        )
        self.is_dark_mode = _dl.value("Dark_Light/is_dark_mode", False, type=bool)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 14, 20, 14)
        self.main_layout.setSpacing(10)

        self._build_header()
        self.main_layout.addWidget(_hsep())
        self._build_info_strip()
        self.main_layout.addWidget(_hsep())
        self._build_body()
        self._create_menus()

    # --------------------------------------------------------------------- #

    def _build_header(self):
        title = QLabel(self._texts.get("title", "Permittivity Results"))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; border: none;")
        subtitle = QLabel("Complex permittivity ε_r(f) of the characterized material")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; border: none;")
        self.main_layout.addWidget(title)
        self.main_layout.addWidget(subtitle)

    # --------------------------------------------------------------------- #

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
        if cal is not None and cal.ref1_key and cal.ref2_key:
            refs_text = (
                f"{get_reference_liquid(cal.ref1_key).display_name} / "
                f"{get_reference_liquid(cal.ref2_key).display_name}"
            )

        items = [
            (info.get("technique",    "Technique"),   technique),
            (info.get("temperature",  "Temperature"), f"{temp:.1f} °C" if temp is not None else "—"),
            (info.get("references",   "References"),  refs_text),
            (info.get("sweep",        "Sweep"),
             f"{start/1e6:.3f}–{stop/1e6:.3f} MHz · {steps} pts"
             if start is not None and stop is not None else "—"),
        ]

        _BADGE = (
            "background-color: #1e2a3a; border: 1px solid #2d5a8e;"
            " border-radius: 6px; padding: 4px 14px;"
        )
        _KEY_STYLE = "font-size: 10px; font-weight: bold; color: #5a8fc0; border: none; background: transparent;"
        _VAL_STYLE = "font-size: 12px; color: #7ab3f5; border: none; background: transparent;"

        row = QHBoxLayout()
        row.setSpacing(16)
        row.setContentsMargins(0, 6, 0, 6)
        row.addStretch()

        for label_text, value_text in items:
            badge = QWidget()
            badge.setStyleSheet(_BADGE)
            badge_layout = QVBoxLayout(badge)
            badge_layout.setContentsMargins(0, 4, 0, 4)
            badge_layout.setSpacing(2)

            key_lbl = QLabel(label_text.rstrip(":"))
            key_lbl.setAlignment(Qt.AlignCenter)
            key_lbl.setStyleSheet(_KEY_STYLE)

            val_lbl = QLabel(value_text)
            val_lbl.setAlignment(Qt.AlignCenter)
            val_lbl.setStyleSheet(_VAL_STYLE)

            badge_layout.addWidget(key_lbl)
            badge_layout.addWidget(val_lbl)
            row.addWidget(badge)

        row.addStretch()
        self.main_layout.addLayout(row)

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

        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(_CARD)
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

        card_layout.addLayout(chart_layout, 1)
        card_layout.addWidget(marker_bar)
        card_layout.addWidget(_hsep())

        caption = QLabel(
            "ε′ = real part (energy storage)  ·  ε″ = imaginary part (dielectric losses)  ·  "
            "Right-click to export"
        )
        caption.setWordWrap(True)
        caption.setStyleSheet("font-size: 11px; border: none; background: transparent;")
        card_layout.addWidget(caption)

        return card

    # --------------------------------------------------------------------- #

    def _build_marker_data_row(self):
        """Two plain white labels below the canvas showing live frequency + permittivity."""
        from PySide6.QtWidgets import QSizePolicy

        _lstyle = "font-size: 13px; border: none; background: transparent;"

        row = QWidget()
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 6, 4, 6)
        row_layout.setSpacing(0)

        self._marker1_info_label = QLabel("—")
        self._marker1_info_label.setStyleSheet(_lstyle)
        self._marker1_info_label.setAlignment(Qt.AlignCenter)

        sep = QLabel("|")
        sep.setStyleSheet("font-size: 13px; border: none; background: transparent;")
        sep.setAlignment(Qt.AlignCenter)
        sep.setFixedWidth(20)

        self._marker2_info_label = QLabel("—")
        self._marker2_info_label.setStyleSheet(_lstyle)
        self._marker2_info_label.setAlignment(Qt.AlignCenter)

        row_layout.addWidget(self._marker1_info_label, 1)
        row_layout.addWidget(sep)
        row_layout.addWidget(self._marker2_info_label, 1)

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
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.charts.epsilon_chart import (
            _fill_nans,
        )

        _s = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
        m1_color = _s.value("Epsilon_Real/MarkerColor1", "#ff0000")
        m2_color = _s.value("Epsilon_Imag/MarkerColor1", "#ff0000")
        m1_size  = float(_s.value("Epsilon_Real/MarkerWidth1", "6"))
        m2_size  = float(_s.value("Epsilon_Imag/MarkerWidth1", "6"))

        freqs = np.asarray(result.f_hz, dtype=float)
        n = len(freqs)
        self._marker_freqs    = freqs
        self._marker_real_eps = _fill_nans(np.real(result.eps_selected))
        self._marker_loss_eps = _fill_nans(-np.imag(result.eps_selected))
        self._marker_n        = n

        try:
            fig.set_layout_engine("none")
        except Exception:
            pass

        # ------------------------------------------------------------------ #
        # Pixel-based layout: sliders occupy a fixed pixel band at the bottom
        # so they never overlap the x-axis labels regardless of window size.
        # ------------------------------------------------------------------ #
        _SL_H_PX   = 26   # slider track height in pixels
        _SL_BOT_PX = 10   # padding below sliders
        _GAP_PX    = 54   # gap between slider top and main-axes bottom
                          # (absorbs x-axis tick labels at any dpi/size)

        def _compute_positions():
            fig_h = fig.get_size_inches()[1] * fig.dpi
            sl_bot = _SL_BOT_PX / fig_h
            sl_h   = _SL_H_PX / fig_h
            ax_bot = (_SL_BOT_PX + _SL_H_PX + _GAP_PX) / fig_h
            ax_h   = max(0.30, 1.0 - ax_bot - 0.06)
            return sl_bot, sl_h, ax_bot, ax_h

        sl_bot0, sl_h0, ax_bot0, ax_h0 = _compute_positions()
        ax.set_position([0.10, ax_bot0, 0.86, ax_h0])

        # Marker cursors
        self._cursor1, = ax.plot([], [], "o", markersize=m1_size, color=m1_color,
                                  zorder=5, clip_on=True)
        self._cursor2, = ax.plot([], [], "o", markersize=m2_size, color=m2_color,
                                  zorder=5, clip_on=True)

        # Slider axes
        sl1_ax = fig.add_axes([0.08, sl_bot0, 0.38, sl_h0])
        sl2_ax = fig.add_axes([0.54, sl_bot0, 0.38, sl_h0])
        for sax in (sl1_ax, sl2_ax):
            sax.set_facecolor("#2a2a2a")
            for spine in sax.spines.values():
                spine.set_color("#444444")

        def _adjust_layout(event=None):
            try:
                sl_bot, sl_h, ax_bot, ax_h = _compute_positions()
                ax.set_position([0.10, ax_bot, 0.86, ax_h])
                sl1_ax.set_position([0.08, sl_bot, 0.38, sl_h])
                sl2_ax.set_position([0.54, sl_bot, 0.38, sl_h])
            except Exception:
                pass

        fig.canvas.mpl_connect("resize_event", _adjust_layout)

        # Restore last saved marker positions (clamped to valid range)
        _ini_mk = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
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

        def _fmt_freq(hz):
            return f"{hz/1e9:.4f} GHz" if hz >= 0.5e9 else f"{hz/1e6:.4f} MHz"

        self._marker_updating = False

        def _upd1(val):
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
                    f"f = {_fmt_freq(freq)}    ε' = {eps_r:.4f}")
            get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve()).setValue(
                "markers/index_1", idx
            )
            if getattr(self, "_cursors_linked", False):
                self._marker_updating = True
                slider2.set_val(idx)
                self._marker_updating = False
                if hasattr(self, "_cursor2") and self._cursor2 is not None:
                    self._cursor2.set_data([freq], [self._marker_loss_eps[idx]])
                if hasattr(self, "_marker2_info_label"):
                    self._marker2_info_label.setText(
                        f"f = {_fmt_freq(freq)}    ε'' = {self._marker_loss_eps[idx]:.4f}")
                get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve()).setValue(
                    "markers/index_2", idx
                )
            canvas.draw_idle()

        def _upd2(val):
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
                    f"f = {_fmt_freq(freq)}    ε'' = {eps_i:.4f}")
            get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve()).setValue(
                "markers/index_2", idx
            )
            if getattr(self, "_cursors_linked", False):
                self._marker_updating = True
                slider1.set_val(idx)
                self._marker_updating = False
                if hasattr(self, "_cursor1") and self._cursor1 is not None:
                    self._cursor1.set_data([freq], [self._marker_real_eps[idx]])
                if hasattr(self, "_marker1_info_label"):
                    self._marker1_info_label.setText(
                        f"f = {_fmt_freq(freq)}    ε' = {self._marker_real_eps[idx]:.4f}")
                get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve()).setValue(
                    "markers/index_1", idx
                )
            canvas.draw_idle()

        slider1.on_changed(lambda val: _upd1(int(val)))
        slider2.on_changed(lambda val: _upd2(int(val)))

        # Persist link state
        _link_ini = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
        self._cursors_linked = _link_ini.value("markers/linked", "true").lower() != "false"

        def _toggle_link():
            self._cursors_linked = not self._cursors_linked
            get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve()).setValue(
                "markers/linked", self._cursors_linked
            )
            if self._cursors_linked:
                slider2.set_val(int(slider1.val))

        self._toggle_cursors_link = _toggle_link

        self._slider1 = slider1
        self._slider2 = slider2

        # ---- Cursor visibility toggle ---- #
        _vis_ini = get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve())
        self._cursor1_visible = _vis_ini.value("markers/visible_1", "true").lower() != "false"
        self._cursor2_visible = _vis_ini.value("markers/visible_2", "true").lower() != "false"

        def _set_cursor1_visible(visible: bool):
            self._cursor1_visible = visible
            if hasattr(self, "_cursor1") and self._cursor1 is not None:
                self._cursor1.set_visible(visible)
            if hasattr(self, "_marker1_info_label"):
                self._marker1_info_label.setVisible(visible)
            get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve()).setValue(
                "markers/visible_1", visible
            )
            canvas.draw_idle()

        def _set_cursor2_visible(visible: bool):
            self._cursor2_visible = visible
            if hasattr(self, "_cursor2") and self._cursor2 is not None:
                self._cursor2.set_visible(visible)
            if hasattr(self, "_marker2_info_label"):
                self._marker2_info_label.setVisible(visible)
            get_settings(_CHART_INI_EXE, _CHART_INI_DEV, Path(__file__).resolve()).setValue(
                "markers/visible_2", visible
            )
            canvas.draw_idle()

        self._set_cursor1_visible = _set_cursor1_visible
        self._set_cursor2_visible = _set_cursor2_visible

        # Apply persisted state before first draw
        _set_cursor1_visible(self._cursor1_visible)
        _set_cursor2_visible(self._cursor2_visible)

        _upd1(_init_idx1)
        _upd2(_init_idx2)

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
        menu = QMenu(self)

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
            }
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
        cal = getattr(self.wizard_window, "perm_calibration", None)
        dut = cal.get_measurement("dut") if cal is not None else None
        if dut is None:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("S11 — Smith Chart (DUT)")
        dlg.setMinimumSize(520, 520)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(8, 8, 8, 8)

        try:
            from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import SmithChartManager
            sm = SmithChartManager()
            s11_fig, _ax, _canvas, _c1, _c2 = sm.create_graphics_panel_smith_chart(
                s_data=dut[1], freqs=dut[0], s_param="S11 (DUT)",
                figsize=(5, 5), container_layout=layout, trace_color="orange",
            )
            self._s11_fig = s11_fig

            _canvas.setContextMenuPolicy(Qt.CustomContextMenu)
            _canvas.customContextMenuRequested.connect(
                lambda pos: self._s11_context_menu(pos, _canvas)
            )
        except Exception as exc:
            logging.error("[MeasurementMainWindow] S11 chart failed: %s", exc)
            layout.addWidget(QLabel(f"Could not render S11 chart: {exc}"))

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

        import csv
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
            scroll_press   = "#28282e"       # gris oscuro al presionar
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
            scroll_press   = "#6a6a80"
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
        temp_str  = f"{temp:.1f} °C" if temp is not None else "—"
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
                width: 12px;
                border-radius: 6px;
                margin: 4px 2px 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_hover};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {scroll_press};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
                background: none;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        for r, i in enumerate(rows_idx):
            re_val   = float(np.real(eps[i]))
            loss_val = float(-np.imag(eps[i]))
            if re_val != 0.0 and np.isfinite(re_val) and np.isfinite(loss_val):
                tand_val = loss_val / re_val
            else:
                tand_val = float("nan")
            for c, val in enumerate([
                f"{f_hz[i]/1e6:.4f}",
                _fmt(re_val,   4),
                _fmt(loss_val, 4),
                _fmt(tand_val, 5),
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

        legend_lbl = QLabel("  — : No data (NaN)")
        legend_lbl.setStyleSheet(
            f"font-size: 10px; color: {legend_color}; border: none;"
            " font-style: italic;"
        )
        footer_row.addWidget(legend_lbl)
        footer_row.addStretch()

        export_btn = QPushButton("  Export CSV  ")
        export_btn.setDefault(False)
        export_btn.setAutoDefault(False)
        export_btn.setFixedHeight(28)
        export_btn.setStyleSheet(
            f"QPushButton {{ background-color: {btn_bg}; color: {btn_fg};"
            f" border: 1px solid {btn_bdr}; border-radius: 6px;"
            f" padding: 3px 12px; font-size: 11px; font-weight: bold; }}"
            f" QPushButton:hover {{ background-color: {btn_hover};"
            f"   border-color: {scroll_hover}; }}"
            f" QPushButton:pressed {{ background-color: {btn_press}; }}"
        )

        def _do_export_csv():
            path, _ = QFileDialog.getSaveFileName(
                dlg, "Save CSV", "permittivity.csv", "CSV Files (*.csv)"
            )
            if not path:
                return
            try:
                e_real = np.real(eps)
                e_imag = -np.imag(eps)
                with open(path, "w", newline="", encoding="utf-8") as fh:
                    writer = csv.writer(fh)
                    writer.writerow(["Frequency (Hz)", "Epsilon_real", "Epsilon_imag"])
                    for freq, er, ei in zip(f_hz, e_real, e_imag):
                        writer.writerow([f"{freq:.4f}", f"{er:.6f}", f"{ei:.6f}"])
                QMessageBox.information(dlg, "Saved", f"CSV saved to:\n{path}")
            except Exception as exc:
                QMessageBox.critical(dlg, "Error", f"Failed to save CSV:\n{exc}")

        export_btn.clicked.connect(_do_export_csv)
        footer_row.addWidget(export_btn)

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
            self._epsilon_manager.update_epsilon_curves(
                self._epsilon_ax,
                self._result.f_hz,
                self._result.eps_selected,
                canvas=None,
            )
            if not getattr(self, "_grid_enabled", True):
                self._epsilon_ax.grid(False)
            _pm2 = get_settings(_PM_INI_EXE, _PM_INI_DEV, Path(__file__).resolve())
            if not _pm2.value("auto_scale/current_state", True, type=bool):
                _ymin = _pm2.value("set_range/ymin", None, type=float)
                _ymax = _pm2.value("set_range/ymax", None, type=float)
                if _ymin is not None and _ymax is not None and _ymax > _ymin:
                    self._epsilon_ax.set_ylim(_ymin, _ymax)
            self._restore_markers_after_redraw()
            self._epsilon_canvas.draw_idle()
        except Exception as exc:
            logging.error("[MeasurementMainWindow] redraw_chart failed: %s", exc)

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

    def return_to_menu_window(self):
        if self.vna:
            self.menu_windows = ModuleSelectionWindow(vna_device=self.vna)
        else:
            self.menu_windows = ModuleSelectionWindow()
        self.menu_windows.show()
        self.close()


# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MeasurementMainWindow()
    window.show()
    sys.exit(app.exec())
