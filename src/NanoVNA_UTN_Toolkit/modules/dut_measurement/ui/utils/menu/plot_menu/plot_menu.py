from pathlib import Path
from NanoVNA_UTN_Toolkit.utils import safe_import

open_plot_settings = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.plot_menu.plot_manager.plot_manager",
    "open_plot_settings"
)

open_signal_filters = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.plot_menu.signal_filters.signal_filters",
    "open_signal_filters"
)


def open_plot_manager(self):
    open_plot_settings(self)


def open_signal_filter(self):
    open_signal_filters(self)