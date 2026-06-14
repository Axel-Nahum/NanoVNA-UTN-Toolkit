"""
Permittivity-vs-frequency chart (module-local).

EN: Plots the complex relative permittivity epsilon_r against frequency:
    the real part (epsilon_r') and the loss (epsilon_r'' = -Im(epsilon_r),
    using the eps' - j*eps'' convention). Optionally overlays the other
    candidate root branches faintly so the user can compare. Built with the
    same builder/manager shape as ``utils/smith_chart_utils.py`` but kept
    inside the module so it does not depend on shared chart utilities.

ES: Grafica la permitividad relativa compleja epsilon_r en funcion de la
    frecuencia: la parte real (epsilon_r') y la perdida
    (epsilon_r'' = -Im(epsilon_r), con la convencion eps' - j*eps''). De forma
    opcional superpone tenuemente las otras ramas candidatas para comparar.
    Construido con la misma forma builder/manager que
    ``utils/smith_chart_utils.py`` pero dentro del modulo para no depender de
    utilidades compartidas.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FuncFormatter, MaxNLocator
from PySide6.QtWidgets import QSizePolicy

logger = logging.getLogger(__name__)

plt.rcParams["mathtext.fontset"] = "cm"
plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.rm"] = "serif"


def _freq_formatter(value, _pos):
    if value >= 1e9:
        return f"{value / 1e9:.2f} GHz"
    if value >= 1e6:
        return f"{value / 1e6:.0f} MHz"
    if value >= 1e3:
        return f"{value / 1e3:.0f} kHz"
    return f"{value:.0f} Hz"


def _make_freq_axis(freqs):
    """Return (unit_str, FuncFormatter) for a clean single-unit x-axis.

    Ticks show plain numbers (e.g. 0.5, 1, 1.5) without trailing zeros;
    the unit appears only in the axis label ("Frequency (GHz)").
    """
    max_f = float(np.max(np.asarray(freqs, dtype=float)))
    if max_f >= 0.5e9:
        div, unit = 1e9, "GHz"
    elif max_f >= 0.5e6:
        div, unit = 1e6, "MHz"
    elif max_f >= 0.5e3:
        div, unit = 1e3, "kHz"
    else:
        div, unit = 1.0, "Hz"

    def _fmt(value, _pos, _div=div):
        v = value / _div
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return s

    return unit, FuncFormatter(_fmt)


class EpsilonChartConfig:
    """Styling for the permittivity chart."""

    def __init__(self):
        self.background_color = "#1e1e1e"
        self.text_color = "#cccccc"
        self.grid_color = "#444444"
        self.spine_color = "#555555"
        self.real_color = "#4da6ff"
        self.loss_color = "#d62728"
        self.candidate_color = "#555555"
        self.linewidth = 2.0
        self.candidate_linewidth = 0.8
        self.candidate_alpha = 0.35


class EpsilonChartManager:
    """High-level manager for the permittivity-vs-frequency chart."""

    def __init__(self, config: Optional[EpsilonChartConfig] = None):
        self.config = config or EpsilonChartConfig()
        self.fig: Optional[Any] = None
        self.ax: Optional[Any] = None
        self.canvas: Optional[FigureCanvas] = None

    def create_wizard_epsilon_chart(self, freqs, figsize=(7, 5), container_layout=None,
                                    title=r"$\varepsilon_r$ vs Frequency",
                                    real_label=r"$\varepsilon_r'$",
                                    loss_label=r"$\varepsilon_r''$"):
        """Create an empty permittivity chart and (optionally) add it to a layout."""
        self.fig, self.ax = plt.subplots(figsize=figsize, layout="constrained")
        # Extra breathing room above the title and below the x-axis ticks.
        self.fig.get_layout_engine().set(h_pad=0.25, rect=[0.0, 0.04, 0.95, 0.94])
        self.fig.patch.set_facecolor(self.config.background_color)
        self.ax.set_facecolor(self.config.background_color)

        self._real_label = real_label
        self._loss_label = loss_label
        self._title = title

        self.ax.set_title(title, fontsize=13, pad=10, color=self.config.text_color)
        self.ax.set_ylabel(r"$\varepsilon_r$", fontsize=12, color=self.config.text_color)
        self.ax.grid(True, linestyle=":", alpha=0.4, color=self.config.grid_color)
        self.ax.tick_params(colors=self.config.text_color)
        for spine in self.ax.spines.values():
            spine.set_color(self.config.spine_color)

        self.canvas = FigureCanvas(self.fig)
        # Ignored: Qt never uses the canvas sizeHint() so canvas.draw() cannot
        # trigger a layout cascade that would grow the wizard window.
        self.canvas.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.canvas.setMinimumSize(1, 1)

        if container_layout is not None:
            container_layout.addWidget(self.canvas)

        return self.fig, self.ax, self.canvas

    def update_epsilon_curves(self, ax, freqs, eps_selected, canvas=None,
                              candidates=None):
        """
        Draw the selected permittivity branch (and optional faint candidates).

        Parameters
        ----------
        eps_selected : np.ndarray (complex)
            The auto-selected / chosen branch, aligned with ``freqs``.
        candidates : np.ndarray (complex) (n_freq, k), optional
            All candidate roots, drawn faintly (real part only) for comparison.
        """
        try:
            freqs = np.asarray(freqs, dtype=float)
            eps_selected = np.asarray(eps_selected, dtype=complex)

            unit, freq_fmt = _make_freq_axis(freqs)

            ax.clear()
            ax.set_facecolor(self.config.background_color)
            ax.set_title(getattr(self, "_title", r"$\varepsilon_r$ vs Frequency"), fontsize=13, pad=10, color=self.config.text_color)
            ax.set_xlabel(f"Frequency ({unit})", fontsize=12, color=self.config.text_color)
            ax.set_ylabel(r"$\varepsilon_r$", fontsize=12, color=self.config.text_color)
            ax.grid(True, linestyle=":", alpha=0.4, color=self.config.grid_color)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune="both"))
            ax.xaxis.set_major_formatter(freq_fmt)
            ax.tick_params(colors=self.config.text_color)
            for spine in ax.spines.values():
                spine.set_color(self.config.spine_color)

            if candidates is not None:
                candidates = np.asarray(candidates, dtype=complex)
                for k in range(candidates.shape[1]):
                    ax.plot(
                        freqs, np.real(candidates[:, k]),
                        color=self.config.candidate_color,
                        linewidth=self.config.candidate_linewidth,
                        alpha=self.config.candidate_alpha,
                        zorder=1,
                    )

            real = np.real(eps_selected)
            loss = -np.imag(eps_selected)   # eps'' for eps = eps' - j*eps''

            ax.plot(freqs, real, color=self.config.real_color,
                    linewidth=self.config.linewidth,
                    label=getattr(self, "_real_label", r"$\varepsilon_r'$"), zorder=3)
            ax.plot(freqs, loss, color=self.config.loss_color,
                    linewidth=self.config.linewidth,
                    label=getattr(self, "_loss_label", r"$\varepsilon_r''$"), zorder=3)

            ax.legend(loc="upper right")

            if canvas:
                canvas.draw()
        except Exception as exc:  # noqa: BLE001
            logger.error("[epsilon_chart] Error updating curves: %s", exc)


def create_wizard_epsilon_chart(freqs, container_layout=None, figsize=(7, 5)):
    """Convenience function mirroring ``create_wizard_smith_chart``."""
    manager = EpsilonChartManager()
    return manager.create_wizard_epsilon_chart(
        freqs, figsize=figsize, container_layout=container_layout
    )
