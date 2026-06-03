from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from pathlib import Path

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

def get_graph_unit(self, graph_number):
    """Read the unit from INI for left (1) or right (2) graph."""
    try:
        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )
        
        group_name = f"Graphic{graph_number}"
        settings.beginGroup(group_name)
        unit = settings.value("db_times", "dB")  # default dB
        settings.endGroup()
        
        return unit
    except Exception as e:
        logging.error(f"Error reading unit from INI: {e}")
        return "dB"