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

        technique = getattr(wiz, "selected_method", "") or ""
        temp = getattr(wiz, "temperature_c", None)
        start = getattr(wiz, "sweep_start_freq", None)
        stop = getattr(wiz, "sweep_stop_freq", None)
        steps = getattr(wiz, "sweep_steps", None)

        refs_text = "-"
        if cal is not None and cal.ref1_key and cal.ref2_key:
            refs_text = (
                f"{get_reference_liquid(cal.ref1_key).display_name} / "
                f"{get_reference_liquid(cal.ref2_key).display_name}"
            )

        badges = [
            (info.get("technique", "Technique"), technique),
            (info.get("temperature", "Temperature"), f"{temp:.1f} °C" if temp is not None else "—"),
            (info.get("references", "References"), refs_text),
            (info.get("sweep", "Sweep"),
             f"{start/1e6:.3f}–{stop/1e6:.3f} MHz, {steps} pts"
             if start is not None and stop is not None else "—"),
        ]

        row = QHBoxLayout()
        row.setSpacing(8)
        row.setContentsMargins(0, 4, 0, 4)
        row.addStretch()
        for label_text, value_text in badges:
            badge = QLabel(f"<b>{label_text}</b>  {value_text}")
            badge.setStyleSheet(
                "background-color: #1e2a3a; color: #7ab3f5; border: 1px solid #2d5a8e;"
                " border-radius: 5px; padding: 4px 12px; font-size: 11px;"
            )
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
            "Faint grey curves are the other candidate roots  ·  Right-click to export"
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
        # Store pre-computed arrays for use in redraw restores
        self._marker_freqs     = freqs
        self._marker_real_eps  = _fill_nans(np.real(result.eps_selected))
        self._marker_loss_eps  = _fill_nans(-np.imag(result.eps_selected))
        self._marker_n         = n

        # Disable constrained layout, then explicitly reposition the main axes
        # to leave room at the bottom for the two slider axes.
        try:
            fig.set_layout_engine("none")
        except Exception:
            pass
        # [left, bottom, width, height] in figure-normalized coords (0–1)
        ax.set_position([0.10, 0.22, 0.86, 0.68])

        # Marker cursors on the main axes (x in Hz, same as update_epsilon_curves)
        self._cursor1, = ax.plot([], [], "o", markersize=m1_size, color=m1_color,
                                  zorder=5, clip_on=True)
        self._cursor2, = ax.plot([], [], "o", markersize=m2_size, color=m2_color,
                                  zorder=5, clip_on=True)

        # Two slider axes side by side at the bottom of the figure
        sl1_ax = fig.add_axes([0.08, 0.08, 0.38, 0.06])
        sl2_ax = fig.add_axes([0.54, 0.08, 0.38, 0.06])
        for sax in (sl1_ax, sl2_ax):
            sax.set_facecolor("#2a2a2a")
            for spine in sax.spines.values():
                spine.set_color("#444444")

        try:
            slider1 = Slider(sl1_ax, "", 0, n - 1, valinit=0,      valstep=1,
                             track_color="#555555",
                             handle_style={"facecolor": m1_color, "edgecolor": m1_color, "size": 10})
            slider2 = Slider(sl2_ax, "", 0, n - 1, valinit=n // 2, valstep=1,
                             track_color="#555555",
                             handle_style={"facecolor": m2_color, "edgecolor": m2_color, "size": 10})
        except TypeError:
            slider1 = Slider(sl1_ax, "", 0, n - 1, valinit=0,      valstep=1, color=m1_color)
            slider2 = Slider(sl2_ax, "", 0, n - 1, valinit=n // 2, valstep=1, color=m2_color)

        for s in (slider1, slider2):
            try:
                s.vline.set_visible(False)
            except Exception:
                pass
            s.label.set_visible(False)
            s.valtext.set_visible(False)

        def _fmt_freq(hz):
            return f"{hz/1e9:.4f} GHz" if hz >= 0.5e9 else f"{hz/1e6:.4f} MHz"

        def _upd1(val):
            if not hasattr(self, "_cursor1") or self._cursor1 is None:
                return
            idx = min(max(int(round(val)), 0), self._marker_n - 1)
            freq = self._marker_freqs[idx]
            eps_r = self._marker_real_eps[idx]
            self._cursor1.set_data([freq], [eps_r])
            if hasattr(self, "_marker1_info_label"):
                self._marker1_info_label.setText(
                    f"f = {_fmt_freq(freq)}    ε' = {eps_r:.4f}")
            canvas.draw_idle()

        def _upd2(val):
            if not hasattr(self, "_cursor2") or self._cursor2 is None:
                return
            idx = min(max(int(round(val)), 0), self._marker_n - 1)
            freq = self._marker_freqs[idx]
            eps_i = self._marker_loss_eps[idx]
            self._cursor2.set_data([freq], [eps_i])
            if hasattr(self, "_marker2_info_label"):
                self._marker2_info_label.setText(
                    f"f = {_fmt_freq(freq)}    ε'' = {eps_i:.4f}")
            canvas.draw_idle()

        slider1.on_changed(lambda val: _upd1(int(val)))
        slider2.on_changed(lambda val: _upd2(int(val)))

        self._slider1 = slider1
        self._slider2 = slider2

        _upd1(0)
        _upd2(n // 2)

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

    # --------------------------------------------------------------------- #

    def _show_chart_context_menu(self, pos):
        menu = QMenu(self)
        export_action = QAction("Export…", self)
        export_action.triggered.connect(self._open_chart_export_dialog)
        menu.addAction(export_action)
        menu.exec(self._epsilon_canvas.mapToGlobal(pos))

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

        dlg = QDialog(self)
        dlg.setWindowTitle("Results Table")
        dlg.setMinimumSize(480, 600)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(8, 8, 8, 8)

        t = self._texts.get("table", {})
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([
            t.get("frequency", "Frequency"),
            t.get("eps_real", "epsilon_r'"),
            t.get("eps_imag", "epsilon_r''"),
            t.get("loss_tangent", "tan delta"),
        ])

        f_hz = result.f_hz
        eps = result.eps_selected
        n = len(f_hz)
        stride = max(1, n // _MAX_TABLE_ROWS)
        rows = list(range(0, n, stride))
        table.setRowCount(len(rows))

        for r, i in enumerate(rows):
            re = float(np.real(eps[i]))
            loss = float(-np.imag(eps[i]))
            tand = loss / re if re not in (0.0,) and np.isfinite(re) else float("nan")
            for c, val in enumerate([f"{f_hz[i]/1e6:.3f} MHz", f"{re:.3f}", f"{loss:.3f}", f"{tand:.4f}"]):
                table.setItem(r, c, QTableWidgetItem(val))

        table.resizeColumnsToContents()
        layout.addWidget(table)
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
