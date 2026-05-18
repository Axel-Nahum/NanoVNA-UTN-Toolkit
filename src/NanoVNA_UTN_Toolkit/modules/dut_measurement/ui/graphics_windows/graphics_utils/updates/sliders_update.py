import logging
import sys

from PySide6.QtCore import QTimer

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.panels_utils import _clear_marker_fields_only
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ---------------------------------------------------------------------------------------------------------------------------------------- #

def update_slider_ranges(self):
    """Update slider ranges and steps to match the current sweep data."""
    if not hasattr(self, 'freqs') or self.freqs is None or len(self.freqs) == 0:
        logging.warning("[graphics_window._update_slider_ranges] No frequency data available, cannot update sliders")
        return
        
    try:
        num_points = len(self.freqs)
        max_index = num_points - 1
        middle_index = max_index // 2
        
        logging.info(f"[graphics_window._update_slider_ranges] Updating sliders for {num_points} frequency points (indices 0 to {max_index})")
        logging.info(f"[graphics_window._update_slider_ranges] Frequency range: {self.freqs[0]/1e6:.3f} - {self.freqs[-1]/1e6:.3f} MHz")
        
        # Update left slider range if it exists and make it visible
        if hasattr(self, 'slider_left') and self.slider_left:
            try:
                # Update slider range to match frequency data indices
                self.slider_left.valmin = 0
                self.slider_left.valmax = max_index
                self.slider_left.valstep = 1
                
                # Set slider to middle position
                self.slider_left.set_val(middle_index)
                
                # Make sure the slider is visible and active
                if hasattr(self.slider_left, 'ax'):
                    self.slider_left.ax.set_visible(True)
                if hasattr(self.slider_left, 'set_active'):
                    self.slider_left.set_active(True)
                
                logging.info(f"[graphics_window._update_slider_ranges] Left slider updated: range 0-{max_index}, positioned at index {middle_index} ({self.freqs[middle_index]/1e6:.3f} MHz)")
            except Exception as e:
                logging.warning(f"[graphics_window._update_slider_ranges] Could not update left slider: {e}")
        
        # Update right slider range if it exists and make it visible
        if hasattr(self, 'slider_right') and self.slider_right:
            try:
                # Update slider range to match frequency data indices  
                self.slider_right.valmin = 0
                self.slider_right.valmax = max_index
                self.slider_right.valstep = 1
                
                # Set slider to middle position
                self.slider_right.set_val(middle_index)
                
                # Make sure the slider is visible and active
                if hasattr(self.slider_right, 'ax'):
                    self.slider_right.ax.set_visible(True)
                if hasattr(self.slider_right, 'set_active'):
                    self.slider_right.set_active(True)
                
                logging.info(f"[graphics_window._update_slider_ranges] Right slider updated: range 0-{max_index}, positioned at index {middle_index} ({self.freqs[middle_index]/1e6:.3f} MHz)")
            except Exception as e:
                logging.warning(f"[graphics_window._update_slider_ranges] Could not update right slider: {e}")

        # Force canvas redraw to show updated markers
        if hasattr(self, 'canvas_left') and self.canvas_left:
            self.canvas_left.draw_idle()
        if hasattr(self, 'canvas_right') and self.canvas_right:
            self.canvas_right.draw_idle()
                
        logging.info("[graphics_window._update_slider_ranges] Slider ranges updated successfully")
        
    except Exception as e:
        logging.error(f"[graphics_window._update_slider_ranges] Error updating slider ranges: {e}")

def reset_sliders_and_markers_for_graph_change(self):
    """Reset sliders and markers to leftmost position specifically for graph type changes."""
    try:
        logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Resetting sliders and markers for graph change")
        
        # Reset slider positions to leftmost position (index 0)
        if hasattr(self, 'slider_left') and self.slider_left:
            try:
                self.slider_left.set_val(0)
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Reset left slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Could not reset left slider: {e}")

        if hasattr(self, 'slider_left_2') and self.slider_left_2:
            try:
                self.slider_left_2.set_val(0)
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Reset left slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Could not reset left slider: {e}")
        
        if hasattr(self, 'slider_right') and self.slider_right:
            try:
                self.slider_right.set_val(0)
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Reset right slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Could not reset right slider: {e}")
        if hasattr(self, 'slider_right_2') and self.slider_right_2:
            try:
                self.slider_right_2.set_val(0)
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Reset right slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Could not reset right slider: {e}")
        
        # Clear marker information fields
        _clear_marker_fields_only(self)
        
        # Force cursor position updates to leftmost position (index 0)
        if hasattr(self, 'update_cursor') and callable(self.update_cursor):
            try:
                self.update_cursor(0)
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Updated left cursor to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Could not update left cursor: {e}")
        if hasattr(self, 'update_cursor_2') and callable(self.update_cursor_2):
            try:
                self.update_cursor_2(0)
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Updated left cursor to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Could not update left cursor: {e}")
        
        if hasattr(self, 'update_right_cursor') and callable(self.update_right_cursor):
            try:
                self.update_right_cursor(0)
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Updated right cursor to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Could not update right cursor: {e}")
        if hasattr(self, 'update_right_cursor_2') and callable(self.update_right_cursor_2):
            try:
                self.update_right_cursor_2(0)
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Updated right cursor to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Could not update right cursor: {e}")
        
        
        # Make cursors visible
        if hasattr(self, 'cursor_left') and self.cursor_left:
            self.cursor_left.set_visible(True)
        if hasattr(self, 'cursor_left_2') and self.cursor_left_2:
            self.cursor_left_2.set_visible(True)
        if hasattr(self, 'cursor_right') and self.cursor_right:
            self.cursor_right.set_visible(True)
        if hasattr(self, 'cursor_right_2') and self.cursor_right_2:
            self.cursor_right_2.set_visible(True)
        
        # Force marker information update after everything is set up (for graph changes)
        def force_cursor_info_update_graph_change():
            try:
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Starting forced cursor info update")
                
                # Ensure sliders are at position 0 first
                if hasattr(self, 'slider_left') and self.slider_left:
                    try:
                        self.slider_left.set_val(0)
                        logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Ensured left slider at position 0")
                    except Exception as e:
                        logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Could not set left slider: {e}")

                if hasattr(self, 'slider_left_2') and self.slider_left_2:
                    try:
                        self.slider_left_2.set_val(0)
                        logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Ensured left slider at position 0")
                    except Exception as e:
                        logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Could not set left slider: {e}")
                
                if hasattr(self, 'slider_right') and self.slider_right:
                    try:
                        self.slider_right.set_val(0)
                        logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Ensured right slider at position 0")
                    except Exception as e:
                        logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Could not set right slider: {e}")

                if hasattr(self, 'slider_right_2') and self.slider_right_2:
                    try:
                        self.slider_right_2.set_val(0)
                        logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Ensured right slider at position 0")
                    except Exception as e:
                        logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Could not set right slider: {e}")
                
                # Force cursor information update
                if hasattr(self, 'update_cursor') and callable(self.update_cursor):
                    try:
                        self.update_cursor(0)
                        logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Updated left cursor info to index 0")
                    except Exception as e:
                        logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Error updating left cursor: {e}")

                if hasattr(self, 'update_cursor_2') and callable(self.update_cursor_2):
                    try:
                        self.update_cursor_2(0)
                        logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Updated left cursor info to index 0")
                    except Exception as e:
                        logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Error updating left cursor: {e}")
                
                if hasattr(self, 'update_right_cursor_2') and callable(self.update_right_cursor_2):
                    try:
                        self.update_right_cursor_2(0)
                        logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Updated right cursor info to index 0")
                    except Exception as e:
                        logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Error updating right cursor: {e}")
                
                # Force canvas redraw to ensure visual update
                if hasattr(self, 'canvas_left') and self.canvas_left:
                    self.canvas_left.draw()
                if hasattr(self, 'canvas_right') and self.canvas_right:
                    self.canvas_right.draw()
                
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Cursor info update completed")
                    
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Error in delayed cursor update: {e}")
        
        # Execute the delayed update after 150ms for graph changes (increased delay)
        QTimer.singleShot(150, force_cursor_info_update_graph_change)
        
        logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] Sliders and markers reset successfully")
        
    except Exception as e:
        logging.error(f"[graphics_window._reset_sliders_and_markers_for_graph_change] Error resetting sliders and markers: {e}")

def left_slider_moved(self, val):
    if self.markers_locked:
        if self.slider_right.val != val:
            self.slider_right.set_val(val)
            self.update_right_cursor(val)

def right_slider_moved(self, val):
    if self.markers_locked:
        if self.slider_left.val != val:
            self.slider_left.set_val(val)
            self.update_cursor(val)

def left_slider_moved_2(self, val):
    if self.markers_locked:
        if self.slider_right_2.val != val:
            self.slider_right_2.set_val(val)
            self.update_right_cursor_2(val)

def right_slider_moved_2(self, val):
    if self.markers_locked:
        if self.slider_left_2.val != val:
            self.slider_left_2.set_val(val)
            self.update_cursor_2(val)