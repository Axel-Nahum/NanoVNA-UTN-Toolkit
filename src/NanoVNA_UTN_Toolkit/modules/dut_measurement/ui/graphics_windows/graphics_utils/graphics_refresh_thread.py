from PySide6.QtCore import QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import QMessageBox
import numpy as np
import logging
import shiboken6
from pathlib import Path

from NanoVNA_UTN_Toolkit.utils import safe_import
from NanoVNA_UTN_Toolkit.shared.utils.qt_logging import log_thread_checkpoint

# ---------------- imports externos ---------------- #

update_plots_with_new_data = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.updates.graphics_update",
    "update_plots_with_new_data"
)

_reset_markers_after_sweep = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.cursors_reset",
    "_reset_markers_after_sweep"
)

_reset_sliders_before_sweep = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.sliders_reset",
    "_reset_sliders_before_sweep"
)

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils",
    "get_settings"
)

get_calibration_path = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils",
    "get_calibration_path"
)

load_sweep_configuration = safe_import(
    "NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.sweep_window.sweep_utils.sweep_utils",
    "load_sweep_configuration"
)

from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.methods import Methods
from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.kits import KitsCalibrator
from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.touchstone_cache import load_network

# =========================================================
# WORKER (THREAD)
# =========================================================

class SweepWorker(QObject):

    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, vna_device, start_freq, stop_freq, segments, parent=None):
        super().__init__()
        self.vna_device = vna_device
        self.start_freq = start_freq
        self.stop_freq = stop_freq
        self.segments = segments
        self.parent = parent
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            self.progress.emit(10)

            if self._abort:
                return

            if not self.vna_device:
                raise RuntimeError("No VNA device")

            if not self.vna_device.connected():
                self.vna_device.connect()

            self.vna_device.datapoints = self.segments

            self.progress.emit(25)

            if self._abort:
                return

            self.vna_device.resetSweep(self.start_freq, self.stop_freq)

            self.progress.emit(50)

            if self._abort:
                return

            self.vna_device.setSweep(self.start_freq, self.stop_freq)

            freqs = np.array(self.vna_device.read_frequencies())

            self.progress.emit(75)

            if self._abort:
                return

            s11 = np.array(self.vna_device.readValues("data 0"))
            s21 = np.array(self.vna_device.readValues("data 1"))

            self.progress.emit(100)

            if self._abort:
                return

            self.finished.emit({
                "freqs": freqs,
                "s11": s11,
                "s21": s21
            })

        except Exception as e:
            self.error.emit(str(e))

# =========================================================
# GUI-THREAD CONTROLLER
# =========================================================
#
# SweepWorker is moved to a QThread, so its signals are emitted from the worker
# thread. A signal connected to a context-less lambda (no QObject receiver) runs
# SYNCHRONOUSLY in the worker thread, which means on_sweep_finished/on_sweep_error
# would touch widgets (canvas draw, setText, QMessageBox) off the GUI thread.
# Connecting to a bound method of this GUI-thread QObject forces a queued
# connection so the handlers run on the GUI thread instead.

class _SweepController(QObject):

    def __init__(self, window):
        super().__init__()  # created on the GUI thread (run_sweep runs there)
        self._window = window
        self._aborted = False

    def abort(self):
        self._aborted = True
        self._window = None

    def on_finished(self, result):  # runs on the GUI thread
        log_thread_checkpoint("graphics_refresh: sweep finished handler (expected GUI)")
        if self._aborted or self._window is None:
            return
        try:
            if not shiboken6.isValid(self._window):
                return
        except RuntimeError:
            return
        on_sweep_finished(self._window, result)

    def on_error(self, msg):  # runs on the GUI thread
        log_thread_checkpoint("graphics_refresh: sweep error handler (expected GUI)")
        if self._aborted or self._window is None:
            return
        try:
            if not shiboken6.isValid(self._window):
                return
        except RuntimeError:
            return
        on_sweep_error(self._window, msg)

    def on_thread_finished(self):  # teardown point
        log_thread_checkpoint("graphics_refresh: worker thread finished, deleting")

def oneshot_sweep_running(window) -> bool:
    """True while the one-shot SweepWorker thread of ``window`` is alive.

    ``window.thread`` shadows ``QObject.thread()``: before the first sweep the
    attribute is that bound method, so a bare ``is not None`` test is wrong.
    """
    thread = getattr(window, "thread", None)
    if not isinstance(thread, QThread):
        return False
    try:
        return thread.isRunning()
    except RuntimeError:  # C++ object already deleted
        return False


# =========================================================
# MAIN THREAD FUNCTIONS
# =========================================================

def run_sweep(self):

    load_sweep_configuration(self)

    if not hasattr(self, "start_freq_hz"):
        logging.warning("start_freq_hz not ready, delaying sweep")
        QTimer.singleShot(200, lambda: run_sweep(self))
        return

    logging.info("[run_sweep] starting sweep")

    if oneshot_sweep_running(self):
        # A second worker would overwrite self.thread while the first QThread is
        # alive ("QThread: Destroyed while thread is still running" -> abort) and
        # interleave commands on the serial port. The menu action has no other guard.
        logging.warning("[run_sweep] sweep already running, ignored")
        return

    if not self.vna_device:
        QMessageBox.warning(self, "Error", "No VNA device connected")
        return

    if not self.vna_device.connected():
        try:
            self.vna_device.connect()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            return

    _reset_sliders_before_sweep(self)

    active_filter = getattr(self, '_active_filter', 'Off')

    if active_filter == "Kalman" and not self.realtime_checkbox.isChecked():
        # Replace, never reset in place: a real-time worker may still be
        # running update() on the old pair in its thread (real_time._done
        # drops that tick when it sees the filters were swapped).
        self.kf_s11 = self.kf_s11.fresh()
        self.kf_s21 = self.kf_s21.fresh()

    self.sweep_button.setText("Sweeping...")
    self.sweep_button.setEnabled(False)
    self.sweep_progress_bar.setVisible(True)
    self.sweep_progress_bar.setValue(0)
    self.reconnect_button.setEnabled(False)

    if not getattr(self, '_initial_sweep_done', False):
        self.realtime_checkbox.setEnabled(False)


    # ---------------- THREAD SETUP ---------------- #

    self.thread = QThread()
    self.worker = SweepWorker(
        self.vna_device,
        self.start_freq_hz,
        self.stop_freq_hz,
        self.segments,
        parent=self,
    )

    self.worker.moveToThread(self.thread)

    # GUI-thread controller so the result/error handlers run on the GUI thread.
    self._sweep_controller = _SweepController(self)

    self.thread.started.connect(self.worker.run)
    self.worker.progress.connect(self.sweep_progress_bar.setValue)
    self.worker.finished.connect(self._sweep_controller.on_finished)
    self.worker.error.connect(self._sweep_controller.on_error)
    # Quit + delete on both outcomes (the previous code leaked the thread on error).
    self.worker.finished.connect(self.thread.quit)
    self.worker.error.connect(self.thread.quit)
    self.worker.finished.connect(self.worker.deleteLater)
    self.worker.error.connect(self.worker.deleteLater)
    self.thread.finished.connect(self._sweep_controller.on_thread_finished)
    self.thread.finished.connect(self.thread.deleteLater)
    self.thread.finished.connect(self._sweep_controller.deleteLater)
    self.thread.start()
    log_thread_checkpoint("graphics_refresh.run_sweep: worker thread started", target_thread=self.thread)


# Threads that have been asked to stop but may still be running their
# blocking serial read.  We keep a Python reference here so that the
# C++ QThread is not destroyed (GC'd) while it is still alive — that
# would produce "QThread: Destroyed while thread is still running".
# Each entry is removed when the thread emits finished().
_stopping_threads: list = []


def stop_sweep(self):
    controller = getattr(self, '_sweep_controller', None)
    worker = getattr(self, 'worker', None)
    thread = getattr(self, 'thread', None)

    if controller:
        try:
            controller.abort()
        except RuntimeError:
            pass

    if worker:
        try:
            # Disconnect progress signal before the widget is destroyed so
            # any queued emission doesn't reach a dangling C++ object.
            worker.progress.disconnect()
        except RuntimeError:
            pass
        try:
            worker.abort()
        except RuntimeError:
            pass

    if thread is not None:
        try:
            thread.quit()
            # Park the thread in _stopping_threads so the Python wrapper
            # (and therefore the C++ QThread) stays alive until the thread
            # finishes its current blocking serial read and exits cleanly.
            _stopping_threads.append(thread)
            def _release(t=thread):
                try:
                    _stopping_threads.remove(t)
                except ValueError:
                    pass
            thread.finished.connect(_release)
        except RuntimeError:
            pass

    self.worker = None
    self.thread = None
    self._sweep_controller = None


def on_sweep_finished(self, result):

    logging.info("[on_sweep_finished] processing data")

    freqs = np.array(result["freqs"])
    s11_med = np.array(result["s11"])
    s21_med = np.array(result["s21"])

    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    calibration_method = settings.value("Calibration/Method", "---")
    kit_name = settings.value("Calibration/Name", "---")

    if "_" in kit_name:
        kit_name = kit_name.rsplit("_", 1)[0]

    cal_dir = get_calibration_path(
        "modules/dut_measurement/calibration/osm_results",
        "modules/dut_measurement/calibration/osm_results",
        Path(__file__).resolve()
    )

    methods = Methods(cal_dir)

    kits_ok = settings.value("Calibration/Kits", False, type=bool)
    no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)
    is_import_dut = settings.value("Calibration/isImportDut", False, type=bool)

    s11 = s11_med
    s21 = s21_med

    if not kits_ok and not no_calibration and not is_import_dut:

        if calibration_method == "OSM (Open - Short - Match)":
            s11 = methods.osm_calibrate_s11(s11_med)

        elif calibration_method == "Thru Normalization":
            cal_dir = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results",
                "modules/dut_measurement/calibration/thru_results",
                Path(__file__).resolve()
            )
            methods = Methods(cal_dir)
            s21 = methods.normalization_calibrate_s21(s21_med)

        elif calibration_method == "Open/Short Normalization":
            cal_dir = get_calibration_path(
                "modules/dut_measurement/calibration/open_short_results",
                "modules/dut_measurement/calibration/open_short_results",
                Path(__file__).resolve()
            )
            methods = Methods(cal_dir)
            s11 = methods.open_short_normalization_calibrate_s11(s11_med)

        elif calibration_method == "1-Port+N":
            s11 = methods.osm_calibrate_s11(s11_med)
            cal_dir = get_calibration_path(
                "modules/dut_measurement/calibration/thru_results",
                "modules/dut_measurement/calibration/thru_results",
                Path(__file__).resolve()
            )
            methods = Methods(cal_dir)
            s21 = methods.normalization_calibrate_s21(s21_med)

        elif calibration_method == "Enhanced-Response":
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
            s11, s21 = methods.enhanced_response_calibrate(
                s11_med, s21_med, osm_dir, thru_dir
            )

    elif kits_ok:
        selected_kit_dir = get_calibration_path(
            "modules/dut_measurement/calibration/Kits",
            "modules/dut_measurement/calibration/Kits",
            Path(__file__).resolve()
        )
        kits_calibrator = KitsCalibrator(selected_kit_dir)
        s11, s21 = kits_calibrator.kits_selected(
            calibration_method, kit_name, s11_med, s21_med
        )

    elif is_import_dut:
        settings.setValue("Calibration/DUT", True)
        data_dut = load_network(self.dut)      # cached by path + mtime
        freqs = np.array(data_dut.f)
        s11 = np.array(data_dut.s[:, 0, 0])
        s21 = np.array(data_dut.s[:, 1, 0])

    # -------------------------------------------------
    # SIGNAL FILTER
    # -------------------------------------------------

    sf_settings = get_settings(
        "INI/dut_measurement/signal_filters/signal_filters.ini",
        "modules/dut_measurement/ui/utils/menu/plot_menu/signal_filters/signal_filters.ini",
        Path(__file__).resolve()
    )

    active_filter = getattr(self, '_active_filter', 'Off')

    if active_filter == "Kalman":
        # One sweep per click (~20 ms), so it stays on the GUI thread. No
        # real-time worker shares these filters: _trigger does not start one
        # while this sweep runs, and in real time run_sweep swapped in a fresh
        # pair before starting it.
        s11_f = np.array([self.kf_s11.update(x) for x in s11])
        s21_f = np.array([self.kf_s21.update(x) for x in s21])
    elif active_filter == "Smoothing":
        pct = sf_settings.value("smoothing/window_pct", 5, type=int)
        n   = len(s11)
        w   = max(1, round(n * pct / 100))
        k   = np.ones(w) / w
        half = w // 2
        def _smooth(s):
            re_f = np.convolve(np.pad(s.real, half, mode='reflect'), k, mode='valid')[:len(s)]
            im_f = np.convolve(np.pad(s.imag, half, mode='reflect'), k, mode='valid')[:len(s)]
            return re_f + 1j * im_f
        s11_f = _smooth(s11)
        s21_f = _smooth(s21)
    else:
        s11_f = s11
        s21_f = s21

    self.freqs = freqs
    self.s11 = s11_f
    self.s21 = s21_f

    # -------------------------------------------------
    # UPDATE UI — rebuild the panels, place the four markers at index 0, and
    # let the Qt backend's coalesced draw_idle() do ONE full draw per panel
    # when this handler returns to the event loop. (Before: two synchronous
    # draws here, a deferred pass with two more and four gc.collect() calls:
    # ~840 ms on the GUI thread per sweep, measured headless.)
    # -------------------------------------------------

    update_plots_with_new_data(self, skip_reset=True, draw=False)
    _reset_markers_after_sweep(self)

    if getattr(self, 'canvas_left', None):
        self.canvas_left.draw_idle()
    if getattr(self, 'canvas_right', None):
        self.canvas_right.draw_idle()

    # -------------------------------------------------
    # UI STATE
    # -------------------------------------------------

    self.sweep_progress_bar.setVisible(False)
    self.sweep_progress_bar.setValue(0)
    self.reconnect_button.setEnabled(True)

    _af = getattr(self, '_active_filter', 'Off')
    if getattr(self, '_rt_active', False) and _af == "Kalman":
        self.sweep_button.setText(f"{self.measurement_ui_button_reset_kalman}")
    else:
        self.sweep_button.setText(f"{self.measurement_ui_button_run_sweep}")

    if not hasattr(self, '_initial_sweep_done') or not self._initial_sweep_done:
        self._initial_sweep_done = True
        self.realtime_checkbox.setEnabled(True)

    self.sweep_button.setEnabled(True)

# =========================================================
# ERROR HANDLER
# =========================================================

def on_sweep_error(self, msg):
    QMessageBox.critical(self, "Sweep Error", msg)

    _af = getattr(self, '_active_filter', 'Off')
    if getattr(self, '_rt_active', False) and _af == "Kalman":
        self.sweep_button.setText(getattr(self, 'measurement_ui_button_reset_kalman', 'Reset Kalman'))
    else:
        self.sweep_button.setText(getattr(self, 'measurement_ui_button_run_sweep', 'Run Sweep'))
    self.sweep_button.setEnabled(True)
    self.sweep_progress_bar.setVisible(False)

    if not getattr(self, '_initial_sweep_done', True):
        self.realtime_checkbox.setEnabled(True)

    try:
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.graphics_refresh import (
            update_reconnect_button_state, _GREEN_BTN_STYLE,
        )
        # Sweep failed — device is disconnected. Force green style directly since
        # vna_device.connected() may still return True before the next serial attempt.
        self.reconnect_button.setEnabled(True)
        self.reconnect_button.setText("Reconnect")
        self.reconnect_button.setStyleSheet(_GREEN_BTN_STYLE)
    except Exception:
        self.reconnect_button.setEnabled(True)