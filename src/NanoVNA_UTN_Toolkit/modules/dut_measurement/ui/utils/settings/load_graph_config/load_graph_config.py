import logging
import sys

from pathlib import Path

# Import get_settings 

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ------------------------------------------------------------------------------------------------------------------ #

def load_graph_configuration():

    # Load configuration for graphics settings and visualization parameters
    settings = get_settings(
        "INI/graphics_config/graphics_config.ini",
        "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
        Path(__file__).resolve()
    )

    settings.sync()

    return {
        'graph_type_tab1': settings.value("Tab1/GraphType1", "Smith Diagram"),
        's_param_tab1': settings.value("Tab1/SParameter", "S11"),

        'graph_type_tab2': settings.value("Tab2/GraphType2", "Magnitude"),
        's_param_tab2': settings.value("Tab2/SParameter", "S11"),

        'trace_color1': settings.value("Graphic1/TraceColor", "blue"),
        'marker_color1': settings.value("Graphic1/MarkerColor1", "blue"),
        'marker2_color1': settings.value("Graphic1/MarkerColor2", "blue"),
        'background_color1': settings.value("Graphic1/BackgroundColor", "blue"),
        'text_color1': settings.value("Graphic1/TextColor", "blue"),
        'axis_color1': settings.value("Graphic1/AxisColor", "blue"),

        'trace_size1': int(settings.value("Graphic1/TraceWidth", 2)),
        'marker_size1': int(settings.value("Graphic1/MarkerWidth1", 6)),
        'marker2_size1': int(settings.value("Graphic1/MarkerWidth2", 6)),

        'trace_color2': settings.value("Graphic2/TraceColor", "blue"),
        'marker_color2': settings.value("Graphic2/MarkerColor1", "blue"),
        'marker2_color2': settings.value("Graphic2/MarkerColor2", "blue"),
        'background_color2': settings.value("Graphic2/BackgroundColor", "blue"),
        'text_color2': settings.value("Graphic2/TextColor", "blue"),
        'axis_color2': settings.value("Graphic2/AxisColor", "blue"),

        'trace_size2': int(settings.value("Graphic2/TraceWidth", 2)),
        'marker_size2': int(settings.value("Graphic2/MarkerWidth1", 6)),
        'marker2_size2': int(settings.value("Graphic2/MarkerWidth2", 6))
    }