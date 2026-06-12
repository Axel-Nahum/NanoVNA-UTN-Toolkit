"""
Graph Preview Export Dialog for NanoVNA Measurements
Provides an interactive preview of S-parameter graphs with navigation
and PDF export functionality using Matplotlib and PySide6.

Each graph has independent Marker 1 and Marker 2 checkboxes.
Markers can be dragged independently for each graph.
Deactivating a marker hides its cursor immediately.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

import numpy as np
import skrf as rf
import copy

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QWidget,
    QCheckBox, QHBoxLayout, QLineEdit, QComboBox, QFrame,
    QRadioButton, QButtonGroup, QStylePainter, QStyleOptionComboBox
)
from PySide6.QtCore import Qt, QLocale
from PySide6.QtGui import QDoubleValidator, QGuiApplication

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt

plt.rcParams['mathtext.fontset'] = 'cm'  
plt.rcParams['text.usetex'] = False       
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'    
plt.rcParams['mathtext.rm'] = 'serif' 

logger = logging.getLogger(__name__)

JsonResourceLoader = safe_import("NanoVNA_UTN_Toolkit.shared.resources.json_resource_loader", "JsonResourceLoader")

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

class _CenteredComboBox(QComboBox):
    """QComboBox that draws its selected text centered."""
    def paintEvent(self, event):
        from PySide6.QtWidgets import QStyle
        from PySide6.QtGui import QPalette
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        opt.currentText = ""
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)
        arrow_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, opt,
            QStyle.SubControl.SC_ComboBoxArrow, self
        )
        text_rect = self.rect()
        text_rect.setRight(arrow_rect.left())
        group = QPalette.ColorGroup.Normal if self.isEnabled() else QPalette.ColorGroup.Disabled
        painter.setPen(self.palette().color(group, QPalette.ColorRole.Text))
        painter.drawText(text_rect, Qt.AlignCenter | Qt.AlignVCenter, self.currentText())


def _make_centered_combo(items):
    combo = _CenteredComboBox()
    combo.addItems(items)
    combo.setCurrentIndex(0)
    for j in range(combo.count()):
        combo.setItemData(j, Qt.AlignCenter, Qt.TextAlignmentRole)
    return combo


class GraphPreviewExportDialog(QDialog):
    def __init__(self, parent=None, freqs=None, s11_data=None, s21_data=None,
             measurement_name=None, output_path=None):
        super().__init__(parent)

# ------------------------------------------------------------------------------------------------------------------- #
# Load JSON 
# ------------------------------------------------------------------------------------------------------------------- #

        settings = get_settings(
            "INI/dut_measurement/preferences/preferences.ini",
            "shared/utils/preferences/preferences.ini", 
            Path(__file__).resolve()
        )

        current_lang = settings.value("Preferences/language", "en")

        self.resourceLoader = JsonResourceLoader(
            self_window = self, 
            module = "dut_measurement", 
            lang = current_lang, 
            json_resource = "dut_measurement_features.json"
        )

        self.resourceLoader.load_pdf_export_resources()  

# ------------------------------------------------------------------------------------------------------------------- #

        self.freqs = freqs
        self.s11_data = s11_data
        self.s21_data = s21_data
        self.measurement_name = measurement_name
        self.output_path = output_path
        self.current_graph_index = 0

        self.saved_figures = []
        self.current_figure = 0

        self.current_index = 0
        self.saved_graphs = []
        self.total_graphs = 5

        # Track marker states for each graph separately
        self.graph_markers = {}  # key=index, value=[marker1_active, marker2_active]
        self.annotations = []    # active annotations for current graph
        self.markers = []        # marker Line2D objects

        self.marker_positions = {i: [None, None] for i in range(5)}
        self.marker_active = {i: [False, False] for i in range(5)}

        self.setWindowTitle("Export Graph Preview")
        self.setModal(True)
        screen = QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        screen_height = geometry.height()
        screen_width = geometry.width()

        dialog_h = max(660, min(780, int(screen_height * 0.72)))
        self.setFixedSize(740, dialog_h)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # --- Header row: title centered, page indicator pinned top-right ---
        self.page_label = QLabel(f"1 / {self.total_graphs}")
        self.page_label.setStyleSheet("color: #aaaaaa; font-size: 12px; font-weight: bold; min-width: 40px;")
        self.page_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        title_label = QLabel(f"{self.pdf_preview_ready}")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #e0e0e0;")
        title_label.setAlignment(Qt.AlignCenter)

        # Left placeholder keeps the title visually centered despite page_label on right
        left_ph = QWidget()
        left_ph.setFixedWidth(50)

        header_row = QHBoxLayout()
        header_row.addWidget(left_ph)
        header_row.addWidget(title_label, 1, Qt.AlignCenter)
        header_row.addWidget(self.page_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        main_layout.addLayout(header_row)

        subtitle_label = QLabel(f"{self.pdf_preview_instruction}")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 11px; color: #999999;")
        main_layout.addWidget(subtitle_label)

        main_layout.addSpacing(4)

        # --- Create figure and canvas ---
        self.fig, self.ax = plt.subplots()
        self.fig.patch.set_facecolor("white")
        self.ax.set_facecolor("white")
        self.fig.subplots_adjust(left=0.15, right=0.95, top=0.9, bottom=0.18)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(360)
        self.canvas.resizeEvent = self._on_canvas_resize

        # --- Previous / Next buttons ---
        self.prev_button = NoEnterButton(f"{self.pdf_preview_previous}")
        self.next_button = NoEnterButton(f"{self.pdf_preview_next}")

        self.prev_button.setFocusPolicy(Qt.NoFocus)
        self.next_button.setFocusPolicy(Qt.NoFocus)

        nav_btn_style = """
            QPushButton {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 5px;
                font-weight: bold;
                padding: 4px 16px;
                min-width: 80px;
                font-size: 12px;
            }
            QPushButton:hover:enabled {
                background-color: #e0e0e0;
                border-color: #999999;
            }
            QPushButton:disabled {
                background-color: #f8f8f8;
                color: #bbbbbb;
                border-color: #e0e0e0;
            }
        """
        self.prev_button.setStyleSheet(nav_btn_style)
        self.next_button.setStyleSheet(nav_btn_style)

        # --- Read marker colors from graphics_config.ini ---
        try:
            _gfx = get_settings(
                "INI/dut_measurement/graphics_config/graphics_config.ini",
                "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
                Path(__file__).resolve()
            )
            _marker_color1 = _gfx.value("Graphic1/MarkerColor1", "#00ff00")
            _marker_color2 = _gfx.value("Graphic2/MarkerColor1", "#ffaa00")
        except Exception:
            _marker_color1 = "#00ff00"
            _marker_color2 = "#ffaa00"

        # --- Marker checkboxes and frequency inputs
        self.marker_checkboxes = {}  # key=graph_index, value=(marker1, marker2)
        self.marker_freq_edits = {}  # key=graph_index, value=(edit1, combo1, edit2, combo2)

        for i in range(5):

            # --- Marker checkboxes ---
            marker1 = QCheckBox(f"{self.pdf_preview_marker_1}")
            marker1.setStyleSheet(f"color: {_marker_color1}; font-weight: bold; font-size: 12pt;")
            marker2 = QCheckBox(f"{self.pdf_preview_marker_2}")
            marker2.setStyleSheet(f"color: {_marker_color2}; font-weight: bold; font-size: 12pt;")
            marker1.stateChanged.connect(lambda _, idx=i: self._update_markers(idx))
            marker2.stateChanged.connect(lambda _, idx=i: self._update_markers(idx))
            self.marker_checkboxes[i] = (marker1, marker2)

            # --- Frequency inputs (white style) ---
            edit1 = QLineEdit()
            edit1.setFixedWidth(80)
            edit1.setStyleSheet("background-color: white; color: black; border: 2px solid white; border-radius: 3px;")
            combo1 = _make_centered_combo(["kHz", "MHz", "GHz"])

            edit2 = QLineEdit()
            edit2.setFixedWidth(80)
            edit2.setStyleSheet("background-color: white; color: black; border: 2px solid white; border-radius: 3px;")
            combo2 = _make_centered_combo(["kHz", "MHz", "GHz"])

            # --- Inline validator function ---
            def validate_input(edit, combo):
                text = edit.text().strip()
                if not text:
                    return
                try:
                    val = float(text)
                except ValueError:
                    return

                unit = combo.currentText()
                min_f = self.freqs[0]
                max_f = self.freqs[-1]

                # Convert freq limits to selected unit
                if unit == "kHz":
                    min_u, max_u = min_f / 1e3, max_f / 1e3
                elif unit == "MHz":
                    min_u, max_u = min_f / 1e6, max_f / 1e6
                else:  # GHz
                    min_u, max_u = min_f / 1e9, max_f / 1e9

                # --- Enforce numeric limits ---
                if unit == "kHz":
                    if val < 50:
                        val = 50
                    val = min(max(val, min_u), max_u)
                    text = f"{val:.2f}"
                elif unit == "MHz":
                    val = min(max(val, min_u), max_u)
                    text = f"{val:.2f}"
                elif unit == "GHz":
                    if val > 1.5:
                        val = 1.5
                    val = min(max(val, min_u), max_u)
                    text = f"{val:.2f}"
                else:
                    text = f"{val:.2f}"

                edit.setText(text)

            # --- Connect editing events ---
            edit1.editingFinished.connect(lambda e=edit1, c=combo1: validate_input(e, c) or self._on_marker_input_changed())
            edit2.editingFinished.connect(lambda e=edit2, c=combo2: validate_input(e, c) or self._on_marker_input_changed())

            combo1.currentIndexChanged.connect(self._on_marker_input_changed)
            combo2.currentIndexChanged.connect(self._on_marker_input_changed)

            # --- Store marker input references ---
            self.marker_freq_edits[i] = (edit1, combo1, edit2, combo2)

        # --- Layout for markers and their inputs ---
        self.marker_layout = QHBoxLayout()
        self.marker_layout.setContentsMargins(0, 0, 0, 0)
        self.marker_layout.setSpacing(0)

        marker_container = QWidget()
        marker_container_layout = QHBoxLayout(marker_container)
        marker_container_layout.setContentsMargins(0, 0, 0, 0)
        marker_container_layout.addStretch()
        marker_container_layout.addLayout(self.marker_layout)
        marker_container_layout.addStretch()

        # --- Magnitude unit selector (created here so nav_strip can reference them) ---
        rb_style = "QRadioButton { color: #333333; font-size: 14px; background-color: transparent; } QRadioButton::indicator { width: 14px; height: 14px; }"
        self.rb_db = QRadioButton("dB")
        self.rb_db.setChecked(True)
        self.rb_db.setFocusPolicy(Qt.NoFocus)
        self.rb_db.setStyleSheet(rb_style)
        self.rb_linear = QRadioButton("Linear")
        self.rb_linear.setFocusPolicy(Qt.NoFocus)
        self.rb_linear.setStyleSheet(rb_style)
        self.unit_group = QButtonGroup(self)
        self.unit_group.addButton(self.rb_db)
        self.unit_group.addButton(self.rb_linear)
        self.unit_group.buttonClicked.connect(self._on_unit_changed)

        # --- Canvas inside a framed container ---
        canvas_frame = QFrame()
        canvas_frame.setStyleSheet(
            "QFrame { border: 1px solid #444444; border-radius: 4px; background-color: white; }"
        )
        frame_layout = QVBoxLayout(canvas_frame)
        frame_layout.setContentsMargins(3, 3, 3, 3)
        frame_layout.setSpacing(0)
        frame_layout.addWidget(self.canvas)

        # --- Nav strip inside the white frame: Prev | stretch | dB/Linear | stretch | Next ---
        nav_strip = QHBoxLayout()
        nav_strip.setContentsMargins(8, 5, 8, 5)
        nav_strip.addWidget(self.prev_button)
        nav_strip.addStretch(1)
        nav_strip.addWidget(self.rb_db)
        nav_strip.addSpacing(60)
        nav_strip.addWidget(self.rb_linear)
        nav_strip.addStretch(1)
        nav_strip.addWidget(self.next_button)
        frame_layout.addLayout(nav_strip)

        main_layout.addWidget(canvas_frame, alignment=Qt.AlignCenter)

        # --- Small spacing between canvas frame and markers ---
        main_layout.addSpacing(6)

        # --- Marker container centered below canvas ---
        main_layout.addWidget(marker_container, alignment=Qt.AlignCenter)

        main_layout.addSpacing(10)

        # --- Bottom toolbar ---
        self.export_button = QPushButton(f"{self.pdf_preview_generate_report}")
        self.export_button.setEnabled(False)
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 5px;
                font-size: 12px;
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

        # --- Connect navigation ---
        self.prev_button.clicked.connect(self._show_previous_graph)
        self.next_button.clicked.connect(self._show_next_graph)

        # --- Initial plot ---
        self._plot_graph(self.current_graph_index)
        self._update_marker_checkboxes()
        self._update_markers()
        self._update_nav_buttons()

    def _on_canvas_resize(self, event):
        w = self.canvas.width()
        h = self.canvas.height()

        # Ajustar márgenes proporcionalmente al tamaño real del canvas
        margin = max(0.10, min(0.20, 0.15 * (600 / max(w, h))))
        self.fig.subplots_adjust(
            left=margin,
            right=1 - margin,
            top=1 - margin - 0.04,   # top gap so title has breathing room
            bottom=margin
        )

        # Ajustar escala del texto (se vuelve muy grande en pantallas chicas)
        scale = (w / 800)
        scale = max(0.6, min(1.0, scale))   # clamp entre 0.6 y 1.0

        self.ax.title.set_fontsize(14 * scale)
        self.ax.xaxis.label.set_fontsize(11 * scale)
        self.ax.yaxis.label.set_fontsize(11 * scale)
        for tick in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            tick.set_fontsize(9 * scale)

        if hasattr(self, "current_graph_index") and self.current_graph_index == 0:
            # Symmetric vertical margins so the square Smith chart is centered
            self.fig.subplots_adjust(
                left=margin,
                right=1 - margin,
                top=1 - margin,
                bottom=margin
            )
            self.ax.set_aspect("equal", adjustable="box")
            self.ax.set_anchor("C")
            self.ax.set_xlim(-1.1, 1.1)
            self.ax.set_ylim(-1.1, 1.1)

        self.canvas.draw_idle()

    def _on_marker_input_changed(self):
        """Update markers for the current graph only, without changing graphs."""
        self._update_markers(self.current_graph_index)
        self.canvas.draw_idle()

    # --- Update marker checkboxes + frequency edits
    def _update_marker_checkboxes(self):
        # Clear all items (widgets, spacers, sub-layouts)
        while self.marker_layout.count():
            self.marker_layout.takeAt(0)

        marker1, marker2 = self.marker_checkboxes[self.current_graph_index]
        edit1, combo1, edit2, combo2 = self.marker_freq_edits[self.current_graph_index]

        # Detach widgets from any previous parent layout
        for w in (marker1, edit1, combo1, marker2, edit2, combo2):
            w.setParent(None)

        # --- Marker 1: title centered, [input][unit] below ---
        vbox1 = QVBoxLayout()
        vbox1.setSpacing(8)
        cb_row1 = QHBoxLayout()
        cb_row1.addStretch()
        cb_row1.addWidget(marker1)
        cb_row1.addStretch()
        vbox1.addLayout(cb_row1)
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(edit1)
        row1.addWidget(combo1)
        vbox1.addLayout(row1)

        # --- Marker 2: title centered, [input][unit] below ---
        vbox2 = QVBoxLayout()
        vbox2.setSpacing(8)
        cb_row2 = QHBoxLayout()
        cb_row2.addStretch()
        cb_row2.addWidget(marker2)
        cb_row2.addStretch()
        vbox2.addLayout(cb_row2)
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(edit2)
        row2.addWidget(combo2)
        vbox2.addLayout(row2)

        self.marker_layout.addLayout(vbox1)
        self.marker_layout.addSpacing(70)
        self.marker_layout.addLayout(vbox2)
        self.canvas.draw_idle()

    # --- Plot graph ---
    def _plot_graph(self, index):
        unit_applies = index in (1, 3)   # only S11/S21 magnitude
        self.rb_db.setVisible(unit_applies)
        self.rb_linear.setVisible(unit_applies)

        self.fig.clear()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("white")
        self.fig.subplots_adjust(left=0.15, right=0.9, top=0.9, bottom=0.18)

        freqs = self.freqs if self.freqs is not None else np.linspace(1e6, 1e8, 100)
        s11 = self.s11_data if self.s11_data is not None else np.exp(1j * np.linspace(0, 2*np.pi, 100))
        s21 = self.s21_data if self.s21_data is not None else 20 * np.log10(np.abs(np.sin(freqs / 1e8 * np.pi)))

        f_min = np.min(freqs)
        f_max = np.max(freqs)

        def freq_unit_and_scale(f_min, f_max):
            def order(f):
                if f < 1e3:
                    return 0      # Hz
                elif f < 1e6:
                    return 1      # kHz
                elif f < 1e9:
                    return 2      # MHz
                else:
                    return 3      # GHz

            o_min = order(f_min)
            o_max = order(f_max)

            units = {
                0: ("Hz", 1),
                1: ("kHz", 1e3),
                2: ("MHz", 1e6),
                3: ("GHz", 1e9),
            }

            if o_min == 1 and o_max == 1:
                target = 1   # kHz
            elif o_min == 1 and o_max == 2:
                target = 2
            elif o_min == 2 and o_max == 3:
                target = 3
            elif o_min == 1 and o_max == 3:
                target = 2
            else:
                target = max(o_min, o_max)

            unit, scale = units[target]
            return unit, scale

        unit, scale = freq_unit_and_scale(f_min, f_max)

        new_freqs = freqs / scale

        if index == 0:
            # Set title for the Smith chart
            self.ax.set_title(rf"{self.pdf_preview_s11_smith_title}", fontsize=14, pad=14)

            # Create a temporary network just for plotting the Smith chart background with labels
            dummy_freq = rf.Frequency(1, 10, 10, unit='GHz')
            dummy_s = np.zeros((10, 1, 1), dtype=complex)
            dummy_ntw = rf.Network(frequency=dummy_freq, s=dummy_s)

            # Plot the Smith chart grid with labels in black, without adding legend entry
            dummy_ntw.plot_s_smith(ax=self.ax, draw_labels=True, color='black', lw=0.5, label=None)

            # Plot actual S11 data on top
            gamma = s11
            line, = self.ax.plot(np.real(gamma), np.imag(gamma), color="red", linewidth=1.2, label=r"$S_{11}$", clip_on=False)

            # Adjust appearance
            self.ax.set_aspect("equal", adjustable="box")
            self.ax.set_xlim(-1.1, 1.1)
            self.ax.set_ylim(-1.1, 1.1)
            self.ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

            # Legend outside the axes, top-left corner above the chart
            legend = self.ax.legend(
                handles=[line],
                loc="lower left",
                bbox_to_anchor=(-0.13, 1.00),
                borderaxespad=0,
                fontsize=10,
                facecolor="white",
                edgecolor="black",
                framealpha=1,
                title=None
            )
            legend.set_draggable(True)

        elif index == 1:
            unit = self._selected_unit()
            y_data, ylabel, title = self._magnitude_curve(s11, r"S_{11}", unit)
            self.ax.plot(new_freqs, y_data, color="red", linewidth=1.3)
            self.ax.set_xlabel(f"{self.pdf_preview_s11_magnitude_x_axis}", fontsize=12)
            self.ax.set_title(title, fontsize=14, pad=14)
            self.ax.set_ylabel(ylabel)
            self.ax.grid(True, linestyle="--", alpha=0.6)
            ylim = self._get_ylim_for_export("S11", "Magnitude")
            if ylim:
                self.ax.set_ylim(*ylim)

        elif index == 2:
            self.ax.plot(new_freqs, np.angle(s11, deg=True), color="red", linewidth=1.3)
            self.ax.set_title(rf"{self.pdf_preview_s11_phase_title}", fontsize=14, pad=14)
            self.ax.set_xlabel(f"{self.pdf_preview_s11_phase_x_axis}", fontsize=12)
            self.ax.set_ylabel(rf"{self.pdf_preview_s11_phase_y_axis}", fontsize=12)
            self.ax.grid(True, linestyle="--", alpha=0.6)
            ylim = self._get_ylim_for_export("S11", "Phase")
            if ylim:
                self.ax.set_ylim(*ylim)

        elif index == 3:
            unit = self._selected_unit()
            y_data, ylabel, title = self._magnitude_curve(s21, r"S_{21}", unit)
            self.ax.plot(new_freqs, y_data, color="blue", linewidth=1.3)
            self.ax.set_title(title, fontsize=14, pad=14)
            self.ax.set_xlabel(f"{self.pdf_preview_s21_magnitude_x_axis}", fontsize=12)
            self.ax.set_ylabel(ylabel)
            self.ax.grid(True, linestyle="--", alpha=0.6)
            ylim = self._get_ylim_for_export("S21", "Magnitude")
            if ylim:
                self.ax.set_ylim(*ylim)
        elif index == 4:
            phase_s21 = np.angle(np.exp(1j * freqs / 1e7), deg=True)
            self.ax.plot(new_freqs, phase_s21, color="blue", linewidth=1.3)
            self.ax.set_title(rf"{self.pdf_preview_s21_phase_title}", fontsize=14, pad=14)
            self.ax.set_xlabel(f"{self.pdf_preview_s21_phase_x_axis}", fontsize=12)
            self.ax.set_ylabel(rf"{self.pdf_preview_s21_phase_y_axis}", fontsize=12)
            ylim = self._get_ylim_for_export("S21", "Phase")
            if ylim:
                self.ax.set_ylim(*ylim)
            self.ax.grid(True, linestyle="--", alpha=0.6)

        self.canvas.draw()
        self._update_markers(index)

    def on_edit_finished(self, edit, combo):
        self.validate_frequency_input(edit, combo, self.freqs)
        self.update_validator(edit, combo)
        self._on_marker_input_changed()

    def update_validator(self, edit, combo):
        unit = combo.currentText()
        edit.textChanged.connect(lambda t: edit.setText(self.block_comma(t)))
        if unit == "kHz":
            validator = QDoubleValidator(50, 999, 2)
            validator.setLocale(QLocale.c())
            edit.setValidator(validator)
        elif unit == "MHz":
            validator = QDoubleValidator(0, 999, 2)
            validator.setLocale(QLocale.c())        
            edit.setValidator(validator)
        elif unit == "GHz":
            validator = QDoubleValidator(0, 1.5, 2)
            validator.setLocale(QLocale.c())
            edit.setValidator(validator)

    def block_comma(text):
        return text.replace(",", ".")

    def validate_frequency_input(self, edit, combo, freqs):
        try:
            val = float(edit.text())
        except ValueError:
            return

        unit = combo.currentText()
        min_freq = freqs[0] / 1e3 if unit == "kHz" else freqs[0] / 1e6 if unit == "MHz" else freqs[0] / 1e9
        max_freq = freqs[-1] / 1e3 if unit == "kHz" else freqs[-1] / 1e6 if unit == "MHz" else freqs[-1] / 1e9

        if unit == "kHz":
            if val < 50:
                val = 50
            val = min(max(val, min_freq), max_freq)
            text = f"{val:.2f}"
        elif unit == "MHz":
            val = min(max(val, min_freq), max_freq)
            text = f"{val:.2f}"
        elif unit == "GHz":
            if val > 1.5:
                val = 1.5
            val = min(max(val, min_freq), max_freq)
            text = f"{val:.2f}"  
        else:
            text = f"{val:.2f}"

        edit.setText(text)

    # --- Navigation ---
    def _show_next_graph(self):
        fig_copy = copy.deepcopy(self.fig)
        if len(self.saved_figures) <= self.current_figure:
            self.saved_figures.append(fig_copy)
        else:
            self.saved_figures[self.current_figure] = fig_copy

        if self.current_graph_index < self.total_graphs - 1:
            self.current_graph_index += 1
            self.current_figure += 1  
            self._plot_graph(self.current_graph_index)
            self._update_nav_buttons()
            self._update_marker_checkboxes()

        self.export_button.setEnabled(self.current_graph_index == self.total_graphs - 1)

    def _show_previous_graph(self):
        fig_copy = copy.deepcopy(self.fig)
        if len(self.saved_figures) <= self.current_figure:
            self.saved_figures.append(fig_copy)
        else:
            self.saved_figures[self.current_figure] = fig_copy

        if self.current_graph_index > 0:
            self.current_graph_index -= 1
            self.current_figure -= 1 
            self._plot_graph(self.current_graph_index)
            self._update_nav_buttons()
            self._update_marker_checkboxes()

        self.export_button.setEnabled(self.current_graph_index == self.total_graphs - 1)

    def _update_nav_buttons(self):
        self.prev_button.setEnabled(self.current_graph_index > 0)
        self.next_button.setEnabled(self.current_graph_index < self.total_graphs - 1)
        self.page_label.setText(f"{self.current_graph_index + 1} / {self.total_graphs}")

    # --- Marker handling ---
    def _update_markers(self, graph_index=None):
        if graph_index is None:
            graph_index = self.current_graph_index

        ax = self.ax
        freqs = self.freqs if self.freqs is not None else np.linspace(1e6, 1e8, 100)
        s11 = self.s11_data if self.s11_data is not None else np.exp(1j * np.linspace(0, 2*np.pi, 100))
        s21 = self.s21_data if self.s21_data is not None else 20 * np.log10(np.abs(np.sin(freqs / 1e8 * np.pi)))

        # --- MISMA ESCALA QUE EL EJE ---
        f_min = np.min(freqs)
        f_max = np.max(freqs)

        def freq_unit_and_scale(f_min, f_max):
            def order(f):
                if f < 1e3: return 0
                elif f < 1e6: return 1
                elif f < 1e9: return 2
                else: return 3

            o_min = order(f_min)
            o_max = order(f_max)

            units = {
                0: ("Hz", 1),
                1: ("kHz", 1e3),
                2: ("MHz", 1e6),
                3: ("GHz", 1e9),
            }

            target = max(o_min, o_max)
            unit, scale = units[target]
            return unit, scale

        unit_x, scale_x = freq_unit_and_scale(f_min, f_max)
        scaled_freqs = freqs / scale_x

        marker1, marker2 = self.marker_checkboxes[graph_index]
        self.marker_active[graph_index] = [marker1.isChecked(), marker2.isChecked()]

        for obj in getattr(self, "ann_objects", []):
            try: obj['text'].remove()
            except Exception: pass
            try: obj['patch'].remove()
            except Exception: pass
        for mk in getattr(self, "markers", []):
            mk.set_visible(False)

        self.ann_objects = []
        self.annotations = []   # kept empty for compatibility
        self.markers = []

        try:
            _gfx = get_settings(
                "INI/dut_measurement/graphics_config/graphics_config.ini",
                "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
                Path(__file__).resolve()
            )
            colors = [
                _gfx.value("Graphic1/MarkerColor1", "#00ff00"),
                _gfx.value("Graphic2/MarkerColor1", "#ffaa00"),
            ]
        except Exception:
            colors = ["#00ff00", "#ffaa00"]
        edits = self.marker_freq_edits[graph_index]

        for i, active in enumerate(self.marker_active[graph_index]):
            edit, combo = (edits[0], edits[1]) if i == 0 else (edits[2], edits[3])

            if active:
                edit.setEnabled(True)
                combo.setEnabled(True)
                edit.setStyleSheet("background-color: white; color: black; border: 2px solid white; border-radius: 3px;")
                combo.update()

                try:
                    freq_val = float(edit.text())
                    unit_factor = {"kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[combo.currentText()]
                    freq_val_hz = freq_val * unit_factor
                except Exception:
                    freq_val_hz = freqs[len(freqs)//3 if i == 0 else 2*len(freqs)//3]
                    freq_val = freq_val_hz / 1e3

                idx = (np.abs(freqs - freq_val_hz)).argmin()
                nearest_freq_hz = freqs[idx]

                # Actualizar input con el valor real más cercano
                nearest_val = nearest_freq_hz / unit_factor
                edit.setText(f"{nearest_val:.2f}")

                # --- USAR X ESCALADO ---
                if graph_index == 0:
                    x = np.real(s11[idx])
                    y = np.imag(s11[idx])
                elif graph_index == 1:
                    x = scaled_freqs[idx]
                    y = 20*np.log10(np.abs(s11[idx]))
                elif graph_index == 2:
                    x = scaled_freqs[idx]
                    y = np.angle(s11[idx], deg=True)
                elif graph_index == 3:
                    x = scaled_freqs[idx]
                    y = 20*np.log10(np.abs(s21[idx]))
                elif graph_index == 4:
                    phase_s21 = np.angle(np.exp(1j * freqs / 1e7), deg=True)
                    x = scaled_freqs[idx]
                    y = phase_s21[idx]

                mk_line, = ax.plot(x, y, marker='o', color=colors[i], markersize=8)

                if combo.currentText() == "MHz" and freq_val >= 1000:
                    freq_val /= 1000
                    unit_display = "GHz"
                else:
                    unit_display = combo.currentText()

                freq_display = f"{freq_val:.2f} {unit_display}"

                if graph_index == 0:
                    text = (
                        f"Marker {i+1}\n"
                        f"Freq: {nearest_val:.2f} {combo.currentText()}\n"
                        f"Re: {np.real(s11[idx]):.3f}   Im: {np.imag(s11[idx]):.3f}"
                    )
                elif graph_index in [1, 3]:
                    text = (
                        f"Marker {i+1}\n"
                        f"Freq: {nearest_val:.2f} {combo.currentText()}\n"
                        f"|S|: {y:.3f} dB"
                    )
                else:
                    text = (
                        f"Marker {i+1}\n"
                        f"Freq: {nearest_val:.2f} {combo.currentText()}\n"
                        f"Phase: {y:.3f}°"
                    )

                # Center of annotation box in data coords
                ann_x, ann_y = self.marker_positions[graph_index][i] if self.marker_positions[graph_index][i] else (x, y)

                # Text — no bbox, centered at annotation position
                txt = ax.text(ann_x, ann_y, text,
                              ha='center', va='center',
                              color=colors[i], fontsize=9,
                              linespacing=2.0,
                              zorder=10, clip_on=False)

                # Measure text bbox in pixels to size the background patch
                renderer = self.canvas.get_renderer()
                tbbox = txt.get_window_extent(renderer=renderer)
                PAD = 6
                L_px = tbbox.x0 - PAD
                B_px = tbbox.y0 - PAD
                R_px = tbbox.x1 + PAD
                T_px = tbbox.y1 + PAD

                try:
                    d_lb = ax.transData.inverted().transform((L_px, B_px))
                    d_rt = ax.transData.inverted().transform((R_px, T_px))
                except Exception:
                    d_lb = (ann_x - 0.15, ann_y - 0.08)
                    d_rt = (ann_x + 0.15, ann_y + 0.08)

                patch = FancyBboxPatch(
                    (d_lb[0], d_lb[1]),
                    max(1e-9, d_rt[0] - d_lb[0]),
                    max(1e-9, d_rt[1] - d_lb[1]),
                    boxstyle='square,pad=0',
                    facecolor='white', edgecolor=colors[i],
                    alpha=0.85, transform=ax.transData,
                    zorder=9, clip_on=False
                )
                ax.add_patch(patch)

                self.markers.append(mk_line)
                self.ann_objects.append({'text': txt, 'patch': patch, 'idx': i})
                self.marker_positions[graph_index][i] = (ann_x, ann_y)

            else:
                edit.setEnabled(False)
                combo.setEnabled(False)
                edit.setStyleSheet("background-color: #d8d8d8; color: #888888; border: 1px solid #aaaaaa; border-radius: 3px;")
                combo.update()

                unit_factor = {"kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[combo.currentText()]
                default_val = freqs[0] / unit_factor
                edit.setText(f"{default_val:.2f}")

        self._enable_drag_annotations()
        self.canvas.draw()

    # --- Draggable markers ---
    def _enable_drag_annotations(self):
        for cid in getattr(self, "_drag_cids", []):
            try: self.canvas.mpl_disconnect(cid)
            except Exception: pass

        drag_state = {
            "obj": None, "mode": None, "press_px": None,
            "edge": None, "bbox0_px": None,
            "fontsize0": None, "text_w0": None, "text_h0": None,
            "patch_xy0": None, "txt_pos0": None,
        }

        EDGE_TOL = 10
        MIN_W_PX, MIN_H_PX = 50, 35

        def _patch_px(patch):
            """Patch bounds in canvas pixels: (L, B, R, T)."""
            t = patch.get_transform()
            x, y = patch.get_x(), patch.get_y()
            w, h = patch.get_width(), patch.get_height()
            lb = t.transform((x, y))
            rt = t.transform((x + w, y + h))
            return lb[0], lb[1], rt[0], rt[1]

        def _px_to_data(px, py):
            return tuple(self.ax.transData.inverted().transform((px, py)))

        def _detect_edge(L, B, R, T, mx, my):
            on_l = abs(mx - L) < EDGE_TOL
            on_r = abs(mx - R) < EDGE_TOL
            on_b = abs(my - B) < EDGE_TOL
            on_t = abs(my - T) < EDGE_TOL
            in_x = L + EDGE_TOL < mx < R - EDGE_TOL
            in_y = B + EDGE_TOL < my < T - EDGE_TOL
            if on_r and on_t: return "top_right"
            if on_l and on_t: return "top_left"
            if on_r and on_b: return "bot_right"
            if on_l and on_b: return "bot_left"
            if on_r and in_y: return "right"
            if on_l and in_y: return "left"
            if on_t and in_x: return "top"
            if on_b and in_x: return "bottom"
            return None

        def _edge_cursor(edge):
            if edge in ("left", "right"):          return Qt.SizeHorCursor
            if edge in ("top", "bottom"):          return Qt.SizeVerCursor
            if edge in ("top_right", "bot_left"):  return Qt.SizeBDiagCursor
            if edge in ("top_left",  "bot_right"): return Qt.SizeFDiagCursor
            return Qt.ArrowCursor

        def _inside(L, B, R, T, mx, my):
            return L + EDGE_TOL < mx < R - EDGE_TOL and B + EDGE_TOL < my < T - EDGE_TOL

        def on_move_hover(event):
            if drag_state["obj"] is not None:
                return
            for obj in self.ann_objects:
                L, B, R, T = _patch_px(obj['patch'])
                edge = _detect_edge(L, B, R, T, event.x, event.y)
                if edge:
                    self.canvas.setCursor(_edge_cursor(edge))
                    return
                if _inside(L, B, R, T, event.x, event.y):
                    self.canvas.setCursor(Qt.OpenHandCursor)
                    return
            self.canvas.setCursor(Qt.ArrowCursor)

        def on_press(event):
            for obj in self.ann_objects:
                patch = obj['patch']
                txt   = obj['text']
                L, B, R, T = _patch_px(patch)
                edge = _detect_edge(L, B, R, T, event.x, event.y)
                if edge:
                    renderer = self.canvas.get_renderer()
                    tbbox = txt.get_window_extent(renderer=renderer)
                    drag_state.update({
                        "obj": obj, "mode": "resize",
                        "press_px": (event.x, event.y),
                        "edge": edge,
                        "bbox0_px": (L, B, R, T),
                        "fontsize0": txt.get_fontsize(),
                        "text_w0": max(1.0, tbbox.width),
                        "text_h0": max(1.0, tbbox.height),
                    })
                    self.canvas.setCursor(_edge_cursor(edge))
                    return
                if _inside(L, B, R, T, event.x, event.y):
                    drag_state.update({
                        "obj": obj, "mode": "move",
                        "press_px": (event.x, event.y),
                        "patch_xy0": (patch.get_x(), patch.get_y()),
                        "txt_pos0": txt.get_position(),
                    })
                    self.canvas.setCursor(Qt.ClosedHandCursor)
                    return

        def on_motion(event):
            if drag_state["obj"] is None:
                return
            obj   = drag_state["obj"]
            patch = obj['patch']
            txt   = obj['text']
            press_px, press_py = drag_state["press_px"]
            dx = event.x - press_px   # right = +
            dy = event.y - press_py   # up    = +

            if drag_state["mode"] == "move":
                try:
                    d0 = _px_to_data(press_px, press_py)
                    d1 = _px_to_data(event.x, event.y)
                    ddx, ddy = d1[0] - d0[0], d1[1] - d0[1]
                    px0, py0 = drag_state["patch_xy0"]
                    tx0, ty0 = drag_state["txt_pos0"]
                    patch.set_x(px0 + ddx)
                    patch.set_y(py0 + ddy)
                    txt.set_position((tx0 + ddx, ty0 + ddy))
                    # Save new center
                    cx_d = tx0 + ddx
                    cy_d = ty0 + ddy
                    self.marker_positions[self.current_graph_index][obj['idx']] = (cx_d, cy_d)
                except Exception:
                    pass

            elif drag_state["mode"] == "resize":
                L0, B0, R0, T0 = drag_state["bbox0_px"]
                edge = drag_state["edge"]

                # Each edge: only the grabbed side moves, all others stay fixed
                if   edge == "right":     nL,nB,nR,nT = L0,   B0,   R0+dx, T0
                elif edge == "left":      nL,nB,nR,nT = L0+dx,B0,   R0,   T0
                elif edge == "top":       nL,nB,nR,nT = L0,   B0,   R0,   T0+dy
                elif edge == "bottom":    nL,nB,nR,nT = L0,   B0+dy,R0,   T0
                elif edge == "top_right": nL,nB,nR,nT = L0,   B0,   R0+dx,T0+dy
                elif edge == "top_left":  nL,nB,nR,nT = L0+dx,B0,   R0,   T0+dy
                elif edge == "bot_right": nL,nB,nR,nT = L0,   B0+dy,R0+dx,T0
                elif edge == "bot_left":  nL,nB,nR,nT = L0+dx,B0+dy,R0,   T0
                else: return

                # Enforce minimum size
                if nR - nL < MIN_W_PX:
                    if 'left' in edge: nL = nR - MIN_W_PX
                    else:              nR = nL + MIN_W_PX
                if nT - nB < MIN_H_PX:
                    if 'bot' in edge or edge == 'bottom': nB = nT - MIN_H_PX
                    else:                                  nT = nB + MIN_H_PX

                try:
                    d_lb = _px_to_data(nL, nB)
                    d_rt = _px_to_data(nR, nT)
                    patch.set_x(d_lb[0])
                    patch.set_y(d_lb[1])
                    patch.set_width(max(1e-9,  d_rt[0] - d_lb[0]))
                    patch.set_height(max(1e-9, d_rt[1] - d_lb[1]))
                    # Center text in new box
                    txt.set_position(((d_lb[0]+d_rt[0])/2, (d_lb[1]+d_rt[1])/2))
                    # Scale font so text fits in both dimensions of the new box
                    PAD_PX = 8
                    tw0 = drag_state["text_w0"]
                    th0 = drag_state["text_h0"]
                    avail_w = max(1.0, (nR - nL) - 2 * PAD_PX)
                    avail_h = max(1.0, (nT - nB) - 2 * PAD_PX)
                    fs_w = drag_state["fontsize0"] * (avail_w / tw0)
                    fs_h = drag_state["fontsize0"] * (avail_h / th0)
                    txt.set_fontsize(max(4, min(fs_w, fs_h)))
                except Exception:
                    pass

            self.canvas.draw_idle()

        def on_release(event):
            if drag_state["obj"] is not None:
                obj = drag_state["obj"]
                try:
                    L, B, R, T = _patch_px(obj['patch'])
                    cx_d, cy_d = _px_to_data((L+R)/2, (B+T)/2)
                    self.marker_positions[self.current_graph_index][obj['idx']] = (cx_d, cy_d)
                except Exception:
                    pass
            drag_state.update({
                "obj": None, "mode": None, "press_px": None,
                "edge": None, "bbox0_px": None,
                "fontsize0": None, "text_w0": None, "text_h0": None,
                "patch_xy0": None, "txt_pos0": None,
            })
            self.canvas.setCursor(Qt.ArrowCursor)

        self._drag_cids = [
            self.canvas.mpl_connect('motion_notify_event', on_move_hover),
            self.canvas.mpl_connect('button_press_event', on_press),
            self.canvas.mpl_connect('motion_notify_event', on_motion),
            self.canvas.mpl_connect('button_release_event', on_release),
        ]

    def _save_current_graph(self):
        if not hasattr(self, "saved_figures"):
            self.saved_figures = []
        fig_copy = copy.deepcopy(self.fig)
        self.saved_figures.append(fig_copy)

    # --- PDF Export ---
    def _generate_pdf(self):
        try:
            self._save_current_graph()

            from NanoVNA_UTN_Toolkit.modules.dut_measurement.exporters.latex_exporter import LatexExporter
            exporter = LatexExporter(figures=self.saved_figures)
            if not self.output_path:
                QMessageBox.warning(self, "Missing Path", "No output path specified.")
                return
            success = exporter.export_to_pdf(
                freqs=self.freqs,
                s11_data=self.s11_data,
                s21_data=self.s21_data,
                measurement_name=self.measurement_name,
                output_path=self.output_path,
                magnitude_unit=self._selected_unit()
            )
            if success:
                QMessageBox.information(self, "Export Complete",
                                        f"PDF successfully created at:\n{self.output_path}")
                self.accept()
            else:
                QMessageBox.warning(self, "Export Failed",
                                    "PDF export failed. Please check the logs for details.")
        except Exception as e:
            logger.exception("PDF export failed")
            QMessageBox.critical(self, "Export Failed",
                                 f"Error creating PDF:\n{str(e)}")

    def _get_ylim_for_export(self, s_param, graph_type):
        """Return (ymin, ymax) if a fixed Y range is configured for this graph, else None."""
        try:
            gfx = get_settings(
                "INI/dut_measurement/graphics_config/graphics_config.ini",
                "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini",
                Path(__file__).resolve()
            )
            as_ = get_settings(
                "INI/dut_measurement/auto_scale/auto_scale.ini",
                "modules/dut_measurement/ui/utils/context_menu/auto_scale/auto_scale.ini",
                Path(__file__).resolve()
            )
            tab1_sp = gfx.value("Tab1/SParameter", "S11")
            tab1_gt = gfx.value("Tab1/GraphType1", "Magnitude")
            tab2_sp = gfx.value("Tab2/SParameter", "S21")
            tab2_gt = gfx.value("Tab2/GraphType2", "Phase")

            if tab1_sp == s_param and tab1_gt == graph_type:
                if not as_.value("AutoScale/enabled_left", True, type=bool):
                    return (as_.value("AutoScale/ymin_left", 0.0, type=float),
                            as_.value("AutoScale/ymax_left", 0.0, type=float))
            if tab2_sp == s_param and tab2_gt == graph_type:
                if not as_.value("AutoScale/enabled_right", True, type=bool):
                    return (as_.value("AutoScale/ymin_right", 0.0, type=float),
                            as_.value("AutoScale/ymax_right", 0.0, type=float))
        except Exception:
            pass
        return None

    def _selected_unit(self):
        return "dB" if self.rb_db.isChecked() else "times"

    def _on_unit_changed(self):
        self._plot_graph(self.current_graph_index)
        self._update_markers(self.current_graph_index)
        self.canvas.draw_idle()

    def _magnitude_curve(self, s_data, param_tex, unit):
        if unit == "dB":
            y = 20 * np.log10(np.abs(s_data))
            ylabel = rf"$|{param_tex}|\ \mathrm{{(dB)}}$"
            title  = rf"Magnitude $|{param_tex}|$ (dB)"
        elif unit == "Power ratio":
            y = np.abs(s_data) ** 2
            ylabel = rf"$|{param_tex}|^2$"
            title  = rf"Power Ratio $|{param_tex}|^2$"
        else:
            y = np.abs(s_data)
            ylabel = rf"$|{param_tex}|$"
            title  = rf"Magnitude $|{param_tex}|$"
        return y, ylabel, title


class NoEnterButton(QPushButton):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Ignora solo si el botón tiene foco
            if self.hasFocus():
                event.ignore()  # dejar que el QLineEdit reciba Enter si tiene foco
        else:
            super().keyPressEvent(event)
