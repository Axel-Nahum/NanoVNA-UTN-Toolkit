from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication
)

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

update_plots_with_new_data = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.graphics_update", "update_plots_with_new_data")

update_slider_range_silent = safe_import("NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.set_slider_val_silent", "update_slider_range_silent")

# updater, slider, QSettings key for saved cursor index
_PANEL_CURSORS = {
    "left": [
        ("update_cursor",         "slider_left",    "Cursor_1_1/index"),
        ("update_cursor_2",       "slider_left_2",  "Cursor_2_1/index"),
    ],
    "right": [
        ("update_right_cursor",   "slider_right",   "Cursor_1_2/index"),
        ("update_right_cursor_2", "slider_right_2", "Cursor_2_2/index"),
    ],
}

# ------------------------------------------------------------------------------------------------------------------ #

def toggle_db_times(self, event, new_mode):
    """
    Toggle between dB and times for the clicked graph.
    Saves independently for Left (Graphic1) and Right (Graphic2) graph in the INI.
    """
    import os
    from PySide6.QtCore import QSettings

    try:
        # Detect the graph clicked
        widget_under_cursor = QApplication.widgetAt(event.globalPos())
        if widget_under_cursor is None:
            return

        graph_number = 1  # default left
        current_widget = widget_under_cursor
        while current_widget:
            if hasattr(self, "canvas_right") and current_widget == self.canvas_right:
                graph_number = 2
                break
            elif hasattr(self, "canvas_left") and current_widget == self.canvas_left:
                graph_number = 1
                break
            current_widget = current_widget.parent()

        # Decide INI section based on graph
        ini_section = "Graphic1" if graph_number == 1 else "Graphic2"

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        settings.beginGroup(ini_section)

        # Guardar la unidad seleccionada
        settings.setValue("db_times", new_mode)

        # Guardar número de gráfico
        settings.setValue("graph_number", graph_number)

        settings.endGroup()
        settings.sync()

        logging.info(f"Unit {new_mode} saved for {ini_section}")

        # Rebuild only the clicked panel; restore cursors to their saved
        # position instead of resetting to 0.
        panel = "left" if graph_number == 1 else "right"
        update_plots_with_new_data(self, skip_reset=True, draw=False, panels=(panel,))

        freqs = getattr(self, "freqs", None)
        if freqs is not None and len(freqs) > 0:
            max_index = len(freqs) - 1
            pending = getattr(self, "_marker_index_pending", {})
            for updater_name, slider_name, key in _PANEL_CURSORS[panel]:
                saved = int(pending.get(key) if key in pending else settings.value(key, 0))
                saved = min(max(0, saved), max_index)
                slider = getattr(self, slider_name, None)
                if slider is not None:
                    update_slider_range_silent(slider, max_index, saved)
                fn = getattr(self, updater_name, None)
                if callable(fn):
                    try:
                        fn(saved)
                    except Exception as e:
                        logging.warning(f"[toggle_db_times] {updater_name}({saved}) failed: {e}")

        (self.canvas_left if panel == "left" else self.canvas_right).draw_idle()

    except Exception as e:
        logging.error(f"Error toggling db/times: {e}")