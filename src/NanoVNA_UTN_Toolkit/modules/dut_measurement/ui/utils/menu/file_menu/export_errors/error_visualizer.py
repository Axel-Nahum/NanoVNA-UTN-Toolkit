import os
import re
import logging
import numpy as np
import skrf as rf

from pathlib import Path
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import rcParams

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QWidget, QFileDialog, QMessageBox, QSizePolicy
)
from PySide6.QtGui import QFont, QIcon

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Human-readable names for each error term file
_ERROR_LABELS = {
    "directivity":           "Directivity (EDF)",
    "source_match":          "Source Match (ESF)",
    "reflection_tracking":   "Reflection Tracking (ERF)",
    "transmission_tracking": "Transmission Tracking (ETF)",
    "load_match":            "Load Match (ELF)",
}

# Order in which terms are shown per method
_METHOD_TERMS = {
    "OSM (Open - Short - Match)": [
        "directivity", "source_match", "reflection_tracking"
    ],
    "Normalization": [
        "transmission_tracking"
    ],
    "1-Port+N": [
        "directivity", "source_match", "reflection_tracking", "transmission_tracking"
    ],
    "Enhanced-Response": [
        "directivity", "source_match", "reflection_tracking",
        "transmission_tracking", "load_match"
    ],
}

# Which S-parameter index to read per term:
# 1-port files (s1p) → S11 = s[:,0,0]
# 2-port files (s2p) → S21 = s[:,1,0]  (forward transmission)
_TERM_IS_TWOPORT = {
    "directivity":           False,
    "source_match":          False,
    "reflection_tracking":   False,
    "transmission_tracking": True,
    "load_match":            True,
}


def _get_s_data(network: rf.Network, term: str) -> np.ndarray:
    """
    Return the most meaningful S-parameter vector for a given error term.

    - 1-port terms (directivity, source_match, reflection_tracking) → S11 = s[:,0,0]
    - 2-port terms (transmission_tracking, load_match)              → S21 = s[:,1,0]

    Falls back gracefully if the file has fewer ports than expected.
    """
    nports = network.s.shape[1]
    want_twoport = _TERM_IS_TWOPORT.get(term, False)

    if want_twoport and nports >= 2:
        return network.s[:, 1, 0]   # S21
    return network.s[:, 0, 0]       # S11


def _find_file(folder: str, stem: str) -> str | None:
    """Return the first file in *folder* whose stem matches *stem* (any extension)."""
    for ext in (".s1p", ".s2p", ".s3p"):
        candidate = os.path.join(folder, f"{stem}{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def _load_network(path: str) -> rf.Network | None:
    try:
        return rf.Network(path)
    except Exception as e:
        logging.warning("[error_visualizer] Could not load %s: %s", path, e)
        return None


def _resolve_kit_base_name(kit_name: str) -> str:
    """
    Strip the timestamp suffix from a kit name.

    Examples
    --------
    'Normalization_Calibration_20250601_143022' → 'Normalization_Calibration'
    'OSM_Kit_3'                                 → 'OSM_Kit'  (legacy numeric suffix)
    'MyKit'                                     → 'MyKit'    (no suffix, unchanged)
    """
    # First try to strip a full datetime stamp: _YYYYMMDD_HHMMSS
    name = re.sub(r'_\d{8}_\d{6}$', '', kit_name)
    if name != kit_name:
        return name

    # Fallback: strip a plain trailing numeric suffix (e.g. _3)
    return re.sub(r'_\d+$', '', kit_name)


# ─────────────────────────────────────────────────────────────────────────────
# Plot canvas
# ─────────────────────────────────────────────────────────────────────────────

class _DualCanvas(QWidget):
    """Two matplotlib axes side by side: magnitude (dB) and phase (°)."""

    def __init__(self, is_dark: bool = True, parent=None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._setup_rcparams()

        self.fig = Figure(figsize=(9, 3.6), tight_layout=True)
        self.ax_mag   = self.fig.add_subplot(1, 2, 1)
        self.ax_phase = self.fig.add_subplot(1, 2, 2)

        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self._apply_theme()

    # ── theme ─────────────────────────────────────────────────────────────────

    def _setup_rcparams(self):
        rcParams['mathtext.fontset'] = 'cm'
        rcParams['text.usetex']      = False
        rcParams['font.family']      = 'serif'
        rcParams['axes.labelsize']   = 11

    def _bg(self):   return "#1e1e2e" if self._is_dark else "#f8f8f2"
    def _fg(self):   return "#cdd6f4" if self._is_dark else "#1e1e2e"
    def _grid(self): return "#45475a" if self._is_dark else "#ccc"
    def _accent(self): return "#89b4fa"  # Catppuccin blue – works on both themes

    def _apply_theme(self):
        bg = self._bg()
        fg = self._fg()
        grid = self._grid()

        self.fig.patch.set_facecolor(bg)
        for ax in (self.ax_mag, self.ax_phase):
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg, labelsize=9)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            ax.title.set_color(fg)
            for spine in ax.spines.values():
                spine.set_edgecolor(grid)
            ax.grid(True, color=grid, linewidth=0.5, linestyle="--", alpha=0.6)

    # ── public ────────────────────────────────────────────────────────────────

    def plot(self, network: rf.Network, label: str, term: str):
        """
        Plot magnitude and phase of the appropriate S-parameter from *network*.

        *term* is used to select the correct S-parameter index (S11 vs S21).
        """
        self.ax_mag.cla()
        self.ax_phase.cla()
        self._apply_theme()

        freqs_ghz = network.f / 1e9
        # FIX: use the correct S-parameter index for the given error term
        s = _get_s_data(network, term)

        mag_db = 20 * np.log10(np.abs(s) + 1e-12)
        phase  = np.angle(s, deg=True)

        color = self._accent()

        self.ax_mag.plot(freqs_ghz, mag_db, color=color, linewidth=1.6)
        self.ax_mag.set_xlabel("Frequency (GHz)")
        self.ax_mag.set_ylabel("Magnitude (dB)")
        self.ax_mag.set_title(f"{label} — Magnitude")

        self.ax_phase.plot(freqs_ghz, phase, color="#a6e3a1", linewidth=1.6)
        self.ax_phase.set_xlabel("Frequency (GHz)")
        self.ax_phase.set_ylabel("Phase (°)")
        self.ax_phase.set_title(f"{label} — Phase")

        self.canvas.draw()

    def clear(self):
        self.ax_mag.cla()
        self.ax_phase.cla()
        self._apply_theme()
        self.canvas.draw()

    def get_figure(self) -> Figure:
        return self.fig


# ─────────────────────────────────────────────────────────────────────────────
# Main dialog
# ─────────────────────────────────────────────────────────────────────────────

class ErrorVisualizerDialog(QDialog):
    """
    Visualize calibration error terms with navigation and export.

    Parameters
    ----------
    errors_folder : str
        Path to the folder containing the .s1p/.s2p error files.
    method : str
        Calibration method name (key in _METHOD_TERMS).
    is_dark : bool
        Match the app's dark/light theme.
    """

    def __init__(self, errors_folder: str, method: str,
                 is_dark: bool = True, parent=None):
        super().__init__(parent)

        self._folder  = errors_folder
        self._method  = method
        self._is_dark = is_dark
        self._terms   = _METHOD_TERMS.get(method, [])
        self._index   = 0

        self._networks: dict[str, rf.Network | None] = {}
        self._load_all()

        self._build_ui()
        self._refresh()

    # ── data ──────────────────────────────────────────────────────────────────

    def _load_all(self):
        for term in self._terms:
            path = _find_file(self._folder, term)
            self._networks[term] = _load_network(path) if path else None

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("NanoVNA UTN Toolkit — Calibration Error Viewer")
        self.setMinimumSize(860, 520)
        self.resize(960, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)

        # ── header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()

        self._method_label = QLabel(f"Method:  {self._method}")
        self._method_label.setFont(QFont("serif", 10))
        self._method_label.setStyleSheet(f"color: {'#89b4fa' if self._is_dark else '#3060c0'}; font-weight: bold;")

        self._term_label = QLabel()
        self._term_label.setFont(QFont("serif", 13, QFont.Bold))
        self._term_label.setAlignment(Qt.AlignCenter)

        self._counter_label = QLabel()
        self._counter_label.setFont(QFont("serif", 10))
        self._counter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._counter_label.setStyleSheet(f"color: {'#6c7086' if self._is_dark else '#888'};")

        header.addWidget(self._method_label, 1)
        header.addWidget(self._term_label,   2)
        header.addWidget(self._counter_label, 1)
        root.addLayout(header)

        # ── canvas ────────────────────────────────────────────────────────────
        self._canvas = _DualCanvas(is_dark=self._is_dark, parent=self)
        root.addWidget(self._canvas, stretch=1)

        # ── navigation + export ───────────────────────────────────────────────
        nav = QHBoxLayout()
        nav.setSpacing(10)

        self._btn_prev = QPushButton("◀  Previous")
        self._btn_prev.setFixedWidth(120)
        self._btn_prev.clicked.connect(self._prev)

        self._btn_next = QPushButton("Next  ▶")
        self._btn_next.setFixedWidth(120)
        self._btn_next.clicked.connect(self._next)

        self._btn_export_img = QPushButton("⬇  Export Images")
        self._btn_export_img.clicked.connect(self._export_images)

        self._btn_export_ts = QPushButton("⬇  Export Touchstone")
        self._btn_export_ts.clicked.connect(self._export_touchstone)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)

        nav.addWidget(self._btn_prev)
        nav.addWidget(self._btn_next)
        nav.addStretch()
        nav.addWidget(self._btn_export_img)
        nav.addWidget(self._btn_export_ts)
        nav.addSpacing(16)
        nav.addWidget(btn_close)

        root.addLayout(nav)

    # ── navigation ────────────────────────────────────────────────────────────

    def _prev(self):
        if self._index > 0:
            self._index -= 1
            self._refresh()

    def _next(self):
        if self._index < len(self._terms) - 1:
            self._index += 1
            self._refresh()

    def _refresh(self):
        n = len(self._terms)
        if n == 0:
            self._term_label.setText("No error terms available")
            self._canvas.clear()
            return

        term    = self._terms[self._index]
        label   = _ERROR_LABELS.get(term, term)
        network = self._networks.get(term)

        self._term_label.setText(label)
        self._counter_label.setText(f"{self._index + 1} / {n}")

        self._btn_prev.setEnabled(self._index > 0)
        self._btn_next.setEnabled(self._index < n - 1)

        if network is not None:
            # FIX: pass *term* so the canvas picks the correct S-parameter index
            self._canvas.plot(network, label, term)
        else:
            self._canvas.clear()
            for ax in (self._canvas.ax_mag, self._canvas.ax_phase):
                ax.text(
                    0.5, 0.5, "File not found",
                    transform=ax.transAxes,
                    ha="center", va="center",
                    fontsize=13,
                    color="#f38ba8",
                    fontstyle="italic"
                )
            self._canvas.canvas.draw()

    # ── export ────────────────────────────────────────────────────────────────

    def _export_images(self):
        """Save one PNG per error term (both magnitude+phase in the same figure)."""
        dest_dir = QFileDialog.getExistingDirectory(
            self, "Select folder to save images"
        )
        if not dest_dir:
            return

        saved = 0
        for term in self._terms:
            net = self._networks.get(term)
            if net is None:
                continue
            label = _ERROR_LABELS.get(term, term)

            fig = Figure(figsize=(10, 4), tight_layout=True)
            ax_m = fig.add_subplot(1, 2, 1)
            ax_p = fig.add_subplot(1, 2, 2)

            freqs_ghz = net.f / 1e9
            # FIX: use correct S-parameter index per term
            s = _get_s_data(net, term)
            mag_db = 20 * np.log10(np.abs(s) + 1e-12)
            phase  = np.angle(s, deg=True)

            ax_m.plot(freqs_ghz, mag_db,  color="#89b4fa", linewidth=1.6)
            ax_m.set_xlabel("Frequency (GHz)"); ax_m.set_ylabel("Magnitude (dB)")
            ax_m.set_title(f"{label} — Magnitude"); ax_m.grid(True, linestyle="--", alpha=0.5)

            ax_p.plot(freqs_ghz, phase, color="#a6e3a1", linewidth=1.6)
            ax_p.set_xlabel("Frequency (GHz)"); ax_p.set_ylabel("Phase (°)")
            ax_p.set_title(f"{label} — Phase"); ax_p.grid(True, linestyle="--", alpha=0.5)

            out_path = os.path.join(dest_dir, f"{term}.png")
            fig.savefig(out_path, dpi=150, bbox_inches="tight")
            saved += 1

        QMessageBox.information(self, "Export complete",
                                f"Saved {saved} image(s) to:\n{dest_dir}")

    def _export_touchstone(self):
        """Copy all error .s1p/.s2p files for the current method to a chosen folder."""
        dest_dir = QFileDialog.getExistingDirectory(
            self, "Select folder to save Touchstone files"
        )
        if not dest_dir:
            return

        import shutil
        saved = 0
        missing = []

        for term in self._terms:
            path = _find_file(self._folder, term)
            if path:
                shutil.copy2(path, dest_dir)
                saved += 1
            else:
                missing.append(term)

        msg = f"Exported {saved} Touchstone file(s) to:\n{dest_dir}"
        if missing:
            labels = [_ERROR_LABELS.get(t, t) for t in missing]
            msg += f"\n\nNot found: {', '.join(labels)}"

        QMessageBox.information(self, "Export complete", msg)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def open_error_visualizer(parent_self, errors_folder: str | None = None,
                          method: str | None = None):
    """
    Open the error visualizer dialog.

    Can be called from two contexts:

    1. After a fresh calibration — pass *errors_folder* and *method* explicitly.
    2. From the kit selector — resolve folder/method from QSettings if not passed.
    """
    from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings
    from NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils import get_calibration_path

    # ── resolve method ────────────────────────────────────────────────────────
    if method is None:
        settings = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )
        method = settings.value("Calibration/Method", "---")

    if method == "---" or method not in _METHOD_TERMS:
        QMessageBox.warning(parent_self, "No calibration",
                            "No valid calibration method found.")
        return

    # ── resolve folder ────────────────────────────────────────────────────────
    if errors_folder is None:
        settings = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )

        kit_ok         = settings.value("Calibration/Kits", False, type=bool)
        no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)

        if no_calibration:
            QMessageBox.information(parent_self, "No calibration",
                                    "No calibration is active.")
            return

        if kit_ok:
            import sys
            kit_name = settings.value("Calibration/Name", "")

            base_name = _resolve_kit_base_name(kit_name)

            errors_folder = get_calibration_path(
                f"modules/dut_measurement/calibration/kits/{base_name}",
                f"modules/dut_measurement/calibration/kits/{base_name}",
                Path(__file__).resolve()
            )

            # Safety check: if the resolved folder doesn't exist, warn early
            # instead of silently showing "File not found" for every term.
            if not os.path.isdir(str(errors_folder)):
                logging.warning(
                    "[error_visualizer] Kit folder not found: %s  "
                    "(kit_name=%r, base_name=%r)",
                    errors_folder, kit_name, base_name
                )
                QMessageBox.warning(
                    parent_self, "Kit folder not found",
                    f"Could not locate the calibration kit folder:\n{errors_folder}\n\n"
                    f"Kit name stored in settings: '{kit_name}'\n"
                    f"Resolved base name: '{base_name}'"
                )
                return
        else:
            _folder_map = {
                "OSM (Open - Short - Match)":
                    ("modules/dut_measurement/calibration/osm_results/osm_errors",) * 2,
                "Normalization":
                    ("modules/dut_measurement/calibration/thru_results/normalization_errors",) * 2,
                "1-Port+N":
                    ("modules/dut_measurement/calibration/thru_results/1-Port+N_errors",) * 2,
                "Enhanced-Response":
                    ("modules/dut_measurement/calibration/thru_results/enhanced_response_errors",) * 2,
            }
            rel1, rel2 = _folder_map[method]
            errors_folder = get_calibration_path(rel1, rel2, Path(__file__).resolve())

    # ── dark mode ─────────────────────────────────────────────────────────────
    is_dark = getattr(parent_self, "is_dark_mode", True)

    # ── open ──────────────────────────────────────────────────────────────────
    dlg = ErrorVisualizerDialog(
        errors_folder=str(errors_folder),
        method=method,
        is_dark=is_dark,
        parent=parent_self
    )
    dlg.exec()