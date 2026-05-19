"""
Wizard step manager.
"""

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.introduction_screen import build_introduction_screen


from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.methods.method_a.method_a_calibration import build_method_a_calibration
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.methods.method_b.method_b_calibration import build_method_b_calibration
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.methods.method_c.method_c_calibration import build_method_c_calibration

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.methods.method_a.method_a_measurement import build_method_a_measurement
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.methods.method_b.method_b_measurement import build_method_b_measurement
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.methods.method_c.method_c_measurement import build_method_c_measurement

from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.methods.method_a.method_a_result import build_method_a_result
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.methods.method_b.method_b_result import build_method_b_result
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.methods.method_c.method_c_result import build_method_c_result

# ------------------------------------------------------------------------------------------------------------------- #

def update_step_screen(self):

    self.clear_content()

# ------------------------------------------------------------------------------------------------------------------- #
    # METHOD A
# ------------------------------------------------------------------------------------------------------------------- #

    if self.selected_method == "Method A":

        if self.current_step == 0:

            build_introduction_screen(self)

        elif self.current_step == 1:

            build_method_a_calibration(self)

        elif self.current_step == 2:

            build_method_a_measurement(self)

        elif self.current_step == 3:
            build_method_a_result(self)

# ------------------------------------------------------------------------------------------------------------------- #
    # METHOD B
# ------------------------------------------------------------------------------------------------------------------- #

    elif self.selected_method == "Method B":

        if self.current_step == 0:

            build_introduction_screen(self)

        elif self.current_step == 1:

            build_method_b_calibration(self)

        elif self.current_step == 2:

            build_method_b_measurement(self)

        elif self.current_step == 3:
            build_method_b_result(self)

# ------------------------------------------------------------------------------------------------------------------- #
    # METHOD C
# ------------------------------------------------------------------------------------------------------------------- #

    elif self.selected_method == "Method C":

        if self.current_step == 0:

            build_introduction_screen(self)

        elif self.current_step == 1:

            build_method_c_calibration(self)

        elif self.current_step == 2:

            build_method_c_measurement(self)

        elif self.current_step == 3:
            build_method_c_result(self)