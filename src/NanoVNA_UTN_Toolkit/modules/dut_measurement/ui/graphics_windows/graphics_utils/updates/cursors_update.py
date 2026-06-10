from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import numpy as np

force_marker_visibility = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.cursors_visibility", "force_marker_visibility")

force_marker_visibility, force_marker_visibility_2 = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.cursors_visibility", "force_marker_visibility", "force_marker_visibility_2")

def recreate_cursors_for_new_plots(self, graph_type_1, graph_type_2, marker_color_left, marker_color_right, 
    marker2_color_left, marker2_color_right, marker1_size_left, marker1_size_right, marker2_size_left, marker2_size_right):
    """Recreate cursors when the plot type changes."""

    try:
        logging.info("[graphics_window._recreate_cursors_for_new_plots] Recreating cursors for plot type changes")
        
        # Clear any existing wrapper functions
        if hasattr(self, '_original_update_cursor'):
            self.update_cursor = self._original_update_cursor
            delattr(self, '_original_update_cursor')
        if hasattr(self, '_original_update_cursor_2'):
            self.update_cursor_2 = self._original_update_cursor_2
            delattr(self, '_original_update_cursor_2')
        if hasattr(self, '_original_update_right_cursor'):
            self.update_right_cursor = self._original_update_right_cursor
            delattr(self, '_original_update_right_cursor')
        if hasattr(self, '_original_update_right_cursor_2'):
            self.update_right_cursor_2 = self._original_update_right_cursor_2
            delattr(self, '_original_update_right_cursor_2')
        
        # Remove existing cursors from axes
        if hasattr(self, 'cursor_left') and self.cursor_left:
            try:
                self.cursor_left.remove()
            except:
                pass
            self.cursor_left = None

        if hasattr(self, 'cursor_left_2') and self.cursor_left_2:
            try:
                self.cursor_left_2.remove()
            except:
                pass
            self.cursor_left_2 = None
            
        if hasattr(self, 'cursor_right') and self.cursor_right:
            try:
                self.cursor_right.remove()
            except:
                pass
            self.cursor_right = None

        if hasattr(self, 'cursor_right_2') and self.cursor_right_2:
            try:
                self.cursor_right_2.remove()
            except:
                pass
            self.cursor_right_2 = None
        
        # Create new cursors at position (0,0) - they will be positioned correctly later
        # Make them invisible initially to avoid the "fixed cursor" problem

        if graph_type_1 == "Smith Diagram":
            if hasattr(self, 'ax_left') and self.ax_left:
                self.cursor_left = self.ax_left.plot(self.s11.real[0], self.s11.imag[0], 'o', color=marker_color_left, markersize=marker1_size_left, 
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

                self.cursor_left_2 = self.ax_left.plot(self.s11.real[0], self.s11.imag[0], 'o', color=marker2_color_left, markersize=marker2_size_left, 
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_1 == "Magnitude":
            if hasattr(self, 'ax_left') and self.ax_left:
                _y0_left_mag = self.line_left.get_ydata()[0] if (hasattr(self, 'line_left') and self.line_left is not None) else np.abs(self.s11[0])
                self.cursor_left = self.ax_left.plot(self.freqs[0] / 1e6, _y0_left_mag, 'o', color=marker_color_left, markersize=marker1_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

                self.cursor_left_2 = self.ax_left.plot(self.freqs[0] / 1e6, _y0_left_mag, 'o', color=marker2_color_left, markersize=marker2_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_1 == "Phase":
            if hasattr(self, 'ax_left') and self.ax_left:
                _y0_left = self.line_left.get_ydata()[0] if (hasattr(self, 'line_left') and self.line_left is not None) else 0
                self.cursor_left = self.ax_left.plot(self.freqs[0] / 1e6, _y0_left, 'o', color=marker_color_left, markersize=marker1_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]
                self.cursor_left_2 = self.ax_left.plot(self.freqs[0] / 1e6, _y0_left, 'o', color=marker2_color_left, markersize=marker2_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        if graph_type_2 == "Smith Diagram":
            if hasattr(self, 'ax_right') and self.ax_right:
                self.cursor_right = self.ax_right.plot(self.s11.real[0], self.s11.imag[0], 'o', color=marker_color_right, markersize=marker1_size_right, 
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

                self.cursor_right_2 = self.ax_right.plot(self.s11.real[0], self.s11.imag[0], 'o', color=marker2_color_right, markersize=marker2_size_right, 
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_2 == "Magnitude":
            if hasattr(self, 'ax_right') and self.ax_right:
                _y0_right_mag = self.line_right.get_ydata()[0] if (hasattr(self, 'line_right') and self.line_right is not None) else np.abs(self.s11[0])
                self.cursor_right = self.ax_right.plot(self.freqs[0] / 1e6, _y0_right_mag, 'o', color=marker_color_right, markersize=marker1_size_right,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

                self.cursor_right_2 = self.ax_right.plot(self.freqs[0] / 1e6, _y0_right_mag, 'o', color=marker2_color_right, markersize=marker2_size_right,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_2 == "Phase":
            if hasattr(self, 'ax_right') and self.ax_right:
                _y0_right = self.line_right.get_ydata()[0] if (hasattr(self, 'line_right') and self.line_right is not None) else 0
                self.cursor_right = self.ax_right.plot(self.freqs[0] / 1e6, _y0_right, 'o', color=marker_color_right, markersize=marker1_size_right,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]
                self.cursor_right_2 = self.ax_right.plot(self.freqs[0] / 1e6, _y0_right, 'o', color=marker2_color_right, markersize=marker2_size_right,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]
        
        # Update markers list with new cursor references
        if hasattr(self, 'markers') and self.markers:
            if len(self.markers) >= 1 and self.markers[0]:
                self.markers[0]['cursor'] = self.cursor_left
            if len(self.markers) >= 1 and self.markers[0]:
                self.markers[0]['cursor_2'] = self.cursor_left_2
            if len(self.markers) >= 2 and self.markers[1]:
                self.markers[1]['cursor'] = self.cursor_right
            if len(self.markers) >= 2 and self.markers[1]:
                self.markers[1]['cursor_2'] = self.cursor_right_2

        # Force marker visibility setup to create the wrapper functions again
        force_marker_visibility(self, marker_color_left=marker_color_left, marker_color_right=marker_color_right, 
            marker1_size_left=marker1_size_left, marker1_size_right=marker1_size_right)

        force_marker_visibility_2(self, marker_color_left=marker2_color_left, marker_color_right=marker2_color_right,
            marker_size_left=marker2_size_left, marker_size_right=marker2_size_right)

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

        logging.info("[graphics_window._recreate_cursors_for_new_plots] Cursors recreated successfully")
        
    except Exception as e:
        logging.error(f"[graphics_window._recreate_cursors_for_new_plots] Error recreating cursors: {e}")