"""
Graph Preview Export Dialog for NanoVNA Measurements
Provides an interactive preview of S-parameter graphs with navigation
and PDF export functionality using Matplotlib and PySide6.

Each graph has independent Marker 1 and Marker 2 checkboxes.
Markers can be dragged independently for each graph.
Deactivating a marker hides its cursor immediately.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QWidget,
    QCheckBox, QHBoxLayout, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, QLocale
from PySide6.QtGui import QDoubleValidator
from PySide6.QtGui import QGuiApplication

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np
import skrf as rf
import logging
import copy

plt.rcParams['mathtext.fontset'] = 'cm'  
plt.rcParams['text.usetex'] = False       
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'    
plt.rcParams['mathtext.rm'] = 'serif' 

logger = logging.getLogger(__name__)

class GraphPreviewExportDialog(QDialog):
    def __init__(self, parent=None, freqs=None, s11_data=None, s21_data=None,
             measurement_name=None, output_path=None):
        super().__init__(parent)
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

        # Ajustar solo la altura, no el ancho
        self.resize(800, int(screen_height * 0.7))
        self.setMaximumSize(screen_width, screen_height)

        main_layout = QVBoxLayout(self)

        # --- Instruction label
        label = QLabel(
            "Graph preview is ready.\n"
            "Use the arrows below to explore all measurement views before exporting the PDF."
        )
        label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(label)

        # --- Create figure and canvas ---
        self.fig, self.ax = plt.subplots()
        self.fig.patch.set_facecolor("white")
        self.ax.set_facecolor("white")
        self.fig.subplots_adjust(left=0.15, right=0.95, top=0.9, bottom=0.18)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.resizeEvent = self._on_canvas_resize

        # --- Previous / Next buttons ---
        self.prev_button = NoEnterButton("← Previous")
        self.next_button = NoEnterButton("Next →")

        self.prev_button.setFocusPolicy(Qt.NoFocus)
        self.next_button.setFocusPolicy(Qt.NoFocus)
        btn_style = """
            QPushButton {
                background-color: rgba(245, 245, 245, 0.9);
                border: 1px solid #777;
                border-radius: 5px;
                font-weight: bold;
                color: #333;
                min-width: 70px;
                max-width: 70px;
                min-height: 20px;
                max-height: 20px;   
                padding: 2px 4px;
            }
            QPushButton:hover {
                background-color: rgba(220, 220, 220, 0.95);
            }
        """
        self.prev_button.setStyleSheet(btn_style)
        self.next_button.setStyleSheet(btn_style)

        # --- Marker checkboxes and frequency inputs
        self.marker_checkboxes = {}  # key=graph_index, value=(marker1, marker2)
        self.marker_freq_edits = {}  # key=graph_index, value=(edit1, combo1, edit2, combo2)

        for i in range(5):

            # --- Marker checkboxes ---
            marker1 = QCheckBox("Marker 1")
            marker1.setStyleSheet("color: green; font-weight: bold; font-size: 12pt;")
            marker2 = QCheckBox("Marker 2")
            marker2.setStyleSheet("color: orange; font-weight: bold; font-size: 12pt;")
            marker1.stateChanged.connect(lambda _, idx=i: self._update_markers(idx))
            marker2.stateChanged.connect(lambda _, idx=i: self._update_markers(idx))
            self.marker_checkboxes[i] = (marker1, marker2)

            # --- Frequency inputs (white style) ---
            edit1 = QLineEdit()
            edit1.setFixedWidth(80)
            edit1.setStyleSheet("background-color: white; color: black;")
            combo1 = QComboBox()
            combo1.addItems(["kHz", "MHz", "GHz"])
            combo1.setCurrentText("kHz")
            combo1.setStyleSheet("background-color: white; color: black;")

            edit2 = QLineEdit()
            edit2.setFixedWidth(80)
            edit2.setStyleSheet("background-color: white; color: black;")
            combo2 = QComboBox()
            combo2.addItems(["kHz", "MHz", "GHz"])
            combo2.setCurrentText("kHz")
            combo2.setStyleSheet("background-color: white; color: black;")

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
        self.marker_layout.setSpacing(20)
        self.marker_layout.addStretch()

        marker_container = QWidget()
        marker_container_layout = QHBoxLayout(marker_container)
        marker_container_layout.setContentsMargins(0, 0, 0, 0)
        marker_container_layout.addStretch()
        marker_container_layout.addLayout(self.marker_layout)
        marker_container_layout.addStretch()

        # --- Canvas container with navigation buttons inside ---
        self.canvas_container = QWidget()
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)

        # Add the Matplotlib canvas
        canvas_layout.addWidget(self.canvas)

        # --- Create an overlay widget on top of canvas for buttons ---
        self.overlay_widget = QWidget(self.canvas)
        self.overlay_widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.overlay_widget.setStyleSheet("background: transparent;")
        self.overlay_widget.setGeometry(0, 0, self.canvas.width(), 40)

        # Layout for navigation buttons inside overlay
        overlay_layout = QHBoxLayout(self.overlay_widget)
        overlay_layout.setContentsMargins(10, 5, 10, 5)
        overlay_layout.addWidget(self.prev_button, alignment=Qt.AlignLeft)
        overlay_layout.addStretch()
        overlay_layout.addWidget(self.next_button, alignment=Qt.AlignRight)

        main_layout.addWidget(self.canvas_container, alignment=Qt.AlignCenter)

        # --- Add a small vertical spacing between canvas and markers ---
        main_layout.addSpacing(10)  # small gap

        # --- Marker container centered below canvas ---
        main_layout.addWidget(marker_container, alignment=Qt.AlignCenter)

        main_layout.addSpacing(15)

        # --- Export button ---
        self.export_button = QPushButton("Generate PDF Report")
        self.export_button.setEnabled(False)
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.export_button.clicked.connect(self._generate_pdf)
        main_layout.addWidget(self.export_button, alignment=Qt.AlignCenter)
        main_layout.addStretch()

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
            top=1 - margin,
            bottom=margin
        )

        # Ajustar escala del texto (se vuelve muy grande en pantallas chicas)
        scale = (w / 800)
        scale = max(0.6, min(1.0, scale))   # clamp entre 0.6 y 1.0

        self.ax.title.set_fontsize(12 * scale)
        self.ax.xaxis.label.set_fontsize(11 * scale)
        self.ax.yaxis.label.set_fontsize(11 * scale)
        for tick in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            tick.set_fontsize(9 * scale)

        if hasattr(self, "current_graph_index") and self.current_graph_index == 0:
            self.ax.set_aspect("equal", adjustable="box")
            self.ax.set_xlim(-1.1, 1.1)
            self.ax.set_ylim(-1.1, 1.1)

        # Reposicionar overlay de botones
        overlay_height = int(40 * scale)
        self.overlay_widget.setGeometry(
            0,
            self.canvas.height() - overlay_height - 5,
            self.canvas.width(),
            overlay_height
        )

        self.canvas.draw_idle()

    def _on_marker_input_changed(self):
        """Update markers for the current graph only, without changing graphs."""
        self._update_markers(self.current_graph_index)
        self.canvas.draw_idle()

    # --- Update marker checkboxes + frequency edits
    def _update_marker_checkboxes(self):
        for i in reversed(range(self.marker_layout.count())):
            item = self.marker_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                else:
                    layout_item = item.layout()
                    if layout_item:
                        while layout_item.count():
                            child = layout_item.takeAt(0)
                            if child.widget():
                                child.widget().setParent(None)

        self.marker_layout.addStretch()
        marker1, marker2 = self.marker_checkboxes[self.current_graph_index]
        edit1, combo1, edit2, combo2 = self.marker_freq_edits[self.current_graph_index]

        # --- Marker 1 layout
        vbox1 = QVBoxLayout()
        vbox1.addWidget(marker1, alignment=Qt.AlignCenter)
        vbox1.addWidget(edit1, alignment=Qt.AlignCenter)
        vbox1.addWidget(combo1, alignment=Qt.AlignCenter)

        # --- Marker 2 layout
        vbox2 = QVBoxLayout()
        vbox2.addWidget(marker2, alignment=Qt.AlignCenter)
        vbox2.addWidget(edit2, alignment=Qt.AlignCenter)
        vbox2.addWidget(combo2, alignment=Qt.AlignCenter)

        self.marker_layout.addLayout(vbox1)
        self.marker_layout.addLayout(vbox2)
        self.marker_layout.addStretch()
        self.canvas.draw_idle()

    # --- Plot graph ---
    def _plot_graph(self, index):
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
            self.fig.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1)

            # Set title for the Smith chart
            self.ax.set_title(r"Smith Diagram - $S_{11}$", fontsize=12, pad=20)
            
            # Create a temporary network just for plotting the Smith chart background with labels
            dummy_freq = rf.Frequency(1, 10, 10, unit='GHz')
            dummy_s = np.zeros((10, 1, 1), dtype=complex)
            dummy_ntw = rf.Network(frequency=dummy_freq, s=dummy_s)
            
            # Plot the Smith chart grid with labels in black, without adding legend entry
            dummy_ntw.plot_s_smith(ax=self.ax, draw_labels=True, color='black', lw=0.5, label=None)
            
            # Plot actual S11 data on top
            gamma = s11
            line, = self.ax.plot(np.real(gamma), np.imag(gamma), color="red", linewidth=1.2, label="S11")
            
            # Adjust appearance
            self.ax.set_aspect("equal", adjustable="box")
            self.ax.set_xlim(-1.1, 1.1)
            self.ax.set_ylim(-1.1, 1.1)
            self.ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

            # Custom legend showing only the S11 trace
            legend = self.ax.legend(
                handles=[line],
                loc="upper left",
                fontsize=9,
                facecolor="white",
                edgecolor="black",
                framealpha=1,
                title=None
            )
            legend.set_draggable(True)

        elif index == 1:
            self.ax.plot(new_freqs, 20 * np.log10(np.abs(s11)), color="red", linewidth=1.3)
            self.ax.set_xlabel(f"Frequency ({unit})", fontsize=12)
            self.ax.set_title(r"Magnitude $|S_{11}|$ (dB)", fontsize=12, pad=12)
            self.ax.set_ylabel(r"$|S_{11}|$ (dB)")
            self.ax.grid(True, linestyle="--", alpha=0.6)

        elif index == 2:
            self.ax.plot(new_freqs, np.angle(s11, deg=True), color="red", linewidth=1.3)
            self.ax.set_title(r"Phase $S_{11}$ (°)", fontsize=12, pad=12)
            self.ax.set_xlabel(f"Frequency ({unit})", fontsize=12)
            self.ax.set_ylabel(r"$ \phi_{S_{11}} $ (°)", fontsize=12)
            self.ax.grid(True, linestyle="--", alpha=0.6)
        elif index == 3:
            self.ax.plot(new_freqs, 20*np.log10(np.abs(s21)), color="blue", linewidth=1.3)
            self.ax.set_title(r"Magnitude $|S_{21}|$ (dB)", fontsize=12, pad=12)
            self.ax.set_xlabel(f"Frequency ({unit})", fontsize=12)
            self.ax.set_ylabel(r"$|S_{21}|$ (dB)")
            self.ax.grid(True, linestyle="--", alpha=0.6)
        elif index == 4:
            phase_s21 = np.angle(np.exp(1j * freqs / 1e7), deg=True)
            self.ax.plot(new_freqs, phase_s21, color="blue", linewidth=1.3)
            self.ax.set_title(r"Phase $S_{21}$ (°)", fontsize=12, pad=12)
            self.ax.set_xlabel(f"Frequency ({unit})", fontsize=12)
            self.ax.set_ylabel(r"$ \phi_{S_{21}} $ (°)", fontsize=12)
            self.ax.grid(True, linestyle="--", alpha=0.6)

        self.canvas.draw()
        self._update_markers(index)

    def on_edit_finished(self, edit, combo):
        self.validate_frequency_input(edit, combo, self.freqs)
        self.update_validator(edit, combo)
        self._on_marker_input_changed()

    def update_validator(self, edit, combo):
        unit = combo.currentText()
        edit.textChanged.connect(lambda t: edit.setText(block_comma(t)))
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
        self.prev_button.setVisible(self.current_graph_index > 0)
        self.next_button.setVisible(self.current_graph_index < 4)

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

        for ann in getattr(self, "annotations", []):
            ann.set_visible(False)
        for mk in getattr(self, "markers", []):
            mk.set_visible(False)

        self.annotations = []
        self.markers = []

        colors = ["green", "orange"]
        edits = self.marker_freq_edits[graph_index]

        for i, active in enumerate(self.marker_active[graph_index]):
            edit, combo = (edits[0], edits[1]) if i == 0 else (edits[2], edits[3])

            if active:
                edit.setEnabled(True)
                combo.setEnabled(True)
                edit.setStyleSheet("background-color: white; color: black;")

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
                        f"Re: {np.real(s11[idx]):.3f}\n"
                        f"Im: {np.imag(s11[idx]):.3f}"
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

                ann_x, ann_y = self.marker_positions[graph_index][i] if self.marker_positions[graph_index][i] else (x, y)

                ann = ax.annotate(
                    text,
                    xy=(x, y),
                    xycoords='data',
                    xytext=(ann_x, ann_y),
                    bbox=dict(facecolor='white', edgecolor=colors[i], alpha=0.7),
                    color=colors[i]
                )

                self.markers.append(mk_line)
                self.annotations.append(ann)
                prev_pos = self.marker_positions[graph_index][i]
                self.marker_positions[graph_index][i] = prev_pos if prev_pos is not None else (x, y)

            else:
                edit.setEnabled(False)
                combo.setEnabled(False)
                edit.setStyleSheet("background-color: lightgray; color: darkgray;")

                unit_factor = {"kHz": 1e3, "MHz": 1e6, "GHz": 1e9}[combo.currentText()]
                default_val = freqs[0] / unit_factor
                edit.setText(f"{default_val:.2f}")

        self._enable_drag_annotations()
        self.canvas.draw()

    # --- Draggable markers ---
    def _enable_drag_annotations(self):
        drag_state = {"dragging": None, "mode": None, "corner": None}

        def detect_corner(bbox, x, y, tol=8):
            if abs(x - bbox.x1) < tol and abs(y - bbox.y1) < tol:
                return "top_right"
            return None

        def on_move_hover(event):
            if event.inaxes != self.ax:
                self.canvas.setCursor(Qt.ArrowCursor)
                return
            renderer = self.canvas.get_renderer()
            for ann in self.annotations:
                bbox = ann.get_window_extent(renderer=renderer)
                if detect_corner(bbox, event.x, event.y):
                    self.canvas.setCursor(Qt.SizeBDiagCursor)
                    return
                if bbox.contains(event.x, event.y):
                    self.canvas.setCursor(Qt.OpenHandCursor)
                    return
            self.canvas.setCursor(Qt.ArrowCursor)

        def on_press(event):
            if event.inaxes != self.ax:
                return
            renderer = self.canvas.get_renderer()
            for ann in self.annotations:
                bbox = ann.get_window_extent(renderer=renderer)
                corner = detect_corner(bbox, event.x, event.y)
                if corner:
                    drag_state.update({
                        "dragging": ann,
                        "mode": "resize",
                        "corner": corner,
                        "fontsize0": ann.get_fontsize()
                    })
                    return
                if bbox.contains(event.x, event.y):
                    idx = self.annotations.index(ann)
                    drag_state.update({
                        "dragging": ann,
                        "mode": "move",
                        "corner": None,
                        "x0": ann.xy[0],
                        "y0": ann.xy[1],
                        "press_xdata": event.xdata,
                        "press_ydata": event.ydata,
                        "idx": idx
                    })
                    return

        def on_motion(event):
            if drag_state["dragging"] is None or event.xdata is None or event.ydata is None:
                return
            ann = drag_state["dragging"]
            if drag_state["mode"] == "move":
                dx = event.xdata - drag_state["press_xdata"]
                dy = event.ydata - drag_state["press_ydata"]
                new_pos = (drag_state["x0"] + dx, drag_state["y0"] + dy)
                ann.set_position(new_pos)
                idx = drag_state["idx"]
                self.marker_positions[self.current_graph_index][idx] = new_pos
            elif drag_state["mode"] == "resize" and drag_state["corner"] == "top_right":
                renderer = self.canvas.get_renderer()
                bbox = ann.get_window_extent(renderer=renderer)
                delta = event.x - bbox.x1 + bbox.y1 - event.y
                new_size = max(6, drag_state["fontsize0"] + delta * 0.05)
                ann.set_fontsize(new_size)
            self.canvas.draw_idle()

        def on_release(event):
            drag_state["dragging"] = None
            drag_state["mode"] = None
            drag_state["corner"] = None
            drag_state.pop("idx", None)

        self.canvas.mpl_connect('motion_notify_event', on_move_hover)
        self.canvas.mpl_connect('button_press_event', on_press)
        self.canvas.mpl_connect('motion_notify_event', on_motion)
        self.canvas.mpl_connect('button_release_event', on_release)

    def _save_current_graph(self):
        if not hasattr(self, "saved_figures"):
            self.saved_figures = []
        fig_copy = copy.deepcopy(self.fig)
        self.saved_figures.append(fig_copy)

    # --- PDF Export ---
    def _generate_pdf(self):
        try:
            self._save_current_graph()

            from NanoVNA_UTN_Toolkit.exporters.latex_exporter import LatexExporter
            exporter = LatexExporter(figures=self.saved_figures)
            if not self.output_path:
                QMessageBox.warning(self, "Missing Path", "No output path specified.")
                return
            success = exporter.export_to_pdf(
                freqs=self.freqs,
                s11_data=self.s11_data,
                s21_data=self.s21_data,
                measurement_name=self.measurement_name,
                output_path=self.output_path
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

class NoEnterButton(QPushButton):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Ignora solo si el botón tiene foco
            if self.hasFocus():
                event.ignore()  # dejar que el QLineEdit reciba Enter si tiene foco
        else:
            super().keyPressEvent(event)
