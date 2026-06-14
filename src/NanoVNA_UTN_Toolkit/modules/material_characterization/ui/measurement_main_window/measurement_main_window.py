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

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMainWindow, QMenu,
    QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

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
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff; border: none;")
        subtitle = QLabel("Complex permittivity ε_r(f) of the characterized material")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; color: #666666; border: none;")
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
            placeholder.setStyleSheet("font-size: 15px; color: gray;")
            self.main_layout.addWidget(placeholder, stretch=1)
            return

        self.main_layout.addWidget(self._build_epsilon_chart(result), stretch=1)

    # --------------------------------------------------------------------- #

    def _build_epsilon_chart(self, result):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.charts.epsilon_chart import (
            EpsilonChartManager,
        )
        exp = self._texts.get("export", {})

        geo = QGuiApplication.primaryScreen().availableGeometry()
        max_h = geo.height() // 2
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

        manager = EpsilonChartManager()
        title = exp.get("epsilon_title", "εr — {sample}").format(sample=self._sample_name())
        fig, ax, canvas = manager.create_wizard_epsilon_chart(
            result.f_hz, figsize=(7, 6.5), container_layout=chart_layout,
            title=title,
            real_label=self._texts.get("table", {}).get("eps_real", "ε′"),
            loss_label=self._texts.get("table", {}).get("eps_imag", "ε″"),
        )
        manager.update_epsilon_curves(
            ax, result.f_hz, result.eps_selected, canvas=canvas,
            candidates=result.eps_candidates,
        )
        self._epsilon_manager = manager
        self._epsilon_fig = fig
        self._epsilon_canvas = canvas

        canvas.setMaximumWidth(max_w)
        canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        canvas.customContextMenuRequested.connect(self._show_chart_context_menu)

        card_layout.addLayout(chart_layout, 1)
        card_layout.addWidget(_hsep())

        caption = QLabel(
            "ε′ = real part (energy storage)  ·  ε″ = imaginary part (dielectric losses)  ·  "
            "Faint grey curves are the other candidate roots  ·  Right-click to export"
        )
        caption.setWordWrap(True)
        caption.setStyleSheet("font-size: 11px; color: #555555; border: none; background: transparent;")
        card_layout.addWidget(caption)

        return card

    # --------------------------------------------------------------------- #

    def _show_chart_context_menu(self, pos):
        menu = QMenu(self)
        exp = self._texts.get("export", {})
        export_action = QAction(exp.get("export_epsilon", "Export εr image…"), self)
        export_action.triggered.connect(
            lambda: self._export_figure(self._epsilon_fig, f"epsilon_{self._sample_name()}")
        )
        menu.addAction(export_action)
        menu.exec(self._epsilon_canvas.mapToGlobal(pos))

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
        menu = self._texts.get("menu", {})
        menubar = self.menuBar()

        file_menu = menubar.addMenu(menu.get("file", "File"))
        back_action = QAction(menu.get("back_to_menu", "Back to menu"), self)
        back_action.triggered.connect(self.return_to_menu_window)
        file_menu.addAction(back_action)

        view_menu = menubar.addMenu(menu.get("view", "View"))

        s11_action = QAction(menu.get("show_s11", "S11 — Smith Chart"), self)
        s11_action.triggered.connect(self._show_s11_window)
        view_menu.addAction(s11_action)

        table_action = QAction(menu.get("show_table", "Results Table"), self)
        table_action.triggered.connect(self._show_table_window)
        view_menu.addAction(table_action)

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
