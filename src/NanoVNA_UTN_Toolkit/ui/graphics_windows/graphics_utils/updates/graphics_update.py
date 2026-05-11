import logging
import sys
import os

from pathlib import Path

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.load_graph_config.load_graph_config import load_graph_configuration
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

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

            # --- Determine which data to plot ---
            s_data_left = self.s11 if s_param_tab1 == "S11" else self.s21
            s_data_right = self.s11 if s_param_tab2 == "S11" else self.s21

            # --- Clear existing plots ---
            self.ax_left.clear()
            self.ax_right.clear()

            # --- Recreate left panel plot ---
            logging.info(f"[graphics_window.update_plots_with_new_data] Recreating left plot: {graph_type_tab1} - {s_param_tab1}")
            unit_left = self.get_graph_unit(1)
    
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

            self._recreate_single_plot(
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
                cursor_graph_2=self.cursor_left_2
            )

            # --- Recreate right panel plot ---
            logging.info(f"[graphics_window.update_plots_with_new_data] Recreating right plot: {graph_type_tab2} - {s_param_tab2}")
            unit_right = self.get_graph_unit(2)
            self._recreate_single_plot(
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
                cursor_graph_2=self.cursor_right_2
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
                self.toggle_marker_visibility(0, self.show_graphic1_marker1)
                self.toggle_marker2_visibility(0, self.show_graphic1_marker2)

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

            self._recreate_cursors_for_new_plots(
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
                self._reset_sliders_and_markers_for_graph_change()
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