"""
Wizard step dispatcher (descriptor-driven).

EN: Maps the wizard's ``current_step`` to a screen builder using the selected
    technique descriptor. Step 0 is the technique-selection intro; every later
    step is ``descriptor.steps[current_step - 1]`` and is dispatched on its
    ``StepKind``. This replaces the previous hard-coded method_a/b/c branches,
    so adding a technique requires no change here.

ES: Mapea el ``current_step`` del asistente a un constructor de pantalla usando
    el descriptor de la tecnica seleccionada. El paso 0 es la introduccion
    (seleccion de tecnica); cada paso posterior es
    ``descriptor.steps[current_step - 1]`` y se despacha segun su ``StepKind``.
    Esto reemplaza las ramas fijas method_a/b/c, de modo que agregar una tecnica
    no requiere cambios aqui.
"""

import logging

from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import get
from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.base import StepKind
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.introduction_screen import (
    build_introduction_screen,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.config_screen import (
    build_config_screen,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.standard_screen import (
    build_standard_screen,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.result_screen import (
    build_result_screen,
)

logger = logging.getLogger(__name__)


def update_step_screen(self):
    """Render the screen for the wizard's current step."""
    self.clear_content()

    if self.current_step == 0 or not self.selected_technique_id:
        build_introduction_screen(self)
        return

    descriptor = get(self.selected_technique_id)
    steps = descriptor.steps

    # Guard against overshoot.
    index = self.current_step - 1
    if index < 0 or index >= len(steps):
        logger.warning("[steps_manager] step %d out of range", self.current_step)
        return

    step_def = steps[index]

    if step_def.kind is StepKind.CONFIG:
        build_config_screen(self, descriptor, step_def)
    elif step_def.kind in (StepKind.STANDARD_MEASURE, StepKind.DUT_MEASURE):
        build_standard_screen(self, descriptor, step_def)
    elif step_def.kind is StepKind.RESULT:
        build_result_screen(self, descriptor, step_def)
    else:
        logger.warning("[steps_manager] unhandled step kind: %s", step_def.kind)

    # Update the Next button label on the final step.
    is_last = self.current_step == len(steps)
    self.next_button.setText(self.finish_button_text if is_last else "▶▶")
