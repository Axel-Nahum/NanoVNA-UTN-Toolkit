import logging
import sys
import os

from PySide6.QtCore import QTimer

try:
    from src.NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.reset.panels_utils import _clear_all_marker_fields
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

def _reset_sliders_after_reconnect(self):
    """Reset sliders and show cursor information after successful device reconnection."""
    try:
        logging.info("[graphics_window._reset_sliders_after_reconnect] Resetting sliders after successful reconnection")
        
        # Only reset if we have data available
        if not (hasattr(self, 'freqs') and self.freqs is not None and len(self.freqs) > 0):
            logging.info("[graphics_window._reset_sliders_after_reconnect] No sweep data available, skipping reset")
            return
        
        # Reset slider positions to leftmost position (index 0)
        if hasattr(self, 'slider_left') and self.slider_left:
            try:
                self.slider_left.set_val(0)
                logging.info("[graphics_window._reset_sliders_after_reconnect] Reset left slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_after_reconnect] Could not reset left slider: {e}")

        if hasattr(self, 'slider_left_2') and self.slider_left_2:
            try:
                self.slider_left_2.set_val(0)
                logging.info("[graphics_window._reset_sliders_after_reconnect] Reset left slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_after_reconnect] Could not reset left slider: {e}")
        
        
        if hasattr(self, 'slider_right') and self.slider_right:
            try:
                self.slider_right.set_val(0)
                logging.info("[graphics_window._reset_sliders_after_reconnect] Reset right slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_after_reconnect] Could not reset right slider: {e}")

        if hasattr(self, 'slider_right_2') and self.slider_right_2:
            try:
                self.slider_right_2.set_val(0)
                logging.info("[graphics_window._reset_sliders_after_reconnect] Reset right slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_after_reconnect] Could not reset right slider: {e}")
        
        # Update cursor information to show data for minimum position
        if hasattr(self, 'update_cursor') and callable(self.update_cursor):
            try:
                self.update_cursor(0)
                logging.info("[graphics_window._reset_sliders_after_reconnect] Updated left cursor info to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_after_reconnect] Could not update left cursor: {e}")

        if hasattr(self, 'update_cursor_2') and callable(self.update_cursor_2):
            try:
                self.update_cursor_2(0)
                logging.info("[graphics_window._reset_sliders_after_reconnect] Updated left cursor info to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_after_reconnect] Could not update left cursor: {e}")
        
        if hasattr(self, 'update_right_cursor') and callable(self.update_right_cursor):
            try:
                self.update_right_cursor(0)
                logging.info("[graphics_window._reset_sliders_after_reconnect] Updated right cursor info to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_after_reconnect] Could not update right cursor: {e}")
        if hasattr(self, 'update_right_cursor_2') and callable(self.update_right_cursor_2):
            try:
                self.update_right_cursor_2(0)
                logging.info("[graphics_window._reset_sliders_after_reconnect] Updated right cursor info to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_after_reconnect] Could not update right cursor: {e}")
        
        # Force canvas redraw to ensure visual update
        if hasattr(self, 'canvas_left') and self.canvas_left:
            self.canvas_left.draw()
        if hasattr(self, 'canvas_right') and self.canvas_right:
            self.canvas_right.draw()
                
        logging.info("[graphics_window._reset_sliders_after_reconnect] Sliders reset and info updated after reconnection")
        
    except Exception as e:
        logging.error(f"[graphics_window._reset_sliders_after_reconnect] Error resetting sliders after reconnection: {e}")

def _reset_sliders_before_sweep(self):
    """Reset sliders and CLEAR all cursor information before starting a sweep."""
    try:
        logging.info("[graphics_window._reset_sliders_before_sweep] Resetting sliders and clearing info before sweep starts")
        
        # Reset slider positions to leftmost position (index 0)
        if hasattr(self, 'slider_left') and self.slider_left:
            try:
                self.slider_left.set_val(0)
                logging.info("[graphics_window._reset_sliders_before_sweep] Reset left slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_before_sweep] Could not reset left slider: {e}")

        if hasattr(self, 'slider_left_2') and self.slider_left_2:
            try:
                self.slider_left_2.set_val(0)
                logging.info("[graphics_window._reset_sliders_before_sweep] Reset left slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_before_sweep] Could not reset left slider: {e}")
        
        if hasattr(self, 'slider_right') and self.slider_right:
            try:
                self.slider_right.set_val(0)
                logging.info("[graphics_window._reset_sliders_before_sweep] Reset right slider to index 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_before_sweep] Could not reset right slider: {e}")
        
        if hasattr(self, 'slider_right_2') and self.slider_right_2:
            try:
                self.slider_right_2.set_val(0)
                logging.info("[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Ensured right slider at position 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_sliders_and_markers_for_graph_change] DELAYED: Could not set right slider: {e}")
        
        # CLEAR all marker information (DO NOT update cursor info - just clear it)
        _clear_all_marker_fields(self)
        logging.info("[graphics_window._reset_sliders_before_sweep] Cleared all marker information display")
                
        logging.info("[graphics_window._reset_sliders_before_sweep] Sliders reset and info cleared before sweep")
        
    except Exception as e:
        logging.error(f"[graphics_window._reset_sliders_before_sweep] Error resetting sliders before sweep: {e}")