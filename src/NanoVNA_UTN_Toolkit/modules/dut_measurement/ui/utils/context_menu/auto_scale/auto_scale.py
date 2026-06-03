from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import sys

from pathlib import Path

# Import get_settings 

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

def on_auto_scale_toggled(self):

    # Load configuration for graphics settings and visualization parameters
    settings = get_settings(
        "INI/dut_measurement/auto_scale/auto_scale.ini",
        "modules/dut_measurement/ui/utils/context_menu/auto_scale/auto_scale.ini", 
        Path(__file__).resolve()
    )

    settings.setValue("AutoScale/enabled_left", self.auto_scale_enabled_left)
    settings.setValue("AutoScale/enabled_right", self.auto_scale_enabled_right)

def save_auto_scale_data(self, ymin, ymax, target_ax):
    # Load configuration for graphics settings and visualization parameters
    settings = get_settings(
        "INI/dut_measurement/auto_scale/auto_scale.ini",
        "modules/dut_measurement/ui/utils/context_menu/auto_scale/auto_scale.ini", 
        Path(__file__).resolve()
    )

    if target_ax == self.ax_left:
        settings.setValue("AutoScale/ax", "left")
        settings.setValue("AutoScale/ymin_left", ymin)
        settings.setValue("AutoScale/ymax_left", ymax)
        settings.setValue("AutoScale/enabled_left", self.auto_scale_enabled_left)
    elif target_ax == self.ax_right:
        settings.setValue("AutoScale/ax", "right")
        settings.setValue("AutoScale/ymin_right", ymin)
        settings.setValue("AutoScale/ymax_right", ymax)
        settings.setValue("AutoScale/enabled_right", self.auto_scale_enabled_right)

def read_auto_scale_data(self):

    settings = get_settings(
        "INI/dut_measurement/auto_scale/auto_scale.ini",
        "modules/dut_measurement/ui/utils/context_menu/auto_scale/auto_scale.ini",
        Path(__file__).resolve()
    )

    auto_scale_enabled_left = settings.value("AutoScale/enabled_left", True, type=bool)
    auto_scale_enable_right = settings.value("AutoScale/enabled_right", True, type=bool)
    ymin_left = settings.value("AutoScale/ymin_left", 0.0, type=float)
    ymax_left = settings.value("AutoScale/ymax_left", 0.0, type=float)
    ymin_right = settings.value("AutoScale/ymin_right", 0.0, type=float)
    ymax_right = settings.value("AutoScale/ymax_right", 0.0, type=float)
    ax_name = settings.value("AutoScale/ax", "left", type=str)

    return [auto_scale_enabled_left, auto_scale_enable_right, ymin_left, ymax_left, ymin_right, ymax_right, ax_name]
