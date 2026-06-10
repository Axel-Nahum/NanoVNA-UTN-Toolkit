from NanoVNA_UTN_Toolkit.utils import safe_import
import logging

from PySide6.QtCore import QTimer

_clear_marker_fields_only = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.panels_utils", "_clear_marker_fields_only")

update_slider_ranges = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.sliders_update", "update_slider_ranges")

# -------------------------------------------------------------------------------------------------------------------- #

def _reset_markers_after_sweep(self):
    """Reset markers and all marker-dependent information after a sweep completes."""
    logging.info("[graphics_window._reset_markers_after_sweep] Resetting markers after sweep completion")

    try:
        if self.cursor_left and getattr(self.cursor_left, "ax", None):
            _ = self.cursor_left.ax.get_figure()
        else:
            return

    except Exception as e:
        logging.warning("[graphics_window._reset_markers_after_sweep] Skipped invalid cursor: %s", e)

    try:
        # ----------------------------
        # 1. RESET SLIDERS (STATE)
        # ----------------------------
        for name in ["slider_left", "slider_left_2", "slider_right", "slider_right_2"]:
            if hasattr(self, name) and getattr(self, name):
                try:
                    getattr(self, name).set_val(0)
                    logging.info(f"[graphics_window._reset_markers_after_sweep] Reset {name} to 0")
                except Exception as e:
                    logging.warning(f"[graphics_window._reset_markers_after_sweep] Could not reset {name}: {e}")

        # ----------------------------
        # 2. CLEAR TEXT FIELDS ONLY
        # ----------------------------
        _clear_marker_fields_only(self)

        # ----------------------------
        # 3. UPDATE INTERNAL RANGE STATE
        # ----------------------------
        update_slider_ranges(self)

        # ----------------------------
        # 4. CURSOR LOGIC (STATE UPDATE ONLY)
        # ----------------------------
        def safe_update(func, label):
            try:
                if hasattr(self, func) and callable(getattr(self, func)):
                    getattr(self, func)(0)
                    logging.info(f"[graphics_window._reset_markers_after_sweep] Updated {label} cursor to 0")
            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] {label} update failed: {e}")

        safe_update("update_cursor", "left")
        safe_update("update_cursor_2", "left_2")
        safe_update("update_right_cursor", "right")
        safe_update("update_right_cursor_2", "right_2")

        # ----------------------------
        # 5. FIRST SAFE DRAW
        # ----------------------------
        try:
            if hasattr(self, 'canvas_left') and self.canvas_left:
                self.canvas_left.draw_idle()
            if hasattr(self, 'canvas_right') and self.canvas_right:
                self.canvas_right.draw_idle()
        except Exception as e:
            logging.warning(f"[graphics_window._reset_markers_after_sweep] canvas draw failed: {e}")

        # ----------------------------
        # 6. DELAYED SYNC (AFTER EVENT LOOP)
        # ----------------------------
        def force_cursor_info_update():
            try:
                for fn in ["update_cursor", "update_cursor_2", "update_right_cursor", "update_right_cursor_2"]:
                    if hasattr(self, fn) and callable(getattr(self, fn)):
                        getattr(self, fn)(0)

                if hasattr(self, 'canvas_left') and self.canvas_left:
                    self.canvas_left.draw_idle()
                if hasattr(self, 'canvas_right') and self.canvas_right:
                    self.canvas_right.draw_idle()

            except Exception as e:
                logging.warning(f"[graphics_window._reset_markers_after_sweep] delayed update error: {e}")

        QTimer.singleShot(0, force_cursor_info_update)

        logging.info("[graphics_window._reset_markers_after_sweep] Marker reset completed successfully")

    except Exception as e:
        logging.error(f"[graphics_window._reset_markers_after_sweep] Error resetting markers: {e}")