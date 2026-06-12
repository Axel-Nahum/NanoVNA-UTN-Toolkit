"""
Smith Chart utilities for NanoVNA toolkit.

This module consolidates all Smith chart-related functionality that was previously
duplicated across multiple files (wizard_windows.py, graphics_window.py, graphics_utils.py, etc.).
"""

import logging
import numpy as np
import skrf as rf
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QSizePolicy
import matplotlib.pyplot as plt
from typing import Optional, Dict, Tuple, List, Any

plt.rcParams['mathtext.fontset'] = 'cm'   # Fuente Computer Modern
plt.rcParams['text.usetex'] = False     
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'    
plt.rcParams['mathtext.rm'] = 'serif'    


class SmithChartConfig:
    """Configuration class for Smith chart styling and behavior."""
    
    def __init__(self):
        # Default colors
        self.background_color = "white"
        self.axis_color = "black" 
        self.text_color = "black"
        self.trace_color = "blue"
        self.marker_color = "red"
        
        # Default styling
        self.linewidth = 2
        self.markersize = 6
        self.marker_visible = True
        self.marker_visible_2=False
        
        # Impedance
        self.z0 = 50
        
        # Center line styling
        self.center_line_color = "black"
        self.center_line_width = 1.1
        self.center_line_zorder = 10


class SmithChartBuilder:
    """Builder class for creating and customizing Smith charts."""
    
    def __init__(self, config=None):
        self.config = config if config else SmithChartConfig()
        self.ax: Optional[Any] = None
        self.fig: Optional[Any] = None
        self.canvas: Optional[FigureCanvas] = None
        self.network: Optional[rf.Network] = None
        
    def create_empty_network(self, start_freq, stop_freq, num_points):
        """Create an empty network for base Smith chart."""
        freqs = np.linspace(start_freq, stop_freq, num_points)
        s_data = np.zeros((len(freqs), 1, 1), dtype=complex)
        return rf.Network(frequency=freqs, s=s_data, z0=self.config.z0)
    
    def create_network_from_data(self, freqs, s_data):
        """Create network from frequency and S-parameter data."""
        if s_data.ndim == 1:
            # Convert 1D array to 3D for scikit-rf
            s_data = s_data[:, np.newaxis, np.newaxis]
        elif s_data.ndim == 2 and s_data.shape[1] == 1:
            # Convert 2D array to 3D for scikit-rf 
            s_data = s_data[:, :, np.newaxis]
        return rf.Network(frequency=freqs, s=s_data, z0=self.config.z0)
    
    def setup_figure(self, figsize=(5, 5), layout_params=None):
        """Setup matplotlib figure and axis for Smith chart."""
        if layout_params is None:
            layout_params = {'left': 0.2, 'right': 0.8, 'top': 0.8, 'bottom': 0.2}
        
        import logging
        logging.info(f"[SmithChartBuilder] Creating figure with figsize={figsize}")
            
        self.fig, self.ax = plt.subplots(figsize=figsize)
        self.fig.subplots_adjust(**layout_params)
        
        # Set background colors
        self.fig.patch.set_facecolor(self.config.background_color)
        self.ax.set_facecolor(self.config.background_color)
        
        return self.fig, self.ax
    
    def create_canvas(self):
        """Create Qt canvas for the figure."""
        if self.fig is None:
            raise ValueError("Figure must be created first using setup_figure()")
            
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return self.canvas
    
    def draw_base_smith_chart(self, network=None, draw_labels=True, show_legend=False):
        """Draw base Smith chart with reference circles and lines."""
        if self.ax is None:
            raise ValueError("Axis must be created first using setup_figure()")
            
        if network is None:
            # Create empty network for reference circles only
            network = self.create_empty_network(1e6, 1e9, 10)
            
        # Draw Smith chart base
        network.plot_s_smith(ax=self.ax, draw_labels=draw_labels, show_legend=show_legend)
        
        self._configure_smith_chart_appearance()

        self.ax.set_title(r"$\mathrm{Smith\ Diagram}$", 
                  fontsize=14,       
                  pad=30,           
                  color=self.config.text_color)
        
        return self.ax
    
    def _configure_smith_chart_appearance(self):
        """Apply consistent styling to Smith chart elements."""
        if self.ax is None:
            return
            
        # Configure text colors
        for text in self.ax.texts:
            text.set_color(self.config.text_color)
        
        # Configure patch colors (Smith chart circles and arcs)
        for patch in self.ax.patches:
            patch.set_edgecolor(self.config.axis_color)
            patch.set_facecolor("none")
        
        # Add center horizontal line
        self.ax.hlines(0, -1, 1, 
                      color=self.config.center_line_color, 
                      linewidth=self.config.center_line_width, 
                      zorder=self.config.center_line_zorder)
        
        # Remove ticks
        self.ax.set_xticks([])
        self.ax.set_yticks([])
    
    def plot_measurement_data(self, freqs, s_data, label=None, color=None, linewidth=None):
        """Plot measurement data on Smith chart."""
        if self.ax is None:
            raise ValueError("Axis must be created first using setup_figure()")
            
        color = color or self.config.trace_color
        linewidth = linewidth or self.config.linewidth
        
        # Create network and plot
        network = self.create_network_from_data(freqs, s_data)
        
        # Plot the data points directly on Smith chart
        self.ax.plot(np.real(s_data), np.imag(s_data), 'o-',
                    color=color, linewidth=linewidth, markersize=3,
                    label=label)
        
        return network
    
    def add_legend(self, labels, colors=None, location='lower left', bbox_anchor=(-0.13, 1.00)):
        """Add legend to Smith chart matching preview style."""
        if self.ax is None:
            return

        if colors is None:
            colors = [self.config.trace_color] * len(labels)

        def _latex_label(lbl):
            if len(lbl) >= 2 and lbl[0] == 'S' and lbl[1:].isdigit():
                return r"$S_{%s}$" % lbl[1:]
            return lbl

        latex_labels = [_latex_label(lbl) for lbl in labels]
        legend_lines = [Line2D([0], [0], color=color) for color in colors]
        legend = self.ax.legend(
            legend_lines, latex_labels,
            loc=location,
            bbox_to_anchor=bbox_anchor,
            borderaxespad=0,
            fontsize=10,
            facecolor="white",
            edgecolor="black",
            framealpha=1,
        )
        legend.set_draggable(True)
    
    def update_data_line_styles(self, freqs, color=None, linewidth=None):
        """Update styling of data lines that match frequency array."""
        if self.ax is None:
            return
            
        color = color or self.config.trace_color
        linewidth = linewidth or self.config.linewidth
        
        for line in self.ax.lines:
            try:
                xdata = line.get_xdata()
                # Check if this line contains actual measurement data
                if hasattr(xdata, '__len__') and hasattr(freqs, '__len__') and len(xdata) == len(freqs):
                    line.set_color(color)
                    line.set_linewidth(linewidth)
            except:
                # Some lines might not support these operations
                continue

        for patch in self.ax.patches:
            patch.set_edgecolor(self.config.axis_color)
            patch.set_facecolor("none")

        # Actualizar color de la línea central
        self.ax.hlines(
            0, -1, 1,
            color=self.config.axis_color,
            linewidth=self.config.center_line_width,
            zorder=self.config.center_line_zorder
        )
    
    def add_cursor_marker(self, visible=None, visible_2=None, color=None, color2=None, size=None):
        """Add cursor marker for interactive use."""
        if self.ax is None:
            return None
            
        visible = visible if visible is not None else self.config.marker_visible
        visible_2 = visible_2 if visible_2 is not None else self.config.marker_visible_2
        color = color or self.config.marker_color
        color2 = color2 or self.config.marker_color
        size = size or self.config.markersize
        
        cursor, = self.ax.plot([], [], 'o', markersize=size, color=color, visible=visible, zorder=10)
        cursor_2, = self.ax.plot([], [], 'o', markersize=size, color=color2, visible=visible_2, zorder=10)

        return cursor, cursor_2

    def add_start_point_marker(self, s_data, color=None):
        """Add a visual marker at the starting point of the trace."""
        if self.ax is None or s_data is None or len(s_data) == 0:
            return None
            
        start_point = s_data[0]
        marker_color = color or self.config.trace_color
        
        # Add starting point marker with distinctive styling
        start_marker = self.ax.plot(
            np.real(start_point), np.imag(start_point),
            marker='o', 
            markersize=self.config.markersize + 1,  # Slightly larger
            color=marker_color,
            markeredgecolor=marker_color,
            markeredgewidth=1.25,
            zorder=2,  # Below cursors but above trace
            linestyle='None',
            picker=False  # Not interactive
        )
        
        return start_marker[0] if start_marker else None

    def clear_and_redraw(self):
        """Clear axis and prepare for new plot."""
        if self.ax:
            self.ax.clear()
    
    def refresh_canvas(self):
        """Refresh the canvas display."""
        if self.canvas:
            self.canvas.draw()

class SmithChartManager:
    """High-level manager for Smith chart operations."""
    
    def __init__(self, config=None):
        self.config = config if config else SmithChartConfig()
        self.builder = SmithChartBuilder(self.config)
    
    def create_wizard_smith_chart(self, start_freq, stop_freq, num_points, 
                                 figsize=(5, 5), container_layout=None):
        """Create Smith chart for calibration wizard use."""
        # Setup figure
        fig, ax = self.builder.setup_figure(figsize=figsize)
        
        # Create empty base network
        network = self.builder.create_empty_network(start_freq, stop_freq, num_points)
        
        # Draw base Smith chart
        self.builder.draw_base_smith_chart(network, draw_labels=True, show_legend=False)
        
        # Create canvas
        canvas = self.builder.create_canvas()
        
        # Add to layout if provided
        if container_layout:
            container_layout.addWidget(canvas)
        
        return fig, ax, canvas
    
    def create_graphics_panel_smith_chart(self, s_data, freqs, s_param="S11",
                                        figsize=(5, 5), container_layout=None,
                                        trace_color=None, marker_color=None, marker2_color=None):
        """Create Smith chart for graphics panels."""
        # Setup figure
        fig, ax = self.builder.setup_figure(figsize=figsize)
        
        # Create network from data
        network = self.builder.create_network_from_data(freqs, s_data)
        
        # Draw base Smith chart
        self.builder.draw_base_smith_chart(network, draw_labels=True, show_legend=False)
        
        # Update line styles for data
        self.builder.update_data_line_styles(freqs, color=trace_color)
        
        # Add starting point marker
        self.builder.add_start_point_marker(s_data, color=trace_color)
        
        # Add legend
        self.builder.add_legend([s_param], colors=[trace_color or self.config.trace_color])
        
        # Add cursor marker
        cursor, cursor_2 = self.builder.add_cursor_marker(color=marker_color, color2=marker2_color)
        
        # Create canvas
        canvas = self.builder.create_canvas()
        
        # Add to layout if provided
        if container_layout:
            container_layout.addWidget(canvas)
        
        return fig, ax, canvas, cursor, cursor_2
    
    def update_wizard_measurement(self, ax, freqs, s11_data, standard_name, 
                                 canvas=None, color_map=None):
        """Update wizard Smith chart with new measurement."""
        if color_map is None:
            color_map = {'open': 'red', 'short': 'green', 'match': 'blue'}
        
        try:
            # Clear and redraw base
            ax.clear()
            
            # Get sweep configuration for base chart
            network_base = self.builder.create_empty_network(freqs[0], freqs[-1], len(freqs))
            network_base.plot_s_smith(ax=ax, draw_labels=True, show_legend=False)
            
            # Configure appearance
            self.builder.ax = ax  # Temporarily set for configuration
            self.builder._configure_smith_chart_appearance()
            
            # Plot measurement data
            color = color_map.get(standard_name.lower(), self.config.trace_color)
            ax.plot(np.real(s11_data), np.imag(s11_data), 'o-',
                   color=color, linewidth=self.config.linewidth, markersize=3)
            
            # Add starting point marker
            self.builder.add_start_point_marker(s11_data, color=color)
            
            # Add legend
            legend_line = Line2D([0], [0], color=color)
            ax.legend([legend_line], [rf"$\mathrm{{S11 - {standard_name}}}$"], 
                loc='upper left', bbox_to_anchor=(-0.17, 1.14))
            
            # Refresh canvas
            if canvas:
                canvas.draw()
                
            logging.info(f"[SmithChartUtils] Updated Smith chart for {standard_name}")
            
        except Exception as e:
            logging.error(f"[SmithChartUtils] Error updating measurement: {e}")
    
    def show_multiple_measurements(self, ax, measurements_dict, canvas=None, 
                                  color_map=None, start_freq=None, stop_freq=None, num_points=None):
        """Show multiple measurements on same Smith chart."""
        if color_map is None:
            color_map = {'open': 'red', 'short': 'green', 'match': 'blue'}
        
        try:
            # Clear and redraw base
            ax.clear()
            
            # Create base chart
            if start_freq and stop_freq and num_points:
                freqs_base = np.linspace(start_freq, stop_freq, num_points)
                network_base = self.builder.create_empty_network(start_freq, stop_freq, num_points)
            else:
                # Use first measurement for base
                first_measurement = next(iter(measurements_dict.values()))
                freqs_base, _ = first_measurement
                network_base = self.builder.create_empty_network(freqs_base[0], freqs_base[-1], len(freqs_base))
            
            network_base.plot_s_smith(ax=ax, draw_labels=True, show_legend=False)
            
            # Configure appearance
            self.builder.ax = ax  # Temporarily set for configuration
            self.builder._configure_smith_chart_appearance()
            
            # Plot each measurement
            legend_lines = []
            legend_labels = []
            
            for standard_name, (freqs, s11_data) in measurements_dict.items():
                color = color_map.get(standard_name.lower(), self.config.trace_color)
                ax.plot(np.real(s11_data), np.imag(s11_data), 'o-',
                       color=color, linewidth=self.config.linewidth, markersize=3)
                
                legend_lines.append(Line2D([0], [0], color=color))
                legend_labels.append(standard_name.upper())
            
            # Add legend for all measurements
            if legend_lines:
                ax.legend(legend_lines, legend_labels, 
                         loc='upper left', bbox_to_anchor=(-0.17, 1.14))
            
            # Refresh canvas
            if canvas:
                canvas.draw()
                
            logging.info(f"[SmithChartUtils] Displayed {len(measurements_dict)} measurements")
            
        except Exception as e:
            logging.error(f"[SmithChartUtils] Error showing multiple measurements: {e}")


# Convenience functions for common use cases
def create_simple_smith_chart(freqs, s_data, figsize=(5, 5), s_param="S11"):
    """Simple function to create a basic Smith chart."""
    manager = SmithChartManager()
    return manager.create_graphics_panel_smith_chart(s_data, freqs, s_param, figsize)

def update_smith_chart_measurement(ax, freqs, s_data, standard_name, canvas=None):
    """Simple function to update Smith chart with measurement."""
    manager = SmithChartManager()
    manager.update_wizard_measurement(ax, freqs, s_data, standard_name, canvas)

def create_wizard_smith_chart(start_freq, stop_freq, num_points, container_layout=None, figsize=(5, 5)):
    """Simple function to create Smith chart for wizard."""
    manager = SmithChartManager()
    return manager.create_wizard_smith_chart(start_freq, stop_freq, num_points, 
                                           figsize=figsize, container_layout=container_layout)
