"""
Permittivity-vs-frequency chart (module-local).

EN: Plots the complex relative permittivity epsilon_r against frequency:
    the real part (epsilon_r') and the loss (epsilon_r'' = -Im(epsilon_r),
    using the eps' - j*eps'' convention). Optionally overlays the other
    candidate root branches faintly so the user can compare. Frequencies
    without a solution (gaps) are left as breaks in both curves -- never
    interpolated -- and isolated valid points are drawn as dots. Built with
    the same builder/manager shape as ``utils/smith_chart_utils.py`` but kept
    inside the module so it does not depend on shared chart utilities.

ES: Grafica la permitividad relativa compleja epsilon_r en funcion de la
    frecuencia: la parte real (epsilon_r') y la perdida
    (epsilon_r'' = -Im(epsilon_r), con la convencion eps' - j*eps''). De forma
    opcional superpone tenuemente las otras ramas candidatas para comparar.
    Las frecuencias sin solucion (gaps) quedan como cortes en ambas curvas
    -- nunca se interpolan -- y los puntos validos aislados se dibujan como
    puntos. Construido con la misma forma builder/manager que
    ``utils/smith_chart_utils.py`` pero dentro del modulo para no depender de
    utilidades compartidas.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure as _Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator
from PySide6.QtWidgets import QSizePolicy

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.permittivity_columns import (
    isolated_points,
    permittivity_columns,
    plot_with_gaps,
)

logger = logging.getLogger(__name__)

plt.rcParams.update({
    "mathtext.fontset":           "cm",
    "font.family":                "serif",
    "mathtext.rm":                "serif",
})

# Tick numbers in the CM math font are wanted on THIS chart only. Setting
# "axes.formatter.use_mathtext" globally (as before) made every tick label of
# every chart in the app a mathtext string, and a new label costs ~14 ms to
# parse: the first draw of a rebuilt wizard step spent 450 ms on tick labels.


def _use_cm_ticks(ax) -> None:
    """CM-font tick numbers on ``ax`` (what the global rcParam used to give)."""
    for axis in (ax.xaxis, ax.yaxis):
        fmt = axis.get_major_formatter()
        if hasattr(fmt, "set_useMathText"):
            fmt.set_useMathText(True)


def _enlarge_mathtext_cache(size: int = 512) -> None:
    """matplotlib caches parsed mathtext in an lru_cache(50); the epsilon chart
    alone shows more distinct tick labels than that across autoscaled ticks,
    so every tick re-parsed. Re-wrap the parser with a larger cache (best
    effort: silently skipped if matplotlib's internals differ)."""
    try:
        import functools
        from matplotlib.mathtext import MathTextParser
        cached = MathTextParser._parse_cached
        inner = getattr(cached, "__wrapped__", None)
        if inner is not None and getattr(cached, "cache_info", None) is not None \
                and cached.cache_info().maxsize is not None and cached.cache_info().maxsize < size:
            MathTextParser._parse_cached = functools.lru_cache(size)(inner)
    except Exception as exc:   # noqa: BLE001
        logger.debug("[epsilon_chart] mathtext cache not enlarged: %s", exc)


_enlarge_mathtext_cache()


def _freq_formatter(value, _pos):
    if value >= 1e9:
        return f"{value / 1e9:.2f} GHz"
    if value >= 1e6:
        return f"{value / 1e6:.0f} MHz"
    if value >= 1e3:
        return f"{value / 1e3:.0f} kHz"
    return f"{value:.0f} Hz"


def _freq_unit_for_range(start_hz: float, stop_hz: float):
    """Return (divisor, unit_str) for a frequency range, matching the user unit rule.

    Both in kHz → kHz; both MHz → MHz; both GHz → GHz;
    kHz + GHz → GHz; kHz + MHz or MHz + GHz → MHz.
    """
    def _tier(f):
        if f >= 1e9: return 2
        if f >= 1e6: return 1
        return 0

    t0, t1 = _tier(start_hz), _tier(stop_hz)
    if t0 == t1:
        return (1e9, "GHz") if t0 == 2 else (1e6, "MHz") if t0 == 1 else (1e3, "kHz")
    if 1 in (t0, t1):
        return 1e6, "MHz"
    return 1e9, "GHz"


def _make_freq_axis(freqs):
    """Return (unit_str, FuncFormatter) for a clean single-unit x-axis.

    Ticks show plain numbers (e.g. 0.5, 1, 1.5) without trailing zeros;
    the unit appears only in the axis label ("Frequency (GHz)").
    Uses start + end frequency to determine the unit via the user rule.
    """
    arr = np.asarray(freqs, dtype=float)
    start_f = float(arr[0]) if len(arr) > 0 else 0.0
    stop_f  = float(arr[-1]) if len(arr) > 0 else 0.0
    div, unit = _freq_unit_for_range(start_f, stop_f)

    def _fmt(value, _pos, _div=div):
        v = value / _div
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return f"${s}$"

    return unit, FuncFormatter(_fmt)


def _plot_trace(ax, x, y, **line_kwargs):
    """``plot_with_gaps`` that also returns its isolated-point markers (or None)."""
    before = len(ax.lines)
    line = plot_with_gaps(ax, x, y, **line_kwargs)
    extra = ax.lines[before + 1:]
    return line, (extra[0] if extra else None)


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
        self.real_linewidth = 2.0
        self.loss_linewidth = 2.0
        self.candidate_linewidth = 0.8
        self.candidate_alpha = 0.35


class EpsilonChartManager:
    """High-level manager for the permittivity-vs-frequency chart."""

    def __init__(self, config: Optional[EpsilonChartConfig] = None):
        self.config = config or EpsilonChartConfig()
        self.fig: Optional[Any] = None
        self.ax: Optional[Any] = None
        self.canvas: Optional[FigureCanvas] = None
        # Artists of the last full update_epsilon_curves, for in-place updates.
        self._live: Optional[dict] = None

    def create_wizard_epsilon_chart(self, freqs, figsize=(7, 5), container_layout=None,
                                    title=r"$\varepsilon_r$ vs Frequency",
                                    real_label=r"$\varepsilon_r'$",
                                    loss_label=r"$\varepsilon_r''$"):
        """Create an empty permittivity chart and (optionally) add it to a layout."""
        self.fig = _Figure(figsize=figsize)
        self.ax = self.fig.add_subplot(111)
        self.fig.set_layout_engine("constrained")
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
                              candidates=None, autoscale=True, crosscheck=None,
                              crosscheck_label=None):
        """
        Draw the selected permittivity branch (and optional faint candidates).

        Parameters
        ----------
        eps_selected : np.ndarray (complex)
            The auto-selected / chosen branch, aligned with ``freqs``.
        candidates : np.ndarray (complex) (n_freq, k), optional
            All candidate roots, drawn faintly (real part only) for comparison.
        crosscheck : np.ndarray (complex) (n_freq,), optional
            Simplified-method curve overlaid as dotted lines in the same
            colors, so both methods can be compared on one chart.
        crosscheck_label : str, optional
            Legend label of the cross-check pair (default "simplified").
        """
        try:
            freqs = np.asarray(freqs, dtype=float)
            eps_selected = np.asarray(eps_selected, dtype=complex)

            unit, freq_fmt = _make_freq_axis(freqs)

            ax.clear()
            _use_cm_ticks(ax)
            ax.set_facecolor(self.config.background_color)
            ax.set_title(getattr(self, "_title", r"$\varepsilon_r$ vs Frequency"), fontsize=13, pad=10, color=self.config.text_color)
            ax.set_xlabel(rf"Frequency $(\mathrm{{{unit}}})$", fontsize=12, color=self.config.text_color)
            ax.set_ylabel(r"$\varepsilon_r$", fontsize=12, color=self.config.text_color)
            ax.grid(True, linestyle=":", alpha=0.4, color=self.config.grid_color)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune="both"))
            ax.xaxis.set_major_formatter(freq_fmt)
            ax.tick_params(colors=self.config.text_color)
            for spine in ax.spines.values():
                spine.set_color(self.config.spine_color)

            self._live = None
            traces = []   # (kind, line, dots) in drawing order, for in-place updates

            if candidates is not None:
                candidates = np.asarray(candidates, dtype=complex)
                for k in range(candidates.shape[1]):
                    cand_real, _ = permittivity_columns(candidates[:, k])
                    traces.append(("cand",) + _plot_trace(
                        ax, freqs, cand_real,
                        color=self.config.candidate_color,
                        linewidth=self.config.candidate_linewidth,
                        alpha=self.config.candidate_alpha,
                        zorder=1,
                    ))

            # eps'' = -Im(eps) for eps = eps' - j*eps''. Gaps stay NaN in both
            # curves: a visible break is honest, an interpolated bridge is not.
            real, loss = permittivity_columns(eps_selected)

            traces.append(("real",) + _plot_trace(
                ax, freqs, real, color=self.config.real_color,
                linewidth=self.config.real_linewidth,
                label=getattr(self, "_real_label", r"$\varepsilon_r'$"), zorder=3))
            traces.append(("loss",) + _plot_trace(
                ax, freqs, loss, color=self.config.loss_color,
                linewidth=self.config.loss_linewidth,
                label=getattr(self, "_loss_label", r"$\varepsilon_r''$"), zorder=3))

            if crosscheck is not None:
                cc_real, cc_loss = permittivity_columns(crosscheck)
                cc_tag = crosscheck_label or "simplified"
                # Dotted, same colors: reads as "the same quantity, other method".
                traces.append(("cc_real",) + _plot_trace(
                    ax, freqs, cc_real,
                    color=self.config.real_color, linewidth=1.4,
                    linestyle=":", alpha=0.85, zorder=2,
                    label=rf"$\varepsilon_r'$ ({cc_tag})"))
                traces.append(("cc_loss",) + _plot_trace(
                    ax, freqs, cc_loss,
                    color=self.config.loss_color, linewidth=1.4,
                    linestyle=":", alpha=0.85, zorder=2,
                    label=rf"$\varepsilon_r''$ ({cc_tag})"))

            ax.legend(loc="upper right")

            if autoscale:
                all_y = np.concatenate([real, loss])
                finite_y = all_y[np.isfinite(all_y)]
                if len(finite_y) > 0:
                    y_min, y_max = float(finite_y.min()), float(finite_y.max())
                    y_margin = (y_max - y_min) * 0.10 if y_max != y_min else 1.0
                    ax.set_ylim(y_min - y_margin, y_max + y_margin)
                    ax.autoscale(False)

                freq_range = float(freqs[-1] - freqs[0])
                x_margin = freq_range * 0.04
                ax.set_xlim(float(freqs[0]) - x_margin, float(freqs[-1]) + x_margin)

            self._live = {
                "ax": ax,
                "freqs": freqs.copy(),
                "unit": unit,
                "traces": traces,
                "has_crosscheck": crosscheck is not None,
                "n_candidates": 0 if candidates is None else int(candidates.shape[1]),
            }

            if canvas:
                canvas.draw()
        except Exception as exc:  # noqa: BLE001
            logger.error("[epsilon_chart] Error updating curves: %s", exc)

    def trace_artists(self, ax=None) -> list:
        """Lines and isolated-point markers drawn by the last full update."""
        live = self._live
        if not live or (ax is not None and live["ax"] is not ax):
            return []
        arts = []
        for _kind, line, dots in live["traces"]:
            for artist in (line, dots):
                if artist is not None and getattr(artist, "axes", None) is live["ax"]:
                    arts.append(artist)
        return arts

    def update_epsilon_curves_inplace(self, ax, freqs, eps_selected, candidates=None,
                                      crosscheck=None) -> Optional[list]:
        """
        New data into the existing curves; nothing else on the axes changes.

        EN: The real-time path of the results window: a full update clears the
            axes and rebuilds title, labels, grid, ticks and legend (~70 ms of
            the ~90 ms tick). Here only the line data (and the isolated-point
            markers) change. Returns the trace artists for the caller to blit,
            or None when the chart cannot be updated in place (no previous full
            update on ``ax``, another frequency grid or unit, a different set of
            curves, a new isolated point without a marker artist): the caller
            then does the full update. Axis limits are the caller's business.
        ES: Datos nuevos en las curvas existentes; None si hace falta la
            reconstruccion completa (otra grilla, otras curvas, punto aislado
            nuevo sin artista).
        """
        live = self._live
        if not live or live["ax"] is not ax:
            return None
        try:
            freqs = np.asarray(freqs, dtype=float)
            old_freqs = live["freqs"]
            if freqs.shape != old_freqs.shape or not np.array_equal(freqs, old_freqs):
                return None
            if (crosscheck is not None) != live["has_crosscheck"]:
                return None
            n_cand = 0 if candidates is None else int(np.asarray(candidates).shape[1])
            if n_cand != live["n_candidates"]:
                return None

            real, loss = permittivity_columns(np.asarray(eps_selected, dtype=complex))
            series = {"real": [real], "loss": [loss], "cand": []}
            if candidates is not None:
                candidates = np.asarray(candidates, dtype=complex)
                series["cand"] = [permittivity_columns(candidates[:, k])[0] for k in range(n_cand)]
            if crosscheck is not None:
                cc_real, cc_loss = permittivity_columns(crosscheck)
                series["cc_real"], series["cc_loss"] = [cc_real], [cc_loss]

            # Validate everything first, then mutate: a refusal leaves the chart intact.
            plan = []
            cursor = {key: 0 for key in series}
            for kind, line, dots in live["traces"]:
                values = series.get(kind)
                if values is None or cursor[kind] >= len(values) or getattr(line, "axes", None) is not ax:
                    return None
                y = np.asarray(values[cursor[kind]], dtype=float)
                cursor[kind] += 1
                lonely = isolated_points(y)
                if np.any(lonely) and dots is None:
                    return None   # a marker artist would have to be created
                plan.append((line, dots, y, lonely))

            arts = []
            for line, dots, y, lonely in plan:
                line.set_data(freqs, y)
                arts.append(line)
                if dots is not None:
                    dots.set_data(freqs[lonely], y[lonely])
                    arts.append(dots)
            return arts
        except Exception as exc:  # noqa: BLE001
            logger.warning("[epsilon_chart] in-place update failed, full update instead: %s", exc)
            return None


def create_wizard_epsilon_chart(freqs, container_layout=None, figsize=(7, 5)):
    """Convenience function mirroring ``create_wizard_smith_chart``."""
    manager = EpsilonChartManager()
    return manager.create_wizard_epsilon_chart(
        freqs, figsize=figsize, container_layout=container_layout
    )
