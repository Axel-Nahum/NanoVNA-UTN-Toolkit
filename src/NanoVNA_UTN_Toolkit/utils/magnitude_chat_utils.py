"""
Magnitude Plot utilities for NanoVNA toolkit.

This module consolidates all magnitude plot-related functionality that was previously
duplicated across multiple files (wizard_windows.py, graphics_window.py, graphics_utils.py, etc.).
"""

import logging
import numpy as np

from pathlib import Path

from matplotlib.lines import Line2D
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import matplotlib.pyplot as plt

plt.rcParams['mathtext.fontset'] = 'cm'   # Fuente Computer Modern
plt.rcParams['text.usetex'] = False       # No requiere LaTeX externo
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'     # Coincide con el estilo de LaTeX
plt.rcParams['mathtext.rm'] = 'serif'     # Números y texto coherentes

# Import get_settings 

try:
    from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

class MagnitudeChartConfig:
    """Configuration class for magnitude chart styling and behavior."""
    
    def __init__(self):
        # Colors
        self.background_color = "white"
        self.axis_color = "black"
        self.text_color = "black"
        self.trace_color = "blue"
        self.marker_color = "red"
        
        # Line styling
        self.linewidth = 2
        self.markersize = 6
        self.marker_visible = True

        # ----------------------------------------------------
        # Plot Manager settings
        # ----------------------------------------------------

        self.settings = get_settings(
            "INI/dut_measurement/plot_manager/plot_manager.ini",
            "modules/dut_measurement/ui/utils/menu/plot_menu/plot_manager.ini",
            Path(__file__).resolve()
        )

class MagnitudeChartBuilder:
    """Builder class for creating and customizing magnitude charts (|S21| vs frequency)."""
    
    def __init__(self, config=None):
        self.config = config if config else MagnitudeChartConfig()
        self.ax = None
        self.fig = None
        self.canvas = None

    def setup_figure(self, figsize=(6, 4), layout_params=None):
        if layout_params is None:
            layout_params = {'left': 0.2, 'right': 0.9, 'top': 0.9, 'bottom': 0.15}

        self.fig, self.ax = plt.subplots(figsize=figsize)
        self.fig.subplots_adjust(**layout_params)
        self.ax.tick_params(axis='x', colors=self.config.axis_color)
        self.ax.tick_params(axis='y', colors=self.config.axis_color)
        self.ax.xaxis.label.set_color(self.config.text_color)
        self.ax.yaxis.label.set_color(self.config.text_color)
        self.ax.title.set_color(self.config.text_color)
        self.fig.patch.set_facecolor(self.config.background_color)
        self.ax.set_facecolor(self.config.background_color)

        current_state_grid = self.settings.value("grid/current_left_state", "true", type=bool)

        self.ax.grid(current_state_grid, linestyle="--", alpha=0.5)

        self.ax.set_xlabel(r"$\mathrm{Frequency\ (MHz)}$")
        self.ax.set_ylabel(r"$|S_{21}|\ (\mathrm{dB})$")
        self.ax.set_title(r"$\mathrm{Magnitude}$")

        #self.fig.tight_layout()

        def on_resize(event):
            #self.fig.tight_layout()
            self.canvas.draw_idle()

        self.fig.canvas.mpl_connect("resize_event", on_resize)

        return self.fig, self.ax

    def create_canvas(self):
        """Create Qt canvas for the figure."""
        if self.fig is None:
            raise ValueError("Figure must be created first using setup_figure()")
        self.canvas = FigureCanvas(self.fig)
        return self.canvas

    def plot_measurement_data(self, freqs, s_data, label=None, color=None, in_dB=False):
        """Plot measurement data as magnitude vs frequency."""
        if self.ax is None:
            raise ValueError("Axis must be created first using setup_figure()")
        
        color = color or self.config.trace_color
        magnitude = np.abs(s_data)
        if in_dB:
            magnitude = 20 * np.log10(magnitude + 1e-12)
        
        self.ax.plot(freqs, magnitude, '-', color=color, linewidth=self.config.linewidth, label=label)
        if label:
            self.ax.legend()
        return self.ax

    def add_cursor_marker(self, visible=None, color=None, size=None):
        """Add a cursor marker for interactive use."""
        visible = visible if visible is not None else self.config.marker_visible
        color = color or self.config.marker_color
        size = size or self.config.markersize
        if self.ax is None:
            return None
        cursor, = self.ax.plot([], [], 'o', markersize=size, color=color, visible=visible)
        return cursor

    def clear_and_redraw(self):
        """Clear axis for new plot."""
        if self.ax:
            self.ax.clear()
    
    def refresh_canvas(self):
        """Refresh the canvas display."""
        if self.canvas:
            self.canvas.draw()


class MagnitudeChartManager:
    """High-level manager for magnitude chart operations."""
    
    def __init__(self, config=None):
        self.config = config if config else MagnitudeChartConfig()
        self.builder = MagnitudeChartBuilder(self.config)

    # ============================================================
    # Wizard charts
    # ============================================================
    def create_wizard_magnitude_chart(self, start_freq, stop_freq, num_points, figsize=(6, 4), container_layout=None):
        """Create magnitude chart for calibration wizard."""
        fig, ax = self.builder.setup_figure(figsize=figsize)
        freqs = np.linspace(start_freq, stop_freq, num_points)

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

            if f_max < 1e6:
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

        ax.plot(new_freqs, np.zeros(num_points), color="white", alpha=0.3)
        ax.tick_params(axis="x", colors="black")
        ax.tick_params(axis="y", colors="black")
        ax.xaxis.label.set_color("black")
        ax.yaxis.label.set_color("black")
        ax.title.set_color("black")
        
        canvas = self.builder.create_canvas()
        if container_layout:
            container_layout.addWidget(canvas)
        return fig, ax, canvas

    def apply_axis_style(self, ax):
        """Apply consistent styling to the given axis."""
        ax.set_facecolor(self.config.background_color)
        ax.tick_params(axis='x', colors=self.config.axis_color)
        ax.tick_params(axis='y', colors=self.config.axis_color)
        ax.xaxis.label.set_color(self.config.text_color)
        ax.yaxis.label.set_color(self.config.text_color)
        ax.title.set_color(self.config.text_color)

        current_state_grid = self.settings.value("grid/current_left_state", "true", type=bool)

        ax.grid(current_state_grid, linestyle="--", alpha=0.5)

    def update_wizard_measurement(self, ax, freqs, s21_data, standard_name, canvas=None, color_map=None, in_dB=False):
        if color_map is None:
            color_map = {'thru': 'blue', 'open': 'orange', 'short': 'red', 'load': 'green'}


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

        try:
            ax.clear() 

            self.apply_axis_style(ax) 

            ax.set_xlabel(rf"$\mathrm{{Frequency\ ({unit})}}$")
            ax.set_ylabel(r"$|S_{21}|\ (\mathrm{dB})$")
            ax.set_title(rf"$\mathrm{{{standard_name.upper()}}}\ (\mathrm{{S21}})$")

            color = color_map.get(standard_name.lower(), self.config.trace_color)
            magnitude = np.abs(s21_data)
            magnitude = 20 * np.log10(magnitude + 1e-12)

            ax.plot(new_freqs, magnitude, '-', color=color, linewidth=self.config.linewidth)
            legend_line = Line2D([0], [0], color=color)
            ax.legend([legend_line], [rf"$\mathrm{{{standard_name.upper()}}}$"], 
                loc='upper left', frameon=True)

            if canvas:
                canvas.draw()

            logging.info(f"[MagnitudeChartManager] Updated magnitude plot for {standard_name}")

        except Exception as e:
            logging.error(f"[MagnitudeChartManager] Error updating magnitude measurement: {e}")


    # ============================================================
    # Graphics panel charts
    # ============================================================
    def create_graphics_panel_magnitude_chart(self, s_data, freqs, s_param="S21", figsize=(6, 4),
                                              container_layout=None, trace_color=None, marker_color=None, in_dB=False):
        """Create magnitude chart for graphics panels."""
        fig, ax = self.builder.setup_figure(figsize=figsize)
        self.builder.plot_measurement_data(freqs, s_data, label=s_param, color=trace_color, in_dB=in_dB)
        cursor = self.builder.add_cursor_marker(color=marker_color)
        canvas = self.builder.create_canvas()
        if container_layout:
            container_layout.addWidget(canvas)
        return fig, ax, canvas, cursor

    # ============================================================
    # Multi-measurement support
    # ============================================================
    def show_multiple_measurements(self, ax, measurements_dict, canvas=None, color_map=None,
                                   start_freq=None, stop_freq=None, num_points=None, in_dB=False):
        """Show multiple magnitude measurements on the same chart."""
        if color_map is None:
            color_map = {name.lower(): None for name in measurements_dict.keys()}
        try:
            ax.clear()
            for standard_name, (freqs, s21_data) in measurements_dict.items():
                color = color_map.get(standard_name.lower(), self.config.trace_color)
                magnitude = np.abs(s21_data)
                if in_dB:
                    magnitude = 20 * np.log10(magnitude + 1e-12)
                ax.plot(freqs, magnitude, '-', color=color, linewidth=self.config.linewidth, label=standard_name.upper())
            ax.set_xlabel(r"$\mathrm{Frequency\ (Hz)}$")
            ax.set_ylabel(r"$|S_{21}|\ (\mathrm{dB})$" if in_dB else r"$|S_{21}|\ (\mathrm{dB})$")

            current_state_grid = self.settings.value("grid/current_left_state", "true", type=bool)

            ax.grid(current_state_grid, linestyle="--", alpha=0.5)
            ax.legend()
            if canvas:
                canvas.draw()
            logging.info(f"[MagnitudeChartManager] Displayed {len(measurements_dict)} magnitude measurements")
        except Exception as e:
            logging.error(f"[MagnitudeChartManager] Error showing multiple magnitude measurements: {e}")


# ============================================================
# Convenience functions (analogous to Smith chart)
# ============================================================
def create_simple_magnitude_chart(freqs, s_data, figsize=(6, 4), s_param="S21", in_dB=False):
    """Simple function to create a basic magnitude chart."""
    manager = MagnitudeChartManager()
    fig, ax = manager.builder.setup_figure(figsize=figsize)
    manager.builder.plot_measurement_data(freqs, s_data, label=s_param, in_dB=in_dB)
    canvas = manager.builder.create_canvas()
    return fig, ax, canvas

def update_magnitude_chart_measurement(ax, freqs, s21_data, standard_name, canvas=None, in_dB=False):
    """Simple function to update magnitude chart with measurement."""
    manager = MagnitudeChartManager()
    manager.update_wizard_measurement(ax, freqs, s21_data, standard_name, canvas, in_dB=in_dB)

def create_wizard_magnitude_chart(start_freq, stop_freq, num_points, container_layout=None, figsize=(6, 4)):
    """Simple function to create wizard magnitude chart."""
    manager = MagnitudeChartManager()
    return manager.create_wizard_magnitude_chart(start_freq, stop_freq, num_points, figsize=figsize, container_layout=container_layout)
