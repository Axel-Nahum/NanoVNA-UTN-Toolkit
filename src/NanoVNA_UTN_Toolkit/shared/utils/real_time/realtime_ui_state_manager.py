from NanoVNA_UTN_Toolkit.utils import safe_import
import logging

from PySide6.QtCore import QTimer

from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.panels_utils import _clear_axis_and_show_message, _clear_panel_labels

load_graph_configuration = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.load_graph_config.load_graph_config",
    "load_graph_configuration"
)

def enter_realtime_initializing_state(self):
    """
    Clears UI and prepares the system for real-time mode startup.
    Shows waiting message until first sweep arrives.
    """

    logging.info("[graphics_window._enter_realtime_initializing_state] Entering realtime init state")

    config = load_graph_configuration()
    graph_type_tab1 = config['graph_type_tab1']
    graph_type_tab2 = config['graph_type_tab2']

    # ---------------- LEFT PANEL ----------------
    if graph_type_tab1 in ("Smith Diagram", "Magnitude", "Phase"):

        # clear labels + markers
        _clear_panel_labels(self, 'left')

        # hide cursors safely
        if hasattr(self, 'cursor_left') and self.cursor_left:
            self.cursor_left.set_visible(False)

        if hasattr(self, 'cursor_left_2') and self.cursor_left_2:
            self.cursor_left_2.set_visible(False)

        # show waiting message
        _clear_axis_and_show_message(
            self,
            panel_side='left',
            message_pos=(0.5, 0.5)
        )

    # ---------------- RIGHT PANEL ----------------
    if graph_type_tab2 in ("Smith Diagram", "Magnitude", "Phase"):

        _clear_panel_labels(self, 'right')

        if hasattr(self, 'cursor_right') and self.cursor_right:
            self.cursor_right.set_visible(False)

        if hasattr(self, 'cursor_right_2') and self.cursor_right_2:
            self.cursor_right_2.set_visible(False)

        _clear_axis_and_show_message(
            self,
            panel_side='right',
            message_pos=(0.5, 0.5)
        )

    logging.info("[graphics_window._enter_realtime_initializing_state] UI ready, waiting for first sweep")