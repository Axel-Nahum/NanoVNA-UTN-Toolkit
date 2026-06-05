import logging

import numpy as np
import skrf as rf

from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread, QTimer

from NanoVNA_UTN_Toolkit.utils import safe_import

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

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

            freqs = np.linspace(self.start_freq_hz, self.stop_freq_hz, self.segments)

            self.vna_device.datapoints = self.segments

            self.start_freq_hz_old = self.start_freq_hz
            self.stop_freq_hz_old = self.stop_freq_hz

            # Load configuration for sweep settings and frequency range parameters
            settings_sweep = get_settings(
                "INI/dut_measurement/sweep_config/sweep_config.ini",
                "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini", 
                Path(__file__).resolve()        
            )

            new_start_freq_hz = settings_sweep.value("Frequency/StartFreqHz", "50000", type=float)
            new_stop_freq_hz = settings_sweep.value("Frequency/StopFreqHz", "1500000", type=float)

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
            logging.exception("[SweepWorker] error")
            self.sweep_failed.emit(str(e))

# ------------------------------------------------------------------------------------------------------------------ #
# PUBLIC API
# ------------------------------------------------------------------------------------------------------------------ #

def on_realtime_toggled(self, enabled):

    if not enabled:
        self.sweep_button.setEnabled(False)
        logging.info("[real_time] ENABLED")
        self._rt_generation = getattr(self, "_rt_generation", 0) + 1
        start_realtime(self)
    else:
        self._initial_sweep_done = True
        self.sweep_button.setEnabled(True)
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
# CORE LOOP
# ------------------------------------------------------------------------------------------------------------------ #

def _trigger(self):

    if not self._rt_active:
        return

    if self._rt_busy:
        return

    if not self.vna_device or not self.vna_device.connected():
        stop_realtime(self)
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

    thread = QThread(self)  
    worker.moveToThread(thread)

    thread.started.connect(worker.run)

    gen = self._rt_generation

    worker.sweep_finished.connect(
        lambda f, s11, s21: _done(self, f, s11, s21, thread, worker, gen)
    )

    worker.sweep_failed.connect(
        lambda msg: _fail(self, msg, thread, worker, gen)
    )

    # SAFE CLEANUP (NO BLOCKING WAIT INSIDE CALLBACK CONTEXT)
    worker.sweep_finished.connect(lambda: _schedule_thread_stop(thread))
    worker.sweep_failed.connect(lambda: _schedule_thread_stop(thread))

    thread.start()

    self._rt_thread = thread
    self._rt_worker = worker


# ------------------------------------------------------------------------------------------------------------------ #
# SAFE THREAD STOP 
# ------------------------------------------------------------------------------------------------------------------ #

def _schedule_thread_stop(thread):
    QTimer.singleShot(0, lambda: _safe_stop_thread(thread))


def _safe_stop_thread(thread):

    if thread is None:
        return

    try:
        thread.quit()
        thread.wait(2000)
    except RuntimeError:
        return

    thread.deleteLater()

# ------------------------------------------------------------------------------------------------------------------ #
# DONE
# ------------------------------------------------------------------------------------------------------------------ #

def _done(self, freqs, s11, s21, thread, worker, gen):

    # ----------------------------------------------------
    # Plot Manager settings
    # ----------------------------------------------------

    settings = get_settings(
        "INI/dut_measurement/signal_filters/signal_filters.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/signal_filters/signal_filters.ini",
        Path(__file__).resolve()
    )

    is_kalman_enabled = settings.value("kalman/enabled", False, type=bool)

    if gen != self._rt_generation:
        return

    # data read from worker, now safe to stop thread and clean up worker references
    self.s11_raw = s11
    self.s21_raw = s21

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

def _fail(self, msg, thread, worker, gen):

    if gen != self._rt_generation:
        return

    logging.error("[real_time] sweep failed: %s", msg)

    self._rt_busy = False

# ------------------------------------------------------------------------------------------------------------------ #
# ABORT
# ------------------------------------------------------------------------------------------------------------------ #

def _abort(self):

    worker = getattr(self, "_rt_worker", None)
    thread = getattr(self, "_rt_thread", None)

    if worker:
        worker.abort()

    if thread:
        QTimer.singleShot(0, lambda: _safe_stop_thread(thread))

    self._rt_worker = None
    self._rt_thread = None


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

        if method == "Normalization":
            thru_dir = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results",
                "modules/dut_measurement/calibration/thru_results",
                Path(__file__).resolve()
            )
            return s11_raw, Methods(thru_dir).normalization_calibrate_s21(s21_raw)

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