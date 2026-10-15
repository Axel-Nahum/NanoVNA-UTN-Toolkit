"""
Open a saved calibration kit in the characterization wizard.

EN: The ONE function every "use a saved kit" action calls (welcome screen
    dropdown, Calibration > Select / Import menu). There used to be two copies
    that had drifted apart: the menu one forgot the per-standard preset
    temperatures (a water reference recorded at 18 C was then evaluated at
    the session's 25 C) and the probe, and neither kept the pre-calibrated
    steps (kits stored them already divided, without their reference).

ES: La UNICA funcion que llama toda accion de "usar un kit guardado" (combo de
    la pantalla de bienvenida, menu Calibracion > Seleccionar / Importar).
    Habia dos copias que se habian separado: la del menu olvidaba las
    temperaturas de preset de cada patron (una referencia de agua medida a
    18 C se evaluaba a los 25 C de la sesion) y la sonda, y ninguna conservaba
    los pasos pre-calibrados (los kits los guardaban ya divididos, sin su
    referencia).
"""

from __future__ import annotations

import logging

from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import calibration_store
from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import get as get_technique
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.session_liquids import (
    set_liquid_key,
)

logger = logging.getLogger(__name__)


def configure_wizard_from_kit(wizard, kit_name: str):
    """
    Put the session of ``wizard`` in the state saved in kit ``kit_name``.

    EN: Technique, localized method title, temperature, sweep, reference
        liquids, probe, every standard (with its preset temperature and its
        own pre-calibration) and the temperature warnings. The manifest, the
        technique and every file are validated before anything changes;
        raises ``ValueError`` / ``FileNotFoundError`` with a user-readable
        message. Returns the technique descriptor. No Qt involved.
    ES: Tecnica, titulo localizado del metodo, temperatura, barrido, liquidos
        de referencia, sonda, cada patron (con su temperatura de preset y su
        propia pre-calibracion) y las advertencias de temperatura. El manifiesto, la
        tecnica y todos los archivos se validan antes de cambiar nada; lanza
        ``ValueError`` / ``FileNotFoundError`` con un mensaje legible.
        Devuelve el descriptor de la tecnica. No usa Qt.
    """
    meta = calibration_store.read_calibration_meta(kit_name)
    label = meta.display_name or kit_name
    if not meta.technique_id:
        raise ValueError(
            f"Calibration '{label}' has no technique ID stored in its manifest.\n"
            "This calibration was saved incorrectly. Please redo the measurement and save it again."
        )
    try:
        descriptor = get_technique(meta.technique_id)
    except KeyError:
        raise ValueError(
            f"Calibration '{label}' references unknown technique '{meta.technique_id}'.\n"
            "The calibration may have been created with a different version of the app."
        ) from None

    # Reads and validates every file before touching the calibration.
    meta, warnings = calibration_store.apply_calibration(wizard.perm_calibration, kit_name)

    wizard.selected_technique_id = meta.technique_id
    # Localized title, as the introduction screen stores it; the raw
    # name_token would end up verbatim in the report.
    methods = load_text("characterization_methods.json").get("methods", {})
    wizard.selected_method = methods.get(descriptor.name_token, {}).get(
        "title", descriptor.name_token)
    wizard.temperature_c = meta.temperature_c
    if meta.f_start_hz is not None:
        wizard.sweep_start_freq = meta.f_start_hz
    if meta.f_stop_hz is not None:
        wizard.sweep_stop_freq = meta.f_stop_hz
    if meta.points is not None:
        wizard.sweep_steps = meta.points
    # The screens read the liquid of each reference from the session map, not
    # from the calibration: without this a kit saved with ethanol as ref1
    # would be shown (and its preset list filtered) as the default water.
    set_liquid_key(wizard, "ref1", meta.ref1_key)
    if meta.ref2_key:
        set_liquid_key(wizard, "ref2", meta.ref2_key)
    wizard.temperature_warnings = warnings
    wizard.epsilon_result = None

    logger.info("[kit_loader] kit '%s' loaded (technique=%s, pre-cal=%s)",
                kit_name, meta.technique_id, meta.precal_kinds or "none")
    return descriptor


def load_kit_into_wizard(wizard, kit_name: str) -> None:
    """``configure_wizard_from_kit`` and then open the DUT measurement step."""
    from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.steps_manager import (
        update_step_screen,
    )

    descriptor = configure_wizard_from_kit(wizard, kit_name)
    # current_step = descriptor index + 1 (step 0 is the introduction).
    dut_step = next(
        (i + 1 for i, s in enumerate(descriptor.steps)
         if s.standard is not None and s.standard.key == "dut"),
        None,
    )
    if dut_step is not None:
        wizard.current_step = dut_step
        update_step_screen(wizard)
