import logging
import sys

from PySide6.QtCore import QTimer

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.reset.panels_utils import _clear_marker_fields_only
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.updates.sliders_update import update_slider_ranges
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# -------------------------------------------------------------------------------------------------------------------- #

def _reset_markers_after_sweep(self):
    """Reset markers and all marker-dependent information after a sweep completes."""
    logging.info("[graphics_window._reset_markers_after_sweep] Resetting markers after sweep completion")

    try:
        if self.cursor_left and getattr(self.cursor_left, "ax", None):
            fig = self.cursor_left.ax.get_figure() # type: ignore
            # continue normal update
        else:
            return  # cursor already removed or destroyed
    except Exception as e:
        logging.warning("[graphics_window._reset_markers_after_sweep] Skipped invalid cursor: %s", e)
    
    try:
        # Reset slider positions to leftmost position (index 0) if they exist
        if hasattr(self, 'slider_left') and self.slider_left:
            # Reset left slider to leftmost position
            try:
                self.slider_left.set_val(0)
                logging.info("[graphics_window._reset_markers_after_sweep] Reset left slider to index 0 (leftmost)")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not reset left slider: {e}")

        if hasattr(self, 'slider_left_2') and self.slider_left_2:
            # Reset left slider to leftmost position
            try:
                self.slider_left_2.set_val(0)
                logging.info("[graphics_window._reset_markers_after_sweep] Reset left slider_2 to index 0 (leftmost)")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not reset left slider: {e}")
        
        if hasattr(self, 'slider_right') and self.slider_right:
            # Reset right slider to leftmost position  
            try:
                self.slider_right.set_val(0)
                logging.info("[graphics_window._reset_markers_after_sweep] Reset right slider to index 0 (leftmost)")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not reset right slider: {e}")

        if hasattr(self, 'slider_right_2') and self.slider_right_2:
            # Reset right slider to leftmost position  
            try:
                self.slider_right_2.set_val(0)
                logging.info("[graphics_window._reset_markers_after_sweep] Reset right slider to index 0 (leftmost)")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not reset right slider: {e}")
        
        # Reset ONLY marker field information - NOT the graphs themselves
        _clear_marker_fields_only(self)
        
        # Update slider ranges to match the new sweep data
        update_slider_ranges(self)
        
        # Force cursor position updates if update functions exist
        if hasattr(self, 'update_cursor') and callable(self.update_cursor):
            try:
                # Always set cursor to leftmost position (index 0)
                self.update_cursor(0)
                logging.info("[graphics_window._reset_markers_after_sweep] Updated left cursor to index 0 (leftmost)")
                
                # Force cursor visibility and redraw after data update
                if hasattr(self, 'cursor_left') and self.cursor_left and self.show_graphic1_marker1:
                    self.cursor_left.set_visible(True)
                    if hasattr(self.cursor_left, 'get_data'):
                        x_data, y_data = self.cursor_left.get_data()
                        logging.info(f"[graphics_window._reset_markers_after_sweep] Left cursor after update: x={x_data}, y={y_data}")

            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not update left cursor: {e}")

        if hasattr(self, 'update_cursor_2') and callable(self.update_cursor_2):
            try:
                # Always set cursor to leftmost position (index 0)
                self.update_cursor_2(0)
                logging.info("[graphics_window._reset_markers_after_sweep] Updated left cursor to index 0 (leftmost)")
                
                # Force cursor visibility and redraw after data update
                if hasattr(self, 'cursor_left_2') and self.cursor_left_2 and self.show_graphic1_marker2:
                    self.cursor_left_2.set_visible(True)
                    if hasattr(self.cursor_left_2, 'get_data'):
                        x_data, y_data = self.cursor_left_2.get_data()
                        logging.info(f"[graphics_window._reset_markers_after_sweep] Left cursor after update 2: x={x_data}, y={y_data}")
                    
            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not update left cursor: {e}")
        
        if hasattr(self, 'update_right_cursor') and callable(self.update_right_cursor):
            try:
                # Always set cursor to leftmost position (index 0)
                self.update_right_cursor(0)
                logging.info("[graphics_window._reset_markers_after_sweep] Updated right cursor to index 0 (leftmost)")
                
                # Force cursor visibility and redraw after data update
                if hasattr(self, 'cursor_right') and self.cursor_right and self.show_graphic2_marker1:
                    self.cursor_right.set_visible(True)
                    if hasattr(self.cursor_right, 'get_data'):
                        x_data, y_data = self.cursor_right.get_data()
                        logging.info(f"[graphics_window._reset_markers_after_sweep] Right cursor after update: x={x_data}, y={y_data}")
                    
            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not update right cursor: {e}")

        if hasattr(self, 'update_right_cursor_2') and callable(self.update_right_cursor_2):
            try:
                # Always set cursor to leftmost position (index 0)
                self.update_right_cursor_2(0)
                logging.info("[graphics_window._reset_markers_after_sweep] Updated right cursor_2 to index 0 (leftmost)")
                
                # Force cursor visibility and redraw after data update
                if hasattr(self, 'cursor_right_2') and self.cursor_right_2 and self.show_graphic2_marker2:
                    self.cursor_right_2.set_visible(True)
                    if hasattr(self.cursor_right_2, 'get_data'):
                        x_data, y_data = self.cursor_right_2.get_data()
                        logging.info(f"[graphics_window._reset_markers_after_sweep] Right cursor after update: x={x_data}, y={y_data}")
                    
            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not update right cursor: {e}")
                
        # Final forced redraw with explicit visibility check
        try:
            # Force canvas redraw to show the cursors with their new data
            if hasattr(self, 'canvas_left') and self.canvas_left:
                self.canvas_left.draw()  # Use draw() instead of draw_idle() for immediate effect
                logging.info("[graphics_window._reset_markers_after_sweep] Forced left canvas redraw")
            if hasattr(self, 'canvas_right') and self.canvas_right:
                self.canvas_right.draw()  # Use draw() instead of draw_idle() for immediate effect
                logging.info("[graphics_window._reset_markers_after_sweep] Forced right canvas redraw")
                
        except Exception as e:
            logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not force canvas redraw: {e}")
                
        # Force marker information update after everything is set up
        # Use QTimer to ensure all cursor recreation is complete before updating info
        def force_cursor_info_update():
            try:
                if hasattr(self, 'update_cursor') and callable(self.update_cursor):
                    self.update_cursor(0)
                    logging.info("[graphics_window._reset_markers_after_sweep] DELAYED: Updated left cursor info to index 0")

                if hasattr(self, 'update_cursor_2') and callable(self.update_cursor_2):
                    self.update_cursor_2(0)
                    logging.info("[graphics_window._reset_markers_after_sweep] DELAYED: Updated left 2 cursor info to index 0")
                
                if hasattr(self, 'update_right_cursor') and callable(self.update_right_cursor):
                    self.update_right_cursor(0)
                    logging.info("[graphics_window._reset_markers_after_sweep] DELAYED: Updated right cursor info to index 0")

                if hasattr(self, 'update_right_cursor_2') and callable(self.update_right_cursor_2):
                    self.update_right_cursor_2(0)
                    logging.info("[graphics_window._reset_markers_after_sweep] DELAYED: Updated right cursor info to index 0")
                    
                # Force final canvas redraw
                if hasattr(self, 'canvas_left') and self.canvas_left:
                    self.canvas_left.draw()
                if hasattr(self, 'canvas_right') and self.canvas_right:
                    self.canvas_right.draw()
                    
            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] Error in delayed cursor update: {e}")
        
        # Execute the delayed update after 100ms to ensure cursor recreation is complete
        QTimer.singleShot(100, force_cursor_info_update)
                
        # Force marker visibility with debug AND fix cursor references
        self._force_marker_visibility()
        self._force_marker_visibility_2()
                
        logging.info("[graphics_window._reset_markers_after_sweep] Marker reset completed successfully")
        
    except Exception as e:
        logging.error(f"[graphics_window._reset_markers_after_sweep] Error resetting markers: {e}")