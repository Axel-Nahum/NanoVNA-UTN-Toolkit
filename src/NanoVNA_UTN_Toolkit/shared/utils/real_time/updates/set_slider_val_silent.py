# shared/utils/real_time/updates/slider_utils.py

import logging

def set_slider_val_silent(slider, value):
    """
    Setea el valor del slider sin disparar callbacks (on_changed).
    Usar siempre que el cambio sea programático, no del usuario.
    """
    if slider is None:
        return
    try:
        # Guardar y desconectar callbacks
        callbacks = slider._observers.callbacks.get("changed", {})
        saved = dict(callbacks)  # copia de {cid: func}
        for cid in list(saved.keys()):
            slider._observers.disconnect(cid)

        # Actualizar rango si es necesario
        slider.valmin  = min(slider.valmin, value)
        slider.valmax  = max(slider.valmax, value)

        # Setear valor sin disparar nada
        slider.set_val(value)

    except Exception as e:
        logging.warning(f"[set_slider_val_silent] {e}")

    finally:
        # Reconectar callbacks aunque haya error
        try:
            for func in saved.values():
                slider.on_changed(func)
        except Exception as e:
            logging.warning(f"[set_slider_val_silent] reconnect error: {e}")


def update_slider_range_silent(slider, new_max, new_val=None):
    """
    Actualiza el rango del slider y opcionalmente su valor, sin disparar callbacks.
    """
    if slider is None:
        return
    target_val = new_val if new_val is not None else min(int(slider.val), new_max)
    set_slider_val_silent(slider, 0)  # reset temporal para evitar out-of-range
    try:
        slider.valmin  = 0
        slider.valmax  = new_max
        slider.valstep = 1
    except Exception as e:
        logging.warning(f"[update_slider_range_silent] range error: {e}")
    set_slider_val_silent(slider, target_val)