"""
Programmatic slider moves without firing ``on_changed``.

EN: ``Slider.set_val`` only notifies its observers while ``slider.eventson`` is
true, so a silent move just clears that flag around the call. (The previous
version disconnected and re-registered the observers; the registry stores
reference wrappers, so re-registering them left every later user move raising
``TypeError`` inside matplotlib's callback registry.)

ES: Mover un slider por programa sin disparar ``on_changed``: se apaga
``eventson`` alrededor de ``set_val``, que es el mecanismo previsto por matplotlib.
"""

import logging


def set_slider_val_silent(slider, value):
    """Set ``value`` on ``slider`` without running its ``on_changed`` callbacks.

    The range is widened if needed so the value is always representable.
    """
    if slider is None:
        return
    eventson = getattr(slider, "eventson", True)
    slider.eventson = False
    try:
        slider.valmin = min(slider.valmin, value)
        slider.valmax = max(slider.valmax, value)
        slider.set_val(value)
    except Exception as e:
        logging.warning(f"[set_slider_val_silent] {e}")
    finally:
        slider.eventson = eventson


def update_slider_range_silent(slider, new_max, new_val=None):
    """Set the range to ``0..new_max`` (step 1) and the value, silently.

    ``new_val`` defaults to the current value clamped into the new range.
    """
    if slider is None:
        return
    try:
        target_val = new_val if new_val is not None else min(int(slider.val), new_max)
        target_val = max(0, min(int(target_val), int(new_max)))
    except Exception as e:
        logging.warning(f"[update_slider_range_silent] value error: {e}")
        return
    eventson = getattr(slider, "eventson", True)
    slider.eventson = False
    try:
        slider.valmin = 0
        slider.valmax = new_max
        slider.valstep = 1
        slider.set_val(target_val)
    except Exception as e:
        logging.warning(f"[update_slider_range_silent] range error: {e}")
    finally:
        slider.eventson = eventson
