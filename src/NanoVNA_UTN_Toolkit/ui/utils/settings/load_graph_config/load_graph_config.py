import os
import sys

from PySide6.QtCore import QSettings

def load_graph_configuration():

    # Load configuration for UI colors and styles
    if getattr(sys, 'frozen', False):
        appdata = os.getenv("APPDATA")
        base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")
        graph_config = os.path.join(base, "INI", "colors_config", "config.ini") # VER
    else:
        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(__file__)
                    )
                )
            )
        )

        graph_config = os.path.join(
            base_dir,
            "ui",
            "graphics_windows",
            "ini",
            "config.ini"
        )

    settings = QSettings(graph_config, QSettings.IniFormat)

    return {
        'graph_type_tab1': settings.value("Tab1/GraphType1", "Smith Diagram"),
        's_param_tab1': settings.value("Tab1/SParameter", "S11"),
        'graph_type_tab2': settings.value("Tab2/GraphType2", "Magnitude"),
        's_param_tab2': settings.value("Tab2/SParameter", "S11"),
        'trace_color1': settings.value("Graphic1/TraceColor", "blue"),
        'marker_color1': settings.value("Graphic1/MarkerColor1", "blue"),
        'marker2_color1': settings.value("Graphic1/MarkerColor2", "blue"),
        'trace_size1': int(settings.value("Graphic1/TraceWidth", 2)),
        'marker_size1': int(settings.value("Graphic1/MarkerWidth1", 6)),
        'marker2_size1': int(settings.value("Graphic1/MarkerWidth2", 6)),
        'trace_color2': settings.value("Graphic2/TraceColor", "blue"),
        'marker_color2': settings.value("Graphic2/MarkerColor1", "blue"),
        'marker2_color2': settings.value("Graphic2/MarkerColor2", "blue"),
        'trace_size2': int(settings.value("Graphic2/TraceWidth", 2)),
        'marker_size2': int(settings.value("Graphic2/MarkerWidth1", 6)),
        'marker2_size2': int(settings.value("Graphic2/MarkerWidth2", 6))
    }