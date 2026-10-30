from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import numpy as np

force_marker_visibility = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.cursors_visibility", "force_marker_visibility")

get_freq_display_unit = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.sweep_window.sweep_utils.sweep_utils", "get_freq_display_unit")

force_marker_visibility, force_marker_visibility_2 = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.cursors_visibility", "force_marker_visibility", "force_marker_visibility_2")

def _cursor_init_xy(line, freqs, freq_div, fallback_y=0.0):
    """Return (x, y) for the initial cursor dot placement.

    VNA edge points (indices 0-1) can carry extreme artefact values that land
    outside the visible ylim, making the dot invisible.  Start at index 2
    (the first reliable point) so the dot is always visible on screen.
    """
    if line is None or freqs is None or len(freqs) < 3:
        x0 = (freqs[0] / freq_div) if (freqs is not None and len(freqs)) else 0.0
        return x0, fallback_y
    ydata = line.get_ydata()
    idx = 2 if len(ydata) > 2 else 0
    y = float(ydata[idx]) if np.isfinite(ydata[idx]) else fallback_y
    x = freqs[idx] / freq_div
    return x, y

def enable_cursor_picking(self, radius=5):
    """Make the window's current cursors draggable with the mouse.

    The panels register ``pick_event`` handlers once, on the original cursor
    artists; every recreation here (and in ``force_marker_visibility``) must
    give the new artists a picker again or dragging dies after the first sweep.
    """
    for name in ("cursor_left", "cursor_left_2", "cursor_right", "cursor_right_2"):
        cursor = getattr(self, name, None)
        if cursor is not None:
            try:
                cursor.set_picker(radius)
            except Exception as e:
                logging.debug(f"[enable_cursor_picking] {name}: {e}")


def recreate_cursors_for_new_plots(self, graph_type_1, graph_type_2, marker_color_left, marker_color_right,
    marker2_color_left, marker2_color_right, marker1_size_left, marker1_size_right, marker2_size_left, marker2_size_right,
    panels=("left", "right")):
    """Recreate cursors when the plot type changes.

    ``panels`` names the rebuilt panels; the cursors, wrappers and slider
    callbacks of any other panel are left as they are.
    """

    do_left = "left" in panels
    do_right = "right" in panels

    try:
        logging.info("[graphics_window._recreate_cursors_for_new_plots] Recreating cursors for plot type changes (%s)", ", ".join(panels))

        # Clear any existing wrapper functions
        wrapper_names = []
        if do_left:
            wrapper_names += [("update_cursor", "_original_update_cursor"),
                              ("update_cursor_2", "_original_update_cursor_2")]
        if do_right:
            wrapper_names += [("update_right_cursor", "_original_update_right_cursor"),
                              ("update_right_cursor_2", "_original_update_right_cursor_2")]
        for public, original in wrapper_names:
            if hasattr(self, original):
                setattr(self, public, getattr(self, original))
                delattr(self, original)

        # Remove existing cursors from axes
        cursor_names = []
        if do_left:
            cursor_names += ["cursor_left", "cursor_left_2"]
        if do_right:
            cursor_names += ["cursor_right", "cursor_right_2"]
        for name in cursor_names:
            cursor = getattr(self, name, None)
            if cursor:
                try:
                    cursor.remove()
                except Exception:
                    pass
                setattr(self, name, None)

        # Create new cursors at position (0,0) - they will be positioned correctly later
        # Make them invisible initially to avoid the "fixed cursor" problem

        freq_div, _ = get_freq_display_unit(self)

        if not do_left:
            pass
        elif graph_type_1 == "Smith Diagram":
            if hasattr(self, 'ax_left') and self.ax_left:
                self.cursor_left = self.ax_left.plot(self.s11.real[0], self.s11.imag[0], 'o', color=marker_color_left, markersize=marker1_size_left, 
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

                self.cursor_left_2 = self.ax_left.plot(self.s11.real[0], self.s11.imag[0], 'o', color=marker2_color_left, markersize=marker2_size_left, 
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_1 == "Magnitude":
            if hasattr(self, 'ax_left') and self.ax_left:
                _x0_left_mag, _y0_left_mag = _cursor_init_xy(self.line_left if hasattr(self, 'line_left') else None, self.freqs, freq_div, np.abs(self.s11[0]))
                self.cursor_left = self.ax_left.plot(_x0_left_mag, _y0_left_mag, 'o', color=marker_color_left, markersize=marker1_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

                self.cursor_left_2 = self.ax_left.plot(_x0_left_mag, _y0_left_mag, 'o', color=marker2_color_left, markersize=marker2_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_1 == "Phase":
            if hasattr(self, 'ax_left') and self.ax_left:
                _x0_left, _y0_left = _cursor_init_xy(self.line_left if hasattr(self, 'line_left') else None, self.freqs, freq_div)
                self.cursor_left = self.ax_left.plot(_x0_left, _y0_left, 'o', color=marker_color_left, markersize=marker1_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]
                self.cursor_left_2 = self.ax_left.plot(_x0_left, _y0_left, 'o', color=marker2_color_left, markersize=marker2_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_1 in ("Real", "Imaginary", "VSWR"):
            if hasattr(self, 'ax_left') and self.ax_left:
                _x0_left, _y0_left = _cursor_init_xy(self.line_left if hasattr(self, 'line_left') else None, self.freqs, freq_div)
                self.cursor_left = self.ax_left.plot(_x0_left, _y0_left, 'o', color=marker_color_left, markersize=marker1_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]
                self.cursor_left_2 = self.ax_left.plot(_x0_left, _y0_left, 'o', color=marker2_color_left, markersize=marker2_size_left,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        if not do_right:
            pass
        elif graph_type_2 == "Smith Diagram":
            if hasattr(self, 'ax_right') and self.ax_right:
                self.cursor_right = self.ax_right.plot(self.s11.real[0], self.s11.imag[0], 'o', color=marker_color_right, markersize=marker1_size_right, 
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

                self.cursor_right_2 = self.ax_right.plot(self.s11.real[0], self.s11.imag[0], 'o', color=marker2_color_right, markersize=marker2_size_right, 
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_2 == "Magnitude":
            if hasattr(self, 'ax_right') and self.ax_right:
                _x0_right_mag, _y0_right_mag = _cursor_init_xy(self.line_right if hasattr(self, 'line_right') else None, self.freqs, freq_div, np.abs(self.s11[0]))
                self.cursor_right = self.ax_right.plot(_x0_right_mag, _y0_right_mag, 'o', color=marker_color_right, markersize=marker1_size_right,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

                self.cursor_right_2 = self.ax_right.plot(_x0_right_mag, _y0_right_mag, 'o', color=marker2_color_right, markersize=marker2_size_right,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_2 == "Phase":
            if hasattr(self, 'ax_right') and self.ax_right:
                _x0_right, _y0_right = _cursor_init_xy(self.line_right if hasattr(self, 'line_right') else None, self.freqs, freq_div)
                self.cursor_right = self.ax_right.plot(_x0_right, _y0_right, 'o', color=marker_color_right, markersize=marker1_size_right,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]
                self.cursor_right_2 = self.ax_right.plot(_x0_right, _y0_right, 'o', color=marker2_color_right, markersize=marker2_size_right,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]

        elif graph_type_2 in ("Real", "Imaginary", "VSWR"):
            if hasattr(self, 'ax_right') and self.ax_right:
                _x0_right, _y0_right = _cursor_init_xy(self.line_right if hasattr(self, 'line_right') else None, self.freqs, freq_div)
                self.cursor_right = self.ax_right.plot(_x0_right, _y0_right, 'o', color=marker_color_right, markersize=marker1_size_right,
                                                    markeredgecolor='darkred', markeredgewidth=2, visible=False)[0]
                self.cursor_right_2 = self.ax_right.plot(_x0_right, _y0_right, 'o', color=marker2_color_right, markersize=marker2_size_right,
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
            marker1_size_left=marker1_size_left, marker1_size_right=marker1_size_right, panels=panels)

        force_marker_visibility_2(self, marker_color_left=marker2_color_left, marker_color_right=marker2_color_right,
            marker_size_left=marker2_size_left, marker_size_right=marker2_size_right, panels=panels)

        enable_cursor_picking(self)

        if not do_left:
            pass
        elif self.show_graphic1_marker1 and not self.show_graphic1_marker2:
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

        if not do_right:
            pass
        elif self.show_graphic2_marker1 and not self.show_graphic2_marker2:
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