import logging
import sys

from pathlib import Path

try:
    from NanoVNA_UTN_Toolkit.shared.utils.settings_utils import get_settings
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

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