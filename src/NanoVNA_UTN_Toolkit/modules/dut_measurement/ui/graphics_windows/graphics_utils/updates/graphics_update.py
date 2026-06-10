from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys
import os
import numpy as np

from pathlib import Path

load_graph_configuration = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.load_graph_config.load_graph_config", "load_graph_configuration")

# Import get_settings 

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

recreate_cursors_for_new_plots = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.cursors_update", "recreate_cursors_for_new_plots")

reset_sliders_and_markers_for_graph_change = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.sliders_update", "reset_sliders_and_markers_for_graph_change")

get_graph_unit = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.db_unit.db_unit", "get_graph_unit")

toggle_marker_visibility, toggle_marker2_visibility = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.cursors_visibility", "toggle_marker_visibility", "toggle_marker2_visibility")

read_auto_scale_data = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.auto_scale.auto_scale", "read_auto_scale_data")

# ------------------------------------------------------------------------------------------------------------------------------ #

def recreate_single_plot(self, ax, fig, s_data, freqs, graph_type, s_param, 
                            tracecolor, markercolor, background_color_graphics, text_color, axis_color, linewidth, markersize,
                            unit="dB", cursor_graph=None, cursor_graph_2 = None, ax_type="left", unit_mode="dB"):
    
    # ----------------------------------------------------
    # Plot Manager settings
    # ----------------------------------------------------

    self.settings = get_settings(
        "INI/dut_measurement/plot_manager/plot_manager.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/plot_manager/plot_manager.ini",
        Path(__file__).resolve()
    )

    # ----------------------------------------------------
    # Recreate plot based on graph type
    # ----------------------------------------------------

    """Recreate a single plot with new data."""
    try:
        from matplotlib.lines import Line2D

        # Load configuration for calibration settings
        settings_calibration = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )

        settings_calibration.setValue("Calibration/isImportDut", False)

        fig.patch.set_facecolor(f"{background_color_graphics}")
        ax.set_facecolor(f"{background_color_graphics}")

        if graph_type == "Smith Diagram":
            # Use consolidated Smith chart functionality
            from NanoVNA_UTN_Toolkit.utils.smith_chart_utils import SmithChartConfig, SmithChartBuilder
            
            # Create custom config to match original settings
            config = SmithChartConfig()
            config.background_color = background_color_graphics
            config.axis_color = axis_color
            config.text_color = axis_color
            config.trace_color = tracecolor
            config.linewidth = linewidth
            
            # Use builder to recreate Smith chart on existing axis
            builder = SmithChartBuilder(config)
            builder.ax = ax
            builder.fig = fig
            
            # Create network and draw Smith chart
            network = builder.create_network_from_data(freqs, s_data)
            builder.draw_base_smith_chart(network, draw_labels=True, show_legend=False)

            # Add legend
            builder.add_legend([s_param], colors=[tracecolor])
            
            # Update data line styles
            builder.update_data_line_styles(freqs, color=tracecolor, linewidth=linewidth)
            
            # Add starting point marker
            builder.add_start_point_marker(s_data, color=tracecolor)

            data_line = None
                    
        elif graph_type == "Magnitude":
            # Plot magnitude

            if unit == "dB":
                magnitude_db = 20 * np.log10(np.abs(s_data))
            elif unit == "Power ratio":
                magnitude_db = np.abs(s_data)**2
            elif unit == "times":
                magnitude_db = np.abs(s_data)

            cursor_graph.set_xdata([freqs[0] * 1e-6])
            cursor_graph.set_ydata([magnitude_db[0]])

            fig.canvas.draw_idle()

            cursor_x = cursor_graph.get_xdata()[0]
            cursor_y = cursor_graph.get_ydata()[0]

            logging.info(f"[Cursor] Frequency: {cursor_x:.6f} MHz, Magnitude: {cursor_y:.3f} {unit}")

            data_line, = ax.plot(freqs / 1e6, magnitude_db, color=tracecolor, linewidth=linewidth)

            ax.set_xlabel(rf"$\mathrm{{{self.measurement_ui_magnitude_x_axis}}}$", color=f"{text_color}")
            
            if unit == "dB":
                ax.set_ylabel(r"$%s\ \mathrm{[dB]}$" % s_param, color=text_color)
                ax.set_title(rf"${self.measurement_ui_magnitude_title.format(parameter=s_param, db_times=unit_mode)}$", color=text_color)
            else:
                ax.set_ylabel(r"$|%s|$" % s_param, color=f"{text_color}")
                ax.set_title(rf"${self.measurement_ui_magnitude_title.format(parameter=s_param, db_times=unit_mode)}$", color=text_color)

            # Set X-axis limits with margins to match actual frequency range of the sweep
            freq_start = freqs[0] / 1e6
            freq_end = freqs[-1] / 1e6
            freq_range = freq_end - freq_start
            margin = freq_range * 0.05  # 5% margin on each side
            ax.set_xlim(freq_start - margin, freq_end + margin)

            data_config = read_auto_scale_data(self)

            auto_scale_enabled_left = data_config[0]
            auto_scale_enable_right = data_config[1]
            ymin_left = data_config[2]
            ymax_left = data_config[3]
            ymin_right = data_config[4]
            ymax_right = data_config[5]

            if ax_type == "left":
                if auto_scale_enabled_left:
                    # Auto scale
                    y_min = np.min(magnitude_db)
                    y_max = np.max(magnitude_db)
                    y_range = y_max - y_min
                    y_margin = y_range * 0.05

                    ax.set_ylim(y_min - y_margin, y_max + y_margin)
                else:
                    ax.set_ylim(ymin_left, ymax_left)
            elif ax_type == "right":
                if auto_scale_enable_right:
                    # Auto scale
                    y_min = np.min(magnitude_db)
                    y_max = np.max(magnitude_db)
                    y_range = y_max - y_min
                    y_margin = y_range * 0.05

                    ax.set_ylim(y_min - y_margin, y_max + y_margin)
                else:
                    ax.set_ylim(ymin_right, ymax_right)

            ax.autoscale(False)

            ax.tick_params(axis='x', colors=f"{axis_color}")
            ax.tick_params(axis='y', colors=f"{axis_color}")

            for spine in ax.spines.values():
                spine.set_color(f"{axis_color}")

            current_state_grid = self.settings.value(f"grid/current_{ax_type}_state", False, type=bool)
                
            ax.grid(False, which='both', axis='both', color=f"{axis_color}", linestyle='--', linewidth=0.5, alpha=0.3, zorder=1)
            fig.canvas.draw_idle()

            ax.grid(current_state_grid)

        elif graph_type == "Phase":
            # Plot phase — unwrap then normalize to avoid ±180° oscillation
            phase_deg = np.degrees(np.unwrap(np.angle(s_data)))
            if np.mean(phase_deg) < -90:
                phase_deg += 360

            cursor_graph.set_xdata([freqs[0] * 1e-6])
            cursor_graph.set_ydata([phase_deg[0]])

            fig.canvas.draw_idle()

            data_line, = ax.plot(freqs / 1e6, phase_deg, color=tracecolor, linewidth=linewidth)

            ax.set_xlabel(rf"$\mathrm{{{self.measurement_ui_magnitude_x_axis}}}$", color=f"{text_color}")
            ax.set_ylabel(r"$\phi_{%s}\ [^\circ]$" % s_param, color=f"{text_color}")
            ax.set_title(rf"$\mathrm{{{self.measurement_ui_phase_title.format(parameter=s_param)}}}$", color=f"{text_color}")
            
            # Set X-axis limits with margins to match actual frequency range of the sweep
            freq_start = freqs[0] / 1e6
            freq_end = freqs[-1] / 1e6
            freq_range = freq_end - freq_start
            margin = freq_range * 0.05  # 5% margin on each side
            ax.set_xlim(freq_start - margin, freq_end + margin)

            data_config = read_auto_scale_data(self)

            auto_scale_enabled_left = data_config[0]
            auto_scale_enable_right = data_config[1]
            ymin_left = data_config[2]
            ymax_left = data_config[3]
            ymin_right = data_config[4]
            ymax_right = data_config[5]

            if ax_type == "left":
                if auto_scale_enabled_left:
                    # Auto scale
                    y_min = np.min(phase_deg)
                    y_max = np.max(phase_deg)
                    y_range = y_max - y_min
                    y_margin = y_range * 0.05

                    ax.set_ylim(y_min - y_margin, y_max + y_margin)
                else:
                    ax.set_ylim(ymin_left, ymax_left)
            elif ax_type == "right":
                if auto_scale_enable_right:
                    # Auto scale
                    y_min = np.min(phase_deg)
                    y_max = np.max(phase_deg)
                    y_range = y_max - y_min
                    y_margin = y_range * 0.05

                    ax.set_ylim(y_min - y_margin, y_max + y_margin)
                else:
                    ax.set_ylim(ymin_right, ymax_right)
            ax.autoscale(False)

            ax.tick_params(axis='x', colors=f"{axis_color}")
            ax.tick_params(axis='y', colors=f"{axis_color}")

            for spine in ax.spines.values():
                spine.set_color(f"{axis_color}")

            current_state_grid = self.settings.value(f"grid/current_{ax_type}_state", False, type=bool)
                
            ax.grid(current_state_grid, which='both', axis='both', color=f"{axis_color}", linestyle='--', linewidth=0.5, alpha=0.3, zorder=1)

            ax.grid(current_state_grid)

        elif graph_type == "VSWR":
            # Calculate and plot VSWR
            s_magnitude = np.abs(s_data)
            vswr = (1 + s_magnitude) / (1 - s_magnitude)
            ax.plot(freqs / 1e6, vswr, color=tracecolor, linewidth=linewidth)
            ax.set_xlabel('Frequency (MHz)')
            ax.set_ylabel('VSWR')
            ax.set_title(f'{s_param} VSWR')
            ax.grid(current_state_grid, which='both', axis='both', color=f"{axis_color}", linestyle='--', linewidth=0.5, alpha=0.3, zorder=1)

        # Set axis properties
        ax.tick_params(axis='both', which='major', labelsize=8)

        cursor_graph.set_zorder(10)
        ax.add_line(cursor_graph)

        cursor_graph_2.set_zorder(10)
        ax.add_line(cursor_graph_2)
        
        return data_line
    
    except Exception as e:
        logging.error(f"[graphics_window._recreate_single_plot] Error recreating plot: {e}")
        return None

def update_plots_with_new_data(self, skip_reset=False):
    """Update both plots with new sweep data."""
    try:
        logging.info("[graphics_window.update_plots_with_new_data] Updating plots with new sweep data")

        # --- Check if data exists ---
        if self.freqs is None or self.s11 is None or self.s21 is None:
            logging.warning("[graphics_window.update_plots_with_new_data] No data available for plotting")
            return

        logging.info(f"[graphics_window.update_plots_with_new_data] New data: {len(self.freqs)} frequency points")

        config = load_graph_configuration()

        graph_type_tab1 = config['graph_type_tab1']
        s_param_tab1 = config['s_param_tab1']

        graph_type_tab2 = config['graph_type_tab2']
        s_param_tab2 = config['s_param_tab2']

        trace_color1 = config['trace_color1']
        marker_color1 = config['marker_color1']
        marker2_color1 = config['marker2_color1']
        background_color1 = config['background_color1']
        text_color1 = config['text_color1']
        axis_color1 = config['axis_color1']
        trace_size1 = config['trace_size1']
        marker_size1 = config['marker_size1']
        marker2_size1 = config['marker2_size1']

        trace_color2 = config['trace_color2']
        marker_color2 = config['marker_color2']
        marker2_color2 = config['marker2_color2']
        background_color2 = config['background_color2']
        text_color2 = config['text_color2']
        axis_color2 = config['axis_color2']
        trace_size2 = config['trace_size2']
        marker_size2 = config['marker_size2']
        marker2_size2 = config['marker2_size2']

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        unit_left = settings.value("Graphic1/db_times", "dB")
        unit_right = settings.value("Graphic2/db_times", "dB")

        # --- Determine which data to plot ---
        s_data_left = self.s11 if s_param_tab1 == "S11" else self.s21
        s_data_right = self.s11 if s_param_tab2 == "S11" else self.s21

        # --- Clear existing plots ---
        self.ax_left.clear()
        self.ax_right.clear()

        # --- Recreate left panel plot ---
        logging.info(f"[graphics_window.update_plots_with_new_data] Recreating left plot: {graph_type_tab1} - {s_param_tab1}")
        unit_left = get_graph_unit(self, 1)

        # --- Clean up old slider event connections before redrawing 
        if hasattr(self, "slider_left") and self.slider_left is not None:
            try:
                self.slider_left.disconnect_events()
            except Exception as e:
                logging.debug(f"Failed to disconnect slider_left events: {e}")
        if hasattr(self, "slider_right") and self.slider_right is not None:
            try:
                self.slider_right.disconnect_events()
            except Exception as e:
                logging.debug(f"Failed to disconnect slider_right events: {e}")
        """if hasattr(self, "slider_left_2") and self.slider_left_2 is not None:
            try:
                self.slider_left_2.disconnect_events()
            except Exception as e:
                logging.debug(f"Failed to disconnect slider_left_2 events: {e}")
        if hasattr(self, "slider_right_2") and self.slider_right_2 is not None:
            try:
                self.slider_right_2.disconnect_events()
            except Exception as e:
                logging.debug(f"Failed to disconnect slider_right_2 events: {e}")"""

        self.line_left = recreate_single_plot(
            self,
            ax=self.ax_left,
            fig=self.fig_left,
            s_data=s_data_left,
            freqs=self.freqs,
            graph_type=graph_type_tab1,
            s_param=s_param_tab1,
            tracecolor=trace_color1,
            markercolor=marker_color1,
            background_color_graphics=background_color1,
            text_color=text_color1,
            axis_color=axis_color1,
            linewidth=trace_size1,
            markersize=marker_size1,
            unit=unit_left,
            cursor_graph=self.cursor_left,
            cursor_graph_2=self.cursor_left_2,
            ax_type="left",
            unit_mode=unit_left
        )

        # --- Recreate right panel plot ---
        logging.info(f"[graphics_window.update_plots_with_new_data] Recreating right plot: {graph_type_tab2} - {s_param_tab2} - {marker_color2}")
        #unit_right = get_graph_unit(self, 2)

        self.line_right = recreate_single_plot(
            self,
            ax=self.ax_right,
            fig=self.fig_right,
            s_data=s_data_right,
            freqs=self.freqs,
            graph_type=graph_type_tab2,
            s_param=s_param_tab2,
            tracecolor=trace_color2,
            markercolor=marker_color2,
            background_color_graphics=background_color2,
            text_color=text_color2,
            axis_color=axis_color2,
            linewidth=trace_size2,
            markersize=marker_size2,
            unit=unit_right,
            cursor_graph=self.cursor_right,
            cursor_graph_2=self.cursor_right_2,
            ax_type="right",
            unit_mode=unit_right
        )

        # --- Update slider data references ---
        logging.info("[graphics_window.update_plots_with_new_data] Updating cursor data references")
        if hasattr(self, 'update_left_data') and self.update_left_data:
            self.slider_left, self.slider_left_2 = self.update_left_data(
                s_data_left,
                self.freqs,
                self.slider_left,
                self.slider_left_2,
                self.canvas_left,
                self.fig_left,
                self.show_graphic1_marker1,
                self.show_graphic1_marker2,
                self.cursor_left,
                self.cursor_left_2,
                self.info_panel_left,
                self.info_panel_left_2
            )
            toggle_marker_visibility(self, 0, self.show_graphic1_marker1)
            toggle_marker2_visibility(self, 0, self.show_graphic1_marker2)

        if hasattr(self, 'update_right_data') and self.update_right_data:
            self.slider_right, self.slider_right_2 = self.update_right_data(
                s_data_right,
                self.freqs,
                self.slider_right,
                self.slider_right_2,
                self.canvas_right,
                self.fig_right,
                self.show_graphic2_marker1,
                self.show_graphic2_marker2,
                self.cursor_right,
                self.cursor_right_2,
                self.info_panel_right,
                self.info_panel_right_2
            )
        
        # --- Recreate cursors for new graph types ---
        logging.info("[graphics_window.update_plots_with_new_data] Recreating cursors for new graph types")

        if hasattr(self, 'freqs_edit_left') and self.freqs_edit_left:
            self.labels_left["freq"].editingFinished.connect(
                lambda: self.freqs_edit_left(self.slider_left)
            )

        if hasattr(self, 'freqs_edit_right') and self.freqs_edit_right:
            self.labels_right["freq"].editingFinished.connect(
                lambda: self.freqs_edit_right(self.slider_right)
            )

        if hasattr(self, 'freqs_edit_left_2') and callable(self.freqs_edit_left_2):
            self.labels_left_2["freq"].editingFinished.connect(
                lambda s=self.slider_left_2: self.freqs_edit_left_2(s)
            )

        if hasattr(self, 'freqs_edit_right_2') and self.freqs_edit_right_2:
            self.labels_right_2["freq"].editingFinished.connect(
                lambda: self.freqs_edit_right_2(self.slider_right_2)
            )

        recreate_cursors_for_new_plots(
            self,
            graph_type_1=graph_type_tab1,
            graph_type_2=graph_type_tab2,
            marker_color_left=marker_color1,
            marker_color_right=marker_color2,
            marker2_color_left=marker2_color1,
            marker2_color_right=marker2_color2,
            marker1_size_left=marker_size1,
            marker1_size_right=marker_size2,
            marker2_size_left=marker2_size1,
            marker2_size_right=marker2_size2
        )

        # --- Reset sliders and markers if not skipping ---
        if not skip_reset:
            logging.info("[graphics_window.update_plots_with_new_data] Resetting sliders and markers to initial position")
            reset_sliders_and_markers_for_graph_change(self)
        else:
            logging.info("[graphics_window.update_plots_with_new_data] Skipping reset - will be handled by sweep reset")

        if self.show_graphic1_marker1 and not self.show_graphic1_marker2:
            self.cursor_left.set_visible(True)
            self.cursor_left_2.set_visible(False)
        elif self.show_graphic1_marker2 and not self.show_graphic1_marker1:
            self.cursor_left.set_visible(False)
            self.cursor_left_2.set_visible(True)
        elif self.show_graphic1_marker1 and self.show_graphic1_marker2:
            self.cursor_left.set_visible(True)
            self.cursor_left_2.set_visible(True)
        elif not self.show_graphic1_marker1 and not self.show_graphic1_marker2:
            self.cursor_left.set_visible(False)
            self.cursor_left_2.set_visible(False)

        if self.show_graphic2_marker1 and not self.show_graphic2_marker2:
            self.cursor_right.set_visible(True)
            self.cursor_right_2.set_visible(False)
        elif self.show_graphic2_marker2 and not self.show_graphic2_marker1:
            self.cursor_right.set_visible(False)
            self.cursor_right_2.set_visible(True)
        elif self.show_graphic2_marker1 and self.show_graphic2_marker2:
            self.cursor_right.set_visible(True)
            self.cursor_right_2.set_visible(True)
        elif not self.show_graphic2_marker1 and not self.show_graphic2_marker2:
            self.cursor_right.set_visible(False)
            self.cursor_right_2.set_visible(False)

        # --- Force redraw ---
        self.canvas_left.draw()
        self.canvas_right.draw()

        logging.info("[graphics_window.update_plots_with_new_data] Plots updated successfully")

    except Exception as e:
        logging.error(f"[graphics_window.update_plots_with_new_data] Error updating plots: {e}")