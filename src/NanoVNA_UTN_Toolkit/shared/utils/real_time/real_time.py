import logging

import numpy as np
import skrf as rf

from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread, QTimer

from NanoVNA_UTN_Toolkit.utils import safe_import
from NanoVNA_UTN_Toolkit.shared.utils.qt_logging import log_thread_checkpoint

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

# Consecutive failed real-time sweeps tolerated before declaring the device lost.
_RT_MAX_RETRIES = 5

# ------------------------------------------------------------------------------------------------------------------ #
# WORKER
# ------------------------------------------------------------------------------------------------------------------ #

class SweepWorker(QObject):

    sweep_finished = Signal(object, object, object)
    sweep_failed = Signal(str)

    def __init__(self, vna_device, start_freq_hz, stop_freq_hz, segments, calibration_fn, dut=None):
        super().__init__()
        self.vna_device = vna_device
        self.start_freq_hz = start_freq_hz
        self.stop_freq_hz = stop_freq_hz
        self.segments = segments
        self.calibration_fn = calibration_fn
        self.dut = dut
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):

        try:
            if self._abort:
                return
            
            self.vna_device.setSweep(self.start_freq_hz, self.stop_freq_hz)

            freqs = np.linspace(self.start_freq_hz, self.stop_freq_hz, self.segments)

            self.vna_device.datapoints = self.segments

            if self._abort:
                return

            s11_raw = np.array(self.vna_device.readValues("data 0"))
            s21_raw = np.array(self.vna_device.readValues("data 1"))

            if self._abort:
                return

            if self.dut is not None:
                net = rf.Network(self.dut)
                freqs = net.f
                s11 = net.s[:, 0, 0]
                s21 = net.s[:, 1, 0]
            else:
                s11, s21 = self.calibration_fn(s11_raw, s21_raw, freqs)

            self.sweep_finished.emit(freqs, s11, s21)

        except Exception as e:
            # Concise here: the GUI side (_fail) logs the user-facing message with a
            # retry counter. Full traceback only at DEBUG so it never floods the log
            # when the device is unplugged mid-sweep.
            logging.debug("[SweepWorker] error", exc_info=True)
            self.sweep_failed.emit(str(e))

# ------------------------------------------------------------------------------------------------------------------ #
# PUBLIC API
# ------------------------------------------------------------------------------------------------------------------ #

def on_realtime_toggled(self, enabled):

    sf_settings = get_settings(
        "INI/dut_measurement/signal_filters/signal_filters.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/signal_filters/signal_filters.ini",
        Path(__file__).resolve()
    )

    preset = sf_settings.value("kalman/preset", "Default")

    if preset == "Off" and not self.realtime_checkbox.isChecked():
        self.sweep_button.setEnabled(False)
    else:
        self.sweep_button.setEnabled(True)

    if not enabled: 
        self.sweep_button.setText(f"{self.measurement_ui_button_reset_kalman}")
        logging.info("[real_time] ENABLED")
        self._rt_generation = getattr(self, "_rt_generation", 0) + 1
        start_realtime(self)
    else:
        self.sweep_button.setText(self.measurement_ui_button_run_sweep)
        logging.info("[real_time] DISABLED")
        stop_realtime(self)

# ------------------------------------------------------------------------------------------------------------------ #
# START / STOP
# ------------------------------------------------------------------------------------------------------------------ #

def start_realtime(self):

    if getattr(self, "_rt_active", False):
        return

    self._rt_active = True
    self._rt_busy = False
    self._rt_failures = 0
    self._rt_proc_errors = 0

    self.realtime_interval_ms = getattr(self, "realtime_interval_ms", 100)

    self._rt_timer = QTimer(self)
    self._rt_timer.timeout.connect(lambda: _trigger(self))
    self._rt_timer.start(self.realtime_interval_ms)

def stop_realtime(self):

    self._rt_active = False
    self._rt_busy = False

    if hasattr(self, "_rt_timer") and self._rt_timer:
        self._rt_timer.stop()
        self._rt_timer.deleteLater()
        self._rt_timer = None

    _abort(self)

# ------------------------------------------------------------------------------------------------------------------ #
# CORE LOOP — GUI-THREAD CONTROLLER
# ------------------------------------------------------------------------------------------------------------------ #
#
# SweepWorker is moved to a QThread, so it emits its signals FROM the worker
# thread. In PySide6 a signal connected to a context-less lambda/functor (no
# QObject receiver) is invoked SYNCHRONOUSLY in the *emitting* thread — Qt has no
# receiver affinity to queue against, so it cannot marshal the call to the GUI
# thread. That is what made the result handler and the thread-stop run in the
# worker thread: _safe_stop_thread then called thread.wait() on the worker thread
# itself -> "QThread::wait: Thread tried to wait on itself", and _done() updated
# matplotlib canvases off the GUI thread.
#
# Connecting instead to a *bound method of a QObject that lives in the GUI thread*
# makes Qt use a queued connection, so the slot runs on the GUI thread. This tiny
# controller (created in _trigger, i.e. on the GUI thread) provides those slots.

class _RealtimeController(QObject):

    def __init__(self, window, gen):
        super().__init__()  # created on the GUI thread -> GUI-thread affinity
        self._window = window
        self._gen = gen

    def on_finished(self, freqs, s11, s21):  # runs on the GUI thread
        log_thread_checkpoint("real_time: sweep_finished handler (expected GUI)")
        try:
            _done(self._window, freqs, s11, s21, self._gen)
        except Exception as e:
            _handle_processing_error(self._window, e)

    def on_failed(self, msg):  # runs on the GUI thread
        log_thread_checkpoint("real_time: sweep_failed handler (expected GUI)")
        try:
            _fail(self._window, msg, self._gen)
        except Exception:
            logging.exception("[real_time] on_failed handler error")
            self._window._rt_busy = False

    def on_thread_finished(self):  # teardown point (where quit()+wait() used to run)
        log_thread_checkpoint("real_time: worker thread finished, deleting")


def _trigger(self):

    if not self._rt_active:
        return

    if self._rt_busy:
        return

    if not self.vna_device or not self.vna_device.connected():
        # Port already closed -> no point retrying; go straight to disconnected UI.
        _handle_realtime_disconnect(self)
        return

    self._rt_busy = True

    worker = SweepWorker(
        self.vna_device,
        self.start_freq_hz,
        self.stop_freq_hz,
        self.segments,
        _build_calibration_fn(self),
        getattr(self, "dut", None)
    )

    thread = QThread(self)  # QThread object has GUI-thread affinity
    worker.moveToThread(thread)

    gen = self._rt_generation

    # The controller lives on the GUI thread; its bound-method slots therefore run
    # on the GUI thread (queued connection), unlike a context-less lambda.
    controller = _RealtimeController(self, gen)

    thread.started.connect(worker.run)

    # Results -> GUI thread.
    worker.sweep_finished.connect(controller.on_finished)
    worker.sweep_failed.connect(controller.on_failed)

    # Lifecycle: quit the worker's event loop, then delete everything. There is no
    # wait() anywhere, so the self-wait warning can no longer occur. quit() is a
    # bound method of the GUI-thread QThread, so it is also marshalled correctly.
    worker.sweep_finished.connect(thread.quit)
    worker.sweep_failed.connect(thread.quit)
    thread.finished.connect(controller.on_thread_finished)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(controller.deleteLater)

    thread.start()
    log_thread_checkpoint("real_time._trigger: worker thread started", target_thread=thread)

    self._rt_thread = thread
    self._rt_worker = worker
    self._rt_controller = controller

# ------------------------------------------------------------------------------------------------------------------ #
# DONE
# ------------------------------------------------------------------------------------------------------------------ #

def _done(self, freqs, s11, s21, gen):

    # ----------------------------------------------------
    # Plot Manager settings
    # ----------------------------------------------------

    settings = get_settings(
        "INI/dut_measurement/signal_filters/signal_filters.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/signal_filters/signal_filters.ini",
        Path(__file__).resolve()
    )

    is_kalman_enabled = settings.value("kalman/enabled", False, type=bool)

    if gen != self._rt_generation or not getattr(self, "_rt_active", False):
        return

    # Successful read -> the device is responsive again; clear the failure streaks.
    self._rt_failures = 0
    self._rt_proc_errors = 0

    self.s11_raw = s11
    self.s21_raw = s21

    # spike removal — only when a calibration method is active
    cal_settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )
    _is_calibrated = (
        not cal_settings.value("Calibration/NoCalibration", False, type=bool)
        and (
            cal_settings.value("Calibration/Method", "---") != "---"
            or cal_settings.value("Calibration/Kits", False, type=bool)
        )
    )
    if _is_calibrated:
        s11 = _remove_spikes(s11, freqs)
        s21 = _remove_spikes(s21, freqs)
        s11 = _remove_phase_spikes(s11, freqs)
        s21 = _remove_phase_spikes(s21, freqs)

    # kalman filter for smoothing
    if is_kalman_enabled:
        s11_f = np.array([self.kf_s11.update(x) for x in s11])
        s21_f = np.array([self.kf_s21.update(x) for x in s21])
    else:
        s11_f = s11
        s21_f = s21

    self.freqs = freqs
    self.s11 = s11_f
    self.s21 = s21_f

    from NanoVNA_UTN_Toolkit.shared.utils.real_time.updates.graphic_real_times_update import update_plots_realtime
    update_plots_realtime(self)

    self._rt_busy = False

# ------------------------------------------------------------------------------------------------------------------ #
# FAIL
# ------------------------------------------------------------------------------------------------------------------ #

def _fail(self, msg, gen):

    if gen != self._rt_generation or not getattr(self, "_rt_active", False):
        return

    self._rt_busy = False
    self._rt_failures = getattr(self, "_rt_failures", 0) + 1

    if self._rt_failures < _RT_MAX_RETRIES:
        # Transient: let the timer retry on the next tick. One concise WARNING per
        # retry instead of a full traceback flood.
        logging.warning("[real_time] sweep failed (%d/%d), retrying: %s",
                        self._rt_failures, _RT_MAX_RETRIES, msg)
    else:
        logging.error("[real_time] sweep failed %d/%d times: %s",
                      self._rt_failures, _RT_MAX_RETRIES, msg)
        _handle_realtime_disconnect(self)


# ------------------------------------------------------------------------------------------------------------------ #
# DEVICE-LOST HANDLER
# ------------------------------------------------------------------------------------------------------------------ #

def _handle_realtime_disconnect(self):
    """Give up after too many failed sweeps: stop the loop, keep the last data on
    screen, and surface the reconnect button so the user can retry."""

    # Stop the loop first — this is what ends the flood of failing sweeps.
    stop_realtime(self)
    self._rt_failures = 0

    # Reflect "real-time stopped" in the checkbox without re-firing on_realtime_toggled.
    if hasattr(self, "realtime_checkbox"):
        self.realtime_checkbox.blockSignals(True)
        self.realtime_checkbox.setChecked(True)  # "Single Sweep Mode" => real-time off
        self.realtime_checkbox.blockSignals(False)

    # Restore the normal sweep-button label (it read "Reset Kalman" during real-time).
    if hasattr(self, "sweep_button"):
        self.sweep_button.setText(getattr(self, "measurement_ui_button_run_sweep", "Run Sweep"))

    # Make the reconnect button available. The last measured data is left untouched
    # on the plots (self.freqs / self.s11 / self.s21 are not cleared).
    try:
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.graphics_refresh import (
            update_reconnect_button_state,
        )
        update_reconnect_button_state(self)
    except Exception:
        logging.debug("[real_time] update_reconnect_button_state failed", exc_info=True)

    logging.warning(
        "[real_time] NanoVNA unresponsive after %d retries - real-time stopped. "
        "Last data kept on screen; press Reconnect to retry.", _RT_MAX_RETRIES
    )


def _handle_processing_error(self, exc):
    """A sweep result failed to process (e.g. a bug in _done / Kalman). Bounded
    logging so a persistent error never floods the log, and stop real-time after
    too many in a row. Last good data stays on screen."""

    self._rt_busy = False
    self._rt_proc_errors = getattr(self, "_rt_proc_errors", 0) + 1

    if self._rt_proc_errors == 1:
        # Full traceback once, so the underlying bug stays debuggable.
        logging.error("[real_time] error processing sweep result: %s", exc, exc_info=True)
    elif self._rt_proc_errors < _RT_MAX_RETRIES:
        logging.warning("[real_time] error processing sweep result (%d/%d): %s",
                        self._rt_proc_errors, _RT_MAX_RETRIES, exc)
    else:
        logging.error("[real_time] real-time stopped after %d consecutive processing errors: %s",
                      _RT_MAX_RETRIES, exc)
        stop_realtime(self)
        self._rt_proc_errors = 0
        # Leave the UI usable; last measured data stays on the plots.
        if hasattr(self, "realtime_checkbox"):
            self.realtime_checkbox.blockSignals(True)
            self.realtime_checkbox.setChecked(True)
            self.realtime_checkbox.blockSignals(False)
        if hasattr(self, "sweep_button"):
            self.sweep_button.setText(getattr(self, "measurement_ui_button_run_sweep", "Run Sweep"))

# ------------------------------------------------------------------------------------------------------------------ #
# ABORT
# ------------------------------------------------------------------------------------------------------------------ #

def _abort(self):

    worker = getattr(self, "_rt_worker", None)
    thread = getattr(self, "_rt_thread", None)

    if worker:
        worker.abort()

    if thread is not None:
        # _abort runs on the GUI thread (called from stop_realtime). quit() is
        # non-blocking; the thread.finished -> deleteLater chain set up in
        # _trigger tears the thread down. No wait() -> no self-wait risk.
        # The checkpoint flags loudly if this ever runs on the worker thread.
        log_thread_checkpoint("real_time._abort: stopping worker thread", target_thread=thread)
        try:
            thread.quit()
        except RuntimeError:
            pass

    self._rt_worker = None
    self._rt_thread = None
    self._rt_controller = None


# ------------------------------------------------------------------------------------------------------------------ #
# SPIKE REMOVAL
# ------------------------------------------------------------------------------------------------------------------ #

_SPIKE_THRESHOLD       = 3.0
_PHASE_SPIKE_MULT      = 2.0
_PHASE_SPIKE_FLOOR_DEG = 1.0
_SPIKE_PASSES          = 2

def _remove_spikes(s_data, freqs, threshold=_SPIKE_THRESHOLD, passes=_SPIKE_PASSES):
    s = np.array(s_data, dtype=complex)
    freqs = np.asarray(freqs, dtype=float)
    n = min(len(s), len(freqs))
    s, freqs = s[:n], freqs[:n]

    for _ in range(passes):
        mag = np.abs(s)
        for i in range(1, n - 1):
            local_avg = (mag[i - 1] + mag[i + 1]) / 2.0
            if local_avg > 0 and mag[i] >= threshold * local_avg:
                t = (freqs[i] - freqs[i - 1]) / (freqs[i + 1] - freqs[i - 1])
                s[i] = s[i - 1] + t * (s[i + 1] - s[i - 1])
                mag[i] = abs(s[i])

    return s


def _remove_phase_spikes(s_data, freqs, multiplier=_PHASE_SPIKE_MULT, floor_deg=_PHASE_SPIKE_FLOOR_DEG, passes=_SPIKE_PASSES):
    s = np.array(s_data, dtype=complex)
    freqs = np.asarray(freqs, dtype=float)
    n = min(len(s), len(freqs))
    s, freqs = s[:n], freqs[:n]
    floor_rad = np.deg2rad(floor_deg)

    for _ in range(passes):
        phase = np.unwrap(np.angle(s))
        for i in range(1, n - 1):
            neighbor_avg = (phase[i - 1] + phase[i + 1]) / 2.0
            neighbor_diff = abs(phase[i + 1] - phase[i - 1])
            deviation = abs(phase[i] - neighbor_avg)
            if deviation >= max(floor_rad, multiplier * neighbor_diff):
                t = (freqs[i] - freqs[i - 1]) / (freqs[i + 1] - freqs[i - 1])
                s[i] = s[i - 1] + t * (s[i + 1] - s[i - 1])

    return s

# ------------------------------------------------------------------------------------------------------------------ #
# CALIBRATION
# ------------------------------------------------------------------------------------------------------------------ #

def _build_calibration_fn(self):
    from pathlib import Path
    import logging

    try:
        from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings
        from NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils import get_calibration_path
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.methods import Methods
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.kits import KitsCalibrator
    except Exception as e:
        logging.error("[calibration] import error: %s", e)
        return lambda s11, s21, f: (s11, s21)

    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    method = settings.value("Calibration/Method", "---")
    kit_name = settings.value("Calibration/Name", "---")

    if "_" in kit_name:
        kit_name = kit_name.rsplit("_", 1)[0]

    kits_ok = settings.value("Calibration/Kits", False, type=bool)
    no_cal = settings.value("Calibration/NoCalibration", False, type=bool)

    def calibrate(s11_raw, s21_raw, freqs):

        if no_cal or method == "---":
            return s11_raw, s21_raw

        if kits_ok:
            path = get_calibration_path(
                "modules/dut_measurement/calibration/Kits",
                "modules/dut_measurement/calibration/Kits",
                Path(__file__).resolve()
            )
            return KitsCalibrator(path).kits_selected(
                method, kit_name, s11_raw, s21_raw
            )

        cal_dir = get_calibration_path(
            "modules/dut_measurement/calibration/osm_results",
            "modules/dut_measurement/calibration/osm_results",
            Path(__file__).resolve()
        )

        methods = Methods(cal_dir)

        if method == "OSM (Open - Short - Match)":
            return methods.osm_calibrate_s11(s11_raw), s21_raw

        if method == "Thru Normalization":
            thru_dir = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results",
                "modules/dut_measurement/calibration/thru_results",
                Path(__file__).resolve()
            )
            return s11_raw, Methods(thru_dir).normalization_calibrate_s21(s21_raw)

        if method == "Open/Short Normalization":
            os_dir = get_calibration_path(
                "modules/dut_measurement/calibration/open_short_results",
                "modules/dut_measurement/calibration/open_short_results",
                Path(__file__).resolve()
            )
            return Methods(os_dir).open_short_normalization_calibrate_s11(s11_raw), s21_raw

        if method == "1-Port+N":
            s11_cal = methods.osm_calibrate_s11(s11_raw)
            thru_dir = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results",
                "modules/dut_measurement/calibration/thru_results",
                Path(__file__).resolve()
            )
            s21_cal = Methods(thru_dir).normalization_calibrate_s21(s21_raw)
            return s11_cal, s21_cal

        if method == "Enhanced-Response":
            osm_dir = get_calibration_path(
                "modules/dut_measurement/calibration/osm_results",
                "modules/dut_measurement/calibration/osm_results",
                Path(__file__).resolve()
            )
            thru_dir = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results",
                "modules/dut_measurement/calibration/thru_results",
                Path(__file__).resolve()
            )
            return methods.enhanced_response_calibrate(
                s11_raw, s21_raw, osm_dir, thru_dir
            )

        return s11_raw, s21_raw

    return calibrate