import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication
)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.updates.graphics_update import update_plots_with_new_data
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

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

        # Load configuration for UI colors and styles

        settings = get_settings(
            "INI/colors_config/config.ini",
            "ui/graphics_windows/graphics_ini/graphics_config.ini", 
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

        update_plots_with_new_data(self, skip_reset=False)

        self.update_cursor()
        self.update_right_cursor()

        self.update_cursor_2()
        self.update_right_cursor_2()

    except Exception as e:
        logging.error(f"Error toggling db/times: {e}")