"""
Measurement results window for material characterization.

EN: Displays the computed complex permittivity of the unknown liquid: an info
    strip (technique, temperature, reference liquids, sweep), a per-frequency
    results table (epsilon_r', epsilon_r'', loss tangent), the epsilon_r(f)
    plot and the DUT S11 on a Smith chart. Reads everything from the wizard
    window's calibration manager. Full save/export is a Stage 2 feature.

ES: Muestra la permitividad compleja calculada del líquido incógnita: una
    franja de información (técnica, temperatura, líquidos de referencia,
    barrido), una tabla de resultados por frecuencia (epsilon_r', epsilon_r'',
    tangente de pérdidas), el gráfico de epsilon_r(f) y el S11 del DUT en una
    carta de Smith. Lee todo desde el administrador de calibración de la ventana
    del asistente. El guardado/exportado completo es una funcionalidad de la
    Etapa 2.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import sys
import logging

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
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

# Cap the number of table rows for readability on large sweeps.
_MAX_TABLE_ROWS = 250


class MeasurementMainWindow(QMainWindow):

    def __init__(self, vna_device=None, wizard_window=None):
        super().__init__()

        self.vna = vna_device
        self.wizard_window = wizard_window
        self._texts = load_text("characterization_measurement_main.json")

        self.setWindowTitle(self._texts.get("window_title", "Material Characterization - Results"))
        self.setGeometry(200, 200, 1100, 700)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen.center())
        self.move(window_geometry.topLeft())

        apply_window_icon(self)
        dark_light_config(self)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        title = QLabel(self._texts.get("title", "Permittivity Results"))
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.main_layout.addWidget(title, alignment=Qt.AlignTop)

        self._build_info_strip()
        self._build_body()
        self._create_menus()

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
            refs_text = f"{get_reference_liquid(cal.ref1_key).display_name} / " \
                        f"{get_reference_liquid(cal.ref2_key).display_name}"

        parts = [
            f"{info.get('technique', 'Technique:')} {technique}",
            f"{info.get('temperature', 'Temperature:')} {temp:.1f} °C" if temp is not None else "",
            f"{info.get('references', 'Reference liquids:')} {refs_text}",
            (f"{info.get('sweep', 'Sweep:')} {start/1e6:.3f}–{stop/1e6:.3f} MHz, {steps} pts"
             if start is not None and stop is not None else ""),
        ]
        strip = QLabel("    |    ".join(p for p in parts if p))
        strip.setWordWrap(True)
        strip.setStyleSheet("font-size: 12px; color: #cccccc; padding: 4px;")
        self.main_layout.addWidget(strip)

    def _build_body(self):
        result = getattr(self.wizard_window, "epsilon_result", None)

        if result is None:
            placeholder = QLabel(self._texts.get(
                "no_result", "No permittivity result is available. Please complete the wizard."
            ))
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("font-size: 15px; color: gray;")
            self.main_layout.addWidget(placeholder, stretch=1)
            return

        body = QHBoxLayout()
        body.addWidget(self._build_table(result), stretch=2)
        body.addWidget(self._build_plots(result), stretch=3)
        self.main_layout.addLayout(body, stretch=1)

    def _build_table(self, result):
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
            values = [f"{f_hz[i]/1e6:.3f} MHz", f"{re:.3f}", f"{loss:.3f}", f"{tand:.4f}"]
            for c, val in enumerate(values):
                table.setItem(r, c, QTableWidgetItem(val))

        table.resizeColumnsToContents()
        return table

    def _sample_name(self):
        name = (getattr(self.wizard_window, "unknown_liquid_name", "") or "").strip()
        return name or "sample"

    def _build_plots(self, result):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.charts.epsilon_chart import (
            EpsilonChartManager,
        )
        exp = self._texts.get("export", {})

        container = QWidget()
        layout = QVBoxLayout(container)
        self._epsilon_fig = None
        self._s11_fig = None

        # epsilon_r(f) plot
        manager = EpsilonChartManager()
        title = exp.get("epsilon_title", "εr — {sample}").format(sample=self._sample_name())
        fig, ax, canvas = manager.create_wizard_epsilon_chart(
            result.f_hz, figsize=(6, 3.5), container_layout=layout, title=title,
            real_label=self._texts.get("table", {}).get("eps_real", "ε′"),
            loss_label=self._texts.get("table", {}).get("eps_imag", "ε″"),
        )
        manager.update_epsilon_curves(
            ax, result.f_hz, result.eps_selected, canvas=canvas,
            candidates=result.eps_candidates,
        )
        self._epsilon_manager = manager
        self._epsilon_fig = fig

        eps_btn = QPushButton(exp.get("export_epsilon", "Export εr image"))
        eps_btn.clicked.connect(lambda: self._export_figure(
            self._epsilon_fig, f"epsilon_{self._sample_name()}"))
        layout.addWidget(eps_btn)

        # DUT S11 on a Smith chart (reuse shared util, read-only)
        cal = getattr(self.wizard_window, "perm_calibration", None)
        dut = cal.get_measurement("dut") if cal is not None else None
        if dut is not None:
            try:
                from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import SmithChartManager
                sm = SmithChartManager()
                s11_fig, _ax, _canvas, _c1, _c2 = sm.create_graphics_panel_smith_chart(
                    s_data=dut[1], freqs=dut[0], s_param="S11 (DUT)",
                    figsize=(4, 4), container_layout=layout, trace_color="orange",
                )
                self._s11_fig = s11_fig
                s11_btn = QPushButton(exp.get("export_s11", "Export S11 image"))
                s11_btn.clicked.connect(lambda: self._export_figure(
                    self._s11_fig, f"s11_{self._sample_name()}"))
                layout.addWidget(s11_btn)
            except Exception as exc:  # noqa: BLE001
                logging.error("[MeasurementMainWindow] S11 chart failed: %s", exc)

        return container

    # --------------------------------------------------------------------- #

    def _export_figure(self, fig, default_stem):
        """Save a matplotlib figure in high quality (dpi=300), like the rest of the app."""
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
        except Exception as exc:  # noqa: BLE001
            logging.error("[MeasurementMainWindow] export failed: %s", exc)
            QMessageBox.critical(self, "Export Error", f"Failed to save image: {exc}")

    # --------------------------------------------------------------------- #

    def _create_menus(self):
        menu = self._texts.get("menu", {})
        menubar = self.menuBar()
        file_menu = menubar.addMenu(menu.get("file", "File"))
        back_action = QAction(menu.get("back_to_menu", "Back to menu"), self)
        back_action.triggered.connect(self.return_to_menu_window)
        file_menu.addAction(back_action)

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
